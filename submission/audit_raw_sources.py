"""Read pinned public sources and compare every retained score to frozen inputs.

Audit only: no overwrite of data/, no upstream executable code is run.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / 'evidence' / 'followup-20261002'
E.mkdir(exist_ok=True)
RB_SHA = 'b19c7033e964187d12e74a43a07f2d727a3d37e5'
WMT_SHA = '56352a3d563d371622935c84974b3f215abeede3'

def get(url):
    with urllib.request.urlopen(url, timeout=60) as f:
        return f.read()

def rewardbench():
    models = json.loads((ROOT / 'evidence/source-model-files.json').read_text())
    frozen = json.loads((ROOT / 'data/rb2_ranked_panel.json').read_text())
    def one(entry):
        name, path = entry
        url = 'https://huggingface.co/datasets/allenai/reward-bench-2-results/resolve/' + RB_SHA + '/' + path
        raw = get(url)
        d = json.loads(raw)
        assert len(d['id']) == len(d['subset']) == len(d['scores'])
        retained = {}
        duplicate_ids = []
        conflicting_duplicates = []
        for pid, subset, scores in zip(d['id'], d['subset'], d['scores']):
            if subset == 'Ties' or len(scores) != 4:
                continue
            flat = [x[0] if isinstance(x, list) and len(x) == 1 else x for x in scores]
            if not all(isinstance(x, (float, int)) for x in flat):
                continue
            if str(pid) in retained:
                duplicate_ids.append(str(pid))
                if retained[str(pid)] != (subset, list(map(float, flat))):
                    conflicting_duplicates.append(str(pid))
            retained[str(pid)] = (subset, list(map(float, flat)))
        mismatches = []
        for pid in frozen['prompt_ids']:
            if pid not in retained or retained[pid][1] != frozen['scores'][name][pid] or retained[pid][0] != frozen['subset'][pid]:
                mismatches.append(pid)
        print('RB', name, 'mismatches', len(mismatches), flush=True)
        return {'model': name, 'path': path, 'url': url, 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest(), 'retained_ids': sorted(retained, key=int),
                'mismatches': mismatches, 'duplicate_ids': duplicate_ids,
                'conflicting_duplicate_ids': conflicting_duplicates,
                'duplicate_policy': 'last occurrence retained, matching the original builder'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(one, models))
    common = set(records[0]['retained_ids'])
    for record in records:
        common &= set(record.pop('retained_ids'))
    same_ids = sorted(common, key=int) == frozen['prompt_ids']
    report = {'repository_revision': RB_SHA, 'files': records, 'common_ids_identical': same_ids,
              'scores_compared': len(models) * len(frozen['prompt_ids']) * 4,
              'status': 'PASS_PINNED_RAW_SOURCE_RECONSTRUCTION' if same_ids and all(not r['mismatches'] for r in records) else 'FAIL_SOURCE_MISMATCH',
              'license': 'NO_DECLARED_RESULTS_REPOSITORY_LICENSE; NOT_REDISTRIBUTION_CLEARANCE'}
    (ROOT / 'submission/rewardbench-source-audit.json').write_text(json.dumps(report, indent=2)+'\n')

class HashStream:
    def __init__(self, f):
        self.f = f
        self.hash = hashlib.sha256()
        self.count = 0
    def read(self, n=-1):
        b = self.f.read(n)
        self.hash.update(b)
        self.count += len(b)
        return b

def wmt():
    url = 'https://huggingface.co/datasets/tttonyyy/mt-metrics-eval-v2/resolve/' + WMT_SHA + '/mt-metrics-eval-v2.tgz'
    frozen = json.loads((ROOT / 'data/wmt23_metric_panel.json').read_text())
    wanted = 'mt-metrics-eval-v2/wmt23/metric-scores/en-de/'
    raws = {}
    notices = {}
    with urllib.request.urlopen(url, timeout=60) as f:
        stream = HashStream(f)
        with tarfile.open(fileobj=stream, mode='r|gz') as tf:
            for member in tf:
                if not member.isfile():
                    continue
                name = member.name
                if name.startswith(wanted) and name.endswith('-refA.seg.score'):
                    raws[Path(name).name[:-len('-refA.seg.score')]] = tf.extractfile(member).read()
                if any(x in Path(name).name.lower() for x in ['license', 'readme', 'copying', 'notice']):
                    if member.size < 500000:
                        notices[name] = tf.extractfile(member).read().decode(errors='replace')
        while stream.read(1 << 20):
            pass
        archive_digest, archive_bytes = stream.hash.hexdigest(), stream.count
    seen, metrics, duplicates = {}, [], {}
    for name in sorted(raws):
        digest = hashlib.sha256(raws[name]).hexdigest()
        if digest in seen:
            duplicates[name] = seen[digest]
        else:
            seen[digest] = name
            metrics.append(name)
    parsed = {}
    for m in metrics:
        systems = {}
        for line in raws[m].decode().splitlines():
            name, value = line.split('\t')
            systems.setdefault(name, []).append(float(value))
        parsed[m] = systems
    common = set.intersection(*(set(v) for v in parsed.values()))
    systems = sorted(common)
    mismatch_count = 0
    for m in metrics:
        for gi, sid in enumerate(frozen['prompt_ids']):
            values = [parsed[m][s][gi] for s in systems]
            mismatch_count += sum(a != b for a, b in zip(values, frozen['scores'].get(m, {}).get(sid, [])))
    dimensions = metrics == frozen['models'] and systems == frozen['systems'] and all(len(parsed[m][s]) == len(frozen['prompt_ids']) for m in metrics for s in systems)
    records = [{'metric': m, 'sha256': hashlib.sha256(raws[m]).hexdigest(), 'bytes': len(raws[m])} for m in sorted(raws)]
    (E / 'wmt-archive-notices.json').write_text(json.dumps(notices, indent=2)+'\n')
    report = {'mirror_revision': WMT_SHA, 'url': url, 'archive_sha256': archive_digest,
              'archive_bytes': archive_bytes, 'files': records, 'duplicates': duplicates,
              'dimensions_and_order_identical': dimensions, 'value_mismatches': mismatch_count,
              'scores_compared': len(metrics)*len(frozen['prompt_ids'])*len(systems),
              'archive_notice_paths': sorted(notices),
              'status': 'PASS_PINNED_MIRROR_RECONSTRUCTION' if dimensions and mismatch_count == 0 else 'FAIL_SOURCE_MISMATCH',
              'license': 'MIRROR_CARD_MIT; THIRD_PARTY_SCORE_RIGHTS_NOT_AUTOMATICALLY_CLEARED'}
    (ROOT / 'submission/wmt-source-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print('WMT', report['status'], 'scores', report['scores_compared'], 'archive bytes', archive_bytes, flush=True)

if __name__ == '__main__':
    rewardbench()
    wmt()

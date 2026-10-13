"""Verify input identity and chosen-response orientation against native records."""
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
E = ROOT/'evidence/followup-20261002'
RB_SHA = 'b19c7033e964187d12e74a43a07f2d727a3d37e5'
NATIVE_SHA = '7ff08853b0d5686e79b13fda8677024f566a104a'

def get(url):
    with urllib.request.urlopen(url,timeout=60) as f:
        return f.read()

native_url = 'https://huggingface.co/datasets/allenai/reward-bench-2/resolve/'+NATIVE_SHA+'/data/test-00000-of-00001.parquet'
raw = get(native_url)
native = pq.read_table(io.BytesIO(raw)).to_pylist()
by_id = {}
for i, row in enumerate(native):
    by_id.setdefault(str(row['id']), []).append((i, row))
frozen = json.loads((ROOT/'data/rb2_ranked_panel.json').read_text())
models = json.loads((ROOT/'evidence/source-model-files.json').read_text())

def one(entry):
    name,path = entry
    d = json.loads(get('https://huggingface.co/datasets/allenai/reward-bench-2-results/resolve/'+RB_SHA+'/'+path))
    retained = {}
    for j,(pid,subset,scores) in enumerate(zip(d['id'],d['subset'],d['scores'])):
        if subset!='Ties' and len(scores)==4:
            retained[str(pid)] = j
    matches, unmatched, ambiguous = {}, [], []
    for pid in frozen['prompt_ids']:
        texts = d['text'][retained[pid]]
        found = []
        for i,row in by_id.get(pid,[]):
            responses = row['chosen']+row['rejected']
            if len(row['chosen'])!=1 or len(row['rejected'])!=3 or len(responses)!=4 or row['subset']!=frozen['subset'][pid]:
                continue
            if all(row['prompt'].strip() in t and response.strip() in t for t,response in zip(texts,responses)):
                found.append(i)
        if len(found)==1:
            matches[pid] = found[0]
        elif not found:
            unmatched.append(pid)
        else:
            ambiguous.append(pid)
    print(name,'native matches',len(matches),'unmatched',len(unmatched),'ambiguous',len(ambiguous),flush=True)
    return {'model':name,'native_indices':matches,'unmatched_ids':unmatched,'ambiguous_ids':ambiguous}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records=list(pool.map(one,models))
reference = records[0]['native_indices']
cross_model_conflicts = []
for pid in frozen['prompt_ids']:
    values={r['native_indices'][pid] for r in records if pid in r['native_indices']}
    if len(values)>1:
        cross_model_conflicts.append({'id':pid,'native_rows_by_model':{r['model']:r['native_indices'].get(pid) for r in records}})
passed=not cross_model_conflicts and all(not r['unmatched_ids'] and not r['ambiguous_ids'] for r in records)
report={'native_revision':NATIVE_SHA,'native_url':native_url,'native_file_sha256':hashlib.sha256(raw).hexdigest(),
        'results_revision':RB_SHA,'method':'For every retained ID, match the native prompt and each chosen-then-rejected completion as exact substrings of its model-formatted input; require one native row and identical row across models.',
        'records':records,'cross_model_conflicts':cross_model_conflicts,
        'status':'PASS_NATIVE_RECORD_ALIGNMENT_AND_CHOSEN_ORIENTATION' if passed else 'HOLD_SEMANTIC_ALIGNMENT',
        'score_completions_checked':len(records)*len(frozen['prompt_ids'])*4,
        'native_quality_label_condition':'Each matched retained record has exactly one chosen and three rejected responses.',
        'duplicate_ids_do_not_prove_alignment':'Record content rather than ID alone is required.'}
(ROOT/'submission/rewardbench-alignment-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],'conflicts',len(cross_model_conflicts),flush=True)

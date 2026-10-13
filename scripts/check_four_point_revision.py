"""Scoped checks for the four-point revision; restricted data checks are opt-in."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'review-revision/four-point-implementation'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-local', action='store_true')
    parser.add_argument('--packages', action='store_true')
    args = parser.parse_args()
    main_text = (ROOT / 'manuscript/main.tex').read_text()
    appendix = (ROOT / 'manuscript/appendix.tex').read_text()
    baseline = json.loads((ROOT / 'review-revision/editorial-implementation/mathematical-baseline.json').read_text())
    assert re.findall(r'\\begin\{theorem\}.*?\\end\{theorem\}', main_text, re.S) == baseline['main_theorems']
    assert re.findall(r'\\begin\{proposition\}.*?\\end\{proposition\}', main_text, re.S) == baseline['main_propositions']
    proof = appendix.split('\\section{Reproducible Experimental Specification}')[0]
    assert re.findall(r'\\\[.*?\\\]', proof, re.S) == baseline['proof_displays']
    for s in ['Within a frozen panel', 'no per-prompt or per-source return quota',
              'These post-freeze counts exclude the full-panel WMT23 correlation check',
              'assess preference precision among the returned outputs']:
        assert s in main_text, s
    assert 'preferred-response yield' not in main_text
    for s in ['Before assigning splits', 'neither changes score signs',
              'nonpositive correlation would reject the build',
              '0.18425', '0.09446', '0.07931', '173{,}784',
              'does not establish acquisition savings from the start of panel construction',
              r'Q_{\rm exact}\le mK\le NK',
              'This exact bound does not apply directly to the positive-gap results']:
        assert s in appendix, s
    assert 'correlation checks orient scores' not in appendix
    statement = (ROOT / 'DATA_STATEMENT_CURRENT.md').read_text()
    for s in ['173,784', '0.0944620166', '0.0793120831', 'post-freeze', 'reference-only process']:
        assert s in statement, s
    # Every numerical tabular body remains as delivered before these edits.
    tables = 0
    bases = ROOT / 'review-revision/editorial-implementation/table-bases'
    for p in bases.glob('*.tex'):
        old = re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}', p.read_text(), re.S)
        current = re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}', (ROOT / 'manuscript/tables' / p.name).read_text(), re.S)
        clean = lambda v: v.replace(' & Gap (outputs)', ' & Gap').replace(' & Mean max &', ' & Max &')
        assert old == [clean(v) for v in current], p.name
        tables += len(old)
    keys = re.findall(r'@\w+\s*\{\s*([^,]+)', (ROOT / 'manuscript/references.bib').read_text())
    assert len(keys) == len(set(keys))
    cited = {k.strip() for body in re.findall(r'\\cite\w*\{([^}]+)\}', main_text + appendix) for k in body.split(',')}
    assert cited <= set(keys)
    result = {'status': 'PASS_SCOPED_FOUR_POINT_REVISION_CHECKS',
              'core_theorems_propositions_and_proof_displays_preserved': True,
              'tabular_bodies_preserved': tables, 'cited_keys_resolve': len(cited),
              'full_local_evidence_checked': False, 'packages': [],
              'scope': 'Specified claim boundaries, existing arithmetic identities and delivery consistency; not full novelty, human proof or redistribution certification.'}
    if args.full_local:
        pre = json.loads((OUT / 'precheck-three-pass.json').read_text())
        for name, h in pre['protected_files'].items():
            assert digest(ROOT / name) == h, name
        frozen = json.loads((ROOT / 'MANIFEST_SHA256.json').read_text())
        assert digest(ROOT / 'MANIFEST_SHA256.json') == pre['frozen_manifest_sha256']
        for name, h in frozen.items():
            assert digest(ROOT / name) == h, name
        for p in (ROOT / 'history/before-four-point-implementation/manuscript/tables').glob('*.tex'):
            assert p.read_bytes() == (ROOT / 'manuscript/tables' / p.name).read_bytes(), p.name
        import numpy as np
        b = json.loads((ROOT / 'data/wmt23_metric_panel.json').read_text())
        models, ids, systems = b['models'], b['prompt_ids'], b['systems']
        x = np.array([[b['scores'][m][i] for i in ids] for m in models])
        anchor = models.index('BLEURT-20')
        full = np.corrcoef(x.reshape(len(models), -1))[anchor]
        assert np.isfinite(full).all() and (full > 0).all()
        diagnostics = []
        for name, cols in [('WMT23', list(range(len(systems)))),
                           ('WMT23_without_synthetic_ref', [j for j, s in enumerate(systems) if s != 'synthetic_ref'])]:
            correlations = []
            for rep in range(40):
                order = list(range(len(ids)))
                random.Random(87000 + rep).shuffle(order)
                ref = x[:, order[:len(ids) // 3]][:, :, cols].reshape(len(models), -1)
                correlations.append(np.corrcoef(ref)[anchor])
            cs = np.array(correlations)
            assert np.isfinite(cs).all() and (cs > 0).all()
            diagnostics.append({'dataset': name, 'checks': int(cs.size), 'nonpositive': 0, 'minimum': float(cs.min())})
        quality = json.loads((ROOT / 'outputs/query_analysis.json').read_text())['quality_records']
        for r in quality:
            assert 0 <= r['preferred_yield'] <= r['K']
            assert r['precision'] is not None and abs(r['preferred_yield'] - r['K'] * r['precision']) < 1e-9
        columns = json.loads((ROOT / 'outputs/column-certificates/results.json').read_text())['records']
        for r in columns:
            assert r['Q_entry'] <= r['m'] * r['K_col'] <= r['N'] * r['K_col']
            assert r['score_entry_cost'] == r['N'] * r['K_col']
        result.update(full_local_evidence_checked=True,
                      frozen_manifest_entries_preserved=len(frozen),
                      protected_scientific_files_preserved=len(pre['protected_files']),
                      reference_only_diagnostic=diagnostics,
                      yield_identities_checked=len(quality), exact_column_units_checked=len(columns))
    if args.packages:
        for name in ['manuscript/source_private.zip', 'packages/current_mapping_column_code_private.zip', 'packages/synthetic_certificate_reproduction.zip']:
            with zipfile.ZipFile(ROOT / name) as z:
                assert len(z.namelist()) == len(set(z.namelist()))
                manifest = json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'))
                assert set(z.namelist()) == set(manifest) | {'PACKAGE_CONTENTS_SHA256.json'}
                for n, h in manifest.items():
                    assert hashlib.sha256(z.read(n)).hexdigest() == h, (name, n)
                assert not any(n.startswith('data/') for n in z.namelist())
                if 'source_private' in name:
                    assert z.read('manuscript/main.tex') == (ROOT / 'manuscript/main.tex').read_bytes()
                    assert z.read('manuscript/main.pdf') == (ROOT / 'manuscript/main.pdf').read_bytes()
                    assert 'ROOT/REPRODUCTION_FOUR_POINT_REVISION.md' in z.namelist()
                if 'current_mapping' in name:
                    assert z.read('DATA_STATEMENT_CURRENT.md') == (ROOT / 'DATA_STATEMENT_CURRENT.md').read_bytes()
                    assert 'scripts/check_four_point_revision.py' in z.namelist()
                result['packages'].append({'name': name, 'members_verified': len(manifest)})
    OUT.mkdir(exist_ok=True, parents=True)
    (OUT / ('package-regression-check.json' if args.packages else 'regression-check.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

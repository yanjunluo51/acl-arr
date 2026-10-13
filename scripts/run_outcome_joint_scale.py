"""Outcome-count exact MILP on the same empty-history exact scale instances."""
import os
for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
import argparse
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import multiprocessing
import time
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from compact_joint_certificate import compact_certificate
from run_joint_scale_experiment import PANELS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/outcome-joint-scale'
SPEC = ROOT/'review-revision/joint-scale-implementation/outcome-protocol.json'


def task(key):
    panel, rep, q = key
    spec = json.loads(SPEC.read_text())
    c = prepare((panel, 'mean', rep, q))
    selected = np.flatnonzero(c['selected'])
    selected = selected[np.argsort(c['tie'][selected])]
    records = []
    for size in spec['sizes']:
        ids = selected if size == 'full' else selected[:size]
        N = c['N'] if size == 'full' else len(ids)
        k = max(1, round(q*N))
        T = c['T']; budget = 2*k*7*T//10
        rows, caps = c['f'][:, ids].T.tolist(), c['p'][ids].tolist()
        value = compact_certificate(rows, caps, budget, seconds=spec['seconds'], outcome_counts=True)
        records.append(dict(dataset=panel, split=rep, q=q, requested_size=size,
                            N=N, T=T, k=k, budget=budget, epsilon=0,
                            history='empty', stopping='exact',
                            selected_count=len(ids), active_rows=sum(p > 0 for p in caps),
                            rows=rows, caps=caps, observed=[0]*len(ids),
                            original_output_ids=ids.tolist(), **value))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        assert not SPEC.exists()
        spec = dict(panels=PANELS, splits=list(range(8)), q=[.05, .30],
                    sizes=[4, 8, 16, 32, 64, 'full'], alpha=.10,
                    history='empty', stopping='exact', workers=6, seconds=60,
                    expected_records=576, matches_existing_scale_cases=True,
                    joint_plus_separated_shared_wall_limit=True,
                    mode='complete exact flip-outcome-count integer model',
                    pre_results_frozen=True)
        SPEC.write_text(json.dumps(spec, indent=2)+'\n')
        print('Frozen 576 outcome-count exact-certificate cases')
        return
    assert not OUT.exists()
    assert json.loads((ROOT/'review-revision/joint-scale-implementation/outcome-backend-check.json').read_text())['minima'] == 7680
    spec = json.loads(SPEC.read_text())
    OUT.mkdir()
    start = time.monotonic()
    progress = dict(status='RUNNING', cases=0, expected_records=576)
    def save():
        progress['elapsed_seconds'] = time.monotonic()-start
        (OUT/'run_progress.json').write_text(json.dumps(progress, indent=2)+'\n')
    save()
    keys = [(panel, rep, q) for rep in spec['splits'] for q in spec['q'] for panel in spec['panels']]
    with (OUT/'records.jsonl').open('w') as file, multiprocessing.get_context('spawn').Pool(spec['workers']) as pool:
        for group in pool.imap_unordered(task, keys):
            for x in group:
                file.write(json.dumps(x, separators=(',', ':'))+'\n')
            file.flush()
            progress['cases'] += len(group)
            save()
            print(progress['cases'], '/ 576', round(time.monotonic()-start, 1), flush=True)
    assert progress['cases'] == 576
    progress['status'] = 'COMPLETE_EXECUTION_PENDING_AUDIT'
    save()


if __name__ == '__main__':
    main()

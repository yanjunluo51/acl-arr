"""Predefined scale study of the complete exact joint certificate program."""
import os
for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
import argparse
import gc
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import math
import multiprocessing
import platform
import threading
import time
from pathlib import Path
import numpy as np
import psutil
from analyze_acquisition_mechanisms import prepare
from joint_certificate_resources import solve_certificate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/joint-scale'
SPEC = ROOT / 'review-revision/joint-scale-implementation/protocol.json'
PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref',
          'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']


def task(key):
    panel, rep, q = key
    prep_start = time.perf_counter()
    c = prepare((panel, 'mean', rep, q))
    selected = np.flatnonzero(c['selected'])
    selected = selected[np.argsort(c['tie'][selected])]
    setup_seconds = time.perf_counter()-prep_start
    spec = json.loads(SPEC.read_text())
    records = []
    for size in spec['sizes']:
        ids = selected if size == 'full' else selected[:size]
        rows = c['f'][:, ids].T.tolist()
        caps = c['p'][ids].tolist()
        T = c['T']
        N = c['N'] if size == 'full' else len(ids)
        k = max(1, round(q*N))
        budget = 2*k*7*T//10
        S = len(ids)
        eligibility = [(i, r) for i, p in enumerate(caps) if p > 0 for r in range(T)]
        quarter = [0]*S
        for i, r in eligibility[:len(eligibility)//4]:
            quarter[i] |= 1 << r
        for history, observed in [('empty', [0]*S), ('quarter', quarter)]:
            for stopping, epsilon in [('exact', 0), ('primary', math.ceil(.02*S))]:
                gc.collect()
                process = psutil.Process()
                baseline = process.memory_info().rss
                samples = [baseline]
                done = threading.Event()
                def monitor():
                    while not done.wait(.01):
                        samples.append(process.memory_info().rss)
                thread = threading.Thread(target=monitor, daemon=True)
                thread.start()
                value = solve_certificate(rows, caps, budget, epsilon, observed,
                                          separated=True, limits=spec['limits'])
                samples.append(process.memory_info().rss)
                done.set()
                thread.join()
                record = dict(dataset=panel, split=rep, q=q, requested_size=size,
                              full_panel=size == 'full', N=N, selected_count=S,
                              active_rows=sum(p > 0 for p in caps), T=T, k=k,
                              budget=budget, history=history, stopping=stopping,
                              epsilon=epsilon, original_output_ids=ids.tolist(),
                              rows=rows, caps=caps, observed=observed,
                              cohort_preprocessing_seconds=setup_seconds,
                              rss_baseline_bytes=baseline, sampled_peak_rss_bytes=max(samples),
                              rss_sampling_interval_seconds=.01, **value)
                records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        assert not SPEC.exists()
        spec = dict(experiment='exact joint evidence scale study',
                    panels=PANELS, splits=list(range(8)), q=[.05, .30],
                    sizes=[4, 8, 16, 32, 64, 'full'], alpha=.10,
                    histories=['empty', 'quarter'], stopping=['exact', 'primary'],
                    limits=dict(states=100000, transitions=10000000, seconds=60),
                    workers=6, nested_selection='frozen original label-blind tie order',
                    full_candidate_families=True, mean_pooling=True,
                    original_full_panel_budget_for_full=True,
                    subbatch_budget_recomputed=True,
                    offline_truth_used=True, online_policy=False,
                    expected_records=2304,
                    resource_limits_apply_to_joint_plus_separated_search=True,
                    rss_includes_python_runtime_inputs_and_resident_caches=True,
                    pre_results_frozen=True)
        SPEC.write_text(json.dumps(spec, indent=2)+'\n')
        print('Frozen 2304 scale cases before execution')
        return
    assert not OUT.exists(), 'Resume from saved receipts instead of overwriting runs'
    spec = json.loads(SPEC.read_text())
    OUT.mkdir()
    start = time.monotonic()
    progress = dict(status='RUNNING', cases=0, expected_records=spec['expected_records'],
                    platform=platform.platform(), python=platform.python_version(),
                    workers=spec['workers'])
    def save():
        progress['elapsed_seconds'] = time.monotonic()-start
        (OUT/'run_progress.json').write_text(json.dumps(progress, indent=2)+'\n')
    save()
    keys = [(panel, rep, q) for rep in spec['splits'] for q in spec['q'] for panel in spec['panels']]
    with (OUT/'records.jsonl').open('w') as file, multiprocessing.get_context('spawn').Pool(spec['workers']) as pool:
        for group in pool.imap_unordered(task, keys):
            for record in group:
                file.write(json.dumps(record, separators=(',', ':'))+'\n')
            file.flush()
            progress['cases'] += len(group)
            save()
            print(progress['cases'], '/', spec['expected_records'], round(time.monotonic()-start, 1), flush=True)
    assert progress['cases'] == spec['expected_records']
    progress['status'] = 'COMPLETE_EXECUTION_PENDING_AUDIT'
    save()


if __name__ == '__main__':
    main()

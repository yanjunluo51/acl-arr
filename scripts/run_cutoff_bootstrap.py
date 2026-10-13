"""Group-resampled reference cutoff sensitivity; test outputs remain fixed."""
import os
for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import math
import multiprocessing
import time
from pathlib import Path
import numpy as np
from mapping_column_experiments import raw, indices, map_scores, cdf
from query_selection import aggregate, endpoint_cost, all_flips, capacity
from tolerance_certificates import minimum_gap_certificate
from run_joint_scale_experiment import PANELS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/cutoff-bootstrap'
SPEC = ROOT / 'review-revision/joint-scale-implementation/bootstrap-protocol.json'


def task(key):
    panel, rep = key
    spec = json.loads(SPEC.read_text())
    z, values, width = raw(panel)
    ix, seed, _, _ = indices(panel, rep, '1')
    reference, test = ix[0], ix[2]
    original_ref, original_test, _, _, _ = map_scores(panel, rep, '1', 'right')
    if panel.startswith('WMT24'):
        labels = np.repeat(np.asarray(z['source_document_ids'], dtype=object), width)
    else:
        labels = np.repeat(np.arange(len(z['prompt_ids'])), width)
    ref_labels = labels[reference]
    units = list(dict.fromkeys(ref_labels.tolist()))
    blocks = [np.flatnonzero(ref_labels == unit) for unit in units]
    rng = np.random.default_rng(spec['seed'] + PANELS.index(panel)*1000 + rep)
    N, T = len(test), len(z['models'])-7
    q = spec['q']
    k = max(1, round(q*N))
    budget = 2*k*7*T//10
    original = {}
    for agg in ['median', 'mean']:
        cutoff = float(np.sort(aggregate(original_ref[:7], agg))[-max(1, round(q*len(reference)))])
        mask = aggregate(original_test[:7], agg) >= cutoff
        original[agg] = cutoff, mask
    records = []
    for draw in range(spec['bootstrap_replicates']):
        sampled = rng.integers(0, len(blocks), len(blocks))
        positions = np.concatenate([blocks[i] for i in sampled])
        fixed_ref = original_ref[:, positions]
        rr = reference[positions]
        fitted_ref = np.array([cdf(row[rr], row[rr], 'right') for row in values])
        fitted_test = np.array([cdf(row[test], row[rr], 'right') for row in values])
        for arm, ref, tt in [('cutoff_only', fixed_ref, original_test),
                             ('maps_and_cutoff', fitted_ref, fitted_test)]:
            for agg in ['median', 'mean']:
                cutoff = float(np.sort(aggregate(ref[:7], agg))[-max(1, round(q*len(rr)))])
                base, hidden = tt[:7], tt[7:]
                selected = aggregate(base, agg) >= cutoff
                p = endpoint_cost(base, cutoff, agg)
                f = all_flips(base, hidden, cutoff, agg)
                assert np.all(f <= p)
                active = selected & (p > 0)
                S = int(selected.sum())
                free = int(np.sum(selected & (p == 0)))
                vl = free + capacity(T*p[active], budget)
                vhi = S
                optimum = capacity(f.sum(axis=0)[selected], budget)
                epsilon = math.ceil(.02*S)
                oldcut, oldmask = original[agg]
                union = int(np.sum(selected | oldmask))
                result = dict(dataset=panel, split=rep, draw=draw, arm=arm,
                              aggregator=agg, q=q, N=N, T=T, k=k, budget=budget,
                              reference_groups=len(blocks), reference_outputs=len(rr),
                              cutoff=cutoff, original_cutoff=oldcut,
                              cutoff_delta=cutoff-oldcut,
                              selected_count=S, active_rows=int(active.sum()),
                              invariant_count=free, V_initial_lower=vl,
                              V_initial_upper=vhi, initial_gap=vhi-vl,
                              epsilon=epsilon, zero_query_stop=vhi-vl <= epsilon,
                              full_information_retained=optimum,
                              selected_jaccard=float(np.sum(selected & oldmask))/union if union else 1.,
                              median_exact_minimum=None, median_primary_minimum=None)
                if agg == 'median':
                    opposition = (f[:, active].sum(axis=0)//4).tolist()
                    assert np.all((p[active] == 4))
                    result['median_exact_minimum'] = minimum_gap_certificate(opposition, T, budget//4, 0)['queries']
                    result['median_primary_minimum'] = minimum_gap_certificate(opposition, T, budget//4, epsilon)['queries']
                records.append(result)
    return records


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        assert not SPEC.exists()
        spec = dict(panels=PANELS, splits=list(range(8)), q=.05,
                    bootstrap_replicates=50, seed=620275,
                    arms=['cutoff_only', 'maps_and_cutoff'],
                    aggregators=['median', 'mean'], alpha=.10,
                    unit='whole original reference prompt/source/document group',
                    original_test_groups_fixed=True,
                    full_candidate_families=True, quality_labels_used=False,
                    acquisition_policies_rerun=False,
                    mean_minimum_claim=False, independent_protocol_instances=True,
                    expected_records=9600, workers=4, pre_results_frozen=True)
        SPEC.write_text(json.dumps(spec, indent=2)+'\n')
        print('Frozen 9600 full-test bootstrap protocol instances')
        return
    assert not OUT.exists()
    OUT.mkdir()
    spec = json.loads(SPEC.read_text())
    start = time.monotonic()
    progress = dict(status='RUNNING', cases=0, expected_records=spec['expected_records'])
    def save():
        progress['elapsed_seconds'] = time.monotonic()-start
        (OUT/'run_progress.json').write_text(json.dumps(progress, indent=2)+'\n')
    save()
    keys = [(panel, rep) for rep in spec['splits'] for panel in spec['panels']]
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

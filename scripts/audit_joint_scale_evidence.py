"""Saved-witness audit, independent small-instance optimization and summaries."""
import argparse
import collections
import csv
import hashlib
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import math
import statistics
from pathlib import Path
import numpy as np
from check_joint_panels import solve as independent_subset_milp

ROOT = Path(__file__).resolve().parents[1]


def capacity(values, budget):
    total = 0
    for n, value in enumerate(sorted(values), 1):
        total += value
        if total > budget:
            return n-1
    return len(values)


def read(folder):
    return [json.loads(line) for line in (ROOT/'outputs'/folder/'records.jsonl').open()]


def scale():
    directory = ROOT/'outputs/joint-scale'
    progress = json.loads((directory/'run_progress.json').read_text())
    assert progress['status'] == 'COMPLETE_EXECUTION_PENDING_AUDIT'
    records = read('joint-scale')
    assert len(records) == 2304
    seen = set()
    checked = calls = 0
    for x in records:
        key = x['dataset'], x['split'], x['q'], x['requested_size'], x['history'], x['stopping']
        assert key not in seen
        seen.add(key)
        assert x['N'] >= x['selected_count'] == len(x['rows'])
        assert x['active_rows'] == sum(p > 0 for p in x['caps'])
        assert x['budget'] == 2*x['k']*7*x['T']//10
        assert x['k'] == max(1, round(x['q']*x['N']))
        assert x['epsilon'] == (0 if x['stopping'] == 'exact' else math.ceil(.02*x['selected_count']))
        assert len(set(x['original_output_ids'])) == x['selected_count']
        lo, up = [], []
        T = x['T']
        new_count = 0
        for i, (row, cap, obs) in enumerate(zip(x['rows'], x['caps'], x['observed'])):
            new = (x['query_mask'] >> (i*T)) & ((1 << T)-1)
            assert not new & obs
            new_count += bin(new).count('1')
            mask = obs | new
            lower = sum(v for r, v in enumerate(row) if (mask >> r) & 1)
            lo.append(lower)
            up.append(lower+(T-bin(mask).count('1'))*cap)
            assert all(0 <= value <= cap for value in row)
        b = x['budget']
        assert new_count == x['queries']
        vl, vh = capacity(up, b), capacity(lo, b)
        assert (vl, vh) == (x['V_lower'], x['V_upper'])
        assert vh-vl <= x['epsilon']
        assert sum(up[i] for i in range(len(up)) if x['safe_mask'] >> i & 1) <= b
        assert capacity([sum(row) for row in x['rows']], b) == x['true_optimum']
        if x['status'] == 'OPTIMAL':
            assert x['joint_optimal'] and x['separated_optimal']
            assert x['split_queries'] >= x['queries']
        if x['separated_optimal']:
            assert x['joint_optimal']
        do_independent = (len(x['rows']) <= 4 or
                          (len(x['rows']) == 8 and x['split'] == 0 and x['history'] == 'empty' and x['stopping'] == 'exact'))
        if do_independent:
            q, split, n = independent_subset_milp(x['rows'], x['caps'], b, x['epsilon'], x['observed'])
            calls += n
            if x['joint_optimal']:
                assert q == x['queries'], key
            else:
                assert q <= x['queries'], key
            if x['separated_optimal']:
                assert split == x['split_queries'], key
            checked += 1
    summaries = []
    for size in [4, 8, 16, 32, 64, 'full']:
        g = [x for x in records if x['requested_size'] == size]
        assert len(g) == 384
        proven = [x for x in g if x['joint_optimal']]
        paired = [x for x in g if x['separated_optimal']]
        saving = sum(x['split_queries']-x['queries'] for x in paired)
        total = sum(x['split_queries'] for x in paired)
        summaries.append(dict(size=size, cases=len(g), active_min=min(x['active_rows'] for x in g),
                              active_max=max(x['active_rows'] for x in g),
                              joint_proven=len(proven), paired_proven=len(paired),
                              runtime_median=statistics.median(x['solver_seconds'] for x in g),
                              runtime_p90=float(np.percentile([x['solver_seconds'] for x in g], 90)),
                              sampled_rss_p90_mib=float(np.percentile([x['sampled_peak_rss_bytes']/2**20 for x in g], 90)),
                              strict_improvements=sum(x['split_queries'] > x['queries'] for x in paired),
                              total_saved=saving, total_separate=total,
                              aggregate_saving_fraction=saving/total if total else None,
                              statuses=dict(collections.Counter(x['status'] for x in g))))
    result = dict(status='PASS_SCALE_SAVED_WITNESSES_AND_SUBSET_MILP',
                  cases=len(records), independent_subset_minima_checked=checked,
                  independent_subset_MILP_calls=calls, all_incumbents_integer_verified=True,
                  summaries=summaries,
                  large_nonzero_minima_independently_certified=False,
                  limits_are_unresolved_not_infeasible=True)
    (directory/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return result


def bootstrap():
    directory = ROOT/'outputs/cutoff-bootstrap'
    assert json.loads((directory/'run_progress.json').read_text())['status'] == 'COMPLETE_EXECUTION_PENDING_AUDIT'
    records = read('cutoff-bootstrap')
    assert len(records) == 9600
    seen = set()
    for x in records:
        key = x['dataset'], x['split'], x['draw'], x['arm'], x['aggregator']
        assert key not in seen
        seen.add(key)
        assert x['N'] > 0 and x['reference_outputs'] > 0
        assert x['budget'] == 2*x['k']*7*x['T']//10
        assert 0 <= x['selected_jaccard'] <= 1
        assert 0 <= x['cutoff'] <= 1
        assert x['initial_gap'] == x['V_initial_upper']-x['V_initial_lower']
        assert x['V_initial_lower'] <= x['full_information_retained'] <= x['V_initial_upper'] == x['selected_count']
        assert x['active_rows']+x['invariant_count'] == x['selected_count']
        assert x['zero_query_stop'] == (x['initial_gap'] <= x['epsilon'])
        if x['aggregator'] == 'mean':
            assert x['median_exact_minimum'] is None
    summaries = []
    for panel in sorted({x['dataset'] for x in records}):
        for agg in ['median', 'mean']:
            for arm in ['cutoff_only', 'maps_and_cutoff']:
                g = [x for x in records if (x['dataset'], x['aggregator'], x['arm']) == (panel, agg, arm)]
                assert len(g) == 400
                row = dict(dataset=panel, aggregator=agg, arm=arm, cases=len(g),
                           jaccard_median=statistics.median(x['selected_jaccard'] for x in g),
                           jaccard_p10=float(np.percentile([x['selected_jaccard'] for x in g], 10)),
                           jaccard_p90=float(np.percentile([x['selected_jaccard'] for x in g], 90)),
                           zero_stop_fraction=statistics.fmean(x['zero_query_stop'] for x in g),
                           initial_gap_median=statistics.median(x['initial_gap'] for x in g),
                           active_median=statistics.median(x['active_rows'] for x in g),
                           median_exact_minimum_median=statistics.median(x['median_exact_minimum'] for x in g) if agg == 'median' else None,
                           median_primary_minimum_median=statistics.median(x['median_primary_minimum'] for x in g) if agg == 'median' else None)
                summaries.append(row)
    result = dict(status='PASS_BOOTSTRAP_SAVED_ACCOUNTING', cases=len(records),
                  summary_cells=len(summaries), summaries=summaries,
                  descriptive_percentiles_not_population_CIs=True,
                  separate_protocol_instances_not_independent_populations=True,
                  mean_full_panel_minima_computed=False)
    (directory/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PASS bootstrap accounting', len(records))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bootstrap-only', action='store_true')
    args = parser.parse_args()
    bootstrap()
    if not args.bootstrap_only:
        scale()

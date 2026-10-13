"""Describe the same initial-gap strata without changing any acquisition run."""
from pathlib import Path
import csv
import itertools
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/nontrivial-certification'
METHODS = ['fixed', 'random', 'largest_width', 'reference_priority']
PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref',
          'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']


def average(values):
    return statistics.fmean(values) if values else None


def compute():
    initial, records, sources = {}, {}, []
    for name in ['outputs/query_metrics.json', 'outputs/review-external/results.json']:
        x = json.loads((ROOT / name).read_text())
        sources.append({'path': name, 'query_records': len(x['query_records'])})
        for r in x['baseline_records']:
            if r['method'] == 'zero_query_structural':
                key = (r['dataset'], r['aggregator'], r['q'], r['split'])
                assert key not in initial
                initial[key] = r
        for r in x['query_records']:
            key = (r['dataset'], r['aggregator'], r['q'], r['stopping'], r['split'], r['method'])
            assert key not in records
            records[key] = r
    cells = []
    for panel, pool, q, stop in itertools.product(PANELS, ['median', 'mean'],
                                                 [.05, .1, .2, .3],
                                                 ['two_percent_gap', 'exact_gap']):
        bases = [initial[panel, pool, q, i] for i in range(40)]
        selected = []
        epsilons = []
        for i, b in enumerate(bases):
            rs = [records[panel, pool, q, stop, i, m] for m in METHODS]
            eps = rs[0]['epsilon']
            assert all(r['epsilon'] == eps and r['alpha'] == .1 for r in rs)
            gap = b['selected_count'] - b['returned_count']
            assert gap >= 0
            assert all((r['queries'] > 0) == (gap > eps) for r in rs)
            assert all(r['certificate_gap'] <= eps for r in rs)
            if gap > eps:
                selected.append(i)
            epsilons.append(eps)
        methods = []
        for method in METHODS:
            all_rows = [records[panel, pool, q, stop, i, method] for i in range(40)]
            rows = [all_rows[i] for i in selected]
            fields = ['queries', 'active_fraction', 'returned_count', 'certificate_gap',
                      'selected_coverage', 'realized_regret']
            methods.append({'method': method,
                            'all_splits': {f: average([r[f] for r in all_rows]) for f in fields},
                            'nontrivial_splits': {f: average([r[f] for r in rows]) for f in fields}})
        cells.append({'dataset': panel, 'aggregator': pool, 'q': q, 'stopping': stop,
                      'alpha': .1, 'splits': 40, 'nontrivial_splits': len(selected),
                      'nontrivial_split_ids': selected, 'zero_query_splits': 40-len(selected),
                      'initial_gap_mean': average([b['selected_count']-b['returned_count'] for b in bases]),
                      'initial_selected_coverage_mean': average([b['selected_coverage'] for b in bases]),
                      'epsilon_mean': average(epsilons), 'methods': methods})
    assert len(cells) == 96 and len(records) == 15360 and len(initial) == 1920
    return {'scope': 'Post-protocol descriptive stratification; no tuning or population inference.',
            'selection_condition': 'initial V_upper - V_lower > epsilon, common to all methods',
            'initial_upper': 'selected_count; zero observed candidate-test costs',
            'sources': sources, 'query_records_checked': len(records), 'initial_states_checked': len(initial),
            'new_scorer_inference': False, 'cells': cells}


def main():
    OUT.mkdir(exist_ok=True)
    result = compute()
    (OUT / 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    rows = []
    for c in result['cells']:
        for m in c['methods']:
            row = {k: c[k] for k in ['dataset', 'aggregator', 'q', 'stopping', 'alpha',
                   'splits', 'nontrivial_splits', 'zero_query_splits', 'initial_gap_mean',
                   'initial_selected_coverage_mean', 'epsilon_mean']}
            row['method'] = m['method']
            for group in ['all_splits', 'nontrivial_splits']:
                for field, value in m[group].items():
                    row[group+'_'+field] = value
            rows.append(row)
    with (OUT / 'cells.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(json.dumps({'cells': len(result['cells']), 'method_cells': len(rows),
                      'query_records_checked': result['query_records_checked']}))


if __name__ == '__main__':
    main()

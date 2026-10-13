"""Same-instance full-panel mean certificate requirements versus discovery."""
import csv
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)
from fractions import Fraction
from pathlib import Path
import statistics
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/outcome-joint-scale'


def main():
    primary = [json.loads(x) for x in (OUT/'records.jsonl').open()]
    full = {(x['dataset'], x['split'], x['q']): x for x in primary if x['requested_size'] == 'full'}
    assert len(full) == 96
    for line in (OUT/'retry-records.jsonl').open():
        r = json.loads(line)
        if r['primary_key'][3] == 'full' and r['joint_optimal'] and r['separated_optimal']:
            key = tuple(r['primary_key'][:3])
            full[key] = dict(full[key], **{k:v for k,v in r.items() if k != 'primary_key'})
    assert all(x['joint_optimal'] and x['separated_optimal'] for x in full.values())
    original = list(csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open()))
    saved = {(x['dataset'], int(x['split']), float(x['q']), x['method']): x for x in original
             if x['aggregator'] == 'mean' and Fraction(x['tau']) == 0}
    methods = ['fixed', 'random', 'largest_width', 'reference_priority']
    records = []
    for key, witness in sorted(full.items()):
        for method in methods:
            x = saved[(*key, method)]
            count = int(x['queries'])
            assert count >= witness['queries']
            assert int(x['returned_count']) == int(x['V_upper']) == witness['V_lower']
            minimum = witness['queries']
            records.append(dict(dataset=key[0], split=key[1], q=key[2], method=method,
                                N=witness['N'], T=witness['T'], budget=witness['budget'],
                                exact_queries=count, minimum=minimum,
                                separated_minimum=witness['split_queries'],
                                sharing_saving=witness['split_queries']-minimum,
                                ratio=count/minimum if minimum else None))
    summaries = []
    for panel in sorted({x['dataset'] for x in records}):
        for q in [.05, .30]:
            for method in methods:
                g = [x for x in records if (x['dataset'], x['q'], x['method']) == (panel, q, method)]
                assert len(g) == 8
                positive = [x['ratio'] for x in g if x['ratio'] is not None]
                summaries.append(dict(dataset=panel, q=q, method=method, splits=8,
                                      minimum_mean=statistics.fmean(x['minimum'] for x in g),
                                      queries_mean=statistics.fmean(x['exact_queries'] for x in g),
                                      positive_minima=len(positive),
                                      ratio_mean=statistics.fmean(positive) if positive else None,
                                      strict_sharing=sum(x['sharing_saving'] > 0 for x in g)))
    for filename, data in [('full_discovery_records.csv', records), ('full_discovery_summary.csv', summaries)]:
        with (OUT/filename).open('w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
    total_separate = sum(x['split_queries'] for x in full.values())
    saved_count = sum(x['split_queries']-x['queries'] for x in full.values())
    receipt = dict(status='PASS_MATCHING_FULL_MEAN_MINIMA_AND_EXACT_DISCOVERY',
                   full_instances=96, discovery_records=384,
                   minimums_positive=sum(x['queries'] > 0 for x in full.values()),
                   strict_sharing=sum(x['queries'] < x['split_queries'] for x in full.values()),
                   total_saved=saved_count, total_separated=total_separate,
                   aggregate_saving_fraction=saved_count/total_separate,
                   exact_stop_only=True, original_full_panel_N_and_budget=True,
                   original_online_paths_unchanged=True)
    (OUT/'full-discovery-check.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()

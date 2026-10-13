"""Portable integer-witness checks of both compact formulations and retries."""
import collections
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def capacity(cost, b):
    spent = count = 0
    for v in sorted(cost):
        if spent+v > b:
            break
        spent += v; count += 1
    return count


def check(x, value=None):
    value = value or x
    T = x['T']; b = x['budget']
    assert x['k'] == max(1, round(x['q']*x['N']))
    assert b == 2*x['k']*7*T//10
    low, up = [], []
    for i, (row, p, obs) in enumerate(zip(x['rows'], x['caps'], x['observed'])):
        new = value['query_mask'] >> (i*T) & ((1 << T)-1)
        assert not new & obs
        mask = new | obs
        lo = sum(v for r, v in enumerate(row) if mask >> r & 1)
        low.append(lo); up.append(lo+(T-bin(mask).count('1'))*p)
    assert bin(value['query_mask']).count('1') == value['queries']
    assert sum(up[i] for i in range(len(up)) if value['safe_mask'] >> i & 1) <= b
    assert (capacity(up, b), capacity(low, b)) == (value['V_lower'], value['V_upper'])
    assert value['V_lower'] == value['V_upper'] == capacity([sum(row) for row in x['rows']], b)
    if value['separated_optimal'] and value['joint_optimal']:
        assert value['queries'] <= value['split_queries']
    if value['joint_optimal'] and 'joint_lower_bound' in value:
        assert value['joint_lower_bound'] == value['queries']


def main(root=ROOT, write=True):
    global ROOT
    ROOT = root
    dp = [json.loads(line) for line in (ROOT/'outputs/joint-scale/records.jsonl').open()]
    dpindex = {(x['dataset'], x['split'], x['q'], x['requested_size']): x
               for x in dp if x['history'] == 'empty' and x['stopping'] == 'exact'}
    result = {}
    index = {}
    for name in ['compact-joint-scale', 'outcome-joint-scale']:
        directory = ROOT/'outputs'/name
        assert json.loads((directory/'run_progress.json').read_text())['status'] == 'COMPLETE_EXECUTION_PENDING_AUDIT'
        records = [json.loads(line) for line in (directory/'records.jsonl').open()]
        assert len(records) == 576
        index[name] = {}
        compared = 0
        for x in records:
            key = x['dataset'], x['split'], x['q'], x['requested_size']
            assert key not in index[name]
            index[name][key] = x
            check(x)
            old = dpindex[key]
            assert (old['rows'], old['caps'], old['budget']) == (x['rows'], x['caps'], x['budget'])
            if old['joint_optimal'] and x['joint_optimal']:
                assert old['queries'] == x['queries']
                compared += 1
            if old['separated_optimal'] and x['separated_optimal']:
                assert old['split_queries'] == x['split_queries']
            if name == 'outcome-joint-scale':
                other = index['compact-joint-scale'][key]
                if other['joint_optimal'] and x['joint_optimal']:
                    assert other['queries'] == x['queries']
                if other['separated_optimal'] and x['separated_optimal']:
                    assert other['split_queries'] == x['split_queries']
        summaries = []
        for size in [4, 8, 16, 32, 64, 'full']:
            g = [x for x in records if x['requested_size'] == size]
            assert len(g) == 96
            paired = [x for x in g if x['separated_optimal'] and x['joint_optimal']]
            saved = sum(x['split_queries']-x['queries'] for x in paired)
            total = sum(x['split_queries'] for x in paired)
            times = sorted(x['seconds'] for x in g)
            position = .9*(len(times)-1)
            i = int(position); frac = position-i
            p90 = times[i]*(1-frac)+times[min(i+1, len(times)-1)]*frac
            summaries.append(dict(size=size, cases=len(g),
                                  active_min=min(x['active_rows'] for x in g), active_max=max(x['active_rows'] for x in g),
                                  joint_proven=sum(x['joint_optimal'] for x in g), paired_proven=len(paired),
                                  runtime_median=statistics.median(times), runtime_p90=p90,
                                  max_variables=max(x['max_variables'] for x in g),
                                  max_constraints=max(x['max_constraints'] for x in g),
                                  strict_improvements=sum(x['queries'] < x['split_queries'] for x in paired),
                                  total_saved=saved, total_separate=total,
                                  aggregate_saving_fraction=saved/total if total else None))
        receipt = dict(status='PASS_COMPACT_INTEGER_WITNESSES_AND_MATCHING_OPTIMA',
                       cases=len(records), DP_minima_compared=compared,
                       unresolved=sum(x['status'] != 'OPTIMAL' for x in records), summaries=summaries)
        result[name] = receipt
        if write:
            (directory/'audit.json').write_text(json.dumps(receipt, indent=2)+'\n')
    retries = ROOT/'outputs/outcome-joint-scale/retry-records.jsonl'
    if retries.exists():
        assert json.loads(retries.with_name('retry-progress.json').read_text())['status'] == 'COMPLETE_EXECUTION_PENDING_AUDIT'
        data = [json.loads(line) for line in retries.open()]
        for x in data:
            check(index['outcome-joint-scale'][tuple(x['primary_key'])], x)
        result['retries'] = dict(cases=len(data), joint_proven=sum(x['joint_optimal'] for x in data),
                                 paired_proven=sum(x['separated_optimal'] and x['joint_optimal'] for x in data),
                                 unresolved=sum(x['status'] != 'OPTIMAL' for x in data))
    return result


if __name__ == '__main__':
    print(json.dumps(main(), indent=2))

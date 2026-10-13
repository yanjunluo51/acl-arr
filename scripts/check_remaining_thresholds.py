"""Resolve the one remaining subbatch by enumerating feasible true thresholds.

This is an additional optimization check, not a replacement for primary records.
Thresholds impossible even with the true complete row costs cannot certify any
partial completion. Each retained threshold is solved in the full count model.
"""
import os
for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)
from pathlib import Path
import compact_joint_certificate as module
from joint_certificates import capacity
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/outcome-joint-scale'


def main():
    assert not (OUT/'threshold-check.json').exists()
    data = [json.loads(x) for x in (OUT/'records.jsonl').open()]
    x = next(x for x in data if x['dataset'] == 'WMT24-ja-zh' and x['split'] == 3 and x['q'] == .05 and x['requested_size'] == 64)
    F = list(map(sum, x['rows']))
    s = capacity(F, x['budget']); p = s+1
    thresholds = [t for t in range(max(F)+1)
                  if p*t-sum(max(0, t-v) for v in F) >= x['budget']+1]
    protocol = dict(primary_key=['WMT24-ja-zh', 3, .05, 64], safe_target=s,
                    screened_thresholds=thresholds, seconds_per_threshold=60,
                    outside_thresholds_impossible_even_with_true_costs=True,
                    original_records_preserved=True)
    (OUT/'threshold-protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    original = module.milp
    records = []
    for t in thresholds:
        calls = []
        def fixed(*args, **kwargs):
            # In the full joint model the final variable is its integer t.
            lower = kwargs['bounds'].lb.copy(); upper = kwargs['bounds'].ub.copy()
            lower[-1] = upper[-1] = t
            kwargs['bounds'] = module.Bounds(lower, upper)
            result = original(*args, **kwargs)
            calls.append({k: getattr(result, k, None) for k in
                          ['status', 'message', 'fun', 'mip_dual_bound', 'mip_gap']})
            return result
        module.milp = fixed
        value = module.compact_certificate(x['rows'], x['caps'], x['budget'],
                                           separated=False, seconds=60, outcome_counts=True)
        assert len(calls) == 1
        records.append(dict(threshold=t, minimum_scope='fixed_threshold',
                            solver=calls[0], **value))
        print(t, value['queries'], value['joint_lower_bound'], value['seconds'], flush=True)
    lower = min(x['joint_lower_bound'] for x in records)
    best = min(records, key=lambda x: x['queries'])
    result = dict(protocol=protocol, records=records,
                  global_lower_bound=lower, global_upper_bound=best['queries'],
                  globally_proven=lower == best['queries'],
                  best_witness=best)
    (OUT/'threshold-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print('GLOBAL', lower, best['queries'], result['globally_proven'])


if __name__ == '__main__':
    main()

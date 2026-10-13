"""Exact threshold-screened outcome solver for empty or residual exact tasks."""
from compact_joint_certificate import compact_certificate
from joint_certificates import capacity


def threshold_certificate(rows, caps, budget, observed=None, seconds_per_threshold=60):
    active = [row for row, p in zip(rows, caps) if p > 0]
    F = list(map(sum, active))
    p = capacity(F, budget)+1
    if not active or p > len(active):
        return compact_certificate(rows, caps, budget, observed=observed,
                                   separated=False, outcome_counts=True,
                                   seconds=seconds_per_threshold)
    thresholds = [t for t in range(max(F)+1)
                  if p*t-sum(max(0, t-v) for v in F) >= budget+1]
    assert thresholds
    values = [compact_certificate(rows, caps, budget, observed=observed,
                                  separated=False, outcome_counts=True,
                                  fixed_threshold=t, seconds=seconds_per_threshold)
              for t in thresholds]
    best = min(values, key=lambda x: x['queries'])
    lower = min(x['joint_lower_bound'] for x in values)
    result = dict(best)
    result.update(minimum_scope='global', joint_lower_bound=lower,
                  joint_optimal=lower == best['queries'],
                  status='OPTIMAL' if lower == best['queries'] else 'UNRESOLVED',
                  permitted_thresholds=thresholds,
                  threshold_receipts=[dict(threshold=t, **x) for t, x in zip(thresholds, values)])
    return result

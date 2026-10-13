"""Shared helpers for the 2026-10-12 ACL review experiments.

Reuses the frozen instance loader (analyze_acquisition_mechanisms.prepare):
full-reference right ECDF, original splits, original candidate families,
alpha = .10. Hidden candidate test scores are read only through the query
callback or for post hoc full-information quantities.
"""
import os
for _k in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[_k] = '1'
import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_acquisition_mechanisms import prepare  # noqa: E402
from query_selection import aggregate, capacity  # noqa: E402

PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref',
          'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']
QS = [.05, .10, .20, .30]
SPLITS = list(range(40))


def instance(panel, agg, rep, q):
    c = prepare((panel, agg, rep, q))
    c['epsilon'] = int(math.ceil(.02 * c['S']))
    c['agg'] = agg
    return c


def flip_matrix(base, x, cutoff, agg):
    """Boolean (n, M): replacing base member j of row i by score x[i] flips row i."""
    M, n = base.shape
    old = aggregate(base, agg) >= cutoff
    out = np.zeros((n, M), dtype=bool)
    for j in range(M):
        rep = base.copy()
        rep[j] = x
        out[:, j] = (aggregate(rep, agg) >= cutoff) != old
    return out


def flip_count(base, x, cutoff, agg):
    return flip_matrix(base, x, cutoff, agg).sum(axis=1).astype(np.int64)


def reference_path(c):
    """Reference-priority entry order on active selected rows (budget independent).

    Same rule as the frozen solver: row with the smallest estimated total cost
    (observed flips plus predictions for unqueried entries; WMT24 uses 1e-12
    ticks), ties by the seeded label-blind priority; within the row, the
    unqueried candidate with the largest predicted upper-cost reduction.
    Returns a list of (local_row, candidate).
    """
    m, T = c['m'], c['T']
    if m == 0:
        return []
    truth, est, ids, tie = c['truth'], c['ticks'], c['ids'], c['tie']
    quant = c['quantized']
    known = np.zeros((m, T), bool)
    low = np.zeros(m, np.int64)
    rowtie = tie[ids]
    path = []
    est = np.asarray(est)
    for _ in range(m * T):
        remain = np.flatnonzero(~known.all(axis=1))
        unk = np.where(known, 0, est).sum(axis=1)
        expected = low * 10**12 + unk if quant else low + unk
        sub = remain[np.lexsort((rowtie[remain], expected[remain]))]
        i = int(sub[0])
        cand = np.flatnonzero(~known[i])
        r = int(cand[np.lexsort((cand, est[i, cand]))][0])
        known[i, r] = True
        low[i] += int(truth[i, r])
        path.append((i, r))
    return path


def first_stop(n, gap_at, eps):
    """Smallest prefix length t in [0, n] with gap_at(t) <= eps (gap nonincreasing)."""
    lo, hi = 0, n
    if gap_at(0) <= eps:
        return 0
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if gap_at(mid) <= eps:
            hi = mid
        else:
            lo = mid
    return hi

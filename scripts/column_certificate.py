"""Exact offline column witnesses for the existing unconstrained median model.

A column contains all batch scores; only selected boundary bits affect capacity.
No acquisition policy receives this hindsight matrix. Enumeration uses all T
columns, with no candidate or row truncation. Pure Python is available without
Numba; Numba accelerates the same complete subset enumeration.
"""
import numpy as np
try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        return lambda function: function


def capacity_sorted(values, budget):
    a = np.sort(np.asarray(values, dtype=np.int64))
    return int(np.count_nonzero(np.cumsum(a, dtype=np.int64) <= budget))


@njit(cache=True)
def _popcounts(T):
    pc = np.zeros(1 << T, dtype=np.int64)
    for a in range(1, len(pc)):
        pc[a] = pc[a >> 1] + (a & 1)
    return pc


@njit(cache=True)
def _hist_capacity(hist, offset, budget):
    available = budget
    count = 0
    for value in range(len(hist)):
        cost = value + offset
        take = hist[value] if cost == 0 else min(hist[value], available // cost)
        count += take
        available -= take * cost
        if take < hist[value]:
            break
    return count


@njit(cache=True)
def _enumerate(supports, frequencies, T, budget, L, lower_bound, upper_bound):
    pc = _popcounts(T)
    best, witness, evaluated = upper_bound + 1, -1, 0
    for subset in range(1 << T):
        size = pc[subset]
        if size < lower_bound or size >= best or size > upper_bound:
            continue
        hist = np.zeros(T + 1, dtype=np.int64)
        for i in range(len(supports)):
            hist[pc[supports[i] & subset]] += frequencies[i]
        evaluated += 1
        if (_hist_capacity(hist, 0, budget) == L and
                _hist_capacity(hist, T-size, budget) == L):
            best, witness = size, subset
            if best == lower_bound:
                break
    return best, witness, evaluated


def support_masks(bits):
    y = np.asarray(bits, dtype=np.int64)
    assert y.ndim == 2 and 0 <= y.shape[1] <= 20
    assert np.all((y == 0) | (y == 1))
    return y @ (1 << np.arange(y.shape[1], dtype=np.int64))


def certify_subset(bits, budget, subset):
    """Independent raw-row sort check; no support-frequency histogram."""
    y = np.asarray(bits, dtype=np.int64)
    cols = [c for c in range(y.shape[1]) if subset & (1 << c)]
    lower = y[:, cols].sum(axis=1, dtype=np.int64)
    upper = lower + y.shape[1] - len(cols)
    return capacity_sorted(upper, budget), capacity_sorted(lower, budget)


def exact_columns(bits, budget, entry_witness, upper_bound=None):
    y = np.asarray(bits, dtype=np.int64)
    m, T = y.shape
    assert budget >= 0 and entry_witness >= 0
    L = capacity_sorted(y.sum(axis=1), budget)
    if m == 0 or entry_witness == 0:
        assert certify_subset(y, budget, 0) == (L, L)
        return {'K_col': 0, 'subset_mask': 0, 'columns': [], 'L': L,
                'count_lower_bound': 0, 'evaluated_subsets': 0,
                'unique_row_supports': len(np.unique(support_masks(y)))}
    lower = (entry_witness + m - 1) // m
    upper = min(T, entry_witness, T if upper_bound is None else upper_bound)
    masks, counts = np.unique(support_masks(y), return_counts=True)
    K, witness, evaluated = _enumerate(masks, counts, T, budget, L, lower, upper)
    assert lower <= K <= upper and witness >= 0
    assert certify_subset(y, budget, int(witness)) == (L, L)
    return {'K_col': int(K), 'subset_mask': int(witness),
            'columns': [c for c in range(T) if witness & (1 << c)],
            'L': L, 'count_lower_bound': int(lower),
            'evaluated_subsets': int(evaluated), 'unique_row_supports': len(masks)}


@njit(cache=True)
def _check_predecessors(raw_masks, T, budget, K):
    """All (K-1)-subsets, full rows, separate combination traversal.

By monotonicity, failure of every (K-1)-subset excludes every smaller subset.
The supplied witness has already passed a raw-row sort feasibility check.
"""
    if K == 0:
        return True, 0
    target = K - 1
    pc = _popcounts(T)
    checked = 0
    subset = (1 << target) - 1
    while subset < (1 << T):
        lower_hist = np.zeros(T+1, dtype=np.int64)
        for i in range(len(raw_masks)):
            # Count revealed zeros first; a separate representation of costs.
            zeros = pc[(~raw_masks[i]) & subset]
            lower_hist[target-zeros] += 1
        checked += 1
        if (_hist_capacity(lower_hist, 0, budget) ==
                _hist_capacity(lower_hist, T-target, budget)):
            return False, checked
        if target == 0:
            break
        lowbit = subset & (-subset)
        increase = subset + lowbit
        subset = increase | (((subset ^ increase) >> 2) // lowbit)
    return True, checked


def verify_minimality(bits, budget, result):
    L = capacity_sorted(np.asarray(bits).sum(axis=1), budget)
    assert certify_subset(bits, budget, result['subset_mask']) == (L, L)
    valid, count = _check_predecessors(support_masks(bits), bits.shape[1], budget,
                                     result['K_col'])
    assert valid, 'A smaller column certificate exists'
    return int(count)

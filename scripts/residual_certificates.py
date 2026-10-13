"""Exact hindsight residual and mixed median certificates.

The completion model, uniform replacement loss and bit budget are unchanged.
Entry actions have a common positive price; column prices may differ. Prices
are additive action costs, not measured GPU runtimes. No online policy sees
the true bit matrix supplied to these offline witness functions.
"""
import numpy as np


def capacity(values, budget):
    total = count = 0
    for value in sorted(int(v) for v in values):
        if total + value > budget:
            break
        total += value
        count += 1
    return count


def _state(bits, known, budget, epsilon):
    original = np.asarray(bits)
    y = np.asarray(bits, dtype=np.int64)
    k = np.asarray(known, dtype=bool)
    if y.ndim != 2 or y.shape != k.shape or y.shape[1] < 1:
        raise ValueError('Expected matching row-by-candidate arrays')
    if (np.any(original != y) or np.any((y != 0) & (y != 1)) or
            budget < 0 or epsilon < 0 or int(budget) != budget or int(epsilon) != epsilon):
        raise ValueError('Invalid Boolean instance or budget/tolerance')
    z = y.sum(axis=1)
    o = (y * k).sum(axis=1)
    a = ((1-y) * k).sum(axis=1)
    return y, k, z, o, a


def safety_table(z, upper, budget, max_count):
    """Cardinality/true-cost DP; never replaces the online certificate solver."""
    dp = [dict() for _ in range(max_count+1)]
    dp[0][0] = (0, ())
    for i, (cost, u) in enumerate(zip(z, upper)):
        for n in range(min(i+1, max_count), 0, -1):
            for previous, (value, rows) in list(dp[n-1].items()):
                total = previous + int(cost)
                if total > budget:
                    continue
                candidate = (value+int(u), rows+(i,))
                if total not in dp[n] or candidate < dp[n][total]:
                    dp[n][total] = candidate
    return [min(values.values()) if values else None for values in dp]


def opposition_extension(z, observed, budget, target):
    """Minimum new oppositions excluding every target-row set."""
    z, o = np.asarray(z, dtype=np.int64), np.asarray(observed, dtype=np.int64)
    m = len(z)
    if target > m or sum(sorted(o)[:target]) > budget:
        return 0, o.copy(), None
    if target < 1 or sum(sorted(z)[:target]) <= budget:
        raise ValueError('Exclusion target is truly feasible')
    for level in range(int(z.max(initial=0))+1):
        counts = np.maximum(o, np.minimum(z, level))
        smallest_sum = sum(sorted(counts)[:target])
        if smallest_sum >= budget+1:
            break
    expected = int((counts-o).sum()) - (smallest_sum-budget-1)
    # Reduce new observations along the cheapest target-row frontier. Each
    # reduction decreases that prefix sum by exactly one, until strict exclusion.
    while smallest_sum > budget+1:
        threshold = sorted(counts)[target-1]
        eligible = np.flatnonzero((counts > o) & (counts <= threshold))
        assert len(eligible)
        counts[int(eligible[0])] -= 1
        smallest_sum -= 1
        assert sum(sorted(counts)[:target]) == smallest_sum
    assert int((counts-o).sum()) == expected
    return expected, counts, level


def residual_gap_certificate(bits, known, budget, epsilon=0):
    y, k, z, o, a = _state(bits, known, budget, epsilon)
    budget, epsilon = int(budget), int(epsilon)
    m, T = y.shape
    optimum = capacity(z, budget)
    safe = safety_table(z, T-a, budget, optimum)
    candidates = []
    for n in range(max(0, optimum-epsilon), optimum+1):
        upper_sum, rows = safe[n]
        agreements = max(0, upper_sum-budget)
        oppositions, counts, level = opposition_extension(z, o, budget, n+epsilon+1)
        candidates.append((agreements+oppositions, n, agreements, oppositions,
                           rows, counts, level))
    best = min(candidates, key=lambda v: (v[0], v[1]))
    size, n, agreement_count, opposition_count, rows, counts, level = best
    reveal = np.zeros_like(k)
    left = agreement_count
    for i in rows:
        cols = np.flatnonzero(~k[i] & (y[i] == 0))
        take = min(left, len(cols))
        reveal[i, cols[:take]] = True
        left -= take
    assert left == 0
    for i in range(m):
        cols = np.flatnonzero(~k[i] & (y[i] == 1))
        take = int(counts[i]-o[i])
        assert take <= len(cols)
        reveal[i, cols[:take]] = True
    final = k | reveal
    lower = (y*final).sum(axis=1)
    upper = T-((1-y)*final).sum(axis=1)
    vminus, vplus = capacity(upper, budget), capacity(lower, budget)
    assert reveal.sum() == size and vplus-vminus <= epsilon
    return {'queries': int(size), 'safe_target': int(n),
            'agreements': int(agreement_count), 'oppositions': int(opposition_count),
            'opposition_level': level, 'true_optimum': int(optimum),
            'V_minus': vminus, 'V_plus': vplus,
            'entries': np.argwhere(reveal).tolist()}


def mixed_certificate(bits, budget, column_costs, entry_cost=1, epsilon=0):
    """Full finite optimization; no column/row truncation or greedy substitute."""
    original = np.asarray(bits)
    y = original
    if y.ndim != 2 or y.shape[1] != len(column_costs):
        raise ValueError('Column prices must match all candidates')
    y, _, _, _, _ = _state(original, np.zeros_like(original, dtype=bool), budget, epsilon)
    budget, epsilon = int(budget), int(epsilon)
    prices = [int(c) for c in column_costs]
    if (not np.isfinite(entry_cost) or entry_cost <= 0 or int(entry_cost) != entry_cost or
            any(c <= 0 for c in prices) or any(c != v for c, v in zip(prices, column_costs))):
        raise ValueError('Use positive integer prices (rational prices can be scaled)')
    best = None
    T = y.shape[1]
    for subset in range(1 << T):
        columns = [c for c in range(T) if subset >> c & 1]
        paid_columns = sum(prices[c] for c in columns)
        if best is not None and paid_columns > best['cost']:
            continue
        known = np.zeros_like(y, dtype=bool)
        known[:, columns] = True
        residual = residual_gap_certificate(y, known, budget, epsilon)
        cost = paid_columns + entry_cost*residual['queries']
        result = {'cost': cost, 'columns': columns, 'subset_mask': subset,
                  'column_cost': paid_columns, 'entry_cost': entry_cost,
                  'epsilon': epsilon, 'residual': residual}
        if best is None or (cost, len(columns), subset) < (best['cost'], len(best['columns']), best['subset_mask']):
            best = result
    return best

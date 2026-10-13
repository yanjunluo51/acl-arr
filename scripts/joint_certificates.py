"""Exact residual entry certificates for integer flip contributions.

Offline verifier construction, not an online acquisition policy. Per-row subset
states preserve joint safety/exclusion evidence, including intermediate mean flips.
"""
from itertools import product

def capacity(cost, budget):
    total = count = 0
    for x in sorted(cost):
        if total + x > budget: break
        total += x; count += 1
    return count


def row_states(values, observed, p):
    """(additional count, added lower cost, query-bitmask)."""
    states = {(0, 0): 0}
    for r, value in enumerate(values):
        if (observed >> r) & 1: continue
        updates = {}
        for (q, v), mask in states.items():
            key = (q + 1, v + value)
            if key not in states and key not in updates:
                updates[key] = mask | (1 << r)
        states.update(updates)
    return [(q, v, mask) for (q, v), mask in sorted(states.items())]


def _solve(rows, caps, observed, budget, safe, exclude, cutoff):
    """Row DP: safe cardinality, upper cost, lower-cost threshold deficit."""
    m = len(rows); T = len(rows[0]) if rows else 0
    bound = None if exclude is None else exclude * cutoff - budget - 1
    if bound is not None and bound < 0: return None
    states = {(0, 0, 0): (0, 0, 0)}
    for i, (values, p, obs) in enumerate(zip(rows, caps, observed)):
        lower0 = sum(v for r, v in enumerate(values) if (obs >> r) & 1)
        upper0 = lower0 + (T - bin(obs).count('1')) * p
        new = {}
        for q, added, mask in row_states(values, obs, p):
            lower = lower0 + added; upper = upper0 - q * p + added
            deficit = 0 if bound is None else max(0, cutoff - lower)
            for (n, u, d), (cost, chosen, kept) in states.items():
                dd = d + deficit
                if bound is not None and dd > bound: continue
                for take in ((0,) if safe is None else (0, 1)):
                    nn = n + take; uu = u + take * upper
                    if safe is not None and (nn > safe or nn + m-i-1 < safe or uu > budget): continue
                    key = (nn, uu, dd); newcost = cost + q
                    old = new.get(key)
                    if old is None or newcost < old[0]:
                        new[key] = (newcost, chosen | (mask << (i*T)), kept | (take << i))
        states = new
        if not states: return None
    results = [v for (n, _, _), v in states.items() if safe is None or n == safe]
    return min(results, default=None)


def minimum_joint_certificate(rows, caps, budget, epsilon=0, observed=None,
                              separated=False):
    """Minimum *additional* unit-cost entry queries plus a reconstructed witness.

    `rows` contains true integer f_ir; `caps[i]` is the row endpoint maximum.
    `observed[i]` is a bitmask of already revealed entries. No assumptions on
    intermediate attainable score levels are needed: endpoints suffice for bounds.
    """
    rows = [list(map(int, row)) for row in rows]; caps = list(map(int, caps))
    m = len(rows); T = len(rows[0]) if m else 0
    observed = [0]*m if observed is None else list(map(int, observed))
    if budget < 0 or epsilon < 0 or int(budget) != budget or int(epsilon) != epsilon:
        raise ValueError('Budget and epsilon must be nonnegative integers')
    if len(caps) != m or len(observed) != m or any(len(v) != T for v in rows):
        raise ValueError('Shape mismatch')
    if any(p < 0 or obs < 0 or obs >= 1 << T or any(x < 0 or x > p for x in row)
           for row, p, obs in zip(rows, caps, observed)):
        raise ValueError('Invalid caps, flips or observed entries')
    if not m: return dict(queries=0, query_mask=0, safe_mask=0, safe_target=0,
                         true_optimum=0, V_lower=0, V_upper=0, split_queries=0)
    true = [sum(v) for v in rows]; L = capacity(true, budget)
    maxlevel = max(true, default=0); best = None; splitbest = None
    for s in range(max(0, L-epsilon), L+1):
        p = s + epsilon + 1; exclusion = p if p <= m else None
        levels = range((budget+1+p-1)//p, maxlevel+1) if exclusion else [0]
        safeonly = _solve(rows, caps, observed, budget, s, None, 0) if separated else None
        exbest = None
        for t in levels:
            joint = _solve(rows, caps, observed, budget, s, exclusion, t)
            if joint is not None and (best is None or joint[0] < best['queries']):
                best = dict(queries=joint[0], query_mask=joint[1], safe_mask=joint[2],
                            safe_target=s, exclusion_target=exclusion, threshold=t,
                            true_optimum=L)
            if separated:
                ex = _solve(rows, caps, observed, budget, None, exclusion, t)
                if ex is not None and (exbest is None or ex[0] < exbest): exbest = ex[0]
        if separated and safeonly is not None and exbest is not None:
            splitbest = min(splitbest, safeonly[0]+exbest) if splitbest is not None else safeonly[0]+exbest
    assert best is not None
    low, up = [], []
    for i, (row, cap, obs) in enumerate(zip(rows, caps, observed)):
        query = (best['query_mask'] >> (i*T)) & ((1 << T)-1)
        assert not query & obs
        mask = query | obs
        lo = sum(v for r, v in enumerate(row) if (mask >> r) & 1)
        low.append(lo); up.append(lo+(T-bin(mask).count('1'))*cap)
    vlo, vhi = capacity(up, budget), capacity(low, budget)
    assert vlo <= L <= vhi and vhi-vlo <= epsilon
    assert sum(up[i] for i in range(m) if (best['safe_mask'] >> i) & 1) <= budget
    best.update(V_lower=vlo, V_upper=vhi, split_queries=splitbest)
    if separated: assert best['queries'] <= splitbest
    return best

"""Instrumented exact row DP, with reusable row states and resource receipts.

Same integer optimization as joint_certificates.py. Limits terminate a search;
they never turn an incumbent into a certified minimum. Offline true flips only.
"""
import time
from joint_certificates import capacity, row_states


class ResourceLimit(RuntimeError):
    pass


def solve_certificate(rows, caps, budget, epsilon=0, observed=None,
                      separated=True, limits=None):
    limits = limits or {}
    start = time.perf_counter()
    stats = dict(transitions=0, threshold_runs=0, peak_states=0,
                 row_state_pairs=0, row_state_seconds=0., joint_seconds=None,
                 separated_seconds=None)
    rows = [list(row) for row in rows]
    caps = list(caps)
    m = len(rows)
    T = len(rows[0]) if m else 0
    observed = [0] * m if observed is None else list(observed)
    assert len(caps) == len(observed) == m
    assert isinstance(budget, int) and budget >= 0
    assert isinstance(epsilon, int) and epsilon >= 0
    assert all(len(row) == T and all(isinstance(v, int) and 0 <= v <= p for v in row)
               for row, p in zip(rows, caps))
    assert all(isinstance(p, int) and p >= 0 for p in caps)
    assert all(0 <= obs < 1 << T for obs in observed)
    low0 = [sum(v for r, v in enumerate(row) if (obs >> r) & 1)
            for row, obs in zip(rows, observed)]
    upper0 = [lo + (T - bin(obs).count('1')) * p
              for lo, p, obs in zip(low0, caps, observed)]
    true = [sum(row) for row in rows]
    L = capacity(true, budget)
    base = dict(true_optimum=L, V_initial_lower=capacity(upper0, budget),
                V_initial_upper=capacity(low0, budget))

    def check():
        if stats['transitions'] > limits.get('transitions', float('inf')):
            raise ResourceLimit('TRANSITION_LIMIT')
        if time.perf_counter() - start > limits.get('seconds', float('inf')):
            raise ResourceLimit('TIME_LIMIT')

    def finish(witness):
        lo, up = [], []
        for i, (row, p, obs) in enumerate(zip(rows, caps, observed)):
            mask = (witness['query_mask'] >> (i * T)) & ((1 << T) - 1)
            assert not mask & obs
            mask |= obs
            lower = sum(v for r, v in enumerate(row) if mask >> r & 1)
            lo.append(lower)
            up.append(lower + (T - bin(mask).count('1')) * p)
        witness.update(V_lower=capacity(up, budget), V_upper=capacity(lo, budget))
        assert witness['V_lower'] <= L <= witness['V_upper']
        assert witness['V_upper'] - witness['V_lower'] <= epsilon
        assert sum(up[i] for i in range(m) if witness['safe_mask'] >> i & 1) <= budget
        assert bin(witness['query_mask']).count('1') == witness['queries']
        return witness

    def safe_mask(cost):
        left = budget
        mask = 0
        for i in sorted(range(m), key=lambda i: (cost[i], i)):
            if cost[i] > left:
                break
            left -= cost[i]
            mask |= 1 << i
        return mask

    if base['V_initial_upper'] - base['V_initial_lower'] <= epsilon:
        result = finish(dict(queries=0, query_mask=0, safe_mask=safe_mask(upper0)))
        return dict(status='OPTIMAL', **base, **result, split_queries=0,
                    joint_optimal=True, separated_optimal=True,
                    solver_seconds=time.perf_counter()-start, stats=stats)

    # Full remaining active evidence is an initial feasible certificate. It is
    # an upper bound, not a minimum, until the entire search completes.
    fullmask = sum(((1 << T)-1 ^ obs) << (i*T)
                   for i, (p, obs) in enumerate(zip(caps, observed)) if p > 0)
    best = finish(dict(queries=bin(fullmask).count('1'), query_mask=fullmask,
                       safe_mask=safe_mask(true)))
    splitbest = None
    joint_proven = False
    try:
        cache = [row_states(row, obs, p) if p else [(0, 0, 0)]
                 for row, obs, p in zip(rows, observed, caps)]
        stats['row_state_pairs'] = sum(map(len, cache))
        stats['row_state_seconds'] = time.perf_counter() - start
        check()

        def dp(safe, exclude, cutoff, incumbent=None):
            stats['threshold_runs'] += 1
            bound = None if exclude is None else exclude * cutoff - budget - 1
            if bound is not None and bound < 0:
                return None
            states = {(0, 0, 0): (0, 0, 0)}
            for i, (p, pairs) in enumerate(zip(caps, cache)):
                new = {}
                for q, added, mask in pairs:
                    lower = low0[i] + added
                    upper = upper0[i] - q*p + added
                    deficit = 0 if bound is None else max(0, cutoff-lower)
                    for (n, u, d), (cost, chosen, kept) in states.items():
                        stats['transitions'] += 1
                        if stats['transitions'] % 4096 == 0:
                            check()
                        newcost = cost + q
                        # Future query costs are nonnegative, so an incumbent
                        # permits pruning states that cannot improve its value.
                        if incumbent is not None and newcost >= incumbent:
                            continue
                        dd = d + deficit
                        if bound is not None and dd > bound:
                            continue
                        for take in ((0,) if safe is None else (0, 1)):
                            nn, uu = n+take, u+take*upper
                            if safe is not None and (nn > safe or nn+m-i-1 < safe or uu > budget):
                                continue
                            key = nn, uu, dd
                            old = new.get(key)
                            if old is None or newcost < old[0]:
                                new[key] = newcost, chosen | mask << (i*T), kept | take << i
                                stats['peak_states'] = max(stats['peak_states'], len(new))
                                if len(new) > limits.get('states', float('inf')):
                                    raise ResourceLimit('STATE_LIMIT')
                states = new
                if not states:
                    return None
            return min((v for (n, _, _), v in states.items()
                        if safe is None or n == safe), default=None)

        targets = []
        for s in range(max(0, L-epsilon), L+1):
            p = s+epsilon+1
            exclude = p if p <= m else None
            levels = range((budget+p)//p, max(true)+1) if exclude else [0]
            targets.append((s, exclude, list(levels)))
            for t in levels:
                value = dp(s, exclude, t, best['queries'])
                if value is not None:
                    best = finish(dict(queries=value[0], query_mask=value[1],
                                       safe_mask=value[2], safe_target=s, threshold=t))
        stats['joint_seconds'] = time.perf_counter()-start
        joint_proven = True
        if separated:
            for s, exclude, levels in targets:
                safety = dp(s, None, 0)
                exbest = None
                for t in levels:
                    exclusion = dp(None, exclude, t)
                    if exclusion is not None:
                        exbest = min(exbest, exclusion[0]) if exbest is not None else exclusion[0]
                assert safety is not None and exbest is not None
                value = safety[0]+exbest
                splitbest = min(splitbest, value) if splitbest is not None else value
            assert splitbest >= best['queries']
            stats['separated_seconds'] = time.perf_counter()-start-stats['joint_seconds']
        return dict(status='OPTIMAL', **base, **best, split_queries=splitbest,
                    joint_optimal=True, separated_optimal=separated,
                    solver_seconds=time.perf_counter()-start, stats=stats)
    except ResourceLimit as exc:
        return dict(status=str(exc), **base, **best, split_queries=None,
                    joint_optimal=joint_proven,
                    separated_optimal=False,
                    solver_seconds=time.perf_counter()-start, stats=stats)

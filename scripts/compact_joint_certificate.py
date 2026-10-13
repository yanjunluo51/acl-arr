"""Exact entry-variable MILP equivalent to the joint row-state certificate.

Binary revealed-entry and safe-row variables share the same observations.
Continuous AND variables linearize safety; an integer order threshold excludes
larger sets without subset or row-state enumeration. Offline true flips only.
"""
import math
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from joint_certificates import capacity


def compact_certificate(rows, caps, budget, epsilon=0, observed=None,
                        separated=True, seconds=60, outcome_counts=False, fixed_threshold=None):
    start = time.perf_counter()
    T = len(rows[0]) if rows else 0
    observed = [0]*len(rows) if observed is None else observed
    assert all(isinstance(x, int) and 0 <= x <= p for row, p in zip(rows, caps) for x in row)
    ids = [i for i, p in enumerate(caps) if p > 0]
    free = sum(p == 0 for p in caps)
    active = [rows[i] for i in ids]
    cap = [caps[i] for i in ids]
    obs = [observed[i] for i in ids]
    m = len(active)
    low = [sum(v for r, v in enumerate(row) if obs[i] >> r & 1) for i, row in enumerate(active)]
    up = [low[i]+(T-bin(obs[i]).count('1'))*cap[i] for i in range(m)]
    L = capacity([sum(row) for row in active], budget)
    cells = [(i, r) for i in range(m) for r in range(T) if not obs[i] >> r & 1]
    groups = [[r] for i, r in cells]
    if outcome_counts:
        cells, groups = [], []
        for i, row in enumerate(active):
            by_value = {}
            for r, value in enumerate(row):
                if not obs[i] >> r & 1:
                    by_value.setdefault(value, []).append(r)
            for value, candidates in sorted(by_value.items()):
                cells.append((i, candidates[0]))
                groups.append(candidates)
    multiplicities = list(map(len, groups))
    calls = 0
    max_variables = max_constraints = 0

    def witness(query, safe):
        qm = sum(1 << (ids[i]*T+r) for (i, _), candidates, count in zip(cells, groups, query) for r in candidates[:count])
        sm = sum(1 << i for i, p in enumerate(caps) if p == 0)
        sm |= sum(1 << ids[i] for i, y in enumerate(safe) if y)
        lower, upper = [], []
        for i, (row, p, known) in enumerate(zip(rows, caps, observed)):
            mask = ((qm >> (i*T)) & ((1 << T)-1)) | known
            lo = sum(v for r, v in enumerate(row) if mask >> r & 1)
            lower.append(lo)
            upper.append(lo+(T-bin(mask).count('1'))*p)
        result = dict(queries=bin(qm).count('1'), query_mask=qm, safe_mask=sm,
                      V_lower=capacity(upper, budget), V_upper=capacity(lower, budget))
        assert sum(upper[i] for i in range(len(rows)) if sm >> i & 1) <= budget
        return result

    if capacity(low, budget)-capacity(up, budget) <= epsilon:
        safe = [0]*m
        left = budget
        for i in sorted(range(m), key=lambda i: (up[i], i)):
            if up[i] > left:
                break
            safe[i] = 1
            left -= up[i]
        value = witness([0]*len(cells), safe)
        return dict(status='OPTIMAL', **value, true_optimum=L+free,
                    joint_optimal=True, separated_optimal=separated,
                    split_queries=0 if separated else None,
                    seconds=time.perf_counter()-start, milp_calls=0,
                    max_variables=0, max_constraints=0)

    def run(s, mode):
        nonlocal calls, max_variables, max_constraints
        p = s+epsilon+1
        exclusion = mode != 'safety' and p <= m
        safety = mode != 'exclusion'
        if not safety and not exclusion:
            return dict(value=0, lower_bound=0, proven=True, query=[0]*len(cells), safe=None)
        left = seconds-(time.perf_counter()-start)
        if left <= .05:
            return dict(value=None, lower_bound=0, proven=False)
        count = len(cells)
        xvars = list(range(count))
        yvars = list(range(count, count+m)) if safety else []
        count += len(yvars)
        zvars = {}
        if safety:
            for a, (i, r) in enumerate(cells):
                if cap[i] > active[i][r]:
                    zvars[a] = count
                    count += 1
        wvars = list(range(count, count+m)) if exclusion else []
        count += len(wvars)
        tv = count if exclusion else None
        count += int(exclusion)
        objective = np.zeros(count)
        objective[xvars] = 1
        integral = np.zeros(count)
        integral[xvars+yvars] = 1
        lower = np.zeros(count)
        upper = np.ones(count)
        upper[xvars] = multiplicities
        for a, z in zvars.items():
            upper[z] = multiplicities[a]
        if exclusion:
            integral[tv] = 1
            upper[wvars] = T*max(cap)
            upper[tv] = max(map(sum, active))
            if fixed_threshold is not None:
                assert 0 <= fixed_threshold <= upper[tv]
                lower[tv] = upper[tv] = fixed_threshold
        rr, cc, vv, lb, ub = [], [], [], [], []
        def constraint(coeff, a=-np.inf, b=np.inf):
            number = len(lb)
            for key, value in coeff.items():
                if value:
                    rr.append(number); cc.append(key); vv.append(value)
            lb.append(a); ub.append(b)
        if safety:
            constraint({y: 1 for y in yvars}, s, s)
            coeff = {y: up[i] for i, y in enumerate(yvars)}
            for a, z in zvars.items():
                i, r = cells[a]
                coeff[z] = -(cap[i]-active[i][r])
                constraint({z: 1, xvars[a]: -1}, b=0)
                constraint({z: 1, yvars[i]: -multiplicities[a]}, b=0)
                constraint({z: 1, xvars[a]: -1, yvars[i]: -multiplicities[a]}, a=-multiplicities[a])
            constraint(coeff, b=budget)
        if exclusion:
            coeff = {tv: p}
            coeff.update({w: -1 for w in wvars})
            constraint(coeff, a=budget+1)
            for i, w in enumerate(wvars):
                coeff = {w: 1, tv: -1}
                coeff.update({xvars[a]: active[i][r] for a, (row, r) in enumerate(cells) if row == i})
                constraint(coeff, a=-low[i])
        matrix = coo_matrix((vv, (rr, cc)), shape=(len(lb), count)).tocsc()
        max_variables = max(max_variables, count)
        max_constraints = max(max_constraints, len(lb))
        result = milp(objective, integrality=integral, bounds=Bounds(lower, upper),
                      constraints=LinearConstraint(matrix, np.array(lb), np.array(ub)),
                      options=dict(mip_rel_gap=0., time_limit=left))
        calls += 1
        dual = getattr(result, 'mip_dual_bound', None)
        bound = max(0, math.ceil(float(dual)-1e-6)) if dual is not None and np.isfinite(dual) else 0
        if result.x is None:
            return dict(value=None, lower_bound=bound, proven=False)
        integers = np.rint(result.x[xvars+yvars]).astype(int)
        query = integers[:len(cells)].tolist()
        kept = integers[len(cells):].tolist() if safety else None
        # Every returned integer solution is checked in the original costs.
        lo = low.copy(); hi = up.copy()
        for (i, r), q, multiple in zip(cells, query, multiplicities):
            assert 0 <= q <= multiple
            lo[i] += q*active[i][r]
            hi[i] -= q*(cap[i]-active[i][r])
        if safety:
            assert sum(kept) == s and sum(a*b for a, b in zip(hi, kept)) <= budget
        if exclusion:
            assert sum(sorted(lo)[:p]) >= budget+1
        value = sum(query)
        assert abs(result.fun-value) < 1e-6
        return dict(value=value, lower_bound=bound, proven=result.status == 0,
                    query=query, safe=kept)

    full = multiplicities.copy()
    true = [sum(row) for row in active]
    safe = [0]*m
    left = budget
    for i in sorted(range(m), key=lambda i: (true[i], i)):
        if true[i] > left:
            break
        safe[i] = 1; left -= true[i]
    best = witness(full, safe)
    targets = list(range(max(0, L-epsilon), L+1))
    joint_bounds = []
    for s in targets:
        result = run(s, 'joint')
        joint_bounds.append(result['lower_bound'])
        if result['value'] is not None and result['value'] < best['queries']:
            best = witness(result['query'], result['safe'])
    joint_proven = min(joint_bounds) >= best['queries']
    split = None
    split_bounds = []
    if separated:
        for s in targets:
            a, b = run(s, 'safety'), run(s, 'exclusion')
            split_bounds.append(a['lower_bound']+b['lower_bound'])
            if a['value'] is not None and b['value'] is not None:
                value = a['value']+b['value']
                split = min(split, value) if split is not None else value
    split_proven = bool(separated and split is not None and min(split_bounds) >= split)
    assert best['V_upper']-best['V_lower'] <= epsilon
    if joint_proven and split_proven:
        assert best['queries'] <= split
    return dict(status=('OPTIMAL_FIXED_THRESHOLD' if fixed_threshold is not None else 'OPTIMAL') if joint_proven and (not separated or split_proven) else 'UNRESOLVED',
                minimum_scope='fixed_threshold' if fixed_threshold is not None else 'global',
                **best, true_optimum=L+free, joint_optimal=joint_proven,
                separated_optimal=split_proven, split_queries=split,
                joint_lower_bound=min(joint_bounds),
                seconds=time.perf_counter()-start, milp_calls=calls,
                max_variables=max_variables, max_constraints=max_constraints)

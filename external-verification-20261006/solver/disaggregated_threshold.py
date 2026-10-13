"""Bounded fixed-threshold MILP and continuous lower-bound screening; threshold decomposition for closure.

Offline integer flip outcomes only. Two branches cover nonautomatic and
automatic exclusion. This changes search representation, not the certificate.
"""
import math
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from joint_certificates import capacity


def certificate(rows, caps, budget, epsilon=0, observed=None, seconds=60,
                presolve=True, entry_variables=False, separated=False, fixed_threshold=None, incumbent=None, relaxation=False, improving_only=False, fixed_target=None):
    start = time.perf_counter()
    rows = [list(map(int, r)) for r in rows]
    caps = list(map(int, caps))
    observed = [0]*len(rows) if observed is None else list(map(int, observed))
    T = len(rows[0]) if rows else 0
    assert len(rows) == len(caps) == len(observed)
    assert budget >= 0 and int(epsilon) == epsilon and epsilon >= 0
    assert all(len(r) == T and 0 <= o < 1 << T and
               all(0 <= v <= p for v in r)
               for r, p, o in zip(rows, caps, observed))
    ids = [i for i, p in enumerate(caps) if p]
    free = len(rows)-len(ids)
    active, cap, obs = [rows[i] for i in ids], [caps[i] for i in ids], [observed[i] for i in ids]
    m = len(ids)
    lo = [sum(v for r, v in enumerate(row) if o >> r & 1) for row, o in zip(active, obs)]
    hi = [v+(T-bin(o).count('1'))*p for v, o, p in zip(lo, obs, cap)]
    L = capacity(list(map(sum, active)), budget)
    groups = []
    for i, row in enumerate(active):
        by = {}
        for r, v in enumerate(row):
            if not obs[i] >> r & 1:
                by.setdefault(r if entry_variables else v, []).append(r)
        groups += [(i, row[rr[0]], rr) for _, rr in sorted(by.items())]
    mult = [len(rr) for i, v, rr in groups]

    def reconstruct(q, exclusion_q=None):
        aq = q
        bq = q if exclusion_q is None else exclusion_q
        q = [max(x, y) for x, y in zip(aq, bq)]
        qm = sum(1 << (ids[i]*T+r) for (i, v, rr), n in zip(groups, q) for r in rr[:n])
        lower, upper = [], []
        for i, (row, p, old) in enumerate(zip(rows, caps, observed)):
            known = old | (qm >> (i*T) & ((1 << T)-1))
            a = sum(v for r, v in enumerate(row) if known >> r & 1)
            lower.append(a); upper.append(a+(T-bin(known).count('1'))*p)
        kept = []; left = budget
        for i in sorted(range(len(rows)), key=lambda i: (upper[i], i)):
            if upper[i] > left: break
            left -= upper[i]; kept.append(i)
        vl, vu = len(kept), capacity(lower, budget)
        assert vu-vl <= epsilon
        assert bin(qm).count('1') == sum(q)
        return dict(queries=sum(q), objective=sum(aq)+sum(bq) if separated else sum(q),
                    query_mask=qm, safe_mask=sum(1 << i for i in kept),
                    V_lower=vl, V_upper=vu, true_optimum=L+free)

    if capacity(lo, budget)-capacity(hi, budget) <= epsilon:
        return dict(status='OPTIMAL', joint_optimal=True, joint_lower_bound=0,
                    **reconstruct([0]*len(groups)), calls=[], seconds=time.perf_counter()-start)
    best = reconstruct(mult) if incumbent is None else {k:incumbent[k] for k in ['queries','objective','query_mask','safe_mask','V_lower','V_upper','true_optimum']}
    cutoff = best['objective']-1 if improving_only else None
    calls = []
    bounds = []
    smin = max(0, L-epsilon)
    branches = []
    if smin <= min(L, m-epsilon-1):
        branches.append(('coupled', smin, min(L, m-epsilon-1)))
    if max(smin, m-epsilon) <= L:
        # Safety-only cost is monotone in its required cardinality.
        branches.append(('automatic', max(smin, m-epsilon), max(smin, m-epsilon)))
    if fixed_target is not None:
        branches=[(name,fixed_target,fixed_target) for name,a,b in branches if a<=fixed_target<=b]
        assert branches, 'target outside the complete branch partition'
    feasible_branches = 0
    for branch, a, b in branches:
        if branch == 'coupled' and fixed_threshold is not None and (b+epsilon+1)*fixed_threshold-sum(max(0,fixed_threshold-sum(row)) for row in active)<budget+1:
            bounds.append((2 if separated else 1)*sum(mult)+1)
            calls.append(dict(branch=branch,status='EXCLUDED_BY_TRUE_COSTS',lower_bound=bounds[-1]))
            continue
        feasible_branches += 1
        remaining = seconds-(time.perf_counter()-start)
        if remaining < .05:
            bounds.append(0); calls.append(dict(branch=branch, status='NOT_RUN', lower_bound=0)); continue
        n = 0
        def alloc(k):
            nonlocal n
            v = list(range(n, n+k)); n += k; return v
        xx = alloc(len(groups))
        ex = alloc(len(groups)) if separated and branch == 'coupled' else xx
        yy = alloc(m)
        zz = {g:alloc(1)[0] for g, (i, v, rr) in enumerate(groups) if cap[i] > v}
        ww = alloc(m) if branch == 'coupled' else []
        tt = alloc(1)[0] if branch == 'coupled' else None
        bit_weights = [1 << j for j in range((b-a).bit_length())] if fixed_threshold is None else []
        bb = alloc(len(bit_weights))
        products = alloc(len(bb))
        obj, integ, lower, upper = np.zeros(n), np.zeros(n), np.zeros(n), np.ones(n)
        obj[xx] = 1; obj[ex] = 1
        integ[xx+ex+yy+bb] = 1; upper[xx] = mult; upper[ex] = mult
        for g, z in zz.items(): upper[z] = mult[g]
        tmax = max(map(sum, active), default=0)
        if tt is not None:
            integ[tt] = 1; upper[ww+[tt]+products] = tmax
            if fixed_threshold is not None: lower[tt] = upper[tt] = fixed_threshold
        ri, ci, vv, lbs, ubs = [], [], [], [], []
        def con(coef, lb=-np.inf, ub=np.inf):
            k = len(lbs)
            for c, v in coef.items():
                if v: ri.append(k); ci.append(c); vv.append(v)
            lbs.append(lb); ubs.append(ub)
        coef = {y:1 for y in yy}; coef.update({v:-w for v, w in zip(bb, bit_weights)})
        con(coef, a, a if fixed_threshold is None else b)
        if bb: con({v:w for v, w in zip(bb, bit_weights)}, ub=b-a)
        coef = {y:hi[i] for i, y in enumerate(yy)}
        for g, z in zz.items():
            i, v, rr = groups[g]; coef[z] = -(cap[i]-v)
            con({z:1, xx[g]:-1}, ub=0)
            con({z:1, yy[i]:-mult[g]}, ub=0)
            con({z:1, xx[g]:-1, yy[i]:-mult[g]}, lb=-mult[g])
        con(coef, ub=budget)
        if tt is not None:
            for bit, prod in zip(bb, products):
                con({prod:1, tt:-1}, ub=0)
                con({prod:1, bit:-tmax}, ub=0)
                con({prod:1, tt:-1, bit:-tmax}, lb=-tmax)
            coef = {tt:a+epsilon+1}
            if fixed_threshold is not None:
                coef = {tt:epsilon+1}; coef.update({y:fixed_threshold for y in yy})
            coef.update({v:w for v, w in zip(products, bit_weights)})
            coef.update({v:-1 for v in ww})
            con(coef, lb=budget+1)
            for i, w in enumerate(ww):
                coef = {w:1, tt:-1}
                coef.update({ex[g]:v for g, (j, v, rr) in enumerate(groups) if j == i})
                con(coef, lb=-lo[i])
        if cutoff is not None: con({j:v for j,v in enumerate(obj) if v}, ub=cutoff)
        if relaxation: integ[:]=0
        matrix = coo_matrix((vv, (ri, ci)), shape=(len(lbs), n)).tocsc()
        res = milp(obj, integrality=integ, bounds=Bounds(lower, upper),
                   constraints=LinearConstraint(matrix, np.asarray(lbs), np.asarray(ubs)),
                   options=dict(time_limit=remaining, mip_rel_gap=0., presolve=presolve))
        dual = getattr(res, 'mip_dual_bound', None)
        bound = max(0, math.ceil(float(dual)-1e-6)) if dual is not None and np.isfinite(dual) else 0
        if relaxation and res.status == 0: bound=max(0,math.ceil(float(res.fun)-1e-6))
        if res.status == 2: bound = cutoff+1 if cutoff is not None else 0
        meta = dict(branch=branch, min_target=a, max_target=b, status=int(res.status),
                    lower_bound=bound, variables=n, constraints=len(lbs), message=res.message)
        if res.x is not None and not relaxation:
            q = np.rint(res.x[xx]).astype(int).tolist()
            assert all(0 <= v <= c for v, c in zip(q, mult))
            bq = np.rint(res.x[ex]).astype(int).tolist() if separated and branch == 'coupled' else None
            if separated and branch == 'automatic': bq = [0]*len(groups)
            safety_hi = hi.copy(); exclusion_lo = lo.copy()
            for g, (i, v, rr) in enumerate(groups):
                safety_hi[i] -= q[g]*(cap[i]-v)
                exclusion_lo[i] += (q[g] if bq is None else bq[g])*v
            target = sum(int(round(res.x[y])) for y in yy)
            assert a <= target <= b and capacity(safety_hi, budget) >= target
            if branch == 'coupled': assert capacity(exclusion_lo, budget) <= target+epsilon
            candidate = reconstruct(q, bq)
            assert abs(candidate['objective']-res.fun) < 1e-5
            meta['value'] = candidate['objective']
            if candidate['objective'] < best['objective']: best = candidate
        calls.append(meta); bounds.append(bound)
    bounds = [min(b,best['objective']) for b in bounds]
    proven = feasible_branches > 0 and min(bounds) >= best['objective']
    return dict(status='OPTIMAL' if proven else 'UNRESOLVED', joint_optimal=proven,
                joint_lower_bound=min(bounds), **best, calls=calls,
                seconds=time.perf_counter()-start, presolve=presolve,
                entry_variables=entry_variables, separated_objective=separated, fixed_threshold=fixed_threshold, fixed_target=fixed_target, relaxation=relaxation, improving_only=improving_only)

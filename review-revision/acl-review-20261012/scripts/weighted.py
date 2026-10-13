"""Joint versus separate evidence under nonuniform replacement weights.

Scenario weights w_{jr} = w_r / (M W), W = sum_r w_r, with integer candidate
weights w_r drawn uniformly from {1,2,3} (seeded per instance). The weighted
risk is sum_i sum_r w_r f_ir / (2 k M W); the integer budget is
floor(2 k alpha M W). Entry (i, r) has lower contribution w_r f_ir and upper
contribution w_r p_i when unqueried, so caps are candidate specific. The MILP
generalizes the compact entry formulation (outcome groups keyed by the pair of
contributions) with the same order-threshold exclusion constraint. Empty
history; exact and primary tolerances; original 960 mean instances.
"""
import json
import math
import multiprocessing
import sys
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from common import EXP, PANELS, QS, SPLITS, instance, capacity

LIMIT = 60.0


def solve(g, a, budget, s, eps, mode, seconds):
    """Min entries for safe count s and exclusion of s+eps+1 (mode joint/safety/exclusion).

    g, a: (m, T) integer lower/upper contributions. Returns dict with value,
    lower bound, query counts per group and safe vector.
    """
    m, T = g.shape
    up0 = a.sum(axis=1)
    cells, mult = [], []
    for i in range(m):
        seen = {}
        for r in range(T):
            seen.setdefault((int(g[i, r]), int(a[i, r])), []).append(r)
        for key, rs in sorted(seen.items()):
            cells.append((i, key[0], key[1])); mult.append(len(rs))
    p = s + eps + 1
    exclusion = mode != 'safety' and p <= m
    safety = mode != 'exclusion'
    if not safety and not exclusion:
        return dict(value=0, bound=0, proven=True, x=[0] * len(cells), y=None, cells=cells)
    n = len(cells)
    xv = list(range(n)); cnt = n
    yv = list(range(cnt, cnt + m)) if safety else []; cnt += len(yv)
    zv = {}
    if safety:
        for c, (i, gi, ai) in enumerate(cells):
            if ai > gi:
                zv[c] = cnt; cnt += 1
    wv = list(range(cnt, cnt + m)) if exclusion else []; cnt += len(wv)
    tv = cnt if exclusion else None; cnt += int(exclusion)
    obj = np.zeros(cnt); obj[xv] = 1
    integ = np.zeros(cnt); integ[xv + yv] = 1
    lo = np.zeros(cnt); hi = np.ones(cnt); hi[xv] = mult
    for c, z in zv.items():
        hi[z] = mult[c]
    if exclusion:
        integ[tv] = 1; hi[wv] = a.sum(axis=1).max(); hi[tv] = a.sum(axis=1).max()
    R, C, V, LB, UB = [], [], [], [], []

    def con(coef, l=-np.inf, u=np.inf):
        k = len(LB)
        for key, val in coef.items():
            if val:
                R.append(k); C.append(key); V.append(val)
        LB.append(l); UB.append(u)
    if safety:
        con({y: 1 for y in yv}, s, s)
        coef = {y: float(up0[i]) for i, y in enumerate(yv)}
        for c, z in zv.items():
            i, gi, ai = cells[c]
            coef[z] = -(ai - gi)
            con({z: 1, xv[c]: -1}, u=0)
            con({z: 1, yv[i]: -mult[c]}, u=0)
            con({z: 1, xv[c]: -1, yv[i]: -mult[c]}, l=-mult[c])
        con(coef, u=budget)
    if exclusion:
        coef = {tv: p}; coef.update({w: -1 for w in wv})
        con(coef, l=budget + 1)
        for i, w in enumerate(wv):
            coef = {w: 1, tv: -1}
            coef.update({xv[c]: cells[c][1] for c in range(n) if cells[c][0] == i})
            con(coef, l=0)
    A = coo_matrix((V, (R, C)), shape=(len(LB), cnt)).tocsc()
    res = milp(obj, integrality=integ, bounds=Bounds(lo, hi),
               constraints=LinearConstraint(A, np.array(LB), np.array(UB)),
               options=dict(mip_rel_gap=0., time_limit=seconds, presolve=False))
    dual = getattr(res, 'mip_dual_bound', None)
    bound = max(0, math.ceil(float(dual) - 1e-6)) if dual is not None and np.isfinite(dual) else 0
    if res.x is None:
        return dict(value=None, bound=bound, proven=False, cells=cells)
    x = np.rint(res.x[xv]).astype(int)
    y = np.rint(res.x[yv]).astype(int) if safety else None
    low = np.zeros(m); upp = up0.astype(float).copy()
    for c, (i, gi, ai) in enumerate(cells):
        low[i] += x[c] * gi; upp[i] -= x[c] * (ai - gi)
    if safety:
        assert y.sum() == s and (upp * y).sum() <= budget
    if exclusion:
        assert np.sort(low)[:p].sum() >= budget + 1
    value = int(x.sum())
    return dict(value=value, bound=max(bound, 0), proven=res.status == 0, x=x.tolist(),
                y=None if y is None else y.tolist(), cells=cells)


def union_min(g, a, budget, s, eps, qs, qe, seconds):
    """Min |X_S u X_E| over safety witnesses of size qs and exclusion witnesses of size qe."""
    m, T = g.shape
    up0 = a.sum(axis=1)
    p = s + eps + 1
    E = [(i, r) for i in range(m) for r in range(T)]
    n = len(E)
    # variables: xs (n), xe (n), u (n), y (m), zs (n) [xs*y], w (m), t
    xs = np.arange(n); xe = n + xs; u = 2 * n + xs; yv = 3 * n + np.arange(m)
    zs = 3 * n + m + xs; wv = 4 * n + m + np.arange(m); tv = 4 * n + 2 * m
    cnt = tv + 1
    obj = np.zeros(cnt); obj[u] = 1
    integ = np.zeros(cnt); integ[np.r_[xs, xe, u, yv, tv]] = 1
    lo = np.zeros(cnt); hi = np.ones(cnt)
    hi[wv] = up0.max(); hi[tv] = up0.max()
    R, C, V, LB, UB = [], [], [], [], []

    def con(coef, l=-np.inf, uu=np.inf):
        k = len(LB)
        for key, val in coef:
            R.append(k); C.append(int(key)); V.append(val)
        LB.append(l); UB.append(uu)
    con([(x, 1) for x in xs], qs, qs)
    con([(x, 1) for x in xe], qe, qe)
    for c in range(n):
        con([(u[c], 1), (xs[c], -1)], l=0)
        con([(u[c], 1), (xe[c], -1)], l=0)
    con([(y, 1) for y in yv], s, s)
    coef = [(yv[i], float(up0[i])) for i in range(m)]
    for c, (i, r) in enumerate(E):
        red = a[i, r] - g[i, r]
        if red:
            coef.append((zs[c], -float(red)))
        con([(zs[c], 1), (xs[c], -1)], uu=0)
        con([(zs[c], 1), (yv[i], -1)], uu=0)
        con([(zs[c], 1), (xs[c], -1), (yv[i], -1)], l=-1)
    con(coef, uu=budget)
    if p <= m:
        con([(tv, p)] + [(w, -1) for w in wv], l=budget + 1)
        for i in range(m):
            con([(wv[i], 1), (tv, -1)] + [(xe[i * T + r], float(g[i, r])) for r in range(T) if g[i, r]], l=0)
    else:
        assert qe == 0
    A = coo_matrix((V, (R, C)), shape=(len(LB), cnt)).tocsc()
    res = milp(obj, integrality=integ, bounds=Bounds(lo, hi),
               constraints=LinearConstraint(A, np.array(LB), np.array(UB)),
               options=dict(mip_rel_gap=0., time_limit=seconds, presolve=False))
    dual = getattr(res, 'mip_dual_bound', None)
    bound = max(0, math.ceil(float(dual) - 1e-6)) if dual is not None and np.isfinite(dual) else 0
    value = int(round(res.fun)) if res.x is not None else None
    return dict(value=value, bound=bound, proven=res.status == 0)


def certify(g, a, budget, eps, seconds=LIMIT):
    m = g.shape[0]
    L = capacity(g.sum(axis=1), budget)
    targets = list(range(max(0, L - eps), L + 1))
    out = dict(L=int(L), m=int(m))
    if L + eps >= m:
        # Exclusion is automatic for the largest admissible target: union = split = joint
        # is not guaranteed in general, so still solve all three objectives.
        pass
    joint, jb, sep, sb, comps = None, [], None, [], {}
    for s in targets:
        r = solve(g, a, budget, s, eps, 'joint', seconds)
        jb.append(r['bound'] if not r['proven'] else r['value'])
        if r['value'] is not None:
            joint = r['value'] if joint is None else min(joint, r['value'])
        A_ = solve(g, a, budget, s, eps, 'safety', seconds)
        B_ = solve(g, a, budget, s, eps, 'exclusion', seconds)
        sb.append((A_['value'] if A_['proven'] else A_['bound']) + (B_['value'] if B_['proven'] else B_['bound']))
        if A_['value'] is not None and B_['value'] is not None:
            comps[s] = (A_['value'], B_['value'], A_['proven'] and B_['proven'])
            v = A_['value'] + B_['value']
            sep = v if sep is None else min(sep, v)
    out.update(joint=joint, joint_proven=joint is not None and min(jb) >= joint,
               split=sep, split_proven=sep is not None and min(sb) >= sep)
    union, ub = None, []
    if out['joint_proven'] and out['split_proven']:
        if joint == sep:
            union, ub = joint, [joint]
        else:
            for s, (qs, qe, ok) in comps.items():
                if not ok:
                    ub.append(0); continue
                r = union_min(g, a, budget, s, eps, qs, qe, 2 * seconds)
                ub.append(r['value'] if r['proven'] else r['bound'])
                if r['value'] is not None:
                    union = r['value'] if union is None else min(union, r['value'])
    out.update(union=union, union_proven=union is not None and len(ub) == len(targets) and min(ub) >= union)
    return out


def task(key):
    panel, rep, q = key
    t0 = time.monotonic()
    c = instance(panel, 'mean', rep, q)
    T, m, S, free = c['T'], c['m'], c['S'], c['free']
    rng = np.random.default_rng(31012027 + 1000 * PANELS.index(panel) + 10 * rep + int(round(100 * q)))
    w = rng.integers(1, 4, size=T)
    W = int(w.sum())
    budget = (2 * c['k'] * 7 * W) // 10
    g = (c['truth'] * w[None, :]).astype(np.int64)
    a = (c['lp'][:, None] * w[None, :]).astype(np.int64)
    Lw = capacity(g.sum(axis=1), budget)
    Lu = capacity(c['truth'].sum(axis=1), c['budget'])
    rec = dict(dataset=panel, split=rep, q=q, weights=w.tolist(), budget=int(budget), selected=int(S),
               active=int(m), free=int(free), V_star_weighted=int(free + Lw), V_star_uniform=int(free + Lu))
    for stop, eps in [('exact', 0), ('primary', c['epsilon'])]:
        if Lw + eps >= m and Lw == m:
            # Full retention: optimistic count stays |S0|; safety alone certifies.
            rec[stop] = dict(full_retention=True)
            continue
        rec[stop] = dict(full_retention=False, **certify(g, a, budget, eps))
    rec['seconds'] = time.monotonic() - t0
    return rec


def main():
    out = EXP / 'outputs' / 'weighted_records.jsonl'
    done = set()
    if out.exists():
        for line in out.open():
            x = json.loads(line); done.add((x['dataset'], x['split'], x['q']))
    keys = [(p, s, q) for q in QS for p in PANELS for s in SPLITS if (p, s, q) not in done]
    print('tasks', len(keys), flush=True)
    with out.open('a') as f, multiprocessing.get_context('spawn').Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as pool:
        for i, rec in enumerate(pool.imap_unordered(task, keys)):
            f.write(json.dumps(rec) + '\n'); f.flush()
            if i % 20 == 0:
                print(i, rec['dataset'], rec['q'], round(rec['seconds'], 1), flush=True)


if __name__ == '__main__':
    main()

"""Per-replacement (worst-scenario) churn certification on the original grid.

Target: every declared replacement j->r individually satisfies churn <= alpha,
i.e. committed membership flips <= beta = floor(2 k alpha) in each scenario.
Unobserved selected-row entries take score 0 for the upper bound (every
scenario flip attained by one completion) and score 1 for the lower bound.
Retained-count capacity under H scenario budgets is an integer program; we
solve it with HiGHS. Acquisition reuses the budget-independent reference
priority path, so the average and per-replacement stops are compared on the
same query sequence.
"""
import json
import multiprocessing
import sys
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import csr_matrix
from common import (EXP, PANELS, QS, SPLITS, instance, flip_matrix,
                    reference_path, first_stop, capacity)

LIMIT = 120.0


def max_capacity(A, beta, limit=LIMIT):
    """A: (n, S) 0/1 scenario flips of candidate rows. Max |C| s.t. A^T y <= beta.

    Returns (primal, dual_bound, proven). Rows with no scenario flip are free.
    """
    n = A.shape[0]
    if n == 0:
        return 0, 0, True
    load = A.sum(axis=1)
    free = int((load == 0).sum())
    A = A[load > 0]
    A = A[:, A.any(axis=0)]
    if A.shape[0] == 0:
        return free, free, True
    # Greedy cheap check: everything fits.
    if (A.sum(axis=0) <= beta).all():
        return free + A.shape[0], free + A.shape[0], True
    k = A.shape[0]
    res = milp(-np.ones(k), integrality=np.ones(k), bounds=Bounds(0, 1),
               constraints=LinearConstraint(csr_matrix(A.T.astype(float)), -np.inf, beta),
               options=dict(mip_rel_gap=0., time_limit=limit, presolve=False))
    if res.x is None:
        return free, free + k, False
    y = np.rint(res.x).astype(int)
    assert (A.T @ y <= beta).all()
    primal = int(y.sum())
    dual = getattr(res, 'mip_dual_bound', None)
    ub = int(np.floor(-dual + 1e-6)) if dual is not None and np.isfinite(dual) else k
    ub = max(primal, min(k, ub))
    return free + primal, free + ub, res.status == 0 and ub == primal


def task(key):
    panel, agg, rep, q = key
    t0 = time.monotonic()
    c = instance(panel, agg, rep, q)
    ids, m, T, M = c['ids'], c['m'], c['T'], 7
    base = c['base'][:, ids]
    hidden = c['hidden'][:, ids]
    beta = (2 * c['k']) // 10
    eps = c['epsilon']
    # phi[i, j, r]: replacing j by r flips active row i; pi[i, j]: endpoint flip.
    phi = np.stack([flip_matrix(base, hidden[r], c['cutoff'], agg) for r in range(T)], axis=2) if m else np.zeros((0, M, T), bool)
    pi = flip_matrix(base, np.zeros(m), c['cutoff'], agg) if m else np.zeros((0, M), bool)
    assert np.array_equal(phi.sum(axis=1), c['truth'].astype(int)) if m else True
    assert (phi <= pi[:, :, None]).all()
    path = reference_path(c)
    unresolved = [0]

    def bounds_at(t):
        known = np.zeros((m, T), bool)
        for i, r in path[:t]:
            known[i, r] = True
        up = np.where(known[:, None, :], phi, pi[:, :, None]).reshape(m, M * T)
        lo = np.where(known[:, None, :], phi, False).reshape(m, M * T)
        vlo, _, p1 = max_capacity(up, beta)
        _, vhi, p2 = max_capacity(lo, beta)
        unresolved[0] += (not p1) + (not p2)
        return c['free'] + vlo, c['free'] + vhi

    cache = {}

    def gap(t):
        if t not in cache:
            cache[t] = bounds_at(t)
        return cache[t][1] - cache[t][0]

    full_lo, full_hi, full_proven = max_capacity(phi.reshape(m, M * T), beta)
    vstar_max = c['free'] + full_lo
    n = len(path)
    stops = {}
    for name, e in [('exact', 0), ('primary', eps)]:
        t = first_stop(n, gap, e)
        stops[name] = dict(queries=t, V_lower=cache.get(t, bounds_at(t))[0])
    # Average-budget reference on the same path.
    def avg_gap(t):
        low = np.zeros(m, np.int64); up = T * c['lp'].copy()
        for i, r in path[:t]:
            f = c['truth'][i, r]; low[i] += f; up[i] -= c['lp'][i] - f
        return capacity(low, c['budget']) - capacity(up, c['budget']), c['free'] + capacity(up, c['budget'])
    avg = {}
    for name, e in [('exact', 0), ('primary', eps)]:
        t = first_stop(n, lambda s: avg_gap(s)[0], e)
        avg[name] = dict(queries=t, V_lower=avg_gap(t)[1])
    vstar_avg = c['free'] + capacity(c['truth'].sum(axis=1), c['budget'])
    zero = cache.get(0) or bounds_at(0)
    return dict(dataset=panel, aggregator=agg, split=rep, q=q, N=int(c['N']), T=int(T), k=int(c['k']),
                beta=int(beta), avg_budget=int(c['budget']), selected=int(c['S']), active=int(m),
                epsilon=int(eps), V_star_avg=int(vstar_avg), V_star_max=int(vstar_max),
                V_star_max_upper=int(c['free'] + full_hi), V_star_max_proven=bool(full_proven),
                zero_safe_avg=int(c['free'] + capacity(T * c['lp'], c['budget'])),
                zero_safe_max=int(zero[0]),
                avg_primary_queries=avg['primary']['queries'], avg_exact_queries=avg['exact']['queries'],
                avg_primary_returned=int(avg['primary']['V_lower']),
                max_primary_queries=stops['primary']['queries'], max_exact_queries=stops['exact']['queries'],
                max_primary_returned=int(stops['primary']['V_lower']),
                active_entries=int(m * T), unresolved_milps=int(unresolved[0]),
                seconds=time.monotonic() - t0)


def main():
    qs = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else QS
    out = EXP / 'outputs' / 'per_replacement_records.jsonl'
    done = set()
    if out.exists():
        for line in out.open():
            x = json.loads(line); done.add((x['dataset'], x['aggregator'], x['split'], x['q']))
    keys = [(p, a, s, q) for q in qs for p in PANELS for a in ['median', 'mean'] for s in SPLITS
            if (p, a, s, q) not in done]
    print('tasks', len(keys), flush=True)
    with out.open('a') as f, multiprocessing.get_context('spawn').Pool(5) as pool:
        for i, rec in enumerate(pool.imap_unordered(task, keys)):
            f.write(json.dumps(rec) + '\n'); f.flush()
            if i % 40 == 0:
                print(i, rec['dataset'], rec['aggregator'], rec['q'], round(rec['seconds'], 1), flush=True)


if __name__ == '__main__':
    main()

"""Exhaustive checks of the new solvers on small random instances.

1. weighted.certify (joint, split, union) against enumeration of every entry subset.
2. per_replacement.max_capacity against enumeration of every row subset.
"""
import itertools
import random
import sys
import numpy as np
from weighted import certify
from per_replacement import max_capacity


def lowup(g, a, X):
    m, T = g.shape
    lo = np.zeros(m); up = a.sum(axis=1).astype(float)
    for (i, r) in X:
        lo[i] += g[i, r]; up[i] -= a[i, r] - g[i, r]
    return lo, up


def safe_ok(up, s, B):
    return s == 0 or np.sort(up)[:s].sum() <= B


def excl_ok(lo, p, B, m):
    return p > m or np.sort(lo)[:p].sum() >= B + 1


def brute(g, a, B, eps):
    m, T = g.shape
    L = 0
    tot = g.sum(axis=1)
    c = np.sort(tot); L = int(np.searchsorted(np.cumsum(c), B + 1e-9, side='right'))
    cells = [(i, r) for i in range(m) for r in range(T)]
    subsets = [frozenset(X) for k in range(len(cells) + 1) for X in itertools.combinations(cells, k)]
    info = [(X,) + lowup(g, a, X) for X in subsets]
    joint, split, union = None, None, None
    for s in range(max(0, L - eps), L + 1):
        p = s + eps + 1
        S = [X for X, lo, up in info if safe_ok(up, s, B)]
        E = [X for X, lo, up in info if excl_ok(lo, p, B, m)]
        J = [X for X, lo, up in info if safe_ok(up, s, B) and excl_ok(lo, p, B, m)]
        js = min(map(len, J)); ss = min(map(len, S)); es = min(map(len, E))
        Smin = [X for X in S if len(X) == ss]; Emin = [X for X in E if len(X) == es]
        us = min(len(x | y) for x in Smin for y in Emin)
        joint = js if joint is None else min(joint, js)
        split = ss + es if split is None else min(split, ss + es)
        union = us if union is None else min(union, us)
    return joint, split, union


def main():
    rng = random.Random(7)
    bad = 0; n = 0; gains = 0
    while n < 1500:
        m, T = rng.choice([(2, 2), (2, 3), (3, 2), (3, 3), (2, 4)])
        caps = [rng.randint(1, 4) for _ in range(m)]
        w = [rng.randint(1, 3) for _ in range(T)]
        f = np.array([[rng.randint(0, caps[i]) for _ in range(T)] for i in range(m)])
        g = f * np.array(w)[None, :]
        a = np.array(caps)[:, None] * np.array(w)[None, :]
        B = rng.randint(0, int(a.sum()))
        eps = rng.choice([0, 0, 1])
        L = int(np.searchsorted(np.cumsum(np.sort(g.sum(axis=1))), B + 1e-9, side='right'))
        if L == m:
            continue
        bj, bs, bu = brute(g, a, B, eps)
        r = certify(g.astype(np.int64), a.astype(np.int64), B, eps, seconds=30)
        u = r['union'] if r['union'] is not None else (r['joint'] if r['joint'] == r['split'] else None)
        n += 1; gains += bu > bj
        if (r['joint'], r['split'], u) != (bj, bs, bu) or not r['joint_proven']:
            bad += 1; print('MISMATCH', f.tolist(), w, caps, B, eps, (bj, bs, bu), r)
    print('weighted certify: instances', n, 'mismatches', bad, 'brute strict gains', gains)
    # per-replacement capacity
    bad2 = 0
    for t in range(3000):
        k = rng.randint(1, 8); S = rng.randint(1, 6); beta = rng.randint(0, 3)
        A = np.array([[rng.random() < .4 for _ in range(S)] for _ in range(k)])
        best = max(len(C) for n_ in range(k + 1) for C in itertools.combinations(range(k), n_)
                   if (A[list(C)].sum(axis=0) <= beta).all()) if k else 0
        lo, hi, ok = max_capacity(A, beta)
        if lo != best or hi != best or not ok:
            bad2 += 1; print('CAP MISMATCH', A.astype(int).tolist(), beta, best, lo, hi)
    print('per-replacement capacity: instances 3000 mismatches', bad2)
    sys.exit(1 if bad or bad2 else 0)


if __name__ == '__main__':
    main()

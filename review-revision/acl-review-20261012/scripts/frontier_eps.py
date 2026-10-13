"""Tolerance-aware frontier priority: exclusion target s+eps+1 instead of s+1.

Identical to scripts/frontier_priority.py (joint mode) except that the exclusion
deficit targets p = s + eps + 1 rows, matching the stopping condition of
Theorem joint. Only the primary stop differs (eps = 0 reproduces the original).
Results are compared on the same 960 mean instances with the saved records.
"""
import os
for k in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']: os.environ[k] = '1'
import json, math, multiprocessing, sys, time
from pathlib import Path
import numpy as np
from numba import njit
EXP = Path(__file__).resolve().parents[1]
ROOT = EXP.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from frontier_priority import cap_hist


@njit(cache=True)
def choose_eps(caps, predicted, known, lower, upper, lh, uh, budget, eps):
    m, T = predicted.shape
    vl, vh = cap_hist(uh, budget), cap_hist(lh, budget)
    estimate = lower * 1000000000000
    for i in range(m):
        for r in range(T):
            if not known[i, r]: estimate[i] += predicted[i, r]
    order = np.argsort(estimate, kind='mergesort')
    total = 0; guess = 0
    for i in order:
        if total + estimate[i] > budget * 1000000000000: break
        total += estimate[i]; guess += 1
    target = min(vh, max(vl + 1, guess))
    safe = np.zeros(m, np.bool_); need_s = -budget
    for j in range(target): safe[order[j]] = True; need_s += upper[order[j]]
    threshold = 0; need_e = 0
    p = target + eps + 1
    if p <= m:
        threshold = (estimate[order[p - 1]] + 999999999999) // 1000000000000
        need_e = budget + 1 - p * threshold
        for i in range(m): need_e += max(0, threshold - lower[i])
    best = -1; bi = -1; br = -1
    for i in range(m):
        for r in range(T):
            if known[i, r]: continue
            f = predicted[i, r] / 1000000000000.0; score = 0.
            if safe[i] and need_s > 0: score += (caps[i] - f) / need_s
            if need_e > 0: score += min(f, max(0, threshold - lower[i])) / need_e
            tick = int(np.rint(score * 1000000000000.0))
            if tick > best: best = tick; bi = i; br = r
    if best <= 0:
        width = -1
        for i in range(m):
            if upper[i] - lower[i] > width:
                for r in range(T):
                    if not known[i, r]: width = upper[i] - lower[i]; bi = i; br = r; break
    return bi, br


def acquire_eps(caps, prior, budget, epsilon, query):
    caps = np.asarray(caps, np.int64); prior = np.asarray(prior, float)
    m, T = prior.shape
    predicted = np.rint(np.clip(prior, 0, caps[:, None]) * 10**12).astype(np.int64)
    known = np.zeros((m, T), bool); lower = np.zeros(m, np.int64); upper = T * caps.copy()
    lh = np.zeros(int(T * max(caps, default=0)) + 1, np.int64); uh = lh.copy(); lh[0] = m
    for v in upper: uh[v] += 1
    n = 0
    while True:
        vl, vh = int(cap_hist(uh, budget)), int(cap_hist(lh, budget))
        if vh - vl <= epsilon: return n, vl
        i, r = map(int, choose_eps(caps, predicted, known, lower, upper, lh, uh, budget, epsilon))
        f = int(query(i, r))
        lh[lower[i]] -= 1; uh[upper[i]] -= 1
        lower[i] += f; upper[i] -= caps[i] - f
        lh[lower[i]] += 1; uh[upper[i]] += 1; known[i, r] = True; n += 1


def task(key):
    from analyze_acquisition_mechanisms import prepare
    panel, rep, q = key; c = prepare((panel, 'mean', rep, q))
    ids = c['ids']; ids = ids[np.argsort(c['tie'][ids])]
    truth = c['f'][:, ids].T; prior = c['prior'][ids]; caps = c['p'][ids]
    eps = math.ceil(.02 * c['S']); t0 = time.monotonic()
    nq, vl = acquire_eps(caps, prior, c['budget'], eps, lambda i, r: int(truth[i, r]))
    return dict(dataset=panel, split=rep, q=q, epsilon=eps, queries=nq,
                V_lower=vl + c['S'] - len(ids), seconds=round(time.monotonic() - t0, 2))


if __name__ == '__main__':
    out = EXP / 'outputs' / 'frontier_eps_primary.jsonl'
    done = set()
    if out.exists():
        done = {(r['dataset'], r['split'], r['q']) for r in map(json.loads, out.read_text().splitlines())}
    PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref', 'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']
    keys = [(p, s, q) for s in range(40) for q in [.05, .10, .20, .30] for p in PANELS if (p, s, q) not in done]
    with out.open('a') as f, multiprocessing.get_context('spawn').Pool(10) as pool:
        for x in pool.imap_unordered(task, keys):
            f.write(json.dumps(x) + '\n'); f.flush()

"""Odd-median minimum certificates under oracle deviation caps.

A deviation cap |s_r(i) - c_P(i)| <= D_r confines each unqueried candidate score
to [max(0, c-D_r), min(1, c+D_r)]. For odd medians, an entry whose range lies
below the cutoff is a fixed opposition and one whose range lies at or above it
is a fixed agreement; every other entry keeps both outcomes. Fixed entries act
as free history, so the residual witness of Appendix M.4 gives the minimum
certificate. D_r is the smallest cap valid on the hidden active rows (oracle).
"""
import json
import math
import multiprocessing
import sys
import time
import numpy as np
from common import EXP, ROOT, PANELS, QS, SPLITS, instance, aggregate
sys.path.insert(0, str(ROOT / 'scripts'))
from residual_certificates import residual_gap_certificate


def task(key):
    panel, rep, q = key
    c = instance(panel, 'median', rep, q)
    m, T = c['m'], c['T']
    rec = dict(dataset=panel, split=rep, q=q, active=int(m), T=int(T), selected=int(c['S']), epsilon=int(c['epsilon']))
    if m == 0:
        rec.update(free=0, fixed=0, **{f'{s}_{v}': 0 for s in ['exact', 'primary'] for v in ['none', 'dev']})
        return rec
    ids = c['ids']
    base = c['base'][:, ids]
    S = c['hidden'][:, ids]
    cons = aggregate(base, 'median')
    cut = c['cutoff']
    bits = (c['truth'] // 4).astype(np.int64)
    assert np.array_equal(bits * 4, c['truth'])
    # bits[i, r] = 1 when candidate r opposes row i (score below cutoff)
    assert np.array_equal(bits, (S.T < cut).astype(np.int64))
    D = np.abs(S - cons[None, :]).max(axis=1)
    lo = np.clip(cons[None, :] - D[:, None], 0, 1).T
    hi = np.clip(cons[None, :] + D[:, None], 0, 1).T
    fixed = (hi < cut) | (lo >= cut)
    assert np.array_equal(bits[(hi < cut)], np.ones(int((hi < cut).sum()), dtype=np.int64))
    b = c['budget'] // 4
    none = np.zeros_like(fixed)
    rec.update(fixed=int(fixed.sum()), entries=int(m * T))
    from fractions import Fraction
    for stop, eps, tau in [('exact', 0, Fraction(0)), ('primary', c['epsilon'], Fraction(1, 50))]:
        if c['witnesses'][tau] == 0:
            # Fixed entries act as free history, so the capped minimum cannot exceed zero.
            rec[f'{stop}_none'] = rec[f'{stop}_dev'] = 0
            continue
        q0 = residual_gap_certificate(bits, none, b, eps)['queries']
        q1 = residual_gap_certificate(bits, fixed, b, eps)['queries']
        rec[f'{stop}_none'] = int(q0)
        rec[f'{stop}_dev'] = int(q1)
    # The empty-history witness must reproduce the recorded closed form.
    from fractions import Fraction
    assert rec['exact_none'] == c['witnesses'][Fraction(0)], (key, rec['exact_none'], c['witnesses'][Fraction(0)])
    assert rec['primary_none'] == c['witnesses'][Fraction(1, 50)], key
    return rec


def main():
    out = EXP / 'outputs' / 'median_deviation_minima.jsonl'
    done = set()
    if out.exists():
        done = {(r['dataset'], r['split'], r['q']) for r in map(json.loads, out.read_text().splitlines())}
    keys = [(p, s, q) for q in QS for p in PANELS for s in SPLITS if (p, s, q) not in done]
    t0 = time.monotonic()
    with out.open('a') as f, multiprocessing.get_context('spawn').Pool(6) as pool:
        for i, rec in enumerate(pool.imap_unordered(task, keys)):
            f.write(json.dumps(rec) + '\n'); f.flush()
    print('done', round(time.monotonic() - t0, 1), flush=True)


if __name__ == '__main__':
    main()

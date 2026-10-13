"""Closed-form-guided acquisition for odd median pools (M = 7, h = 3).

Every active selected row is a boundary row; a candidate entry is either an
agreement (reduces the upper opposition count) or an opposition (raises the
lower count). Theorem 1 and Corollary 1 say a minimum gap witness consists of
agreements inside a safe target set and oppositions capped at a common level
t across rows. The policy plugs reference-ridge opposition probabilities into
that structure: it chooses the safe count s minimizing the predicted witness
cost, then queries the entry with the largest predicted fractional progress
(agreement probability / safety deficit inside the target set; opposition
probability / exclusion deficit in rows below the predicted cap). Predictions
only order queries; stopping uses the unchanged certificate bounds. The policy
is tolerance aware, so primary and exact stops use separate paths.
"""
import json
import math
import multiprocessing
import time
from fractions import Fraction
import numpy as np
from common import EXP, PANELS, QS, SPLITS, instance, capacity


def frac_capacity(cost, budget):
    c = np.sort(cost)
    return int(np.searchsorted(np.cumsum(c), budget + 1e-9, side='right'))


def policy_path(c, eps):
    m, T = c['m'], c['T']
    if m == 0:
        return 0
    z = (c['truth'] // 4).astype(np.int64)
    assert np.array_equal(z * 4, c['truth'])
    b = c['budget'] // 4
    pi = np.clip(c['pred'] / 4.0, 0, 1)
    tie = c['tie'][c['ids']].astype(float)
    known = np.zeros((m, T), bool)
    o = np.zeros(m, np.int64)
    a = np.zeros(m, np.int64)
    q = 0
    while True:
        up = T - a
        vlo, vhi = capacity(up, b), capacity(o, b)
        if vhi - vlo <= eps:
            return q
        unk = ~known
        zhat = o + np.where(unk, pi, 0).sum(axis=1)
        Lhat = min(max(frac_capacity(zhat, b), vlo), vhi)
        order = np.lexsort((tie, zhat))
        best = None
        for s in range(max(vlo, Lhat - eps), max(vlo, Lhat) + 1):
            # Safety: s rows with smallest predicted cost; deficit in opposition units.
            A = order[:s]
            Ds = max(0, int(up[A].sum()) - b)
            pa = np.where(unk[A], 1 - pi[A], 0).sum()
            cs = Ds / max(pa / max(unk[A].sum(), 1), 1e-6) if Ds else 0.0
            p = s + eps + 1
            if p > m:
                De, t, ce = 0, 0, 0.0
            else:
                zs = np.sort(zhat)[:p]
                t = next((tt for tt in range(T + 1) if np.minimum(zs, tt).sum() >= b + 1), T)
                # Lower-bound exclusion deficit (Lemma: p smallest lower counts >= b+1).
                De = max(0, b + 1 - int(np.sort(o)[:p].sum()))
                need = np.clip(t - o, 0, None)
                po = np.where(unk & (need[:, None] > 0), pi, 0).sum()
                ce = float(np.minimum(need, unk.sum(axis=1)).sum()) * (De > 0) / max(po / max((unk & (need[:, None] > 0)).sum(), 1), 1e-6)
            cost = cs + ce
            if best is None or cost < best[0]:
                best = (cost, A, Ds, t, De)
        _, A, Ds, t, De = best
        score = np.zeros((m, T))
        inA = np.zeros(m, bool); inA[A] = True
        if Ds > 0:
            score += np.where(inA[:, None] & unk, (1 - pi) / Ds, 0)
        if De > 0:
            score += np.where(((o < t)[:, None]) & unk, pi / De, 0)
        if not (score > 0).any():
            # Fall back to largest width with the label-blind tie order.
            width = np.where(unk.any(axis=1), up - o, -1)
            i = int(np.lexsort((tie, -width))[0]); r = int(np.flatnonzero(unk[i])[0])
        else:
            flat = np.argmax(score)
            i, r = divmod(int(flat), T)
            ties = np.argwhere(score == score[i, r])
            i, r = min(map(tuple, ties), key=lambda x: (tie[x[0]], x[1]))
        known[i, r] = True
        q += 1
        if z[i, r]:
            o[i] += 1
        else:
            a[i] += 1


def task(key):
    panel, rep, q = key
    t0 = time.monotonic()
    c = instance(panel, 'median', rep, q)
    eps = c['epsilon']
    rec = dict(dataset=panel, split=rep, q=q, selected=int(c['S']), active=int(c['m']), T=int(c['T']),
               epsilon=int(eps), guided_primary=policy_path(c, eps), guided_exact=policy_path(c, 0),
               witness_primary=int(c['witnesses'][Fraction(1, 50)]), witness_exact=int(c['witnesses'][Fraction(0)]))
    rec['seconds'] = time.monotonic() - t0
    return rec


def main():
    out = EXP / 'outputs' / 'median_guided_records.jsonl'
    done = set()
    if out.exists():
        for line in out.open():
            x = json.loads(line); done.add((x['dataset'], x['split'], x['q']))
    keys = [(p, s, q) for q in QS for p in PANELS for s in SPLITS if (p, s, q) not in done]
    print('tasks', len(keys), flush=True)
    with out.open('a') as f, multiprocessing.get_context('spawn').Pool(4) as pool:
        for i, rec in enumerate(pool.imap_unordered(task, keys)):
            f.write(json.dumps(rec) + '\n'); f.flush()
            if i % 20 == 0:
                print(i, rec['dataset'], rec['q'], round(rec['seconds'], 1), flush=True)


if __name__ == '__main__':
    main()

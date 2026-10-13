"""Certification under hard cross-entry constraints (indicative study).

Two constraint families on candidate test scores, restricted to the active
selected rows of a batch:
  box:   |s_r(i) - c_P(i)| <= D_r            (evaluator-level deviation cap)
  lip:   |s_r(i) - s_r(i')| <= L_r d(i, i')  (Lipschitz in base-score space,
         d = max_j |s_j(i) - s_j(i')|, a pseudometric)
For both, the pointwise lower and upper envelopes of consistent completions are
themselves consistent completions (box: trivially; lip: McShane-Whitney), so
the endpoint bounds of the completion model remain jointly attainable and the
sorted-prefix capacity bounds stay exact. Parameters are oracle-valid (computed
on the hidden test batch); reference-estimated parameters are checked for
validity only. Acquisition reuses the budget-independent reference path.
"""
import json
import multiprocessing
import sys
import time
import numpy as np
from common import (EXP, PANELS, QS, SPLITS, instance, flip_count,
                    reference_path, first_stop, capacity, aggregate)


def dist(A, B):
    """L_inf distance between columns of A (M, a) and B (M, b) -> (a, b)."""
    return np.abs(A[:, :, None] - B[:, None, :]).max(axis=0)


def lipschitz_constant(S, D):
    """Max |S_i - S_j| / D_ij over pairs; inf if D=0 with a score difference."""
    diff = np.abs(S[:, None] - S[None, :])
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(D > 0, diff / np.where(D > 0, D, 1), np.where(diff > 0, np.inf, 0.0))
    np.fill_diagonal(ratio, 0.0)
    return float(ratio.max()) if ratio.size else 0.0


def ref_lipschitz(Sref, Bref, chunk=1500):
    n = Sref.shape[0]
    best = 0.0
    for a in range(0, n, chunk):
        D = dist(Bref[:, a:a + chunk], Bref)
        diff = np.abs(Sref[a:a + chunk, None] - Sref[None, :])
        with np.errstate(divide='ignore', invalid='ignore'):
            r = np.where(D > 0, diff / np.where(D > 0, D, 1), np.where(diff > 1e-15, np.inf, 0.0))
        best = max(best, float(r.max()))
    return best


def task(key):
    panel, agg, rep, q = key
    t0 = time.monotonic()
    c = instance(panel, agg, rep, q)
    ids, m, T = c['ids'], c['m'], c['T']
    cut, budget, free, eps = c['cutoff'], c['budget'], c['free'], c['epsilon']
    base = c['base'][:, ids]
    S = c['hidden'][:, ids]           # (T, m) hidden; used for oracle params and replies
    cons = aggregate(base, agg)
    truth = c['truth']
    path = reference_path(c)
    n = len(path)
    rec = dict(dataset=panel, aggregator=agg, split=rep, q=q, selected=int(c['S']), active=int(m),
               T=int(T), epsilon=int(eps), V_star=int(free + capacity(truth.sum(axis=1), budget)))
    if m == 0:
        rec['seconds'] = time.monotonic() - t0
        return rec
    D = dist(base, base)
    box = np.abs(S - cons[None, :]).max(axis=1)                     # oracle D_r
    lip = np.array([lipschitz_constant(S[r], D) for r in range(T)])  # oracle L_r
    ref, = [c['ref']]
    rbase, rcand = ref[:7], ref[7:]
    rcons = aggregate(rbase, agg)
    box_ref = np.abs(rcand - rcons[None, :]).max(axis=1)
    lip_ref = np.array([ref_lipschitz(rcand[r], rbase) for r in range(T)])
    rec.update(box_oracle_mean=float(box.mean()), box_ref_mean=float(box_ref.mean()),
               box_ref_valid_columns=int((box <= box_ref + 1e-12).sum()),
               lip_oracle_finite_columns=int(np.isfinite(lip).sum()),
               lip_oracle_median=float(np.median(lip)),
               lip_ref_finite_columns=int(np.isfinite(lip_ref).sum()),
               lip_ref_valid_columns=int((lip <= lip_ref * (1 + 1e-12)).sum()))
    fx = lambda x: flip_count(base, x, cut, agg)

    def bounds(t, family):
        known = np.zeros((m, T), bool)
        for i, r in path[:t]:
            known[i, r] = True
        low = np.zeros(m, np.int64)
        up = np.zeros(m, np.int64)
        for r in range(T):
            if family == 'none':
                lo, hi = np.zeros(m), np.ones(m)
            elif family == 'box':
                lo, hi = np.clip(cons - box[r], 0, 1), np.clip(cons + box[r], 0, 1)
            else:
                obs = np.flatnonzero(known[:, r])
                lo, hi = np.zeros(m), np.ones(m)
                if np.isfinite(lip[r]) and len(obs):
                    Dr = D[:, obs]
                    lo = np.clip((S[r, obs][None, :] - lip[r] * Dr).max(axis=1), 0, 1)
                    hi = np.clip((S[r, obs][None, :] + lip[r] * Dr).min(axis=1), 0, 1)
            # Selected rows: flips nonincreasing in the candidate score.
            fu, fl = fx(lo), fx(hi)
            assert (fl <= truth[:, r]).all() and (truth[:, r] <= fu).all()
            low += np.where(known[:, r], truth[:, r], fl)
            up += np.where(known[:, r], truth[:, r], fu)
        return free + capacity(up, budget), free + capacity(low, budget)

    for family in ['none', 'box', 'lip']:
        cache = {}
        def gap(t):
            if t not in cache:
                cache[t] = bounds(t, family)
            return cache[t][1] - cache[t][0]
        z = bounds(0, family)
        rec[f'{family}_zero_safe'] = int(z[0])
        rec[f'{family}_zero_gap'] = int(z[1] - z[0])
        for name, e in [('primary', eps), ('exact', 0)]:
            rec[f'{family}_{name}_queries'] = int(first_stop(n, gap, e))
    rec['active_entries'] = int(m * T)
    rec['seconds'] = time.monotonic() - t0
    return rec


def main():
    qs = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [.05]
    out = EXP / 'outputs' / 'constrained_records.jsonl'
    done = set()
    if out.exists():
        for line in out.open():
            x = json.loads(line); done.add((x['dataset'], x['aggregator'], x['split'], x['q']))
    keys = [(p, a, s, q) for q in qs for p in PANELS for a in ['median', 'mean'] for s in SPLITS
            if (p, a, s, q) not in done]
    print('tasks', len(keys), flush=True)
    with out.open('a') as f, multiprocessing.get_context('spawn').Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 4) as pool:
        for i, rec in enumerate(pool.imap_unordered(task, keys)):
            f.write(json.dumps(rec) + '\n'); f.flush()
            if i % 20 == 0:
                print(i, rec['dataset'], rec['aggregator'], rec['q'], round(rec['seconds'], 1), flush=True)


if __name__ == '__main__':
    main()

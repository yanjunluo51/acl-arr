"""Pre-scoring diagnostics for strict joint gain on the 1,920 mean targets.

Features use only reference-fitted predictions, visible base scores, the
budget and tolerance (no candidate test score). Labels are the numerically
closed joint and optimal-union minima in the audited full-mean records.
"""
import csv
import json
import multiprocessing
import numpy as np
from common import EXP, ROOT, instance, capacity


def frac_capacity(cost, budget):
    c = np.sort(cost)
    return int(np.searchsorted(np.cumsum(c), budget + 1e-9, side='right'))


def task(key):
    panel, rep, q = key
    c = instance(panel, 'mean', rep, q)
    m, T, S, free, b = c['m'], c['T'], c['S'], c['free'], c['budget']
    pred_tot = c['pred'].sum(axis=1) if m else np.zeros(0)
    vhat = free + frac_capacity(pred_tot, b)
    vstar = free + capacity(c['truth'].sum(axis=1), b) if m else S
    zero_safe = free + capacity(T * c['lp'], b) if m else S
    return dict(dataset=panel, split=rep, q=q, S=int(S), m=int(m), T=int(T), budget=int(b),
                V_hat=int(vhat), V_star=int(vstar), zero_safe=int(zero_safe),
                multi_level_fraction=float((c['lp'] >= 2).mean()) if m else 0.0,
                budget_ratio=float(b / max(1, T * c['lp'].sum())),
                pred_cost_ratio=float(pred_tot.sum() / b) if m else 0.0)


def auc(score, label):
    score, label = np.asarray(score, float), np.asarray(label, bool)
    pos, neg = score[label], score[~label]
    if len(pos) == 0 or len(neg) == 0:
        return None
    gt = (pos[:, None] > neg[None, :]).sum() + .5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def main():
    recs = list(csv.DictReader((ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv').open()))
    keys = sorted({(r['dataset'], int(r['split']), float(r['q'])) for r in recs})
    assert len(keys) == 960
    with multiprocessing.get_context('spawn').Pool(4) as pool:
        feats = {(f['dataset'], f['split'], f['q']): f for f in pool.map(task, keys)}
    rows = []
    for r in recs:
        f = feats[(r['dataset'], int(r['split']), float(r['q']))]
        eps = int(r['epsilon'])
        joint, union = int(r['joint_upper']), int(r['union_minimum'])
        assert int(r['joint_lower']) == joint and int(r['selected_count']) == f['S']
        rows.append(dict(f, stopping=r['stopping'], epsilon=eps, joint=joint, union=union,
                         gain=int(union > joint),
                         true_exclusion_needed=int(f['V_star'] + eps < f['S']),
                         pred_exclusion_needed=int(f['V_hat'] + eps < f['S']),
                         pred_slack=(f['S'] - eps - f['V_hat']) / f['S'],
                         zero_gap=(f['S'] - f['zero_safe']) / f['S']))
    out = EXP / 'outputs'
    with (out / 'gain_predictor_records.csv').open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary = {}
    for stop in ['primary', 'exact', 'all']:
        sub = [x for x in rows if stop == 'all' or x['stopping'] == stop]
        y = [x['gain'] for x in sub]
        s = dict(targets=len(sub), gains=sum(y))
        for name in ['true_exclusion_needed', 'pred_exclusion_needed']:
            tp = sum(1 for x in sub if x[name] and x['gain']); fp = sum(1 for x in sub if x[name] and not x['gain'])
            fn = sum(1 for x in sub if not x[name] and x['gain'])
            s[name] = dict(flagged=tp + fp, true_pos=tp, false_pos=fp, false_neg=fn)
        for name in ['pred_slack', 'zero_gap', 'multi_level_fraction', 'budget_ratio', 'pred_cost_ratio']:
            s['auc_' + name] = auc([x[name] for x in sub], y)
        summary[stop] = s
    (out / 'gain_predictor_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()

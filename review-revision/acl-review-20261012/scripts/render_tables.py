"""Render appendix tables and summary numbers for the 2026-10-12 review experiments."""
import csv
import json
import sys
from collections import defaultdict
import numpy as np
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP


def hu(x, d=1):
    """Decimal half-up rounding of an exact mean (Appendix B convention)."""
    q = x if isinstance(x, Fraction) else Fraction(Decimal(repr(float(x))))
    v = Decimal(q.numerator) / Decimal(q.denominator)
    return str(v.quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def emean(values):
    values = list(values)
    return sum(Fraction(v) for v in values) / len(values)
from common import EXP, ROOT, PANELS

TAB = ROOT / 'manuscript' / 'tables'
NAMES = {'RewardBench2': 'RewardBench~2', 'WMT23': 'WMT23 (13)', 'WMT23_without_synthetic_ref': 'WMT23 (12)',
         'WMT24-en-de': 'WMT24 en-de', 'WMT24-en-es': 'WMT24 en-es', 'WMT24-ja-zh': 'WMT24 ja-zh'}


def load(name):
    return [json.loads(l) for l in (EXP / 'outputs' / name).open()]


def per_replacement():
    R = load('per_replacement_records.jsonl')
    assert len(R) == 1920 and len({(r['dataset'], r['aggregator'], r['split'], r['q']) for r in R}) == 1920
    assert sum(r['unresolved_milps'] for r in R) == 0 and all(r['V_star_max_proven'] for r in R)
    lines = [r'\begin{table*}[t]', r'\centering\small', r'\begin{tabular}{@{}llrrrrrrr@{}}', r'\toprule',
             r'Panel & Pool & $|S_0|$ & $V^*$ & $V^*_{\max}$ & $V^-_0$ & $V^-_{0,\max}$ & Avg.\ (\%) & Per-repl.\ (\%)\\', r'\midrule']
    for p in PANELS:
        for a in ['median', 'mean']:
            v = [r for r in R if r['dataset'] == p and r['aggregator'] == a and r['q'] == .05]
            assert len(v) == 40
            f = lambda k: emean([x[k] for x in v])
            g = lambda k: 100 * emean([Fraction(x[k], x['active_entries']) if x['active_entries'] else Fraction(0) for x in v])
            lines.append(f"{NAMES[p]} & {a} & {hu(f('selected'))} & {hu(f('V_star_avg'))} & {hu(f('V_star_max'))} & "
                         f"{hu(f('zero_safe_avg'))} & {hu(f('zero_safe_max'))} & {hu(g('avg_primary_queries'))} & {hu(g('max_primary_queries'))}\\\\")
    lines += [r'\bottomrule', r'\end{tabular}',
              r'\caption{Average-budget and per-replacement targets at $q=.05$, $\alpha=.10$, means over 40 splits. $V^*$ and $V^*_{\max}$ are full-information retained counts; $V^-_0$ and $V^-_{0,\max}$ are zero-query safe counts. The last two columns give active-entry inspection at the primary stop on the same reference-priority path.}',
              r'\label{tab:per-replacement}', r'\end{table*}']
    (TAB / 'per-replacement.tex').write_text('\n'.join(lines) + '\n')
    A = np.array([[r['V_star_avg'], r['V_star_max'], r['avg_primary_queries'], r['max_primary_queries']] for r in R])
    s = dict(n=len(R), lower=int((A[:, 1] < A[:, 0]).sum()), more=int((A[:, 3] > A[:, 2]).sum()),
             fewer=int((A[:, 3] < A[:, 2]).sum()), equal=int((A[:, 3] == A[:, 2]).sum()))
    for p in PANELS:
        for a in ['median', 'mean']:
            v = [r for r in R if r['dataset'] == p and r['aggregator'] == a and r['q'] == .05]
            s[(p, a)] = {k: float(np.mean([x[k] for x in v])) for k in ['selected', 'V_star_avg', 'V_star_max', 'avg_primary_queries', 'max_primary_queries', 'active_entries']}
            s[(p, a)]['avg_pct'] = 100 * np.mean([x['avg_primary_queries'] / x['active_entries'] if x['active_entries'] else 0 for x in v])
            s[(p, a)]['max_pct'] = 100 * np.mean([x['max_primary_queries'] / x['active_entries'] if x['active_entries'] else 0 for x in v])
    return s


if __name__ == '__main__':
    s = per_replacement()
    for k, v in s.items():
        print(k, v)


def constrained(qs=(.05, .10)):
    R = load('constrained_records.jsonl')
    keys = {(r['dataset'], r['aggregator'], r['split'], r['q']) for r in R}
    assert len(keys) == len(R)
    lines = [r'\begin{table*}[t]', r'\centering\small', r'\begin{tabular}{@{}llrrrrrrrr@{}}', r'\toprule',
             r'& & \multicolumn{3}{c}{Zero-query safe count} & \multicolumn{3}{c}{Primary-stop queries} & \multicolumn{2}{c}{Ref.\ constants valid (\%)}\\',
             r'\cmidrule(lr){3-5}\cmidrule(lr){6-8}\cmidrule(l){9-10}',
             r'Panel & Pool & None & Dev. & Lip. & None & Dev. & Lip. & Dev. & Lip.\\', r'\midrule']
    out = {}
    for q in qs:
        lines.append(r'\multicolumn{10}{@{}l}{$q=' + f'{q:.2f}'.lstrip('0') + r'$}\\')
        for p in PANELS:
            for a in ['median', 'mean']:
                v = [r for r in R if r['dataset'] == p and r['aggregator'] == a and r['q'] == q]
                assert len(v) == 40, (p, a, q, len(v))
                f = lambda k: emean([x.get(k, x['selected'] if 'zero_safe' in k else 0) for x in v])
                act = [x for x in v if x['active']]
                val = lambda k: 100 * emean([Fraction(x[k], x['T']) for x in act]) if act else None
                row = {k: f(k) for k in ['none_zero_safe', 'box_zero_safe', 'lip_zero_safe', 'none_primary_queries',
                                         'box_primary_queries', 'lip_primary_queries']}
                row.update(box_valid=val('box_ref_valid_columns'), lip_valid=val('lip_ref_valid_columns'))
                for name in ['none', 'box', 'lip']:
                    for st in ['primary', 'exact']:
                        row[f'{name}_{st}_list'] = [x.get(f'{name}_{st}_queries', 0) for x in v]
                out[(p, a, q)] = row
                lines.append(f"{NAMES[p]} & {a} & {hu(row['none_zero_safe'])} & {hu(row['box_zero_safe'])} & {hu(row['lip_zero_safe'])} & "
                             f"{hu(row['none_primary_queries'])} & {hu(row['box_primary_queries'])} & {hu(row['lip_primary_queries'])} & "
                             f"{hu(row['box_valid'])} & {hu(row['lip_valid'])}\\\\")
    lines += [r'\bottomrule', r'\end{tabular}',
              r'\caption{Certification under oracle-valid deviation caps (Dev.) and Lipschitz bounds in base-score space (Lip.), $\alpha=.10$, means over 40 splits. Queries follow the unchanged reference-priority path. The last two columns give the share of candidates whose reference-estimated constant also holds on the test batch.}',
              r'\label{tab:constrained}', r'\end{table*}']
    (TAB / 'constrained.tex').write_text('\n'.join(lines) + '\n')
    return out


def weighted():
    W = load('weighted_records.jsonl')
    assert len({(w['dataset'], w['split'], w['q']) for w in W}) == len(W)
    unif = {}
    for r in csv.DictReader((ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv').open()):
        unif[(r['dataset'], int(r['split']), float(r['q']), r['stopping'])] = int(r['union_minimum']) > int(r['joint_upper'])
    out = {}
    for stop in ['exact', 'primary']:
        rows = [w for w in W if not w[stop].get('full_retention', False)]
        closed, gains, savings, rel, ug = 0, 0, [], [], 0
        open_ = []
        for w in rows:
            x = w[stop]
            union_ok = x['union_proven'] or (x['joint_proven'] and x['split_proven'] and x['joint'] == x['split'])
            union = x['joint'] if (x['joint_proven'] and x['split_proven'] and x['joint'] == x['split']) else x['union']
            if x['joint_proven'] and union_ok:
                closed += 1
                if union > x['joint']:
                    gains += 1; savings.append(union - x['joint']); rel.append((union - x['joint']) / union)
                    ug += unif.get((w['dataset'], w['split'], w['q'], stop), False)
            else:
                open_.append((w['dataset'], w['split'], w['q']))
        out[stop] = dict(instances=len(W), nonfull=len(rows), closed=closed, gains=gains,
                         mean_saving=float(np.mean(savings)) if savings else 0.0,
                         max_rel=float(max(rel)) if rel else 0.0, gains_also_uniform=ug, open=open_)
    return out

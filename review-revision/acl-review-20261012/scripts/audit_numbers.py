"""Independent recomputation of every number added in the 2026-10-12 revision.

Reads raw records only (no render_tables helpers) and checks each value
against the literal string in main.tex / appendix.tex. Exit code 1 on any
mismatch.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP


def exact(x):
    if isinstance(x, Fraction):
        return x
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return Fraction(int(x))
    return Fraction(Decimal(repr(float(x))))


def hu(x, d):
    """Decimal half-up rounding, the convention stated in Appendix B."""
    q = exact(x)
    v = Decimal(q.numerator) / Decimal(q.denominator)
    return str(v.quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def emean(values):
    values = list(values)
    if all(isinstance(v, (int, np.integer, Fraction)) and not isinstance(v, bool) for v in values):
        return sum(Fraction(int(v)) if not isinstance(v, Fraction) else v for v in values) / len(values)
    return float(np.mean(values))

ROOT = Path(__file__).resolve().parents[3]
REC = ROOT / 'outputs' / 'scope-extensions'
MAIN = (ROOT / 'manuscript' / 'main.tex').read_text()
APP = (ROOT / 'manuscript' / 'appendix.tex').read_text()
TEXT = MAIN + APP
fails, passes = [], 0


def check(label, value, literal, where=TEXT):
    global passes
    ok = literal in where
    if not ok:
        fails.append(f'{label}: literal {literal!r} not in text (value {value})')
    else:
        passes += 1


def eq(label, a, b):
    global passes
    if a != b:
        fails.append(f'{label}: {a} != {b}')
    else:
        passes += 1


def r1(x):
    return hu(x, 1)


def jl(name):
    return [json.loads(l) for l in (REC / name).open()]


PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref', 'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']

# ---------------- per-replacement
P = jl('per_replacement_records.jsonl')
eq('per-rep count', len({(r['dataset'], r['aggregator'], r['split'], r['q']) for r in P}), 1920)
eq('per-rep unresolved', sum(r['unresolved_milps'] for r in P) + sum(not r['V_star_max_proven'] for r in P), 0)
eq('per-rep never higher', sum(r['V_star_max'] > r['V_star_avg'] for r in P), 0)
lower = sum(r['V_star_max'] < r['V_star_avg'] for r in P); check('per-rep lower', lower, f'lower in {lower:,}' if lower >= 1000 else f'lower in {lower}')
eq('per-rep lower kept out of Limitations', f'lower in {lower} of 1,920' in MAIN, False)
more = sum(r['max_primary_queries'] > r['avg_primary_queries'] for r in P)
fewer = sum(r['max_primary_queries'] < r['avg_primary_queries'] for r in P)
same = sum(r['max_primary_queries'] == r['avg_primary_queries'] for r in P)
check('per-rep more/fewer/same', (more, fewer, same), f'more queries in {more:,} instances, fewer in {fewer} and the same number in {same}')


def pct(v, k):
    return 100 * emean([Fraction(x[k], x['active_entries']) if x['active_entries'] else Fraction(0) for x in v])


cell = lambda p, a: [r for r in P if r['dataset'] == p and r['aggregator'] == a and r['q'] == .05]
avg_mean = [pct(cell(p, 'mean'), 'avg_primary_queries') for p in PANELS]
max_mean = [pct(cell(p, 'mean'), 'max_primary_queries') for p in PANELS]
check('per-rep avg range', avg_mean, f'{r1(min(avg_mean))}--{r1(max(avg_mean))}\\%', MAIN)
check('per-rep max range main', max_mean, f'{r1(min(max_mean))}--{r1(max(max_mean))}\\%', MAIN)
check('per-rep max range app', max_mean, f'rose to {r1(min(max_mean))}--{r1(max(max_mean))}\\%', APP)
avg_med = [pct(cell(p, 'median'), 'avg_primary_queries') for p in PANELS]
max_med = [pct(cell(p, 'median'), 'max_primary_queries') for p in PANELS]
check('per-rep median ranges', (avg_med, max_med), f'from {r1(min(avg_med))}--{r1(max(avg_med))}\\% to {r1(min(max_med))}--{r1(max(max_med))}\\%', APP)
for p, name in [('WMT23', 'thirteen-stream WMT23'), ('RewardBench2', 'RewardBench~2')]:
    v = cell(p, 'mean')
    a, b = emean([x['V_star_avg'] for x in v]), emean([x['V_star_max'] for x in v])
    check(f'per-rep retention {p}', (a, b), f'from {r1(a)} to {r1(b)}', APP)

# ---------------- constrained
C = jl('constrained_records.jsonl')
eq('constrained count', len({(r['dataset'], r['aggregator'], r['split'], r['q']) for r in C}), 960)
A = [r for r in C if r['active']]
for fam in ['box', 'lip']:
    for st in ['primary', 'exact']:
        eq(f'{fam} {st} never more', sum(r[f'{fam}_{st}_queries'] > r[f'none_{st}_queries'] for r in A), 0)
zb = [r for r in A if r['box_zero_safe'] > r['none_zero_safe']]
check('box zero raised', len(zb), f'in {len(zb)} of 960 configurations: {sum(r["aggregator"]=="mean" for r in zb)} with mean pooling and {sum(r["aggregator"]=="median" for r in zb)} with median pooling', APP)
eq('lip zero raised', sum(r['lip_zero_safe'] > r['none_zero_safe'] for r in A), 0)
for fam, label in [('box', 'box'), ('lip', 'lip')]:
    d = np.array([r[f'{fam}_primary_queries'] - r['none_primary_queries'] for r in A])
    base = sum(r['none_primary_queries'] for r in A)
    check(f'{fam} fewer+saving', ((d < 0).sum(), -100 * d.sum() / base), f'in {(d < 0).sum()} configurations, by {hu(-100 * d.sum() / base,2)}\\% in total', APP)
v = [r for r in A if r['dataset'] == 'RewardBench2' and r['aggregator'] == 'mean' and r['q'] == .05]
check('box RB rise', 0, f'from {r1(emean([x["none_zero_safe"] for x in v]))} to {r1(emean([x["box_zero_safe"] for x in v]))} outputs', APP)
v = [r for r in A if r['dataset'] == 'WMT23' and r['aggregator'] == 'median' and r['q'] == .05]
check('lip WMT23', 0, f'from {r1(emean([x["none_primary_queries"] for x in v]))} to {r1(emean([x["lip_primary_queries"] for x in v]))}', APP)
check('lip finite', 0, f'{hu(100*emean([Fraction(r["lip_oracle_finite_columns"], r["T"]) for r in A]),1)}\\% of candidates', APP)
bv, lv = sum(r['box_ref_valid_columns'] == r['T'] for r in A), sum(r['lip_ref_valid_columns'] == r['T'] for r in A)
check('ref valid app', (bv, lv), f'in {bv} configurations for deviation caps and in {lv} for Lipschitz bounds', APP)
eq('ref valid kept out of Limitations', f'held on {bv} and {lv} of 960 configurations' in MAIN, False)
eq('constrained all active', len(A), 960)

# ---------------- weighted
W = jl('weighted_records.jsonl')
eq('weighted count', len({(w['dataset'], w['split'], w['q']) for w in W}), 960)
full = sum(w['exact'].get('full_retention', False) for w in W)
check('weighted full', full, f'feasible in {full} instances', APP)
check('weighted other', 960 - full, f'For the other {960 - full}', APP)
for stop in ['exact', 'primary']:
    rows = [w[stop] for w in W if not w[stop].get('full_retention', False)]
    closed, gains, sav, rel = 0, 0, [], []
    for x in rows:
        sandwich = x['joint_proven'] and x['split_proven'] and x['joint'] == x['split']
        union = x['joint'] if sandwich else x['union']
        if x['joint_proven'] and (x['union_proven'] or sandwich):
            closed += 1
            # Independent sanity: joint <= union <= split.
            assert x['joint'] <= union <= x['split'], x
            if union > x['joint']:
                gains += 1; sav.append(union - x['joint']); rel.append(100 * (union - x['joint']) / union)
    open_ = len(rows) - closed
    if stop == 'exact':
        check('w exact', (closed, gains), f'{closed} comparisons closed, and all {gains} showed', APP)
        eq('w exact all gains', closed, gains)
        check('w exact saving', np.mean(sav), f'mean saving was {hu(np.mean(sav),1)} entries, at most {hu(max(rel),2)}\\%', APP)
    else:
        check('w primary', (closed, gains, np.mean(sav), max(rel)), f'{closed} comparisons closed and six showed a gain, with mean saving {hu(np.mean(sav),1)} entries and at most {hu(max(rel),2)}\\%', APP)
        eq('w primary gains', gains, 6)
    check(f'w open {stop}', open_, f'{open_} exact' if stop == 'exact' else f'{open_} primary', APP)

# ---------------- gain predictors
G = list(csv.DictReader((REC / 'gain_predictor_records.csv').open()))
eq('gain rows', len(G), 1920)


def auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, bool)
    p, n = s[y], s[~y]
    return ((p[:, None] > n[None]).sum() + .5 * (p[:, None] == n[None]).sum()) / (len(p) * len(n))


for stop in ['primary', 'exact']:
    sub = [g for g in G if g['stopping'] == stop]
    y = [g['gain'] == '1' for g in sub]
    ratio = [float(g['pred_cost_ratio']) for g in sub]
    check(f'auc ratio {stop}', 0, f'{hu(auc(ratio, y),3)}'.lstrip('0'))
    check(f'auc gap {stop}', 0, f'{hu(auc([float(g["zero_gap"]) for g in sub], y),3)}'.lstrip('0'), APP)
    check(f'auc multi {stop}', 0, f'{hu(auc([float(g["multi_level_fraction"]) for g in sub], y),3)}'.lstrip('0'), APP)
eq('true rule exact', sum(g['true_exclusion_needed'] == '1' and g['gain'] == '1' for g in G), sum(g['gain'] == '1' for g in G))
eq('true rule no fp', sum(g['true_exclusion_needed'] == '1' and g['gain'] == '0' for g in G), 0)
fl = [g for g in G if g['pred_exclusion_needed'] == '1']
check('pred flagged', len(fl), f'flagged {len(fl)} of 1,920 targets, which contained {sum(g["gain"]=="1" for g in fl)} of the 89 gains', APP)

# ---------------- mapping index
M = list(csv.DictReader((ROOT / 'outputs/protocol-evidence-20261005/records.csv').open()))
eq('mapping rows', len(M), 5760)
gap = [float(x['initial_gap']) / float(x['selected_count']) for x in M]
qn = [float(x['offline_exact_certificate']) / float(x['selected_count']) for x in M]
rho = spearmanr(gap, qn).statistic
check('mapping rho', rho, f'{hu(rho,3)}'.lstrip('0'))
per = defaultdict(list)
for x, a, b in zip(M, gap, qn):
    per[x['dataset']].append((a, b))
mn = min(spearmanr(*zip(*v)).statistic for v in per.values())
eq('mapping within >= .999', round(mn, 3) >= .999, True)
for k, lab in [('active_selected_items', '.569'), ('cutoff_tie_selected_fraction', '.219')]:
    vals = [float(x[k]) / float(x['selected_count']) if k == 'active_selected_items' else float(x[k]) for x in M]
    eq(f'mapping {k}', f'{hu(spearmanr(vals, qn).statistic,3)}'.lstrip('0'), lab)

# ---------------- median guided
MG = jl('median_guided_records.jsonl')
eq('mg count', len(MG), 960)
S = {}
for x in csv.DictReader((ROOT / 'outputs/tolerance-sensitivity/stop_records.csv').open()):
    if x['aggregator'] == 'median' and x['tau'] in ('0', '1/50'):
        S[(x['dataset'], int(x['split']), float(x['q']), x['method'], x['tau'])] = int(x['queries'])
for stop, tau in [('primary', '1/50'), ('exact', '0')]:
    g = np.array([m[f'guided_{stop}'] for m in MG], float)
    ref = np.array([S[(m['dataset'], m['split'], m['q'], 'reference_priority', tau)] for m in MG], float)
    wid = np.array([S[(m['dataset'], m['split'], m['q'], 'largest_width', tau)] for m in MG], float)
    w = np.array([m[f'witness_{stop}'] for m in MG], float)
    eq(f'mg never below witness {stop}', bool((g >= w).all()), True)
    if stop == 'primary':
        check('mg means', 0, f'averaged {hu(g.mean(),1)} entries at primary stopping. Reference priority averaged {hu(ref.mean(),1)}, width {hu(wid.mean(),1)} and the matching minimum $Q_\\varepsilon$ {hu(w.mean(),1)}', APP)
        check('mg wins', 0, f'beat reference on {(g < ref).sum()} instances and lost on {(g > ref).sum()}', APP)
        check('mg app', 0, f'It beat reference on {(g < ref).sum()} instances and lost on {(g > ref).sum()}', APP)
        q05 = np.array([m['q'] == .05 for m in MG])
        check('mg q05', 0, f'averaged {hu(g[q05].mean(),1)} entries versus {hu(ref[q05].mean(),1)}', APP)
        for q in [.1, .2, .3]:
            qq = np.array([m['q'] == q for m in MG])
            eq(f'mg loses on average q={q}', g[qq].mean() > ref[qq].mean(), True)
    else:
        check('mg exact', 0, f'with {hu(g.mean(),1)} versus {hu(ref.mean(),1)} entries', APP)

# ---------------- solver
SV = jl('solver_sensitivity.jsonl')
eq('solver jobs', len(SV), 768)
eq('solver targets', len({(r['dataset'], r['split'], r['q'], r['stopping']) for r in SV}), 192)
for lim, n in [(10.0, 155), (60.0, 179)]:
    for pre in (True, False):
        eq(f'solver closed {lim} {pre}', sum(r['proven'] for r in SV if r['limit'] == lim and r['presolve'] == pre), n)
eq('solver closed equal recorded', sum(r['proven'] and r['value'] != r['recorded'] for r in SV), 0)
eq('solver none below', sum(r['value'] < r['recorded'] for r in SV), 0)
med = [np.median([r['seconds'] for r in SV if r['proven'] and r['limit'] == l and r['presolve'] == p]) for l in (10., 60.) for p in (True, False)]
check('solver median range', med, f'{hu(min(med),2)}--{hu(max(med),2)} seconds', APP)
for pre, lit in [(True, 'with presolve'), (False, 'without it')]:
    p90 = np.percentile([r['seconds'] for r in SV if r['proven'] and r['limit'] == 60. and r['presolve'] == pre], 90)
    check(f'solver p90 {pre}', p90, f'{hu(p90,1)} seconds {lit}', APP)
op = [r for r in SV if r['limit'] == 60. and r['presolve'] and not r['proven']]
eq('solver open 13', len(op), 13)
eq('solver open panels', all(r['dataset'] == 'WMT24-ja-zh' or (r['dataset'].startswith('WMT24') and r['q'] == .3) for r in op), True)
eq('solver open equal', sum(r['value'] == r['recorded'] for r in op), 7)
v = [r for r in SV if r['presolve'] and r['limit'] == 60.]
check('solver rho', 0, f'{hu(spearmanr([r["variables"] for r in v], [r["seconds"] for r in v]).statistic,3)}'.lstrip('0'), APP)
check('solver vars', 0, f'from {min(r["variables"] for r in v)} to {max(r["variables"] for r in v):,}', APP)

# ---------------- frontier diagnostic
F = [r for r in csv.DictReader((ROOT / 'outputs/frontier-priority-20261005/records.csv').open()) if r['method'] == 'joint' and r['stopping'] == 'primary']
eq('frontier n', len(F), 960)
d = np.array([int(r['delta_reference']) for r in F])
check('frontier sizes main', 0, f'Its wins averaged {round(-d[d < 0].mean())} entries and its losses {round(d[d > 0].mean())}', MAIN)
check('frontier sizes app', 0, f'wins average {hu(-d[d < 0].mean(),1)} entries and losses {hu(d[d > 0].mean(),1)}', APP)
byq = defaultdict(list)
for r, x in zip(F, d):
    byq[(r['dataset'], float(r['q']))].append(x)
allwin30 = [p for p in PANELS if (np.array(byq[(p, .3)]) < 0).sum() == 40]
eq('frontier q30 five panels', sorted(allwin30) == sorted(set(PANELS) - {'WMT24-ja-zh'}), True)
eq('frontier q05 >=34 losses', min((np.array(byq[(p, .05)]) > 0).sum() for p in PANELS) >= 34, True)

print(f'PASS {passes}  FAIL {len(fails)}')
for f in fails:
    print('FAIL', f)
sys.exit(1 if fails else 0)

"""Recompute numbers introduced while addressing the round-4 reviews."""
import csv, json, re, sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
M = (ROOT/'manuscript/main.tex').read_text(); A = (ROOT/'manuscript/appendix.tex').read_text()
fails = []; n = 0


def chk(label, cond):
    global n
    n += 1
    if not cond: fails.append(label)


def hu(q, d):
    return str((Decimal(q.numerator)/Decimal(q.denominator)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def comma(s):
    i, _, f = s.partition('.')
    return f'{int(i):,}' + ('.' + f if f else '')


# Switching policy from the saved frontier records and the pre-scoring flags.
F = {}
for r in csv.DictReader(open(ROOT/'outputs/frontier-priority-20261005/records.csv')):
    k = (r['dataset'], int(r['split']), float(r['q']), r['stopping'])
    F[k + (r['method'],)] = int(r['queries'])
    F[k + ('reference',)] = int(r['reference_priority_queries'])
G = list(csv.DictReader(open(EXP/'outputs/gain_predictor_records.csv')))
means = {}
for stop in ['primary', 'exact']:
    rows = [g for g in G if g['stopping'] == stop]
    chk(f'{stop} 960 targets', len(rows) == 960)
    acc = defaultdict(list)
    for g in rows:
        k = (g['dataset'], int(g['split']), float(g['q']), stop)
        j, s = F[k + ('joint',)], F[k + ('safety',)]
        acc['joint'].append(j); acc['safety'].append(s)
        acc['switch'].append(j if g['pred_exclusion_needed'] == '1' else s)
        acc['oracle'].append(j if g['true_exclusion_needed'] == '1' else s)
    means[stop] = {key: Fraction(sum(v), len(v)) for key, v in acc.items()}
p = means['primary']
chk('switch primary', f"averaged {comma(hu(p['switch'], 1))} queries, against {comma(hu(p['joint'], 1))} for joint and {comma(hu(p['safety'], 1))} for safety-only" in A)
chk('oracle primary', f"true non-full condition gave {comma(hu(p['oracle'], 1))}" in A)
e = means['exact']; spread = max(e.values()) - min(e.values())
chk('exact spread', Fraction(24, 10) < spread <= Fraction(25, 10) and 'the four means differed by at most 2.5 entries' in A)
chk('809.58 main', 'exceeded $Q_{\\rm joint}$ by 809.58 entries on average' in M)
RG = [r for r in csv.DictReader(open(ROOT/'outputs/full-mean-grid-20261005/audited_records.csv')) if r['stopping'] == 'primary']
ov = lambda m: hu(Fraction(sum(int(r[m + '_queries']) - int(r['joint_upper']) for r in RG), len(RG)), 2)
chk('frontier overheads', len(RG) == 960 and f"exceeded $Q_{{\\rm joint}}$ by {ov('frontier_joint')} and {ov('frontier_safety')} entries on average" in A
    and ov('reference_priority') == '809.58')

# Maximum relative joint gain in the abstract.
rel = []
for r in csv.DictReader(open(ROOT/'outputs/full-mean-grid-20261005/audited_records.csv')):
    u, j = int(r['union_minimum']), int(r['joint_upper'])
    if u > j: rel.append(Fraction(u - j, u))
chk('89 gain targets', len(rel) == 89)
chk('2.61 abstract', hu(100*max(rel), 2) == '2.61' and 'Joint gains of at most 2.61\\% beyond the best separate union appeared in 89 targets' in M)
ab = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', M, re.S).group(1)
chk('abstract <= 200 words', len(ab.replace('~', ' ').split()) <= 200)

# Real-scoring time range of the adaptive policies.
tab = (ROOT/'manuscript/tables/real-scoring-primary.tex').read_text()
secs = [Decimal(m.group(2)) for m in re.finditer(r'^([A-Z][A-Za-z -]+?) & [\d.]+ & [\d.]+ & ([\d.]+) &', tab, re.M) if m.group(1) != 'Full scoring']
chk('seven adaptive rows', len(secs) == 7)
chk('time range', f'All query policies took {min(secs)}--{max(secs)} s' in M)

# Scope sentences.
chk('AP68 exact scope', 'For exact stopping, Proposition~\\ref{prop:fixed-discovery} rules out' in A)
chk('AP28 real weights', 'exclusion compares the sum of the smallest lower costs with the real budget by strict inequality' in A)
chk('adversarial weights', 'maximum over normalized nonnegative weights therefore sits at a single scenario' in A)

# Half-up rendering is idempotent and agrees with independently rendered tables.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_tables
before = {f: (ROOT/'manuscript/tables'/f).read_text() for f in ['per-replacement.tex', 'constrained.tex']}
render_tables.per_replacement(); render_tables.constrained()
for f, s in before.items():
    chk(f'render idempotent {f}', (ROOT/'manuscript/tables'/f).read_text() == s)
chk('118.4 agrees', 'RewardBench~2 & median & 118.9 & 118.4' in before['per-replacement.tex']
    and 'RewardBench 2 & Batch retention & 0.082 & 99.6 & 118.4' in (ROOT/'manuscript/tables/query-baselines.tex').read_text())
chk('1289.6 agrees', '& 1289.6 &' in before['constrained.tex'] and 'RewardBench 2 & 0.10 & 1289.6' in (ROOT/'manuscript/tables/frontier-primary.tex').read_text())

total, pending = __import__('apply_tie_rounding').main(check_only=True)
chk('56 tie corrections in place', total == 56 and pending == 0)

# Pre-scoring AUC of the predicted cost ratio.
for stop, lit in [('primary', '.971'), ('exact', '.959')]:
    rows = [g for g in G if g['stopping'] == stop]
    pos = [float(g['pred_cost_ratio']) for g in rows if int(g['gain']) > 0]
    neg = [float(g['pred_cost_ratio']) for g in rows if int(g['gain']) == 0]
    auc = Fraction(sum(2*(a > b) + (a == b) for a in pos for b in neg), 2*len(pos)*len(neg))
    chk(f'AUC {stop}', len(pos) + len(neg) == 960 and hu(auc, 3).lstrip('0') == lit)
chk('AUC main', 'ranked gain targets above no-gain targets (AUC .971 primary, .959 exact;' in M)

# Odd-median guided policy versus reference priority.
MG = [json.loads(l) for l in open(EXP/'outputs/median_guided_records.jsonl')]
REF = {}
for x in csv.DictReader(open(ROOT/'outputs/tolerance-sensitivity/stop_records.csv')):
    if x['aggregator'] == 'median' and x['tau'] == '1/50' and x['method'] == 'reference_priority':
        REF[(x['dataset'], int(x['split']), float(x['q']))] = int(x['queries'])
d = [m['guided_primary'] - REF[(m['dataset'], m['split'], m['q'])] for m in MG]
chk('guided 960', len(d) == 960)
lost, won = sum(v > 0 for v in d), sum(v < 0 for v in d)
chk('142 of 183', (lost, won) == (142, 41) and 'lost on 142' in A)

# Whole-column minima: every non-full mean target needs every column.
COL = [json.loads(l) for l in open(ROOT/'outputs/evidence-cost-columns/records.jsonl')]
COL = [r for r in COL if r['model'] == 'mean']
vstar = {(r['dataset'], r['split'], r['q']): r['V_lower'] for r in COL if r['stopping'] == 'exact'}
nonfull = [r for r in COL if vstar[(r['dataset'], r['split'], r['q'])] < r['selected_count']]
chk('column targets', len(COL) == 1920 and len(nonfull) == 114)
chk('non-full needs every column', all(r['column_minimum'] == r['T'] for r in nonfull)
    and 'every non-full column target needed all columns' in M)

# Median pools never inspect more than mean pools (all budgets, depths and panels).
def active(path, col):
    out = {}
    for line in (ROOT/'manuscript/tables'/path).read_text().split('\n'):
        c = [x.strip() for x in line.split('\\\\')[0].split('&')]
        if len(c) > col and re.fullmatch(r'0\.\d+', c[0] if col == 5 else c[2] or ''):
            out[tuple(c[:2]) if col == 5 else (c[0], c[2])] = (c[1], Decimal(c[col]))
    return out
pairs = 0; worse = 0
for i in range(3):
    md = {k: v for k, v in active(f'review-budget-{i}-median.tex', 5).items()}
    mn = {k: v for k, v in active(f'review-budget-{i}-mean.tex', 5).items()}
    for k in md:
        pairs += 1; worse += md[k][1] > mn[k][1]
ext = {}
for line in (ROOT/'manuscript/tables/review-external-all.tex').read_text().split('\n'):
    c = [x.strip() for x in line.split('\\\\')[0].split('&')]
    if len(c) == 7 and c[1] in ('median', 'mean'):
        ext[(c[0], c[2], c[1])] = Decimal(c[6])
for (lang, q, agg), v in ext.items():
    if agg == 'median':
        pairs += 1; worse += v > ext[(lang, q, 'mean')]
chk('median inspection never higher', pairs == 72 and len(ext) == 24 and worse == 0
    and 'mean pooling averaged 85.4--86.5' in M.replace('Mean pooling','mean pooling'))

# Round 5: conditional frontier ablation, SummEval recheck, positioning sentences.
FR = defaultdict(dict)
for r in csv.DictReader(open(ROOT/'outputs/frontier-priority-20261005/records.csv')):
    FR[(r['dataset'], r['split'], r['q'], r['stopping'])][r['method']] = r
ex, full = [], []
for k, v in FR.items():
    if k[3] != 'primary': continue
    j, s = v['joint'], v['safety']; vs, s0, e = int(j['V_star']), int(j['selected_count']), int(j['epsilon'])
    d = int(s['queries']) - int(j['queries'])
    if vs + e < s0: ex.append(d)
    elif vs == s0: full.append(d)
chk('excl 32 targets', len(ex) == 32 and len(full) == 903)
chk('20.28 saving', hu(Fraction(sum(ex), 32), 2) == '20.28' and (sum(x > 0 for x in ex), sum(x < 0 for x in ex), sum(x == 0 for x in ex)) == (25, 6, 1)
    and 'frontier priority saved 20.28 entries over safety-only frontier' in M and 'with 25 wins, six losses and one tie' in A)
chk('3.72 full', hu(Fraction(-sum(full), 903), 2) == '3.72' and 'Under full retention it added 3.72' in M)
chk('switch not better', p['switch'] > p['safety'])
SU = [json.loads(l) for l in open(EXP/'outputs/summeval_union_recheck.jsonl')]
chk('summeval recheck', len(SU) == 48 and all(r['status'] == 'OPTIMAL' and r['union_presolve_off'] == r['union_recorded'] for r in SU))
g = sum(r['union_presolve_off'] > r['joint'] for r in SU); eqn = sum(r['union_presolve_off'] == r['joint'] for r in SU)
SC = (ROOT/'manuscript/summarization-confirmation.tex').read_text()
chk('summeval 27/21', (g, eqn) == (27, 21) and 'smaller than the best separate union on 27 and equal on 21' in M
    and 'Re-solving all 48 unions with HiGHS presolve disabled reproduced every value' in SC)
chk('positioning', 'Unlike matroid feasibility in basis verification \\citep{diwan2026basis}, retention feasibility depends on unobserved flip costs' in M
    and 'Matroid verification also selects the certified basis' in M)


# Odd-median minima under oracle deviation caps.
DV = [json.loads(l) for l in open(EXP/'outputs/median_deviation_minima.jsonl')]
chk('deviation 960', len({(r['dataset'], r['split'], r['q']) for r in DV}) == 960 and len(DV) == 960)
share = Fraction(sum(r['fixed'] for r in DV), sum(r['entries'] for r in DV if r['active']))
sm = [r for r in DV if r['exact_dev'] < r['exact_none']]
red = lambda st: Fraction(sum(r[st + '_none'] - r[st + '_dev'] for r in DV), sum(r[st + '_none'] for r in DV))
mx = max(Fraction(r['exact_none'] - r['exact_dev'], r['exact_none']) for r in DV if r['exact_none'])
chk('deviation numbers', all(r['exact_dev'] <= r['exact_none'] and r['primary_dev'] <= r['primary_none'] for r in DV)
    and hu(100 * share, 3) == '0.015' and len(sm) == 27 and sum(r['dataset'] == 'WMT23' for r in sm) == 26
    and hu(100 * red('exact'), 2) == '0.48' and hu(100 * red('primary'), 2) == '0.71' and hu(100 * mx, 1) == '8.2'
    and '0.015\\% of active entries' in A and 'The exact minimum fell in 27 configurations, 26 of them on thirteen-stream WMT23. The summed minimum fell by 0.48\\% in total and by at most 8.2\\%' in A
    and 'At primary stopping the total fell by 0.71\\%' in A)

chk('no strict-gain re-solve claim', 'strict_gain_evidence' not in A and 'Re-solving 66' not in A)
# SummEval: mean targets requiring exclusion without strict gain (needs private traces; skipped if absent).
TP = EXP/'private/traces-private.jsonl'
if TP.exists():
    XS = {(tuple(x['composition']), x['q']): x for x in map(json.loads, TP.read_text().splitlines()) if x['aggregator'] == 'mean'}
    def cap(costs, b):
        t = n = 0
        for c in sorted(costs):
            if t + c > b: break
            t += c; n += 1
        return n
    need = noq = 0
    for r in SU:
        x = XS[(tuple(r['composition']), r['q'])]
        s0 = x['selected']; e = 0 if r['stop'] == 'exact' else -(-2 * s0 // 100)
        vs = s0 - len(x['truth']) + cap([sum(row) for row in x['truth']], x['budget'])
        if vs + e < s0:
            need += 1; noq += r['union_presolve_off'] == r['joint']
    chk('summeval 13 of 40', (need, noq) == (40, 13) and '13 of the 40 SummEval mean targets requiring exclusion showed no gain' in M)
chk('rejected bound pointer', 'reports one rejected conflicting bound' in M and 'invalidates the reported bound for the subproblem' in A)
chk('no compatible-witness wording', 'witnesses are compatible' not in M and 'Compatibility, whether' not in M)

# Tolerance-aware frontier ablation.
EP = {(r['dataset'], r['split'], r['q']): r for r in map(json.loads, open(EXP/'outputs/frontier_eps_primary.jsonl'))}
ex_e, all_e, ex_j, wl = [], [], [], [0, 0, 0]
for k, v in FR.items():
    if k[3] != 'primary': continue
    e = EP[(k[0], int(k[1]), float(k[2]))]; j = v['joint']; s = v['safety']
    all_e.append(e['queries'])
    if int(j['V_star']) + int(j['epsilon']) < int(j['selected_count']):
        ex_e.append(e['queries']); ex_j.append(int(j['queries']))
        d = e['queries'] - int(j['queries']); wl[0 if d < 0 else 1 if d > 0 else 2] += 1
chk('eps ablation', len(EP) == 960 and len(all_e) == 960 and hu(Fraction(sum(all_e), 960), 1) == '5209.7'
    and hu(Fraction(sum(ex_e), 32), 1) == '8175.6' and hu(Fraction(sum(ex_j), 32), 1) == '8163.3' and wl == [10, 19, 3]
    and 'it averaged 5,209.7 queries' in A and 'it averaged 8,175.6 queries, against 8,163.3 for joint' in A
    and 'Against joint frontier it had 10 wins, 19 losses and three ties' in A
    and 'A tolerance-aware target, $s+\\varepsilon+1$, did not help these 32 targets' in M)
chk('median ratio table ref', 'Both medians use splits with $Q_{\\rm exact}>0$ (Appendix Table~\\ref{tab:entry-overhead-summary})' in M)

print(f'PASS {n-len(fails)}  FAIL {len(fails)}')
for f in fails: print('FAIL', f)
sys.exit(1 if fails else 0)

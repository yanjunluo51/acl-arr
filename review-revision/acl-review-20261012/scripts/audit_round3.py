"""Recompute numbers introduced while addressing the 63-item review (round 3)."""
import csv, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
M = (ROOT/'manuscript/main.tex').read_text(); A = (ROOT/'manuscript/appendix.tex').read_text()
S = (ROOT/'manuscript/summarization-confirmation.tex').read_text()
T = M + A + S + ''.join(p.read_text() for p in (ROOT/'manuscript/tables').glob('*.tex'))
fails = []; n = 0
def chk(label, cond):
    global n
    n += 1
    if not cond: fails.append(label)
# splits: thirds of group lists
rb = json.load(open(ROOT/'data/rb2_ranked_panel.json')); w23 = json.load(open(ROOT/'data/wmt23_metric_panel.json'))
for name, g, lit in [('rb', len(rb['prompt_ids']), '574/574/575'), ('wmt23', len(w23['prompt_ids']), '185/185/187')]:
    t = g // 3; chk(f'split {name}', f'{t}/{t}/{g-2*t}' == lit and lit in M)
chk('1,723 prompts', len(rb['prompt_ids']) == 1723 and '1,723 four-completion prompts' in M)
chk('557 segments', len(w23['prompt_ids']) == 557)
# A-F011 risk aggregates
risk = {(r['aggregator'], r['stopping'], r['method']): r for r in csv.DictReader(open(ROOT/'review-revision/granularity-risk-implementation/risk-aggregate.csv'))}
for agg, mx, av in [('median', '.0945', '.0427'), ('mean', '.1404', '.0496')]:
    r = risk[(agg, 'primary', 'reference_priority')]
    chk(f'risk {agg} masks', r['masks'] == '960')
    chk(f'risk {agg} max', f"{float(r['mean_max_risk']):.4f}".lstrip('0') == mx)
    chk(f'risk {agg} avg', f"{float(r['mean_average_risk']):.4f}".lstrip('0') == av)
chk('risk text', 'mean per-mask maximum risk is .0945 for median pooling and .1404 for mean pooling' in A)
# A-F008 composition table
med = (ROOT/'manuscript/tables/review-composition-median.tex').read_text(); mean = (ROOT/'manuscript/tables/review-composition-mean.tex').read_text()
chk('comp median', re.search(r'WMT23, 13 streams & median & 0\.05 & [^&]*& [^&]*& 0\.0--67\.8', med) is not None)
chk('comp mean', re.search(r'WMT23, 13 streams & mean & 0\.05 & [^&]*& [^&]*& 79\.0--84\.4', mean) is not None)
chk('comp text', '0.0--67.8\\% under median pooling and 79.0--84.4\\% under mean pooling' in A)
# 101 of 114
chk('range 56+45', '56 of 57 exact and 45 of 57 primary' in A and 'for 101 of them' in A and '114 non-full-retention targets' in A)
# C05 arithmetic
chk('C05', 2573 + 72 == 2645 and abs(72/433303*100 - 0.0166) < 5e-5 and 'totals 2,645 entries' in A)
# C09 protocol
p = json.load(open(ROOT/'review-revision/evidence-confirmation-implementation/solver/protocol.json')) if (ROOT/'review-revision/evidence-confirmation-implementation/solver/protocol.json').exists() else None
if p:
    chk('C09', p['original_attempts'] == 202 and p['unresolved_profiles'] == 73 and p['distinct_targets'] == 40 and p['per_objective_seconds'] == 180)
chk('C09 text', 'all 73 attempts left unresolved or failed by a 202-attempt replay' in A and '180 seconds per objective' in A and '40 distinct targets' in A)
# SummEval counts
chk('192 runs', 8*4*2*3 == 192 and 'gave 192 runs on one A40' in M)
chk('160 targets', 10*4*2*2 == 160 and 'the 160 cached-score SummEval targets' in T)
# abstract
ab = M[M.index('\\begin{abstract}')+16:M.index('\\end{abstract}')]
chk('abstract <=200', len(ab.replace('~', ' ').split()) <= 200)
chk('no placeholders', not re.search(r'TBD|UNIONDONE|\\perRep|\\constrainedSummary|\\weightedSummary', T))
print(f'PASS {n-len(fails)} FAIL {len(fails)}'); [print('FAIL', f) for f in fails]
sys.exit(1 if fails else 0)

"""Figure 1: where certificate cost goes (mean decomposition) and the size of strict joint gains."""
import csv
from fractions import Fraction
from pathlib import Path
import matplotlib.pyplot as plt
from figstyle import setup, panel_label, BLUE, GREEN, GRAY, INK, MUTED, COLUMN

ROOT = Path(__file__).resolve().parents[3]
R = list(csv.DictReader(open(ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv')))
assert len(R) == 1920
mean = lambda rows, f: float(Fraction(sum(f(r) for r in rows), len(rows)))
parts = {}
for stop in ['primary', 'exact']:
    P = [r for r in R if r['stopping'] == stop]
    assert len(P) == 960
    parts[stop] = [mean(P, lambda r: int(r['split_upper']) - int(r['union_minimum'])),
                   mean(P, lambda r: int(r['union_minimum']) - int(r['joint_upper'])),
                   mean(P, lambda r: int(r['reference_priority_queries']) - int(r['joint_upper']))]
assert [round(x, 2) for x in parts['primary']] == [18.69, 5.34, 809.58]
assert [round(x, 2) for x in parts['exact']] == [81.79, 1.19, 796.66]
G = [r for r in R if int(r['union_minimum']) > int(r['joint_upper'])]
assert len(G) == 89
pct = [100 * (int(r['union_minimum']) - int(r['joint_upper'])) / int(r['union_minimum']) for r in G]
assert round(max(pct), 2) == 2.61

setup()
fig, (a, b) = plt.subplots(1, 2, figsize=(COLUMN, 1.45), gridspec_kw={'width_ratios': [1.35, 1]})
labels = ['Deduplication\n' r'$Q_{\rm split}-Q_{\cup,\rm sep}$', 'Joint gain\n' r'$Q_{\cup,\rm sep}-Q_{\rm joint}$',
          'Discovery\n' r'$Q_{\rm ref}-Q_{\rm joint}$']
y = [2, 1, 0]
for stop, c, off, h in [('primary', BLUE, 0.17, None), ('exact', GREEN, -0.17, '////')]:
    a.barh([v + off for v in y], parts[stop], height=0.3, color=c, label=stop, edgecolor='white', linewidth=0.6, hatch=h)
    for v, x in zip(y, parts[stop]):
        a.text(x * 1.12, v + off, f'{x:.2f}', va='center', ha='left', fontsize=6.8, color=INK)
a.set_xscale('log'); a.set_xlim(0.8, 6000)
a.set_yticks(y); a.set_yticklabels(labels, fontsize=7)
a.tick_params(axis='y', length=0)
a.grid(axis='y', visible=False)
a.set_xlabel('Mean entries per target (log)')
a.legend(frameon=False, loc='center right', handlelength=0.8, borderaxespad=0.1, fontsize=7)
panel_label(a, '(a) Where the cost goes')
bins = [i * 0.25 for i in range(12)]
b.hist(pct, bins=bins, color=BLUE, edgecolor='white', linewidth=0.6)
b.axvline(max(pct), color=GREEN, lw=0.8, ls=(0, (2, 1.5)))
b.text(max(pct) - 0.06, b.get_ylim()[1] * 0.92, 'max 2.61%', ha='right', va='top', fontsize=6.8, color=GREEN)
b.set_xlabel('Gain over best union (%)'); b.set_ylabel('Targets')
b.set_xlim(0, 2.9); b.grid(axis='x', visible=False)
panel_label(b, f'(b) {len(G)} strict-gain targets')
fig.tight_layout(pad=0.1, w_pad=0.8)
fig.savefig(ROOT / 'manuscript/figures/overhead.pdf')

"""Figure: discovery overhead versus minimum joint certificates, and the size of strict joint gains."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
R = list(csv.DictReader(open(ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv')))
gain = lambda r: int(r['union_minimum']) > int(r['joint_upper'])
P = [r for r in R if r['stopping'] == 'primary']
G = [r for r in R if gain(r)]
assert len(R) == 1920 and len(P) == 960 and len(G) == 89
BLUE, ORANGE = '#2a6fdb', '#c4621a'
plt.rcParams.update({'font.size': 7, 'font.family': 'serif', 'axes.linewidth': 0.5,
                     'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'pdf.fonttype': 42})
fig, (a, b) = plt.subplots(1, 2, figsize=(3.15, 1.55), gridspec_kw={'width_ratios': [1.25, 1]})
for sub, c, m, lab in [([r for r in P if not gain(r)], BLUE, 'o', 'no strict gain'),
                       ([r for r in P if gain(r)], ORANGE, '^', 'strict gain')]:
    a.scatter([int(r['joint_upper']) for r in sub], [int(r['reference_priority_queries']) for r in sub],
              s=5, c=c, marker=m, linewidths=0, alpha=0.8, label=lab)
lo, hi = 30, 4e4
a.plot([lo, hi], [lo, hi], ls='--', lw=0.6, c='#555555')
a.set_xscale('log'); a.set_yscale('log'); a.set_xlim(lo, hi); a.set_ylim(lo, hi)
a.set_xlabel(r'$Q_{\rm joint}$'); a.set_ylabel('Reference queries')
a.legend(frameon=False, fontsize=5.5, loc='upper left', handletextpad=0.1, borderaxespad=0.1)
a.set_title('(a) 960 primary targets', fontsize=7)
pct = [100 * (int(r['union_minimum']) - int(r['joint_upper'])) / int(r['union_minimum']) for r in G]
b.hist(pct, bins=[i * 0.25 for i in range(12)], color=ORANGE, edgecolor='white', linewidth=0.5)
b.set_xlabel('Gain over union (%)'); b.set_ylabel('Targets')
b.set_title('(b) 89 gain targets', fontsize=7)
for ax in (a, b):
    ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout(pad=0.2, w_pad=0.6)
fig.savefig(ROOT / 'manuscript/figures/overhead.pdf')
print('max', max(pct), 'n', len(pct))

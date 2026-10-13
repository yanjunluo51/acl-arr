"""Figure: per-panel ratio of reference-priority queries to the minimum joint certificate."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
R = list(csv.DictReader(open(ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv')))
assert len(R) == 1920
PANELS = [('RewardBench2', 'RewardBench 2'), ('WMT23', 'WMT23, 13'), ('WMT23_without_synthetic_ref', 'WMT23, 12'),
          ('WMT24-en-de', 'WMT24 en-de'), ('WMT24-en-es', 'WMT24 en-es'), ('WMT24-ja-zh', 'WMT24 ja-zh')]
BLUE, ORANGE = '#2a6fdb', '#c4621a'
plt.rcParams.update({'font.size': 7, 'font.family': 'serif', 'axes.linewidth': 0.5, 'pdf.fonttype': 42})
fig, ax = plt.subplots(figsize=(3.15, 1.7))
for j, (stop, c, off) in enumerate([('primary', BLUE, -0.18), ('exact', ORANGE, 0.18)]):
    data = []
    for key, _ in PANELS:
        rows = [r for r in R if r['dataset'] == key and r['stopping'] == stop]
        assert len(rows) == 160
        data.append([int(r['reference_priority_queries']) / int(r['joint_upper']) for r in rows])
    bp = ax.boxplot(data, positions=[i + off for i in range(len(PANELS))], widths=0.3, patch_artist=True,
                    showfliers=False, medianprops={'color': 'black', 'linewidth': 0.8},
                    whiskerprops={'linewidth': 0.5}, capprops={'linewidth': 0.5}, boxprops={'linewidth': 0.5})
    for b in bp['boxes']:
        b.set_facecolor(c); b.set_alpha(0.75)
    ax.plot([], [], 's', color=c, label=f'{stop} stopping')
ax.axhline(1, ls='--', lw=0.6, c='#555555')
ax.set_xticks(range(len(PANELS))); ax.set_xticklabels([p for _, p in PANELS], rotation=25, ha='right')
ax.set_ylabel(r'Ref. queries / $Q_{\rm joint}$')
ax.spines[['top', 'right']].set_visible(False)
ax.legend(frameon=False, fontsize=6, loc='upper right')
fig.tight_layout(pad=0.2)
fig.savefig(ROOT / 'manuscript/figures/overhead_ratio.pdf')

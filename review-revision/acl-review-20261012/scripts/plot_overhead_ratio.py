"""Figure: per-panel ratio of reference-priority queries to the minimum joint certificate."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
from figstyle import setup, BLUE, GREEN, MUTED, COLUMN

ROOT = Path(__file__).resolve().parents[3]
R = list(csv.DictReader(open(ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv')))
assert len(R) == 1920
PANELS = [('RewardBench2', 'RewardBench 2'), ('WMT23', 'WMT23, 13'), ('WMT23_without_synthetic_ref', 'WMT23, 12'),
          ('WMT24-en-de', 'WMT24 en-de'), ('WMT24-en-es', 'WMT24 en-es'), ('WMT24-ja-zh', 'WMT24 ja-zh')]
setup()
fig, ax = plt.subplots(figsize=(COLUMN, 1.7))
for j, (stop, c, off) in enumerate([('primary', BLUE, -0.18), ('exact', GREEN, 0.18)]):
    data = []
    for key, _ in PANELS:
        rows = [r for r in R if r['dataset'] == key and r['stopping'] == stop]
        assert len(rows) == 160
        data.append([int(r['reference_priority_queries']) / int(r['joint_upper']) for r in rows])
    bp = ax.boxplot(data, positions=[i + off for i in range(len(PANELS))], widths=0.3, patch_artist=True,
                    showfliers=False, medianprops={'color': 'white', 'linewidth': 1.0},
                    whiskerprops={'linewidth': 0.6, 'color': MUTED}, capprops={'linewidth': 0.6, 'color': MUTED}, boxprops={'linewidth': 0})
    for b in bp['boxes']:
        b.set_facecolor(c)
    ax.plot([], [], 's', color=c, label=f'{stop} stopping')
ax.axhline(1, ls='--', lw=0.6, c='#555555')
ax.set_xticks(range(len(PANELS))); ax.set_xticklabels([p for _, p in PANELS], rotation=25, ha='right')
ax.set_ylabel(r'Ref. queries / $Q_{\rm joint}$')
ax.grid(axis='x', visible=False)
ax.legend(frameon=False, fontsize=6, loc='upper right')
fig.tight_layout(pad=0.2)
fig.savefig(ROOT / 'manuscript/figures/overhead_ratio.pdf')

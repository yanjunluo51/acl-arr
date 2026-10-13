"""Figure 3: active-entry inspection by acquisition order (values of Appendix Table tab:stopping)."""
import re
from pathlib import Path
import matplotlib.pyplot as plt
from figstyle import setup, BLUE, GRAY, INK, MUTED, COLUMN

ROOT = Path(__file__).resolve().parents[3]
rows = []
for line in (ROOT / 'manuscript/tables/query-stopping.tex').read_text().splitlines():
    m = re.match(r'(RewardBench 2|WMT23, 1[23] streams) & (median|mean) & (.*)\\\\', line)
    if m:
        rows.append((m.group(1), m.group(2), [float(x) for x in m.group(3).split('&')]))
assert len(rows) == 6
setup()
fig, ax = plt.subplots(figsize=(COLUMN, 1.58))
names = [f"{p.replace(' streams', '')}, {pool}" for p, pool, _ in rows]
y = list(range(len(rows)))[::-1]
markers = [('Fixed', 1, 'o'), ('Random', 2, 's'), ('Width', 3, 'D')]
for yy, (_, _, v) in zip(y, rows):
    xs = [v[i] for _, i, _ in markers] + [v[4]]
    ax.plot([min(xs), max(xs)], [yy, yy], color='#d1d5db', lw=1.0, zorder=1)
for lab, i, mk in markers:
    ax.scatter([v[i] for _, _, v in rows], y, marker=mk, s=11, facecolor='white', edgecolor=GRAY, linewidth=0.7, label=lab, zorder=2)
ax.scatter([v[4] for _, _, v in rows], y, marker='o', s=18, color=BLUE, label='Reference', zorder=3)
for yy, (_, _, v) in zip(y, rows):
    ax.text(101.5, yy, f'{v[5]:.1f}', va='center', ha='left', fontsize=6, color=INK)
ax.text(101.5, max(y) + 0.75, 'Cov.', va='center', ha='left', fontsize=6, color=MUTED)
ax.axhline(2.5, color='#e5e7eb', lw=0.6)
ax.set_yticks(y); ax.set_yticklabels(names); ax.tick_params(axis='y', length=0)
ax.set_xlim(0, 100); ax.set_ylim(-0.6, 5.9)
ax.set_xlabel('Active entries inspected (%)')
ax.grid(axis='y', visible=False)
ax.legend(frameon=False, ncol=4, loc='lower center', bbox_to_anchor=(0.45, 1.0), handletextpad=0.2, columnspacing=0.8)
fig.tight_layout(pad=0.1)
fig.savefig(ROOT / 'manuscript/figures/inspection.pdf')

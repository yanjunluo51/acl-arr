"""Figure 2: separate-union cost relative to the joint certificate in the two realizable mean families."""
from fractions import Fraction
from pathlib import Path
import matplotlib.pyplot as plt
from figstyle import setup, panel_label, BLUE, GREEN, INK, MUTED, COLUMN

ROOT = Path(__file__).resolve().parents[3]


def growing(T):  # Proposition strict-joint: M = T+1, even T >= 2
    return Fraction(2 * T, T + 1)


def fixed_pool(T, M=7, alpha=Fraction(1, 10)):  # Proposition fixed-pool-separation
    b = int(2 * M * T * alpha)
    assert T <= b < (M - 1) * T
    r, t = divmod(b, M - 1)
    joint = T + 1
    union = T + 1 if r == 0 else 2 * T + 1 - r - (1 if t > 0 else 0)
    return Fraction(union, joint)


assert fixed_pool(6, alpha=Fraction(6, 84)) == Fraction(12, 7)  # Table 1: caps (7,6), budget six
Ts = list(range(2, 121, 2))
g = [float(growing(T)) for T in Ts]
f = [float(fixed_pool(T)) for T in Ts]
lim = 2 - Fraction(2 * 7, 10) / 6
assert lim == Fraction(53, 30)

setup()
fig, ax = plt.subplots(figsize=(COLUMN, 1.38))
ax.axhline(2, color=MUTED, lw=0.6, ls=(0, (3, 2)))
ax.axhline(float(lim), color=MUTED, lw=0.6, ls=(0, (3, 2)))
ax.axhline(1, color=MUTED, lw=0.6)
ax.plot(Ts, g, color=BLUE, lw=1.4, solid_capstyle='round')
ax.plot(Ts, f, color=GREEN, lw=1.4, solid_capstyle='round')
ax.text(121, 2, ' factor two', va='center', ha='left', fontsize=7, color=MUTED)
ax.text(121, float(lim), ' 53/30', va='center', ha='left', fontsize=7, color=MUTED)
ax.text(121, 1, r' $\varepsilon=1$', va='center', ha='left', fontsize=7, color=MUTED)
ax.text(119, 1.875, r'growing pool, $M=T+1$', color=BLUE, fontsize=7.5, ha='right', va='center')
ax.text(119, 1.63, r'fixed pool, $M=7$, $\alpha=.10$', color=GREEN, fontsize=7.5, ha='right', va='center')
ax.set_xlim(0, 120); ax.set_ylim(0.9, 2.1)
ax.set_xlabel(r'Candidate evaluators $T$')
ax.set_ylabel(r'$Q_{\cup,\rm sep}/Q_{\rm joint}$')
ax.grid(axis='x', visible=False)
fig.tight_layout(pad=0.1)
fig.savefig(ROOT / 'manuscript/figures/separation.pdf')

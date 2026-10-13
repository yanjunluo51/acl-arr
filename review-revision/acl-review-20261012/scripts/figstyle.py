"""Shared figure style: Times-like text matching the ACL template, recessive axes, validated palette."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BLUE, ORANGE, GRAY, INK, MUTED = '#1f5fbf', '#d1731f', '#8a94a3', '#222222', '#6b7280'
COLUMN = 3.03  # inches, ACL single-column width


def setup():
    plt.rcParams.update({
        'font.family': 'serif', 'font.serif': ['STIXGeneral', 'Times New Roman', 'Times'],
        'mathtext.fontset': 'stix', 'font.size': 7.5, 'axes.titlesize': 7.5, 'axes.labelsize': 7.5,
        'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'legend.fontsize': 6.5,
        'axes.linewidth': 0.5, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK,
        'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5,
        'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'axes.grid': True, 'grid.color': '#e5e7eb',
        'grid.linewidth': 0.5, 'axes.axisbelow': True, 'axes.spines.top': False, 'axes.spines.right': False,
        'pdf.fonttype': 42, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02,
    })


def panel_label(ax, s):
    ax.set_title(s, loc='left', fontsize=7.5, color=INK, pad=3)

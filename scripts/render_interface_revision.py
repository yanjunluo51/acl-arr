"""Add verified quality-table conditions after the existing display layers.

Only captions change. Numeric table bodies, labels, and split records are kept.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['query-quality.tex', 'review-mqm-median.tex', 'review-mqm-mean.tex']
CONDITIONS = (r'All results use $\alpha=.10$ and the primary stopping criterion '
              r'$V^+-V^-\le\lceil.02|S_0(P)|\rceil$. ')


def main():
    changed = []
    for name in NAMES:
        path = ROOT / 'manuscript/tables' / name
        old = path.read_text()
        start = old.index(r'\caption{') + len(r'\caption{')
        end = old.index('\n' + r'\label{', start)
        caption = old[start:end]
        if CONDITIONS not in caption:
            point = caption.index('. ') + 2
            caption = caption[:point] + CONDITIONS + caption[point:]
            new = old[:start] + caption + old[end:]
            path.write_text(new)
            changed.append(name)
    print(json.dumps({'status': 'PASS_INTERFACE_QUALITY_CAPTION_LAYER',
                      'table_files': len(NAMES), 'changed': changed,
                      'numeric_results_changed': False}))


if __name__ == '__main__':
    main()

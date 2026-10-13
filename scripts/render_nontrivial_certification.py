"""Render conditional descriptive results from the complete existing methods."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'RewardBench2': 'RewardBench 2', 'WMT23': 'WMT23, 13',
          'WMT23_without_synthetic_ref': 'WMT23, 12', 'WMT24-en-de': 'WMT24 en-de',
          'WMT24-en-es': 'WMT24 en-es', 'WMT24-ja-zh': 'WMT24 ja-zh'}


def fmt(value, places=1):
    return '--' if value is None else f'{value:.{places}f}'


def main():
    cells = json.loads((ROOT/'outputs/nontrivial-certification/results.json').read_text())['cells']
    for pool in ['median', 'mean']:
        for stop in ['two_percent_gap', 'exact_gap']:
            short = 'tolerant' if stop == 'two_percent_gap' else 'exact'
            target = r'$\varepsilon=\lceil .02|S_0|\rceil$' if short == 'tolerant' else r'$\varepsilon=0$'
            rows = []
            for c in cells:
                if (c['aggregator'], c['stopping']) != (pool, stop):
                    continue
                ref = c['methods'][-1]['nontrivial_splits']
                rows.append(' & '.join([LABELS[c['dataset']], fmt(c['q'], 2),
                    str(c['nontrivial_splits'])] +
                    [fmt(m['nontrivial_splits']['queries']) for m in c['methods']] +
                    [fmt(None if ref['active_fraction'] is None else 100*ref['active_fraction']),
                     fmt(ref['returned_count']), fmt(ref['certificate_gap'])])+r' \\')
            caption = (pool.capitalize()+r' entry acquisition with '+target+r' and $\alpha=.10$. '
                r'Each configuration has 40 splits. The shared subset has initial gap greater than $\varepsilon$; '
                r'$n$ gives its size. Query counts are conditional means for fixed, random, largest-width and '
                r'reference-priority acquisition. Ref.\ active reports its mean $Q/(mT)$ in percent; '
                r'$K$ and gap also refer to reference priority. Empty subsets are marked --. '
                r'Counts and ratios are averaged separately. These overlapping splits give descriptive results.')
            text = '\n'.join([r'\begin{table*}[t]', r'\centering\small',
                r'\caption{'+caption+'}', r'\label{tab:nontrivial-'+pool+'-'+short+'}',
                r'\begin{tabular}{llrrrrrrrr}', r'\toprule',
                r'Panel & $q$ & $n$ & Fixed & Random & Width & Ref. & Ref.\ active & $K$ & Gap \\',
                r'\midrule', *rows, r'\bottomrule', r'\end{tabular}', r'\end{table*}', ''])
            (ROOT/'manuscript/tables'/f'nontrivial-{pool}-{short}.tex').write_text(text)
    print('Rendered four tables covering all 96 configurations.')


if __name__ == '__main__':
    main()

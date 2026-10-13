"""Evidence-bound LaTeX tables; run only after the independent checker passes."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/tolerance-sensitivity'
TABLES=ROOT/'manuscript/tables'


def f(value,percent=False):
    return '--' if value is None else f'{value*(100 if percent else 1):.1f}'


def main():
    assert json.loads((OUT/'independent-check.json').read_text())['status'].startswith('PASS_')
    z=json.loads((OUT/'results.json').read_text());spec=z['protocol']
    cells={(c['dataset'],c['aggregator'],c['q'],c['method'],c['tau']):c for c in z['cells']}
    names={'RewardBench2':'RewardBench 2','WMT23':'WMT23, thirteen streams',
           'WMT23_without_synthetic_ref':'WMT23, twelve streams',
           'WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
    methods={'fixed':'Fixed','random':'Random','largest_width':'Width','reference_priority':'Reference'}
    blocks=[]
    for n,panel in enumerate(spec['panels']):
        lines=[r'\begin{table*}[t]',r'\centering\small\setlength{\tabcolsep}{3pt}',
               r'\begin{tabular}{llrrrrrrrrrr}',r'\toprule',
               r'Pooling & Order & $q$ & \multicolumn{6}{c}{Active entries queried (\%), at tolerance $\tau$} & \multicolumn{3}{c}{Selected coverage (\%)}\\',
               r'\cmidrule(lr){4-9}\cmidrule(lr){10-12}',
               r' & & & 0 & .005 & .01 & .02 & .05 & .10 & 0 & .02 & .10\\',r'\midrule']
        for agg in spec['aggregators']:
            for q in spec['quantiles']:
                for method in spec['methods']:
                    cs=[cells[panel,agg,q,method,t] for t in spec['tolerances']]
                    line=[agg.capitalize(),methods[method],f'{q:.2f}']
                    line += [f(c['active_fraction'],True) for c in cs]
                    line += [f(cs[j]['selected_coverage'],True) for j in [0,3,5]]
                    lines.append(' & '.join(line)+r'\\')
                lines.append(r'\addlinespace')
            if agg=='median':lines.append(r'\midrule')
        lines += [r'\bottomrule',r'\end{tabular}',
                  '\\caption{Fixed-path retention-tolerance sensitivity on '+names[panel]+r'. All entries average splitwise ratios over 40 overlapping splits, with $\alpha=.10$, full-reference right ECDF and the original pool. The stop is $V^+-V^-\le\lceil\tau|S_0|\rceil$. Active cost divides by $mT$; empty active sets contribute zero. Coverage divides by the unchanged base-list size.}',
                  f'\\label{{tab:tolerance-all-{n}}}',r'\end{table*}',r'\FloatBarrier']
        blocks.append('\n'.join(lines))
    (TABLES/'tolerance-all.tex').write_text('\n\n'.join(blocks)+'\n')
    lines=[r'\begin{table*}[t]',r'\centering\small\setlength{\tabcolsep}{4pt}',
           r'\begin{tabular}{lrrrrrrr}',r'\toprule',
           r'Panel & $\tau$ & $\varepsilon/|S_0|$ (\%) & $Q_\varepsilon$ & Online queries & Ratio & Positive $Q_\varepsilon$ & Zero-query (\%)\\',r'\midrule']
    for panel in spec['panels']:
        for t in spec['tolerances']:
            c=cells[panel,'median',.05,'reference_priority',t]
            line=[names[panel],f(float(__import__('fractions').Fraction(t))),f(c['effective_tolerance'],True),
                  f(c['offline_gap_certificate']),f(c['queries']),
                  '--' if c['query_to_gap_witness'] is None else f"{c['query_to_gap_witness']:.3f}",
                  str(c['query_to_gap_witness_defined_splits']),f(c['zero_query'],True)]
            # Tolerance needs enough precision to distinguish .005 and .01.
            line[1]=format(float(__import__('fractions').Fraction(t)),'.3f').rstrip('0').rstrip('.') or '0'
            lines.append(' & '.join(line)+r'\\')
        lines.append(r'\addlinespace')
    lines += [r'\bottomrule',r'\end{tabular}',
              r'\caption{Tolerance-specific median entry witnesses at $q=.05$, $\alpha=.10$, with reference-priority acquisition. Witness and online counts average all 40 splits. Ratio averages splitwise $Q_{\rm online}/Q_\varepsilon$ over positive witnesses, whose count is reported separately. Zero witnesses have undefined ratios. Effective tolerance includes integer rounding. These descriptive ratios are not online competitive guarantees.}',
              r'\label{tab:tolerance-witness}',r'\end{table*}',r'\FloatBarrier']
    (TABLES/'tolerance-witness.tex').write_text('\n'.join(lines)+'\n')
    print('Rendered 1152 active-cost cells and 36 tolerance-specific witness rows')


if __name__=='__main__':main()

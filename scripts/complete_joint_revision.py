"""Keep eight-page main exposition focused on certificate complexity."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def replace(s,a,b):
    assert s.count(a)==1,a[:70]
    return s.replace(a,b)
def main():
    p=ROOT/'manuscript/main.tex';s=p.read_text()
    a=s[s.index(r'\paragraph{A minimum-size certificate.}'):s.index(r'\begin{theorem}[Safety witness]')]
    s=replace(s,a,r'''\paragraph{A minimum-size certificate.}
With $M=7,T=3,k=2,\alpha=.10$ and boundary costs $z=(0,1,2)$, four agreements certify two rows safe and three oppositions exclude all three rows. These seven queries attain exact stopping (Appendix~\ref{app:worked-example}).

''')
    a=s[s.index(r'\paragraph{From entries to evaluator columns.}'):s.index(r'\section{Acquiring a Certificate}')]
    s=replace(s,a,r'''\paragraph{Shared columns and existing observations.}
A whole-evaluator query reveals $N$ scores. Column minima depend on where evidence occurs, even at identical row costs (Appendix~\ref{app:granularity}). Residual witnesses $Q_\varepsilon(\mathcal O)$ count additional entries after existing observations. With fixed additive entry price $\tau$ and column prices $c_r$, the minimum offline mixed cost is $\min_A\{\sum_{r\in A}c_r+\tau Q_\varepsilon(\mathcal O_A)\}$ (Appendix~\ref{app:residual}); the joint witness gives the mean counterpart.

''')
    a=s[s.index('Before inspecting WMT24 results'):s.index(r'\input{tables/review-external}')]
    s=replace(s,a,r'''Before inspecting WMT24 results, we fixed the risk objective and panel-inclusion criteria. An exact-replay failure led to a later priority-tie repair (Appendix~\ref{app:review-quality}). Official en-de, en-es and ja-zh panels \citep{freitag2024wmt24} contain 998, 998 and 722 source paragraphs, with 26, 23 and 22 output streams and 21, 21 and 22 default-reference metrics. Human references are excluded. Alphabetical order assigns seven base metrics; the others are candidates. Document-grouped splits, both pooling rules and all four depths give 960 configurations with four acquisition rules at $\alpha=.10$.

''')
    a='WMT24 Sentinel probes \\citep{perrella2024sentinel} correlate positively with pooled MQM but tie systems within each paragraph: pooled association need not imply within-source discrimination (Table~\\ref{tab:review-sentinel}).\n\n'
    s=replace(s,a,'')
    # Gap minima remain central; shorten only descriptive material duplicated in appendix.
    s=replace(s,r'Prediction rank accuracy does not consistently identify the cheaper query order; changing $q$ also changes the cutoff, selected rows, flip allowance and target (Appendix~\ref{app:acquisition-diagnostics}).',r'Across-depth prediction correlations confound changes in cutoff, rows and target (Appendix~\ref{app:acquisition-diagnostics}); the interventions below keep each task fixed.')
    p.write_text(s)
    p=ROOT/'manuscript/appendix.tex';s=p.read_text()
    s=s.replace(r'relative to the offline witness for the same target; full-panel mean ratios are not reported; the joint minima',r'relative to the offline witness for the same target. Full-panel mean ratios are not reported: the joint minima')
    p.write_text(s)
if __name__=='__main__':main()

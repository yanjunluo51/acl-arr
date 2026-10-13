"""Integrate the equivalent compact witness model into the existing story."""
from pathlib import Path
import json
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'review-revision/joint-scale-implementation'


def replace(text, old, new):
    assert text.count(old) == 1, old[:80]
    return text.replace(old, new)


def main():
    assert json.loads((OUT/'outcome-backend-check.json').read_text())['minima'] == 7680
    main_path = ROOT/'manuscript/main.tex'
    appendix_path = ROOT/'manuscript/appendix.tex'
    s, a = main_path.read_text(), appendix_path.read_text()
    s = replace(s, 'Review denotes deferral, without a model of subsequent human decisions or costs.',
                'The decision is how many existing selections to accept automatically at a stated churn allowance; review denotes deferral.')
    s = replace(s, r'Covering models also use shared revelation \citep{megow2023set}.',
                r'Covering models use shared revelation \citep{megow2023set}; query competition compares discovery with sufficient evidence \citep{erlebach2015survey,erlebach2021parallel}. Our oracle reveals individual evaluator--output scores.')
    s = replace(s, r'Our target is churn feasibility and count regret.',
                r'Certified ranking under word-substitution attacks concerns input perturbations \citep{wu2022certdr}. MT filtering and reranking measure quality \citep{perrella-etal-2024-beyond}; metric tradeoffs affect evaluation \citep{shayegh-etal-2025-feeding}. Our target is churn feasibility and count regret at fixed maps.')
    s = replace(s, 'Mean pooling can have $0<f_{ir}<p_i$, so one query contributes to both proofs.',
                'Flip counts are integers. Mean pooling can have $0<f_{ir}<p_i$, so one query contributes to both proofs.')
    s = replace(s, r'The threshold condition excludes every $p$-row set. A row-state dynamic program computes the minimum and reconstructs the queried entries, including queries shared by both proofs (Appendix~\ref{app:joint-evidence}). It applies to both pooling rules under the same endpoint completion model and specializes to the median minima.',
                r'The threshold excludes every $p$-row set. The offline dynamic program is polynomial in the explicit counts $m,T,M$, with a potentially large budget-indexed state space. An equivalent integer program groups equal flip outcomes, avoiding that grid (Appendix~\ref{app:compact-joint}). Both reconstruct minimum witnesses; online policies use interval updates instead.')
    s = replace(s, r'Without cross-entry constraints, zero-flip endpoints jointly realize $\ell$ and maximum-flip endpoints realize $u$. Both retention bounds are attainable, without statistical independence.',
                r'The completion set imposes no cross-entry constraints: zero-flip endpoints jointly realize $\ell$ and maximum-flip endpoints realize $u$. Correlated true scores remain covered; narrowing this set can change sharpness. Both bounds are attainable without statistical independence.')
    a = replace(a, r'\paragraph{Separate witnesses as a comparison.}', r'''
\paragraph{Complete search cost.}
Row states can be cached once in $O(\sum_i T|\mathcal D_i|)$ time and $O(\sum_i|\mathcal D_i|)$ space, apart from stored subsets. Total dynamic-program time then sums the fixed-$s,t$ bound over the permitted safe targets and thresholds; the working state grid is reused. An incumbent query count $q_0$ permits discarding partial states already costing at least $q_0$, since remaining query costs are nonnegative. This pruning seeks strict improvement and preserves a previously constructed witness when no improvement exists.

\begin{algorithm}[t]
\caption{Offline minimum joint witness by row states}
\label{alg:offline-joint}
\begin{algorithmic}[1]
\REQUIRE True integer contributions, endpoint caps, existing observations, $b_H$, $\varepsilon$.
\STATE Construct and cache each $\mathcal D_i$; compute $L^*$ from true row costs.
\STATE Initialize an incumbent with all remaining active entries.
\FOR{$s=\max(0,L^*-\varepsilon),\ldots,L^*$}
\STATE Set $p=s+\varepsilon+1$.
\FOR{each permitted threshold $t$ (or no threshold if $p>m$)}
\STATE Initialize the state $(n,u,d)=(0,0,0)$.
\STATE Apply the row transitions above; keep the cheapest witness for each reachable state.
\STATE Compare terminal states with $n=s$ against the incumbent.
\ENDFOR
\ENDFOR
\RETURN The minimum query count and its reconstructed entries.
\end{algorithmic}
\end{algorithm}

\paragraph{A compact outcome-count formulation.}
\label{app:compact-joint}
Candidate identity is unnecessary for unit-cost entry witnesses once its true flip contribution is known. For active row $i$, let $d_{iv}$ count remaining candidates with contribution $v\in\{0,\ldots,p_i\}$. Querying $a_{iv}$ of them gives the same row bounds regardless of which candidates are chosen. This groups integer outcomes without discretizing scores.

For a fixed safe target $s$, write $p=s+\varepsilon+1$. Use integer counts $0\le a_{iv}\le d_{iv}$, binary safe-row indicators $y_i$, and continuous products $z_{iv}$ constrained by
\begin{align*}
 0\le z_{iv}&\le a_{iv},\\
 z_{iv}&\le d_{iv}y_i,\\
 z_{iv}&\ge a_{iv}-d_{iv}(1-y_i).
\end{align*}
These inequalities make $z_{iv}=a_{iv}y_i$ exactly. Minimize $\sum_{i,v}a_{iv}$ subject to
\begin{align*}
 \sum_i y_i&=s,\\
 \sum_i u_i^0y_i-\sum_{i,v}(p_i-v)z_{iv}&\le b_H.
\end{align*}
If $p\le m$, also use an integer threshold $0\le t\le TM$ and nonnegative continuous deficits $w_i$ satisfying
\begin{align*}
 w_i&\ge t-\ell_i^0-\sum_v v a_{iv},\\
 pt-\sum_i w_i&\ge b_H+1.
\end{align*}
For $p>m$, omit the threshold and deficit constraints.

\begin{proposition}[Outcome-count equivalence]
\label{prop:compact-joint}
Minimizing this program over the same safe targets as Theorem~\ref{thm:joint} gives the same minimum additional entry count. With $G=\sum_i|\{v:d_{iv}>0\}|\le m\min(T,M+1)$, each target has $O(G+m)$ variables and constraints.
\end{proposition}
\begin{proof}
Every entry witness determines counts $a_{iv}$ and a safe set of $s$ rows. The product constraints encode its safe upper-cost sum. Lemma~\ref{lem:order-threshold} supplies a threshold and deficits satisfying the exclusion constraint. Conversely, choose any $a_{iv}$ distinct remaining entries from each outcome group. They realize lower costs $\ell_i^0+\sum_v v a_{iv}$ and upper costs $u_i^0-\sum_v(p_i-v)a_{iv}$. The indicated $s$ rows are safe, and the deficits exclude every $p$-row set. Each query is counted once. Both mappings preserve objective value, proving equivalence. There are at most $M+1$ outcome groups per row and at most $T$ nonempty groups; the variable and constraint bounds follow. These size bounds do not bound integer-program search time.
\end{proof}
The ungrouped entry formulation assigns one binary query variable to each remaining cell and is the special case $d_{iv}=1$ with equal outcomes left separate. Both formulations use the true matrix offline. Outcome grouping is specific to unit-cost entries; whole-column actions still depend on candidate identity.

\paragraph{Separate witnesses as a comparison.}''')
    a = replace(a, r'Full-information controls use exact observed costs and $b_H$; the zero-query control uses endpoint upper costs.',
                r'Full-information controls use exact observed costs and $b_H$; the zero-query control uses endpoint upper costs. Table~\ref{tab:control-objects} summarizes their different decision objects and guarantees.')
    a = replace(a, r'\paragraph{Native and matched fixed-count controls.}', r'''\begin{table*}[t]
\centering\small
\begin{tabular}{llll}
\toprule
Control & Decision object & Guarantee or objective & Candidate scores\\
\midrule
Zero-query retention & Baseline-selected outputs & Endpoint-safe retained count & None on test\\
Batch selected retention & Baseline-selected outputs & Optimal count under churn & Full test matrix\\
Batch cardinality & Selected and excluded decisions & Optimal committed count & Full test matrix\\
Batch uniform threshold & All outputs below a cost threshold & Feasible tied cost level & Full test matrix\\
Fixed-count retention & Replacement-specific top-$k$ lists & Retention under a different rule & Full test matrix\\
CRC / grouped SCoRE & Group acceptance or abstention & Calibrated risk at group level & Calibration; test as specified\\
\bottomrule
\end{tabular}
\caption{Objects and information used by the controls. The acquisition policies alone share the same selected-retention target and stopping criterion; the other rows compare objectives or guarantees.}
\label{tab:control-objects}
\end{table*}

\paragraph{Native and matched fixed-count controls.}''')
    main_path.write_text(s)
    appendix_path.write_text(a)
    bib_path = ROOT/'manuscript/references.bib'
    bib = bib_path.read_text()
    for url in ['https://aclanthology.org/2024.emnlp-main.1152.bib', 'https://aclanthology.org/2025.wmt-1.16.bib']:
        entry = urllib.request.urlopen(url, timeout=30).read().decode()
        key = entry.split('{', 1)[1].split(',', 1)[0]
        assert '{'+key+',' not in bib
        bib += '\n'+entry+'\n'
    bib += r'''
@inproceedings{erlebach2021parallel,
 author={Erlebach, Thomas and Hoffmann, Michael and de Lima, Murilo Santos},
 title={Round-Competitive Algorithms for Uncertainty Problems with Parallel Queries},
 booktitle={38th International Symposium on Theoretical Aspects of Computer Science (STACS 2021)},
 pages={27:1--27:18}, series={Leibniz International Proceedings in Informatics (LIPIcs)},
 volume={187}, year={2021}, publisher={Schloss Dagstuhl -- Leibniz-Zentrum f{\"u}r Informatik},
 doi={10.4230/LIPIcs.STACS.2021.27},
 url={https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.STACS.2021.27}
}
@misc{wu2022certdr,
 author={Wu, Chen and Zhang, Ruqing and Guo, Jiafeng and Chen, Wei and Fan, Yixing and de Rijke, Maarten and Cheng, Xueqi},
 title={Certified Robustness to Word Substitution Ranking Attack for Neural Ranking Models},
 year={2022}, eprint={2209.06691}, archivePrefix={arXiv},
 note={Accepted at CIKM 2022}, url={https://arxiv.org/abs/2209.06691}
}
'''
    bib_path.write_text(bib)
    print('Integrated equivalent outcome-count model, DP pseudocode and task positioning')


if __name__ == '__main__':
    main()

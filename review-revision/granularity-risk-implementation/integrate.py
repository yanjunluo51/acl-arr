from pathlib import Path
import json,difflib
D=Path(__file__).resolve().parent;R=D.parents[1];changes=[]
def edit(file,old,new):
 p=R/file;s=p.read_text();assert s.count(old)==1,(file,old[:60]);p.write_text(s.replace(old,new));changes.append(dict(file=file,old=old,new=new))
def main():
 assert json.loads((D/'layout-audit.json').read_text())['status']=='PASS_COLUMN_MINIMA_AND_SUFFICIENT_CONDITION'
 assert json.loads((D/'risk-audit.json').read_text())['status']=='PASS_SCENARIO_RISK_ARITHMETIC'
 (D/'pre-integration-three-pass.json').write_text(json.dumps({'checks':[{'pass':1,'scope':'Original matrices and acquisition masks unchanged; coverage uses all 57 original non-full instances and both targets, not just the 89 gains.'},{'pass':2,'scope':'Proof: lower frontier after any single-column omission is at least V(F-min f); upper-cost capacity is at most V(F+p-max f). Strict lower gap forces all columns by monotonicity. Independently checked 66339 finite integer instances and 9236 predecessor subsets.'},{'pass':3,'scope':'One sufficient condition explaining query granularity, not a new competing selection method. Risk diagnostic identifies average-vs-max scope; no quality claim or runtime saving. New condition is posthoc and sufficient, not necessary or literature-certified.'}]},indent=2))
 edit('manuscript/main.tex',r'Thus $\alpha$ budgets normalized churn, $b_H$ counts flips, and $b$ counts oppositions. Query counts measure observations.',r'Thus $\alpha$ budgets normalized churn, $b_H$ counts flips, and $b$ counts oppositions. For $M=7$, $T=3$, $k=2$ and $\alpha=.10$, these budgets are $b_H=8$ and $b=2$ (Appendix~\ref{app:worked-example}). Query counts measure observations.')
 edit('manuscript/main.tex',r'All 1,920 mean column targets have equal joint and best separate-union minima, including the 89 with strict entry gains (Appendix~\ref{app:mean-even-columns}). A realizable mean example nevertheless permits strict column gain. Previously unevaluated WMT22 panels yield 12 mean instances (24 stopping targets), all permitting full retention and showing no joint gain (Appendix~\ref{app:wmt22-confirmation}).',r'All 1,920 mean column targets have equal joint and best separate-union minima, including the 89 with strict entry gains. All 114 non-full-retention targets require every candidate column. A realizable mean example nevertheless permits strict column gain (Appendix~\ref{app:mean-even-columns}).')
 edit('manuscript/main.tex',r'Shared contributions alone do not ensure gain. In the complete mean entry grid, each no-gain target has an optimal witness certifying at least $|S_0|-\varepsilon$ outputs safe. The near-full criterion covers none of its 960 exact targets. Matching column targets show no gains, but the counterexample excludes universal equality: compatibility depends on the target and query unit.',r'Shared contributions alone do not ensure gain. Each no-gain mean entry target has an optimal witness certifying at least $|S_0|-\varepsilon$ outputs safe. The near-full entry criterion covers none of the 960 exact targets. For columns, a contribution-range condition forces full revelation in 101 of the 114 non-full-retention targets, regardless of within-row permutations (Proposition~\ref{prop:all-columns}). Thus query grouping can prevent savings even when entries support shared evidence.')
 anchor=r'For two $k$-element subsets of an $N$-output batch, the largest symmetric difference is $2\min(k,N-k)$.'
 risk=r'''\paragraph{Risk across individual replacements.}
For each of the 15,360 saved masks from six panels, two pooling rules, four depths, 40 splits, four acquisition orders and two stopping targets, we reconstruct all $MT$ member-replacement outcomes. Each individual risk divides committed membership flips by the same $2k$; their average matches $R(C)$. All masks satisfy the average budget $.10$, while 6,985 have at least one replacement above $.10$. Among 960 reference-priority primary masks per pooling rule, this occurs in 308 median and 541 mean cases. Their averages of per-mask maximum risk are .0945 and .1404, respectively; their mean replacement-average risks are .0427 and .0496. The largest individual risk across all masks is .50. These observations illustrate the distinction between average and per-replacement constraints, rather than violations of the stated certificate. The accompanying per-panel, depth, policy and stopping summaries include the 95th percentile and fraction of replacements above budget. Splits overlap, so these are descriptive frequencies. Scripts and all summaries are in \nolinkurl{review-revision/granularity-risk-implementation/}.

'''
 edit('manuscript/appendix.tex',anchor,risk+anchor)
 old=r'The fixed-action bound and realizable $3/2$ separation above show that column gains are possible in the model. Their absence on these panels therefore concerns the observed evidence layout, not a universal equality theorem.'
 new=r'The fixed-action bound and realizable $3/2$ separation above show that column gains are possible in the model. On the original 114 non-full-retention targets, every column is necessary. The following condition explains much of this full-revelation requirement using row contribution ranges.'
 edit('manuscript/appendix.tex',old,new)
 anchor=r'\subsection{Heterogeneous column-price sensitivity}'
 theory=r'''\paragraph{A condition forcing every column.}
Restrict all cost vectors in this paragraph to the baseline-selected rows, and retain the capacity $V$ and budget $b_H$. With empty history, let $a_i=\min_r f_{ir}$ and $d_i=\max_r f_{ir}$. Define
\[
 \gamma_{\rm col}=V(F-a)-V(F+p-d).
\]
This quantity uses the full score matrix to explain offline evidence requirements.
\begin{proposition}[Full-column necessity]
\label{prop:all-columns}
Under the completion model of Section~\ref{sec:partial}, if $\gamma_{\rm col}>\varepsilon$, every column is necessary to certify $V^+-V^-\le\varepsilon$. Consequently, the joint and best separate-union minima both equal $T$ unit-cost column queries. This conclusion holds for every within-row permutation of candidate scores with the base scores, cutoff, budget and tolerance fixed.
\end{proposition}
\begin{proof}
If column $r$ alone is unrevealed, the row bounds are $F_i-f_{ir}$ and $F_i+p_i-f_{ir}$. Since $a_i\le f_{ir}\le d_i$ and capacity is nonincreasing in each cost,
\[
 V(F-f_{\cdot r})-V(F+p-f_{\cdot r})
 \ge V(F-a)-V(F+p-d).
\]
Thus no single-column omission satisfies the stopping criterion. Revealing fewer columns cannot reduce the gap, so no proper column subset suffices. Full revelation certifies the exact optimum. Every separate union contains at most the $T$ available columns and is a joint certificate; both minima therefore equal $T$. Within-row permutations preserve $F,a,d,p$ and hence the condition.
\end{proof}

The condition holds for 56 of 57 exact and 45 of 57 primary non-full-retention targets in the original mean grid. The remaining 13 targets also require all columns by direct omission checks. Thus the condition is sufficient, not necessary. Independent enumeration checks it on 66,339 finite integer cases; these checks supplement the proof. Unlike the near-full entry criterion, it describes a reason joint column savings are impossible, without characterizing every equality case.

\paragraph{Changing column layout at fixed row costs.}
We retain all 57 non-full-retention mean instances and both stops. Besides the original layout, we sort each row's candidate contributions increasingly; rotate those sorted rows by their row index modulo $T$; or independently permute each row using PCG64 seeds 104729 and 130363. Each permutation transports the corresponding normalized candidate scores, so the contributions remain realizable under the same base scores and cutoff. These synthetic columns need not represent a single deployed evaluator. Row multisets, $F_i$, $p_i$, $V^*$, budgets and tolerances stay fixed. The rowwise bijection preserves all entry witnesses and their minima; it need not preserve a column witness.

All 570 layout/target comparisons have equal joint and best separate-union minima. Every column is necessary in 566 comparisons. The four exceptions use the aligned layout and primary stopping, where both minima drop by one column and exclusion is automatic. All 114 original-layout targets require every column. Independent sorted-row calculations check 9,236 predecessor subsets and each joint witness. This post hoc intervention shows that the observed column equality persists under these changes of evidence location; it does not establish universal equality or a new NLP task result. Protocols, layout records and condition coverage are in \nolinkurl{review-revision/granularity-risk-implementation/}.

'''
 edit('manuscript/appendix.tex',anchor,theory+anchor)
 (D/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
 diff=''
 for name in ['manuscript/main.tex','manuscript/appendix.tex']:
  diff+=''.join(difflib.unified_diff((D/'before'/name).read_text().splitlines(True),(R/name).read_text().splitlines(True),fromfile='before/'+name,tofile=name))
 (D/'source.diff').write_text(diff)
 print('Applied',len(changes),'bounded revisions')
if __name__=='__main__':main()

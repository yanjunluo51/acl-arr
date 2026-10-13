"""One integrated revision; anchored substitutions, no old-review rollback."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/deduplicated-evidence-implementation'
changes=[]
def replace(s,old,new,file):
    assert s.count(old)==1,(file,old[:90],s.count(old))
    changes.append(dict(file=file,old=old,new=new));return s.replace(old,new)
def main():
    p=ROOT/'manuscript/main.tex';s=p.read_text()
    old=s.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
    new=r'''
Evaluator changes can alter which language outputs are selected. We study the score evidence needed to certify near-optimal retention under a budget on membership changes averaged over a finite family of single-evaluator replacements, with fixed maps and cutoff. Partial scores give safe and optimistic retained counts whose gap bounds shortfall from the full-information optimum. For odd-sized median pools, disjoint agreement and opposition evidence yields minimum offline entry certificates. Mean observations can support both tasks; a joint program minimizes additional evidence, with an equivalent compact formulation grouping integer flip outcomes. Residual minima also characterize mixed entry and column access under fixed additive prices. Cached-score experiments on RewardBench~2 and five WMT panels distinguish required evidence from online discovery. Independent optimization checks 7,680 small-batch certificates. The compact program reaches full-test mean instances with up to 1,860 active outputs; 96 matching minima bound 384 original online paths. Joint minima improve on the best union of separately optimal witnesses in four full instances, with small reductions. True row totals do not always reduce queries under reference priority. These results characterize stability and retained-count evidence; quality and execution savings require separate measurements.

'''
    assert len(new.replace('~',' ').split())<200
    s=replace(s,old,new,'main.tex')
    pairs=[
    ('Reward models and translation metrics select language outputs whose membership can change with evaluators', 'Reward models and translation metrics are used to select language outputs, but evaluator replacement can change the selected set'),
    ('Median agreements and oppositions supply disjoint proofs. Mean queries can supply both proofs at once, so a joint row-state program characterizes their minimum evidence.', 'For odd-sized median pools, agreements certify feasibility and disjoint oppositions exclude larger feasible sets. Mean observations can support both tasks; a joint program characterizes their minimum additional evidence.'),
    (r'Unlike PAC reward estimation \citep{kalyanakrishnan2012pac}, queries reveal fixed scores.',r'PAC subset selection estimates reward means \citep{kalyanakrishnan2012pac}; our queries reveal fixed scores.'),
    ('Median Boolean costs admit closed-form minima; the mean joint program counts queries improving both bounds.','Median Boolean costs admit closed-form minima. The joint program also handles mean pooling, where a queried entry may contribute to both bounds.'),
    (r'For an existing history, let $\ell_i^0,u_i^0$ be its row bounds and $\mathcal D_i$ the attainable pairs $(a,v)$ of additional query count and revealed flip sum on row $i$. Choosing $(a_i,v_i)\in\mathcal D_i$ gives $\ell_i=\ell_i^0+v_i$ and $u_i=u_i^0-a_ip_i+v_i$. Write $L^*$ for the true optimal active count.',r'For history $\mathcal O$, let $\ell_i^0,u_i^0$ be its row bounds and $U_i$ its unqueried candidates. Using true contributions offline, define $\mathcal D_i=\{(|J|,\sum_{r\in J}f_{ir}):J\subseteq U_i\}$. A state $(a_i,v_i)$ gives $\ell_i=\ell_i^0+v_i$, $u_i=u_i^0-a_ip_i+v_i$. Let $L^*$ be the true optimal active count.'),
    (r'The minimum additional entry count for gap at most $\varepsilon$ is $\min\sum_i a_i$',r'For the fixed true matrix, history $\mathcal O$ and integer $\varepsilon\ge0$, the minimum additional entry count $Q_{\rm joint}$ is $\min\sum_i a_i$'),
    ('The threshold excludes every $p$-row set.',r'The threshold says that the $p$ smallest lower costs sum above $b_H$, excluding every feasible $p$-row set (Lemma~\ref{lem:order-threshold}).'),
    (r'(Appendix~\ref{app:residual}); the joint witness gives the mean counterpart.',r'(Appendix~\ref{app:mixed-prices}); the joint residual minimum gives the mean counterpart.'),
    ('Predictions guide order, not bounds.', 'The rule favors predicted inexpensive rows and upper-cost reductions; it does not explicitly optimize exclusion progress. Predictions guide order, not bounds.'),
    (r'\REQUIRE Visible base scores, $T$',r'\REQUIRE Visible base scores, pooling rule (mean or median), $T$'),
    (r'Sorting active costs takes $O(m\log m)$ per update; invariant selected rows add zero cost.',r'Computing each online capacity by sorting active-row costs takes $O(m\log m)$ per update; invariant selected rows add zero cost.'),
    ('Mean reference priority inspects 85.4--86.5\\% across these panels.','Under mean pooling, reference priority inspects 85.4--86.5\\% of active entries across these three panels.'),
    ('Depth changes cutoff, rows and target; the interventions below hold them fixed.','Changing $q$ changes cutoff, selected rows, budget and stopping target; cross-depth correlations do not isolate prediction accuracy. The interventions below fix the instance and target.'),
    (r'Sharing improves on separate proofs in 4/96 tasks, saving 0.607\% overall (Appendix~\ref{app:joint-scale}).',r'Joint evidence improves on the best union of separately optimal witnesses in 4/96 tasks, saving 72 entries in total. Most of the difference from their additive sum is double counting (Appendix~\ref{app:deduplicated}).'),
    ('Official en-de, en-es and ja-zh panels','Processed en-de, en-es and ja-zh panels from the official release'),
    ('Human references are excluded.','Human reference translations are excluded as outputs.'),
    ('At $q=.05$, true row totals instead increase queries from 1,873.7 to 1,892.9.',r'At $q=.05$, true row totals instead increase queries from 1,873.7 to \trueRowWmtMeanQueries{}.'),
    ('Accurate totals need not prioritize the evidence controlling the count gap','Exact row totals need not prioritize the evidence controlling the count gap under this rule'),
    ]
    for old,new in pairs:s=replace(s,old,new,'main.tex')
    old=s.split(r'\section{Conclusion}')[1].split(r'\section*{Limitations}')[0]
    new=r'''
A certificate proves feasibility and excludes feasible retained sets more than $\varepsilon$ outputs larger than the certified safe set. Odd-sized median pools separate the two evidence tasks. Joint mean evidence and outcome grouping characterize minimum additional entries after existing observations; improvements beyond deduplicating separate optima are small on the tested full batches. Matching minima distinguish requirements from discovery. Under reference priority, exact row totals alone need not reduce queries. Column sharing changes available evidence, while some protocol changes alter the task. Quality and execution savings require separate evidence.

'''
    s=replace(s,old,new,'main.tex')
    s=replace(s,r'Appendix~\ref{app:model-scope} discusses constrained completions and replacement weights.',r'Appendix~\ref{app:model-scope} discusses constrained completions and replacement weights. The joint DP has a large count-indexed state space. Outcome grouping reduces the integer model size without guaranteeing polynomial solver time. Complete mean minima cover 96 exact tasks at two depths and eight overlapping splits per panel; they do not cover the full positive-tolerance grid. Resource-limited attempts and subsequent closures are retained. True-score priorities are diagnostic, not deployable policies; observed improvements beyond optimal deduplication are modest.','main.tex')
    p.write_text(s)
    p=ROOT/'manuscript/appendix.tex';s=p.read_text()
    pairs=[
    ('Official source-only and reference-only sentinel score streams are evaluated',r'Official source-only and reference-only sentinel score streams \citep{perrella2024sentinel} are evaluated'),
    ('Thus mapping sensitivity compares different tasks unless this equivariance condition is met.','These transformations give sufficient conditions for task equivalence. Outside them, equivalence must be checked rather than assumed; the ECDF-refitting experiments above change baseline selected sets.'),
    ('attainable intermediate query outcomes can reduce both sides of the interval.','intermediate query outcomes can tighten both bounds, raising the lower cost and lowering the upper cost.'),
    ('Call this value $Q_{\\rm split}$.','Call this additive upper bound $Q_{\\rm split}$. It may count shared cells twice and is not the size of an optimally deduplicated union.'),
    ('All solver optima have zero reported gap; their witnesses are checked in integer arithmetic.','All 7,680 small-batch optimization checks report zero optimizer optimality gap; their witnesses are checked in integer arithmetic. This solver gap is distinct from the retained-count gap.'),
    ('Under exact mean certification, joint evidence saves queries in 186/960 empty-history instances, with total saving 306 and mean saving .319. With the quarter-history, 105 instances save 157 additional queries.',r'Under exact mean certification, $Q_{\rm joint}<Q_{\rm split}$ in 186/960 empty-history instances; their differences total 306 entries, or .319 per instance. With fixed quarter-history, 105 instances have a total difference of 157 additional entries.'),
    ('The observed savings are modest and vary by instance; the mean counterexample above shows why adding minima can still be incorrect.','These reductions from an additive upper bound are modest and instance-dependent. The sum of separate minima remains valid but need not equal the minimum joint certificate size.'),
    ('reports top-5\\% mean ratios only against each matching subbatch minimum, conditional on positive minima.','reports mean-pooling discovery ratios at $q=.05$, averaged over splits with positive matching subbatch minima.'),
    ('Shared evidence reduces the separate-proof count in 4/96 instances, saving 2,645 of 435,876 separate-proof entries, or 0.607\\% in aggregate.',r'In 4/96 instances, $Q_{\rm joint}$ is below the additive $Q_{\rm split}$, by 2,645 of 435,876 separately counted entries (0.607\%). Appendix~\ref{app:deduplicated} separates double counting from improvements beyond optimal deduplication.'),
    (r'\subsection{Mixed entry and column prices}',r'\subsection{Mixed entry and column prices}'+'\n'+r'\label{app:mixed-prices}'),
    (r'For mean pooling, replacing the median residual quantity by Theorem~\ref{thm:joint} gives the corresponding mixed-cost expression with active-row column observations;',r'For mean pooling, replace the median residual minimum by the joint residual minimum from Theorem~\ref{thm:joint}, using active-row column observations;'),
    ('Neither entry-witness formula characterizes mean-pooling certificates or minimum whole-evaluator certificates.',r'These median closed forms do not characterize mean-pooling or whole-evaluator minima. Theorem~\ref{thm:joint} handles joint mean entries; Appendix~\ref{app:joint-scale} supplies matching full-batch exact mean minima, not minima for the entire positive-tolerance grid.'),
    ('Changing the mapping or evaluator pool changes the baseline selected set and the stability question, so fewer queries under that protocol do not establish an improvement for the original list.','Changing the mapping or evaluator pool can change the baseline selected set and stability question. When it does, fewer queries under the new protocol do not establish an improvement for the original list.'),
    ('Both combines them.','The Both variant combines these two interventions.'),
    ('Maps, cutoff, eligible rows, replies, budgets and stopping conditions are identical within each instance.','The score matrix, maps, cutoff, eligible rows, initial bounds, budgets and certificate conditions are fixed within each instance; only query priorities change.'),
    ('All four paths run through exact stopping and record the first primary stop, giving 7,680 paths and 15,360 states.','The reference, true-row, true-candidate and combined paths run through exact stopping and record the first primary stop, giving 7,680 paths and 15,360 states. Width comparisons use the corresponding original acquisition records.'),
    ('Vertical ranges differ across panels.}',r'Curves and dotted lines are arithmetic means of splitwise coverage over 40 splits. Vertical ranges differ across panels.}'),
    ]
    for old,new in pairs:s=replace(s,old,new,'appendix.tex')
    inserted=r'''
\subsection{Joint evidence beyond deduplicating separate optima}
\label{app:deduplicated}
For each safe target $s$ in Theorem~\ref{thm:joint}, let $\mathcal A_s$ contain all minimum-size additional safety witnesses, and let $\mathcal B_{s+\varepsilon+1}$ contain all minimum-size additional exclusion witnesses. Exclusion is automatic beyond the active-row count, with the empty witness. Define
\[
 Q_{\cup,\rm sep}=\min_s\min_{A\in\mathcal A_s,\,B\in\mathcal B_{s+\varepsilon+1}}|A\cup B|.
\]
The history is fixed and not charged again. This comparison ranges over all tied component optima, rather than one pair returned by a solver.

\begin{proposition}[Deduplicated separate evidence]
\label{prop:deduplicated}
For unit-cost entry certification under the same instance, history and tolerance,
\[
 Q_{\rm joint}\le Q_{\cup,\rm sep}\le Q_{\rm split}.
\]
Within each active row, group unqueried entries with equal true contribution. If two witnesses choose $a_g,b_g$ entries from a group, their minimum possible union size is $\max(a_g,b_g)$. Minimizing $\sum_g\max(a_g,b_g)$ at separately optimal component cardinalities exactly characterizes $Q_{\cup,\rm sep}$.
\end{proposition}
\begin{proof}
The union preserves safety and exclusion by monotonicity, proving the first inequality. Choosing the target and witnesses attaining the additive bound gives the second. Within a contribution group, identities do not affect either row bound. Nested choices attain union size $\max(a_g,b_g)$; no union can contain fewer than either component. Summing and optimizing over targets proves the characterization. This exchange argument uses unit-cost entry access; column identities need not be interchangeable.
\end{proof}

The two-row example in Section~\ref{sec:median} has $Q_{\rm split}=3$ but $Q_{\cup,\rm sep}=Q_{\rm joint}=2$: its difference is entirely double counting. We therefore compare both reductions on the existing 3,840 mean small-batch tasks and 96 complete exact tasks, retaining their original histories, budgets and targets. In 3,544 tasks, equality follows from the previously proved joint and additive bounds. For the 392 remaining tasks, an outcome-count program fixes both component cardinalities before minimizing their union. A separate binary-entry model enumerates row subsets on all 388 small tasks; entry-variable threshold programs check the four full tasks. An exhaustive query-subset implementation also checks 160 fixed-seed numerical cases with at most nine entries, including histories and positive tolerances. These are finite implementation checks, not a human proof review.

\input{tables/deduplicated-evidence}
On the 96 full tasks, 2,573 of the 2,645-entry additive difference disappears by deduplication. The remaining joint reduction totals 72 entries in four instances, or 0.0166\% of 433,303 optimally deduplicated entries. Thus joint selection can improve on the best union of separately optimal proofs, but the full-batch improvements here are small. The comparison concerns offline evidence, not a gain achieved by an online policy. Small-task results remain a separate target with reset batch size and budget. Saved records retain query sets, component minima, all-target checks and solver states. One primary outcome run reported infeasibility despite an independently feasible witness; disabling presolve closed the same model. One full entry check reached its initial time limit and was resolved by an append-only retry. Failed and unresolved primary attempts are preserved.

'''
    s=replace(s,r'\subsection{Mixed entry and column prices}',inserted+r'\subsection{Mixed entry and column prices}','appendix.tex')
    p.write_text(s)
    p=ROOT/'manuscript/references.bib';s=p.read_text()
    metadata=json.loads((OUT/'citation-metadata.json').read_text())
    for key,doi in [('asudeh2018stable','10.14778/3291264.3291269'),('bates2021rcps','10.1145/3478535'),('busolin2021exit','10.1145/3404835.3463088')]:
        assert metadata[doi]['status']=='VERIFIED_REGISTRY_METADATA'
        pat=r'(@\w+\{'+key+r',.*?)(\n\})';match=re.search(pat,s,re.S);assert match
        block=match[1];assert not re.search(r'\bdoi\s*=',block,re.I)
        s=s[:match.start()]+block.rstrip()+',\n  doi = {'+doi+'}'+match[2]+s[match.end():]
    s=s.replace('Metrics? Results of the {WMT}24','Metrics? {Results} of the {WMT}24')
    s=s.replace('Herding? Reward Model','Herding? {Reward} Model')
    s=s.replace('Best-of-Evidence: Best-of-N Selection','{Best-of-Evidence}: {Best-of-N} Selection')
    s=s.replace('url = {https://arxiv.org/abs/2608.26529}','url = {https://arxiv.org/abs/2608.26529v1}')
    p.write_text(s)
    (OUT/'prose-changes.json').write_text(json.dumps(changes,indent=2)+'\n')
    print('Integrated',len(changes),'anchored changes; abstract words',len(new.split()))
if __name__=='__main__':main()

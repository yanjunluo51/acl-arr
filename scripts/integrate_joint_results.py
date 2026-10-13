"""Integrate completed, audited evidence without a new research question."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def once(s,a,b):
    assert s.count(a)==1,a[:60]
    return s.replace(a,b)
def main():
    p=ROOT/'manuscript/main.tex';s=p.read_text()
    old=s.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
    new=r'''
Evaluator changes can alter which language outputs are selected. We study the score information needed to certify near-optimal retention under a budget on average membership changes, fixing score maps, cutoff and a finite family of single-evaluator replacements. Partial scores yield safe and optimistic retained counts for mean and median pooling. For odd median pools, disjoint agreement and opposition evidence gives closed-form entry minima. For mean pooling, a query can serve both proofs; a joint row-state program characterizes minimum evidence, including existing observations. Residual witnesses also connect entries to shared columns. Cached-score experiments on RewardBench~2 and five WMT panels distinguish evidence requirements from discovery. Independent optimization checks all 7,680 joint certificates on predefined small batches. Joint evidence improves on separately minimized proofs in 186 of 960 exact mean instances. Full-batch interventions show that true row costs do not always reduce query counts, separating prediction accuracy from certificate acquisition. These results explain certificate size and discovery under the fixed churn task; quality and execution savings require separate evidence.

'''
    s=once(s,old,new)
    marker=r'\subsection{Budget and evaluator composition}'
    text=r'''The joint program extends this comparison to mean evidence. On predefined subbatches of at most four selected outputs, independently checked joint certificates improve on separately minimized safety and exclusion sizes in 186/960 exact mean instances; all median comparisons agree. The subbatches keep original maps, cutoff and candidates but reset batch size and budget (Appendix~\ref{app:joint-validation}). Their minima are not full-panel denominators.

Same-instance interventions separate row and candidate priorities. On full WMT23 mean at $q=.30$, true row totals reduce reference queries from 2,363.8 to 2,180.3, still above width's 1,800.6; true candidate ordering alone raises them to 2,396.4. At $q=.05$, true row totals instead increase queries from 1,873.7 to 1,892.9. These full-information diagnostics retain the original certificate and stopping target. Accurate totals need not prioritize the evidence controlling the count gap (Appendix~\ref{app:query-interventions}).

'''
    s=once(s,marker,text+marker)
    # Keep the scientifically useful budget figure in its existing analysis section.
    start=s.index(r'\begin{figure*}[t]');end=s.index(r'\end{figure*}',start)+len(r'\end{figure*}')
    figure=s[start:end];s=s[:start]+s[end:]
    s=once(s,r'Figure~\ref{fig:review-budgets} varies',r'Appendix Figure~\ref{fig:review-budgets} varies')
    s=once(s,'Median agreements and oppositions characterize minimum entry evidence; residual witnesses account for existing observations and fixed-price mixed queries.','Median evidence separates into agreements and oppositions; the joint row-state program accounts for shared mean evidence. Residual witnesses connect existing observations to fixed-price mixed queries.')
    s=once(s,'NLP inspection depends on initial retention, matching minima and protocol.','NLP inspection depends on initial retention, matching minima and protocol; prediction accuracy alone does not identify efficient discovery.')
    p.write_text(s)
    p=ROOT/'manuscript/appendix.tex';a=p.read_text().replace('independent endpoint attainability','joint endpoint attainability')
    marker=r'\section{Risk Budgets and Evaluator Composition}'
    # Existing appendix has separate titles; locate the first budget-specific subsection.
    idx=a.index(r'\subsection{Risk budgets}') if r'\subsection{Risk budgets}' in a else a.index(r'\input{tables/review-budget')
    a=a[:idx]+figure+'\n\n'+a[idx:]
    marker='Starting with no other candidate test observations, fix entry price'
    validation=r'''\subsection{Joint-certificate validation and NLP subbatches}
\label{app:joint-validation}
Independent query-subset enumeration checks 6,316 capped-integer cases, 768 scaled median cases and 400 realizable mean cases with exact rational scores. Histories, endpoint outcomes, intermediate flips, ties, budgets and count tolerances are included. The median cases match Corollary~\ref{cor:gap-witness}.

For each of six original panels, both pooling rules, four depths and forty splits, take the first four baseline-selected outputs in the original label-blind tie order, or all of them if fewer exist. Reference maps, the cutoff and complete candidate family stay fixed. Set $N$ to this subbatch size, reset $k=\max(1,\operatorname{round}(qN))$ and use $\alpha=.10$. The original $q$ still determines the original reference cutoff; this construction defines a separate batch, not a subset certificate for the original budget. Invariant rows are included and require no queries.

We compute minima at $\varepsilon\in\{0,1\}$ from empty history and from a fixed quarter-history: reveal the first $\lfloor mT/4\rfloor$ eligible cells in seeded row then candidate-index order. These 1,920 batch configurations give 7,680 joint minima and matching $Q_{\rm split}$ comparisons. A separate binary integer optimization enumerates all safe and excluded output subsets, instead of using the threshold identity or row states. All solver optima have zero reported gap; their witnesses are checked in integer arithmetic. All 7,680 pairs agree, with no unresolved instances. Complete records include reconstructed query sets and safe masks.

Under exact mean certification, joint evidence saves queries in 186/960 empty-history instances, with total saving 306 and mean saving .319. With the quarter-history, 105 instances save 157 additional queries. At $\varepsilon=1$, these counts are 74 and 23, respectively. All 3,840 median history/tolerance comparisons have zero difference. The observed savings are modest and vary by instance; the mean counterexample above shows why adding minima can still be incorrect.

\input{tables/joint-small-batches}

The four original complete acquisition policies are also run on these same batches from empty history through exact stopping, retaining their original reference-fitted predictions and tie conventions. Their first stops at $\varepsilon=0$ and one give 15,360 records. Table~\ref{tab:joint-discovery} reports top-5\% mean ratios only against each matching subbatch minimum, conditional on positive minima. Full-panel mean acquisition is not divided by these small-batch minima. These analyses use previously exposed panels and provide descriptive evidence.
\input{tables/joint-discovery}
\FloatBarrier

'''
    a=once(a,marker,validation+marker)
    marker='The formula uses the true matrix to choose evidence offline; it supplies neither an online policy nor a batching-dependent execution model.'
    a=once(a,marker,marker+' For mean pooling, replacing the median residual quantity by Theorem~\\ref{thm:joint} gives the corresponding mixed-cost expression with active-row column observations; the same column-first argument applies.')
    marker=r'\input{tables/acquisition-median}'
    interventions=r'''\subsection{Same-instance row and candidate interventions}
\label{app:query-interventions}
Across all 1,920 complete original configurations, retain the reference method and replace its row estimates, candidate priorities, or both with true flip contributions. True-row priority is $\ell_i+\sum_{r\in U_i}f_{ir}=F_i$; it uses full hidden row totals. True-candidate priority orders unqueried candidates by increasing $f_{ir}$, keeping the row rule otherwise unchanged. Both combines them. Candidate and row ties keep their original priorities. These are full-information mechanism interventions, not online methods. Maps, cutoff, eligible rows, replies, budgets and stopping conditions are identical within each instance.

All four paths run through exact stopping and record the first primary stop, giving 7,680 paths and 15,360 states. The reference method reproduces all 3,840 original exact and primary query counts. An independent checker validates 21,632,445 replies, every stopping mask and first stopping state. It also reconstructs 416,920 query choices by direct row and candidate sorting on all 48 split-zero configurations.

Table~\ref{tab:query-interventions} reports mean results at every depth. On full WMT23 mean at $q=.30$, true-row priority saves queries in all 40 splits relative to reference, but its mean remains 379.7 queries above width. True-candidate priority alone is worse on 36 splits and better on one. At $q=.05$, true-row priority is worse on 31 and better on nine splits. Its fixed true-cost ordering favors cheap rows, while exclusion can need evidence across other rows. The intervention changes that priority within the same instance; it does not identify a universally best learned predictor. Complete median and exact-stop cells retain both gains and losses in the accompanying records.
\input{tables/query-interventions}
\FloatBarrier

'''
    a=once(a,marker,interventions+marker)
    a=a.replace('no corresponding witness formula is derived here for mean pooling.','full-panel mean ratios are not reported; the joint minima in Appendix~\\ref{app:joint-validation} concern separate small batches.')
    p.write_text(a)
if __name__=='__main__':main()

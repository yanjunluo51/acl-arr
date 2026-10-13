from pathlib import Path
import json
D=Path(__file__).resolve().parent;R=D.parents[1]
assert json.loads((D/'theory-check.json').read_text())['status']=='PASS_SCOPED_CONSTRUCTED_SCORE_AND_COLUMN_CHECKS'
changes=[]
def edit(name,old,new):
 p=R/name;s=p.read_text();assert s.count(old)==1,(name,old[:80]);p.write_text(s.replace(old,new));changes.append(dict(file=name,old=old,new=new))
# These three checks precede manuscript changes. The refined cutoff also follows
# the implemented reference ECDF rule; no test score is used to choose it.
(D/'pre-integration-three-pass.json').write_text(json.dumps({
 'version':'Canonical manuscript still matches before/manuscript snapshots',
 'mathematics':'273 explicit score/position checks and 1003 exact-arithmetic indices passed. Full completion correctness, no uniqueness promise; reference ECDF realizes cutoff 3/5. This refines the construction without changing k, budget or search bounds. 570 column targets independently check the omission equivalence.',
 'scope':'Replace the earlier search reduction; integrate the column equivalence in the existing proposition. Exact-search result has initial gap one and gives no positive-tolerance lower bound. No claim of new NLP or human certification.'},indent=2)+'\n')
for n in ['main.tex','appendix.tex']:
 assert (R/'manuscript'/n).read_bytes()==(D/'before/manuscript'/n).read_bytes()
p=R/'manuscript/appendix.tex';s=p.read_text();start=s.index('\\paragraph{A basic obstruction to constant discovery overhead.}');end=s.index('\\paragraph{Fixed query actions.}',start)
new=r'''\paragraph{Discovery at fixed pool size and risk budget.}
The separation between a short witness and finding it persists with the numerical parameters of the primary study. It concerns exact stopping, not the primary positive tolerance.
\begin{proposition}[Exact discovery with fixed parameters]
\label{prop:fixed-discovery}
For every integer $h\ge0$, there is a median instance with $M=T=7$, $q=1/20$, $\alpha=1/10$, $k=20h+17$, $N=20k$ and $|S_0|=k$ whose minimum exact entry certificate has size one. Every deterministic policy correct under the full completion model has an instance in this family requiring at least $49h+42$ queries. Every randomized always-valid policy has a fixed instance with expected cost at least $(49h+43)/2$. Thus no batch-size-independent competitive factor holds for exact discovery even with these parameters fixed.
\end{proposition}
\begin{proof}
Set $m=7h+6$. The $m$ selected boundary rows have four base scores $.75$ and three $.25$. A further $k-m$ selected rows have all base scores $.75$, and the remaining $N-k$ rows have all base scores $.25$. At cutoff $t_0=3/5$, only the boundary rows can change membership. Candidate scores are $.25$ everywhere except one active candidate--output entry with score $.75$. Each active opposition contributes four flips; the unique agreement contributes zero.

These normalized values and cutoff can be realized by the reference procedure. Use 20 reference outputs indexed $a=0,\ldots,19$. For evaluator $j=0,\ldots,13$, set its raw reference scores to $1+((a+3j)\bmod20)$. Each evaluator's right ECDF maps raw scores 5 and 15 to $.25$ and $.75$. The first seven reference columns have maximum median consensus $3/5$. Since $k_{\rm ref}=1$, the fitted cutoff is $3/5$. The reference panel is fixed across all instances and supplies no information about the agreement's location.

The flip budget and opposition budget are
\[
 \begin{aligned}
 b_H&=\lfloor2k\alpha MT\rfloor=196h+166,\\
 b&=\lfloor b_H/4\rfloor=49h+41=mT-1.
 \end{aligned}
\]
All $k$ selected outputs are truly feasible. Initially, however, the upper costs allow only $k-1$ and the lower costs allow $k$. Observing the unique agreement reduces the total upper cost from $4mT$ to $4(mT-1)\le b_H$, certifying all $k$. Hence the exact offline minimum is one.

Before that entry is observed, the all-opposition completion remains consistent and permits only $k-1$ selected outputs, while a completion with an agreement at any unseen active entry permits $k$. These two completions prevent exact stopping. The policy must be correct on the full completion set; it is not given a promise that exactly one agreement exists. Place the agreement last on a deterministic policy's all-opposition path to force $mT$ active queries. For a uniformly chosen agreement location, any fixed random seed induces an order with expected discovery position at least $(mT+1)/2$. Averaging first over locations and then over seeds gives a fixed location with at least that expected cost. Queries outside the active entries can only add cost.
\end{proof}

The initial gap is one. Therefore every $\varepsilon\ge1$, including the primary $\lceil .02|S_0|\rceil$ criterion, allows stopping without queries on this family. The lower bound neither explains the measured positive-tolerance overhead nor establishes how often hard instances occur in NLP. It shows why a short exact offline certificate alone does not imply an efficient exact online policy. The reference construction, explicit replacement checks for all 273 agreement positions at $h=0,1,2$, and exact-arithmetic checks of 1,003 values of $h$ are provided in \nolinkurl{review-revision/discovery-bound-implementation/}; finite checks supplement the proof.

'''
edit('manuscript/appendix.tex',s[start:end],new)
s=p.read_text();start=s.index('\\paragraph{A condition forcing every column.}');end=s.index('\\paragraph{Changing column layout',start)
new=r'''\paragraph{When every column is necessary.}
Restrict all cost vectors to baseline-selected rows, retain capacity $V$ and budget $b_H$, and start with empty history. For $T\ge1$, define the gap when column $r$ alone is missing by
\[
 \delta_r=V(F-f_{\cdot r})-V(F+p-f_{\cdot r}).
\]
Also let $\underline f_i=\min_r f_{ir}$, $\overline f_i=\max_r f_{ir}$ and
\[
 \gamma_{\rm col}=V(F-\underline f)-V(F+p-\overline f).
\]
Both quantities use the full score matrix to explain offline evidence requirements.
\begin{proposition}[Full-column necessity]
\label{prop:all-columns}
Under the completion model of Section~\ref{sec:partial}, the joint minimum equals $T$ unit-cost column queries if and only if $\min_r\delta_r>\varepsilon$. Whenever this holds, the best separate-union minimum also equals $T$. Moreover, $\gamma_{\rm col}\le\min_r\delta_r$, so $\gamma_{\rm col}>\varepsilon$ is a sufficient condition that remains true under every within-row permutation of candidate scores, with base scores, cutoff, budget and tolerance fixed.
\end{proposition}
\begin{proof}
If column $r$ alone is unrevealed, the row bounds are $F_i-f_{ir}$ and $F_i+p_i-f_{ir}$, giving gap $\delta_r$. If some $\delta_r\le\varepsilon$, that omission certifies the target using $T-1$ columns. Otherwise every one-column omission fails; any proper subset is contained in such an omission and has at least its gap by revealing monotonicity. Full revelation always succeeds, proving the equivalence. A best separate union is a joint certificate and uses at most the $T$ available columns, proving equality of the two minima in this case.

Since $\underline f_i\le f_{ir}\le\overline f_i$ and capacity is nonincreasing in each cost,
\[
 \begin{aligned}
 &V(F-f_{\cdot r})-V(F+p-f_{\cdot r})\\
 &\qquad\ge V(F-\underline f)-V(F+p-\overline f).
 \end{aligned}
\]
Within-row permutations preserve $F,\underline f,\overline f,p$ and hence the sufficient condition.
\end{proof}

The range condition holds for 56 of 57 exact and 45 of 57 primary non-full-retention targets in the original mean grid. The omission criterion establishes full revelation for the remaining 13. Independent enumeration checks the range condition on 66,339 finite integer cases; independent omission calculations check the equivalence on all 570 layout/target comparisons below, with full revelation in 566. These checks supplement the proof. The equivalence is a direct consequence of revealing monotonicity: it characterizes full revelation, not all instances of equality or strict advantage between joint and separate-union certificates.

'''
edit('manuscript/appendix.tex',s[start:end],new)
edit('manuscript/appendix.tex',r'In particular, at $b=T-1$, a feasible row with one agreement has a one-entry offline certificate. An adversary can place that agreement at the last entry queried, giving a discovery ratio of $T$. Thus no deterministic exact strategy has a universal constant worst-case ratio to the offline minimum without additional assumptions.',r'At $b=T-1$, a feasible row with one agreement has a one-entry offline certificate, whereas an adversary can force $T$ queries. Proposition~\ref{prop:fixed-discovery} strengthens this obstruction: with $M=T=7$, $q=.05$, $\alpha=.10$ and $|S_0|=k$, exact discovery cost can grow with batch size while the offline minimum remains one.')
edit('manuscript/main.tex',r'Across 960 primary targets, joint savings average 5.34 entries, while reference queries exceed joint minima by 809.58 (Table~\ref{tab:cost-contrasts}). The latter comparison uses full-score knowledge and does not establish savings achievable by an online policy. Discovery overhead remains much larger than the savings from joint optimization.',r'Across 960 primary targets, joint savings average 5.34 entries, while reference queries exceed joint minima by 809.58 (Table~\ref{tab:cost-contrasts}). These offline minima do not prescribe efficient acquisition. At fixed $M=T=7$, $q=.05$ and $\alpha=.10$, exact discovery can require linearly many queries in batch size despite a one-entry certificate (Proposition~\ref{prop:fixed-discovery}). That construction stops immediately at the primary tolerance; the measured positive-tolerance overhead remains unexplained by this bound.')
# Compact glossary supports the existing method, without inventing new objects.
old=r'\subsection{Flip geometry and sharp intervals}'
new=r'''\subsection{Notation and units}
Table~\ref{tab:notation} collects the main quantities. The three-row trace in Appendix~\ref{app:worked-example} illustrates interval updates; the two-row example in Section~\ref{sec:median} isolates the extra choice offered by joint evidence.
\begin{table}[t]
\centering\small
\begin{tabular}{@{}p{.23\columnwidth}p{.69\columnwidth}@{}}
\toprule
Symbol & Meaning and unit\\
\midrule
$N,M,T$ & Outputs, base evaluators, candidate evaluators.\\
$k,S_0$ & Nominal count and baseline-selected set; $|S_0|$ need not equal $k$.\\
$H=MT$ & Number of single-member replacement scenarios.\\
$f_{ir},p_i$ & Entry's flip count and its row's maximum flip count.\\
$F_i$ & Full row cost $\sum_r f_{ir}$, in flips.\\
$b_H$ & Integer flip budget $\lfloor2k\alpha H\rfloor$.\\
$\ell_i,u_i$ & Lower and upper row costs, in flips.\\
$V^-,V^+,V^*$ & Safe, optimistic, and true optimal retained counts.\\
$\varepsilon$ & Allowed certified retained-count gap.\\
$Q_{\rm joint}$ & Minimum joint evidence under the stated query unit.\\
$Q_{\cup,\rm sep}$ & Minimum union over separately minimum proofs.\\
$Q_{\rm split}$ & Minimum sum of separate proof sizes.\\
\bottomrule
\end{tabular}
\caption{Core notation. In odd-median Boolean formulas, dividing by the nonzero flip cap gives opposition-count costs and budget $b$. A column query reveals and is charged for all $N$ score entries.}
\label{tab:notation}
\end{table}

\subsection{Flip geometry and sharp intervals}'''
edit('manuscript/appendix.tex',old,new)
(D/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
print('Applied',len(changes),'bounded replacements')

"""Integrate shared mean evidence into the existing certificate-complexity spine."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def once(s,old,new):
    assert s.count(old)==1,old[:80]
    return s.replace(old,new)

def main():
    p=ROOT/'manuscript/main.tex';s=p.read_text()
    s=once(s,r'The minimum entry-certificate formulas below apply to median Boolean costs; retained-count bounds and stopping apply to both pooling rules.',r'Median Boolean costs admit closed-form minima; for mean pooling, a joint evidence program below preserves queries that improve both bounds.')
    s=once(s,r'\section{Median Certificate Complexity}',r'\section{Minimum Certificate Complexity}')
    s=once(s,r'For $M=2h+1$ with nonnegative integer $h$, median selection',r'\paragraph{Median: disjoint evidence.}'+'\nFor $M=2h+1$ with nonnegative integer $h$, median selection')
    s=once(s,r'For $L<m$, exclusion requires the $p=L+1$ smallest observed opposition counts',r'The level $t^*$ is the smallest opposition cap that makes the cheapest $p$ rows exceed budget; it is distinct from the selection cutoff $t_0$. For $L<m$, exclusion requires the $p=L+1$ smallest observed opposition counts')
    marker=r'\paragraph{From entries to evaluator columns.}'
    joint=r'''\paragraph{Mean: shared evidence.}
An entry with true flip contribution $f_{ir}$ raises its row's lower cost by $f_{ir}$ and reduces its upper cost by $p_i-f_{ir}$. Mean pooling can have $0<f_{ir}<p_i$, so one query contributes to both proofs. Separately minimizing safety and exclusion and adding their sizes can overcount evidence.

For an existing history, let $\ell_i^0,u_i^0$ be its row bounds and $\mathcal D_i$ the attainable pairs $(a,v)$ of additional query count and revealed flip sum on row $i$. Choosing $(a_i,v_i)\in\mathcal D_i$ gives $\ell_i=\ell_i^0+v_i$ and $u_i=u_i^0-a_ip_i+v_i$. Write $L^*$ for the true optimal active count.
\begin{theorem}[Joint entry witness]
\label{thm:joint}
The minimum additional entry count for gap at most $\varepsilon$ is $\min\sum_i a_i$, over $s\in\{\max(0,L^*-\varepsilon),\ldots,L^*\}$, row states in $\mathcal D_i$ and a safe set $C$ of $s$ active rows satisfying $\sum_{i\in C}u_i\le b_H$. If $p=s+\varepsilon+1\le m$, also require an integer $0\le t\le TM$ such that
\[
 \sum_i(t-\ell_i)_+\le pt-b_H-1,
\]
where $(x)_+=\max(0,x)$. For $p>m$, exclusion is automatic.
\end{theorem}
The threshold condition excludes every $p$-row set. A row-state dynamic program computes the minimum and reconstructs the queried entries, including queries shared by both proofs (Appendix~\ref{app:joint-evidence}). It applies to both pooling rules under the same endpoint completion model and specializes to the median minima.

'''
    s=once(s,marker,joint+marker)
    # Move the exact median column detail to the existing full appendix exposition.
    start=s.index('The common offset $T-|A|$ gives both bound vectors')
    end=s.index('\n\nGiven observations',start)
    s=s[:start]+r'''The two sorted-prefix conditions characterize exact median column certificates (Appendix~\ref{app:granularity}). Their minima also depend on where evidence occurs: identical row costs can require different column counts.''' +s[end:]
    s=once(s,r'An acceptable replacement-average allowance of $\rho$ membership changes sets $\alpha=\rho/(2k)$; it gives no per-replacement bound.',r'An acceptable replacement-average allowance of $\rho$ membership changes sets $\alpha=\rho/(2k)$; for $k=10$, an allowance of two flips gives $\alpha=.10$. It gives no per-replacement bound.')
    s=once(s,r'under a churn budget for every consistent completion in a fixed replacement family.',r'under a churn budget for every consistent completion in a fixed replacement family. Weight-region ranking stability studies perturbations of scoring weights \citep{asudeh2018stable}; our perturbations replace evaluators and our certificate concerns retained count at a fixed cutoff.')
    # Clarify direct uncertainty-model differences without claiming general hardness.
    s=once(s,r'and robust selection \citep{goerigk2015robustqueries,chen2026selection}.',r'and robust selection \citep{goerigk2015robustqueries,chen2026selection}. Weight-query knapsack reveals an item\textquotesingle s weight; our entry reveals one contribution to a row\textquotesingle s multi-replacement cost.')
    s=once(s,r'For odd-sized median pools, agreements establish feasibility and oppositions exclude larger sets, yielding minimum entry certificates. Residual witnesses incorporate existing evidence and shared columns under fixed additive prices.',r'Median agreements and oppositions supply disjoint proofs. Mean queries can supply both proofs at once, so a joint row-state program characterizes their minimum evidence. Residual witnesses incorporate existing observations and shared columns under fixed additive prices.')
    p.write_text(s)
    a=ROOT/'manuscript/appendix.tex';s=a.read_text()
    text=r'''\subsection{Joint entry evidence beyond Boolean costs}
\label{app:joint-evidence}
Mean pooling changes how observations serve a certificate. For a selected row with base-score sum $S_i$, replacement of member $j$ flips membership when $x<Mt_0-(S_i-s_j(i))$. Thus $f_i(x)$ is an integer staircase, although scores are continuous. The two endpoint costs remain attainable, as required by Proposition~\ref{prop:stop}; attainable intermediate query outcomes can reduce both sides of the interval.

Consider two selected rows with identical base scores $(.1,.7,.9)$, cutoff $.5$ and one candidate scoring $.6$ on each row. Take $M=3$, $N=2$, $q=.5$, $k=1$ and $\alpha=1/6$, so $b_H=1$. Each row has $p_i=2$ and true cost one. No queries give $(V^-,V^+)=(0,2)$, one query gives $(1,2)$, and two give $(1,1)$. Safety requires one query and exclusion requires two, but their union requires two rather than three. This example identifies the evidence overlap absent from median boundary rows.

\paragraph{Attainable row states.}
For initial observations $\mathcal O$, let $U_i$ be the unobserved candidates on active row $i$. Define
\[
 \mathcal D_i=\left\{\left(|J|,\sum_{r\in J}f_{ir}\right):J\subseteq U_i\right\}.
\]
Initialize the row-state set with $(0,0)$. For each remaining candidate, retain existing states and add $(a+1,v+f_{ir})$ from each $(a,v)$. Store one witnessing subset for each pair. There are at most $(T+1)(Tp_i+1)$ pairs. The offline constructor uses the true contributions to build these states; the verifier subsequently sees only the chosen observations.

\begin{lemma}[Excluding a cardinality by one threshold]
\label{lem:order-threshold}
For nonnegative integer lower costs $\ell$ and $1\le p\le m$,
\[
 \sum_{j=1}^{p}\ell_{(j)}=
 \max_{t\in\{0,\ldots,TM\}}\left[pt-\sum_i(t-\ell_i)_+\right],
\]
provided every $\ell_i\le TM$.
\end{lemma}
\begin{proof}
For any $p$-row set $A$, the bracket is at most $\sum_{i\in A}\ell_i$: bounding each $(t-\ell_i)_+$ below by $t-\ell_i$ on $A$ proves this inequality. At $t=\ell_{(p)}$, all values below $t$ belong to the cheapest $p$ rows, while any remaining rows in that prefix equal $t$. The bracket therefore equals their sum. Integer costs make exceeding $b_H$ equivalent to reaching $b_H+1$.
\end{proof}

\paragraph{Proof of Theorem~\ref{thm:joint}.}
Any successful observation set has active safe count $s=V^--m_0$ in $[\max(0,L^*-\varepsilon),L^*]$, where $m_0$ is the invariant selected count. Its queried cells define row states, and a safe prefix supplies $C$. If $p=s+\varepsilon+1\le m$, optimistic count is at most $s+\varepsilon$, so the cheapest $p$ lower costs exceed $b_H$. Lemma~\ref{lem:order-threshold} supplies the required threshold. Thus every successful certificate appears in the minimization.

Conversely, witnessing row subsets produce the stated bounds. The safe-set constraint gives at least $s$ active retained outputs. The threshold condition gives optimistic active count at most $s+\varepsilon$; for $p>m$, that bound is automatic. Hence the count gap is at most $\varepsilon$. Each additional cell belongs to exactly one row, so its cost is counted once even when it improves both bounds. Minimizing constructs a certificate of exactly the minimum size. The proof uses independent endpoint attainability, not attainability of every integer between those endpoints.

\paragraph{Row-state dynamic program.}
For fixed $s,t$, put $D=pt-b_H-1$ and discard negative $D$. A state $(n,u,d)$ after a row prefix stores the minimum additional query count, where $n$ rows belong to the safe set, $u$ is their upper-cost sum and $d$ is the accumulated threshold deficit. Initialize $(0,0,0)$ with cost zero. For a row pair $(a,v)$ and a choice $y\in\{0,1\}$, update
\[
 \begin{aligned}
 n'&=n+y,\\
 u'&=u+y(u_i^0-ap_i+v),\\
 d'&=d+(t-\ell_i^0-v)_+,
 \end{aligned}
\]
adding query cost $a$. Keep $n'\le s$, $u'\le b_H$ and $d'\le D$. Read the minimum at $n=s$ and reconstruct its row subsets and safe set. For $p>m$, omit the deficit coordinate and threshold. Enumerate the permitted $s$ and thresholds to obtain Theorem~\ref{thm:joint}. No separately minimized safety or exclusion quantity is added in this recurrence.

Writing $R=\max_i|\mathcal D_i|$, the dense computation for fixed $s,t$ takes $O(mR(s+1)(b_H+1)(D+1))$ time and $O((s+1)(b_H+1)(D+1))$ working memory, apart from witness storage. The implementation stores reachable states. In the single-member family, $p_i\le M$ and row costs are at most $TM$. If $b_H\ge\sum_iTp_i$, zero queries suffice; otherwise $b_H<mTM$ and $D\le mTM$. Together with $R\le(T+1)(TM+1)$, these bounds make the algorithm polynomial in the explicit counts $m,T,M$, although the dense state space can be large. For generic integer contributions with binary-encoded large caps, the same budget-indexed algorithm is pseudo-polynomial. The existing median formulas provide a much smaller specialization.

\paragraph{Separate witnesses as a comparison.}
For each safe target $s$, independently minimize safety queries and exclusion queries for $p=s+\varepsilon+1$, then minimize their sum over the same target range. Call this value $Q_{\rm split}$. The union of these separately constructed witnesses is feasible because both bounds improve monotonically under additional observations. Therefore $Q_{\rm joint}\le Q_{\rm split}$. Equality holds for median boundary evidence under Proposition~\ref{prop:residual}; mean intermediate contributions can make the inequality strict.

'''
    marker='Starting with no other candidate test observations, fix entry price'
    s=once(s,marker,text+marker)
    s=once(s,r'Mean pooling can have several flip-count levels and different $p_i$ across rows, so the binary evidence construction does not directly apply.',r'Mean pooling can have several flip-count levels and different $p_i$ across rows; Theorem~\ref{thm:joint} handles their shared evidence without the median binary decomposition.')
    s=once(s,r'N--P analyze tolerance, operational scope and prediction diagnostics.',r'N--P analyze tolerance, operational scope and prediction diagnostics. M also develops joint mean evidence; P includes same-instance query interventions.')
    marker=r'\FloatBarrier'+'\n'+r'\section{Risk Scaling and Selection Objects}'
    equiv=r'''\paragraph{Transformations that preserve the task.}
For odd-sized median pooling, apply a common strictly increasing bijection $h:[0,1]\to[0,1]$ to every score and replace the cutoff by $h(t_0)$. Median order statistics commute with $h$, and cutoff membership is unchanged for every replacement. Transporting each unobserved score by $h$ gives a bijection of completion matrices, so flip costs and certificate minima are unchanged. Separate evaluator-wise ECDF refits are not such a common transformation. For mean pooling, the corresponding property holds for a common positive affine map $h(x)=ax+b$, $a>0$, with the cutoff and score-completion range transported together. A nonlinear common map need not commute with averaging. Thus mapping sensitivity compares different tasks unless this equivariance condition is met.

'''
    s=once(s,marker,equiv+marker)
    a.write_text(s)
if __name__=='__main__':main()

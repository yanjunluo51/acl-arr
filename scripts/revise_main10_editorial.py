"""Apply the reviewed editorial changes to the canonical manuscript."""
from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'review-revision/main10-implementation'
OLD = ROOT/'history/before-main10-editorial/manuscript'

def replace(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)

def paragraph(text, prefix, new):
    match = re.search(r'^'+re.escape(prefix)+r'.*?(?=\n\n|\Z)', text, re.M|re.S)
    assert match, prefix
    return text[:match.start()]+new+text[match.end():]

def main():
    pre = json.loads((OUT/'pre-edit-checks.json').read_text())
    assert pre['status'] == 'PASS_THREE_PRE_EDIT_CHECKS'
    m = (OLD/'main.tex').read_text()
    a = (OLD/'appendix.tex').read_text()
    m = replace(m, r'\title{How Many Evaluator Scores Certify a Stable NLP Selection?}',
                r'\title{How Many Scores Certify NLP Retention under a Churn Budget?}')
    m = paragraph(m, 'Evaluator changes can alter', r'''Evaluator changes can alter which language outputs are selected. We study how many scores certify near-optimal retention under a budget on membership changes averaged over a finite family of single-evaluator replacements. Fixed score maps and cutoff make each output's flip cost depend on its own scores. Partial observations bound the feasible retained count; the gap certifies shortfall from the full-information optimum. For odd-sized median pools, we characterize minimum offline entry certificates: at-or-above-cutoff agreements establish feasibility, and below-cutoff oppositions exclude larger sets. Residual certificates connect prior observations to mixed entry and whole-evaluator queries under fixed additive prices. RewardBench~2 and five WMT panels compare these minima with online discovery and protocol sensitivity. Zero-query retention can include noninvariant outputs within budget; with mean pooling, reference priority inspects 82.1--86.5\% of active entries at $q=.05$, $\alpha=.10$ and gap tolerance $\lceil.02|S_0|\rceil$. Controlled panels hold row costs fixed to isolate evidence sharing across columns. Quality diagnostics remain separate from churn guarantees, and score-information counts do not measure evaluator execution cost.''')
    m = paragraph(m, 'Reward models and translation metrics', r'''Reward models and translation metrics filter language outputs, but evaluator changes can alter the selected set \citep{malik2026rewardbench2,freitag2023wmt23,zheng2023judging}. We ask how many candidate scores must be observed to retain as many baseline-selected outputs as possible while certifying a bound on average membership changes. This is a selection guarantee; ensemble agreement alone does not establish output quality \citep{black2022selective,eisenstein2024herding}.''')
    m = paragraph(m, 'We first select a baseline', r'''We form the baseline list from reference-fitted score maps, base-pool consensus and a cutoff. The maps and cutoff remain fixed when one base evaluator is replaced by a candidate from a finite family. A commitment mask accepts baseline inclusion or exclusion decisions without review. We use the same mask for every replacement and maximize its returned baseline-selected count under an average churn budget.''')
    m = paragraph(m, 'Partial scores bound retained count', r'''Partial scores give a count feasible under every consistent completion and an upper bound on the full-information optimum. Their gap bounds retained-count shortfall. A minimum offline certificate is the smallest observation set establishing the required gap, chosen with knowledge of the true matrix. An online policy must discover sufficient evidence without seeing unqueried scores.''')
    m = paragraph(m, 'For odd-sized median pools, selected outputs', r'''For odd-sized median pools, a selected output can lose membership only at the voting boundary. Its flip cost is proportional to its below-cutoff candidate scores. At-or-above-cutoff agreements certify feasibility; below-cutoff oppositions exclude larger retained sets. This separation gives minimum certificates for exact and positive-gap stopping. Conditioning on prior observations links entry evidence to shared columns and mixed prices. NLP replays compare discovery orders with these minima; controlled panels vary evidence sharing at fixed row costs.''')
    m = replace(m, 'Optimistic profit-density prefixes support resource-augmented knapsack bounds. Here every returned output has unit value, and median replacement costs are Boolean opposition sums. Cost prefixes determine exact retained counts; cells or columns supply evidence.',
                'Each returned output has unit value. After rescaling, median flip costs are Boolean opposition sums, and sorted cost prefixes determine the optimal count. Entry or column queries must reveal enough evidence to certify that count or a specified gap.')
    m = replace(m, r'\section{Selection and Its Observable Risk}', r'\section{Selection under Evaluator Replacements}')
    m = replace(m, 'The true score matrix, maps and cutoff $0<t_0\\le1$ stay fixed during queries and replacements; candidate test scores may be unobserved.',
                'The true matrix, maps and cutoff $0<t_0\\le1$ remain fixed. Base scores are initially visible; candidate test scores are revealed through queries.')
    m = replace(m, 'This count sets the risk scale; $|S_0(P)|$ need not equal $k$.',
                'This count sets the risk scale, not a quota on the baseline or returned list.')
    m = replace(m, "For output $i$, its base scores and candidate $r$\\textquotesingle s score determine the number $f_{ir}$ of base-member replacements changing membership.",
                "Because the cutoff is fixed, output $i$'s base scores and candidate $r$'s score determine all $M$ replacement outcomes for that row. Let $f_{ir}$ count membership changes.")
    m = replace(m, 'Let $C$ contain outputs whose baseline inclusion or exclusion decisions are fixed without review. Holding $C$ fixed, we compare these decisions with membership under each replacement:',
                'The commitment mask $C$ records baseline decisions accepted without review. We evaluate this same mask under every replacement:')
    m = paragraph(m, 'A stopping certificate combines', r'''A stopping certificate uses fixed maps, visible base scores and revealed candidate test scores to verify churn-budget feasibility and a retained-count gap. Reference-fitted predictions guide acquisition but do not tighten the bounds. Each entry query reveals one candidate--output score and determines all $M$ replacement outcomes for that row.''')
    m = replace(m, 'Mean and median replacement consensus are nondecreasing in $x$. For selected outputs, $f_i(x)$ is nonincreasing, maximizing at zero and vanishing at one. For unselected outputs it is nondecreasing, maximizing at one and vanishing at zero.',
                'Under either pooling rule, replacement consensus is nondecreasing in $x$. For selected outputs, $f_i(x)$ is nonincreasing, with its maximum at $x=0$ and zero at $x=1$. For unselected outputs, it is nondecreasing, with its maximum at $x=1$ and zero at $x=0$.')
    m = replace(m, 'let $\\ell_i$ be their observed flip sum.', 'let $\\ell_i$ sum the flip counts determined by those observations.')
    m = replace(m, 'Set the safe count $V^-=V(u)$ and optimistic count $V^+=V(\\ell)$.',
                'The safe count $V^-=V(u)$ is feasible for every consistent completion; the optimistic count $V^+=V(\\ell)$ is attainable in at least one.')
    m = replace(m, 'The zero-flip endpoint assignment realizes $\\ell$; the maximum-flip assignment realizes $u$.',
                'Zero-flip endpoints jointly realize $\\ell$; maximum-flip endpoints jointly realize $u$.')
    m = replace(m, "Tight minimum-query formulas below use median\\textquotesingle s Boolean costs; mean retains the same safe/optimistic guarantee.",
                'The tight minimum-query formulas below use median Boolean costs; both pooling rules retain this count guarantee.')
    m = replace(m, 'A selected row with at least $h+2$ votes remains selected under every replacement. We call a selected row with exactly $h+1$ votes a boundary row, and a candidate below the cutoff reverses membership when it replaces any of those voters.',
                'A selected row with at least $h+2$ scores at or above the cutoff remains selected. A boundary row has exactly $h+1$ such scores. A below-cutoff candidate excludes it precisely when replacing one of those $h+1$ evaluators.')
    m = replace(m, 'Then $F_i=(h+1)z_i$. Boundary feasibility is exactly',
                'Each opposition causes $h+1$ flips, so $F_i=(h+1)z_i$. Measuring boundary costs in opposition units, feasibility is exactly')
    m = replace(m, 'Agreements (scores at or above the cutoff) lower upper costs; oppositions raise lower costs.',
                'An observed agreement reduces the upper cost bound by one; an opposition increases the lower bound by one.')
    m = replace(m, r'\paragraph{A minimal certificate.}', r'\paragraph{A minimum-size certificate.}')
    m = replace(m, 'Three agreements in the first row and one in the second give $(2,3)$. Revealing all three oppositions rules out the three-row set, giving $(2,2)$.',
                'The three agreements in row~1 and one in row~2 give $(2,3)$. The opposition in row~2 and two in row~3 exclude the three-row set, giving $(2,2)$.')
    m = replace(m, 'A truly feasible $L$-row set contains enough agreements to attain this bound. Oppositions cannot reduce its upper cost.',
                'Any $L$-row set feasible under the true costs contains enough agreements to attain this bound. Oppositions do not reduce its upper cost.')
    m = replace(m, 'and observes $t^*$ in every other row.', 'and reveals $t^*$ oppositions in every other row.')
    m = replace(m, 'With $L$ safe boundary rows, gap tolerance $\\varepsilon$ requires an optimistic count at most $L+\\varepsilon$. Thus evidence must exclude every $(L+\\varepsilon+1)$-row set, unless that size exceeds $m$.',
                'Let $s$ be the certified safe boundary count. Gap tolerance $\\varepsilon$ requires optimistic count at most $s+\\varepsilon$, so every $(s+\\varepsilon+1)$-row set must be excluded unless that size exceeds $m$.')
    # A bound-variable rename, confined to the positive-gap corollary.
    start, end = m.index(r'\begin{corollary}[Minimum gap witness]'), m.index(r'\end{corollary}')+len(r'\end{corollary}')
    block = m[start:end].replace(r'\mathcal L_\varepsilon', r'\mathcal S_\varepsilon')
    block = block.replace(r'\min_{L\in', r'\min_{s\in').replace('0,LT-b', '0,sT-b').replace('E(L+\\varepsilon+1)', 'E(s+\\varepsilon+1)')
    m = m[:start]+block+m[end:]
    m = replace(m, 'For the same instance, budget, completion model and tolerance, these minima lower-bound unit-cost entry queries from no prior candidate-test observations.',
                'These minima lower-bound unit-cost entry queries starting with no observed candidate test scores, for the same instance, budget, completion model and tolerance.')
    m = replace(m, 'Both vectors have the same row ordering because their offset is common to all rows.',
                'The common offset $T-|A|$ gives both bound vectors the same row ordering.')
    m = replace(m, 'Matrices with identical row costs can require different numbers of columns because evidence locations differ.',
                'Identical row costs give the same minimum entry-certificate size, but column minima also depend on where the evidence occurs.')
    m = paragraph(m, 'Conditioning agreement and opposition requirements', r'''Given observations $\mathcal O$, the residual witness $Q_\varepsilon(\mathcal O)$ counts the minimum additional entries needed (Appendix~\ref{app:residual}). Starting without other candidate test observations, let entries cost $\tau>0$ and columns have fixed prices $c_r>0$. Columns $A$ reveal $\mathcal O_A$. The minimum offline mixed cost is $\min_{A\subseteq[T]}\{\sum_{r\in A}c_r+\tau Q_\varepsilon(\mathcal O_A)\}$, assuming additive prices independent of query order.''')
    m = replace(m, 'All strategies use the same interval updates and safe-mask solver.',
                'The four strategies differ only in their next-query rule; interval updates, mask solver and stopping criterion are shared.')
    m = replace(m, 'Among active rows with unqueried entries, reference priority chooses the smallest estimated total cost: observed flips plus predictions for remaining entries.',
                'Reference priority first selects the active row with the smallest estimated total flip cost, summing observed flips and predictions for unqueried entries.')
    m = replace(m, 'We establish no minimum-query guarantee for these heuristics.', 'We provide no query-optimality or competitive guarantee for these heuristics.')
    m = replace(m, 'Recompute the safe mask and the two retention frontiers.', 'Recompute the safe mask and the safe and optimistic retained counts.')
    m = replace(m, r'\subsection{Panels and protocol}',
                'The experiments compare initial retention, online discovery and minimum evidence, then vary the selection protocol and query unit.\n\n'+r'\subsection{Panels and protocol}')
    m = replace(m, 'A twelve-stream variant removes the output named \\texttt{synthetic\\_ref} before refitting the protocol. All source segments remain; the output population and fitted score maps change.',
                'A twelve-stream variant removes \\texttt{synthetic\\_ref} before refitting maps and cutoff. Source segments remain, but the output population and selection protocol change.')
    m = replace(m, 'fitted on reference outputs.', 'fitted on all outputs in the reference split.')
    m = replace(m, '$n_{\\rm ref}$ counts reference outputs', '$n_{\\rm ref}$ counts outputs in that split')
    m = replace(m, 'The primary stop is $V^+-V^-\\le\\lceil.02|S_0(P)|\\rceil$, measured in retained outputs; exact stopping uses zero gap.',
                'The primary stop uses integer gap $\\varepsilon=\\lceil.02|S_0(P)|\\rceil$: the nominal 2\\% fraction is rounded up to whole outputs. Exact stopping uses zero gap.')
    m = replace(m, 'Counts exclude the earlier full-panel WMT23 correlation check and describe information use after panel construction.',
                'Counts begin after panel construction, excluding the WMT23 correlation check that reads the full panel; they do not measure savings from the start of preparation.')
    m = replace(m, 'Zero-query coverage includes both structural invariance and budget-admissible uncertainty.',
                'Zero-query retention includes invariant outputs and noninvariant outputs whose worst-case costs fit the budget.')
    m = replace(m, 'zero-query stopping instead tests the initial gap', 'zero-query stopping rate is instead the fraction of splits whose initial gap meets the tolerance')
    m = paragraph(m, 'Envelope CRC calibrates', r'''Envelope CRC calibrates a threshold on loss $d_i=F_i/H$, using $B=N/(2k)$ and correction $B\lambda$ \citep{yeh2025conformal}. Its expectation guarantee permits batch violations. If its threshold is batch feasible, the best feasible threshold in the same nested family retains at least as many decisions (Appendix~\ref{app:baselines}).''')
    m = replace(m, r'\paragraph{Calibration and scoring workload.}', r'\paragraph{A calibrated same-loss comparison.}')
    m = replace(m, 'Median reference priority inspects', 'Reference priority with median pooling inspects')
    m = replace(m, 'Mean reference priority inspects', 'With mean pooling, reference priority inspects')
    m = replace(m, 'On thirteen-stream WMT23 mean, it rises', 'On thirteen-stream WMT23 with mean pooling, it rises')
    m = replace(m, 'Table~\\ref{tab:certificates} compares exact online inspection with Theorem~\\ref{thm:exact}\\textquotesingle s offline witness.',
                'Table~\\ref{tab:certificates} switches to exact stopping to compare online inspection with the matching minimum from Theorem~\\ref{thm:exact}.')
    m = replace(m, 'Agreements can dominate when', 'Agreement observations can dominate certificate size when')
    m = replace(m, 'Among splits with $Q_{\\rm exact}>0$,', 'At $q=.05$, $\\alpha=.10$, among splits with $Q_{\\rm exact}>0$,')
    m = replace(m, 'Exact witnesses describe required agreement and opposition evidence; online counts also depend on its discovery order.',
                'Required evidence and discovery order both affect inspection. Exact and positive-gap minima concern their respective stopping targets.')
    m = replace(m, 'split-mean reference active inspection has a median', 'the 40-split mean active inspection for each pool has a median')
    m = replace(m, 'We fixed the risk objective and panel-inclusion criteria before inspecting WMT24 results.',
                'Before inspecting WMT24 results, we fixed the risk objective and panel-inclusion criteria. A query-priority tie rule was repaired later after an exact-replay failure (Appendix~\\ref{app:review-quality}).')
    m = replace(m, 'The same four acquisition rules, features, depths and stopping criteria run at $\\alpha=.10$ on 960 configurations. Appendix~\\ref{app:review-quality} discloses a numerical tie-handling repair made after an exact-replay failure.',
                'Three panels, two pooling rules, four $q$ values and 40 splits define 960 configurations at $\\alpha=.10$, each evaluated with all four acquisition rules.')
    moved = 'At $q=.05$ and $\\varepsilon=\\lceil.10|S_0|\\rceil$, reference mean inspection is 72.4--76.2\\% across all six panels (Appendix~\\ref{app:tolerance}).'
    m = replace(m, ' '+moved, '')
    marker = r'\subsection{Budget and evaluator composition}'
    m = replace(m, marker, 'At $q=.05$, relaxing nominal count tolerance to $.10$ still leaves reference priority with mean pooling querying 72.4--76.2\\% of active entries across all six panels (Appendix~\\ref{app:tolerance}).\n\n'+marker)
    m = replace(m, 'Count-matched comparisons have differences of either sign and concern observed labels only;',
                'Both total-count-matched and annotated-count-matched MQM comparisons have differences of either sign and concern observed labels only;')
    m = replace(m, 'Source-only and reference-only Sentinel probes', 'WMT24 source-only and reference-only Sentinel probes')
    m = replace(m, 'Six protocols combine full, half or quarter reference groups', 'Six protocols combine all, half or one quarter of reference groups')
    m = replace(m, 'Baseline-set Jaccard is 0.77: mapping changes the selection task',
                'Jaccard similarity between the two baseline selected sets is 0.77, so the reduced inspection applies to a changed selection task')
    m = replace(m, 'Entry paths access all seven candidates. Exact median column witnesses average',
                'These fractions divide by all $NT$ candidate scores, not $mT$ active entries; entry paths touch all seven candidates. For the separate exact target with median pooling, minimum column witnesses average')
    m = replace(m, 'cyclic and all eight independent layouts need twelve', 'the cyclic layout and all eight tested independent layouts need twelve')
    m = paragraph(m, 'Agreements and oppositions characterize minimum median certificates.', r'''Certification cost separates the evidence required by a retained-count target from the cost of discovering it. Median agreements establish feasibility; oppositions exclude larger sets. Shared evidence can change minimum column counts even at fixed row costs. NLP replays show why low inspection must be interpreted alongside initial retention and the selection protocol. These results certify count under a churn budget; quality and execution costs require separate evidence.''')
    m = replace(m, 'Dataset sources and acquisition instructions are documented in \\texttt{DATA\\_STATEMENT\\_CURRENT.md}, available in the local source/code packages; Appendix~\\ref{app:review-quality} identifies the acquisition record.',
                'Appendices~\\ref{app:protocol} and~\\ref{app:review-quality} document data sources and acquisition; the prepared source/code packages contain \\texttt{DATA\\_STATEMENT\\_CURRENT.md}.')

    # The old abstract terminator shares its paragraph; retain the environment.
    m = m.replace('\\section{Introduction}', '\\end{abstract}\n\n\\section{Introduction}')

    # Appendix: preserve mathematics while making evidence, units and protocol
    # transitions explicit. Unresolved release/checkpoint facts are retained.
    a = replace(a, 'A scalar cutoff includes all ties.', 'Our cutoff rule includes scores equal to the threshold.')
    a = replace(a, 'every reference score maps into', 'every score in the reference split maps into')
    a = replace(a, 'Known candidate functions, score correlations and raw-score restrictions are not used to reduce the completion set.',
                'The declared completion set does not encode additional constraints from evaluator functions, score correlations or raw-score support. Sharpness is relative to this set.')
    numerical = re.search(r'^The replay rebuilds replacement score vectors.*?(?=\n\n)', a, re.M|re.S).group()
    a = replace(a, numerical+'\n\n', '')
    a = replace(a, r'\label{app:protocol}', r'\label{app:protocol}'+'\n'+r'\paragraph{Numerical consistency.}'+'\n'+numerical+'\n\n'+r'\paragraph{Panel construction.}')
    a = replace(a, 'the target has infinite witness cost.', 'this infeasible target is represented by infinite certificate cost.')
    a = replace(a, 'Since $x_i\\le z_i$ for every row, the sorted values satisfy $x_{(i)}\\le z_{(i)}$. Let $t=x_{(p)}$.',
                'Rowwise inequalities $x_i\\le z_i$ imply order-statistic inequalities $x_{(j)}\\le z_{(j)}$ for every $j$. Let $t=x_{(p)}$, the $p$-th smallest observed count.')
    a = replace(a, 'Assign observed counts to the first $p$ rows between zero and', 'Assign integer observed counts to the first $p$ rows between zero and')
    a = replace(a, ' These counts are integers.', '')
    a = replace(a, 'An adversary can reply to the first $T-1$ queries with exactly $b$ oppositions.',
                'An adversary can arrange the first $T-1$ replies to contain exactly $b$ oppositions in total.')
    start = a.index(r'\subsection{Minimum witnesses at positive retention tolerance}')
    end = a.index(r'\subsection{A complete certificate example}')
    block = a[start:end]
    # Rename only unstarred L in this proof; keep L* as the true optimum.
    block = block.replace('L^*', '__OPTIMUM__')
    block = re.sub(r'\bL\b', 's', block).replace('__OPTIMUM__', 'L^*')
    a = a[:start]+block+a[end:]
    a = replace(a, 'Table~\\ref{tab:worked-example} uses bit units for the row bounds.',
                'Table~\\ref{tab:worked-example} reports $\\ell/4$ and $u/4$ in opposition-count units.')
    a = replace(a, 'Exhaustive enumeration of all $2^9=512$ observation subsets',
                'Enumerating all $2^9=512$ subsets of the nine observable entries in this fixed matrix')
    a = replace(a, 'Aligned records use native order: chosen completion first, then three rejected completions.',
                'Aligned records retain native order: the chosen completion followed by three rejected completions. Selection ties use the separate label-blind priorities below.')
    tie_start = a.index('In contrast to the seeded priorities above, fixed-count control')
    tie_end = a.index(' Reindexing carries', tie_start)
    tie = a[tie_start:tie_end]
    a = a[:tie_start]+a[tie_end:]
    a = replace(a, r'\end{itemize}', r'\end{itemize}'+'\n\n'+r'\paragraph{Fixed-count tie convention.}'+'\n'+tie)
    a = replace(a, 'For each policy, overall coverage is $|C|/N$',
                'For each policy, commitment coverage is $|C|/N$ (including committed exclusions)')
    a = replace(a, 'Structurally zero-cost nonselected items are committed for free.',
                'Nonselected outputs with $p_i=0$ are also committed, at zero churn cost.')
    a = replace(a, 'The total cost of all items at or below it', 'The total cost of all selected and unselected outputs at or below it')
    a = replace(a, 'The expectation control computes', 'The CRC expectation control uses fully observed candidate scores to compute')
    a = replace(a, 'The subsequent control tables separate policy-specific selected coverage from preference precision across every depth and pooling rule.',
                'The subsequent controls report selected coverage relative to each control\'s own baseline, separately from preference precision, across all nominal selection fractions and pooling rules.')
    a = replace(a, 'Since $K$ cannot exceed the base cutoff list size, this top-$K$ comparator is also a within-cutoff list.',
                'The comparator uses the same consensus and $K\\le|S_0|$, so its top-$K$ outputs lie within the baseline cutoff list.')
    a = replace(a, 'The diagnostic was specified after the inspection protocol', 'The diagnostic was specified after fixing the inspection protocol')
    a = replace(a, 'The official archive matches all 173,784 entries of the frozen 24-metric, 557-segment, thirteen-stream score panel.',
                'The official metric scores agree numerically with all 173,784 metric-score entries of the frozen 24-metric, 557-segment, thirteen-stream panel.')
    a = replace(a, 'Its MQM mean is compared with', 'The returned annotated subset\'s MQM mean is compared with')
    a = replace(a, 'prevents population quality conclusions.', 'prevents extending these MQM comparisons to all returned outputs.')
    a = replace(a, 'An independent checker rebuilds labels', 'A separate implementation rebuilds labels')
    a = replace(a, 'We sample 20 distinct seven-member pools, excluding the original pool as a complete combination while allowing its members in other combinations.',
                'We sample 20 distinct seven-member pools other than the original pool. Its individual evaluators remain eligible for the sampled pools.')
    a = replace(a, 'the complement is not asserted to contain exclusively learned metrics.', 'the remaining group is not restricted to learned metrics.')
    a = replace(a, 'every simple order', 'all four acquisition strategies')
    a = replace(a, 'The second term measures the share of noninvariant outputs retained within the average churn budget; it does not establish invariance.',
                'The second term divides retained noninvariant outputs by all baseline-selected outputs, not by the noninvariant subset. It measures budget-admissible retention, not invariance.')
    a = replace(a, 'The local source/code packages contain', 'The prepared source/code packages contain')
    a = replace(a, 'A hosting update does not change the declared data release. Its WMT24 score files label paragraph granularity as',
                'The analysis uses the archive\'s WMT24 release files despite the updated host. In those files, paragraph granularity is labeled')
    a = replace(a, 'System-name metadata excludes all human reference outputs; all other common systems remain, including benchmark outliers.',
                'Using system-name metadata, we exclude human references as outputs and retain other MT systems common to the admitted metrics, including benchmark outliers.')
    a = replace(a, 'the second forms unused calibration', 'the second forms a reserved calibration split not used by these WMT24 query experiments')
    a = replace(a, 'Candidate order uses the per-cell ticks and candidate index; row ties use the frozen item order. Rounding precedes integer summation.',
                'Within the chosen row, candidates are ordered by decreasing predicted upper-cost reduction from the rounded per-cell values; candidate index breaks ties. Row ties use the frozen item order. Each value is rounded before summation.')
    a = replace(a, 'the $J$ annotated returned outputs', 'the $J$ annotated returned outputs ($J$ has the same meaning as $K_{\\rm lab}$ in Appendix~\\ref{app:quality})')
    a = replace(a, 'Neither comparator has a stability certificate.', 'Neither comparator is constructed under the churn-budget constraint.')
    a = replace(a, 'unequal gold scores', 'unequal MQM scores')
    a = replace(a, r'\section{Replacement-Wise Diagnostics}', r'\section{Variation across Individual Replacements}')
    a = replace(a, 'Their splitwise means describe variation across replacements, without a per-replacement guarantee.',
                'We average each split\'s maximum and exceedance fraction separately. These are descriptive diagnostics; only replacement-average churn is constrained.')
    a = replace(a, 'A group acceptance decision $\\psi(U)$ commits its selected outputs together, and structurally zero-cost decisions can be added for free.',
                'The group decision $\\psi(U)$ accepts or rejects its baseline-selected outputs jointly. Structurally invariant decisions may additionally be committed at zero churn cost.')
    a = replace(a, 'Among 4,800 fixed-panel records, 70 exceed their batch budget. These exceedances alone do not contradict an expectation guarantee.',
                'Of 4,800 panel-and-budget records, 70 have realized batch churn above their specified budget. The records reuse panels, so this is not a frequency estimate from 4,800 independent samples. These exceedances do not by themselves contradict the expectation guarantee.')
    a = replace(a, 'The 40 independently refitted splits are not such a deployment sequence.',
                'The 40 separately refitted, overlapping splits do not form such a deployment sequence.')
    a = replace(a, 'share $L=0$ and $Q_{\\rm exact}=2$, but have column costs one and two.',
                'share $L=0$ and $Q_{\\rm exact}=2$, but have minimum column counts one and two.')
    a = replace(a, 'The capacity under upper costs equals $L$ exactly when its cheapest $L$-row prefix is feasible.',
                'Since upper-cost capacity cannot exceed the true optimum $L$, it equals $L$ exactly when the cheapest $L$-row upper-cost prefix is feasible.')
    a = replace(a, 'The integer condition supplies an exact finite enumeration for these panels.',
                'For these candidate counts, we compute exact column minima by enumerating subsets and testing Proposition~\\ref{prop:column-condition}.')
    a = replace(a, 'The full costs constrain which sets can be made safe, while the existing agreements determine how much evidence remains.',
                'In this offline minimization, true costs restrict the sets to those actually feasible. Existing agreements determine the additional evidence needed for each such set.')
    a = replace(a, 'Ordered values $v_{(j)}(t)$ are recomputed at each level.',
                'At each level $t$, the values $v_i(t)$ are sorted anew; this order need not match the true-cost order.')
    a = replace(a, 'Replacing them by $v_i(t)$ can raise each of their cheapest $p$ counts, while keeping other counts at least $t$. Hence the resulting $p$-prefix sum is at least $B$, so $t\\ge\\lambda_p$.',
                'For $w_i\\le t$, we have $v_i(t)\\ge w_i$ because $o_i\\le w_i\\le z_i$; for $w_i>t$, $v_i(t)\\ge t$. Thus $v_i(t)\\ge\\min(w_i,t)$ rowwise. Since $t=w_{(p)}$, truncating at $t$ preserves the sum of the $p$ smallest counts. Their sum cannot decrease when $\\min(w,t)$ is replaced by $v(t)$, so it remains at least $B$, implying $t\\ge\\lambda_p$.')
    a = replace(a, 'along the current cheapest $p$-row frontier', 'among the current $p$ smallest row counts')
    a = replace(a, 'For a fixed positive entry price $\\tau$ and positive column prices $c_r$,',
                'Starting with no other candidate test observations, fix entry price $\\tau>0$ and column prices $c_r>0$.')
    # Adjust grammar after replacing the lead-in comma with a full sentence.
    a = replace(a, '$c_r>0$. let $\\mathcal O_A', '$c_r>0$. Let $\\mathcal O_A')
    a = replace(a, 'To prove this, remove entry actions covered by a purchased column and reorder the remaining actions with columns first.',
                'Under these additive, order-independent prices, remove entry actions already covered by a purchased column and place the column actions first.')
    a = replace(a, 'minimum certificates still require a large fraction of scores',
                'minimum whole-column certificates still reveal a large fraction of candidate test scores')
    a = replace(a, 'In 30 of the 3,840 nonuniform-price records, the minimum-cost witness uses more columns than the minimum-count witness.',
                'Cost ties are resolved by minimizing column count. In 30 of the 3,840 nonuniform-price records, even the fewest-column minimum-cost witness uses more columns than the minimum feasible count. Enumerating all same-price subsets in these 30 records confirms this secondary minimum.')
    a = replace(a, 'a five-column ascending-price optimum of 55 scaled units',
                'a five-column ascending-price optimum with raw price 55, or $55/13$ after normalization')
    a = replace(a, 'minimizing the number of calls and minimizing their cost', 'minimizing column count and minimizing additive query cost')
    a = replace(a, 'For every positive-query stop, its predecessor must have a gap exceeding the tolerance.',
                'For each stopping state reached after at least one query, the immediately preceding state must have a gap greater than the tolerance.')
    a = replace(a, 'reference median acquisition on RewardBench', 'reference priority with median pooling on RewardBench')
    a = replace(a, 'These reductions trade retained count for information, rather than improving the same exact target.',
                'These reductions relax the retained-count target rather than reduce queries for the same exact-certification problem.')
    a = replace(a, 'Mean acquisition remains costly across the tolerance grid.',
                'With mean pooling, reference priority still queries a large fraction of active entries across the tolerance grid.')
    a = replace(a, 'reference mean inspection across the six panels', 'reference-priority active inspection across the six panels')
    a = replace(a, 'because its target is $Q_{\\varepsilon_\\eta}$.', 'because the matching minimum is $Q_{\\varepsilon_\\eta}$ for target gap $\\varepsilon_\\eta$.')
    a = replace(a, 'Savings relative to exact stopping are undefined for an exact path requiring zero queries.',
                'Relative query savings, normalized by the exact-stopping count, are undefined when that count is zero.')
    a = paragraph(a, 'Choose the query unit from the scoring interface.', r'''Choose the query unit supported by the scoring interface: entries target individual outputs, whereas columns reveal all $N$ scores. For an operational comparison, include reference fitting, base scores, preprocessing, calibration when used and certificate computation. The accounting boundary is specified in Appendix~\ref{app:protocol}; deployment claims require measured execution costs.''')
    a = replace(a, 'If an independently specified content or calibrated acceptance rule gives an eligible set $A_{\\rm cal}$ before certification,',
                'If a content or calibrated acceptance rule fixes an eligible set $A_{\\rm cal}$ that is visible before certification,')
    a = replace(a, 'Initial row-total alignment is the Spearman correlation', 'Initial row-total rank correlation is the Spearman correlation')
    a = replace(a, 'It diagnoses surviving rows rather than giving an unbiased initial error or a causal explanation of query cost.',
                'The error concerns row-total estimates on rows with unqueried entries, normalized by the full row scale $Tp_i$. It is not an unbiased initial error or a causal explanation of query cost.')
    a = replace(a, 'Median excess entry queries are', 'For median pooling, excess entry queries are')
    a = replace(a, '; mean has no corresponding witness formula here.', '; no corresponding witness formula is derived here for mean pooling.')
    a = replace(a, r'\subsection{What the full-path results explain}', r'\subsection{Prediction Accuracy and Observed Query Cost}')
    a = replace(a, 'On thirteen-stream WMT23 mean,', 'On thirteen-stream WMT23 with mean pooling,')
    a = replace(a, 'Initial row-total alignment alone is insufficient to choose the most economical rule.',
                'Initial row-total rank correlation alone does not identify the rule with the fewest queries in these configurations.')
    a = replace(a, 'At RewardBench median $q=.05$,', 'On RewardBench with median pooling at $q=.05$,')
    a = replace(a, 'Candidate-level upper-cost reduction, observed replies and which rows matter to the gap also enter the path.',
                'Query choices also depend on candidate-level predicted upper-cost reductions and observed replies; stopping depends on which rows determine the count bounds.')
    # Avoid multiple labels for the two counts in prose (not figure filenames).
    for old, new in [('retention frontiers', 'retained-count bounds'),
                     ('both frontiers', 'both count bounds'),
                     ('saved stopping frontier', 'saved stopping count bounds')]:
        m = m.replace(old, new); a = a.replace(old, new)
    # Remove repetition to preserve the eight-page technical main without
    # changing font, spacing, mathematical assumptions or result values.
    m = replace(m, 'Zero-query retention can include noninvariant outputs within budget; with mean pooling, reference priority inspects 82.1--86.5\\% of active entries at $q=.05$, $\\alpha=.10$ and gap tolerance $\\lceil.02|S_0|\\rceil$.',
                'At nominal 5\\% selection, budget $.10$ and a 2\\% count tolerance rounded up to whole outputs, reference priority with mean pooling inspects 82.1--86.5\\% of active entries.')
    m = replace(m, 'We form the baseline list from reference-fitted score maps, base-pool consensus and a cutoff. The maps and cutoff remain fixed when one base evaluator is replaced by a candidate from a finite family. A commitment mask accepts baseline inclusion or exclusion decisions without review. We use the same mask for every replacement and maximize its returned baseline-selected count under an average churn budget.',
                'Reference-fitted maps, base-pool consensus and a cutoff define the baseline list. Maps and cutoff stay fixed under single-evaluator replacements from a finite candidate family. One commitment mask accepts baseline decisions without review across every replacement. We maximize its returned baseline-selected count under an average churn budget.')
    m = replace(m, 'For odd-sized median pools, a selected output can lose membership only at the voting boundary. Its flip cost is proportional to its below-cutoff candidate scores. At-or-above-cutoff agreements certify feasibility; below-cutoff oppositions exclude larger retained sets. This separation gives minimum certificates for exact and positive-gap stopping. Conditioning on prior observations links entry evidence to shared columns and mixed prices. NLP replays compare discovery orders with these minima; controlled panels vary evidence sharing at fixed row costs.',
                'For odd-sized median pools, only boundary outputs can lose membership. Their flip costs count below-cutoff candidate scores up to a fixed factor. At-or-above-cutoff agreements certify feasibility; below-cutoff oppositions exclude larger sets. This separation yields minimum entry certificates. Residual witnesses incorporate prior observations and shared columns. NLP replays compare discovery with these minima; controlled panels vary sharing at fixed row costs.')
    m = replace(m, 'Each returned output has unit value. After rescaling, median flip costs are Boolean opposition sums, and sorted cost prefixes determine the optimal count. Entry or column queries must reveal enough evidence to certify that count or a specified gap.',
                'Here unit-valued outputs have rescaled Boolean opposition costs; sorted prefixes determine optimal count. Entry or column observations certify this count or a specified gap.')
    m = replace(m, 'The experiments compare initial retention, online discovery and minimum evidence, then vary the selection protocol and query unit.',
                'We compare initial retention, discovery and minimum evidence, then vary protocol and query unit.')
    m = replace(m, 'Counts begin after panel construction, excluding the WMT23 correlation check that reads the full panel; they do not measure savings from the start of preparation.',
                'Counts start after panel construction, excluding full-panel WMT23 correlation reads.')
    m = replace(m, 'zero-query stopping rate is instead the fraction of splits whose initial gap meets the tolerance',
                'zero-query stopping rate counts splits whose initial gap meets the tolerance')
    m = replace(m, 'Table~\\ref{tab:certificates} switches to exact stopping to compare online inspection with the matching minimum from Theorem~\\ref{thm:exact}. Agreement observations can dominate certificate size when nearly all boundary rows must be retained; oppositions prove that no larger retained set is feasible.',
                'Table~\\ref{tab:certificates} compares exact stopping with its matching minimum (Theorem~\\ref{thm:exact}). Agreements can dominate when nearly all boundary rows must be retained; oppositions exclude larger sets.')
    tol = 'At $q=.05$, relaxing nominal count tolerance to $.10$ still leaves reference priority with mean pooling querying 72.4--76.2\\% of active entries across all six panels (Appendix~\\ref{app:tolerance}).'
    m = replace(m, tol+'\n\n', '')
    anchor = 'Low median query counts thus coincide with high initial coverage.'
    m = replace(m, anchor, anchor+'\n\nAt $q=.05$, relaxing nominal count tolerance to $.10$ leaves reference priority with mean pooling querying 72.4--76.2\\% of active entries across all six panels (Appendix~\\ref{app:tolerance}).')
    m = replace(m, 'These fractions divide by all $NT$ candidate scores, not $mT$ active entries; entry paths touch all seven candidates. For the separate exact target with median pooling,',
                'Fractions use $NT$, not $mT$; entries touch all seven candidates. Separately, for exact median stopping,')
    m = replace(m, 'Certification cost separates the evidence required by a retained-count target from the cost of discovering it. Median agreements establish feasibility; oppositions exclude larger sets. Shared evidence can change minimum column counts even at fixed row costs. NLP replays show why low inspection must be interpreted alongside initial retention and the selection protocol. These results certify count under a churn budget; quality and execution costs require separate evidence.',
                'Required evidence and its discovery determine certification cost. Median agreements establish feasibility; oppositions exclude larger sets. Sharing changes minimum column counts at fixed row costs. NLP query counts must be interpreted with initial retention and protocol. Count guarantees, quality and execution costs concern separate evidence.')

    m = replace(m, 'Predictions affect query order, not interval bounds, so inaccurate predictions or correlated candidate scores do not invalidate the certificate. We provide no query-optimality or competitive guarantee for these heuristics. Retention-gap reduction need not have diminishing returns, so adaptive-submodular guarantees do not apply without further assumptions (Appendix~\\ref{app:proofs}).',
                'Predictions guide order, not bounds. These heuristics have no query-optimality guarantee; the gap need not have diminishing returns (Appendix~\\ref{app:proofs}).')
    m = replace(m, 'At fixed $\\alpha=.10$, composition sensitivity samples 20 distinct seven-member pools per panel, using all remaining evaluators as candidates. Each WMT23 panel also has a metadata-defined pool with three surface-overlap metrics and four others. For thirteen-stream WMT23 median at $q=.05$, the 40-split mean active inspection for each pool has a median of \\compWmtMedianActive\\% across pools and descriptive 10th--90th percentiles of \\compWmtMedianLow--\\compWmtMedianHigh\\%. Changing the pool changes the replacement family and selected set; cutoff and priorities are refitted for each pool (Appendix~\\ref{app:review-composition}).',
                'At $\\alpha=.10$, we sample 20 seven-member pools per panel and test a metadata-defined WMT23 pool. For thirteen-stream WMT23 median at $q=.05$, pool-wise 40-split mean inspection has median \\compWmtMedianActive\\% and descriptive 10th--90th percentiles \\compWmtMedianLow--\\compWmtMedianHigh\\%. Refitting each pool changes the replacement family and selected set (Appendix~\\ref{app:review-composition}).')
    m = replace(m, 'Both pooling rules run at $q\\in\\{.05,.10,.20,.30\\}$, with main budget $\\alpha=.10$ and sensitivity at $.02,.05,.15,.20$. Query orders are reused across budgets, with separate stopping states (Appendix~\\ref{app:review-composition}).',
                'Both pooling rules use $q\\in\\{.05,.10,.20,.30\\}$ and budgets $\\alpha\\in\\{.02,.05,.10,.15,.20\\}$ (primary $.10$). Orders are shared across budgets; stops are separate.')
    m = replace(m, 'Within each group, it jointly accepts or rejects the baseline-selected outputs. Its expectation guarantee assumes conditional whole-group exchangeability. Appendix~\\ref{app:review-score} gives the reduction and scoring costs; it is not applied to unequal-size WMT24 documents.',
                'It accepts or rejects selected outputs jointly within a group, assuming conditional whole-group exchangeability. Appendix~\\ref{app:review-score} gives costs and the reduction; unequal-size WMT24 documents are excluded.')
    m = replace(m, 'These differences do not support improved preference precision. Appendix~\\ref{app:quality} reports all strategies and depths.',
                'These differences do not support improved precision (Appendix~\\ref{app:quality}).')
    m = replace(m, 'Required evidence and discovery order both affect inspection. Exact and positive-gap minima concern their respective stopping targets.',
                'Evidence requirements and discovery order both affect inspection; each minimum concerns its own stopping target.')

    assert 'sum of squared residuals' in m
    assert '55 scaled units' not in a and '70 have realized batch churn' in a
    assert 'can raise each' not in a and 'independently refitted' not in a
    (ROOT/'manuscript/main.tex').write_text(m)
    (ROOT/'manuscript/appendix.tex').write_text(a)
    print(json.dumps({'status':'EDITORIAL_SOURCE_WRITTEN','new_model_scoring':False,'new_theory_claim':False}))

if __name__ == '__main__':
    main()

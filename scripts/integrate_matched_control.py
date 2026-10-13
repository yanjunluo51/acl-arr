"""Report the verified paired control and remove redundant main-text prose."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/html-review-implementation'
def main():
    check=json.loads((ROOT/'outputs/matched-tie-control/independent-check.json').read_text())
    assert check['status']=='PASS_SCOPED_MATCHED_TIE_CONTROL'
    m=(ROOT/'manuscript/main.tex').read_text();a=(ROOT/'manuscript/appendix.tex').read_text()
    start=a.index(r'\paragraph{Fixed-count tie convention.}');end=a.index('The CRC expectation control',start)
    a=a[:start]+r'''\paragraph{Native and matched fixed-count controls.}
The original control selects the $k$ largest consensus--item-index keys in the baseline and every replacement. Its historical results remain unchanged. A prior 320-configuration RewardBench audit inspected baseline lists only. We now additionally recompute full-information controls on all six panels, both pooling rules, four depths and 40 splits: 1,920 paired configurations at $\alpha=.10$.

The matched control orders every baseline and complete-batch replacement by decreasing consensus, then increasing the same seeded label-blind priority used by the retention solver. It refits neither maps nor cutoff and changes no query path. We recompute membership flips, maximum-retention masks, own-baseline coverage, average and replacement-specific churn. Labels are not loaded. Table~\ref{tab:matched-tie-control} gives all configurations; \nolinkurl{outputs/matched-tie-control/} supplies masks and per-split records.

Relative to native ties, 452 baseline lists and 453 retained sets change; replacement memberships change in 1,869 configurations. Returned count changes in only one configuration, by one output, but average churn changes in 1,435. The sign of fixed-count-minus-frozen returned count is unchanged in all 1,920 configurations. Thus count ordering is robust to this tie correction on these panels, while memberships and risk are not generally invariant. This removes a tie-priority difference, but fixed-count and frozen-cutoff rules still define different baseline tasks. We do not apply the row-local median entry formula to globally coupled top-$k$ membership or claim a new online certificate.

All 3,840 native/frozen control records reconcile with the original results. An independent sort and cardinality implementation checks matched masks, costs and priority transport under reindexing on 96 configurations across all panels, depths and pooling rules. All 5,760 new control records meet their integer churn budgets. These are cached-score checks, not evaluator execution or independent population replications.

'''+a[end:]
    a+='\n\\FloatBarrier\n\\input{tables/matched-tie-control}\n'
    # Use the main text to communicate the result, with detail retained in C.
    m=m.replace(r'Fixed-count retention changes the selection rule; Appendix~\ref{app:baselines} additionally matches label-blind tie priorities in a paired full-information control.',r'A matched-tie fixed-count control changes 453 retained sets but preserves returned-count ordering against frozen cutoff in all 1,920 configurations. The rules still select different baselines (Appendix~\ref{app:baselines}).')
    # Compact continuous introduction; no core definition or theorem is relocated.
    start=m.index(r'\section{Introduction}')+len(r'\section{Introduction}');end=m.index(r'\section{Related Work}')
    m=m[:start]+r'''
Reward models and translation metrics select language outputs, but evaluator changes can alter the selected set \citep{malik2026rewardbench2,freitag2023wmt23,zheng2023judging}. Consider a batch selected by a fixed evaluator pool and cutoff. A curator may retain some selections and refer other decisions for review. The trade-off concerns retained count and replacement sensitivity; agreement alone does not establish quality \citep{black2022selective,eisenstein2024herding}. Review interprets uncommitted decisions, without modeling human behavior or cost.

We ask how much score evidence certifies near-optimal retention under a budget on average membership changes. Maps and cutoff stay fixed across a finite family of single-evaluator replacements. One commitment mask is assessed across that family. The objective imposes neither a fixed-size quota nor one returned output per prompt, and gives no per-replacement budget guarantee.

Sufficient evidence and its discovery are two parts of this question. An offline constructor knows the true matrix; an online policy sees initially available information and earlier replies. For mean and median pooling, partial scores give safe and optimistic retained counts whose gap certifies shortfall from the full-information optimum. For odd-sized median pools, agreements establish feasibility and oppositions exclude larger sets, yielding minimum entry certificates. Residual witnesses incorporate existing evidence and shared columns under fixed additive prices.

NLP replays compare discovery with matching minima; controlled panels vary sharing at fixed row costs. Protocol controls change the selection task and are separate from same-task query-order comparisons. Sections~\ref{sec:setting}--\ref{sec:median} develop the certificates; Sections~\ref{sec:acquisition}--\ref{sec:experiments} study their discovery.

'''+m[end:]
    # Closest literature remains central; do not grow a catalogue of parallel aims.
    start=m.index(r'\section{Related Work}')+len(r'\section{Related Work}');end=m.index(r'\section{Selection under Evaluator Replacements}')
    m=m[:start]+r'''
\paragraph{Risk and evaluator consistency.}
CRC controls expected monotone loss \citep{angelopoulos2024crc}; parameter-dependent bounds sharpen calibration \citep{yeh2025conformal}. Prediction sets give high-probability risk control \citep{bates2021rcps}, and SCoRE controls selected and marginal risk with zero-loss abstention \citep{bai2026score}. Human-preference calibration \citep{badshah2026scope,cheng2026multiexpert}, shared-error audits \citep{afrin2026evaluatorensemblesrewardhacking}, training agreement \citep{black2022selective}, judge robustness \citep{li2026llmsreliablyjudgeyet} and pipeline attribution \citep{han2026leaderboardcertifycompositionalcontrollability} concern different guarantees. We bound retained-count shortfall under a churn budget for every consistent completion in a fixed finite replacement family.

\paragraph{Verification and costly queries.}
Priced information and Boolean score classification study input queries \citep{charikar2002priced,deshpande2016sbfe,gkenosis2018ssclass}. Robust selection combines queries and safe decisions \citep{goerigk2015robustqueries,chen2026selection}. Knapsack verification separates solution and exclusion evidence for uncertain profits \citep{schloter2025knapsack}; uncertainty matroids and monotone functions also admit certificates \citep{diwan2026basis,gupta2022monotone}. Our median model has unit-valued outputs and Boolean opposition costs. Sorted prefixes determine optimal retained count; entry or column evidence certifies that count or a gap. Partial and shared revelation also occur in refinement and covering models \citep{erlebach2015survey,megow2023set}.

\paragraph{Ranking and evaluation.}
Necessary and possible top-$k$ winners occur in every and some preference completion \citep{imber2020topk}; we certify count under a cutoff and churn budget. Weight or deletion stability \citep{asudeh2018stable,liang2025ranking} and rank uncertainty \citep{fermanian2025transductive} use other perturbations. Pruning, ensembles and ranking exits reduce scoring in their respective settings \citep{li2022pruning,inoue2019ensemble,busolin2021exit}. PAC selection estimates reward means \citep{kalyanakrishnan2012pac}; our queries reveal fixed scores. Middleware top-$k$ uses sorted and sometimes random access \citep{fagin2003optimal}; our oracle has no sorted interface. Best-of-Evidence reuses checks to choose candidates \citep{zhang2026bestofevidencebestofnselectionpartial}; we certify churn feasibility and count regret. MT stress tests assess metric quality \citep{moghe-etal-2025-machine,huang-baldwin-2023-robustness}.

'''+m[end:]
    (ROOT/'manuscript/main.tex').write_text(m);(ROOT/'manuscript/appendix.tex').write_text(a)
    (OUT/'matched-control-integration.json').write_text(json.dumps({'items':['I006','E086','E087','I004','E001','E002','I001'],'new_online_theory_claimed':False,'matched_control':check,'source_condensation':'Continuous introduction/related work with cited distinctions, no core result relocated'},indent=2)+'\n')
if __name__=='__main__':main()

# Derived files

- `supplement/extended_result_grids.csv`: 26 display tables, 465 rows (including headers). `table_id` is the original LaTeX label, `source_file/source_line` locate the table source, `row_index` is the zero-based display row within the table, and `cell_*_latex` keeps the cell LaTeX; trailing empty columns are padding.
- `extended_result_grids.json`: complete table source, wrapping input, table notes and units for the same display grid; not raw unrounded observations.
- `gain_distribution.json` and `manuscript/tables/gain-distribution.tex`: 960 targets per stopping condition. gain=`union_minimum-joint_upper`, and all targets are numerically closed; `positive` is the number of strictly positive differences, `median/mean` summarize all targets, `positive_mean` covers only positive-difference targets, and `max_relative` is the maximum percentage relative to the best separate union, not an average ratio. Aggregates across targets and overlapping splits are descriptive analyses.

`external-verification-20261006/solver/verified-case-states.jsonl` is merged on top of the original full-grid/closure. `PROVED_BY_TARGET_LOWER_BOUNDS` is a global proof that all safe-target lower bounds coincide with one feasible optimal component union; internal unclosed subproblems are not relabelled OPTIMAL. `partition_receipt` keeps each integer threshold, the relaxation/integer solve status and the lower bound; `threshold_screen` must bind a complete exclusion component receipt. All 1,920 joint/split/union are numerically closed.

# Result paths and units

All paths are relative to the repository root. `DATA_STATEMENT_CURRENT.md` states acquisition and redistribution restrictions, and `ACQUISITION_INDEX.md` identifies inputs and their access routes. The repository supplies aggregate results, paired-control masks, small-batch derived flip evidence and derived query traces of integer flip contributions. It excludes original third-party score and MQM arrays. Files marked "not included" exceed the repository file-size limit; `scripts/run_all.sh` regenerates them after the panels are rebuilt.

| Evidence | Relative path | Fields and units |
|---|---|---|
| Original entry experiments | `outputs/query_metrics.json` | `baseline_records`, `query_records`; count, own-baseline selected coverage, churn, exact/positive-gap stopping, integer tolerance, offline exact witness |
| Original quality comparator | `outputs/query_analysis.json` | `quality_records`, `quality_cells`; K, returned precision, unconstrained matched-K precision |
| Budget sensitivity | `outputs/review-budget/results.json` | all four acquisition orders and controls; budget, query count, capacities, risk, replacement max/fraction; means in cells |
| Pool composition | `outputs/review-composition/results.json` (not included) | pool identities and all strategies, budgets/targets, witness decomposition and per-replacement diagnostics |
| WMT24 | `outputs/review-external/results.json` | baseline/query records; exact/positive-gap target, MQM annotated count/coverage, matched-total and matched-annotated quality diagnostics |
| Original full paths | `outputs/query_traces.jsonl.gz`; `outputs/review-budget/traces.jsonl.gz` (not included); `outputs/review-composition/traces.jsonl.gz` (not included); `outputs/review-external/traces.jsonl.gz` (not included) | per-query traces of candidate, output and integer flip contribution |
| WMT23 MQM | `review-revision/acceptance-review-implementation/wmt23-quality-results.json` | frozen masks/path diagnostics; K, annotated count, coverage, matched-label comparator; no estimate for missing labels |
| MQM source identity | `review-revision/acceptance-review-implementation/wmt23-official-files.json` | hashes and relative names of 44 original used files; files themselves excluded |
| Mapping and column protocol | `outputs/mapping-column/results.json`; `outputs/mapping-column/all_result_cells.csv` | mapping, reference fraction, entry/column unit; NT vs mT fractions; exact and positive-gap targets |
| Exact column witnesses | `outputs/column-certificates/results.json` | column subset optima and witness comparisons for exact median target |
| Additive-price witnesses | `review-revision/acceptance-review-implementation/cost-results.json` | price profiles and exact/positive-gap targets; counts and additive costs, not measured runtime |
| Synthetic score sharing | `outputs/synthetic-certificates/results.json` | full generated scores and paths are available in the independent synthetic package; no third-party matrices needed |
| Tolerance | `outputs/tolerance-sensitivity/results.json` | legacy `tau` means nominal tolerance fraction eta, not entry price; epsilon=ceil(eta*|S0|). Undefined ratios remain missing |
| Prediction diagnostics | `outputs/acquisition-mechanisms/results.json` | path-dependent error, query difference, frozen first stopping states and finite replay receipts |
| Matched-tie successor | `outputs/matched-tie-control/records.csv`; `paired.csv`; `cells.csv`; `masks.json` | 1,920 configurations, 5,760 control records. Full-information frozen/native/matched controls. Costs are integer flips; risk divides by 2kH. Cov. uses each rule's own baseline. Masks are packbits in original test-item order with N recorded |

`V_lower` and `V_upper` are retained-count bounds, not risks. `V_star` is a full-information evaluation count. `epsilon` is an integer shortfall tolerance; `alpha` bounds replacement-average churn. `replacement_max_risk` and `replacement_over_alpha_fraction` are diagnostics, not enforced constraints. Score-entry counts do not measure GPU calls or execution savings.

The paired control never loads quality labels and never modifies original acquisition paths. `native_to_matched_returned_delta` compares tie conventions, whereas `matched_minus_frozen_returned` compares different selection rules. `selected_cost_sha256` hashes the complete per-output integer flip-cost vector, despite its legacy field label. The historical `certificate=conditional_expected_churn` string in SCoRE records denotes a marginal expectation guarantee under exchangeability assumptions; it is not a conditional-risk assertion.

## Joint certificate and intervention evidence

| Evidence | Relative path | Fields and units |
|---|---|---|
| Small-batch instances | `outputs/joint-certificates/instances.jsonl` | original output indices; integer endpoint caps and f_ir; observed masks; reconstructed joint query/safe bitmasks. At most four selected outputs with N/k/budget reset; preserves full candidate family |
| Joint minima | `outputs/joint-certificates/panel_records.csv`; `outputs/joint-certificates/panel_summary.csv` | additional queries; joint vs separately minimized safety+exclusion sizes; history, epsilon, bounds, dual-use fraction; descriptive 40-split means |
| Small-batch policy paths | `outputs/joint-certificates/discovery_paths.jsonl`; `outputs/joint-certificates/discovery_records.csv`; `outputs/joint-certificates/discovery_summary.csv` | four complete original policies; predictions/ties, (candidate, row, integer flip) traces, matching minima, positive-denominator ratios |
| Finite and independent minima audits | `outputs/joint-certificates/independent-check.json`; `outputs/joint-certificates/panel-independent-check.json` | exhaustive finite checks and a distinct explicit-output-subset integer optimizer; no human certification |
| Complete full-instance interventions | `outputs/query-mechanism-interventions/traces.jsonl.gz`; `outputs/query-mechanism-interventions/records.csv`; `outputs/query-mechanism-interventions/summary.csv` | derived (local active row, candidate, integer flip) traces and stop masks; reference/true-row/true-candidate/both. Oracle variants see true costs solely for diagnosis |
| Complete intervention audit | `outputs/query-mechanism-interventions/independent-check.json` | all replies/masks/first stops, and direct-sort choices on split-zero configurations |

`sharing_saving` is Q_split minus Q_joint, not a measured execution saving. `observed_entries` do not count as additional queries. `history=quarter` is a fixed initial evidence set, not a new data split. Mean small-batch minima do not bound different full-batch tasks. The newer intervention traces contain derived flip counts rather than raw scorer values; their source-derived redistribution status remains unresolved. Default portable checks establish saved derivation consistency; `--verify-optima` independently recomputes all small-batch minima.

## Joint-scale fields

`outputs/joint-scale` stores 2,304 tasks; `joint_optimal` and `separated_optimal` indicate whether the joint and the separate targets, respectively, are closed, and neither implies the other. Under resource limits, `queries` is a valid witness upper bound and cannot be taken as the minimum. `observed` is the existing per-row bit mask, `query_mask` the added entries and `safe_mask` the returned rows; all are arbitrary-precision integers. `N,k,budget` are the task's own quantities; subbatch and full are kept separate.

`outputs/compact-joint-scale` and `outcome-joint-scale` store the matched 576 main runs; the latter also has `retry-records.jsonl`, the complete `threshold-check.json`, API checks, resource probes and full discovery summaries. Single-threshold optimality holds only for its fixed t; the global minimum is marked only after the minimum lower and upper bounds over all feasible thresholds are closed. The full discovery ratio is the per-split `exact_queries/minimum`, then averaged; only the 96 tasks matching the original full tasks, zero tolerance.

The 9,600 records in `outputs/cutoff-bootstrap` are changed fixed protocols, not an independent population. `cutoff_only` keeps the original ECDF; `maps_and_cutoff` refits ECDF+cutoff; both use the same set of draws. `zero_query_stop` means the initial gap satisfies the primary epsilon, not that all selected rows are invariant. The mean minimum was not computed; the median minimum is that draw's own unit-entry minimum. The online query policy was not rerun, and quality labels were not used to select protocols.

## Deduplicated optimal evidence fields

`outputs/deduplicated-evidence/records.jsonl` has 3,936 distinct tasks, key=(scope,dataset,split,q,history,epsilon). In each line, rows are the derived integer flips per row/candidate, caps are endpoint p_i, observed is the bit mask of known entries, and the original N/k/budget or the reset small conditions are kept with the task; no original score/response/MQM arrays are included.

`joint_minimum`=Q_joint, `additive_minimum`=Q_split, `result.union_minimum`=Q_cup,sep. The latter fixes, per safe target, each minimum safety/exclusion cardinality and optimizes the union over all component ties, rather than taking an arbitrary pair of returned solutions. `targets` contains each target's component minima and union minima; `safety_mask`, `exclusion_mask` and `union_mask` are integer bit masks of added entries, and `safe_mask` is the returned rows. Existing observed entries are not charged again. With history fixed, added entries are the sole unified cost unit.

The 3,544 instances with `mode=bound_sandwich` certify equality of the three via the existing Q_joint=Q_split and the sandwich relation; they do not pretend to re-solve. The remaining 392 fresh tasks are 388 small + 4 full. `solver_calls` contains status/dual_bound/optimality_gap/options and objective; the programmatic numerical-optimality conclusion and the integer-feasibility recheck are kept separate. `retry-records.jsonl` appends only one primary closure, `full-entry-check.jsonl` has 4 independent entry checks, and `full-entry-retry.jsonl` appends only one timeout closure. The merge audit does not delete initial records.

In `summary.csv`, `double_count_reduction`=sum(Q_split-Q_cup,sep), `genuine_joint_reduction`=sum(Q_cup,sep-Q_joint), and `joint_below_union` is the number of strictly improved instances, not the number of entries, scorer calls or runtime. Small and complete tasks with different batch/budget are not combined to compute overall gains; the 40 splits or 8 splits are overlapping descriptive samples, with no independent significance test.


## Current complete-grid and frontier additions

- outputs/full-mean-grid-20261005/records.jsonl: 1,920 original targets, integer flip matrix/caps, original output IDs, N/k/budget/history/epsilon, feasible masks and numerical solver bounds. closure-*.jsonl overlays append-only improvements; each primary must match the preceding state. audited_records.csv separates joint_lower/joint_upper/joint_proven, split bounds and union_proven. Missing ratios stay empty.
- outputs/frontier-priority-20261005/traces.jsonl.gz: 960 instances, three methods each, integer (active row,candidate,flip) replies. records.csv has 5,760 first primary/exact stops, query/K/risk/gap/regret and matching original baselines; summary.csv aggregates all 40 splits. It contains derived outcomes, not original scorer text or raw numeric scores.
- outputs/common-information-20261005: 3,840 records and96 cells. Reference/calibration/test/total candidate entries normalized by NT; pool stages separate. Expectation versus deterministic guarantees remain distinct.
- outputs/protocol-evidence-20261005: 5,760 median protocol geometries and144 cells. initial gap, zero-query decomposition, matching Q0 and selected-set Jaccard; no new query paths or mean protocol minima.
- review-revision/editorial-integration-20261006: exact-count display check, runtime probe, current-source acquisition, three pre-edit checks, final clean build and evidence delivery receipts. Numerical solver status is not human proof certification.

## Same-instance evidence cost contrasts

`outputs/evidence-cost-contrasts/records.csv` has 13,440 rows keyed by `(dataset,split,q,stopping,method)`, covering 1,920 mean targets and seven policies. N/k/T/budget/selected_count/epsilon and empty history bind the target. `dedup_saving = Q_split - Q_union,sep`; `joint_gain = Q_union,sep - Q_joint`; these fields are empty when union optimality is unresolved. `online_excess` is exact only when joint optimality is proved. `online_excess_lower/upper` retain valid bounds on all tasks. `online_ratio` is defined only for proved strictly positive minima; `zero_minimum` records proved zero separately. These contrasts are not additive cost components. `summary.csv` contains 98 summaries (all panels plus six panels, two stops, seven methods); `*_closed_union` means use the identical closed-union subset; `*_all` bounds include every task. They aggregate all four depths. No missing optimum is imputed.

`supplement/result_grids.csv` preserves 408 displayed rows, including headers, from 18 grids. The LaTeX cell columns retain hierarchy rather than pretending rounded display entries are raw estimates. JSON retains full source, labels, captions and units. Original numeric records and all table generators remain available in the code package.

`outputs/evidence-cost-columns/records.jsonl` has 5,760 whole-column targets (mean pooling and even medians with six and eight members, 960 instances, two stops each). `column_minimum` is the minimum number of candidate columns certifying the target; `entry_minimum` is the matching entry-query minimum; `paths` hold the column orders and the (columns, safe count, optimistic count) frontiers of three online column policies. Records contain derived integer outcomes only.

`outputs/scope-extensions/summeval_union_recheck.jsonl` re-solves the 48 non-full SummEval mean unions without presolve; `tie_rounding_corrections.json` stores the exact value of every corrected table cell; `median_deviation_minima.jsonl` gives odd-median minima with and without oracle deviation caps.

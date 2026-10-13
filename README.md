# Certifying Output Retention Under Evaluator Replacement: Code and Results

Anonymous companion repository for the submission *How Many Evaluator Scores Certify Output Retention Under a Churn Budget?*

The repository contains the analysis code, derived result records and supplementary tables cited in the paper. It does not redistribute third-party response text or the original evaluator score arrays. Scripts rebuild those inputs from pinned public sources on the reader's machine (see below).

## Layout

| Path | Contents |
|---|---|
| `scripts/` | Core implementation: certificate bounds, acquisition policies, minimum-certificate solvers, experiment runners and checkers. |
| `submission/` | Independent audit scripts called by `scripts/run_all.sh`. |
| `supplement/` | Machine-readable versions of the supplementary result grids (`result_grids.csv`, `extended_result_grids.csv`, manifests). |
| `outputs/` | Derived records cited in the paper (matched-tie control, evidence-cost contrasts, query interventions). |
| `outputs/scope-extensions/` | Records for the per-replacement, constrained-completion, weighted-replacement, gain-diagnostic, odd-median guided acquisition and solver-sensitivity analyses. |
| `review-revision/acl-review-20261012/scripts/` | Scripts that produce `outputs/scope-extensions/` and their independent checks (`bruteforce_check.py`, `audit_numbers.py`). |
| `review-revision/`, `external-verification-20261006/` | Scripts and records for the numerical closure, discovery-bound and risk analyses cited in the appendix. |
| `evidence/`, `novelty-development/` | Pinned source manifests and the frozen execution protocol read by the scripts. |
| `ACQUISITION_INDEX.md`, `RESULT_DATA_DICTIONARY.md`, `PARTITION_AND_ARTIFACT_INDEX.md`, `DATA_STATEMENT_CURRENT.md`, `RESPONSIBLE_NLP_CURRENT.md` | Acquisition instructions, field definitions, artifact index, data statement and responsible-NLP record. |

## Environment

Python 3.9 with `numpy==2.0.2` and `scipy==1.13.1` (HiGHS through `scipy.optimize.milp`); see `requirements*.txt`. The analyses use cached scores and need no GPU.

## Rebuilding the inputs

```bash
python3 scripts/fetch_inputs.py                 # RewardBench 2 and WMT23 panels from pinned revisions
python3 scripts/fetch_external_inputs.py --archive mt-metrics-eval-v2.tgz   # WMT24 panels from the official archive
```

Both scripts write to `data/` by default (`--output-dir` changes this), never overwrite existing inputs and check the pinned hashes. The WMT archive is available from the official mt-metrics-eval distribution. Acquiring these files does not grant redistribution rights; see `DATA_STATEMENT_CURRENT.md`.

## Reproducing the results

`scripts/run_all.sh` runs the main query-selection, budget, composition, external-panel and score-comparison experiments with their audits. Individual analyses have their own runners in `scripts/` (for example `run_full_mean_grid.py`, `run_frontier_priority.py`, `run_cutoff_bootstrap.py`); `RESULT_DATA_DICTIONARY.md` maps each table to its records.

The scope extensions run from `review-revision/acl-review-20261012/scripts/`:

```bash
python3 per_replacement.py      # per-replacement churn caps
python3 constrained.py          # deviation and Lipschitz constraints
python3 weighted.py             # nonuniform replacement weights
python3 gain_predictors.py      # pre-scoring diagnostics of joint gain
python3 median_guided.py        # closed-form-guided odd-median acquisition
python3 solver_sensitivity.py   # HiGHS presolve and time-limit sensitivity
python3 bruteforce_check.py     # exhaustive checks of the new solvers
python3 audit_numbers.py        # recomputes every reported number from the records
python3 median_deviation_minima.py  # odd-median minima under deviation caps
python3 apply_tie_rounding.py   # decimal half-up for exact ties printed by earlier renderers
python3 audit_round4.py         # recomputes the numbers added in the latest revision
```

Except in `solver_sensitivity.py`, which varies the setting, the integer programs in these scripts run with HiGHS presolve disabled. On one small instance, presolve returned an incorrect optimum for the union program; `bruteforce_check.py` detects such cases.

`audit_numbers.py` reads `manuscript/main.tex` and `manuscript/appendix.tex`, which hold the submitted LaTeX sources. `summeval_union_recheck.py` needs the SummEval integer flip traces, which are not redistributed; its output `summeval_union_recheck.jsonl` is included.

## License

No license is granted for third-party data. Code is provided for review.

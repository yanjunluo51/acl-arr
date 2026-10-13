# Algorithm and evidence index

All paths are relative to the repository root.

## Numerical optimality closure

- `scripts/variable_target_certificate.py`: integer programs for all joint and additive safe targets.
- `scripts/deduplicated_certificates.py`: per-target optimization of the separately minimum safety and exclusion witnesses and of their minimum union.
- `external-verification-20261006/solver/disaggregate_pending.py`: safe-target domains and automatically excluded branches.
- `external-verification-20261006/solver/disaggregated_threshold.py`: model for a fixed threshold and target.
- `external-verification-20261006/solver/partition_adapter.py`: exhaustive partition of integer thresholds, LP screening and the subsequent MILP calls.
- `external-verification-20261006/solver/target_bound_certificate.py`: all-target lower bounds, optimality of tied components and union-witness verification.
- `external-verification-20261006/solver/highs_adapter.py`: settings for the later highspy calls; these settings do not recover unsaved historical SciPy settings.

The branch domains, calls and closure records are `disaggregated-attempts.jsonl`, `disaggregated-integer.jsonl`, `disaggregated-closures.jsonl`, `union-partitions.jsonl`, `union-screeneds.jsonl` and `union-finals.jsonl` in `external-verification-20261006/solver/`. Timeout, failure and interruption records are retained.

## Tables, protocols and randomization

- `supplement/result_grids.csv`, `supplement/result_grids.json`, `supplement/extended_result_grids.csv`, `supplement/extended_result_grids.json`: machine-readable results for the tables.
- `outputs/tolerance-sensitivity/stop_records.csv`: records per split, method and tolerance; the main-text means come from the same integer records.
- `review-revision/joint-scale-implementation/bootstrap-protocol.json`, `scripts/run_cutoff_bootstrap.py`, `outputs/cutoff-bootstrap/records.jsonl`: seeds and grouped bootstrap.
- `review-revision/evidence-discovery-implementation-20261005/frontier-protocol.json`, `scripts/run_frontier_priority.py`, `scripts/frontier_priority.py`: row priority, utility ties and the three frontier strategies.
- `RESULT_DATA_DICTIONARY.md`: field meanings, denominators and stopping targets.
- `ACQUISITION_INDEX.md`: commands for rebuilding the raw inputs.

## Cross-year confirmation

`review-revision/editorial-evidence-followthrough/confirmation/protocol.json` specifies the three WMT22 official primary evaluation directions, the complete test partition, methods and stopping targets. `admission.json` records admission, and `summary.csv` and `audit.json` in the same directory store the aggregate results and the scope of independent verification. Raw scores and score panels are not included; `ACQUISITION_INDEX.md` gives the rebuild command.

## Fixed-evaluator scale theory

`review-revision/fixed-pool-budget-extension/check_fixed_pool.py` is a standard-library rational-number implementation with exhaustive per-subset and grouped counting. It covers all integer budget branches, tolerance boundaries and local perturbations for 595 constructed instances; `--output` writes a new receipt, and the saved result is `theory-check.json` in the same directory. These constructed instances are not an NLP panel.

## Scope extensions

`review-revision/acl-review-20261012/scripts/` produces the records in `outputs/scope-extensions/` (per-replacement caps, constrained completions, weighted replacements, gain diagnostics, odd-median guided acquisition and solver sensitivity) and contains their exhaustive and numeric checks.

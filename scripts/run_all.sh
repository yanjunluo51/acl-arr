#!/usr/bin/env bash
set -euo pipefail
ARR_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARR_PY="${ARR_PY:-python3}"
cd "$ARR_ROOT"
if [[ -f outputs/review-budget/results.json || -f outputs/review-composition/results.json || -f outputs/review-external/results.json ]]; then
  echo "Completed review evidence exists. Use a fresh extraction/checker; never overwrite canonical evidence." >&2
  exit 1
fi
"$ARR_PY" scripts/test_query_selection.py
"$ARR_PY" scripts/test_review_priority.py
"$ARR_PY" scripts/query_selection.py
"$ARR_PY" submission/audit_query_results.py
"$ARR_PY" scripts/query_analysis.py
"$ARR_PY" scripts/render_query.py

"$ARR_PY" scripts/review_accelerated.py budget --workers 4
"$ARR_PY" submission/audit_review_parallel.py budget --workers 4
"$ARR_PY" scripts/review_accelerated.py composition --workers 6
"$ARR_PY" submission/audit_review_parallel.py composition --workers 6
"$ARR_PY" scripts/external_experiments.py --workers 4
"$ARR_PY" submission/audit_review_parallel.py external --workers 4
"$ARR_PY" scripts/score_comparison.py --workers 2
"$ARR_PY" submission/audit_score_comparison.py
"$ARR_PY" scripts/sentinel_diagnostics.py
"$ARR_PY" scripts/render_review.py

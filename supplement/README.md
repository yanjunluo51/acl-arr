# Complete result grids

`result_grids.csv` provides every displayed row from the 18 grids moved out of the reading PDF. Columns contain LaTeX cell text, including headers; `table_id`, source line and row index preserve grouping. Empty trailing cells are padding, not missing scientific outcomes. Rounded table entries must not be treated as original observations.

`result_grids.json` retains complete table source, captions, units, headers and labels, allowing exact reconstruction. Baseline grids are `query-full-baselines-*`; five-budget acquisition grids are `review-budget-*`; grouped-SCoRE grids are `review-score-*`. Panel indices 0/1/2 denote RewardBench 2, WMT23 thirteen-stream and WMT23 twelve-stream panels. Pooling is explicit in each name. All configurations are retained.

Unrounded records and table renderers remain in the local code package; see `RESULT_DATA_DICTIONARY.md` and the current reproduction guide. These display files supplement the definitions and representative results in the manuscript, rather than replacing them. Regenerate with `python3 scripts/export_result_grids.py` after replaying table renderers. Original `.tex` grids also remain in `manuscript/tables/`.

This local packaging does not assert complete redistribution permission for underlying or derived third-party data.

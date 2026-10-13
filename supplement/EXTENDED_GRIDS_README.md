# Extended complete grids

The reading PDF retains representative summaries, core proofs, the main acquisition algorithm and interpretation-changing diagnostics. `extended_result_grids.csv` preserves every displayed row moved in the presentation revision, including headers and units. `extended_result_grids.json` also preserves every complete table source and the input wrapper. `table_id` is the original LaTeX label; source filenames retain the family and panel index. Empty CSV trailing cells are padding. Displayed rounding is not raw precision.

Families: mapping-all-depths (all reference mappings), column-all-depths (entry/column acquisition), entry-overhead-all (all original exact-query ratios), tolerance-all (all stopping tolerances), review-external-all (all WMT24 depths), column-witness-all (all exact column minima). All configurations and adverse results remain included. The original table sources remain in `manuscript/tables/` and can be inserted back into the same LaTeX document. Unrounded records and renderers remain in the code package.

Regenerate with `python3 review-revision/resend-integration-20261007/render_supplement.py`. This local artifact does not confer redistribution permission for source or derived third-party data.

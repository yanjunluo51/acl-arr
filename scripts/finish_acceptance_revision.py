"""Evidence-bounded integration of the locked acceptance-review analyses."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'review-revision/acceptance-review-implementation'

def replace(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, old[:100]
    path.write_text(text.replace(old, new))

def main():
    receipt = json.loads((OUT/'wmt23-quality-independent.json').read_text())
    assert receipt['status'] == 'PASS_INDEPENDENT_RAW_MQM_AND_FIXED_MASK_CHECKS'
    assert receipt['query_records_recomputed'] + receipt['baseline_records_recomputed'] == 6400
    m = ROOT/'manuscript/main.tex'
    a = ROOT/'manuscript/appendix.tex'
    replace(m, 'The WMT23 score panels used here do not include human-quality labels. WMT24 MQM covers',
        'An official WMT23 MQM alignment adds post hoc diagnostics for fixed masks (Appendix~\\ref{app:quality}); missing labels remain missing. WMT24 MQM covers')
    replace(m, 'Appendix~\\ref{app:practical} relates protocol choices to scoring workload.',
        'Appendices~\\ref{app:column-prices} and~\\ref{app:practical} relate priced witnesses and protocol choices to scoring workload.')
    replace(a, 'The WMT23 score panels used here lack native quality labels, so their precision entries remain missing.',
        'The original WMT23 score panels contain no quality labels, so their original precision fields remain missing. Appendix~\\ref{app:quality} separately aligns official MQM after freezing the masks and paths.')
    replace(a, '\\section{Preference Diagnostic at Matched Returned Count}',
        '\\section{External Quality Diagnostics at Matched Count}')
    replace(a, 'All RewardBench comparisons have 40 defined splits; supplied WMT23 panels contain no preference or translation-quality labels.\n\\input{tables/query-quality}',
        r'''All RewardBench comparisons have 40 defined splits.
\input{tables/query-quality}

\subsection{Official WMT23 MQM alignment}
The official archive matches all 173,784 entries of the frozen 24-metric, 557-segment, thirteen-stream score panel. We align MQM by system name and original segment identifier, separately from the original score builder. Twelve MT systems have labels on 460 of 557 segments each, giving 5,520 observed labels among 7,241 outputs. The \texttt{synthetic\_ref} output has no MQM label. Higher released MQM scores are better; missing annotations remain missing.

We preserve all original splits, mappings, masks and acquisition paths. The analysis covers both WMT23 populations, both pooling rules, four depths and 40 splits, with all four entry orders at exact and positive-gap stops, plus zero-query and full-information masks: 6,400 records. Labels do not choose the acquisition order, stopping point or protocol. For each returned set, we report total count $K$, annotated count $K_{\rm lab}$ and annotated coverage. Its MQM mean is compared with the $K_{\rm lab}$ highest-consensus annotated test outputs, using the original label-blind tie key. This matches observed-label count; the comparator need not satisfy the churn budget. It does not estimate quality on unannotated outputs.

Table~\ref{tab:wmt23-native-quality} gives reference-priority positive-gap results at every depth; complete records retain all orders and stops. At median top-5\%, mean returned-label coverage is 28.3\% on thirteen streams and 77.3\% on twelve streams. The corresponding matched-label MQM differences are approximately $-.0020$ and $-.0002$. Other configurations have differences of either sign. Low coverage, especially when \texttt{synthetic\_ref} is admitted, prevents population quality conclusions. The 40 overlapping splits provide descriptive averages, not independent samples for a significance test. An independent checker rebuilds labels and both baseline masks and recomputes every diagnostic record.
\input{tables/wmt23-native-quality}''')
    replace(a, 'Restricting the commitment mask for a subsequent content policy preserves the fixed-denominator budget but can reduce the returned count (Appendix~\\ref{app:risk-interpretation}).',
        r'''Restricting the commitment mask for a subsequent content policy preserves the fixed-denominator budget but can reduce the returned count (Appendix~\ref{app:risk-interpretation}).

If an independently specified content or calibrated acceptance rule gives an eligible set $A_{\rm cal}$ before certification, apply the capacity calculation to $S_0\cap A_{\rm cal}$. The same monotone-cost argument gives $V^-_A\le V^*_A\le V^+_A$ and a gap guarantee relative to this restricted full-information optimum. It does not preserve near-optimality over the original $S_0$. Pruning a calibrated mask preserves an expected bound only for the same fixed-denominator, nonnegative loss under its calibration assumptions. A churn guarantee supplies no semantic-quality bound. If quality is audited after certification, report the audit separately; using those labels to select a stopping point requires an additional valid selection or calibration procedure.

Fixed additive column prices can change the cheapest evidence without changing the certification target (Appendix~\ref{app:column-prices}). Real batching, model loading and shared computation can instead make prices depend on the action history. Deployment claims require a verified scorer revision and interface, measured setup and inference costs, and the same target and retained-count accounting. The current priced-witness study does not replace those measurements.''')
    statement=ROOT/'DATA_STATEMENT_CURRENT.md'
    replace(statement, "Its acquisition is reproducible against that pinned mirror; equality to a current official archive is not established by the mirror reconstruction.",
        "Its acquisition is reproducible against that pinned mirror. The present supplemental audit also establishes exact equality of all 173,784 retained metric-score entries to the locally pinned official archive; this is a value/identity check, not a redistribution authorization.")
    replace(statement, 'The score panels used here have no native human-quality labels. This does not mean the WMT23 benchmark lacks human annotations.',
        'The original processed score panels have no human-quality labels. A separate post hoc alignment now supplies official MQM diagnostics for the frozen masks; original score inputs and missing precision fields are preserved.')
    insert='''
The supplemental alignment uses the already pinned official archive in `review-revision/acquisition/mt-metrics-eval-v2.tgz`. Forty-four used files are bound by `review-revision/acceptance-review-implementation/wmt23-official-files.json`. Exact system names and original segment identifiers align MQM, with 460 of 557 segments labeled for each of twelve MT systems (5,520 of 7,241 thirteen-stream outputs). `synthetic_ref` has no label. Higher released MQM is better; no missing values are filled. Full masks and query paths are unchanged. All 6,400 records (including zero/full-information baselines) and 1,440 summary fields were independently recomputed. The primary comparator matches the returned annotated count, not total returned count. Forty overlapping splits yield descriptive diagnostics only. Official source text, score files and label arrays remain local and are excluded from source/code packages; complete redistribution clearance remains unresolved.
'''
    replace(statement, '\n## WMT24 and MQM', insert+'\n## WMT24 and MQM')

if __name__ == '__main__': main()

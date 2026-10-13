"""Final editorial layer; changes captions/headers, never result rows."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def transform(name, text):
    if name == 'query-stopping.tex':
        text = text.replace('Z: zero-query stops among 40 splits.',
                            'Z: percentage of 40 splits stopping without queries.')
    if name == 'query-certificates.tex':
        text = text.replace('Safety and Exclusion sum to',
                            'Safety counts agreement entries; Exclusion counts opposition entries. They sum to')
    if name.startswith('query-full-baselines-') or name == 'query-baselines.tex':
        text = text.replace('The WMT23 score panels used here do not include human-quality labels.',
                            r'These controls do not use human-quality labels; the separate WMT23 MQM diagnostic is in Appendix~\ref{app:quality}.')
        text = text.replace('the WMT23 score panels used here lack quality labels.',
                            r'these WMT23 controls omit human-quality labels (see Appendix~\ref{app:quality} for the separate MQM diagnostic).')
    if name == 'query-quality.tex':
        text = text.replace('The comparator has no risk certificate.',
                            'The comparator is constructed without a churn-budget constraint.')
    if name == 'query-prefix-example.tex':
        text = text.replace('First tolerant stop', 'First positive-gap stop')
        text = text.replace('The tolerant gap is 15 outputs.', 'The allowed gap is 15 outputs.')
    if name == 'zero-query-decomposition.tex':
        text = text.replace('Invariant & Budget &', 'Invariant & Noninv. &')
        text = text.replace('Invariant and Budget are', 'Invariant and Noninv. are')
    if name.startswith('review-budget-'):
        text = text.replace('Queries counts candidate--output score entries.',
                            'Queries is the separately averaged entry count; Active averages splitwise queried fractions, not a ratio of mean counts.')
    if name.startswith('review-mqm-'):
        text = text.replace('matching annotated count.',
                            r'matching annotated count $J=K_{\rm lab}$. The matched-$K$ comparator matches total count; both MQM means use only its annotated subset.')
    if name == 'review-workload.tex':
        text = text.replace(' & Test & Total ', r' & Cand. test & Accounted total ')
        text = text.replace('Test counts candidate test entries.',
                            'Cand. test excludes base-test scores already counted in Setup. Accounted total sums these three columns after panel construction; it omits preprocessing reads of the full panel.')
    if name.startswith('column-witness-'):
        text = text.replace('Minimum exact column costs', 'Minimum exact column counts')
    if name.startswith('column-cost-'):
        text = text.replace('where a minimum-cost witness uses more columns than the minimum-count witness.',
                            'where even the fewest-column minimum-cost witness uses more columns than the minimum feasible count. Price ties minimize column count.')
    if name == 'column-summary.tex':
        text = text.replace('Touched counts candidate evaluators accessed by entries.',
                            'Touched counts candidate columns accessed by entry queries; it is not a scoring-call count.')
    if name == 'tolerance-all.tex':
        text = text.replace('Coverage divides by the unchanged base-list size.',
                            'Coverage divides by the unchanged base-list size and is shown at three of the six nominal tolerances; integer rounding determines the actual allowed gap.')
    if name.startswith('acquisition-'):
        text = text.replace('Remaining error uses', r'Remaining error is normalized by the full row scale $Tp_i$ and uses')
        text = text.replace('$\\Delta Q$ is reference minus largest-width queries.',
                            '$\\Delta Q$ is the reference-minus-largest-width entry count, not a percentage.')
    return text


def main():
    changed = []
    for p in sorted((ROOT/'manuscript/tables').glob('*.tex')):
        old = p.read_text()
        new = transform(p.name, old)
        if old != new:
            p.write_text(new)
            changed.append(p.name)
    print(json.dumps({'status': 'EDITORIAL_TABLE_LAYER_APPLIED', 'changed_tables': changed,
                      'numeric_result_rows_modified': False}))


if __name__ == '__main__':
    main()

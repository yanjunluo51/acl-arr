"""Independent bisect ECDF and explicit replacement replay on 24 fixed cases."""
import bisect
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import math
import random
from pathlib import Path
import numpy as np
from mapping_column_experiments import raw
from tolerance_certificates import minimum_gap_certificate

ROOT = Path(__file__).resolve().parents[1]
PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref',
          'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']


def mapping(values, reference):
    answer = []
    for row in values:
        ordered = sorted(row[reference])
        answer.append([bisect.bisect_right(ordered, v)/len(ordered) for v in row])
    return np.array(answer)


def consensus(base, agg):
    return (np.sort(base, axis=0)[3] if agg == 'median' else
            np.add.reduce(base, axis=0)/7)


def capacity(values, budget):
    count = total = 0
    for value in sorted(values):
        if total+value > budget:
            break
        total += value; count += 1
    return count


def main():
    records = [json.loads(line) for line in (ROOT/'outputs/cutoff-bootstrap/records.jsonl').open()]
    lookup = {(x['dataset'], x['arm'], x['aggregator']): x for x in records if x['split'] == 0 and x['draw'] == 0}
    count = 0
    for panel in PANELS:
        z, a, g = raw(panel)
        external = panel.startswith('WMT24')
        labels = (np.repeat(np.asarray(z['source_document_ids'], dtype=object), g) if external
                  else np.repeat(np.arange(len(z['prompt_ids'])), g))
        units = list(dict.fromkeys(labels.tolist()))
        seed = 924000 if external else 20260815 if panel == 'RewardBench2' else 87000
        shuffled = units.copy(); random.Random(seed).shuffle(shuffled)
        third = len(shuffled)//3
        reference_units = shuffled[:third]
        test_units = shuffled[2*third:]
        assert not set(reference_units) & set(test_units)
        if external:
            reference = np.flatnonzero(np.isin(labels, reference_units))
            test = np.flatnonzero(np.isin(labels, test_units))
        else:
            reference = np.array([i*g+j for i in reference_units for j in range(g)])
            test = np.array([i*g+j for i in test_units for j in range(g)])
        ordered_units = list(dict.fromkeys(labels[reference].tolist()))
        blocks = [reference[labels[reference] == unit] for unit in ordered_units]
        draw = np.random.default_rng(620275+PANELS.index(panel)*1000).integers(0, len(blocks), len(blocks))
        sampled = np.concatenate([blocks[i] for i in draw])
        old = mapping(a, reference)
        fitted = mapping(a, sampled)
        for arm in ['cutoff_only', 'maps_and_cutoff']:
            mapped = old if arm == 'cutoff_only' else fitted
            for agg in ['median', 'mean']:
                x = lookup[panel, arm, agg]
                nr = len(sampled)
                cutoff = sorted(consensus(mapped[:7, sampled], agg))[-max(1, round(.05*nr))]
                base = mapped[:7, test]
                selected = consensus(base, agg) >= cutoff
                original_cutoff = sorted(consensus(old[:7, reference], agg))[-max(1, round(.05*len(reference)))]
                original_selected = consensus(old[:7, test], agg) >= original_cutoff
                p = np.zeros(len(test), dtype=int)
                endpoints = np.where(selected, 0., 1.)
                costs = np.zeros(len(test), dtype=int)
                for j in range(7):
                    modified = base.copy(); modified[j] = endpoints
                    p += (consensus(modified, agg) >= cutoff) != selected
                    for candidate in mapped[7:, test]:
                        modified = base.copy(); modified[j] = candidate
                        costs += (consensus(modified, agg) >= cutoff) != selected
                active = selected & (p > 0)
                free = int(np.sum(selected & (p == 0)))
                S = int(selected.sum())
                budget = x['budget']
                union = int(np.sum(selected | original_selected))
                jac = float(np.sum(selected & original_selected))/union if union else 1.
                assert math.isclose(float(cutoff), x['cutoff'], abs_tol=1e-14)
                assert math.isclose(jac, x['selected_jaccard'], abs_tol=1e-14)
                assert S == x['selected_count'] and int(active.sum()) == x['active_rows']
                assert free+capacity(x['T']*p[active], budget) == x['V_initial_lower']
                assert capacity(costs[selected], budget) == x['full_information_retained']
                if agg == 'median':
                    opposition = (costs[active]//4).tolist()
                    assert minimum_gap_certificate(opposition, x['T'], budget//4, 0)['queries'] == x['median_exact_minimum']
                count += 1
    result = dict(status='PASS_INDEPENDENT_REFERENCE_ECDF_AND_EXPLICIT_REPLACEMENTS',
                  full_test_cases_reconstructed=count, expected_cases=24,
                  reference_test_disjoint=True, public_quality_labels_used=False,
                  all_9600_instances_independently_recomputed=False)
    assert count == 24
    (ROOT/'outputs/cutoff-bootstrap/independent-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

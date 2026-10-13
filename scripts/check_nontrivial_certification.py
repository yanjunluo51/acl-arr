"""Independent arithmetic and initial-state checks for the descriptive strata."""
from pathlib import Path
import gzip
import itertools
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'review-revision/operational-scope-implementation'


def main():
    result = json.loads((ROOT/'outputs/nontrivial-certification/results.json').read_text())
    originals = json.loads((ROOT/'outputs/query_metrics.json').read_text())
    external = json.loads((ROOT/'outputs/review-external/results.json').read_text())
    observations = {}
    initial = {}
    for r in originals['checkpoint_records']:
        if r['queries'] == 0 and r['allowance_queries'] == 0:
            key = (r['dataset'], r['aggregator'], r['q'], r['split'])
            state = (r['V_lower'], r['V_upper'], r['certificate_gap'])
            assert state[2] == state[1]-state[0]
            assert key not in initial or initial[key] == state
            initial[key] = state
    external_states = 0
    with gzip.open(ROOT/'outputs/review-external/traces.jsonl.gz', 'rt') as f:
        for line in f:
            row = json.loads(line)
            panel, _, split, pool, q = row['key']
            key = (panel, pool, q, split)
            for method in row['trace']:
                state = method['budgets'][0]['states'][0]
                assert state['queries'] == 0
                value = (state['V_lower'], state['V_upper'], state['gap'])
                assert value[2] == value[1]-value[0]
                assert key not in initial or initial[key] == value
                initial[key] = value
                external_states += 1
    for x in [originals, external]:
        for r in x['query_records']:
            key = (r['dataset'], r['aggregator'], r['q'], r['split'], r['stopping'], r['method'])
            observations[key] = r
            start = initial[key[:4]]
            assert start[1] == r['selected_count']
            assert (start[2]>r['epsilon']) == (r['queries']>0)
            assert r['epsilon'] == (0 if r['stopping']=='exact_gap' else math.ceil(.02*r['selected_count']))
    fields = 0
    for c in result['cells']:
        panel, pool, q, stop = c['dataset'], c['aggregator'], c['q'], c['stopping']
        eps = [observations[panel,pool,q,i,stop,'fixed']['epsilon'] for i in range(40)]
        ids = [i for i in range(40) if initial[panel,pool,q,i][2]>eps[i]]
        assert c['nontrivial_split_ids'] == ids and c['nontrivial_splits'] == len(ids)
        for m in c['methods']:
            for group, selected in [('all_splits', range(40)), ('nontrivial_splits', ids)]:
                rows = [observations[panel,pool,q,i,stop,m['method']] for i in selected]
                for field, value in m[group].items():
                    expected = float(np.mean([r[field] for r in rows])) if rows else None
                    assert (value is None and expected is None) or np.isclose(value,expected,rtol=1e-12,atol=1e-12)
                    fields += 1
    assert len(initial) == 1920 and external_states == 3840 and len(observations) == 15360
    receipt = {'status':'PASS_INDEPENDENT_INITIAL_STATE_AND_SUMMARY_ARITHMETIC',
               'initial_configurations':len(initial), 'external_initial_method_states':external_states,
               'query_records':len(observations), 'summary_fields':fields,
               'hard_subset_determined_before_acquisition':True,
               'same_subset_for_all_four_methods':True, 'new_scorer_inference':False,
               'population_inference':False}
    (OUT/'nontrivial-independent-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()

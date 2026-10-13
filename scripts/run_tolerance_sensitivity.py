"""Full fixed-path sensitivity on all six original right-ECDF score panels.

No inference, fitting, new query order or modification of old outputs. Inputs
are full recorded paths and cached score panels. Every score reply is checked;
each new stop returns the original solver's upper-cost prefix with fixed ties.
"""
import base64
import csv
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import time

import numpy as np
from numba import njit
from mapping_column_experiments import map_scores
from query_selection import aggregate, endpoint_cost, all_flips, prefix, capacity
from tolerance_certificates import minimum_gap_certificate

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT/'review-revision/information-certification-implementation/protocol.json'
OUT = ROOT/'outputs/tolerance-sensitivity'


@njit(cache=True)
def histogram_capacity(hist, budget):
    retained = hist[0]
    remaining = budget
    for value in range(1, len(hist)):
        take = min(hist[value], remaining // value)
        retained += take
        remaining -= take*value
        if take < hist[value]:
            break
    return retained


@njit(cache=True)
def scan_path(local_p, local_trace, T, budget, free, epsilons):
    m = len(local_p)
    limit = int(T*np.max(local_p)) if m else 0
    lh, uh = np.zeros(limit+1, np.int64), np.zeros(limit+1, np.int64)
    lo = np.zeros(m, np.int64)
    up = T*local_p.copy()
    lh[0] = m
    for x in up:
        uh[x] += 1
    stops = np.full((len(epsilons), 3), -1, np.int64)
    previous_gap = m
    for step in range(len(local_trace)+1):
        vlo = free + histogram_capacity(uh, budget)
        vhi = free + histogram_capacity(lh, budget)
        gap = vhi-vlo
        assert 0 <= gap <= previous_gap
        previous_gap = gap
        for e in range(len(epsilons)):
            if stops[e, 0] < 0 and gap <= epsilons[e]:
                stops[e] = (step, vlo, vhi)
        if step == len(local_trace):
            assert gap == 0
            break
        i, f = local_trace[step]
        assert 0 <= f <= local_p[i]
        lh[lo[i]] -= 1
        uh[up[i]] -= 1
        lo[i] += f
        up[i] -= local_p[i]-f
        assert lo[i] <= up[i]
        lh[lo[i]] += 1
        uh[up[i]] += 1
    assert np.all(stops[:, 0] >= 0)
    return stops


def configurations():
    with gzip.open(ROOT/'outputs/query_traces.jsonl.gz', 'rt') as stream:
        for line in stream:
            z = json.loads(line)
            panel, agg, rep, q, method = z['key']
            yield (panel, agg, rep, q), method, z['trace'], z['two_percent_stop'], z['exact_stop']
    with gzip.open(ROOT/'outputs/review-external/traces.jsonl.gz', 'rt') as stream:
        for line in stream:
            z = json.loads(line)
            panel, pool, rep, agg, q = z['key']
            assert pool == 'alphabetical'
            for path in z['trace']:
                budget = path['budgets']
                assert len(budget) == 1 and budget[0]['alpha'] == .1
                yield (panel, agg, rep, q), path['method'], path['trace'], budget[0]['two_percent_stop'], budget[0]['exact_stop']


def prepare(key, spec):
    panel, agg, rep, q = key
    ref, test, seed, _, _ = map_scores(panel, rep, '1', 'right')
    base, hidden = test[:7], test[7:]
    T, N = hidden.shape
    k = max(1, round(q*N))
    threshold = np.sort(aggregate(ref[:7], agg))[-max(1, round(q*ref.shape[1]))]
    selected = aggregate(base, agg) >= threshold
    p = endpoint_cost(base, threshold, agg)
    f = all_flips(base, hidden, threshold, agg)
    assert np.all(f <= p)
    cost = f.sum(axis=0)
    ids = np.flatnonzero(selected & (p > 0))
    local = np.full(N, -1, np.int64)
    local[ids] = np.arange(len(ids))
    free = int(np.sum(selected & (p == 0)))
    S = int(selected.sum())
    budget = 2*k*7*T//10
    tie = np.random.default_rng(seed+rep+700001).permutation(N)
    true_V = capacity(cost[selected], budget)
    eps = np.array([(Fraction(tau).numerator*S + Fraction(tau).denominator-1)//Fraction(tau).denominator
                    for tau in spec['tolerances']], dtype=np.int64)
    # Confirm existing float multiplication produced the same published 2% epsilon.
    assert eps[3] == int(np.ceil(.02*S))
    witnesses = [minimum_gap_certificate(cost[ids]//4, T, budget//4, e)
                 if agg == 'median' else None for e in eps]
    return locals()


def main():
    spec = json.loads(SPEC.read_text())
    OUT.mkdir(exist_ok=False)
    inputs = ['outputs/query_traces.jsonl.gz', 'outputs/review-external/traces.jsonl.gz',
              'data/rb2_ranked_panel.json', 'data/wmt23_metric_panel.json']
    inputs += ['data/wmt24_'+d+'_panel.json' for d in ['en-de', 'en-es', 'ja-zh']]
    bindings = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in inputs}
    begin = time.monotonic()
    (OUT/'execution.json').write_text(json.dumps({'status':'RUNNING', 'protocol':str(SPEC.relative_to(ROOT)),
                                                 'input_bindings':bindings}, indent=2)+'\n')
    rows, cache_key, paths, replies = [], None, 0, 0
    seen = set()
    with gzip.open(OUT/'stopping_masks.jsonl.gz', 'wt') as mask_log:
        for key, method, trace, old_tol, old_exact in configurations():
            panel, agg, rep, q = key
            assert panel in spec['panels'] and method in spec['methods']
            assert (*key, method) not in seen
            seen.add((*key, method))
            if key != cache_key:
                c = prepare(key, spec)
                cache_key = key
            tr = np.asarray(trace, dtype=np.int64).reshape(-1, 3)
            if len(tr):
                assert len({(int(r), int(i)) for r, i, _ in tr}) == len(tr)
                assert np.all(c['local'][tr[:, 1]] >= 0)
                assert np.array_equal(c['f'][tr[:, 0], tr[:, 1]], tr[:, 2])
            local_trace = np.column_stack((c['local'][tr[:, 1]], tr[:, 2]))
            stops = scan_path(c['p'][c['ids']], local_trace, c['T'], c['budget'], c['free'], c['eps'])
            assert stops[0, 0] == len(tr) == old_exact['queries']
            upper = c['T']*c['p'][c['ids']].copy()
            lower = np.zeros(len(c['ids']), dtype=np.int64)
            cursor = 0
            masks = {}
            for queries in sorted(set(int(s[0]) for s in stops)):
                while cursor < queries:
                    i, f = local_trace[cursor]
                    lower[i] += f
                    upper[i] -= c['p'][c['ids'][i]]-f
                    cursor += 1
                keep = (c['p'] == 0).copy()
                safe = prefix(upper, c['budget'], c['tie'][c['ids']])
                keep[c['ids'][safe]] = True
                upper_cost = int(upper[safe].sum())
                risk_cost = int(c['cost'][keep].sum())
                assert risk_cost <= upper_cost <= c['budget']
                masks[queries] = (keep, upper_cost, risk_cost)
            for j, (tau, epsilon) in enumerate(zip(spec['tolerances'], c['eps'])):
                Q, vlo, vhi = map(int, stops[j])
                mask, upper_cost, risk_cost = masks[Q]
                K = int(np.sum(mask & c['selected']))
                assert K == vlo <= c['true_V'] <= vhi and vhi-vlo <= epsilon
                assert c['true_V']-K <= epsilon
                if j in (0, 3):
                    old = old_exact if j == 0 else old_tol
                    assert Q == old['queries'] and vlo == old['V_lower'] and vhi == old['V_upper']
                    assert np.array_equal(mask, old['mask'])
                w = c['witnesses'][j]
                if w is not None:
                    assert Q >= w['queries']
                exact_Q = int(stops[0, 0])
                row = {'dataset':panel,'aggregator':agg,'split':rep,'q':q,'method':method,
                       'tau':str(tau),'tau_value':float(Fraction(tau)),'epsilon':int(epsilon),
                       'effective_tolerance':int(epsilon)/c['S'] if c['S'] else None,
                       'queries':Q,'active_entries':len(c['ids'])*c['T'], 'panel_entries':c['N']*c['T'],
                       'active_fraction':Q/(len(c['ids'])*c['T']) if len(c['ids']) else 0.,
                       'panel_fraction':Q/(c['N']*c['T']), 'zero_query':int(Q==0),
                       'returned_count':K,'selected_count':c['S'],
                       'selected_coverage':K/c['S'] if c['S'] else None,
                       'certificate_gap':vhi-vlo,'V_upper':vhi,'V_star':c['true_V'],
                       'realized_regret':c['true_V']-K,'integer_budget':c['budget'],
                       'true_cost':risk_cost,'upper_cost':upper_cost,
                       'risk':risk_cost/(2*c['k']*7*c['T']),
                       'exact_path_queries':exact_Q,
                       'saving_from_exact':1-Q/exact_Q if exact_Q else None,
                       'offline_gap_certificate':w['queries'] if w is not None else None,
                       'query_to_gap_witness':Q/w['queries'] if w is not None and w['queries'] else None}
                rows.append(row)
                mask_log.write(json.dumps({'key':[panel,agg,rep,q,method,tau],
                    'n_items':c['N'],'queries':Q,'mask_packbits_base64':base64.b64encode(np.packbits(mask).tobytes()).decode()})+'\n')
            paths += 1
            replies += len(tr)
            if paths % 160 == 0:
                print('paths',paths,'records',len(rows),'seconds',round(time.monotonic()-begin,1),flush=True)
    assert paths == spec['planned_paths'] and len(rows) == spec['planned_stop_records']
    groups = {}
    for r in rows:
        groups.setdefault((r['dataset'],r['aggregator'],r['q'],r['method'],r['tau']),[]).append(r)
    summary = []
    fields = ['queries','active_fraction','panel_fraction','zero_query','returned_count','selected_coverage',
              'certificate_gap','realized_regret','epsilon','effective_tolerance','saving_from_exact',
              'offline_gap_certificate','query_to_gap_witness']
    for key, group in sorted(groups.items()):
        assert len(group)==40 and {r['split'] for r in group}==set(range(40))
        cell = dict(zip(['dataset','aggregator','q','method','tau'],key),splits=40)
        for field in fields:
            v = [r[field] for r in group if r[field] is not None]
            cell[field] = statistics.fmean(v) if v else None
            cell[field+'_defined_splits'] = len(v)
        cell['maximum_regret'] = max(r['realized_regret'] for r in group)
        cell['maximum_effective_tolerance'] = max(r['effective_tolerance'] for r in group if r['effective_tolerance'] is not None)
        summary.append(cell)
    assert len(summary)==spec['planned_summary_cells']
    result = {'protocol':spec,'records':rows,'cells':summary,
              'scope':'Post hoc fixed-path sensitivity on exposed cached panels; descriptive overlapping splits, no inference.'}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for name, values in [('stop_records.csv',rows),('summary_cells.csv',summary)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    assert bindings == {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in inputs}
    execution={'status':'PASS_FULL_FIXED_PATH_SENSITIVITY','paths':paths,'stop_records':len(rows),
               'summary_cells':len(summary),'cached_replies_verified':replies,'original_endpoints_and_masks_match':True,
               'new_score_inference':False,'elapsed_seconds':time.monotonic()-begin,'input_bindings':bindings}
    (OUT/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
    print(json.dumps({k:v for k,v in execution.items() if k!='input_bindings'},indent=2))


if __name__=='__main__':
    main()

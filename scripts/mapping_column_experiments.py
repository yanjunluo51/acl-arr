"""Full mapping ablations and whole-evaluator score-query controls.

All test groups, acquisition rules and certificate solvers are preserved.
Reference subsampling is an explicitly labelled ablation, not a reduced test run.
"""
from pathlib import Path
from fractions import Fraction
from functools import lru_cache
import argparse, gzip, hashlib, json, math, multiprocessing, random, time
import numpy as np
from query_selection import (aggregate, endpoint_cost, all_flips, fit_prior,
                             prefix, capacity, exact_offline_certificate, summary)
from review_accelerated import solve_multi
from review_priority import solve_multi_quantized

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'review-revision/mapping-column/protocol.json'
OUT = ROOT / 'outputs/mapping-column'


@lru_cache(maxsize=3)
def raw(panel):
    file = ('rb2_ranked_panel.json' if panel == 'RewardBench2' else
            'wmt23_metric_panel.json' if panel.startswith('WMT23') else
            'wmt24_' + panel.split('-', 1)[1] + '_panel.json')
    z = json.loads((ROOT / 'data' / file).read_text())
    columns = [i for i, s in enumerate(z.get('systems', [0, 1, 2, 3]))
               if panel != 'WMT23_without_synthetic_ref' or s != 'synthetic_ref']
    a = np.array([[np.asarray(z['scores'][m][i])[columns]
                   for i in z['prompt_ids']] for m in z['models']], dtype=float)
    return z, a.reshape(len(z['models']), -1), len(columns)


def indices(panel, rep, fraction):
    z, a, g = raw(panel)
    external = panel.startswith('WMT24')
    seed = 924000 if external else 20260815 if panel == 'RewardBench2' else 87000
    units = (list(dict.fromkeys(z['source_document_ids'])) if external else
             list(range(len(z['prompt_ids']))))
    random.Random(seed + rep).shuffle(units)
    third = len(units) // 3
    ref_units = units[:third][:max(1, int(third * Fraction(fraction)))]
    groups = [ref_units, units[third:2*third], units[2*third:]]
    if external:
        idx = [np.array([i*g+j for i, d in enumerate(z['source_document_ids'])
                         if d in set(part) for j in range(g)]) for part in groups]
    else:
        idx = [np.array([i*g+j for i in part for j in range(g)]) for part in groups]
    return idx, seed, len(ref_units), third


def cdf(values, reference, mode):
    reference = np.sort(reference)
    right = np.searchsorted(reference, values, side='right')
    if mode == 'right':
        return right / len(reference)
    assert mode == 'midrank'
    left = np.searchsorted(reference, values, side='left')
    return (left + right) / (2 * len(reference))


def map_scores(panel, rep, fraction, mode):
    z, a, g = raw(panel)
    idx, seed, groups, fullgroups = indices(panel, rep, fraction)
    rr, tt = idx[0], idx[2]
    ref = np.array([cdf(row[rr], row[rr], mode) for row in a])
    test = np.array([cdf(row[tt], row[rr], mode) for row in a])
    return ref, test, seed, groups, fullgroups


def column_order(method, p, selected, prior, T, seed):
    if method == 'column_fixed':
        return np.arange(T)
    if method == 'column_random':
        return np.random.default_rng(seed + 571921).permutation(T)
    assert method == 'column_reference'
    ids = selected & (p > 0)
    estimate = np.rint(prior[ids] * 10**12).astype(np.int64)
    reduction = np.sum(p[ids, None] * 10**12 - estimate, axis=0)
    return np.lexsort((np.arange(T), -reduction))


def solve_columns(base, selected, p, prior, threshold, agg, T, budget, tie,
                  method, seed, query_column, epsilon):
    ids = np.flatnonzero(selected & (p > 0))
    lower = np.zeros(len(ids), dtype=np.int64)
    upper = T * p[ids].copy()
    free = int(np.sum(selected & (p == 0)))
    trace, tol, exact = [], None, None
    N = len(p)
    order = column_order(method, p, selected, prior, T, seed)
    for step in range(T + 1):
        vlo = free + capacity(upper, budget)
        vhi = free + capacity(lower, budget)
        if tol is None and vhi-vlo <= epsilon or vhi == vlo:
            mask = (p == 0).copy()
            keep = prefix(upper, budget, tie[ids])
            mask[ids[keep]] = True
            st = {'columns': step, 'queries': step*N, 'V_lower': vlo,
                  'V_upper': vhi, 'gap': vhi-vlo, 'mask': mask.tolist(),
                  'upper_selected_cost': int(upper[keep].sum())}
            if tol is None and vhi-vlo <= epsilon:
                tol = st
            if vhi == vlo:
                exact = st
                break
        assert step < T
        c = int(order[step])
        scores = query_column(c)
        assert scores.shape == (N,)
        # The oracle reveals all N scores, even though only selected active
        # entries are relevant to this certificate's objective.
        f = all_flips(base, scores[None, :], threshold, agg)[0, ids]
        assert np.all((0 <= f) & (f <= p[ids]))
        lower += f
        upper -= p[ids] - f
        trace.append(c)
    assert tol is not None and exact is not None
    return trace, tol, exact


def record(common, st, method, stopping, cost, selected, p, T, budget, tie,
           trace, offline):
    mask = np.asarray(st['mask'], dtype=bool)
    V = capacity(cost[selected], budget)
    count = int(selected.sum())
    eps = math.ceil(.02*count) if stopping == 'two_percent_gap' else 0
    assert cost[mask].sum() <= budget
    assert st['V_lower'] <= V <= st['V_upper']
    assert int(np.sum(mask & selected)) == st['V_lower']
    assert st['gap'] <= eps and V-st['V_lower'] <= eps
    active = int(np.sum(selected & (p > 0)))*T
    n = st['queries']
    cols = (st['columns'] if method.startswith('column_') else
            len({x[0] for x in trace[:n]}))
    result = {**common, 'method': method, 'stopping': stopping, 'epsilon': eps,
              'queries': n, 'candidate_columns_touched': cols,
              'active_entries': active,
              'active_fraction': n/active if active else 0,
              'panel_fraction': n/(common['n_test_items']*T),
              'returned_count': st['V_lower'], 'selected_count': count,
              'selected_coverage': st['V_lower']/count if count else None,
              'V_star': V, 'V_lower': st['V_lower'], 'V_upper': st['V_upper'],
              'certificate_gap': st['gap'], 'realized_regret': V-st['V_lower'],
              'risk': int(cost[mask].sum())/(2*common['k']*7*T),
              'setup_entries': common['reference_entries']*(7+T)+7*common['n_test_items'],
              'total_entries': common['reference_entries']*(7+T)+7*common['n_test_items']+n}
    if method.startswith('column_'):
        result['active_fraction'] = None  # Includes nonactive scores; use panel cost.
        result['relevant_active_entries_revealed'] = st['columns']*(active//T)
        for field in ['offline_exact_certificate', 'offline_exact_safe_part',
                      'offline_exact_exclusion_part']:
            result.pop(field, None)
    elif offline is not None:
        Q, S, E = offline
        result.update(offline_exact_certificate=Q, offline_exact_safe_part=S,
                      offline_exact_exclusion_part=E)
        if stopping == 'exact_gap':
            assert n >= Q
    return result


def case(panel, rep, fraction, mode, ref_all, test_all, seed, groups, fullgroups,
         agg, q):
    base, hidden = test_all[:7], test_all[7:]
    ref, candidates = ref_all[:7], ref_all[7:]
    T, N = len(hidden), base.shape[1]
    k = max(1, round(q*N))
    b = 2*k*7*T//10
    threshold = float(np.sort(aggregate(ref, agg))[-max(1, round(q*ref.shape[1]))])
    assert 0 < threshold <= 1
    selected = aggregate(base, agg) >= threshold
    p = endpoint_cost(base, threshold, agg)
    f = all_flips(base, hidden, threshold, agg)
    assert np.all(f <= p)
    cost = f.sum(axis=0)
    prior = fit_prior(ref, candidates, base, threshold, p, agg)
    tie = np.random.default_rng(seed+rep+700001).permutation(N)
    eps = math.ceil(.02*selected.sum())
    offline = (exact_offline_certificate(cost[selected & (p > 0)]//4, T, b//4)
               if agg == 'median' else None)
    zero = capacity((T*p)[selected], b)
    common = {'dataset': panel, 'split': rep, 'reference_fraction': fraction,
              'cdf': mode, 'aggregator': agg, 'q': q, 'alpha': .1,
              'integer_budget': b, 'k': k, 'n_test_items': N, 'T': T,
              'reference_entries': ref.shape[1], 'reference_groups': groups,
              'full_reference_groups': fullgroups, 'threshold': threshold,
              'selected_count': int(selected.sum()),
              'selected_over_k': int(selected.sum())/k,
              'active_selected_items': int(np.sum(selected & (p > 0))),
              'zero_selected_coverage': zero/int(selected.sum()) if selected.any() else None,
              'zero_retained': zero, 'V_star': capacity(cost[selected], b)}
    if offline is not None:
        common.update(offline_exact_certificate=offline[0],
                      offline_exact_safe_part=offline[1], offline_exact_exclusion_part=offline[2])
    paths, rows = [], []
    solver = solve_multi_quantized if panel.startswith('WMT24') else solve_multi
    for method in ['fixed', 'random', 'largest_width', 'reference_priority']:
        observed = set()
        def query(c, i):
            assert (c, i) not in observed
            observed.add((c, i))
            return float(hidden[c, i])
        trace, states, tol, exact = solver(base, selected, p, prior, threshold, agg,
            T, np.array([b], dtype=np.int64), tie, method, seed+rep+99173,
            query, [0, 1], eps)
        for c, i, answer in trace:
            assert answer == f[c, i]
        paths.append({'method': method, 'trace': trace, 'two_percent_stop': tol[0],
                      'exact_stop': exact[0]})
        for stop, st in [('two_percent_gap', tol[0]), ('exact_gap', exact[0])]:
            rows.append(record(common, st, method, stop, cost, selected, p,
                               T, b, tie, trace, offline))
    if fraction == '1' and mode == 'right':
        for method in ['column_fixed', 'column_random', 'column_reference']:
            observed = set()
            def query_column(c):
                assert c not in observed
                observed.add(c)
                return hidden[c].copy()
            trace, tol, exact = solve_columns(base, selected, p, prior, threshold,
                 agg, T, b, tie, method, seed+rep+99173, query_column, eps)
            paths.append({'method': method, 'trace': trace,
                          'two_percent_stop': tol, 'exact_stop': exact})
            for stop, st in [('two_percent_gap', tol), ('exact_gap', exact)]:
                rows.append(record(common, st, method, stop, cost, selected, p,
                                   T, b, tie, trace, None))
    return {'key': [panel, rep, fraction, mode, agg, q], 'geometry': common,
            'records': rows, 'paths': paths}


def group_task(task):
    panel, rep, fraction, mode = task
    ref, test, seed, groups, fullgroups = map_scores(panel, rep, fraction, mode)
    return [case(panel, rep, fraction, mode, ref, test, seed, groups, fullgroups,
                 agg, q) for agg in ['median', 'mean'] for q in [.05, .10, .20, .30]]


def main(workers):
    protocol = json.loads(SPEC.read_text())
    for p, h in {**protocol['source_bindings'], **protocol['solver_bindings']}.items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h, p
    OUT.mkdir(exist_ok=False)
    (OUT/'protocol.json').write_text(SPEC.read_text())
    start = time.monotonic()
    tasks = [(panel, rep, fraction, mode) for panel in protocol['panels']
             for rep in range(40) for fraction in protocol['reference_fractions']
             for mode in protocol['cdf_modes']]
    rows, geometry, cases, entry_paths, column_paths = [], [], 0, 0, 0
    with gzip.open(OUT/'traces.jsonl.gz', 'wt', compresslevel=1) as log:
        with multiprocessing.get_context('spawn').Pool(workers) as pool:
            for batch in pool.imap(group_task, tasks, chunksize=1):
                for z in batch:
                    rows.extend(z['records']);geometry.append(z['geometry'])
                    entry_paths += sum(not p['method'].startswith('column_') for p in z['paths'])
                    column_paths += sum(p['method'].startswith('column_') for p in z['paths'])
                    log.write(json.dumps(z, separators=(',', ':'), allow_nan=False)+'\n')
                    cases += 1
                if cases % 320 == 0:
                    status = {'status': 'RUNNING', 'cases': cases, 'entry_paths': entry_paths,
                              'column_paths': column_paths, 'seconds': round(time.monotonic()-start, 1)}
                    (OUT/'execution.json').write_text(json.dumps(status)+'\n')
                    print(json.dumps(status), flush=True)
    assert cases == protocol['expected_configurations']
    assert entry_paths == protocol['expected_entry_paths']
    assert column_paths == protocol['expected_column_paths']
    fields = ['queries','candidate_columns_touched','active_fraction','panel_fraction',
              'selected_coverage','V_star','zero_selected_coverage','selected_over_k',
              'active_selected_items','risk','total_entries','setup_entries',
              'offline_exact_certificate','offline_exact_safe_part','offline_exact_exclusion_part']
    keys = ['dataset','reference_fraction','cdf','aggregator','q','method','stopping']
    payload = {'protocol': protocol, 'geometry': geometry, 'records': rows,
               'cells': summary(rows, keys, fields)}
    (OUT/'results.json').write_text(json.dumps(payload, allow_nan=False, separators=(',', ':'))+'\n')
    receipt = {'status': 'PASS_FULL_EXECUTION_PENDING_SEPARATE_ARITHMETIC_AUDIT',
               'cases': cases, 'entry_paths': entry_paths, 'column_paths': column_paths,
               'records': len(rows), 'runtime_seconds': time.monotonic()-start,
               'runtime_scope': 'cached score replay, not model inference',
               'physical_model_execution': False}
    (OUT/'execution.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--workers', type=int, default=4)
    args = p.parse_args()
    main(args.workers)

"""Complete finite-panel score-inspection experiment; no model inference calls.

The solver receives base scores, reference-fitted priorities, and a query callback.
Hidden candidate test scores and preference labels are used only by the runner
and independent trace verifier. Integer flip counts avoid risk-budget rounding.
"""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import math
import random
import statistics
import time
import traceback
import numpy as np
from analyze import calibrate_envelope, topk

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
PROTOCOL = ROOT / 'novelty-development' / 'EXECUTION_PROTOCOL.json'


def prefix(cost, budget, tie):
    order = np.lexsort((tie, cost))
    cumulative = np.cumsum(cost[order], dtype=np.int64)
    keep = np.zeros(len(cost), dtype=bool)
    keep[order[cumulative <= budget]] = True
    return keep


def capacity(cost, budget):
    # Costs are small integers, so histogram evaluation avoids repeated sorting.
    if len(cost) == 0:
        return 0
    counts = np.bincount(np.asarray(cost, dtype=int))
    retained, available = int(counts[0]), int(budget)
    for value in range(1, len(counts)):
        take = min(int(counts[value]), available // value)
        retained += take
        available -= take * value
        if take < counts[value]:
            break
    return retained


def aggregate(base, aggregator):
    if aggregator == 'median':
        return np.median(base, axis=0)
    # Identical left-to-right reduction for batched and single-item queries.
    result = np.zeros_like(base[0], dtype=float)
    for row in base:
        result = result + row
    return result / len(base)


def flips(base, z, threshold, aggregator):
    """Same replacement/aggregation path for observed scores and endpoint bounds."""
    M = len(base)
    replacements = np.tile(base, (M, 1))
    replacements[np.arange(M), np.arange(M)] = z
    old = bool(aggregate(base, aggregator) >= threshold)
    return int(np.count_nonzero((aggregate(replacements.T, aggregator) >= threshold) != old))


def all_flips(base, candidates, threshold, aggregator):
    old = aggregate(base, aggregator) >= threshold
    result = np.zeros(candidates.shape, dtype=np.int64)
    for j in range(len(base)):
        for r in range(len(candidates)):
            replacement = base.copy()
            replacement[j] = candidates[r]
            result[r] += (aggregate(replacement, aggregator) >= threshold) != old
    return result


def endpoint_cost(base, threshold, aggregator):
    old = aggregate(base, aggregator) >= threshold
    endpoint = np.where(old, 0.0, 1.0)
    costs = np.zeros(base.shape[1], dtype=np.int64)
    for j in range(len(base)):
        replacement = base.copy()
        replacement[j] = endpoint
        costs += (aggregate(replacement, aggregator) >= threshold) != old
    return costs


def features(base, threshold, p, aggregator):
    return np.column_stack((np.ones(base.shape[1]), base.T,
                            aggregate(base, aggregator) - threshold,
                            np.ptp(base, axis=0), p / len(base)))


def fit_prior(ref_base, ref_candidates, test_base, threshold, p_test, aggregator):
    p_ref = endpoint_cost(ref_base, threshold, aggregator)
    x_ref = features(ref_base, threshold, p_ref, aggregator)
    x_test = features(test_base, threshold, p_test, aggregator)
    response = all_flips(ref_base, ref_candidates, threshold, aggregator).T
    penalty = np.eye(x_ref.shape[1])
    penalty[0, 0] = 0.0
    gram = np.einsum('ni,nj->ij', x_ref, x_ref, optimize=False)
    cross = np.einsum('ni,nj->ij', x_ref, response, optimize=False)
    coefficient = np.linalg.solve(gram + penalty, cross)
    prediction = np.einsum('ni,ij->nj', x_test, coefficient, optimize=False)
    assert np.isfinite(coefficient).all() and np.isfinite(prediction).all()
    return np.clip(prediction, 0, p_test[:, None])


def exact_offline_certificate(z, T, budget):
    """Median Boolean oracle only: exact gap-zero certificate, not online optimum."""
    z = np.sort(np.asarray(z, dtype=int))
    m = len(z)
    L = capacity(z, budget)
    safe = max(0, L * T - budget)
    if L == m:
        return safe, safe, 0
    p, B = L + 1, budget + 1
    level = next(t for t in range(T + 1) if int(np.minimum(z[:p], t).sum()) >= B)
    exclusion = B + (m - p) * level
    return safe + exclusion, safe, exclusion


def solve(base, selected, p, prior, threshold, aggregator, T, budget, tie,
          method, seed, query, checkpoints, epsilon):
    """No hidden test matrix, true full-information optimum, or quality input."""
    ids = np.flatnonzero(selected & (p > 0))
    free = int(np.count_nonzero(selected & (p == 0)))
    local_p = p[ids]
    known = np.zeros((len(ids), T), dtype=bool)
    lower = np.zeros(len(ids), dtype=np.int64)
    upper = T * local_p.copy()
    estimate = prior[ids].copy()
    trace, states = [], []
    total = len(ids) * T
    targets = sorted(set(int(math.ceil(f * total)) for f in checkpoints) | {total})
    random_order = np.random.default_rng(seed).permutation(total)
    random_cursor = 0
    first_tolerant = None
    first_exact = None

    def state():
        lo, hi = free + capacity(upper, budget), free + capacity(lower, budget)
        keep = (p == 0).copy()
        safe = prefix(upper, budget, tie[ids])
        keep[ids[safe]] = True
        return {'queries': len(trace), 'V_lower': lo, 'V_upper': hi,
                'gap': hi - lo, 'mask': keep.tolist(),
                'upper_selected_cost': int(upper[safe].sum())}

    for step in range(total + 1):
        gap = capacity(lower, budget) - capacity(upper, budget)
        save = step in targets or (first_tolerant is None and gap <= epsilon) or gap == 0
        st = state() if save else None
        if st is not None:
            if first_tolerant is None and st['gap'] <= epsilon:
                first_tolerant = st
            if first_exact is None and st['gap'] == 0:
                first_exact = st
            if step in targets:
                states.append(st)
        if step == total or first_exact is not None:
            break
        remaining = np.any(~known, axis=1)
        if method == 'random':
            cell = int(random_order[random_cursor]); random_cursor += 1
            item, candidate = divmod(cell, T)
        elif method == 'fixed':
            item = min(np.flatnonzero(remaining), key=lambda a: tie[ids[a]])
            candidate = int(np.flatnonzero(~known[item])[0])
        elif method == 'largest_width':
            width = upper - lower
            item = min(np.flatnonzero(remaining), key=lambda a: (-int(width[a]), tie[ids[a]]))
            candidate = int(np.flatnonzero(~known[item])[0])
        elif method == 'reference_priority':
            expected = lower + np.sum(np.where(known, 0.0, estimate), axis=1)
            item = min(np.flatnonzero(remaining), key=lambda a: (expected[a], tie[ids[a]]))
            candidate = max(np.flatnonzero(~known[item]),
                            key=lambda c: (local_p[item] - estimate[item, c], -int(c)))
        else:
            raise ValueError(method)
        assert not known[item, candidate]
        full_item = int(ids[item])
        score = query(int(candidate), full_item)
        f = flips(base[:, full_item], score, threshold, aggregator)
        assert 0 <= f <= local_p[item]
        known[item, candidate] = True
        lower[item] += f
        upper[item] -= local_p[item] - f
        trace.append([int(candidate), full_item, f])
    assert first_tolerant is not None and first_exact is not None
    # Once exact optimum is certified, freeze its mask at all larger budgets.
    existing = {x['queries'] for x in states}
    for target in targets:
        if target not in existing:
            states.append({**first_exact, 'budget_checkpoint_queries': target})
    return trace, states, first_tolerant, first_exact


def metrics(cost, selected, keep, H, k, labels):
    ret = selected & keep
    n = int(ret.sum()); sel = int(selected.sum())
    return {'risk': int(cost[keep].sum()) / (2 * k * H),
            'coverage': float(keep.mean()), 'selected_coverage': n / sel if sel else None,
            'returned_count': n, 'selected_count': sel,
            'selected_review_count': int((selected & ~keep).sum()),
            'nonselected_review_count': int((~selected & ~keep).sum()),
            'selected_risk': int(cost[selected & keep].sum()) / (2 * k * H),
            'nonselected_risk': int(cost[~selected & keep].sum()) / (2 * k * H),
            'returned_over_k': n / k,
            'precision': float(labels[ret].mean()) if labels is not None and n else None,
            'preferred_yield': int(labels[ret].sum()) if labels is not None else None}


def verify_path(trace, states, tolerant, exact, hidden_cost, p, selected,
                T, budget, true_V, epsilon):
    lower = np.zeros(len(p), dtype=np.int64)
    upper = T * p.copy()
    seen = set(); checks = 0
    targets = {s['queries']: [] for s in states + [tolerant, exact]}
    for s in states + [tolerant, exact]:
        targets[s['queries']].append(s)
    for index in range(len(trace) + 1):
        for s in targets.get(index, []):
            mask = np.asarray(s['mask'], dtype=bool)
            assert int(upper[mask].sum()) <= budget
            assert int(hidden_cost[mask].sum()) <= budget
            vlo = capacity(upper[selected], budget)
            vhi = capacity(lower[selected], budget)
            assert s['V_lower'] == vlo and s['V_upper'] == vhi
            assert vlo <= true_V <= vhi
            assert int((mask & selected).sum()) == vlo
            checks += 6
        if index == len(trace):
            break
        c, i, f = trace[index]
        assert (c, i) not in seen
        seen.add((c, i))
        lower[i] += f; upper[i] -= p[i] - f
        assert lower[i] <= hidden_cost[i] <= upper[i]
        checks += 2
    assert true_V - tolerant['V_lower'] <= epsilon
    assert exact['V_lower'] == true_V and exact['gap'] == 0
    return checks + 2


def summary(rows, keyfields, fields):
    grouped = {}
    for row in rows:
        grouped.setdefault(tuple(row[k] for k in keyfields), []).append(row)
    cells = []
    for key, values in sorted(grouped.items()):
        result = dict(zip(keyfields, key), splits=len(values))
        for field in fields:
            numbers = [v[field] for v in values if v.get(field) is not None]
            result[field] = statistics.fmean(numbers) if numbers else None
        cells.append(result)
    return cells


def main():
    protocol = json.loads(PROTOCOL.read_text())
    OUT.mkdir(exist_ok=True)
    (OUT/'query_validation.json').write_text(json.dumps({'status':'RUNNING', 'protocol_sha256': hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()}, indent=2)+'\n')
    baseline_rows, query_rows, checkpoint_rows, datasets = [], [], [], {}
    validation_checks = 0
    start = time.monotonic()
    trace_path = OUT / 'query_traces.jsonl.gz'
    with gzip.open(trace_path, 'wt', encoding='utf-8') as log:
        for name in protocol['panels']:
            filename = 'rb2_ranked_panel.json' if name == 'RewardBench2' else 'wmt23_metric_panel.json'
            blob = json.loads((ROOT / 'data' / filename).read_text())
            models, gids = blob['models'], blob['prompt_ids']
            systems = blob.get('systems', [0, 1, 2, 3])
            columns = [j for j, s in enumerate(systems)
                       if name != 'WMT23_without_synthetic_ref' or s != 'synthetic_ref']
            g = len(columns)
            raw = np.array([[np.asarray(blob['scores'][m][pid])[columns] for pid in gids]
                            for m in models], dtype=float).reshape(len(models), -1)
            assert np.isfinite(raw).all()
            M, T = 7, len(models) - 7; H = M * T
            seed = 20260815 if name == 'RewardBench2' else 87000
            datasets[name] = {'models': models, 'groups': len(gids), 'group_size': g,
                              'M': M, 'T': T, 'H': H, 'seed': seed,
                              'excluded_systems': [s for j, s in enumerate(systems) if j not in columns]}
            for rep in range(protocol['splits']):
                order = list(range(len(gids))); random.Random(seed + rep).shuffle(order)
                third = len(order) // 3
                groups = [order[:third], order[third:2*third], order[2*third:]]
                idx = [np.array([a*g+b for a in units for b in range(g)]) for units in groups]
                mapped = np.empty_like(raw)
                for m in range(len(models)):
                    ref = np.sort(raw[m, idx[0]])
                    mapped[m] = np.searchsorted(ref, raw[m], side='right') / len(ref)
                labels = np.tile(np.array([1, 0, 0, 0]), len(groups[2])) if name == 'RewardBench2' else None
                N = len(idx[2]); tie = np.random.default_rng(seed + rep + 700001).permutation(N)
                for aggregator in protocol['aggregators']:
                    base_ref, base_cal, base_test = (mapped[:M, ix] for ix in idx)
                    candidates_ref = mapped[M:, idx[0]]
                    # Hidden scores remain in runner closure, never in solver inputs.
                    hidden_candidates = mapped[M:, idx[2]]
                    consensus = aggregate(base_test, aggregator)
                    for q in protocol['quantiles']:
                        k = max(1, round(q*N)); budget = (2*k*H)//10
                        threshold = np.sort(aggregate(base_ref, aggregator))[-max(1, round(q*len(idx[0])))]
                        selected = consensus >= threshold
                        p = endpoint_cost(base_test, threshold, aggregator)
                        hidden_matrix = all_flips(base_test, hidden_candidates, threshold, aggregator)
                        cost = hidden_matrix.sum(axis=0)
                        assert np.all(hidden_matrix <= p[None, :])
                        p_cal = all_flips(base_cal, mapped[M:, idx[1]], threshold, aggregator).sum(axis=0)
                        lam = calibrate_envelope(p_cal/H, g, N/(2*k))
                        crc_keep = cost/H <= lam
                        common = {'dataset': name, 'aggregator': aggregator, 'split': rep,
                                  'q': q, 'k': k, 'H': H, 'T': T, 'alpha': 0.1,
                                  'n_test_items': N, 'integer_budget': budget,
                                  'active_selected_items': int((selected & (p>0)).sum()),
                                  'candidate_reference_entries': T*len(idx[0]),
                                  'pool_reference_entries': M*len(idx[0]),
                                  'pool_test_entries': M*N}
                        all_card = prefix(cost, budget, tie)
                        selected_opt = (p == 0).copy()
                        selected_opt[np.flatnonzero(selected)[prefix(cost[selected], budget, tie[selected])]] = True
                        true_V = int((selected_opt & selected).sum())
                        uniform = np.zeros(N, dtype=bool)
                        for value in np.unique(cost):
                            proposed = cost <= value
                            if int(cost[proposed].sum()) <= budget:
                                uniform = proposed
                            else:
                                break
                        zero_query = (p == 0).copy()
                        zero_query[np.flatnonzero(selected)[prefix((T*p)[selected], budget, tie[selected])]] = True
                        fixed = topk(consensus, k)
                        fixed_cost = np.zeros(N, dtype=np.int64)
                        for j in range(M):
                            for c in range(T):
                                replacement = base_test.copy(); replacement[j] = hidden_candidates[c]
                                fixed_cost += topk(aggregate(replacement, aggregator), k) != fixed
                        fixed_keep = np.zeros(N, dtype=bool)
                        fixed_keep[np.flatnonzero(fixed)[prefix(fixed_cost[fixed], budget, tie[fixed])]] = True
                        for method, keep, target, observed_cost in [
                            ('zero_query_structural', zero_query, selected, cost),
                            ('envelope_crc', crc_keep, selected, cost),
                            ('batch_uniform_threshold', uniform, selected, cost),
                            ('batch_max_cardinality', all_card, selected, cost),
                            ('batch_selected_optimum', selected_opt, selected, cost),
                            ('fixed_count_batch_selected_optimum', fixed_keep, fixed, fixed_cost)]:
                            row = {**common, 'method': method,
                                   'certificate': 'expectation_crc' if method == 'envelope_crc' else 'realized_batch',
                                   'candidate_test_entries': 0 if method == 'zero_query_structural' else N*T,
                                   'candidate_calibration_entries': T*len(idx[1]) if method == 'envelope_crc' else 0,
                                   'pool_calibration_entries': M*len(idx[1]) if method == 'envelope_crc' else 0,
                                   **metrics(observed_cost, target, keep, H, k, labels)}
                            baseline_rows.append(row)
                            if method != 'envelope_crc':
                                assert int(observed_cost[keep].sum()) <= budget
                                validation_checks += 1
                        prior = fit_prior(base_ref, candidates_ref, base_test, threshold, p, aggregator)
                        epsilon = int(math.ceil(0.02*selected.sum()))
                        for method in protocol['acquisition_methods']:
                            observed = set()
                            def query(candidate, item):
                                assert (candidate, item) not in observed
                                observed.add((candidate, item))
                                return float(hidden_candidates[candidate, item])
                            trace, states, tolerant, exact = solve(
                                base_test, selected, p, prior, threshold, aggregator, T,
                                budget, tie, method, seed+rep+99173, query,
                                protocol['inspection_checkpoints'], epsilon)
                            # Independently replay every revealed answer and every saved mask.
                            for c, i, f in trace:
                                assert hidden_matrix[c, i] == f
                            validation_checks += verify_path(trace, states, tolerant, exact,
                                                             cost, p, selected, T, budget, true_V, epsilon)
                            total_active = int((selected & (p>0)).sum())*T
                            for stopping, st in [('two_percent_gap', tolerant), ('exact_gap', exact)]:
                                keep = np.asarray(st['mask'], dtype=bool)
                                record = {**common, 'method': method, 'stopping': stopping,
                                          'epsilon': epsilon if stopping == 'two_percent_gap' else 0,
                                          'queries': st['queries'], 'active_entries': total_active,
                                          'active_fraction': st['queries']/total_active if total_active else 0.0,
                                          'panel_fraction': st['queries']/(N*T),
                                          'V_star': true_V, 'V_lower': st['V_lower'], 'V_upper': st['V_upper'],
                                          'certificate_gap': st['gap'], 'realized_regret': true_V-st['V_lower'],
                                          **metrics(cost, selected, keep, H, k, labels)}
                                if aggregator == 'median':
                                    z = cost[selected & (p>0)]//4
                                    Q, Qsafe, Qexclude = exact_offline_certificate(z, T, budget//4)
                                    record.update(offline_exact_certificate=Q,
                                                  offline_exact_safe_part=Qsafe,
                                                  offline_exact_exclusion_part=Qexclude)
                                    if stopping == 'exact_gap':
                                        assert st['queries'] >= Q
                                        validation_checks += 1
                                query_rows.append(record)
                            for st in states:
                                keep = np.asarray(st['mask'], dtype=bool)
                                allowance = st.get('budget_checkpoint_queries', st['queries'])
                                checkpoint_rows.append({**common, 'method': method,
                                                        'allowance_queries': allowance,
                                                        'allowance_fraction': allowance/total_active if total_active else 0.0,
                                                        'queries': st['queries'], 'V_lower': st['V_lower'],
                                                        'V_upper': st['V_upper'], 'V_star': true_V,
                                                        'certificate_gap': st['gap'],
                                                        **metrics(cost, selected, keep, H, k, labels)})
                            log.write(json.dumps({'key': [name, aggregator, rep, q, method],
                                                  'trace': trace, 'states': states,
                                                  'two_percent_stop': tolerant, 'exact_stop': exact},
                                                 separators=(',', ':'))+'\n')
                if rep%10 == 9:
                    print(name, 'completed splits', rep+1, 'elapsed',round(time.monotonic()-start,1),flush=True)
    bf = ['risk', 'coverage', 'selected_coverage', 'returned_count', 'precision', 'preferred_yield',
          'selected_review_count', 'nonselected_review_count']
    qf = bf + ['queries', 'active_fraction', 'panel_fraction', 'V_star', 'certificate_gap',
               'realized_regret', 'offline_exact_certificate', 'offline_exact_safe_part',
               'offline_exact_exclusion_part']
    payload = {'protocol': protocol, 'protocol_sha256': hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
               'numpy': np.__version__, 'datasets': datasets,
               'baseline_records': baseline_rows, 'query_records': query_rows,
               'checkpoint_records': checkpoint_rows,
               'baseline_cells': summary(baseline_rows, ['dataset','aggregator','q','method'], bf),
               'query_cells': summary(query_rows, ['dataset','aggregator','q','method','stopping'], qf),
               'checks': validation_checks, 'scientific_runtime_claim': None}
    (OUT/'query_metrics.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    for label in ['baseline', 'query']:
        rows = payload[label+'_cells']
        with (OUT/(label+'_cells.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=sorted(set().union(*(r.keys() for r in rows))))
            w.writeheader(); w.writerows(rows)
    receipt = {'status':'PASS_COMPLETE_FROZEN_PROTOCOL','checks':validation_checks,
               'query_paths':len(query_rows)//2,'baseline_records':len(baseline_rows),
               'trace_lines':len(query_rows)//2,'runtime_seconds':time.monotonic()-start,
               'runtime_scope':'local replay computation, not model inference',
               'protocol_sha256':payload['protocol_sha256'],
               'trace_sha256':hashlib.sha256(trace_path.read_bytes()).hexdigest()}
    (OUT/'query_validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (OUT/'query_validation.json').write_text(json.dumps({'status':'FAILED', 'error':traceback.format_exc()}, indent=2)+'\n')
        raise

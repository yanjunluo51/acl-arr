"""Full-score, grouped split analysis for the ARR manuscript. No model calls."""
from pathlib import Path
import json, random, statistics, csv
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
QS = (0.05, 0.10, 0.20, 0.30)
ALPHA = 0.10
SPLITS = 40


def calibrate(d, group_size, B, alpha=ALPHA):
    """Average itemwise losses within exchangeable groups, then calibrate."""
    groups = np.asarray(d).reshape(-1, group_size)
    n = len(groups)
    feasible = []
    for lam in sorted(set(d.tolist()) | {0.0}):
        risk = float(np.mean(np.mean(groups * (groups <= lam), axis=1))) * B
        if (n * risk + B) / (n + 1) <= alpha:
            feasible.append(lam)
    return max(feasible) if feasible else None


def calibrate_envelope(d, group_size, B, alpha=ALPHA):
    """Parameter-dependent deterministic envelope B*lambda for the SAME loss."""
    groups = np.asarray(d).reshape(-1, group_size)
    n = len(groups)
    feasible = []
    for lam in sorted(set(d.tolist()) | {0.0}):
        risk = float(np.mean(np.mean(groups * (groups <= lam), axis=1))) * B
        if (n * risk + B * lam) / (n + 1) <= alpha:
            feasible.append(lam)
    # Zero belongs to the search grid and always has zero loss/envelope.
    assert feasible
    return max(feasible)

def topk(v, k):
    mask = np.zeros(len(v), dtype=bool)
    mask[np.lexsort((np.arange(len(v)), v))[-k:]] = True
    return mask


def diagnostic(d, inc, keep, B, k, labels):
    risk = float(np.mean(d * keep)) * B
    cov = float(np.mean(keep))
    selected = int(np.sum(inc))
    returned = int(np.sum(inc & keep))
    quality = float(np.mean(labels[inc & keep])) if labels is not None and returned else None
    return dict(risk=risk, risk_over_alpha=risk / ALPHA,
                risk_given_commit=risk / cov if cov else None,
                coverage=cov, selected_coverage=returned / selected if selected else None,
                selected_count=selected, returned_count=returned,
                review_count=int(np.sum(~keep)), selected_review_count=int(np.sum(inc & ~keep)),
                size_over_k=selected / k, returned_over_k=returned / k,
                abs_size_deviation=abs(selected - k) / k, precision=quality)


def band(base, other, k):
    # A matched cutoff is diagnostic only; it is not used for calibration.
    S = topk(base, k)
    ii = np.arange(len(base))
    edge = np.lexsort((ii, base))[-k]
    Ap = (other > base[edge]) | ((other == base[edge]) & (ii >= edge))
    delta = int(Ap.sum()) - k
    if not delta:
        return 0, 0, 0
    if delta > 0:
        ids = np.where(Ap)[0]
        order = np.lexsort((ids, other[ids]))
        chosen = ids[order[:delta]]
        cancel = ~S[chosen]
        aligned = other[chosen] > base[chosen]
    else:
        ids = np.where(~Ap)[0]
        order = np.lexsort((ids, other[ids]))
        chosen = ids[order[-(-delta):]]
        cancel = S[chosen]
        aligned = other[chosen] < base[chosen]
    assert np.all(~cancel | aligned)
    return len(chosen), int(cancel.sum()), int(aligned.sum())


def panel(name, filename, seed, aggregators=('median', 'mean'), calibration_rule='constant'):
    blob = json.loads((ROOT / 'data' / filename).read_text())
    models, gids = blob['models'], blob['prompt_ids']
    g = len(blob.get('systems', [0, 1, 2, 3]))
    assert len(gids) == (1723 if name == 'RewardBench2' else 557)
    raw = np.array([[blob['scores'][m][p] for p in gids] for m in models], dtype=float).reshape(len(models), -1)
    assert np.isfinite(raw).all()
    pool = list(range(7)); cands = list(range(7, len(models)))
    swaps = [(j, c) for j in pool for c in cands]
    records = []
    for rep in range(SPLITS):
        order = list(range(len(gids))); random.Random(seed + rep).shuffle(order)
        third = len(order) // 3
        units = [order[:third], order[third:2*third], order[2*third:]]
        assert not(set(units[0]) & set(units[1]) or set(units[0]) & set(units[2]) or set(units[1]) & set(units[2]))
        idx = [np.array([j*g+c for j in u for c in range(g)]) for u in units]
        mapped = np.empty_like(raw)
        for m in range(len(models)):
            ref = np.sort(raw[m, idx[0]])
            mapped[m] = np.searchsorted(ref, raw[m], side='right') / len(ref)
        labels = (np.array([c == 0 for _ in units[2] for c in range(g)], dtype=float)
                  if name == 'RewardBench2' else None)
        for agg in aggregators:
            fn = np.median if agg == 'median' else np.mean
            base_all = fn(mapped[pool], axis=0)
            swap_all = np.array([fn(mapped[[c if m == j else m for m in pool]], axis=0) for j, c in swaps])
            base = [base_all[ix] for ix in idx]
            sw_cal, sw_te = swap_all[:, idx[1]], swap_all[:, idx[2]]
            for q in QS:
                N = len(idx[2]); k = max(1, round(q*N)); B = N/(2*k)
                t0 = np.sort(base[0])[-max(1, round(q*len(idx[0])))]
                inc_cal, inc_te = base[1] >= t0, base[2] >= t0
                d_cal = np.mean((sw_cal >= t0) != inc_cal, axis=0)
                d_te = np.mean((sw_te >= t0) != inc_te, axis=0)
                lam = (calibrate_envelope if calibration_rule == 'envelope' else calibrate)(d_cal, g, B)
                keep = np.zeros(N, bool) if lam is None else d_te <= lam
                # The legacy WMT scaling is retained only as a reconciliation diagnostic.
                legacy_lam = calibrate(d_cal, g, 1/(2*q))
                legacy_keep = np.zeros(N, bool) if legacy_lam is None else d_te <= legacy_lam
                legacy_risk = float(np.mean(d_te * legacy_keep))/(2*q)
                fixed = topk(base[2], k)
                f_sw = np.array([topk(v, k) for v in sw_te])
                d_fixed = np.mean(f_sw != fixed, axis=0)
                full_cutoff_churn = B * float(d_te.mean())
                full_fixed_churn = B * float(d_fixed.mean())
                D = (sw_te >= t0) != inc_te
                E = np.logical_xor(np.logical_xor(inc_te, fixed), np.logical_xor(sw_te >= t0, f_sw))
                den = int(E.sum()); num = int((E & D).sum())
                assert np.array_equal(np.sum(f_sw != fixed, axis=1) - np.sum(D, axis=1), np.sum(E, axis=1) - 2*np.sum(E & D, axis=1))
                bw=bc=bu=0
                for ob in sw_te:
                    w,c,u = band(base[2], ob, k);bw+=w;bc+=c;bu+=u
                common = dict(dataset=name, aggregator=agg, split=rep, q=q, alpha=ALPHA,
                              calibration_rule=calibration_rule, n_cal_groups=len(units[1]), group_size=g, n_test_items=N, k=k, B=B,
                              full_cutoff_churn=full_cutoff_churn, full_fixed_churn=full_fixed_churn,
                              gap=full_fixed_churn-full_cutoff_churn,
                              gamma_numerator=num, gamma_denominator=den,
                              band_width=bw, band_cancel=bc, band_up=bu, legacy_risk=legacy_risk)
                for rule, d, inc, committed, cert in [
                    ('cutoff_crc', d_te, inc_te, keep, True),
                    ('cutoff_all', d_te, inc_te, np.ones(N,bool), False),
                    ('fixed_count_all', d_fixed, fixed, np.ones(N,bool), False)]:
                    row = {**common, 'rule':rule,'certificate':cert,'threshold':lam if cert else None,
                           **diagnostic(d,inc,committed,B,k,labels)}
                    if cert:
                        row['rejected_churn']=B*float(np.mean(d_te*~keep))
                        assert abs(full_cutoff_churn-row['risk']-row['rejected_churn']) < 1e-12
                    records.append(row)
        if rep % 10 == 9: print(name, 'completed splits',rep+1,flush=True)
    return records, dict(models=models, pool=[models[j] for j in pool], candidates=[models[j] for j in cands],
                         seed=seed, group_size=g, splits=SPLITS, n_groups=len(gids), n_items=raw.shape[1], pairs=len(swaps), source=blob['source'])


def summarize(records):
    cells=[]
    groups={}
    for r in records:groups.setdefault((r['dataset'],r['aggregator'],r['q'],r['rule']),[]).append(r)
    fields=['risk','risk_over_alpha','risk_given_commit','coverage','selected_coverage','selected_count','returned_count','review_count','selected_review_count','size_over_k','returned_over_k','abs_size_deviation','precision','gap','full_cutoff_churn','full_fixed_churn','legacy_risk','rejected_churn']
    for key, rows in groups.items():
        cell=dict(zip(('dataset','aggregator','q','rule'),key),splits=len(rows),certificate=rows[0]['certificate'],n_cal_groups=rows[0]['n_cal_groups'],n_test_items=rows[0]['n_test_items'],k=rows[0]['k'],B=rows[0]['B'])
        for f in fields:
            vals=[r[f] for r in rows if r.get(f) is not None]
            cell[f]=statistics.fmean(vals) if vals else None
            if f=='precision':cell['nonempty_quality_splits']=len(vals)
        cell['over_budget_splits']=sum(r['risk']>ALPHA for r in rows)
        cell['risk_max']=max(r['risk'] for r in rows)
        cell['risk_se']=statistics.stdev(r['risk'] for r in rows)/len(rows)**0.5
        cell['size_sd']=statistics.stdev(r['selected_count'] for r in rows)
        cell['over_5pct']=statistics.fmean(r['abs_size_deviation']>0.05 for r in rows)
        cell['over_10pct']=statistics.fmean(r['abs_size_deviation']>0.10 for r in rows)
        correction_mass=sum(r['gamma_denominator'] for r in rows)
        band_mass=sum(r['band_width'] for r in rows)
        cell['gamma']=sum(r['gamma_numerator'] for r in rows)/correction_mass if correction_mass else None
        cell['beta_weighted']=sum(r['band_cancel'] for r in rows)/band_mass if band_mass else None
        cell['u_band_weighted']=sum(r['band_up'] for r in rows)/band_mass if band_mass else None
        cells.append(cell)
    return cells


def main():
    rb, rm=panel('RewardBench2','rb2_ranked_panel.json',20260815)
    mt, mm=panel('WMT23','wmt23_metric_panel.json',87000)
    records=rb+mt;cells=summarize(records)
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    payload={'protocol':'ARR common itemwise commit loss v1','alpha':ALPHA,'quantiles':QS,
             'environment':{'numpy':np.__version__},'datasets':{'RewardBench2':rm,'WMT23':mm},
             'quality_definition':'RewardBench completion index 0; WMT quality not evaluated without human labels',
             'aggregation':'equal-weight split means; gamma and band proportions pooled by respective masses',
             'cells':cells,'split_records':records}
    payload['calibration_rule']='constant B comparison'
    (out/'common_metrics.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    with (out/'common_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(cells[0]));w.writeheader();w.writerows(cells)
    er, erm=panel('RewardBench2','rb2_ranked_panel.json',20260815,calibration_rule='envelope')
    em, emm=panel('WMT23','wmt23_metric_panel.json',87000,calibration_rule='envelope')
    envelope={**payload, 'protocol':'ARR grouped committed loss with B-lambda envelope v2',
              'calibration_rule':'parameter-dependent B*lambda primary',
              'datasets':{'RewardBench2':erm,'WMT23':emm},
              'cells':summarize(er+em), 'split_records':er+em}
    (out/'envelope_metrics.json').write_text(json.dumps(envelope,indent=2,allow_nan=False)+'\n')
    with (out/'envelope_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(envelope['cells'][0]));w.writeheader();w.writerows(envelope['cells'])
    for c in cells:
        if c['aggregator']=='median' and c['rule']=='cutoff_crc':
            print(c['dataset'],c['q'],'risk/a',round(c['risk_over_alpha'],4),'cov',round(c['coverage'],4),'selected cov',round(c['selected_coverage'],4),'gap',round(c['gap'],6),'precision',c['precision'],flush=True)

if __name__=='__main__':main()

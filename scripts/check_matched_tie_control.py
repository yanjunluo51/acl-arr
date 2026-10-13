"""Reconcile every native/frozen result and independently check matched optima."""
from pathlib import Path
import argparse,csv,json,hashlib
import numpy as np
from run_matched_tie_control import geometry,OUT
ROOT=Path(__file__).resolve().parents[1]
def key(x):return x['dataset'],int(x['split']),x['aggregator'],float(x['q'])
def main(results_dir=None):
    global OUT
    if results_dir is not None:OUT=Path(results_dir).resolve()
    rows=list(csv.DictReader((OUT/'records.csv').open()));pairs=list(csv.DictReader((OUT/'paired.csv').open()))
    assert len(rows)==5760 and len(pairs)==1920
    original={}
    for folder in ['review-budget','review-external']:
        d=json.loads((ROOT/'outputs'/folder/'results.json').read_text())
        for r in d['baseline_records']:
            if r['alpha']==.1 and r['method'] in ['batch_selected_optimum','fixed_count_batch_selected_optimum']:
                original[key(r),r['method']]=r
    matches=0
    for r in rows:
        assert float(r['risk'])<=.1+1e-12 and int(r['integer_spent'])<=int(r['integer_budget'])
        if r['rule']=='fixed_matched':continue
        method='batch_selected_optimum' if r['rule']=='frozen_cutoff' else 'fixed_count_batch_selected_optimum'
        old=original[key(r),method]
        for field in ['selected_count','returned_count','selected_coverage','risk','replacement_max_risk','replacement_over_alpha_fraction']:
            assert abs(float(r[field])-old[field])<1e-12,(key(r),r['rule'],field,r[field],old[field])
        matches+=1
    masks={tuple(x['key']):x for x in json.loads((OUT/'masks.json').read_text())}
    recomputed=0;entryqueries=0
    # Independent sort orientation and greedy cardinality implementation.
    for r in rows:
        if r['rule']!='fixed_matched' or int(r['split']) not in [0,17]:continue
        panel,rep,agg,q=key(r);ref,score,sw,T,seed=geometry(panel,rep,agg)
        N=len(score);k=int(r['k']);budget=int(r['integer_budget'])
        tie=np.random.default_rng(seed+rep+700001).permutation(N)
        def top(x):
            chosen=sorted(range(N),key=lambda i:(-float(x[i]),int(tie[i])))[:k]
            out=np.zeros(N,dtype=bool);out[chosen]=True;return out
        base=top(score);bits=np.array([top(x)!=base for x in sw]);cost=bits.sum(axis=0)
        ids=sorted(np.flatnonzero(base),key=lambda i:(int(cost[i]),int(tie[i])))
        keep=np.zeros(N,dtype=bool);spent=0
        for i in ids:
            if spent+cost[i]>budget:break
            keep[i]=True;spent+=int(cost[i])
        saved=masks[(panel,rep,agg,q)]
        given=np.unpackbits(np.array(saved['matched'],dtype=np.uint8))[:N].astype(bool)
        assert np.array_equal(given,keep) and int(r['returned_count'])==keep.sum()
        assert hashlib.sha256(cost.astype('<i8').tobytes()).hexdigest()==r['selected_cost_sha256']
        assert int(r['selected_count'])==base.sum() and int(r['integer_spent'])==int(cost[keep].sum())
        risks=bits[:,keep].sum(axis=1)/(2*k)
        for f,v in [('risk',float(risks.mean())),('replacement_max_risk',float(risks.max())),
                    ('replacement_over_alpha_fraction',float(np.mean(risks>.1+1e-12))),
                    ('full_list_churn',int(cost.sum())/(2*k*len(sw)))]:
            assert abs(float(r[f])-v)<1e-12,(key(r),f)
        # Transport item priority on reindexing, checking every replacement.
        perm=np.random.default_rng(seed+rep+991901).permutation(N)
        for x in sw:
            transported=sorted(range(N),key=lambda i:(-float(x[perm[i]]),int(tie[perm[i]])))[:k]
            check=np.zeros(N,dtype=bool);check[perm[transported]]=True;assert np.array_equal(check,top(x))
        entryqueries+=N*len(sw);recomputed+=1
    assert matches==3840 and recomputed==96
    result={'status':'PASS_SCOPED_MATCHED_TIE_CONTROL','configurations':1920,'budget_feasibility_records':5760,
        'original_native_and_frozen_records_reconciled':matches,'matched_optima_independently_recomputed':recomputed,
        'matched_risk_fields_independently_recomputed':recomputed,
        'reindexing_equivariance_checked_on_all_replacements_for_96_configurations':True,
        'labels_loaded':False,'new_online_certificate':False,'physical_model_inference':False,
        'baseline_changed_configurations':sum(int(x['native_to_matched_baseline_changes'])>0 for x in pairs),
        'replacement_changed_configurations':sum(int(x['native_to_matched_replacement_changes'])>0 for x in pairs),
        'mask_changed_configurations':sum(int(x['native_to_matched_mask_changes'])>0 for x in pairs),
        'returned_ordering_sign_changed_configurations':sum(x['returned_comparison_sign_changed']=='True' for x in pairs)}
    (OUT/'independent-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results-dir',type=Path)
    main(p.parse_args().results_dir)

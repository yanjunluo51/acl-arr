"""Independent metric and aggregation checks, separate from trace analysis."""
import csv,json,math,hashlib
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import mapped
from query_selection import aggregate,endpoint_cost,all_flips
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/acquisition-mechanisms'
def ranking(v):
    order=sorted(range(len(v)),key=lambda i:v[i]);r=np.empty(len(v));a=0
    while a<len(v):
        b=a+1
        while b<len(v) and v[order[b]]==v[order[a]]:b+=1
        for i in order[a:b]:r[i]=(a+b-1)/2
        a=b
    return r

def rho(x,y):
    x,y=np.asarray(x,float),np.asarray(y,float)
    if len(x)<2 or x.max()==x.min() or y.max()==y.min():return None
    a,b=ranking(x),ranking(y);a-=a.mean();b-=b.mean()
    return float(math.fsum(a*b)/math.sqrt(math.fsum(a*a)*math.fsum(b*b)))

def eq(a,b):
    if a is None:assert b in ['',None]
    else:assert math.isclose(float(a),float(b),abs_tol=2e-8,rel_tol=2e-8),(a,b)

def main():
    rows=list(csv.DictReader((OUT/'split_diagnostics.csv').open()));summary=list(csv.DictReader((OUT/'summary.csv').open()))
    stops={(r['dataset'],r['aggregator'],r['split'],r['q'],r['tau'],r['method']):r for r in csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open())}
    keys=['dataset','aggregator','q','tau'];g={};matched=0
    for r in rows:
        for method in ['fixed','random','largest_width','reference_priority']:
            s=stops[(r['dataset'],r['aggregator'],r['split'],r['q'],r['tau'],method)]
            assert int(r[method+'_queries'])==int(s['queries']);matched+=1
        ref=int(r['reference_priority_queries']);width=int(r['largest_width_queries']);fixed=int(r['fixed_queries'])
        assert int(r['reference_minus_width'])==ref-width and int(r['reference_minus_fixed'])==ref-fixed
        assert int(r['reference_strict_best'])==int(ref<min(int(r[m+'_queries']) for m in ['fixed','random','largest_width']))
        g.setdefault(tuple(r[k] for k in keys),[]).append(r)
    metrics=['flip_mae','initial_row_rho','prestop_remaining_mae','prestop_row_rho','invariant_fraction','Q_epsilon','reference_witness_overhead','reference_minus_width','reference_minus_fixed']+[m+'_queries' for m in ['fixed','random','largest_width','reference_priority']]
    cells=0
    for s in summary:
        group=g[tuple(s[k] for k in keys)];assert len(group)==40
        for k in metrics:
            values=[float(r[k]) for r in group if r[k]!=''];assert len(values)==int(s[k+'_defined'])
            eq(np.mean(values) if values else None,s[k]);cells+=1
        assert int(s['reference_beats_width'])==sum(int(r['reference_minus_width'])<0 for r in group)
        assert int(s['reference_strict_best'])==sum(int(r['reference_strict_best']) for r in group)
        pairs=[(float(r['flip_mae']),int(r['reference_minus_width'])) for r in group if r['flip_mae']!='']
        eq(rho(*zip(*pairs)) if pairs else None,s['mae_vs_extra_queries_rho']);cells+=1
    metric_cases=0;panels=json.loads((ROOT/'review-revision/score-observation-implementation/protocol.json').read_text())['panels']
    indexed={(r['dataset'],r['aggregator'],int(r['split']),float(r['q']),r['tau']):r for r in rows}
    for panel in panels:
      for agg in ['median','mean']:
       for rep in [0,39]:
        ref,test,*_=mapped(panel,rep);rb,rc=ref[:7],ref[7:];base,candidates=test[:7],test[7:]
        for q in [.05,.30]:
            cutoff=np.sort(aggregate(rb,agg))[-max(1,round(q*ref.shape[1]))]
            p=endpoint_cost(base,cutoff,agg);rp=endpoint_cost(rb,cutoff,agg)
            def design(b,pv):return np.column_stack([np.ones(b.shape[1]),b.T,aggregate(b,agg)-cutoff,b.max(axis=0)-b.min(axis=0),pv/len(b)])
            x,xnew=design(rb,rp),design(base,p);response=all_flips(rb,rc,cutoff,agg).T
            penalty=np.diag([0]+[1]*(x.shape[1]-1))
            gram=np.array([[np.sum(x[:,i]*x[:,j]) for j in range(x.shape[1])] for i in range(x.shape[1])])
            cross=np.array([[np.sum(x[:,i]*response[:,r]) for r in range(response.shape[1])] for i in range(x.shape[1])])
            beta=np.linalg.solve(gram+penalty,cross);assert np.isfinite(beta).all()
            linear=sum(xnew[:,i,None]*beta[i,None,:] for i in range(x.shape[1]));assert np.isfinite(linear).all()
            pred=np.clip(linear,0,p[:,None]);truth=all_flips(base,candidates,cutoff,agg).T
            active=(aggregate(base,agg)>=cutoff)&(p>0);pred,truth,ap=pred[active],truth[active],p[active]
            mae=float(np.mean(np.abs(pred-truth)/ap[:,None])) if len(ap) else None
            eq(mae,indexed[(panel,agg,rep,q,'1/50')]['flip_mae'])
            eq(rho(pred.sum(axis=1),truth.sum(axis=1)),indexed[(panel,agg,rep,q,'1/50')]['initial_row_rho']);metric_cases+=1
    receipt={'status':'PASS_INDEPENDENT_METRIC_AND_SUMMARY_CHECKS','original_stop_counts_matched':matched,'summary_values_checked':cells,'independent_ridge_and_ranking_cases':metric_cases,'scope':'Separate scalar-reduction ridge fit, manual tie ranking and aggregate arithmetic; full trace reply/frontier checks are in execution.json. This is a consistency check, not a causal or new policy experiment.','hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'summary.csv',OUT/'split_diagnostics.csv',OUT/'execution.json',ROOT/'scripts/analyze_acquisition_mechanisms.py']}}
    (OUT/'independent-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='hashes'},indent=2))
if __name__=='__main__':main()

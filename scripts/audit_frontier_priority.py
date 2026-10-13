"""Independent source, integer bounds, first stops and actual retained masks."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import csv,gzip,json,math,statistics,sys
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from run_tolerance_sensitivity import scan_path
from query_selection import prefix,capacity
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/frontier-priority-20261005'

def main():
    assert json.loads((OUT/'run_progress.json').read_text())['status']=='COMPLETE_EXECUTION_PENDING_AUDIT'
    saved={}
    for x in csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open()):
        if x['aggregator']=='mean' and x['tau'] in ['0','1/50']:
            saved[(x['dataset'],int(x['split']),float(x['q']),x['tau'],x['method'])]=x
    rows=[];seen=set();replies=0
    with gzip.open(OUT/'traces.jsonl.gz','rt') as log:
        for res in map(json.loads,log):
            key=res['dataset'],res['split'],res['q'];assert key not in seen;seen.add(key)
            c=prepare((key[0],'mean',key[1],key[2]));ids=np.asarray(res['original_output_ids'],int)
            expected=c['ids'][np.argsort(c['tie'][c['ids']])];assert np.array_equal(ids,expected)
            assert c['N']==res['N'] and c['k']==res['k'] and c['budget']==res['budget'] and c['S']==res['selected_count']
            p=np.asarray(res['caps'],np.int64);assert np.array_equal(p,c['p'][ids])
            truth=c['f'][:,ids].T;Vstar=res['free']+capacity(truth.sum(axis=1),c['budget'])
            eps=math.ceil(.02*c['S'])
            for path in res['paths']:
                trace=np.asarray(path['trace'],np.int64).reshape(-1,3)
                assert len({(int(i),int(r)) for i,r,f in trace})==len(trace)
                if len(trace):assert np.array_equal(trace[:,2],truth[trace[:,0],trace[:,1]])
                independent=scan_path(p,trace[:,[0,2]],c['T'],c['budget'],res['free'],np.array([eps,0],np.int64))
                for j,stop in enumerate(['primary','exact']):
                    x=path['stops'][stop];Q=int(x['queries']);assert tuple(independent[j])==(Q,x['V_lower'],x['V_upper'])
                    lo=np.zeros(len(ids),np.int64);up=c['T']*p.copy()
                    for i,r,f in trace[:Q]:lo[i]+=f;up[i]-=p[i]-f
                    mask=prefix(up,c['budget'],np.arange(len(ids)))
                    assert res['free']+int(mask.sum())==x['V_lower']
                    uppercost=int(up[mask].sum());truecost=int(truth.sum(axis=1)[mask].sum())
                    assert truecost<=uppercost<=c['budget']
                    gap=x['V_upper']-x['V_lower'];regret=Vstar-x['V_lower'];assert 0<=regret<=gap<=([eps,0][j])
                    row=dict(dataset=key[0],split=key[1],q=key[2],stopping=stop,method=path['mode'],
                        queries=Q,K=x['V_lower'],V_upper=x['V_upper'],V_star=Vstar,gap=gap,regret=regret,
                        true_cost=truecost,upper_cost=uppercost,risk=truecost/(2*c['k']*7*c['T']),
                        selected_count=c['S'],epsilon=[eps,0][j],N=c['N'],T=c['T'],
                        active_rows=len(ids),policy_full_path_seconds=path['seconds'])
                    tau=['1/50','0'][j]
                    for method in ['fixed','random','largest_width','reference_priority']:
                        prior=saved[(*key,tau,method)]
                        assert int(prior['selected_count'])==c['S'] and int(prior['integer_budget'])==c['budget']
                        row[method+'_queries']=int(prior['queries'])
                    row['delta_reference']=Q-row['reference_priority_queries'];row['delta_width']=Q-row['largest_width_queries']
                    rows.append(row)
                replies+=len(trace)
    assert len(seen)==960 and len(rows)==5760
    summaries=[]
    for dataset in sorted({x['dataset'] for x in rows}):
        for q in [.05,.10,.20,.30]:
            for stop in ['primary','exact']:
                for method in ['joint','safety','exclusion']:
                    g=[x for x in rows if (x['dataset'],x['q'],x['stopping'],x['method'])==(dataset,q,stop,method)];assert len(g)==40
                    r=dict(dataset=dataset,q=q,stopping=stop,method=method,splits=40)
                    for field in ['queries','K','gap','regret','risk','delta_reference','delta_width','fixed_queries','random_queries','largest_width_queries','reference_priority_queries','policy_full_path_seconds']:
                        r[field]=statistics.fmean(x[field] for x in g)
                    for baseline in ['reference','width']:
                        r['wins_'+baseline]=sum(x['delta_'+baseline]<0 for x in g)
                        r['losses_'+baseline]=sum(x['delta_'+baseline]>0 for x in g)
                    summaries.append(r)
    for name,data in [('records.csv',rows),('summary.csv',summaries)]:
        with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    mainrows=[x for x in rows if x['method']=='joint' and x['stopping']=='primary']
    receipt=dict(status='PASS_FULL_FRONTIER_SOURCE_FIRST_STOPS_AND_CERTIFICATES',instances=len(seen),paths=2880,
        stop_records=len(rows),summary_cells=len(summaries),replies_checked=replies,
        main_wins_reference=sum(x['delta_reference']<0 for x in mainrows),
        main_losses_reference=sum(x['delta_reference']>0 for x in mainrows),
        main_wins_width=sum(x['delta_width']<0 for x in mainrows),
        main_losses_width=sum(x['delta_width']>0 for x in mainrows),
        main_mean_queries=statistics.fmean(x['queries'] for x in mainrows),
        main_mean_reference=statistics.fmean(x['reference_priority_queries'] for x in mainrows),
        main_mean_width=statistics.fmean(x['largest_width_queries'] for x in mainrows),
        quality_labels_used=False,score_model_inference_run=False,preregistered_unseen_evaluation=False)
    (OUT/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
    main()

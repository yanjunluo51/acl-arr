"""Full-information row/candidate interventions on complete frozen NLP instances.

These four variants diagnose discovery, not deployable baselines. They all use
actual query replies, identical endpoint bounds and first-stop certificates.
"""
import csv,gzip,heapq,json,math,multiprocessing,time,statistics
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from run_tolerance_sensitivity import histogram_capacity,scan_path
from query_selection import prefix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/query-mechanism-interventions'
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic','WMT24_en-de','WMT24_en-es','WMT24_ja-zh']
VARIANTS=['reference_priority','oracle_row','oracle_candidate','oracle_both']

def path(c,method):
    m,T=c['m'],c['T'];truth=c['truth'];pred=c['pred'];lp=c['lp'];tie=c['tie'][c['ids']]
    row_oracle=method in ('oracle_row','oracle_both');candidate_oracle=method in ('oracle_candidate','oracle_both')
    estimate=truth if row_oracle else c['ticks'];scale=1 if row_oracle or not c['quantized'] else 10**12
    rank=truth if candidate_oracle else c['ticks']
    order=np.array([np.lexsort((np.arange(T),rank[i])) for i in range(m)],dtype=np.int64).reshape(m,T)
    heap=[(np.sum(estimate[i]).item(),int(tie[i]),i) for i in range(m)];heapq.heapify(heap)
    known=np.zeros((m,T),bool);nseen=np.zeros(m,np.int64);lo=np.zeros(m,np.int64);up=T*lp.copy()
    lim=T*int(lp.max(initial=0))+1;lh=np.bincount(lo,minlength=lim);uh=np.bincount(up,minlength=lim)
    epsilon=math.ceil(c['S']/50);trace=[];stops={}
    for step in range(m*T+1):
        vl=c['free']+int(histogram_capacity(uh,c['budget']));vh=c['free']+int(histogram_capacity(lh,c['budget']))
        for e in (epsilon,0):
            if e not in stops and vh-vl<=e:
                keep=prefix(up,c['budget'],tie)
                assert int(keep.sum())==vl-c['free']
                stops[e]={'queries':step,'V_lower':vl,'V_upper':vh,'gap':vh-vl,'epsilon':e,'upper_cost':int(up[keep].sum()),'true_cost':int(truth.sum(axis=1)[keep].sum()),'active_mask':np.packbits(keep).tobytes().hex()}
        if 0 in stops:break
        _,_,i=heapq.heappop(heap);r=int(order[i,nseen[i]]);f=int(truth[i,r]);assert not known[i,r]
        lh[lo[i]]-=1;uh[up[i]]-=1;lo[i]+=f;up[i]-=int(lp[i])-f;lh[lo[i]]+=1;uh[up[i]]+=1
        known[i,r]=True;nseen[i]+=1;trace.append([i,r,f])
        if nseen[i]<T:
            value=int(lo[i])*scale+np.sum(np.where(known[i],0,estimate[i])).item()
            heapq.heappush(heap,(value,int(tie[i]),i))
    return {'method':method,'trace':trace,'stops':{'primary':stops[epsilon],'exact':stops[0]}}

def task(key):
    c=prepare(key);paths=[path(c,m) for m in VARIANTS]
    return {'key':key,'selected_count':c['S'],'active_rows':c['m'],'T':c['T'],'budget':c['budget'],'free':c['free'],'caps':c['lp'].tolist(),'paths':paths}

def main():
    OUT.mkdir(exist_ok=False);start=time.monotonic()
    # Panel names are read from the frozen diagnostics rather than assumed aliases.
    old=list(csv.DictReader((ROOT/'outputs/acquisition-mechanisms/split_diagnostics.csv').open()))
    keys=sorted({(x['dataset'],x['aggregator'],int(x['split']),float(x['q'])) for x in old})
    assert len(keys)==1920
    saved={(x['dataset'],x['aggregator'],int(x['split']),float(x['q']),x['tau']):x for x in old}
    rows=[];queries=0;checks=0
    (OUT/'execution.json').write_text(json.dumps({'status':'RUNNING','configuration_cases':0},indent=2)+'\n')
    with gzip.open(OUT/'traces.jsonl.gz','wt',compresslevel=1) as log,multiprocessing.get_context('spawn').Pool(3) as pool:
        for j,res in enumerate(pool.imap(task,keys,chunksize=2),1):
            panel,agg,rep,q=res['key']
            for pathrow in res['paths']:
                method=pathrow['method'];queries+=len(pathrow['trace'])
                for stopping,st in pathrow['stops'].items():
                    tau='1/50' if stopping=='primary' else '0';prior=saved[(panel,agg,rep,q,tau)]
                    if method=='reference_priority':
                        assert st['queries']==int(prior['reference_priority_queries']),(res['key'],st,prior)
                        checks+=1
                    x={'dataset':panel,'aggregator':agg,'split':rep,'q':q,'method':method,'stopping':stopping,'selected_count':res['selected_count'],'active_rows':res['active_rows'],'T':res['T'],'budget':res['budget']}
                    x.update({k:v for k,v in st.items() if k!='active_mask'})
                    x.update(reference_queries=int(prior['reference_priority_queries']),width_queries=int(prior['largest_width_queries']),fixed_queries=int(prior['fixed_queries']))
                    x['delta_reference']=st['queries']-x['reference_queries'];x['delta_width']=st['queries']-x['width_queries']
                    rows.append(x)
            log.write(json.dumps(res,separators=(',',':'))+'\n');log.flush()
            if j%80==0:
                receipt={'status':'RUNNING','configuration_cases':j,'elapsed_seconds':time.monotonic()-start}
                (OUT/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
                print(j,round(time.monotonic()-start,1),flush=True)
    groups={}
    for x in rows:groups.setdefault((x['dataset'],x['aggregator'],x['q'],x['method'],x['stopping']),[]).append(x)
    summary=[]
    for key,g in sorted(groups.items()):
        assert len(g)==40
        x=dict(zip(['dataset','aggregator','q','method','stopping'],key),splits=40)
        for f in ['queries','delta_reference','delta_width','V_lower','V_upper','gap','upper_cost','true_cost']:x[f]=statistics.fmean(a[f] for a in g)
        x['strict_improvements_reference']=sum(a['delta_reference']<0 for a in g);x['strict_losses_reference']=sum(a['delta_reference']>0 for a in g)
        summary.append(x)
    for name,data in [('records.csv',rows),('summary.csv',summary)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    receipt={'status':'PASS_FULL_EXECUTION_PENDING_INDEPENDENT_AUDIT','configuration_cases':len(keys),'paths':len(keys)*4,'stop_records':len(rows),'summary_cells':len(summary),'original_reference_stop_equalities':checks,'recorded_replies':queries,'new_model_inference':False,'oracle_variants_deployable':False,'elapsed_seconds':time.monotonic()-start}
    (OUT/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

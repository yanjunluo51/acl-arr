"""Exact joint minima on predefined four-selected-output subbatches.

Original reference maps/cutoffs and full candidate families are retained. This
is a separate small-batch certification task, not a full-panel minimum estimate.
"""
import csv,json,math,multiprocessing,statistics,time
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from joint_certificates import minimum_joint_certificate
from tolerance_certificates import minimum_gap_certificate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/joint-certificates'

def task(key):
    c=prepare(key);panel,agg,rep,q=key
    selected=np.flatnonzero(c['selected']);ids=selected[np.argsort(c['tie'][selected])[:4]]
    assert len(ids)>0
    rows=c['f'][:,ids].T.tolist();caps=c['p'][ids].tolist();m=len(ids);T=c['T'];k=max(1,round(q*m));b=2*k*7*T//10
    obs0=[0]*m;obs1=[0]*m
    # Existing evidence is the first floor(mT/4) eligible cells in seeded row,
    # candidate-index order, excluding invariant rows; unused slots stay unused.
    eligible=[(i,r) for i in range(m) if caps[i]>0 for r in range(T)]
    for i,r in eligible[:len(eligible)//4]:obs1[i]|=1<<r
    records=[]
    for history,obs in [('empty',obs0),('quarter',obs1)]:
        for epsilon in (0,1):
            result=minimum_joint_certificate(rows,caps,b,epsilon,obs,separated=True)
            if agg=='median' and history=='empty':
                old=minimum_gap_certificate([sum(row)//4 for row,p in zip(rows,caps) if p>0],T,b//4,epsilon)
                assert result['queries']==old['queries']
            x={'dataset':panel,'aggregator':agg,'split':rep,'q':q,'history':history,'epsilon':epsilon,'N':m,'T':T,'k':k,'budget':b,'queries':result['queries'],'split_queries':result['split_queries'],'sharing_saving':result['split_queries']-result['queries'],'V_lower':result['V_lower'],'V_upper':result['V_upper'],'true_optimum':result['true_optimum'],'observed_entries':sum(bin(v).count('1') for v in obs),'dual_use_entries':sum(0<v<p for row,p in zip(rows,caps) for v in row),'active_entries':sum(p>0 for p in caps)*T}
            x['dual_use_fraction']=x['dual_use_entries']/x['active_entries'] if x['active_entries'] else 0
            records.append(x)
            x.update(query_mask=result['query_mask'],safe_mask=result['safe_mask'],threshold=result.get('threshold',0),safe_target=result['safe_target'])
    return {'key':list(key),'full_panel_N':c['N'],'original_output_ids':ids.tolist(),'caps':caps,'flips':rows,'observed':{'empty':obs0,'quarter':obs1},'records':records}

def main():
    assert (OUT/'independent-check.json').is_file() and not (OUT/'instances.jsonl').exists()
    start=time.monotonic();old=list(csv.DictReader((ROOT/'outputs/acquisition-mechanisms/split_diagnostics.csv').open()))
    keys=sorted({(x['dataset'],x['aggregator'],int(x['split']),float(x['q'])) for x in old});assert len(keys)==1920
    records=[]
    with (OUT/'instances.jsonl').open('w') as f,multiprocessing.get_context('spawn').Pool(3) as pool:
        for j,x in enumerate(pool.imap(task,keys,chunksize=2),1):
            f.write(json.dumps(x,separators=(',',':'))+'\n');f.flush();records.extend(x['records'])
            if j%80==0:print(j,round(time.monotonic()-start,1),flush=True)
    groups={}
    for x in records:groups.setdefault((x['dataset'],x['aggregator'],x['q'],x['history'],x['epsilon']),[]).append(x)
    cells=[]
    for key,g in sorted(groups.items()):
        assert len(g)==40
        x=dict(zip(['dataset','aggregator','q','history','epsilon'],key),splits=40)
        for f in ['queries','split_queries','sharing_saving','true_optimum','dual_use_fraction','observed_entries']:x[f]=statistics.fmean(a[f] for a in g)
        x['strict_sharing_benefit']=sum(a['sharing_saving']>0 for a in g)
        x['positive_minima']=sum(a['queries']>0 for a in g)
        cells.append(x)
    for name,data in [('panel_records.csv',records),('panel_summary.csv',cells)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    receipt={'status':'PASS_FULL_SMALL_BATCH_EXECUTION_PENDING_INDEPENDENT_AUDIT','configuration_cases':len(keys),'joint_certificates':len(records),'summary_cells':len(cells),'maximum_selected_batch_size':4,'full_candidate_families_retained':True,'full_panel_minimum_claim':False,'new_model_inference':False,'elapsed_seconds':time.monotonic()-start}
    (OUT/'panel-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

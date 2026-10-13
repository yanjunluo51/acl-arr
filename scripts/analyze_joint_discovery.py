"""Complete original policies on exactly the declared small-batch tasks."""
import csv,json,statistics,time
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from review_accelerated import solve_multi
from review_priority import solve_multi_quantized
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/joint-certificates'

def main():
    assert (OUT/'panel-execution.json').exists() and not (OUT/'discovery_records.csv').exists()
    start=time.monotonic();records=[];traces=[];cases=0
    with (OUT/'discovery_paths.jsonl').open('w') as log:
        for line in (OUT/'instances.jsonl').open():
            z=json.loads(line);key=tuple(z['key']);c=prepare(key);ids=np.array(z['original_output_ids'],int)
            base=c['base'][:,ids];hidden=c['hidden'][:,ids];p=c['p'][ids];prior=c['prior'][ids];selected=np.ones(len(ids),bool);tie=c['tie'][ids]
            assert np.array_equal(c['f'][:,ids].T,np.array(z['flips']))
            solve=solve_multi_quantized if c['quantized'] else solve_multi
            paths=[]
            for method in ('fixed','random','largest_width','reference_priority'):
                trace,_,tol,exact=solve(base,selected,p,prior,c['cutoff'],key[1],c['T'],np.array([z['records'][0]['budget']],int),tie,method,c['seed']+key[2]+99173,lambda r,i:float(hidden[r,i]),[],1)
                paths.append({'method':method,'trace':trace,'primary':tol[0],'exact':exact[0]})
                for e,st in [(0,exact[0]),(1,tol[0])]:
                    minimum=next(x['queries'] for x in z['records'] if x['history']=='empty' and x['epsilon']==e)
                    assert st['queries']>=minimum
                    row={'dataset':key[0],'aggregator':key[1],'split':key[2],'q':key[3],'epsilon':e,'method':method,'queries':st['queries'],'minimum':minimum,'discovery_ratio':st['queries']/minimum if minimum else None}
                    records.append(row)
            log.write(json.dumps({'key':list(key),'predictions':prior.tolist(),'ties':tie.tolist(),'paths':paths},separators=(',',':'))+'\n')
            cases+=1
            if cases%320==0:print(cases,round(time.monotonic()-start,1),flush=True)
    groups={}
    for x in records:groups.setdefault((x['dataset'],x['aggregator'],x['q'],x['epsilon'],x['method']),[]).append(x)
    summary=[]
    for key,g in sorted(groups.items()):
        x=dict(zip(['dataset','aggregator','q','epsilon','method'],key),splits=40)
        ratios=[a['discovery_ratio'] for a in g if a['discovery_ratio'] is not None]
        x.update(queries=statistics.fmean(a['queries'] for a in g),minimum=statistics.fmean(a['minimum'] for a in g),positive_minima=len(ratios),mean_ratio=statistics.fmean(ratios) if ratios else None,max_ratio=max(ratios) if ratios else None)
        summary.append(x)
    for name,data in [('discovery_records.csv',records),('discovery_summary.csv',summary)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    receipt={'status':'PASS_COMPLETE_SMALL_BATCH_ORIGINAL_POLICY_EXECUTION','configuration_cases':cases,'original_policies':4,'paths':cases*4,'stopping_records':len(records),'summary_cells':len(summary),'full_panel_minimum_claim':False,'elapsed_seconds':time.monotonic()-start}
    (OUT/'discovery-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,csv,time,collections
import numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1];sys.path.insert(0,str(R/'scripts'))
from run_tolerance_sensitivity import configurations
from mapping_column_experiments import map_scores
from query_selection import aggregate,all_flips,capacity

def main():
 assert not (D/'risk-records.jsonl').exists()
 start=time.monotonic();previous=None;n=0;cells=collections.defaultdict(list);seen=set()
 with (D/'risk-records.jsonl').open('w') as out:
  for key,method,trace,tol,exact in configurations():
   if key!=previous:
    panel,agg,rep,q=key;ref,test,_,_,_=map_scores(panel,rep,'1','right');base=test[:7];cand=test[7:];T,N=cand.shape;M=7;k=max(1,round(q*N));b=2*k*M*T//10
    cutoff=np.sort(aggregate(ref[:7],agg))[-max(1,round(q*ref.shape[1]))];selected=aggregate(base,agg)>=cutoff
    flips=np.empty((T,M,N),bool)
    for c in range(T):
     for j in range(M):
      changed=base.copy();changed[j]=cand[c];flips[c,j]=(aggregate(changed,agg)>=cutoff)!=selected
    truth=all_flips(base,cand,cutoff,agg)
    assert np.array_equal(flips.sum(axis=1),truth)
    trueV=capacity(truth.sum(axis=0)[selected],b);previous=key
   for st,s in [('primary',tol),('exact',exact)]:
    mask=np.asarray(s['mask'],bool);assert mask.shape==(N,)
    counts=flips[:,:,mask].sum(axis=2).reshape(-1).astype(int);risk=counts/(2*k);total=int(counts.sum());assert total<=b
    retained=int(np.sum(selected&mask));assert retained==s['V_lower']<=trueV<=s['V_upper']
    assert int(truth[:,mask].sum())==total
    over=int(np.sum(10*counts>2*k))
    x=dict(dataset=panel,aggregator=agg,split=rep,q=q,method=method,stopping=st,k=k,H=M*T,returned=retained,queries=s['queries'],average_risk=float(risk.mean()),max_risk=float(risk.max()),p95_risk=float(np.quantile(risk,.95,method='linear')),over_replacements=over,over_fraction=over/(M*T),flip_counts=counts.tolist(),scenario_order='candidate-major,base-member-minor')
    identity=(*key,method,st);assert identity not in seen;seen.add(identity)
    out.write(json.dumps(x,separators=(',',':'))+'\n');cells[panel,agg,q,method,st].append(x);n+=1
   if n%640==0:
    out.flush();progress=dict(status='RUNNING',masks=n,expected=15360,seconds=time.monotonic()-start);(D/'risk-progress.json').write_text(json.dumps(progress));print(progress,flush=True)
 assert n==15360
 summaries=[]
 for key,rs in sorted(cells.items()):
  assert len(rs)==40
  z=dict(zip(['dataset','aggregator','q','method','stopping'],key));z.update(masks=40,any_over_masks=sum(x['over_replacements']>0 for x in rs))
  for field in ['average_risk','max_risk','p95_risk','over_fraction']:z['mean_'+field]=float(np.mean([x[field] for x in rs]))
  z['maximum_risk']=max(x['max_risk'] for x in rs);summaries.append(z)
 with (D/'risk-summary.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
 result=dict(status='EXECUTED_PENDING_AUDIT',masks=n,cells=len(summaries),average_budget_violations=0,seconds=time.monotonic()-start,new_scoring=False)
 (D/'risk-progress.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
if __name__=='__main__':main()

"""Independent vectorized equation check of prespecified path checkpoints."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import gzip,json,time,hashlib
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from audit_deduplicated_evidence import capacity
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/frontier-priority-20261005'
def choice(p,pred,known,lo,up,B,mode):
 m,T=pred.shape;vl,vh=capacity(up.tolist(),B),capacity(lo.tolist(),B)
 estimate=lo*10**12+np.where(known,0,pred).sum(axis=1)
 order=np.argsort(estimate,kind='stable');guess=capacity(estimate.tolist(),B*10**12)
 s=min(vh,max(vl+1,guess));safe=np.zeros(m,bool);safe[order[:s]]=True
 ds=int(up[safe].sum())-B;assert ds>0
 utility=np.zeros((m,T),float);f=pred/10**12
 if mode!='exclusion':utility+=safe[:,None]*(p[:,None]-f)/ds
 if s<m:
  t=(int(estimate[order[s]])+10**12-1)//10**12
  de=sum(max(0,t-int(v)) for v in lo)-(s+1)*t+B+1
  if de>0 and mode!='safety':utility+=np.minimum(f,np.maximum(0,t-lo)[:,None])/de
 ticks=np.rint(utility*10**12).astype(np.int64);ticks[known]=-1
 if ticks.max()<=0:
  eligible=np.any(~known,axis=1);width=up-lo;width[~eligible]=-1
  i=int(np.argmax(width));r=int(np.flatnonzero(~known[i])[0]);return i,r
 i,r=np.unravel_index(np.argmax(ticks),ticks.shape);return int(i),int(r)
def main():
 checked=paths=instances=0;start=time.monotonic()
 for x in map(json.loads,gzip.open(OUT/'traces.jsonl.gz','rt')):
  if x['split'] not in [0,20]:continue
  c=prepare((x['dataset'],'mean',x['split'],x['q']));ids=np.array(x['original_output_ids']);p=c['p'][ids];prior=c['prior'][ids]
  pred=np.rint(np.clip(prior,0,p[:,None])*10**12).astype(np.int64);m,T=pred.shape
  for path in x['paths']:
   tr=path['trace'];Qp=path['stops']['primary']['queries'];targets=set(range(min(100,len(tr))))|{max(0,Qp-1),len(tr)//2,max(0,len(tr)-1)}
   known=np.zeros((m,T),bool);lo=np.zeros(m,np.int64);up=T*p.copy()
   for j,(i,r,f) in enumerate(tr):
    if j in targets:assert choice(p,pred,known,lo,up,c['budget'],path['mode'])==(i,r),(x['dataset'],x['split'],x['q'],path['mode'],j);checked+=1
    known[i,r]=True;lo[i]+=f;up[i]-=p[i]-f
   paths+=1
  instances+=1
 assert instances==48 and paths==144
 receipt=dict(status='PASS_INDEPENDENT_FRONTIER_EQUATION_CHECKPOINTS',instances=instances,paths=paths,choices=checked,checkpoints='first 100, last, middle and pre-primary stop; split 0 and 20, all panels/depths/variants',all_replies_and_first_stops_checked_separately=True,seconds=time.monotonic()-start,selector_sha256=hashlib.sha256((ROOT/'scripts/frontier_priority.py').read_bytes()).hexdigest())
 (OUT/'choice-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

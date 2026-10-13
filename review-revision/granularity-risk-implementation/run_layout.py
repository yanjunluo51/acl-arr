import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,time,collections
import numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1];sys.path.insert(0,str(R/'review-revision/evidence-structure-revision'))
from column_union import frontiers,envelope,optimize,direct

def transformed(rows,layout):
 if layout=='original':return rows.copy()
 a=np.sort(rows,axis=1,kind='stable')
 if layout=='aligned_ascending':return a
 if layout=='cyclic_ascending':return np.array([np.roll(row,i%rows.shape[1]) for i,row in enumerate(a)])
 rng=np.random.default_rng(int(layout.rsplit('_',1)[1]));return np.array([rng.permutation(row) for row in rows])

def main():
 protocol=json.loads((D/'protocol.json').read_text())['mean_layout'];cases={};eps={}
 for x in map(json.loads,(R/'outputs/full-mean-grid-20261005/records.jsonl').open()):
  if sum(map(sum,x['rows']))<=x['budget']:continue
  key=(x['dataset'],x['split'],x['q']);cases[key]=x;eps.setdefault(key,{})[x['stopping']]=x['epsilon']
 assert len(cases)==57
 # Verify original layout against independently saved earlier column optima.
 old={(x['dataset'],x['split'],x['q'],x['stopping']):x for x in map(json.loads,(R/'review-revision/evidence-structure-revision/column-records.jsonl').open())}
 path=D/'layout-records.jsonl';assert not path.exists();n=0;t0=time.monotonic()
 with path.open('w') as out:
  for key,x in sorted(cases.items()):
   rows=np.asarray(x['rows'],np.int64);caps=np.asarray(x['caps'],np.int64);T=x['T']
   for layout in protocol['layouts']:
    a=transformed(rows,layout);assert np.array_equal(np.sort(a,axis=1),np.sort(rows,axis=1))
    grouped,freq=np.unique(np.column_stack([caps,a]),axis=0,return_counts=True)
    vl,vh,pc=frontiers(grouped[:,1:],grouped[:,0],freq,x['budget']);A,Z=envelope(vl,vh,pc,T,len(caps))
    for st,e in sorted(eps[key].items()):
     j,jm,u,am,bm,s,na,nb,sp=map(int,optimize(vl,vh,pc,A,Z,int(vl[-1]),e))
     y=dict(rows=a.tolist(),caps=caps.tolist(),T=T,budget=x['budget'])
     assert direct(y,jm)[1]-direct(y,jm)[0]<=e and direct(y,am)[0]>=s and direct(y,bm)[1]<=s+e
     if layout=='original':assert (j,u)==(old[(*key,st)]['joint'],old[(*key,st)]['union'])
     z=dict(dataset=key[0],split=key[1],q=key[2],layout=layout,stopping=st,epsilon=e,T=T,budget=x['budget'],selected=len(caps),true_count=int(vl[-1]),joint=j,union=u,split_cost=sp,joint_mask=jm,safety_mask=am,exclusion_mask=bm,safe_target=s,safety_minimum=na,exclusion_minimum=nb,strict_gain=u-j,subsets=len(pc))
     out.write(json.dumps(z,separators=(',',':'))+'\n');n+=1
    out.flush();p=dict(status='RUNNING',records=n,expected=570,seconds=time.monotonic()-t0);(D/'layout-progress.json').write_text(json.dumps(p));print(p,flush=True)
 assert n==570;p['status']='EXECUTED_PENDING_AUDIT';(D/'layout-progress.json').write_text(json.dumps(p,indent=2))
if __name__=='__main__':main()

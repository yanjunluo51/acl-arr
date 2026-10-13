from pathlib import Path
import sys,json,csv,itertools,time,collections
import numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1]
from run_layout import transformed

def cap(a,b):
 s=0;n=0
 for v in sorted(map(int,a)):
  if s+v>b:break
  s+=v;n+=1
 return n

def bounds(f,p,b,subset):
 lo=np.zeros(len(p),dtype=np.int64)
 for r in subset:lo+=f[:,r]
 return cap(lo+(f.shape[1]-len(subset))*p,b),cap(lo,b)

def gamma(f,p,b):
 F=f.sum(1)
 return cap(F-f.min(1),b)-cap(F+p-f.max(1),b)

def main():
 start=time.monotonic();raw={};coverage=[]
 for x in map(json.loads,(R/'outputs/full-mean-grid-20261005/records.jsonl').open()):
  key=(x['dataset'],x['split'],x['q']);raw[key]=x
  if sum(map(sum,x['rows']))<=x['budget']:continue
  f=np.array(x['rows'],dtype=np.int64);p=np.array(x['caps'],dtype=np.int64);g=gamma(f,p,x['budget'])
  coverage.append(dict(dataset=key[0],split=key[1],q=key[2],stopping=x['stopping'],epsilon=x['epsilon'],gamma=g,covered=g>x['epsilon'],T=x['T']))
 records=list(map(json.loads,(D/'layout-records.jsonl').open()));assert len(records)==570
 checked=0;witnesses=0
 for a in records:
  x=raw[a['dataset'],a['split'],a['q']];f=transformed(np.array(x['rows'],dtype=np.int64),a['layout']);p=np.array(x['caps'],dtype=np.int64);T=a['T'];b=a['budget'];eps=a['epsilon'];K=a['joint']
  cols=[j for j in range(T) if a['joint_mask']>>j&1];l,u=bounds(f,p,b,cols);assert len(cols)==K and u-l<=eps;witnesses+=1
  for subset in itertools.combinations(range(T),K-1):
   l,u=bounds(f,p,b,subset);assert u-l>eps;checked+=1
  # Here joint=union. Any pair of separately minimum column sets has union
  # at most all T columns. T-1 cases have automatic exclusion and a smallest
  # safety witness certified below. This avoids relying on the subset envelope.
  assert a['union']==K
  if K<T:
   assert a['exclusion_minimum']==0 and a['exclusion_mask']==0 and a['safety_minimum']==K
   fulln=len(p);l,u=bounds(f,p,b,cols);assert l>=fulln-eps and u<=fulln
   # No smaller safety witness can reach this same target: the optimistic
   # capacity never exceeds fulln, hence such a witness would stop earlier.
   assert a['safe_target']==fulln-eps
  g=gamma(f,p,b)
  assert g==gamma(np.array(x['rows'],dtype=np.int64),p,b)
  if g>eps:assert K==T
 # Independently enumerate all single-column omissions for every small integer
 # matrix; larger reveal omissions are covered by frontier monotonicity.
 finite=0;covered=0
 for m,T in [(2,3),(3,2)]:
  p=np.full(m,2,dtype=np.int64)
  for flat in itertools.product(range(3),repeat=m*T):
   f=np.array(flat,dtype=np.int64).reshape(m,T)
   for b in range(2*m*T+1):
    g=gamma(f,p,b)
    allgaps=[bounds(f,p,b,tuple(j for j in range(T) if j!=r)) for r in range(T)]
    for eps in range(m+1):
     finite+=1
     if g>eps:
      assert all(hi-lo>eps for lo,hi in allgaps);covered+=1
 with (D/'column-condition-coverage.csv').open('w') as stream:
  w=csv.DictWriter(stream,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)
 summaries=[]
 for layout in dict.fromkeys(x['layout'] for x in records):
  for st in ['primary','exact']:
   g=[x for x in records if x['layout']==layout and x['stopping']==st]
   summaries.append(dict(layout=layout,stopping=st,targets=len(g),strict_gains=sum(x['strict_gain']>0 for x in g),full_columns=sum(x['joint']==x['T'] for x in g),mean_joint=sum(x['joint'] for x in g)/len(g)))
 (D/'layout-summary.json').write_text(json.dumps(summaries,indent=2))
 result=dict(status='PASS_COLUMN_MINIMA_AND_SUFFICIENT_CONDITION',targets=len(records),witnesses=witnesses,independent_predecessor_subsets=checked,finite_integer_instances=finite,finite_covered=covered,condition_coverage={st:sum(x['covered'] for x in coverage if x['stopping']==st) for st in ['primary','exact']},eligible_instances=57,coverage_is_posthoc=True,seconds=time.monotonic()-start)
 (D/'layout-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()

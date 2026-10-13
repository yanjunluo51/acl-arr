"""Try stronger LP bounds by enumerating integer safe targets at hard levels."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,time,copy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import disaggregated_threshold as dt
from highs_adapter import milp
from audit_full_mean_grid import valuecheck
from audit_deduplicated_evidence import capacity
dt.milp=milp
def targets(x):
 active=[r for r,p in zip(x['rows'],x['caps']) if p];m=len(active);L=capacity(list(map(sum,active)),x['budget']);eps=x['epsilon'];a=max(0,L-eps)
 ss=list(range(a,min(L,m-eps-1)+1))
 if max(a,m-eps)<=L:ss.append(max(a,m-eps))
 return ss
def run(x,kind,t,seconds=20,relaxation=True,s=None):
 r=dt.certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],seconds=seconds,separated=kind=='separate',fixed_threshold=t,fixed_target=s,presolve=True,incumbent=x[kind],relaxation=relaxation,improving_only=not relaxation)
 valuecheck(x,r,kind=='separate');return r
if __name__=='__main__':
 # The union of fixed targets is exactly the original safe-target range.
 # Check the fully enumerated small synthetic model against the original solver.
 import bounded_threshold_certificate as old
 old.milp=milp
 for rows,caps,B,eps in [([[1,0],[0,1]],[2,1],1,0),([[1,1],[1,0],[0,0]],[2,2,1],2,1),([[0,2],[1,0]],[2,1],1,0)]:
  z=old.certificate(rows,caps,B,eps,seconds=10);x=dict(rows=rows,caps=caps,observed=[0]*len(rows),T=len(rows[0]),budget=B,epsilon=eps,joint=z)
  got=[]
  for s in targets(x):
   for t in range(max(map(sum,rows))+1):got.append(run(x,'joint',t,10,False,s)['joint_lower_bound'])
  assert min(got)==z['objective']
 (OUT/'disaggregation-check.json').write_text(json.dumps(dict(status='PASS_FIXED_TARGET_PARTITION_ON_THREE_SMALL_CASES',model_change='only fixes integer target in an exhaustive partition'),indent=2)+'\n')
 with (OUT/'disaggregated-attempts.jsonl').open('x') as f:
  for c in map(json.loads,(OUT/'candidate-closures.jsonl').open()):
   x=c['closed']
   for kind,aa in c['threshold_attempts'].items():
    if x[kind]['joint_optimal']:continue
    for a in aa:
     if a['result']['joint_lower_bound']>=x[kind]['objective']:continue
     t=a['threshold'];rs=[]
     for s in targets(x):
      r=run(x,kind,t,30,True,s);rs.append(dict(target=s,result=r))
     record=dict(key=c['key'],kind=kind,threshold=t,targets=targets(x),attempts=rs,lower=min(z['result']['joint_lower_bound'] for z in rs),incumbent=x[kind]['objective'])
     f.write(json.dumps(record)+'\n');f.flush();print(c['key'],kind,t,record['lower'],record['incumbent'],flush=True)
 print('ALL_DISAGGREGATED_LP_ATTEMPTS_TERMINAL',flush=True)

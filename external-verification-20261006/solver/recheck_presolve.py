"""Independently disable presolve for newly pivotal infeasibility receipts."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,time,multiprocessing
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from bounded_threshold_certificate import certificate
from audit_full_mean_grid import valuecheck
def solve(task):
 c,kind,t=task;x=c['closed'];best=x[kind]
 r=certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],seconds=300,separated=kind=='separate',fixed_threshold=t,presolve=False,incumbent=best,improving_only=True)
 valuecheck(x,r,kind=='separate')
 return dict(key=c['key'],kind=kind,threshold=t,expected_minimum=best['objective'],result=r,check='PASS' if r['joint_lower_bound']>=best['objective'] and r['objective']==best['objective'] else 'REQUIRES_FOLLOWUP')
if __name__=='__main__':
 seen=set();jobs=[]
 with (OUT/'presolve-recheck.jsonl').open('x') as f,multiprocessing.get_context('spawn').Pool(2) as pool:
  terminal=False
  while not terminal or jobs:
   data=(OUT/'candidate-closures.jsonl').read_bytes()
   for raw in data[:data.rfind(b'\n')+1].splitlines():
    c=json.loads(raw)
    for kind,aa in c['threshold_attempts'].items():
     old=c['primary'][kind];new=c['closed'][kind]
     if not new['joint_optimal'] or old['joint_optimal']:continue
     for a in aa:
      oldbound=max((r['joint_lower_bound'] for r in a['attempts'] if not(r.get('presolve') and r.get('improving_only'))),default=0)
      last=a['attempts'][-1];key=(*c['key'],kind,a['threshold'])
      if oldbound<new['objective'] and any(r['status']==2 for r in last['calls']) and key not in seen:
       seen.add(key);jobs.append((key,pool.apply_async(solve,((c,kind,a['threshold']),))))
   for key,j in jobs[:]:
    if j.ready():
     r=j.get();f.write(json.dumps(r)+'\n');f.flush();jobs.remove((key,j));print(key,r['check'],flush=True)
   terminal='ALL_ATTEMPTS_TERMINAL' in (OUT/'run.log').read_text()
   if not terminal or jobs:time.sleep(1)
 print('ALL_PRESOLVE_RECHECKS_TERMINAL',flush=True)

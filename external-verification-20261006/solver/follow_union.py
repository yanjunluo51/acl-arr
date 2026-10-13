"""Follow completed union attempts with the same model in modern HiGHS."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,time,copy,multiprocessing,traceback
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import target_aware_union as tu
from highs_adapter import milp
from target_bound_certificate import certify
from audit_deduplicated_evidence import witness
from verify_union_shortcut import verify
tu.milp=milp
CLOSED={'OPTIMAL','PROVED_BY_JOINT_LOWER_BOUND','PROVED_BY_BOUND_SANDWICH'}
def read(n):
 b=(OUT/n).read_bytes();return [json.loads(l) for l in b[:b.rfind(b'\n')+1].splitlines()]
def solve(task):
 key,x,priors=task;start=time.monotonic();name='-'.join(map(str,key))
 def save(e):
  with (OUT/(name+'.union-follow-progress.jsonl')).open('a') as f:f.write(json.dumps(e)+'\n')
 try:
  u=tu.union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],seconds=300,total_seconds=1500,presolve=True,certified_joint_minimum=x['joint']['objective'],prior_results=priors,progress=save)
  if u['status']=='OPTIMAL':witness(x,u)
  elif u['status']=='PROVED_BY_JOINT_LOWER_BOUND':verify(x,u)
  proof=certify(x,priors+[u])
  return dict(key=key,case=x,prior_results=priors,result=u,global_proof=proof,seconds=time.monotonic()-start)
 except Exception:return dict(key=key,status='FAILED_ATTEMPT',error=traceback.format_exc(),seconds=time.monotonic()-start)
if __name__=='__main__':
 assert json.loads((OUT/'target-bound-check.json').read_text())['cases']==391
 first={tuple(c['key']):c for c in read('candidate-closures.jsonl')};diss={tuple(c['key']):c for c in read('disaggregated-closures.jsonl')}
 seen=set();jobs=[]
 with (OUT/'union-followthrough.jsonl').open('x') as f,(OUT/'union-follow-failures.jsonl').open('x') as err,multiprocessing.get_context('spawn').Pool(2) as pool:
  terminal=False
  while not terminal or jobs:
   candidates=list(diss.values())+read('resume-closures.jsonl')
   for c in candidates:
    key=tuple(c['key'])
    if key in seen:continue
    seen.add(key);x=c['closed'];priors=[u for u in [first[key]['primary'].get('union'),first[key]['closed'].get('union'),x.get('union')] if u]
    if x.get('union') and x['union']['status'] in CLOSED:continue
    assert x['joint']['joint_optimal'] and x['separate']['joint_optimal']
    proof=certify(x,priors)
    if proof:
     f.write(json.dumps(dict(key=list(key),case=x,prior_results=priors,result=x['union'],global_proof=proof,seconds=0))+'\n');f.flush();continue
    jobs.append((key,pool.apply_async(solve,((list(key),x,priors),))))
   for key,j in jobs[:]:
    if j.ready():
     r=j.get();target=err if r.get('status')=='FAILED_ATTEMPT' else f;target.write(json.dumps(r)+'\n');target.flush();jobs.remove((key,j))
     print(key,r.get('status')or ('CLOSED_BY_TARGET_BOUNDS' if r['global_proof'] else r['result']['status']),round(r['seconds'],1),flush=True)
   terminal='ALL_RESUME_ATTEMPTS_TERMINAL' in (OUT/'resume.log').read_text()
   if not terminal or jobs:time.sleep(1)
 print('ALL_UNION_FOLLOWTHROUGH_TERMINAL',flush=True)

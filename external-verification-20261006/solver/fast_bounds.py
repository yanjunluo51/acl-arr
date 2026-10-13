"""Same-instance continuation with installed highspy; no model/data changes."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,time,copy,multiprocessing,traceback
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import bounded_threshold_certificate as bt
import resumable_union as ru
from highs_adapter import milp
from audit_full_mean_grid import valuecheck
from audit_deduplicated_evidence import witness
from verify_union_shortcut import verify
bt.milp=ru.milp=milp
def solve(c):
 x=copy.deepcopy(c['closed']);old=copy.deepcopy(x);key=c['key'];name='-'.join(map(str,key));attempts={};start=time.monotonic()
 def save(e):
  with (OUT/(name+'.fast-progress.jsonl')).open('a') as f:f.write(json.dumps(e)+'\n')
 try:
  for kind in ['joint','separate']:
   if x[kind]['joint_optimal']:continue
   aa=copy.deepcopy(c['threshold_attempts'][kind]);best=x[kind];begin=time.monotonic()
   for a in sorted(aa,key=lambda z:z['result']['joint_lower_bound']):
    if a['result']['joint_lower_bound']>=best['objective']:continue
    remaining=900-(time.monotonic()-begin)
    if remaining<1:break
    r=bt.certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],seconds=min(300,remaining),separated=kind=='separate',fixed_threshold=a['threshold'],presolve=True,incumbent=best,improving_only=True)
    valuecheck(x,r,kind=='separate');a['attempts'].append(r)
    if r['objective']<best['objective']:best=r
    low=max(a['result']['joint_lower_bound'],r['joint_lower_bound'])
    a['result']=dict(r,joint_lower_bound=min(low,r['objective']),joint_optimal=low>=r['objective'],status='OPTIMAL' if low>=r['objective'] else 'UNRESOLVED')
    save(dict(kind=kind,threshold=a['threshold'],result=r))
   for a in aa:
    r=a['result'];low=min(r['joint_lower_bound'],best['objective'])
    if r['objective']>best['objective']:a['result']=dict(best,joint_lower_bound=low,joint_optimal=low>=best['objective'],status='OPTIMAL' if low>=best['objective'] else 'UNRESOLVED')
   low=min(a['result']['joint_lower_bound'] for a in aa)
   x[kind]=dict(best,joint_lower_bound=low,joint_optimal=low>=best['objective'],status='OPTIMAL' if low>=best['objective'] else 'UNRESOLVED',scope='global_exhaustive_thresholds')
   attempts[kind]=aa;save(dict(kind=kind,final=x[kind]))
  if x['joint']['joint_optimal'] and x['separate']['joint_optimal']:
   priors=[u for u in [c['primary'].get('union'),x.get('union')] if u]
   u=ru.union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],seconds=300,total_seconds=1200,presolve=True,certified_joint_minimum=x['joint']['objective'],prior_results=priors,progress=save)
   if u['status']=='OPTIMAL':witness(x,u);assert u['split_minimum']==x['separate']['objective']
   elif u['status']=='PROVED_BY_JOINT_LOWER_BOUND':verify(x,u)
   x['union']=u
  return dict(key=key,primary=old,closed=x,threshold_attempts=attempts,seconds=time.monotonic()-start)
 except Exception:
  return dict(key=key,status='FAILED_ATTEMPT',error=traceback.format_exc(),seconds=time.monotonic()-start)
if __name__=='__main__':
 assert json.loads((OUT/'highs-adapter-check.json').read_text())['status'].startswith('PASS_')
 seen=set();jobs=[]
 with (OUT/'fast-closures.jsonl').open('x') as f,(OUT/'fast-failures.jsonl').open('x') as err,multiprocessing.get_context('spawn').Pool(2) as pool:
  terminal=False
  while not terminal or jobs:
   data=(OUT/'candidate-closures.jsonl').read_bytes()
   for raw in data[:data.rfind(b'\n')+1].splitlines():
    c=json.loads(raw);key=tuple(c['key']);x=c['closed']
    if key in seen:continue
    seen.add(key)
    if not x['joint']['joint_optimal'] or not x['separate']['joint_optimal']:jobs.append((key,pool.apply_async(solve,(c,))))
   for key,j in jobs[:]:
    if j.ready():
     r=j.get();target=err if r.get('status')=='FAILED_ATTEMPT' else f;target.write(json.dumps(r)+'\n');target.flush();jobs.remove((key,j))
     print(key,r.get('status')or [r['closed']['joint']['status'],(r['closed'].get('union')or{}).get('status')],flush=True)
   terminal='ALL_ATTEMPTS_TERMINAL' in (OUT/'run.log').read_text()
   if not terminal or jobs:time.sleep(1)
 print('ALL_FAST_ATTEMPTS_TERMINAL',flush=True)

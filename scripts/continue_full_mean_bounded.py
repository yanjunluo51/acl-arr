"""Reuse verified checkpoints and finish remaining bounded full-grid attempts."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,time,multiprocessing,sys,hashlib
from audit_full_mean_grid import key,valuecheck
from bounded_union_certificate import union_certificate
import close_full_mean_bounded as original
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/full-mean-grid-20261005'
CLOSED={'OPTIMAL','PROVED_BY_BOUND_SANDWICH','PROVED_BY_JOINT_LOWER_BOUND'}
def load():
 cases={key(x):x for x in map(json.loads,(OUT/'records.jsonl').open())}
 for p in sorted(OUT.glob('closure-*.jsonl')):
  for r in map(json.loads,p.open()):assert r['primary']==cases[tuple(r['key'])];cases[tuple(r['key'])]=r['closed']
 return cases

def recover(cases):
 progress=OUT/'bounded-attempts-20261006-180951';tasks={}
 for p in sorted(progress.glob('*.json')):
  r=json.loads(p.read_text());tasks.setdefault(tuple(r['key']),{})[r['kind']]=r
 result=[]
 for k,by in tasks.items():
  old=json.loads(json.dumps(cases[k]));x=json.loads(json.dumps(old));attempts={}
  for kind,r in by.items():
   if x[kind]['joint_optimal']:continue
   levels=sorted(r['calls'].values(),key=lambda a:a['threshold'])
   for a in levels:
    for v in a['attempts']:valuecheck(x,v,kind=='separate')
   lower=min(a['result']['joint_lower_bound'] for a in levels);best=min((a['result'] for a in levels),key=lambda a:a['objective'])
   if lower<=x[kind]['joint_lower_bound'] and best['objective']>=x[kind]['objective']:continue
   x[kind]=dict(best,joint_lower_bound=lower,joint_optimal=lower>=best['objective'],status='OPTIMAL' if lower>=best['objective'] else 'UNRESOLVED',scope='recovered_exhaustive_threshold_checkpoint')
   valuecheck(x,x[kind],kind=='separate');attempts[kind]=levels
  if x!=old:
   r=dict(key=list(k),primary=old,closed=x,threshold_attempts=attempts,recovery='Saved complete LP-level cover and completed integer attempts; unsaved calls not inferred')
   result.append(r);cases[k]=x
 if result:
  p=OUT/('closure-'+time.strftime('%Y%m%d-%H%M%S')+'-recovery.jsonl');assert not p.exists()
  p.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in result))
  p.with_suffix('.json').write_text(json.dumps(dict(status='COMPLETED_CHECKPOINT_RECOVERY_PENDING_AUDIT',cases=len(result)),indent=2)+'\n')
 return len(result)

def solve(task):
 x,progress=task
 def bounded(rows,caps,B,eps,seconds=300,presolve=False):
  assert x['joint']['joint_optimal']
  return union_certificate(rows,caps,B,eps,seconds=120,total_seconds=300,presolve=False,
    certified_joint_minimum=x['joint']['objective'],preferred_target=x['joint']['V_lower']-caps.count(0))
 original.union_certificate=bounded
 return original.close((x,progress))

def main():
 cases=load();n=recover(cases)
 # The prior queue's completed resource-bounded cases are not silently retried.
 completed={tuple(r['key']) for r in map(json.loads,(OUT/'closure-20261006-180951.jsonl').open())}
 pending=[]
 for k,x in cases.items():
  need=not x['joint']['joint_optimal'] or not x['separate']['joint_optimal'] or x['union'] is None or x['union']['status'] not in CLOSED
  if need and k not in completed:pending.append(x)
 stamp=time.strftime('%Y%m%d-%H%M%S');p=OUT/f'closure-{stamp}-continuation.jsonl';assert not p.exists();progress=OUT/f'bounded-attempts-{stamp}';progress.mkdir()
 start=time.monotonic();print('Recovered',n,'checkpoints; remaining targets',len(pending),flush=True)
 with p.open('w') as f,multiprocessing.get_context('spawn').Pool(4) as pool:
  for i,r in enumerate(pool.imap_unordered(solve,[(x,str(progress)) for x in pending]),1):
   f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush();x=r['closed'];print(i,len(pending),r['key'],x['joint']['status'],x['union']['status'] if x['union'] else None,round(time.monotonic()-start,1),flush=True)
 p.with_suffix('.json').write_text(json.dumps(dict(status='COMPLETED_CLOSURE_ATTEMPT_PENDING_AUDIT',cases=len(pending),seconds=time.monotonic()-start,recovered_checkpoints=n,previous_completed_cases_not_retried=len(completed),union_nominal_total_seconds=300,union_solver_per_call_seconds=120,lower_bound_shortcut=True,successor_source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'scripts/bounded_union_certificate.py',ROOT/'scripts/continue_full_mean_bounded.py',ROOT/'scripts/verify_union_shortcut.py']}),indent=2)+'\n')
if __name__=='__main__':
 if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
 main()

"""Global union closure by verified strict-improvement searches."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,time,copy,multiprocessing,traceback
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import improving_union as iu
from highs_adapter import milp
from target_bound_certificate import certify
iu.milp=milp
def read(n):
 p=OUT/n
 if not p.exists():return []
 b=p.read_bytes();return [json.loads(l) for l in b[:b.rfind(b'\n')+1].splitlines()]
def solve(task):
 key,x,priors=task;start=time.monotonic();name='-'.join(map(str,key))
 def save(e):
  with (OUT/(name+'.union-improvement-progress.jsonl')).open('a') as f:f.write(json.dumps(e)+'\n')
 try:
  proof=certify(x,priors)
  if proof:return dict(key=key,case=x,prior_results=priors,result=None,global_proof=proof,seconds=0)
  u=iu.union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],seconds=240,total_seconds=1500,presolve=True,certified_joint_minimum=x['joint']['objective'],prior_results=priors,progress=save)
  proof=certify(x,priors+[u])
  return dict(key=key,case=x,prior_results=priors,result=u,global_proof=proof,seconds=time.monotonic()-start)
 except Exception:return dict(key=key,status='FAILED_ATTEMPT',error=traceback.format_exc(),seconds=time.monotonic()-start)
if __name__=='__main__':
 assert json.loads((OUT/'improving-union-check.json').read_text())['cases']==20
 states={tuple(r['key']):r['state'] for r in read('verified-case-states.jsonl')};priors={k:[] for k in states}
 for n in ['candidate-closures.jsonl','resume-closures.jsonl']:
  for c in read(n):
   for x in [c['primary'],c['closed']]:
    if x.get('union'):priors[tuple(c['key'])].append(x['union'])
 for c in read('union-followthrough.jsonl'):
  priors[tuple(c['key'])]+=c['prior_results']+([c['result']] if c['result'] else [])
 jobs=[(list(k),x,priors[k]) for k,x in states.items() if not x.get('union') or x['union']['status'] not in ['OPTIMAL','PROVED_BY_JOINT_LOWER_BOUND','PROVED_BY_BOUND_SANDWICH','PROVED_BY_TARGET_LOWER_BOUNDS']]
 with (OUT/'union-improvements.jsonl').open('x') as f,(OUT/'union-improvement-failures.jsonl').open('x') as err,multiprocessing.get_context('spawn').Pool(2) as pool:
  for r in pool.imap_unordered(solve,jobs):
   target=err if r.get('status')=='FAILED_ATTEMPT' else f;target.write(json.dumps(r)+'\n');target.flush()
   print(r['key'],r.get('status')or ('CLOSED' if r['global_proof'] else 'UNRESOLVED'),round(r['seconds'],1),flush=True)
 print('ALL_UNION_IMPROVEMENTS_TERMINAL',flush=True)

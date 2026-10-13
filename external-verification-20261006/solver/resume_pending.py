"""Append-only second pass on completed first-pass cases; preserve all attempts."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,time,copy,multiprocessing,traceback
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from resumable_union import union_certificate
from audit_deduplicated_evidence import witness
from verify_union_shortcut import verify
CLOSED={'OPTIMAL','PROVED_BY_BOUND_SANDWICH','PROVED_BY_JOINT_LOWER_BOUND'}

def solve(c):
 x=copy.deepcopy(c['closed']);key=c['key'];name='-'.join(map(str,key));old=copy.deepcopy(x)
 priors=[u for u in [c['primary'].get('union'),x.get('union')] if u]
 for l in (OUT/(name+'.progress.jsonl')).read_text().splitlines():
  event=json.loads(l)
  if event.get('kind')=='union':priors.append(event['result'])
 start=time.monotonic()
 def save(e):
  with (OUT/(name+'.resume-progress.jsonl')).open('a') as f:f.write(json.dumps(e)+'\n')
 try:
  u=union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],seconds=300,total_seconds=2400,
      presolve=False,certified_joint_minimum=x['joint']['objective'],preferred_target=x['joint']['V_lower']-x['caps'].count(0),prior_results=priors,progress=save)
  if u['status']=='OPTIMAL':witness(x,u);assert u['split_minimum']==x['separate']['objective']
  elif u['status']=='PROVED_BY_JOINT_LOWER_BOUND':verify(x,u)
  x['union']=u
  return dict(key=key,primary=old,closed=x,threshold_attempts={},seconds=time.monotonic()-start)
 except Exception:
  return dict(key=key,status='FAILED_ATTEMPT',error=traceback.format_exc(),seconds=time.monotonic()-start)

if __name__=='__main__':
 assert json.loads((OUT/'resume-check.json').read_text())['status'].startswith('PASS_')
 submitted=set();skipped=[];jobs=[]
 with (OUT/'resume-closures.jsonl').open('x') as f,(OUT/'resume-failures.jsonl').open('x') as err,multiprocessing.get_context('spawn').Pool(4) as pool:
  terminal=False
  while not terminal or jobs:
   # A complete newline is the first-pass durability boundary.
   data=(OUT/'candidate-closures.jsonl').read_bytes();lines=data[:data.rfind(b'\n')+1].splitlines()
   for raw in lines:
    c=json.loads(raw);key=tuple(c['key'])
    if key in submitted:continue
    submitted.add(key);x=c['closed'];u=x.get('union')
    if u and u['status'] in CLOSED:skipped.append(dict(key=key,reason='ALREADY_CLOSED'));continue
    if not x['joint']['joint_optimal'] or not x['separate']['joint_optimal']:
     skipped.append(dict(key=key,reason='COMPONENT_MINIMUM_PENDING'));continue
    jobs.append((key,pool.apply_async(solve,(c,))))
   for key,job in jobs[:]:
    if not job.ready():continue
    r=job.get();target=err if r.get('status')=='FAILED_ATTEMPT' else f
    target.write(json.dumps(r)+'\n');target.flush();jobs.remove((key,job))
    print('RESUME',key,r.get('status')or r['closed']['union']['status'],round(r['seconds'],1),flush=True)
   terminal='ALL_ATTEMPTS_TERMINAL' in (OUT/'run.log').read_text()
   if not terminal or jobs:time.sleep(1)
 (OUT/'resume-skipped.json').write_text(json.dumps(skipped,indent=2)+'\n')
 print('ALL_RESUME_ATTEMPTS_TERMINAL',flush=True)

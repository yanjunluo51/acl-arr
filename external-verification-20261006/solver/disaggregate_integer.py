import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import sys,json,multiprocessing
from pathlib import Path
OUT=Path(__file__).resolve().parent
from disaggregate_pending import run
def solve(z):
 key,case,kind,t,s=z;r=run(case,kind,t,180,False,s)
 return dict(key=key,kind=kind,threshold=t,target=s,result=r)
if __name__=='__main__':
 assert json.loads((OUT/'disaggregation-check.json').read_text())['status'].startswith('PASS_')
 cases={tuple(c['key']):c['closed'] for c in map(json.loads,(OUT/'candidate-closures.jsonl').open())};jobs=[]
 for d in map(json.loads,(OUT/'disaggregated-attempts.jsonl').open()):
  for a in d['attempts']:
   if a['result']['joint_lower_bound']<d['incumbent']:jobs.append((d['key'],cases[tuple(d['key'])],d['kind'],d['threshold'],a['target']))
 with (OUT/'disaggregated-integer.jsonl').open('x') as f,multiprocessing.get_context('spawn').Pool(2) as pool:
  for r in pool.imap_unordered(solve,jobs):
   f.write(json.dumps(r)+'\n');f.flush();print(r['key'],r['target'],r['result']['joint_lower_bound'],r['result']['objective'],flush=True)
 print('ALL_DISAGGREGATED_INTEGER_ATTEMPTS_TERMINAL',flush=True)

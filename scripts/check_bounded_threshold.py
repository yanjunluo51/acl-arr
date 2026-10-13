"""Exhaustive-case validation of LP screening and incumbent-bounded search."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import json,hashlib,time
from pathlib import Path
from bounded_threshold_certificate import certificate
from variable_target_certificate import certificate as full
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'review-revision/evidence-discovery-implementation-20261005'
def main(output=None):
 cases=json.loads((RUN/'variable-target-check.json').read_text())['records'];start=time.monotonic();attempts=0
 for c in cases:
  vals=[c[k] for k in ['rows','caps','budget','epsilon','observed']]
  for sep,name in [(False,'joint'),(True,'split')]:
   incumbent=full(*vals,seconds=.001,separated=sep);results=[];relax=[]
   for t in range(max(map(sum,c['rows']),default=0)+1):
    r=certificate(*vals,seconds=30,separated=sep,fixed_threshold=t,presolve=False,incumbent=incumbent,improving_only=True)
    lp=certificate(*vals,seconds=30,separated=sep,fixed_threshold=t,presolve=False,incumbent=incumbent,relaxation=True)
    results.append(r);relax.append(lp);attempts+=2
   assert min(r['objective'] for r in results)==c[name]
   assert min(r['joint_lower_bound'] for r in results)==c[name]
   assert min(r['joint_lower_bound'] for r in relax)<=c[name]
 receipt=dict(status='PASS_BOUNDED_THRESHOLDS_AND_LP_SCREENING',independent_cases=len(cases),attempts=attempts,seconds=time.monotonic()-start,source_sha256=hashlib.sha256((ROOT/'scripts/bounded_threshold_certificate.py').read_bytes()).hexdigest(),scope='bounds truncate at an inherited globally feasible witness; per-threshold optimum attainment is not claimed')
 if output is not None:
  with Path(output).open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,help='New receipt path; existing files are never overwritten')
 a=p.parse_args()
 if a.output is not None and a.output.exists():p.error('--output must name a new file')
 main(a.output)

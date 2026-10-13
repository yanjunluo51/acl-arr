"""Compare final fixed-threshold formulation with independent finite enumerations."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import json,hashlib,time
from pathlib import Path
from threshold_target_certificate import certificate
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'review-revision/evidence-discovery-implementation-20261005'
def main():
 start=time.monotonic();cases=json.loads((RUN/'variable-target-check.json').read_text())['records'];tested=0
 for c in cases:
  rows,caps,B,eps,obs=[c[n] for n in ['rows','caps','budget','epsilon','observed']]
  for sep,name in [(False,'joint'),(True,'split')]:
   results=[certificate(rows,caps,B,eps,obs,seconds=30,fixed_threshold=t,separated=sep,presolve=False) for t in range(max(map(sum,rows),default=0)+1)]
   viable=[r for r in results if r['joint_optimal']]
   assert viable and min(r['objective'] for r in viable)==c[name]
   assert min(r['joint_lower_bound'] for r in results)>=c[name]
   tested+=len(results)
 receipt=dict(status='PASS_FINAL_FIXED_THRESHOLD_DECOMPOSITION',independent_cases=len(cases),target_objectives=2*len(cases),threshold_attempts=tested,seconds=time.monotonic()-start,source_sha256=hashlib.sha256((ROOT/'scripts/threshold_target_certificate.py').read_bytes()).hexdigest())
 (RUN/'threshold-decomposition-final-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

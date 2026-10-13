"""Reoptimize both equivalent formulations on all 7,680 saved small tasks."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import json
from pathlib import Path
from compact_joint_certificate import compact_certificate
ROOT=Path(__file__).resolve().parents[1]
def main():
 count=0
 for line in (ROOT/'outputs/joint-certificates/instances.jsonl').open():
  x=json.loads(line)
  for r in x['records']:
   for grouped in [False,True]:
    y=compact_certificate(x['flips'],x['caps'],r['budget'],r['epsilon'],x['observed'][r['history']],outcome_counts=grouped)
    assert y['joint_optimal'] and y['separated_optimal'] and (y['queries'],y['split_queries'])==(r['queries'],r['split_queries'])
   count+=1
 assert count==7680;print(json.dumps(dict(status='PASS_BOTH_NEW_FORMULATIONS_ALL_7680_MINIMA',minima=count)))
if __name__=='__main__':main()

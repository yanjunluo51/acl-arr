import os,sys,json,copy
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import partition_union as iu
from highs_adapter import milp
from target_bound_certificate import certify
iu.milp=milp
n=0;positive=0
for x in map(json.loads,(ROOT/'outputs/deduplicated-evidence/records.jsonl').open()):
 r=x['result']
 if x['scope']!='small' or r['status']!='OPTIMAL' or 'solver_calls' not in r:continue
 # Retain the feasible masks and component proofs; erase union optimality receipts.
 partial=dict(r,targets=[dict(t,proven=False) for t in r['targets']],solver_calls=[c for c in r['solver_calls'] if c['mode']!='union'])
 u=iu.union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],seconds=10,total_seconds=30,prior_results=[partial])
 proof=certify(x,[partial,u]);assert proof and proof['union_minimum']==r['union_minimum']
 n+=1;positive+=x['epsilon']>0
 if n==20 and positive:break
assert n==20 and positive
(OUT/'partition-union-check.json').write_text(json.dumps(dict(status='PASS_20_PARTITIONED_UNION_CASES',cases=n,positive_tolerance_cases=positive),indent=2)+'\n');print('PASS',n,positive)

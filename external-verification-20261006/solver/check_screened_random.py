"""Fresh fixed-seed checks against binary-entry row-subset formulation."""
import os,sys,json,random
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from deduplicated_certificates import union_certificate as independent
import screened_partition_union as pu
from highs_adapter import milp
from target_bound_certificate import certify
pu.milp=milp
rng=random.Random(6100623);n=0;history=0;positive=0;screens=0
for _ in range(100):
 m=rng.randint(1,3);T=rng.randint(1,3);caps=[rng.randint(0,3) for i in range(m)]
 rows=[[rng.randint(0,p) for j in range(T)] for p in caps]
 observed=[rng.randrange(1<<T) for i in range(m)];B=rng.randint(0,sum(map(sum,rows))+2);eps=rng.randint(0,m)
 case=dict(rows=rows,caps=caps,T=T,budget=B,epsilon=eps,observed=observed)
 a=independent(rows,caps,B,eps,observed,seconds=10,independent=True)
 b=pu.union_certificate(rows,caps,B,eps,observed,seconds=10,total_seconds=60)
 assert a['status']=='OPTIMAL',(case,a)
 assert a['union_minimum']==b['union_minimum'],(case,a,b)
 if b['split_minimum'] is not None:assert a['split_minimum']==b['split_minimum']
 proof=certify(case,[b]);assert proof and proof['union_minimum']==a['union_minimum']
 n+=1;history+=any(observed);positive+=eps>0;screens+=sum('threshold_screen' in c for c in b['solver_calls'])
assert screens>0
r=dict(screened_union_calls=screens,status='PASS_100_SCREENED_ENTRY_SUBSET_COMPARISONS',seed=6100623,cases=n,with_nonempty_history=history,with_positive_tolerance=positive,maximum_entries=9)
(OUT/'screened-random-check.json').write_text(json.dumps(r,indent=2)+'\n');print(r)

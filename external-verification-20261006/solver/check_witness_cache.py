import sys,json,copy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from deduplicated_certificates import union_certificate as original
import screened_partition_union as fixed
from highs_adapter import milp
from target_bound_certificate import certify
fixed.milp=milp
rows=[[1,1],[0,0]];caps=[1,1];case=dict(rows=rows,caps=caps,T=2,budget=1,epsilon=1,observed=[0,0])
r=original(rows,caps,1,1,[0,0],independent=True,seconds=10);assert r['union_minimum']==1
prior=copy.deepcopy(r);prior.update(status='UNRESOLVED',union_minimum=2,safe_target=0,safety_mask=0,exclusion_mask=3,union_mask=3,safe_mask=0)
assert certify(case,[prior]) is None
u=fixed.union_certificate(rows,caps,1,1,[0,0],prior_results=[prior],seconds=10,total_seconds=60)
proof=certify(case,[prior,u]);assert proof and u['union_minimum']==proof['union_minimum']==1
result=dict(status='PASS_BETTER_CACHED_TARGET_RECONSTRUCTS_WITNESS',previous_feasible_union=2,better_cached_target_value=1,reconstructed_union=1,query_mask=u['union_mask'])
(OUT/'witness-cache-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
r=json.loads((OUT/'witness-cache-fix.json').read_text());r['status']='PASS_TARGETED_WITNESS_RECONSTRUCTION_REGRESSION';(OUT/'witness-cache-fix.json').write_text(json.dumps(r,indent=2)+'\n')

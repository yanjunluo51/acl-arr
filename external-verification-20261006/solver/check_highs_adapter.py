import os,sys,json
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import bounded_threshold_certificate as bt
import bounded_union_certificate as bu
from highs_adapter import milp
from audit_deduplicated_evidence import witness
bt.milp=bu.milp=milp
cases=[json.loads(l) for l in (ROOT/'outputs/deduplicated-evidence/records.jsonl').open()]
checked=[]
for x in cases:
 if x['scope']!='small' or x['result']['status']!='OPTIMAL' or 'solver_calls' not in x['result']:continue
 args=(x['rows'],x['caps'],x['budget'],x['epsilon'])
 u=bu.union_certificate(*args,observed=x['observed'],seconds=20,total_seconds=60)
 assert u['status']=='OPTIMAL';witness(x,u);assert u['union_minimum']==x['result']['union_minimum']
 for sep in [False,True]:
  r=bt.certificate(*args,observed=x['observed'],seconds=20,separated=sep)
  assert r['joint_optimal'] and r['objective']==x['additive_minimum' if sep else 'joint_minimum']
 checked.append([x['dataset'],x['split'],x['q'],x['history'],x['epsilon']])
 if len(checked)==12:break
assert len(checked)==12 and any(c[-1]>0 for c in checked)
(OUT/'highs-adapter-check.json').write_text(json.dumps(dict(status='PASS_12_SAME_MODEL_THREE_OBJECTIVE_CHECKS',cases=checked,backend='highspy 1.15.1',paid_solver=False),indent=2)+'\n')
print('PASS_12_SAME_MODEL_THREE_OBJECTIVE_CHECKS')

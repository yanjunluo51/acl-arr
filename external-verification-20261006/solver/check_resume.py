import os,sys,json
from pathlib import Path
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from resumable_union import union_certificate
from audit_deduplicated_evidence import witness
cases=[json.loads(l) for l in (ROOT/'outputs/deduplicated-evidence/records.jsonl').open()]
done=[]
for x in cases:
 r=x['result']
 if x['scope']!='small' or r['status']!='OPTIMAL' or 'solver_calls' not in r:continue
 u=union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],prior_results=[r],total_seconds=2)
 witness(x,u);assert u['union_minimum']==r['union_minimum']
 # A subset of prior target records exercises actual resume + reconstruction.
 partial=dict(r,targets=r['targets'][:1],solver_calls=[c for c in r['solver_calls'] if c['target']==r['targets'][0]['target']])
 v=union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],x['observed'],prior_results=[partial],seconds=10,total_seconds=30)
 assert v['status']=='OPTIMAL';witness(x,v);assert v['union_minimum']==r['union_minimum']
 done.append([x['dataset'],x['split'],x['q'],x['history'],x['epsilon']])
 if len(done)==8:break
assert len(done)==8
out=dict(status='PASS_EIGHT_PRIOR_AND_PARTIAL_RESUME_CASES',cases=done,scope='same MILP; only reuses matching optimal receipts',human_proof=False)
(Path(__file__).parent/'resume-check.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])

"""Reject missing or incorrect component receipts for threshold pruning."""
import sys,json,copy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from target_bound_certificate import certify
r=next(x for x in map(json.loads,(OUT/'union-screeneds.jsonl').open()) if x['key']==['WMT24-ja-zh',20,0.05,'primary'])
case=r['case'];ps=r['prior_results']+[r['result']];assert certify(case,ps)
rejected=[]
for mode in ['alter_component_minimum','remove_component_receipt']:
 priors=copy.deepcopy(ps)
 row=next(p for p in reversed(priors) if any('threshold_screen' in c for c in p.get('solver_calls',[])))
 c=next(c for c in row['solver_calls'] if 'threshold_screen' in c)
 if mode=='alter_component_minimum':c['threshold_screen']['component_minimum']+=1
 else:
  ex=c['threshold_screen']['exclusion_receipt'];row['solver_calls']=[c for c in row['solver_calls'] if c!=ex]
 try:certify(case,priors)
 except AssertionError:rejected.append(mode)
 else:raise AssertionError('undetected '+mode)
(OUT/'screen-mutation-check.json').write_text(json.dumps(dict(status='PASS_BOTH_SCREEN_MUTATIONS_REJECTED',rejected=rejected),indent=2)+'\n');print(rejected)

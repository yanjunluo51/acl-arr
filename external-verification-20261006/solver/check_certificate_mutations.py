"""Adversarial checks of target/threshold coverage and reconstructed witnesses."""
import sys,json,copy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from target_bound_certificate import certify
r=next(x for x in map(json.loads,(OUT/'union-partitions.jsonl').open()) if x['key']==['WMT24-ja-zh',37,0.1,'primary'])
case=r['case'];priors=r['prior_results']+[r['result']]
base=certify(case,priors);assert base and base['union_minimum']==6310
rejected=[]
def check(label,mutate):
 ps=copy.deepcopy(priors);mutate(ps)
 try:proof=certify(case,ps)
 except (AssertionError,KeyError,ValueError):rejected.append(label);return
 assert proof is None,(label,'undetected mutation');rejected.append(label)
def part(ps):return next(c['partition_receipt'] for p in reversed(ps) for c in p.get('solver_calls',[]) if 'partition_receipt' in c)
check('remove_threshold',lambda ps:part(ps)['details'].pop())
check('change_partition_lower',lambda ps:part(ps).__setitem__('global_lower',999999))
check('duplicate_threshold',lambda ps:part(ps)['levels'].append(part(ps)['levels'][-1]))
def remove_target(ps):
 for p in ps:p['solver_calls']=[c for c in p.get('solver_calls',[]) if not(c['target']==399 and c['mode']=='union')]
check('remove_winning_target_bound',remove_target)
def badmask(ps):
 for p in ps:
  if p.get('union_minimum')==6310:p['union_mask']^=1<<(len(case['rows'])*case['T'])
check('out_of_domain_union_entry',badmask)
def badcost(ps):
 for p in ps:
  if p.get('union_minimum')==6310:p['union_minimum']-=1
check('incorrect_union_cardinality',badcost)
(OUT/'certificate-mutation-check.json').write_text(json.dumps(dict(status='PASS_SIX_MUTATIONS_REJECTED',case_key=r['key'],correct_minimum=6310,rejected=rejected),indent=2)+'\n')
print(rejected)

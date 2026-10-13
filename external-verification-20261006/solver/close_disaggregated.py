import os,sys,json,copy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_full_mean_grid import valuecheck
from disaggregate_pending import targets
cases={tuple(c['key']):c['closed'] for c in map(json.loads,(OUT/'candidate-closures.jsonl').open())}
lp=[json.loads(l) for l in (OUT/'disaggregated-attempts.jsonl').open()]
ip={(tuple(x['key']),x['kind'],x['threshold'],x['target']):x['result'] for x in map(json.loads,(OUT/'disaggregated-integer.jsonl').open())}
prior={tuple(c['key']):c for c in map(json.loads,(OUT/'candidate-closures.jsonl').open())}
group={}
for d in lp:group.setdefault(tuple(d['key']),[]).append(d)
with (OUT/'disaggregated-closures.jsonl').open('x') as out:
 for key,ds in group.items():
  old=copy.deepcopy(cases[key]);x=copy.deepcopy(old);aa=copy.deepcopy(prior[key]['threshold_attempts'])
  for d in ds:
   assert d['targets']==targets(x) and [a['target'] for a in d['attempts']]==d['targets']
   rs=[]
   for a in d['attempts']:
    s=a['target'];rr=[a['result']];r=ip.get((key,d['kind'],d['threshold'],s))
    if r:rr.append(r)
    for r in rr:
     assert r['fixed_target']==s and r['fixed_threshold']==d['threshold'];valuecheck(x,r,d['kind']=='separate')
    rs.append(dict(target=s,attempts=rr,lower=max(r['joint_lower_bound'] for r in rr)))
   level=next(a for a in aa[d['kind']] if a['threshold']==d['threshold']);level['prior_result']=copy.deepcopy(level['result']);level['target_disaggregation']=rs
   low=max(level['result']['joint_lower_bound'],min(r['lower'] for r in rs))
   # Here the incumbent is unchanged. A changed incumbent would require a new merge.
   assert all(r['objective']>=x[d['kind']]['objective'] for a in rs for r in a['attempts'])
   level['result']=dict(x[d['kind']],joint_lower_bound=low,joint_optimal=low==x[d['kind']]['objective'],status='OPTIMAL' if low==x[d['kind']]['objective'] else 'UNRESOLVED',scope='derived_complete_target_partition')
  for kind,attempts in aa.items():
   low=min(a['result']['joint_lower_bound'] for a in attempts);assert low<=x[kind]['objective']
   x[kind]=dict(x[kind],joint_lower_bound=low,joint_optimal=low==x[kind]['objective'],status='OPTIMAL' if low==x[kind]['objective'] else 'UNRESOLVED');valuecheck(x,x[kind],kind=='separate')
  assert x['joint']['joint_optimal'] and x['separate']['joint_optimal']
  c=dict(key=list(key),primary=old,closed=x,threshold_attempts=aa,closure_method='exhaustive fixed integer safe-target partition')
  out.write(json.dumps(c)+'\n');print(key,x['joint']['objective'])

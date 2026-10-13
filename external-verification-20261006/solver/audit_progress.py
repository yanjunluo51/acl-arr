"""Audit isolated branches and compose bounds without changing canonical outputs."""
import json,sys,copy,math,hashlib,csv
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from continue_full_mean_bounded import load
from audit_full_mean_grid import valuecheck
from audit_deduplicated_evidence import capacity,witness
from verify_union_shortcut import verify
from target_bound_certificate import certify
CLOSED={'OPTIMAL','PROVED_BY_BOUND_SANDWICH','PROVED_BY_JOINT_LOWER_BOUND'}
def read(name):
 p=OUT/name
 if not p.exists():return []
 b=p.read_bytes();return [json.loads(l) for l in b[:b.rfind(b'\n')+1].splitlines()]
def check_branch(c,expected):
 assert c['primary']==expected
 x=c['closed'];assert [x['dataset'],x['split'],x['q'],x['stopping']]==c['key']
 for f in ['rows','caps','observed','N','k','T','budget','epsilon','original_output_ids','selected_count']:
  assert x[f]==expected[f]
 for kind,aa in c['threshold_attempts'].items():
  active=[r for r,p in zip(x['rows'],x['caps']) if p];m=len(active);L=capacity(list(map(sum,active)),x['budget']);pmax=min(L,m-x['epsilon']-1)+x['epsilon']+1
  levels=[t for t in range(max(map(sum,active),default=0)+1) if pmax*t-sum(max(0,t-sum(r)) for r in active)>=x['budget']+1] or [0]
  assert [a['threshold'] for a in aa]==levels
  assert min(a['result']['joint_lower_bound'] for a in aa)==x[kind]['joint_lower_bound']
  assert min(a['result']['objective'] for a in aa)==x[kind]['objective']
  for a in aa:
   for r in a['attempts']:valuecheck(x,r,kind=='separate')
   if 'target_disaggregation' in a:
    from disaggregate_pending import targets
    ds=a['target_disaggregation'];assert [d['target'] for d in ds]==targets(x)
    for d in ds:
     assert d['lower']==max(r['joint_lower_bound'] for r in d['attempts'])
     for r in d['attempts']:
      assert r['fixed_target']==d['target'] and r['fixed_threshold']==a['threshold'];valuecheck(x,r,kind=='separate')
    assert a['result']['joint_lower_bound']==max(a['prior_result']['joint_lower_bound'],min(d['lower'] for d in ds))
 for kind in ['joint','separate']:valuecheck(x,x[kind],kind=='separate')
 u=x.get('union')
 if u and u['status'] in CLOSED:
  assert x['joint']['joint_optimal'] and x['separate']['joint_optimal']
  if u['status']=='OPTIMAL':witness(x,u);assert u['split_minimum']==x['separate']['objective']
  elif u['status']=='PROVED_BY_JOINT_LOWER_BOUND':verify(x,u)
  else:assert u['union_minimum']==x['joint']['objective']==x['separate']['objective']

base=load();first={};branches={};provenance={}
for c in read('candidate-closures.jsonl'):
 k=tuple(c['key']);check_branch(c,base[k]);first[k]=c['closed'];branches[k]=[base[k],c['closed']];provenance[k]=['candidate-closures.jsonl']
for name in ['resume-closures.jsonl','modern-closures.jsonl','fast-closures.jsonl','disaggregated-closures.jsonl']:
 for c in read(name):
  k=tuple(c['key']);check_branch(c,first[k]);branches[k].append(c['closed']);provenance[k].append(name)
for c in read('union-followthrough.jsonl'):
 k=tuple(c['key']);assert any(z==c['case'] for z in branches[k])
 x=copy.deepcopy(c['case']);x['union']=c['result'];u=x['union']
 if u and u['status']=='OPTIMAL':witness(x,u);assert u['split_minimum']==x['separate']['objective']
 elif u and u['status']=='PROVED_BY_JOINT_LOWER_BOUND':verify(x,u)
 # Zero-second records close directly from prior receipts; solver records add u.
 proof=certify(x,c['prior_results']+([u] if u and c['seconds']>0 else []));assert proof==c['global_proof']
 branches[k].append(x);provenance[k].append('union-followthrough.jsonl')
# Improvement runs start from composed, independently checked case states.
# Check immutable instance fields and re-derive all objective bounds below.
extra_priors={}
for name in ['union-improvements.jsonl','union-tights.jsonl','union-partitions.jsonl','union-screeneds.jsonl','union-finals.jsonl']:
 for c in read(name):
  k=tuple(c['key']);x=copy.deepcopy(c['case']);expected=base[k]
  for f in ['rows','caps','observed','N','k','T','budget','epsilon','original_output_ids','selected_count']:
   assert x[f]==expected[f]
  for kind in ['joint','separate']:
   valuecheck(x,x[kind],kind=='separate')
   assert x[kind]['joint_lower_bound']==max(z[kind]['joint_lower_bound'] for z in branches[k])
   assert x[kind]['objective']==min(z[kind]['objective'] for z in branches[k])
  u=c['result'];priors=c['prior_results']+([u] if u else [])
  proof=certify(x,priors);assert proof==c['global_proof']
  if u and u['status']=='OPTIMAL':witness(x,u);assert u['split_minimum']==x['separate']['objective']
  if u:x['union']=u;branches[k].append(x)
  extra_priors.setdefault(k,[]).extend(priors)
  provenance[k].append(name)
records=[];states=[];global_proofs=[]
for item in json.loads((OUT/'pending.json').read_text()):
 k=tuple(item['key']);xs=branches.get(k,[base[k]]);x=copy.deepcopy(xs[-1])
 for kind in ['joint','separate']:
  options=[z[kind] for z in xs];best=copy.deepcopy(min(options,key=lambda r:r['objective']));low=max(r['joint_lower_bound'] for r in options)
  assert low<=best['objective'];best.update(joint_lower_bound=low,joint_optimal=low==best['objective'],status='OPTIMAL' if low==best['objective'] else 'UNRESOLVED');x[kind]=best;valuecheck(x,best,kind=='separate')
 priors=[z['union'] for z in xs if z.get('union')]+extra_priors.get(k,[])
 us=[u for u in priors if u.get('status') in CLOSED]
 if us:
  assert len({u['union_minimum'] for u in us})==1;x['union']=us[0]
 elif x['joint']['joint_optimal'] and x['separate']['joint_optimal']:
  proof=certify(x,priors)
  if proof:
   assert x['joint']['objective']<=proof['union_minimum']<=x['separate']['objective']
   x['union']=proof;global_proofs.append(dict(key=list(k),proof=proof))
  elif priors:x['union']=min(priors,key=lambda u:u.get('union_minimum',float('inf')))
 u=x.get('union');closed=bool(u and u['status'] in CLOSED|{'PROVED_BY_TARGET_LOWER_BOUNDS'})
 r=dict(dataset=k[0],split=k[1],q=k[2],stopping=k[3],joint_lower=x['joint']['joint_lower_bound'],joint_upper=x['joint']['objective'],joint_closed=x['joint']['joint_optimal'],union_closed=closed,union_minimum=u.get('union_minimum') if u else None,union_proof=u['status'] if u else 'NOT_RUN',branch_files=';'.join(provenance.get(k,[])))
 records.append(r);states.append(dict(key=list(k),state=x,sources=provenance.get(k,[])))
pre=json.loads((OUT.parent/'pre-execution.json').read_text())
content_only='--content-only' in sys.argv
adopt_path=OUT.parent/'adoption.json'
adopt=json.loads(adopt_path.read_text()) if adopt_path.exists() else None
if not content_only:
 expected=dict(pre['protected']);expected.update(adopt['after'] if adopt else {})
 assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in expected.items())
failed={n:len(read(n)) for n in ['failed-attempts.jsonl','resume-failures.jsonl','modern-failures.jsonl','fast-failures.jsonl','union-follow-failures.jsonl','union-improvement-failures.jsonl','union-tight-failures.jsonl','union-partition-failures.jsonl','union-screened-failures.jsonl','union-final-failures.jsonl']}
logs=[('run.log','ALL_ATTEMPTS_TERMINAL'),('resume.log','ALL_RESUME_ATTEMPTS_TERMINAL'),('fast.log','ALL_FAST_ATTEMPTS_TERMINAL'),('union-follow.log','ALL_UNION_FOLLOWTHROUGH_TERMINAL'),('union-improvements.log','ALL_UNION_IMPROVEMENTS_TERMINAL'),('union-tight.log','ALL_UNION_TIGHT_TERMINAL'),('union-partition.log','ALL_UNION_PARTITION_TERMINAL'),('union-screened.log','ALL_UNION_SCREENED_TERMINAL'),('union-final.log','ALL_UNION_FINAL_TERMINAL')]
aborted={'resume.log':'resume-aborted.json','union-follow.log':'union-follow-aborted.json','union-improvements.log':'union-improvements-aborted.json','union-tight.log':'union-tight-aborted.json','union-partition.log':'union-partition-aborted.json'}
terminal=all(((OUT/log).exists() and marker in (OUT/log).read_text()) or (log in aborted and (OUT/aborted[log]).exists()) for log,marker in logs) and ((OUT/'modern-aborted.json').exists() or 'ALL_MODERN_ATTEMPTS_TERMINAL' in (OUT/'modern.log').read_text())
status=dict(status='PASS_ISOLATED_BRANCH_WITNESSES_AND_EXHAUSTIVE_THRESHOLD_ACCOUNTING',baseline_targets=1920,initial_pending_targets=22,initial_joint_unresolved=8,initial_union_unresolved=22,
 joint_remaining=sum(not r['joint_closed'] for r in records),union_remaining=sum(not r['union_closed'] for r in records),first_pass_completed=len(first),global_target_bound_closures=len(global_proofs),failed_attempts=failed,
 canonical_manuscript_and_packages_unchanged=not bool(adopt),delivery_bindings_checked=not content_only,human_proof_certified=False,all_computation_terminal=terminal)
with (OUT/'verified-progress.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
(OUT/'verified-progress.json').write_text(json.dumps(status,indent=2)+'\n')
(OUT/'verified-case-states.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in states))
(OUT/'global-target-bound-proofs.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in global_proofs))
print(json.dumps(status,indent=2))

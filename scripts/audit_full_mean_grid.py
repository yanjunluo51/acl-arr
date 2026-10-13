"""Audit full mean saved witnesses; optionally verify original score-derived inputs."""
import csv,hashlib,json,math,statistics,sys
from pathlib import Path
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
from audit_deduplicated_evidence import capacity,witness
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/full-mean-grid-20261005'
def key(x):return (x['dataset'],int(x['split']),float(x['q']),x['stopping'])
def bounds(x,mask):
 rows,caps,T=x['rows'],x['caps'],x['T'];assert type(mask) is int and 0<=mask<(1<<(len(rows)*T))
 lo=[];up=[]
 for i,(r,p,o) in enumerate(zip(rows,caps,x['observed'])):
  new=mask>>(i*T)&((1<<T)-1);assert not new&o
  z=new|o;l=sum(v for j,v in enumerate(r) if z>>j&1)
  lo.append(l);up.append(l+(T-bin(z).count('1'))*p)
 return lo,up

def valuecheck(x,r,separate=False):
 assert r['status'] in ['OPTIMAL','UNRESOLVED'] and r['joint_optimal']==(r['status']=='OPTIMAL')
 assert type(r['objective']) is int and r['objective']>=0 and 0<=r['joint_lower_bound']<=r['objective']
 if r['joint_optimal']:assert r['joint_lower_bound']>=r['objective']
 lo,up=bounds(x,r['query_mask']);B=x['budget'];vl,vu=capacity(up,B),capacity(lo,B)
 assert r['queries']==bin(r['query_mask']).count('1')
 assert r['queries']<=r['objective'] if separate else r['queries']==r['objective']
 assert (vl,vu)==(r['V_lower'],r['V_upper']) and vu-vl<=x['epsilon']
 sm=r['safe_mask'];assert type(sm) is int and 0<=sm<(1<<len(up))
 assert bin(sm).count('1')==vl and sum(v for i,v in enumerate(up) if sm>>i&1)<=B
 assert r['true_optimum']==capacity(list(map(sum,x['rows'])),B)
 if not r['calls']:assert r['objective']==0 and capacity([x['T']*p for p in x['caps']],B)>=capacity([0]*len(up),B)-x['epsilon']

def audit(root=ROOT,source=False,write=False):
 out=root/'outputs/full-mean-grid-20261005';raw=[json.loads(l) for l in (out/'records.jsonl').open()]
 assert len(raw)==len({key(x) for x in raw})==1920
 spec=json.loads((root/'review-revision/evidence-discovery-implementation-20261005/full-mean-protocol.json').read_text())
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in spec['source_bindings'].items())
 expect={(p,s,q,stop) for p in spec['panels'] for s in spec['splits'] for q in spec['q'] for stop in spec['stopping']};assert set(map(key,raw))==expect
 cases={key(x):x for x in raw};primary_unclosed=sum(not x['joint']['joint_optimal'] or not x['separate']['joint_optimal'] or x['union'] is None or x['union']['status']=='UNRESOLVED' for x in raw)
 closures=0
 for path in sorted(out.glob('closure-*.jsonl')):
  for c in map(json.loads,path.open()):
   k=tuple(c['key']);assert k in cases and c['primary']==cases[k]
   new=c['closed'];assert key(new)==k
   for f in ['rows','caps','observed','N','k','T','budget','epsilon','original_output_ids','selected_count']:assert new[f]==cases[k][f]
   for kind,attempts in c['threshold_attempts'].items():
    active=[r for r,p in zip(new['rows'],new['caps']) if p];m=len(active);L=capacity(list(map(sum,active)),new['budget']);pmax=min(L,m-new['epsilon']-1)+new['epsilon']+1
    levels=[t for t in range(max(map(sum,active),default=0)+1) if pmax*t-sum(max(0,t-sum(r)) for r in active)>=new['budget']+1] or [0]
    assert [a['threshold'] for a in attempts]==levels
    lower=min(a['result']['joint_lower_bound'] for a in attempts);best=min(a['result']['objective'] for a in attempts)
    assert new[kind]['joint_lower_bound']==lower and new[kind]['objective']==best and new[kind]['joint_optimal']==(lower>=best)
    for a in attempts:
     for r in a['attempts']:valuecheck(new,r,kind=='separate')
   cases[k]=new;closures+=1
 old=[]
 for x in map(json.loads,(root/'outputs/deduplicated-evidence/records.jsonl').open()):
  if x['scope']=='full':old.append(x)
 assert len(old)==96
 for x in old:
  c=cases[(x['dataset'],x['split'],x['q'],'exact')]
  for field in ['rows','caps','observed','budget','N','k','T']:assert c[field]==x[field]
  if c['joint']['joint_optimal']:assert c['joint']['objective']==x['joint_minimum']
  if c['separate']['joint_optimal']:assert c['separate']['objective']==x['additive_minimum']
  if c['union'] and c['union']['status'] in ['OPTIMAL','PROVED_BY_BOUND_SANDWICH','PROVED_BY_JOINT_LOWER_BOUND']:assert c['union']['union_minimum']==x['result']['union_minimum']
 base={}
 for x in csv.DictReader((root/'outputs/tolerance-sensitivity/stop_records.csv').open()):
  if x['aggregator']=='mean' and x['tau'] in ['0','1/50']:base[(x['dataset'],int(x['split']),float(x['q']),'exact' if x['tau']=='0' else 'primary',x['method'])]=x
 newpol={}
 for x in csv.DictReader((root/'outputs/frontier-priority-20261005/records.csv').open()):newpol[(*key(x),x['method'])]=x
 records=[];sourcechecks=0
 for k,x in sorted(cases.items()):
  assert x['history']=='empty' and x['observed']==[0]*len(x['rows']) and x['selected_count']==len(x['rows'])
  assert x['epsilon']==(0 if x['stopping']=='exact' else math.ceil(.02*x['selected_count']))
  assert x['k']==max(1,round(x['q']*x['N'])) and x['budget']==2*x['k']*7*x['T']//10
  assert len(x['rows'])==len(x['caps'])==len(x['original_output_ids']) and len(set(x['original_output_ids']))==len(x['rows'])
  assert all(len(r)==x['T'] and all(type(v) is int and 0<=v<=p for v in r) for r,p in zip(x['rows'],x['caps']))
  if source and x['stopping']=='exact':
   from analyze_acquisition_mechanisms import prepare
   import numpy as np
   c=prepare((x['dataset'],'mean',x['split'],x['q']));ids=np.flatnonzero(c['selected']);ids=ids[np.argsort(c['tie'][ids])]
   assert ids.tolist()==x['original_output_ids'] and c['f'][:,ids].T.tolist()==x['rows'] and c['p'][ids].tolist()==x['caps']
   assert (c['N'],c['k'],c['T'],c['budget'])==(x['N'],x['k'],x['T'],x['budget']);sourcechecks+=1
  for kind in ['joint','separate']:valuecheck(x,x[kind],kind=='separate')
  u=x['union'];unionproven=u is not None and u['status'] in ['OPTIMAL','PROVED_BY_BOUND_SANDWICH','PROVED_BY_JOINT_LOWER_BOUND']
  if unionproven:
   assert x['joint']['joint_optimal'] and x['separate']['joint_optimal']
   assert x['joint']['objective']<=u['union_minimum']<=x['separate']['objective']
   if u['status']=='PROVED_BY_BOUND_SANDWICH':assert x['joint']['objective']==u['union_minimum']==x['separate']['objective']
   elif u['status']=='PROVED_BY_JOINT_LOWER_BOUND':
    from verify_union_shortcut import verify
    verify(x,u)
   else:witness(x,u);assert u['split_minimum']==x['separate']['objective']
  r={n:x[n] for n in ['dataset','split','q','stopping','epsilon','N','k','T','budget','selected_count','active_rows']}
  r.update(joint_lower=x['joint']['joint_lower_bound'],joint_upper=x['joint']['objective'],joint_proven=int(x['joint']['joint_optimal']),split_lower=x['separate']['joint_lower_bound'],split_upper=x['separate']['objective'],split_proven=int(x['separate']['joint_optimal']),union_minimum=u['union_minimum'] if unionproven else '',union_proven=int(unionproven),initial_gap=len(x['rows'])-capacity([x['T']*p for p in x['caps']],x['budget']))
  for method in ['fixed','random','largest_width','reference_priority']:
   b=base[(*k,method)];Q=int(b['queries']);assert Q>=x['joint']['joint_lower_bound']
   if x['joint']['joint_optimal']:assert Q>=x['joint']['objective']
   assert int(b['integer_budget'])==x['budget'] and int(b['selected_count'])==x['selected_count']
   r[method+'_queries']=Q;r[method+'_ratio']=Q/x['joint']['objective'] if x['joint']['joint_optimal'] and x['joint']['objective']>0 else ''
  for method in ['joint','safety','exclusion']:
   b=newpol[(*k,method)];Q=int(b['queries']);assert Q>=x['joint']['joint_lower_bound']
   if x['joint']['joint_optimal']:assert Q>=x['joint']['objective']
   r['frontier_'+method+'_queries']=Q;r['frontier_'+method+'_ratio']=Q/x['joint']['objective'] if x['joint']['joint_optimal'] and x['joint']['objective']>0 else ''
  records.append(r)
 summaries=[]
 for panel in spec['panels']:
  for q in spec['q']:
   for stop in spec['stopping']:
    g=[r for r in records if (r['dataset'],r['q'],r['stopping'])==(panel,q,stop)];assert len(g)==40
    proved=[r for r in g if r['joint_proven']];unions=[r for r in g if r['union_proven']]
    r=dict(dataset=panel,q=q,stopping=stop,instances=40,joint_proven=len(proved),union_proven=len(unions),zero_minima=sum(x['joint_upper']==0 for x in proved),positive_minima=sum(x['joint_upper']>0 for x in proved),mean_joint_lower=statistics.fmean(x['joint_lower'] for x in g),mean_joint_upper=statistics.fmean(x['joint_upper'] for x in g),joint_below_union=sum(x['joint_upper']<x['union_minimum'] for x in unions),union_sum=sum(x['union_minimum'] for x in unions),joint_sum=sum(x['joint_upper'] for x in unions),split_sum=sum(x['split_upper'] for x in unions))
    for method in ['fixed','random','largest_width','reference_priority','frontier_joint','frontier_safety','frontier_exclusion']:
     a=[x[method+'_ratio'] for x in g if x[method+'_ratio']!=''];r[method+'_ratio']=statistics.fmean(a) if a else '';r[method+'_queries']=statistics.fmean(x[method+'_queries'] for x in g)
    summaries.append(r)
 result=dict(status='PASS_FULL_MEAN_SAVED_WITNESSES_AND_ACCOUNTING',records=len(records),source_instances_verified=sourcechecks,source_verification_requested=source,previous_exact_instances_matched=96,primary_unclosed=primary_unclosed,append_only_closures=closures,joint_proven=sum(r['joint_proven'] for r in records),separate_proven=sum(r['split_proven'] for r in records),union_proven=sum(r['union_proven'] for r in records),online_counts_checked=7*len(records),all_minima_closed=all(r['union_proven'] for r in records),human_proof_certified=False,new_scoring_inference=False)
 if write:
  for name,data in [('audited_records.csv',records),('summary.csv',summaries)]:
   with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
  (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result,records
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--source',action='store_true');a=p.parse_args();print(json.dumps(audit(source=a.source,write=True)[0],indent=2))

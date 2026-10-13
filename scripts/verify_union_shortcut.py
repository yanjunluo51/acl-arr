"""Check a separately-optimal component witness attaining a proved joint minimum."""
from audit_deduplicated_evidence import capacity

def verify(case,r):
 assert r['status']=='PROVED_BY_JOINT_LOWER_BOUND'
 j=case['joint'];assert j['joint_optimal'] and j['objective']==j['joint_lower_bound']
 assert r['certified_joint_minimum']==r['union_minimum']==j['objective']
 rows,caps,T,B,eps=case['rows'],case['caps'],case['T'],case['budget'],case['epsilon']
 free=caps.count(0);L=capacity(list(map(sum,rows)),B)-free
 s=r['safe_target'];assert max(0,L-eps)<=s<=L
 target=next(t for t in r['targets'] if t['target']==s)
 assert len([t for t in r['targets'] if t['target']==s])==1
 for name,field in [('safety','safety_minimum'),('exclusion','exclusion_minimum')]:
  v=target[field];assert type(v) is int and v>=0
  if v:
   calls=[c for c in r['solver_calls'] if c['target']==s and c['mode']==name];assert len(calls)==1
   c=calls[0];assert c['status']==0 and c['optimality_gap'] is not None and 0<=c['optimality_gap']<1e-10
   assert abs(c['dual_bound']-v)<1e-6
  mask=r[name+'_mask'];assert type(mask) is int and 0<=mask<1<<(len(rows)*T) and bin(mask).count('1')==v
 U=r['safety_mask']|r['exclusion_mask'];assert r['union_mask']==U and bin(U).count('1')==r['union_minimum']
 def bounds(mask):
  lo=[];up=[]
  for i,(row,p,o) in enumerate(zip(rows,caps,case['observed'])):
   q=mask>>(i*T)&((1<<T)-1);assert not q&o
   known=q|o;a=sum(v for c,v in enumerate(row) if known>>c&1)
   lo.append(a);up.append(a+(T-bin(known).count('1'))*p)
  return lo,up
 _,a=bounds(r['safety_mask']);b,_=bounds(r['exclusion_mask']);lo,up=bounds(U)
 assert capacity(a,B)>=s+free and capacity(b,B)<=s+free+eps
 assert capacity(lo,B)-capacity(up,B)<=eps
 sm=r['safe_mask'];assert type(sm) is int and 0<=sm<1<<len(rows)
 assert bin(sm).count('1')==capacity(up,B) and sum(v for i,v in enumerate(up) if sm>>i&1)<=B
 return True

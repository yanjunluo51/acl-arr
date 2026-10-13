"""Prove a global union optimum without claiming every target is optimal.

For each admissible target, a valid lower bound suffices. A feasible globally
best witness with separately optimal components supplies the upper bound.
Original per-target solver statuses are never overwritten.
"""
import math
from audit_deduplicated_evidence import capacity

def certify(case,priors,return_partial=False):
 rows,caps,T,B,eps=case['rows'],case['caps'],case['T'],case['budget'],case['epsilon']
 free=caps.count(0);m=len(rows)-free;L=capacity(list(map(sum,rows)),B)-free
 initial_lo=[sum(v for j,v in enumerate(row) if o>>j&1) for row,o in zip(rows,case['observed'])]
 initial_up=[v+(T-bin(o).count('1'))*p for v,o,p in zip(initial_lo,case['observed'],caps)]
 targets=list(range(max(0,L-eps),L+1));bounds={s:0 for s in targets};components={};evidence=[]
 for r in priors:
  ts={t['target']:t for t in r.get('targets',[])}
  assert len(ts)==len(r.get('targets',[])) and set(ts)<=set(targets)
  for c in r.get('solver_calls',[]):
   s,mode=c['target'],c['mode'];assert s in targets and mode in ['safety','exclusion','union']
   if 'partition_receipt' in c:
    part=c['partition_receipt'];active=[row for row,p in zip(rows,caps) if p]
    valid=[t for t in range(max(map(sum,active),default=0)+1)
      if (s+eps+1)*t-sum(max(0,t-sum(row)) for row in active)>=B+1]
    assert valid
    expected=list(range(min(valid),max(valid)+1))
    if 'threshold_screen' in c:
     screen=c['threshold_screen'];ex=screen['exclusion_receipt']
     assert ex in r['solver_calls'] and ex['target']==s and ex['mode']=='exclusion' and ex['status']==0
     assert 'threshold_screen' not in ex and 'partition_receipt' in ex
     assert screen['component_minimum']==ex['dual_bound']==ex['partition_receipt']['global_lower']
     assert ex['partition_receipt']['levels']==expected
     viable=[d['threshold'] for d in ex['partition_receipt']['details'] if not d['infeasible'] and d['lower']<=screen['component_minimum']]
     assert viable;expected=list(range(min(viable),max(viable)+1))
    assert part['levels']==expected
    assert [d['threshold'] for d in part['details']]==part['levels']
    for d in part['details']:
     bad=any(z['status']==2 for z in d['attempts'])
     assert d['infeasible']==bad
     if bad:assert d['lower'] is None
     else:
      ls=[0]
      for z in d['attempts']:
       if z['relaxed'] and z['status']==0:ls.append(max(0,math.ceil(z['objective']-1e-6)))
       elif not z['relaxed'] and math.isfinite(z['dual_bound']):ls.append(max(0,math.ceil(z['dual_bound']-1e-6)))
      assert d['lower']==max(ls)
    lows=[d['lower'] for d in part['details'] if not d['infeasible']]
    assert part['all_infeasible']==(not lows)
    if not lows:assert c['status']==2 and part['global_lower'] is None
    else:
     assert min(lows)==part['global_lower']==c['dual_bound']
     if c['status']==0:assert part['incumbent']==min(lows)
   cutoff_infeasible=c['status']==2 and mode=='union' and type(c.get('improvement_cutoff')) is int
   if c['status'] not in [0,1] and not cutoff_infeasible:continue
   dual=c.get('dual_bound')
   if not cutoff_infeasible and (dual is None or not math.isfinite(dual)):continue
   lower=c['improvement_cutoff']+1 if cutoff_infeasible else max(0,math.ceil(dual-1e-6))
   if mode in ['safety','exclusion']:
    bounds[s]=max(bounds[s],lower)
    if c['status']==0 and c.get('optimality_gap') is not None and 0<=c['optimality_gap']<1e-10:
     v=int(round(dual));assert abs(v-dual)<1e-6
     if (s,mode) in components:assert components[s,mode]['value']==v
     components[s,mode]=dict(value=v,receipt=c)
    evidence.append(dict(target=s,mode=mode,lower=lower,receipt=c))
   elif mode=='union':
    # The union model uses separately minimal component cardinalities.
    t=ts.get(s,{})
    if not all(k in t for k in ['safety_minimum','exclusion_minimum']):continue
    checks=[]
    for mode2 in ['safety','exclusion']:
     v=t[mode2+'_minimum']
     cc=[z for z in r['solver_calls'] if z['target']==s and z['mode']==mode2]
     if v==0 and not cc:
      assert capacity(initial_up,B)>=s+free if mode2=='safety' else capacity(initial_lo,B)<=s+free+eps
      checks.append(dict(mode=mode2,value=0,automatic=True));continue
     valid=[z for z in cc if z['status']==0 and z.get('optimality_gap') is not None and 0<=z['optimality_gap']<1e-10 and abs(z['dual_bound']-v)<1e-6]
     if not valid:break
     checks.append(dict(mode=mode2,value=v,receipt=valid[0]))
    if len(checks)==2:
     bounds[s]=max(bounds[s],lower);evidence.append(dict(target=s,mode='union',lower=lower,receipt=c,component_optima=checks))
 # Free zero-size safety and automatic exclusion need no solver call.
 for s in targets:
  if s==0:components.setdefault((s,'safety'),dict(value=0,automatic=True))
  if s+eps+1>m:components.setdefault((s,'exclusion'),dict(value=0,automatic=True))
 candidates=[]
 for r in priors:
  if not all(k in r for k in ['union_mask','safety_mask','exclusion_mask','safe_mask','safe_target','union_minimum']):continue
  s=r['safe_target'];assert s in targets
  if not all((s,mode) in components for mode in ['safety','exclusion']):continue
  A,D=r['safety_mask'],r['exclusion_mask'];U=A|D
  assert U==r['union_mask'] and bin(U).count('1')==r['union_minimum']
  assert bin(A).count('1')==components[s,'safety']['value']
  assert bin(D).count('1')==components[s,'exclusion']['value']
  def bnd(mask):
   assert type(mask) is int and 0<=mask<1<<(len(rows)*T)
   lo=[];up=[]
   for i,(row,p,o) in enumerate(zip(rows,caps,case['observed'])):
    q=mask>>(i*T)&((1<<T)-1);assert not q&o;obs=q|o
    v=sum(v for j,v in enumerate(row) if obs>>j&1);lo.append(v);up.append(v+(T-bin(obs).count('1'))*p)
   return lo,up
  _,a=bnd(A);d,_=bnd(D);lo,up=bnd(U)
  assert capacity(a,B)>=s+free and capacity(d,B)<=s+free+eps
  assert capacity(lo,B)-capacity(up,B)<=eps
  sm=r['safe_mask'];assert type(sm) is int and 0<=sm<1<<len(rows)
  assert bin(sm).count('1')==capacity(up,B) and sum(v for i,v in enumerate(up) if sm>>i&1)<=B
  candidates.append(r)
 if not candidates:return None
 best=min(candidates,key=lambda r:r['union_minimum']);upper=best['union_minimum'];lower=min(bounds.values())
 assert lower<=upper,('inconsistent numerical bounds',lower,upper)
 if lower!=upper and not return_partial:return None
 return dict(status='PROVED_BY_TARGET_LOWER_BOUNDS' if lower==upper else 'UNRESOLVED_TARGET_BOUNDS',union_minimum=upper,global_lower=lower,
   target_bounds=[dict(target=s,lower=bounds[s]) for s in targets],bound_evidence=evidence,
   best_witness=best,component_receipts=[dict(target=best['safe_target'],mode=mode,**components[best['safe_target'],mode]) for mode in ['safety','exclusion']],
   scope='global minimum only; unresolved per-target optima remain unresolved',human_proof_certified=False)

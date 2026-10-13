"""Exhaustive integer-threshold disaggregation of the same MILP arrays."""
import time,math
from types import SimpleNamespace
import numpy as np
from scipy.optimize import Bounds
from highs_adapter import milp

def partition_milp(c,integrality,bounds,constraints,options,threshold_index,levels):
 start=time.monotonic();levels=list(levels);idx=threshold_index
 assert levels and levels==list(range(int(bounds.lb[idx]),int(bounds.ub[idx])+1))
 assert integrality[idx]==1 and np.all(np.asarray(c)>=0)
 best=None;bestx=None;details=[];total=float(options['time_limit'])
 def call(t,relax,limit):
  lo=np.array(bounds.lb,copy=True);hi=np.array(bounds.ub,copy=True);lo[idx]=hi[idx]=t
  result=milp(c,np.zeros_like(integrality) if relax else integrality,Bounds(lo,hi),constraints,dict(options,time_limit=limit))
  lower=0
  if result.status==2:lower=None
  elif relax and result.status==0:lower=max(0,math.ceil(result.fun-1e-6))
  elif not relax and math.isfinite(result.mip_dual_bound):lower=max(0,math.ceil(result.mip_dual_bound-1e-6))
  entry=dict(relaxed=relax,status=result.status,message=result.message,objective=result.fun,dual_bound=result.fun if relax and result.status==0 else result.mip_dual_bound,lower=lower)
  return result,entry
 def feasible(result):
  if result.x is None:return False
  x=result.x;ints=np.flatnonzero(integrality)
  if np.max(np.abs(x[ints]-np.rint(x[ints])),initial=0)>1e-6:return False
  # Original matrix feasibility, not only the rounded objective.
  a=constraints.A@x
  return bool(np.all(x>=bounds.lb-1e-6) and np.all(x<=bounds.ub+1e-6) and np.all(a>=constraints.lb-1e-5) and np.all(a<=constraints.ub+1e-5))
 for t in levels:
  remaining=total-(time.monotonic()-start)
  d=dict(threshold=t,lower=0,infeasible=False,attempts=[]);details.append(d)
  if remaining<=.05:continue
  r,e=call(t,True,min(10,remaining));d['attempts'].append(e);d['infeasible']=r.status==2;d['lower']=e['lower']
  if feasible(r) and (best is None or r.fun<best):best=int(round(r.fun));bestx=r.x
 for d in sorted(details,key=lambda d: float('inf') if d['infeasible'] else d['lower']):
  if d['infeasible'] or (best is not None and d['lower']>=best):continue
  remaining=total-(time.monotonic()-start)
  if remaining<=.05:break
  r,e=call(d['threshold'],False,min(90,remaining));d['attempts'].append(e)
  if r.status==2:d.update(infeasible=True,lower=None)
  else:d['lower']=max(d['lower'],e['lower'])
  if feasible(r) and (best is None or r.fun<best):best=int(round(r.fun));bestx=r.x
 lower=min((d['lower'] for d in details if not d['infeasible']),default=float('inf'))
 assert best is None or lower<=best
 status=2 if math.isinf(lower) else 0 if best is not None and lower==best else 1
 proof=dict(kind='EXHAUSTIVE_INTEGER_THRESHOLD_PARTITION',levels=levels,details=details,global_lower=None if math.isinf(lower) else lower,all_infeasible=status==2,incumbent=best)
 return SimpleNamespace(status=status,message='derived exhaustive threshold partition; raw highspy statuses retained',x=bestx,fun=best,
  mip_dual_bound=lower,mip_gap=None if best is None else (best-lower)/max(1,abs(best)),partition_receipt=proof)

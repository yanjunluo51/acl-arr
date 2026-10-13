"""Full test partitions for the frozen WMT22 confirmation; no quality labels."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,random,math,time,multiprocessing,hashlib,gzip
import numpy as np
P=Path(__file__).resolve().parent;D=P.parent;R=D.parents[1]
sys.path[:0]=[str(R/'scripts'),str(R/'review-revision/evidence-structure-revision')]
from query_selection import aggregate,endpoint_cost,all_flips,fit_prior,capacity
from mapping_column_experiments import cdf
from review_priority import solve_multi_quantized
from frontier_priority import acquire
from variable_target_certificate import certificate
from deduplicated_certificates import union_certificate
from tolerance_certificates import minimum_gap_certificate
from column_union import frontiers,envelope,optimize,direct

def task(key):
 lp,agg,q=key;tic=time.monotonic();spec=json.loads((P/'protocol.json').read_text())
 z=np.load(P/f'{lp}.npz');models=z['models'].tolist();scores=z['scores'];g=scores.shape[2];docs=z['documents'].tolist()
 units=list(dict.fromkeys(docs));seed=spec['seed']+1000*spec['panels'].index(lp);random.Random(seed).shuffle(units);third=len(units)//3
 sets=[set(units[:third]),set(units[third:2*third]),set(units[2*third:])];assert not(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
 ix=[np.array([i*g+j for i,d in enumerate(docs) if d in ss for j in range(g)]) for ss in sets];rr,tt=ix[0],ix[2]
 raw=scores.reshape(len(models),-1);orient=[];anchor=raw[models.index('BLEURT-20'),rr]
 for row in raw:
  corr=float(np.corrcoef(row[rr],anchor)[0,1]) if np.ptp(row[rr]) and np.ptp(anchor) else None
  orient.append(-1 if corr is not None and corr<0 else 1)
 raw=raw*np.array(orient)[:,None]
 ref=np.array([cdf(v[rr],v[rr],'right') for v in raw]);test=np.array([cdf(v[tt],v[rr],'right') for v in raw]);base,hidden=test[:7],test[7:];T,N=hidden.shape
 cutoff=float(np.sort(aggregate(ref[:7],agg))[-max(1,round(q*len(rr)))]);selected=aggregate(base,agg)>=cutoff;p=endpoint_cost(base,cutoff,agg);f=all_flips(base,hidden,cutoff,agg);assert np.all(f<=p)
 prior=fit_prior(ref[:7],ref[7:],base,cutoff,p,agg);S=int(selected.sum());k=max(1,round(q*N));B=2*k*7*T//10;eps=math.ceil(.02*S);tie=np.random.default_rng(seed+700001).permutation(N)
 ids=np.flatnonzero(selected);ids=ids[np.argsort(tie[ids])];rows=f[:,ids].T.tolist();caps=p[ids].tolist();active=np.flatnonzero(selected&(p>0));active=active[np.argsort(tie[active])];free=S-len(active)
 out=dict(panel=lp,pooling=agg,q=q,N=N,T=T,k=k,budget=B,epsilon=eps,selected_count=S,full_information_count=capacity(list(map(sum,rows)),B),cutoff=cutoff,reference_output_ids=rr.tolist(),test_output_ids=tt.tolist(),orientation=orient,models=models,rows=rows,caps=caps,observed=[0]*S,policies={},offline={},columns=[])
 for method in spec['methods']:
  trace,states,tol,exact=solve_multi_quantized(base,selected,p,prior,cutoff,agg,T,np.array([B]),tie,method,seed+37,lambda r,i:float(hidden[r,i]),[],eps)
  out['policies'][method]=dict(trace=trace,primary=tol[0],exact=exact[0])
 if agg=='mean':
  truth=f[:,active].T
  for mode in ['joint','safety','exclusion']:
   v=acquire(p[active],prior[active],B,eps,lambda i,r:int(truth[i,r]),mode)
   # Normalize query traces to evaluator index, original test-row index, contribution.
   tr=[[r,int(active[i]),v] for i,r,v in v['trace']]
   stops={}
   for st,a in v['stops'].items():stops[st]={**a,'V_lower':a['V_lower']+free,'V_upper':a['V_upper']+free}
   out['policies']['frontier_'+mode]=dict(trace=tr,**stops)
 for st,e in [('exact',0),('primary',eps)]:
  if agg=='median':
   w=minimum_gap_certificate((f.sum(axis=0)[active]//4).tolist(),T,B//4,e);out['offline'][st]=dict(kind='ODD_MEDIAN_CLOSED_FORM',minimum=w['queries'])
  else:
   j=certificate(rows,caps,B,e,seconds=spec['joint_solver_seconds']);s=certificate(rows,caps,B,e,seconds=spec['separate_solver_seconds'],separated=True)
   if j['joint_optimal'] and s['joint_optimal'] and j['objective']==s['objective']:u=dict(status='CLOSED_BY_SANDWICH',union_minimum=j['objective'])
   elif j['joint_optimal'] and s['joint_optimal']:u=union_certificate(rows,caps,B,e,seconds=spec['union_solver_seconds'])
   else:u=dict(status='UNRESOLVED_COMPONENT_OPTIMALITY')
   out['offline'][st]=dict(joint=j,separate=s,union=u)
 # Same complete family of column actions, with all tied component optima.
 if agg=='mean':
  if not rows:out['columns']=[dict(stopping=st,epsilon=e,joint=0,union=0) for st,e in [('exact',0),('primary',eps)]]
  else:
   a=np.asarray(rows,np.int64);pp=np.asarray(caps,np.int64);grouped,freq=np.unique(np.column_stack([pp,a]),axis=0,return_counts=True)
   vl,vh,pc=frontiers(grouped[:,1:],grouped[:,0],freq,B);A,Z=envelope(vl,vh,pc,T,S)
   x=dict(rows=rows,caps=caps,T=T,budget=B)
   for st,e in [('exact',0),('primary',eps)]:
    vals=list(map(int,optimize(vl,vh,pc,A,Z,int(vl[-1]),e)));j,jm,u,am,bm,target,na,nb,split=vals
    assert direct(x,jm)[1]-direct(x,jm)[0]<=e
    assert direct(x,am)[0]>=target and direct(x,bm)[1]<=target+e
    out['columns'].append(dict(stopping=st,epsilon=e,joint=j,union=u,split=split,joint_mask=jm,safety_mask=am,exclusion_mask=bm,safe_target=target,subsets=len(pc)))
 out['seconds']=time.monotonic()-tic
 path=P/'cases'/f'{lp}_{agg}_{q:.2f}.json.gz'
 with gzip.open(path,'wt') as f:f.write(json.dumps(out,separators=(',',':'))+'\n')
 return dict(panel=lp,pooling=agg,q=q,seconds=out['seconds'],file=path.name)

def main():
 assert not (P/'progress.json').exists();(P/'cases').mkdir(exist_ok=False);spec=json.loads((P/'protocol.json').read_text())
 assert all(hashlib.sha256((R/'scripts'/n).read_bytes()).hexdigest()==h for n,h in spec['source_bindings'].items())
 expected=[(lp,a,q) for lp in spec['panels'] for a in spec['pooling'] for q in spec['q']];completed=[]
 def save(status): (P/'progress.json').write_text(json.dumps(dict(status=status,expected=len(expected),completed=completed),indent=2)+'\n')
 save('RUNNING')
 try:
  with multiprocessing.get_context('spawn').Pool(3) as pool:
   for x in pool.imap_unordered(task,expected):completed.append(x);save('RUNNING');print(len(completed),len(expected),x,flush=True)
  save('EXECUTED_PENDING_INDEPENDENT_AUDIT')
 except Exception as e:save('FAILED_PRESERVE_COMPLETED');raise
if __name__=='__main__':main()

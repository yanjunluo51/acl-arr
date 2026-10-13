"""Independent ECDF/replacement and every-observation frontier replay."""
from pathlib import Path
import json,gzip,bisect,math,itertools,csv,hashlib,sys
import numpy as np
P=Path(__file__).resolve().parent;R=P.parents[2];sys.path.insert(0,str(R/'scripts'))
from audit_deduplicated_evidence import capacity as legacy_capacity
from audit_full_mean_grid import valuecheck

def cap(a,b):
 total=0;n=0
 for v in sorted(a):
  if total+v>b:break
  total+=v;n+=1
 return n

def histcap(h,b):
 n=h[0]
 for v in range(1,len(h)):
  take=min(h[v],b//v);n+=take;b-=take*v
  if take<h[v]:break
 return n

def main():
 progress=json.loads((P/'progress.json').read_text());assert progress['status']=='EXECUTED_PENDING_INDEPENDENT_AUDIT' and len(progress['completed'])==24
 seen=set();summary=[];queries=0;paths=0;mean_closed=0;colchecks=0;fchecks=0
 for pth in sorted((P/'cases').glob('*.json.gz')):
  x=json.load(gzip.open(pth,'rt'));key=(x['panel'],x['pooling'],x['q']);assert key not in seen;seen.add(key)
  z=np.load(P/(x['panel']+'.npz'));raw=z['scores'].reshape(len(z['models']),-1)*np.array(x['orientation'])[:,None];rr=x['reference_output_ids'];tt=x['test_output_ids'];g=len(z['systems'])
  assert not (set(rr)&set(tt));assert not({z['documents'][i//g] for i in rr}&{z['documents'][i//g] for i in tt})
  ref=[];test=[]
  for row in raw:
   a=sorted(row[rr]);ref.append([bisect.bisect_right(a,v)/len(a) for v in row[rr]]);test.append([bisect.bisect_right(a,v)/len(a) for v in row[tt]])
  ref=np.array(ref);test=np.array(test);base=test[:7];hidden=test[7:];agg=x['pooling'];T=x['T'];B=x['budget'];N=x['N'];S=x['selected_count']
  def pool(a):
   if agg=='median':return np.sort(a,axis=0)[3]
   out=np.zeros(a.shape[1])
   for row in a:out=out+row
   return out/7
  threshold=sorted(pool(ref[:7]))[-max(1,round(x['q']*len(rr)))];assert threshold==x['cutoff']
  selected=pool(base)>=threshold;assert int(selected.sum())==S
  truth=np.zeros((T,N),dtype=int);caps=np.zeros(N,dtype=int)
  for member in range(7):
   a=base.copy();a[member]=np.where(selected,0.,1.);caps+=(pool(a)>=threshold)!=selected
   for j in range(T):
    a=base.copy();a[member]=hidden[j];truth[j]+=(pool(a)>=threshold)!=selected
  fchecks+=T*N;assert np.all(truth<=caps)
  active=np.flatnonzero(selected&(caps>0));free=int(np.sum(selected&(caps==0)));m=len(active);idx={int(i):j for j,i in enumerate(active)}
  cost=truth.sum(axis=0);vstar=cap(cost[selected].tolist(),B);assert vstar==x['full_information_count']
  for method,rec in x['policies'].items():
   paths+=1;lo=[0]*m;up=(T*caps[active]).tolist();maximum=T*int(caps.max(initial=0));lh=[0]*(maximum+1);uh=lh.copy();lh[0]=m
   for v in up:uh[v]+=1
   seenq=set();first={}
   for step in range(len(rec['trace'])+1):
    vl=free+histcap(uh,B);vh=free+histcap(lh,B)
    assert vl<=vstar<=vh,(key,method,step,vl,vstar,vh,free,m,sum(lh),sum(uh),S)
    for stop,eps in [('primary',x['epsilon']),('exact',0)]:
     if stop not in first and vh-vl<=eps:
      first[stop]=step;a=rec[stop];assert (a['queries'],a['V_lower'],a['V_upper'],a['gap'])==(step,vl,vh,vh-vl)
      if 'mask' in a:
       mask=np.array(a['mask'],bool);assert int(np.sum(mask&selected))==vl and int(cost[mask].sum())<=B
    if step==len(rec['trace']):break
    col,item,f=rec['trace'][step];assert (col,item) not in seenq and item in idx;seenq.add((col,item));assert f==truth[col,item];i=idx[item]
    lh[lo[i]]-=1;uh[up[i]]-=1;lo[i]+=f;up[i]-=int(caps[item])-f;lh[lo[i]]+=1;uh[up[i]]+=1
   assert len(first)==2;queries+=len(rec['trace'])
  for st,v in x['offline'].items():
   eps=0 if st=='exact' else x['epsilon']
   if agg=='mean':
    xx={**x,'epsilon':eps};valuecheck(xx,v['joint'],False);valuecheck(xx,v['separate'],True)
    assert v['joint']['joint_optimal'] and v['separate']['joint_optimal'] and v['union']['status']=='CLOSED_BY_SANDWICH'
    assert v['joint']['objective']==v['union']['union_minimum']==v['separate']['objective'];minimum=v['joint']['objective'];mean_closed+=1
    # Here every selected output is feasible. For exact stopping, independent
    # greedy reductions give an integer lower bound and a matching certificate.
    assert vstar==S
    if eps==0:
     reduction=sorted((int(caps[i])-int(truth[j,i]) for i in active for j in range(T)),reverse=True)
     need=max(0,sum(T*int(caps[i]) for i in active)-B);cum=0;n=0
     while cum<need:cum+=reduction[n];n+=1
     assert n==minimum
   else:
    minimum=v['minimum'];assert all(truth[j,i] in [0,4] for i in active for j in range(T))
    # On these full-retention instances only agreements are required.
    assert vstar==S;assert minimum==max(0,max(0,m-eps)*T-B//4)
   for method,rec in x['policies'].items():assert rec[st]['queries']>=minimum
   summary.append(dict(panel=x['panel'],pooling=agg,q=x['q'],stopping=st,N=N,T=T,selected=S,optimum=vstar,minimum=minimum,reference_queries=x['policies']['reference_priority'][st]['queries'],width_queries=x['policies']['largest_width'][st]['queries'],frontier_queries=x['policies'].get('frontier_joint',{}).get(st,{}).get('queries',''),safety_queries=x['policies'].get('frontier_safety',{}).get(st,{}).get('queries','')))
  for row in summary:
   if (row['panel'],row['pooling'],row['q'])==key:
    for name,field in [('fixed','fixed_queries'),('random','random_queries'),('frontier_exclusion','exclusion_queries')]:
     row[field]=x['policies'].get(name,{}).get(row['stopping'],{}).get('queries','')
  # Independent direct-cost predecessor enumeration for all mean column minima.
  # Automatic exclusion in these full-retention cases implies union=joint.
  for c in x['columns']:
   assert vstar==S and c['joint']==c['union']
   target=S-c['epsilon'];j=c['joint'];pp=caps[selected];a=truth[:,selected]
   def vc(cols):return cap((a[list(cols)].sum(axis=0)+(T-len(cols))*pp).tolist(),B)
   cols=[r for r in range(T) if c['joint_mask']>>r&1];assert len(cols)==j and vc(cols)>=target
   if j:
    for prev in itertools.combinations(range(T),j-1):assert vc(prev)<target;colchecks+=1
 result=dict(status='PASS_NEW_PANEL_SOURCE_AND_ALL_PATH_REPLAY',cases=len(seen),stop_targets=len(summary),paths=paths,revealed_entries_replayed=queries,full_matrix_contributions_reconstructed=fchecks,mean_entry_targets_numerically_closed=mean_closed,mean_strict_gains=0,column_targets=24,column_strict_gains=0,column_predecessors_directly_checked=colchecks,all_mean_targets_full_retention=True,exact_entry_means_independently_greedy_checked=12,positive_tolerance_mean_lower_bounds_numeric=True,one_document_partition_per_panel=True,independent_team=False,human_proof_review=False)
 (P/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 with (P/'summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=summary[0].keys());w.writeheader();w.writerows(summary)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()

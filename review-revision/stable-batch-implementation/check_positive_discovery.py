"""Exact finite checks for the positive-tolerance discovery construction; not a proof oracle."""
from pathlib import Path
from fractions import Fraction as F
import itertools,json,argparse
import numpy as np
D=Path(__file__).resolve().parent

def params(m):
 e=(m+49)//50;s=m-e-1;k=5*s+4;N=20*k;b=(49*k)//5
 assert N>=m and s>=0 and b==49*s+39
 return e,s,k,N,b

def capacity(v,b):
 total=count=0
 for x in sorted(v):
  if total+x>b:break
  total+=x;count+=1
 return count

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=D/'positive-discovery-check.json');a=ap.parse_args()
 # Explicit right-ECDF reference procedure, exact raw-score substitution.
 ref=[[1+(i+3*j)%20 for j in range(14)] for i in range(20)]
 consensus=[sum(F(v,20) for v in row[:7])/7 for row in ref]
 best=max(range(20),key=lambda i:consensus[i]);t=consensus[best];base=[F(v,20) for v in ref[best][:7]]
 assert t==sum(base)/7 and t>F(1,7)
 flips={}
 for score in [F(0),F(1)]:
  flips[str(score)]=sum((sum(base)-base[j]+score)/7<t for j in range(7))
 assert flips=={'0':7,'1':0}
 assert all((F(1)/7)<t for _ in range(7))
 # Check all 0/1-query states and the proposed two-query witness for many sizes.
 sizes=list(range(2,2002))+[10**6,10**9]
 for m in sizes:
  e,s,k,N,b=params(m)
  assert F(k,N)==F(1,20) and (2*k*F(1,10)*49).__floor__()==b
  assert m-s==e+1 and 7*(m-1)<=b
  assert 49*s+35<=b<49*(s+1)+35 # true capacity s+1
  assert 49*s+42>b # one zero reply cannot add a safe row
  assert b>=7 # one positive reply cannot exclude all selected rows
  assert m-(s+1)==e
 # Independently enumerate EVERY entry subset for m=2,3. No proposed minimum supplied.
 counts={};minima={}
 for m in [2,3]:
  e,s,k,N,b=params(m);truth=np.full((m,7),7,dtype=np.int64);truth[-1,:2]=0
  minimum=7*m+1;successful=0;n=1<<(7*m);bit=np.arange(7*m,dtype=np.uint64)
  for start in range(0,n,4096):
   ids=np.arange(start,min(start+4096,n),dtype=np.uint64)
   known=((ids[:,None]>>bit)&1).reshape(-1,m,7).astype(np.int64)
   low=(known*truth).sum(axis=2);up=49-(known*(7-truth)).sum(axis=2)
   vl=(np.cumsum(np.sort(up,axis=1),axis=1)<=b).sum(axis=1)
   vh=(np.cumsum(np.sort(low,axis=1),axis=1)<=b).sum(axis=1)
   good=vh-vl<=e;successful+=int(good.sum())
   if good.any():minimum=min(minimum,int(known.sum(axis=(1,2))[good].min()))
  assert minimum==2;counts[str(m)]={'subsets':n,'successful':successful};minima[str(m)]=minimum
 # Exhaustive all-opposition histories of length <=m-1 for small sizes, with any untouched special row.
 adversarial=0
 for m in [2,3,4,5]:
  e,s,k,N,b=params(m)
  for q in range(m):
   for cells in itertools.combinations(range(7*m),q):
    touched={x//7 for x in cells};assert len(touched)<m
    low=[0]*m
    for x in cells:low[x//7]+=7
    assert capacity(low,b)==m and capacity([49]*m,b)==s
    assert capacity(low,b)-s>e;adversarial+=1
 out=dict(status='PASS_EXACT_FINITE_POSITIVE_TOLERANCE_CHECKS',reference_cutoff=str(t),reference_base=[str(x) for x in base],explicit_flips=flips,parameter_sizes_checked=len(sizes),all_subset_checks=counts,minimum_additional_entries=minima,adversarial_histories_checked=adversarial,general_theorem_independently_human_verified=False,new_NLP_experiment=False)
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

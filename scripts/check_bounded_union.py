"""Independent finite enumeration for the lower-bound shortcut and timeout semantics."""
import json,random
from pathlib import Path
from bounded_union_certificate import union_certificate
from audit_deduplicated_evidence import capacity
ROOT=Path(__file__).resolve().parents[1]
def brute(rows,caps,B,eps):
 T=len(rows[0]);m=len(rows);free=caps.count(0);L=capacity(list(map(sum,rows)),B)-free;states=[]
 for q in range(1<<(m*T)):
  lo=[sum(v for j,v in enumerate(r) if q>>(i*T+j)&1) for i,r in enumerate(rows)]
  up=[lo[i]+(T-bin(q>>(i*T)&((1<<T)-1)).count('1'))*caps[i] for i in range(m)]
  states.append((q,bin(q).count('1'),capacity(up,B),capacity(lo,B)))
 joint=min(n for q,n,vl,vu in states if vu-vl<=eps);union=m*T
 for s in range(max(0,L-eps),L+1):
  amin=min(n for q,n,vl,vu in states if vl>=s+free);bmin=min(n for q,n,vl,vu in states if vu<=s+free+eps)
  aa=[q for q,n,vl,vu in states if vl>=s+free and n==amin];bb=[q for q,n,vl,vu in states if vu<=s+free+eps and n==bmin]
  union=min(union,min(bin(a|b).count('1') for a in aa for b in bb))
 return joint,union

def main(output=None):
 rng=random.Random(20261006);results=[]
 for z in range(80):
  m=1+z%3;T=1+(z//3)%3;caps=[rng.randrange(4) for _ in range(m)];rows=[[rng.randrange(p+1) for _ in range(T)] for p in caps];B=rng.randrange(sum(map(sum,rows))+2);eps=z%(m+1)
  j,u=brute(rows,caps,B,eps)
  r=union_certificate(rows,caps,B,eps,seconds=20,total_seconds=60,presolve=False,certified_joint_minimum=j)
  assert r['status'] in ['OPTIMAL','PROVED_BY_JOINT_LOWER_BOUND'] and r['union_minimum']==u,(z,j,u,r)
  if r['status']=='PROVED_BY_JOINT_LOWER_BOUND':
   assert u==j
   from verify_union_shortcut import verify
   verify(dict(rows=rows,caps=caps,T=T,budget=B,epsilon=eps,observed=[0]*m,joint=dict(joint_optimal=True,objective=j,joint_lower_bound=j)),r)
  results.append(dict(rows=rows,caps=caps,budget=B,epsilon=eps,joint=j,union=u,status=r['status']))
 for T in [2,4]:
  rows=[[1]*T,[1]+[0]*(T-1)];caps=[T+1,T];B=T
  for eps in [0,1]:
   j,u=brute(rows,caps,B,eps)
   r=union_certificate(rows,caps,B,eps,seconds=20,total_seconds=60,presolve=False,certified_joint_minimum=j)
   assert r['status'] in ['OPTIMAL','PROVED_BY_JOINT_LOWER_BOUND'] and r['union_minimum']==u
   if eps==0:assert j==T+1 and u==2*T and r['status']=='OPTIMAL'
   if r['status']=='PROVED_BY_JOINT_LOWER_BOUND':
    from verify_union_shortcut import verify
    verify(dict(rows=rows,caps=caps,T=T,budget=B,epsilon=eps,observed=[0]*2,joint=dict(joint_optimal=True,objective=j,joint_lower_bound=j)),r)
   results.append(dict(rows=rows,caps=caps,budget=B,epsilon=eps,joint=j,union=u,status=r['status']))
 timeout=union_certificate([[1,1],[1,0]],[3,2],2,seconds=1,total_seconds=0,presolve=False,certified_joint_minimum=3)
 assert timeout['status']=='UNRESOLVED'
 x=dict(status='PASS_BOUNDED_UNION_AGAINST_INDEPENDENT_QUERY_SUBSETS',cases=len(results),random_cases=80,strict_family_cases=4,zero_resource_limit_preserves_unknown=True,records=results,general_proof_certified=False)
 if output is not None:
  with Path(output).open('x') as f:f.write(json.dumps(x,indent=2)+'\n')
 print(x['status'],len(results))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,help='New receipt path; existing files are never overwritten')
 a=p.parse_args()
 if a.output is not None and a.output.exists():p.error('--output must name a new file')
 main(a.output)

from pathlib import Path
import json
D=Path(__file__).resolve().parent
f=[[1]*6,[1,0,0,0,0,0]];p=[7,6];b=6
A=[];B=[];J=[]
for mask in range(1<<12):
 lo=[];hi=[]
 for i in range(2):
  seen=[r for r in range(6) if (mask>>(i*6+r))&1];z=sum(f[i][r] for r in seen);lo.append(z);hi.append(z+(6-len(seen))*p[i])
 safe=min(hi)<=b;exclude=sum(lo)>b
 if safe:A.append(mask)
 if exclude:B.append(mask)
 if safe and exclude:J.append(mask)
pc=lambda m:bin(m).count('1');amin=min(map(pc,A));bmin=min(map(pc,B));joint=min(map(pc,J));aa=[x for x in A if pc(x)==amin];bb=[x for x in B if pc(x)==bmin];union=min(pc(a|b) for a in aa for b in bb)
assert (amin,bmin,union,joint)==(5,7,12,7)
(D/'example-check.json').write_text(json.dumps(dict(status='PASS_FINITE_FULL_QUERY_SUBSETS',subsets=4096,safety=amin,exclusion=bmin,best_union=union,joint=joint),indent=2))

"""Independent exhaustive query-subset test, before the NLP comparison."""
import random,json
from pathlib import Path
from itertools import combinations
from deduplicated_certificates import union_certificate

def cap(cost,budget):
    return max((len(c) for n in range(len(cost)+1) for c in combinations(range(len(cost)),n)
                if sum(cost[i] for i in c)<=budget),default=0)

def brute(rows,caps,budget,epsilon,observed):
    m=len(rows);T=len(rows[0]);cells=[(i,r) for i in range(m) for r in range(T) if not observed[i]>>r&1]
    states=[]
    for mask in range(1<<len(cells)):
        ob=observed.copy()
        for j,(i,r) in enumerate(cells):
            if mask>>j&1:ob[i]|=1<<r
        lower=[sum(v for r,v in enumerate(row) if ob[i]>>r&1) for i,row in enumerate(rows)]
        upper=[lower[i]+(T-bin(ob[i]).count('1'))*p for i,p in enumerate(caps)]
        states.append((mask,bin(mask).count('1'),cap(upper,budget),cap(lower,budget)))
    L=cap(list(map(sum,rows)),budget);u=[];sp=[]
    for s in range(max(0,L-epsilon),L+1):
        a=min(x[1] for x in states if x[2]>=s);b=min(x[1] for x in states if x[3]<=s+epsilon)
        aa=[x[0] for x in states if x[1]==a and x[2]>=s];bb=[x[0] for x in states if x[1]==b and x[3]<=s+epsilon]
        u.append(min(bin(x|y).count('1') for x in aa for y in bb));sp.append(a+b)
    return min(u),min(sp)

def main():
    rng=random.Random(5072026);count=0
    for n in range(160):
        m=rng.randint(1,3);T=rng.randint(1,3);caps=[rng.randint(1,3) for _ in range(m)]
        rows=[[rng.randint(0,p) for _ in range(T)] for p in caps];budget=rng.randint(0,sum(map(sum,rows))+1)
        epsilon=rng.randrange(3);obs=[rng.randrange(1<<T) for _ in range(m)]
        u,sp=brute(rows,caps,budget,epsilon,obs)
        for model in [False,True]:
            value=union_certificate(rows,caps,budget,epsilon,obs,independent=model)
            assert value['status']=='OPTIMAL' and (value['union_minimum'],value['split_minimum'])==(u,sp),(rows,caps,budget,epsilon,obs,value,u,sp)
        count+=1
    result=dict(status='PASS_EXHAUSTIVE_QUERY_SUBSET_BACKEND_CHECK',cases=count,models_checked=2,
                all_tied_component_witnesses_enumerated=True,seed=5072026,maximum_entries=9)
    p=Path(__file__).resolve().parents[1]/'review-revision/deduplicated-evidence-implementation/backend-check.json'
    p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()

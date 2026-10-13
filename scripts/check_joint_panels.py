"""Independent MILP using explicit output subsets, not row/threshold DP.

Complete enumeration of the <=4 output safe/excluded subsets; HiGHS minimizes
binary query decisions with zero optimality gap. Every solver witness is checked
in integer arithmetic before accepting its optimum.
"""
import itertools,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/joint-certificates'

def bounds(rows,caps,T,obs):
    low=[sum(v for r,v in enumerate(row) if (obs[i]>>r)&1) for i,row in enumerate(rows)]
    up=[low[i]+(T-bin(obs[i]).count('1'))*caps[i] for i in range(len(rows))]
    return low,up

def cap(x,b):
    return max(bin(mask).count('1') for mask in range(1<<len(x)) if sum(v for i,v in enumerate(x) if (mask>>i)&1)<=b)

def solve(rows,caps,b,e,obs):
    m=len(rows);T=len(rows[0]);lo,up=bounds(rows,caps,T,obs);truth=[sum(v) for v in rows];L=cap(truth,b)
    cells=[(i,r) for i in range(m) if caps[i]>0 for r in range(T) if not (obs[i]>>r)&1]
    joint=[];split=[];calls=0
    def run(coeff,need):
        nonlocal calls
        if all(v<=0 for v in need):return 0
        if not cells:return None
        a=np.array(coeff,float);need=np.array(need,float)
        res=milp(c=np.ones(len(cells)),integrality=np.ones(len(cells)),bounds=Bounds(np.zeros(len(cells)),np.ones(len(cells))),constraints=LinearConstraint(a,need,np.full(len(need),np.inf)),options={'mip_rel_gap':0.0})
        calls+=1
        if res.status==2:return None
        assert res.status==0 and res.mip_gap==0,(res.status,res.message)
        x=np.rint(res.x).astype(np.int64);integer=np.array(coeff,np.int64);demand=np.array(need,np.int64)
        assert np.all((x==0)|(x==1)) and np.all(integer@x>=demand)
        assert abs(res.fun-int(x.sum()))<1e-7
        assert abs(res.mip_dual_bound-res.fun)<1e-7
        return int(x.sum())
    for s in range(max(0,L-e),L+1):
        p=s+e+1;A=list(itertools.combinations(range(m),p)) if p<=m else []
        coeff=[[rows[i][r] if i in subset else 0 for i,r in cells] for subset in A]
        need=[b+1-sum(lo[i] for i in subset) for subset in A]
        exclusion=run(coeff,need)
        safe=[]
        for subset in itertools.combinations(range(m),s):
            if sum(truth[i] for i in subset)>b:continue
            benefit=[caps[i]-rows[i][r] if i in subset else 0 for i,r in cells]
            target=sum(up[i] for i in subset)-b
            q=0;gain=0
            for v in sorted(benefit,reverse=True):
                if gain>=target:break
                gain+=v;q+=1
            assert gain>=target
            safe.append(q)
            result=run(coeff+[benefit],need+[target])
            assert result is not None
            joint.append(result)
        assert safe and exclusion is not None
        split.append(min(safe)+exclusion)
    return min(joint),min(split),calls

def main(write=True):
    assert (OUT/'panel-execution.json').exists();start=time.monotonic();cases=records=calls=0
    for line in (OUT/'instances.jsonl').open():
        z=json.loads(line);rows=z['flips'];caps=z['caps'];T=len(rows[0]);m=len(rows)
        for x in z['records']:
            obs=z['observed'][x['history']];b=x['budget'];e=x['epsilon']
            q,sep,n=solve(rows,caps,b,e,obs);calls+=n
            assert q==x['queries'] and sep==x['split_queries'],(z['key'],x['history'],e,q,sep,x)
            query=x['query_mask'];combined=[v|((query>>(i*T))&((1<<T)-1)) for i,v in enumerate(obs)]
            assert sum(bin(v).count('1') for v in combined)-sum(bin(v).count('1') for v in obs)==q
            lo,up=bounds(rows,caps,T,combined);vl,vh=cap(up,b),cap(lo,b)
            assert vl==x['V_lower'] and vh==x['V_upper'] and vh-vl<=e
            assert sum(up[i] for i in range(m) if (x['safe_mask']>>i)&1)<=b
            records+=1
        cases+=1
        if cases%160==0:print(cases,round(time.monotonic()-start,1),flush=True)
    receipt={'status':'PASS_ALL_SMALL_BATCH_MINIMA_BY_INDEPENDENT_SUBSET_MILP','configuration_cases':cases,'joint_and_separated_minima_checked':records,'zero_gap_integer_MILP_calls':calls,'all_witnesses_rechecked_in_integer_arithmetic':True,'certified_unresolved_instances':0,'elapsed_seconds':time.monotonic()-start}
    assert cases==1920 and records==7680
    if write: (OUT/'panel-independent-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--no-write',action='store_true');a=p.parse_args();main(not a.no_write)

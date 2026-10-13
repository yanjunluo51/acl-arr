"""Independent finite checks of certificate math and hidden-access boundaries."""
import itertools
import numpy as np
from query_selection import (prefix, capacity, exact_offline_certificate,
                             aggregate, flips, all_flips, endpoint_cost,
                             solve, verify_path)


def brute_capacity(cost, b):
    return max((len(C) for L in range(len(cost)+1)
                for C in itertools.combinations(range(len(cost)),L)
                if sum(cost[i] for i in C)<=b),default=0)


def main():
    checks=0
    for n in range(5):
        for cost in itertools.product(range(3),repeat=n):
            for b in range(5):
                expected=brute_capacity(cost,b)
                assert capacity(np.array(cost,dtype=int),b)==expected
                keep=prefix(np.array(cost,dtype=int),b,np.arange(n)[::-1])
                assert keep.sum()==expected and np.array(cost,dtype=int)[keep].sum()<=b
                checks+=2
    # Enumerate actual bit matrices and all possible revealed-cell subsets.
    certificate_cases=0
    for m,T in [(1,1),(1,2),(2,1),(2,2),(3,1),(3,2)]:
        for truth in itertools.product([0,1],repeat=m*T):
            truth=np.array(truth,dtype=int).reshape(m,T)
            z=truth.sum(axis=1)
            for b in range(m*T+1):
                L=brute_capacity(z,b)
                best=m*T+1
                for bits in itertools.product([0,1],repeat=m*T):
                    seen=np.array(bits,dtype=int).reshape(m,T)
                    queries=int(seen.sum())
                    if queries>=best:continue
                    lo=(truth*seen).sum(axis=1)
                    hi=lo+(1-seen).sum(axis=1)
                    if brute_capacity(lo,b)==L==brute_capacity(hi,b):best=queries
                assert exact_offline_certificate(z,T,b)[0]==best
                certificate_cases+=1
    # Ties and endpoints on a rational grid; compare both aggregation paths.
    for agg in ['median','mean']:
        for pool in itertools.product([0,.5,1],repeat=3):
            base=np.tile(np.array(pool)[:,None],(1,5))
            for t in [0, .25, .5, .75, 1]:
                candidate=np.tile(np.array([0,.5,1])[:,None],(1,5))
                full=all_flips(base,candidate,t,agg)
                p=endpoint_cost(base,t,agg)
                assert (full<=p).all()
                for c in range(3):assert flips(base[:,0],candidate[c,0],t,agg)==full[c,0]
                checks+=4
    # Every acquisition mode runs against a logged callback; no truth/labels
    # are arguments to the solver. Independent replay checks each saved state.
    rng=np.random.default_rng(19)
    for agg in ['median','mean']:
        for rep in range(10):
            base=rng.integers(0,11,size=(7,20))/10
            hidden=rng.integers(0,11,size=(5,20))/10
            threshold=.5;selected=aggregate(base,agg)>=threshold
            p=endpoint_cost(base,threshold,agg);cost=all_flips(base,hidden,threshold,agg).sum(axis=0)
            b=15;V=brute_capacity(cost[selected],b) if selected.sum()<12 else capacity(cost[selected],b)
            for method in ['fixed','random','largest_width','reference_priority']:
                access=[]
                def query(c,i):
                    assert (c,i) not in access
                    assert selected[i] and p[i]>0
                    access.append((c,i));return hidden[c,i]
                trace,states,tolerant,exact=solve(base,selected,p,np.full((20,5),1.0),threshold,agg,5,b,np.arange(20),method,rep,query,[0,.1,.25,.5,1],1)
                assert len(trace)==len(access)
                checks+=verify_path(trace,states,tolerant,exact,cost,p,selected,5,b,V,1)
    print({'status':'PASS','checks':checks,'offline_certificate_cases':certificate_cases})


if __name__=='__main__':main()

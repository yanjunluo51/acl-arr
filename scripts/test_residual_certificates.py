"""Independent partial-state and mixed-action verification of residual theory."""
from itertools import combinations, product
from pathlib import Path
import json, time
import numpy as np
from residual_certificates import residual_gap_certificate, mixed_certificate
from tolerance_certificates import minimum_gap_certificate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/acceptance-review-implementation'


def direct_capacity(values,budget):
    total=0
    for i,value in enumerate(sorted(values)):
        total+=value
        if total>budget:return i
    return len(values)


def brute_residual(y,known,b):
    m,T=y.shape
    unknown=list(zip(*np.nonzero(~known)))
    a=[sum(known[i,j] and y[i,j]==0 for j in range(T)) for i in range(m)]
    o=[sum(known[i,j] and y[i,j]==1 for j in range(T)) for i in range(m)]
    best=[m*T+1]*(m+1)
    for subset in range(1<<len(unknown)):
        aa,oo=a.copy(),o.copy();count=0
        for q,(i,j) in enumerate(unknown):
            if subset>>q&1:
                count+=1
                if y[i,j]:oo[i]+=1
                else:aa[i]+=1
        gap=direct_capacity(oo,b)-direct_capacity([T-x for x in aa],b)
        for e in range(gap,m+1):best[e]=min(best[e],count)
    return best


def brute_mixed(y,b,prices,entry_price,epsilon):
    # Enumerate actions directly; do not use residual formulas or their DP.
    m,T=y.shape;best=sum(prices)+entry_price*m*T
    for columns in range(1<<T):
        column_cost=sum(prices[j] for j in range(T) if columns>>j&1)
        if column_cost>=best:continue
        unknown=[(i,j) for i in range(m) for j in range(T) if not columns>>j&1]
        for entries in range(1<<len(unknown)):
            cost=column_cost+entry_price*bin(entries).count('1')
            if cost>=best:continue
            revealed={(i,j) for i in range(m) for j in range(T) if columns>>j&1}
            revealed.update(unknown[q] for q in range(len(unknown)) if entries>>q&1)
            lower=[sum(y[i,j] for j in range(T) if (i,j) in revealed) for i in range(m)]
            upper=[T-sum(1-y[i,j] for j in range(T) if (i,j) in revealed) for i in range(m)]
            if direct_capacity(lower,b)-direct_capacity(upper,b)<=epsilon:best=cost
    return best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started=time.monotonic();checks=states=empty_checks=mixed_checks=random_checks=0
    for m,T in [(3,2),(2,3)]:
        for state in product(range(4),repeat=m*T):
            y=np.array([s%2 for s in state]).reshape(m,T)
            known=np.array([s>=2 for s in state]).reshape(m,T)
            for b in range(m*T+1):
                expected=brute_residual(y,known,b)
                for e in range(m+1):
                    result=residual_gap_certificate(y,known,b,e)
                    assert result['queries']==expected[e],(state,b,e,result,expected)
                    checks+=1
                    if not known.any():
                        assert result['queries']==minimum_gap_certificate(y.sum(axis=1),T,b,e)['queries']
                        empty_checks+=1
            states+=1
        print(json.dumps({'partial_states':states,'residual_checks':checks}),flush=True)
    rng=np.random.default_rng(614927)
    for trial in range(160):
        m,T=4,3;y=rng.integers(0,2,(m,T));known=rng.random((m,T))<.55
        b=int(rng.integers(0,m*T+1));expected=brute_residual(y,known,b)
        for e in range(m+1):
            assert residual_gap_certificate(y,known,b,e)['queries']==expected[e]
            random_checks+=1
    for truth in product(range(2),repeat=6):
        y=np.array(truth).reshape(2,3)
        for b in range(7):
            for e in range(3):
                for prices,unit in [([1,1,1],1),([1,3,7],2),([7,3,1],2)]:
                    result=mixed_certificate(y,b,prices,unit,e)
                    assert result['cost']==brute_mixed(y,b,prices,unit,e),(truth,b,e,prices,result)
                    mixed_checks+=1
    # No-row and full-budget limits still use the complete solver.
    assert residual_gap_certificate(np.zeros((0,3),int),np.zeros((0,3),bool),0)['queries']==0
    assert mixed_certificate(np.zeros((0,3),int),0,[3,2,1])['cost']==0
    receipt={'status':'PASS_INDEPENDENT_RESIDUAL_AND_MIXED_ACTION_ENUMERATION',
             'partial_truth_states':states,'exhaustive_residual_checks':checks,
             'empty_state_matches_existing_formula':empty_checks,
             'larger_random_residual_checks':random_checks,'mixed_action_comparisons':mixed_checks,
             'seconds':time.monotonic()-started,
             'scope':'Finite-instance algebra/implementation validation, not independent human proof or novelty certification.'}
    (OUT/'residual-theory-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()

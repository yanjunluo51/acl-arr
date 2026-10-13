"""Completion oracle and complete subset checks, separate from paper runs."""
import itertools, json
import numpy as np
from column_certificate import (exact_columns, capacity_sorted, certify_subset,
                                verify_minimality)
from query_selection import exact_offline_certificate


def brute_columns(y, b):
    T=y.shape[1]
    for k in range(T+1):
        for cols in itertools.combinations(range(T), k):
            a=sum(1 << c for c in cols)
            if certify_subset(y,b,a)[0] == certify_subset(y,b,a)[1]:
                return k
    raise AssertionError


def main():
    cases=0
    for m,T in [(0,3),(1,1),(1,3),(2,3),(3,2)]:
        for v in itertools.product([0,1],repeat=m*T):
            y=np.array(v,dtype=np.int64).reshape(m,T)
            for b in range(m*T+1):
                Q=exact_offline_certificate(y.sum(axis=1),T,b)[0]
                res=exact_columns(y,b,Q)
                assert res['K_col']==brute_columns(y,b)
                verify_minimality(y,b,res)
                # Explicit completions for every queried column subset.
                for a in range(1 << T):
                    unknown=[(i,c) for i in range(m) for c in range(T)
                             if not (a & (1 << c))]
                    opt=[]
                    for entries in itertools.product([0,1],repeat=len(unknown)):
                        z=y.copy()
                        for pos,bit in zip(unknown,entries):z[pos]=bit
                        opt.append(capacity_sorted(z.sum(axis=1),b))
                    assert certify_subset(y,b,a)==(min(opt),max(opt))
                cases+=1
    rng=np.random.default_rng(438020)
    for _ in range(120):
        m=int(rng.integers(1,25));T=int(rng.integers(1,10))
        y=rng.integers(0,2,(m,T));b=int(rng.integers(0,m*T+1))
        Q=exact_offline_certificate(y.sum(axis=1),T,b)[0]
        r=exact_columns(y,b,Q)
        assert r['K_col']==brute_columns(y,b)
        verify_minimality(y,b,r)
    print(json.dumps({'status':'PASS_COLUMN_CERTIFICATE_COMPLETION_ORACLE',
                      'exhaustive_matrix_budget_cases':cases,'random_complete_subset_cases':120}))

if __name__=='__main__':main()

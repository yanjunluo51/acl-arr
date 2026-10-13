"""Changed-path checks: ECDF ties/subsets and full-column query charging."""
import math
import numpy as np
from mapping_column_experiments import cdf, indices, map_scores, solve_columns
from query_selection import aggregate, endpoint_cost, all_flips, fit_prior
from review_accelerated import mapped_panel
from external_experiments import mapped


def slow_capacity(cost, budget):
    total = 0
    for i, value in enumerate(sorted(int(v) for v in cost)):
        total += value
        if total > budget:
            return i
    return len(cost)


def main():
    ref = np.array([1., 1., 2., 4.])
    values = np.array([0., 1., 1.5, 2., 3., 4., 5.])
    assert np.array_equal(cdf(values, ref, 'right'), [0,.5,.5,.75,.75,1,1])
    assert np.array_equal(cdf(values, ref, 'midrank'), [0,.25,.5,.625,.75,.875,1])
    for panel in ['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de']:
        ix, _, _, _ = indices(panel, 0, '1')
        for fraction in ['1/2','1/4']:
            jx, _, _, _ = indices(panel, 0, fraction)
            assert np.array_equal(ix[1],jx[1]) and np.array_equal(ix[2],jx[2])
            assert set(jx[0]) <= set(ix[0])
        rr, tt, *_ = map_scores(panel, 0, '1','right')
        original = mapped(panel,0)[0] if panel.startswith('WMT24') else mapped_panel(panel,0)[0]
        assert np.array_equal(rr,original[0]) and np.array_equal(tt,original[2])
    rng = np.random.default_rng(510031)
    checks = 0
    for agg in ['median','mean']:
        for trial in range(18):
            base = rng.choice([.2,.4,.6,.8],(7,8))
            hidden = rng.choice([.1,.3,.7,.9],(4,8))
            t=.5;sel=aggregate(base,agg)>=t;p=endpoint_cost(base,t,agg)
            prior=rng.random((8,4))*p[:,None];tie=rng.permutation(8)
            budget=int(rng.integers(0,28));eps=1
            full=all_flips(base,hidden,t,agg)
            for method in ['column_fixed','column_random','column_reference']:
                seen=[]
                def query(c):
                    assert c not in seen;seen.append(c);return hidden[c].copy()
                trace,tol,exact=solve_columns(base,sel,p,prior,t,agg,4,budget,tie,method,991,query,eps)
                lo=np.zeros(8,dtype=int);hi=4*p.copy();first_tol=first_exact=None
                for step in range(len(trace)+1):
                    a=slow_capacity(hi[sel],budget);b=slow_capacity(lo[sel],budget)
                    if b-a<=eps and first_tol is None:first_tol=step
                    if b==a and first_exact is None:first_exact=step
                    for st in [tol,exact]:
                        if step==st['columns']:
                            mask=np.array(st['mask'],dtype=bool)
                            assert (a,b,b-a)==(st['V_lower'],st['V_upper'],st['gap'])
                            assert hi[mask].sum()<=budget
                            assert full[:,mask].sum()<=budget
                            assert st['queries']==8*step
                    if step<len(trace):
                        f=full[trace[step]];lo[sel]+=f[sel];hi[sel]-=p[sel]-f[sel]
                assert (first_tol,first_exact)==(tol['columns'],exact['columns'])
                assert seen==trace;checks+=1
    # A structurally invariant selection must not trigger a charged column.
    base=np.ones((7,8));hidden=np.zeros((4,8));sel=np.ones(8,dtype=bool)
    trace,tol,exact=solve_columns(base,sel,np.zeros(8,dtype=int),np.zeros((8,4)),.5,
                                 'median',4,0,np.arange(8),'column_fixed',0,
                                 lambda c: (_ for _ in ()).throw(AssertionError('unneeded query')),0)
    assert not trace and exact['queries']==0
    print({'status':'PASS_CHANGED_PATH_REGRESSIONS','column_cases':checks,
           'cdf_ties':'manual expected values','reference_test_invariance':True,
           'full_reference_reproduces_original_mapping':True})


if __name__=='__main__':main()

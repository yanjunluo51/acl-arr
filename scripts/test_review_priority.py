"""Regression checks for WMT24 numerical priority ties and cost units."""
import numpy as np
from query_selection import aggregate,endpoint_cost
from review_accelerated import solve_multi
from review_priority import solve_multi_quantized


def run(solver,base,hidden,prior,agg,budget,tie):
    threshold=.5
    selected=aggregate(base,agg)>=threshold
    p=endpoint_cost(base,threshold,agg)
    seen=set()
    def query(c,i):
        assert (c,i) not in seen
        seen.add((c,i))
        return float(hidden[c,i])
    return solver(base,selected,p,prior,threshold,agg,len(hidden),
                  np.array([budget],dtype=np.int64),tie,'reference_priority',
                  91827,query,[0,.1,.25,.5,1],1)


def main():
    rng=np.random.default_rng(51927)
    checks=0
    # Binary-quarter priorities are exactly representable. Fixed-point units
    # must preserve the original heuristic, including observed-cost updates.
    for agg in ['median','mean']:
        for _ in range(100):
            base=rng.choice([.2,.4,.6,.8],size=(7,11))
            hidden=rng.choice([.1,.3,.7,.9],size=(4,11))
            p=endpoint_cost(base,.5,agg)
            prior=(rng.integers(0,5,size=(11,4))/4)*p[:,None]
            tie=rng.permutation(11)
            budget=int(rng.integers(0,25))
            assert run(solve_multi,base,hidden,prior,agg,budget,tie)==run(solve_multi_quantized,base,hidden,prior,agg,budget,tie)
            checks+=1
    # Tiny perturbations around clipped zero must not change the candidate
    # order, query trace, first stops or safe masks under the declared ticks.
    base=np.full((7,5),.51)
    hidden=np.array([[.1,.9,.1,.9,.1],[.9,.1,.9,.1,.9],[.1,.1,.9,.9,.1]])
    prior=np.zeros((5,3));tie=np.arange(5)
    expected=run(solve_multi_quantized,base,hidden,prior,'mean',14,tie)
    for magnitude in [1e-16,1e-15,1e-14,1e-13,4e-13]:
        for candidate in range(3):
            noisy=prior.copy();noisy[:,candidate]=magnitude
            assert run(solve_multi_quantized,base,hidden,noisy,'mean',14,tie)==expected
            checks+=1
    print({'status':'PASS_FIXED_POINT_PRIORITY_REGRESSION','checks':checks,
           'scope':'Finite ordering, query/stop/mask and observed-cost-unit regressions; full WMT24 audit remains required.'})


if __name__=='__main__':main()

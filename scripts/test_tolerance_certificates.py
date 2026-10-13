"""Independent enumeration of observation counts, with no formula-based oracle."""
import itertools
import json
from tolerance_certificates import minimum_gap_certificate


def capacity(z,b):
    count=spent=0
    for x in sorted(z):
        if spent+x>b:
            break
        spent+=x
        count+=1
    return count


def main():
    checks=states=0
    for m,T in [(1,1),(2,2),(3,3),(3,4)]:
        for z in itertools.combinations_with_replacement(range(T+1),m):
            choices=[[(a,o) for a in range(T-s+1) for o in range(s+1)] for s in z]
            observations=list(itertools.product(*choices))
            states+=len(observations)
            previous=None
            for b in range(m*T+1):
                best=[m*T]*(m+1)
                for observed in observations:
                    gap=capacity([o for a,o in observed],b)-capacity([T-a for a,o in observed],b)
                    queries=sum(a+o for a,o in observed)
                    for e in range(gap,m+1):
                        best[e]=min(best[e],queries)
                for e in range(m+1):
                    actual=minimum_gap_certificate(z,T,b,e)['queries']
                    assert actual==best[e],(z,T,b,e,actual,best[e])
                    if e:assert actual<=best[e-1]
                    checks+=1
    assert minimum_gap_certificate([],3,0,0)['queries']==0
    assert minimum_gap_certificate([0,1,2],3,2,0)['queries']==7
    assert minimum_gap_certificate([0,1,2],3,2,1)['queries']==4
    print(json.dumps({'status':'PASS_EXHAUSTIVE_SMALL_MEDIAN_GAP_CERTIFICATES',
                      'formula_comparisons':checks,'observation_count_states':states,
                      'empty_boundary_checked':True,'example_exact':7,'example_gap_one':4},indent=2))


if __name__=='__main__':main()

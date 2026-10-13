"""Exact arithmetic checks for common transforms and weighted endpoint bounds."""
import itertools,json,random
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def select(v,t,agg):return (sorted(v)[len(v)//2] if agg=='median' else sum(v)/len(v))>=t
def f(base,x,t,agg):
    old=select(base,t,agg);return sum(select(base[:j]+[x]+base[j+1:],t,agg)!=old for j in range(len(base)))
def main():
    rng=random.Random(5202610);checks=weights=0
    for M in [1,3,7]:
        for _ in range(512):
            base=[F(rng.randrange(11),10) for j in range(M)];xs=[F(rng.randrange(11),10) for r in range(3)];t=F(rng.randrange(1,11),10)
            for agg,h in [('median',lambda x:x**3),('mean',lambda x:x/2+F(1,4))]:
                b=[h(x) for x in base]
                assert select(base,t,agg)==select(b,h(t),agg)
                for x in xs+[F(0),F(1)]:assert f(base,x,t,agg)==f(b,h(x),h(t),agg);checks+=1
            # Arbitrary fixed positive rational scenario weights, all query subsets.
            w=[[F(rng.randrange(1,8)) for r in range(3)] for j in range(M)];total=sum(sum(v) for v in w);w=[[v/total for v in row] for row in w]
            for agg in ['median','mean']:
                old=select(base,t,agg)
                def g(x,r):return sum(w[j][r]*(select(base[:j]+[x]+base[j+1:],t,agg)!=old) for j in range(M))
                cap=[g(F(0) if old else F(1),r) for r in range(3)];true=[g(x,r) for r,x in enumerate(xs)]
                for mask in range(8):
                    lo=sum(true[r] for r in range(3) if (mask>>r)&1);up=lo+sum(cap[r] for r in range(3) if not (mask>>r)&1)
                    assert lo<=sum(true)<=up;weights+=1
    z={'status':'PASS_EXACT_COMMON_TRANSFORM_AND_WEIGHTED_BOUND_CHECKS','common_transform_flip_checks':checks,'weighted_history_checks':weights,'weighted_acquisition_experiment':False}
    (ROOT/'review-revision/joint-certificate-implementation/protocol-check.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps(z,indent=2))
if __name__=='__main__':main()

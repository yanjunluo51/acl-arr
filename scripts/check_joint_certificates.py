"""Independent exhaustive subset oracle for joint/residual integer certificates."""
import itertools,json,random,time,hashlib
from fractions import Fraction
from pathlib import Path
from joint_certificates import minimum_joint_certificate
from tolerance_certificates import minimum_gap_certificate
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/joint-certificates'

def cap(cost,b):
    # Deliberately enumerate all output masks instead of the solver's prefix.
    return max((bin(mask).count('1') for mask in range(1<<len(cost))
                if sum(x for i,x in enumerate(cost) if (mask>>i)&1)<=b),default=0)

def brute(rows,p,b,e,obs):
    m=len(rows);T=len(rows[0]);cells=[(i,r) for i in range(m) for r in range(T) if not (obs[i]>>r)&1]
    for Q in range(len(cells)+1):
        for chosen in itertools.combinations(cells,Q):
            mask=obs.copy()
            for i,r in chosen:mask[i]|=1<<r
            lo=[sum(x for r,x in enumerate(row) if (mask[i]>>r)&1) for i,row in enumerate(rows)]
            up=[lo[i]+(T-bin(mask[i]).count('1'))*p[i] for i in range(m)]
            if cap(lo,b)-cap(up,b)<=e:return Q
    raise AssertionError('Full revelation failed')

def check(rows,p,b,e,obs):
    a=minimum_joint_certificate(rows,p,b,e,obs)
    expected=brute(rows,p,b,e,obs)
    assert a['queries']==expected,(rows,p,b,e,obs,a,expected)
    return a

def main():
    OUT.mkdir(exist_ok=False);start=time.monotonic();count=0;median=0;realized=0
    # Exhaustive two-row, one-entry capped integer grid, including every history.
    for p in itertools.product(range(1,4),repeat=2):
        for vals in itertools.product(*(range(x+1) for x in p)):
            rows=[[x] for x in vals]
            for b in range(sum(p)+1):
                for e in (0,1,2):
                    for obs in itertools.product((0,1),repeat=2):
                        check(rows,p,b,e,list(obs));count+=1
    rng=random.Random(7102026)
    for j in range(1024):
        m=2+j%3;T=1+j%3
        if m*T>12:T=2
        p=[rng.randrange(1,5) for _ in range(m)]
        rows=[[rng.randrange(x+1) for _ in range(T)] for x in p]
        b=rng.randrange(sum(p)*T+1);e=j%3
        obs=[rng.randrange(1<<T) if j%2 else 0 for _ in range(m)]
        check(rows,p,b,e,obs);count+=1
    for m in range(1,5):
        for T in range(1,4):
            for j in range(64):
                bits=[[rng.randrange(2) for _ in range(T)] for _ in range(m)]
                b=rng.randrange(m*T+1);e=j%3;factor=1+j%4
                rows=[[factor*x for x in row] for row in bits]
                a=check(rows,[factor]*m,b*factor,e,[0]*m)
                old=minimum_gap_certificate([sum(v) for v in bits],T,b,e)
                assert a['queries']==old['queries'];median+=1
    # Realizable selected mean rows, exact rational arithmetic, endpoint/ties.
    grid=[Fraction(x,4) for x in range(5)];cut=Fraction(1,2)
    bases=[v for v in itertools.combinations_with_replacement(grid,3) if sum(v)/3>=cut]
    def flips(base,x):
        return sum((sum(base)-base[j]+x)/3<cut for j in range(3))
    for j,(a,b) in enumerate(itertools.product(bases,bases)):
        candidates=[[grid[(j+r)%5] for r in range(2)], [grid[(2*j+r)%5] for r in range(2)]]
        rows=[[flips(base,x) for x in xs] for base,xs in zip((a,b),candidates)]
        p=[flips(a,Fraction(0)),flips(b,Fraction(0))]
        budget=j%(2*sum(p)+1);e=j%2
        check(rows,p,budget,e,[0,0]);realized+=1
    example=minimum_joint_certificate([[1],[1]],[2,2],1,separated=True)
    assert example['queries']==2 and example['split_queries']==3
    receipt={'status':'PASS_INDEPENDENT_EXHAUSTIVE_SUBSET_VALIDATION','capped_integer_cases':count,'median_formula_crosschecks':median,'rational_realizable_mean_cases':realized,'total_cases':count+median+realized,'dual_use_example':example,'elapsed_seconds':time.monotonic()-start,'solver_sha256':hashlib.sha256((ROOT/'scripts/joint_certificates.py').read_bytes()).hexdigest(),'human_proof_certified':False}
    (OUT/'independent-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

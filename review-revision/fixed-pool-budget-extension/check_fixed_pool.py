"""Exact score realization and two independent finite certificate checks.

Constructed theorem instances, never substitutes for NLP experiments.
Uses only the Python standard library. Run from any directory.
"""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import random


def make(M, T, budget, alpha=None):
    assert M >= 3 and T <= budget < (M - 1) * T
    alpha = F(budget, 2*M*T) if alpha is None else F(alpha)
    assert (2*M*T*alpha).__floor__() == budget
    a = [F(1, 2) + F(j, 4*M*M) for j in range(M)]
    b = [F(1, 16*M*M)] + [F(M, 2*(M-1)) + F(j, 4*M*M) for j in range(M-1)]
    def score(base, v):
        cuts = sorted(F(M, 2)-sum(base)+x for x in base if F(M, 2)-sum(base)+x > 0)
        assert len(cuts) >= v and cuts[-1] < 1
        if v == 0:
            return (cuts[-1]+1)/2
        lo = cuts[-v-1] if v < len(cuts) else F(0)
        return (lo+cuts[-v])/2
    low, extra = divmod(budget, T)
    rows = [[low]*(T-extra)+[low+1]*extra, [1]+[0]*(T-1)]
    scores = [[score(base, v) for v in row] for base, row in zip([a,b],rows)]
    def flip(base, x):
        return sum((sum(base)-v+x)/M < F(1,2) for v in base)
    assert all(sum(base)/M > F(1,2) for base in [a,b])
    assert [[flip(base,x) for x in rr] for base,rr in zip([a,b],scores)] == rows
    caps = [flip(base,F(0)) for base in [a,b]]
    assert caps == [M, M-1]
    values = a+b+scores[0]+scores[1]
    margins = [abs(sum(base)/M-F(1,2)) for base in [a,b]]
    for base, rr in zip([a,b],scores):
        for x in rr+[F(0),F(1)]:
            margins.extend(abs((sum(base)-v+x)/M-F(1,2)) for v in base)
    radius = min(margins + values + [1-x for x in values])/2
    assert radius > 0
    # Independently perturb every base/candidate coordinate; this finite check
    # supplements the analytic infinity-norm margin argument.
    rng = random.Random(10000*M+100*T+budget)
    for _ in range(8):
        aa=[[v+F(rng.randrange(-99,100),100)*radius for v in base] for base in [a,b]]
        ss=[[v+F(rng.randrange(-99,100),100)*radius for v in rr] for rr in scores]
        assert [[flip(base,x) for x in rr] for base,rr in zip(aa,ss)] == rows
        assert [flip(base,F(0)) for base in aa] == caps
        assert all(sum(base)/M>F(1,2) for base in aa)
    return dict(M=M,T=T,budget=budget,alpha=str(alpha),rows=rows,caps=caps,
                bases=[[str(x) for x in a],[str(x) for x in b]],
                candidate_scores=[[str(x) for x in r] for r in scores],
                uniform_perturbation_radius=str(radius))


def capacity(costs, b):
    total=0; count=0
    for x in sorted(costs):
        if total+x>b: break
        total+=x; count+=1
    return count


def literal(x):
    T=x['T']; b=x['budget']; safe=[]; exclude=[]; joint=2*T+1
    amin=emin=positive_gap=2*T+1
    for mask in range(1<<(2*T)):
        q=bin(mask).count("1"); lo=[0,0]; up=[0,0]
        for i in range(2):
            for j in range(T):
                if mask>>(i*T+j)&1: lo[i]+=x['rows'][i][j];up[i]+=x['rows'][i][j]
                else: up[i]+=x['caps'][i]
        s=capacity(up,b)>=1; e=capacity(lo,b)<=1
        if capacity(lo,b)-capacity(up,b)<=1: positive_gap=min(positive_gap,q)
        if s and e: joint=min(joint,q)
        if s and q<=amin:
            if q<amin: safe=[];amin=q
            safe.append(mask)
        if e and q<=emin:
            if q<emin: exclude=[];emin=q
            exclude.append(mask)
    union=min(bin(a|b).count("1") for a in safe for b in exclude)
    return dict(joint=joint,safety=amin,exclusion=emin,union=union,split=amin+emin,
                gap_one=positive_gap,subsets=1<<(2*T),safety_ties=len(safe),exclusion_ties=len(exclude))


def outcome_counts(x):
    # Every entry subset maps to a count vector, and any such vector is
    # realizable. Overlap can simultaneously be maximized within each group.
    groups=[]
    for i,row in enumerate(x['rows']):
        for v in sorted(set(row)): groups.append((i,v,row.count(v)))
    states=0; joint=2*x['T']+1;amin=emin=positive_gap=joint; safe=[];exclude=[]
    for counts in product(*(range(n+1) for _,_,n in groups)):
        states+=1;q=sum(counts);lo=[0,0];up=[0,0]
        for (i,v,n),a in zip(groups,counts):
            lo[i]+=a*v;up[i]+=a*v+(n-a)*x['caps'][i]
        s=capacity(up,x['budget'])>=1;e=capacity(lo,x['budget'])<=1
        if capacity(lo,x['budget'])-capacity(up,x['budget'])<=1: positive_gap=min(positive_gap,q)
        if s and e: joint=min(joint,q)
        if s and q<=amin:
            if q<amin: safe=[];amin=q
            safe.append(counts)
        if e and q<=emin:
            if q<emin: exclude=[];emin=q
            exclude.append(counts)
    union=min(sum(max(a,b) for a,b in zip(sa,ex)) for sa in safe for ex in exclude)
    return dict(joint=joint,safety=amin,exclusion=emin,union=union,split=amin+emin,
                gap_one=positive_gap,states=states,safety_count_vectors=len(safe),exclusion_count_vectors=len(exclude))


def check_result(x,result):
    T=x['T'];r,t=divmod(x['budget'],x['M']-1)
    expected=dict(joint=T+1,safety=T-r,exclusion=T+1,union=(2*T+1-r-int(t>0) if r else T+1),split=2*T+1-r,gap_one=T-r)
    assert all(result[k]==v for k,v in expected.items()), (x['M'],T,x['budget'],result,expected)


def main(output):
    records=[]
    for M in range(3,10):
        for T in range(1,7):
            for b in range(T,(M-1)*T):
                x=make(M,T,b); a=literal(x); c=outcome_counts(x)
                check_result(x,a);check_result(x,c)
                x.update(literal=a,outcome_counts=c);records.append(x)
    for T,b in [(6,6),(12,12),(30,42),(60,84),(90,126)]:
        x=make(7,T,b);c=outcome_counts(x);check_result(x,c)
        x['outcome_counts']=c;records.append(x)
    for T in [7,17]:
        x=make(7,T,(F(1,10)*14*T).__floor__(),F(1,10))
        c=outcome_counts(x);check_result(x,c);x['outcome_counts']=c
        if T==7:
            a=literal(x);check_result(x,a);x['literal']=a
        records.append(x)
    result=dict(status='PASS_EXACT_FIXED_POOL_BUDGET_EXTENSION',
                scope='finite validation of an analytic family; no NLP replication or human proof certification',
                cases=len(records),literal_cases=sum('literal' in x for x in records),
                literal_subsets=sum(x.get('literal',{}).get('subsets',0) for x in records),
                outcome_states=sum(x['outcome_counts']['states'] for x in records),
                perturbation_checks=8*len(records),records=records)
    dest=Path(output)
    with dest.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,help='New receipt path; existing files are never overwritten')
    args=parser.parse_args()
    main(args.output)

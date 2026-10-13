"""Rational mean-score realization and independent subset verification.

This is validation of a theorem construction, not an NLP benchmark.
"""
import json
from fractions import Fraction as F
from pathlib import Path
from variable_target_certificate import certificate
from deduplicated_certificates import union_certificate

def realization(T):
    assert T>=2 and T%2==0
    M=T+1
    a=[F(1,2)+F(j,4*M*M) for j in range(M)]
    b=[F(0)]+[F(M,2*(M-1))+F(j,4*M*M) for j in range(M-1)]
    def cuts(base):return sorted(F(M,2)-sum(base)+v for v in base)
    ca,cb=cuts(a),cuts(b)
    xa,xb=(ca[-1]+ca[-2])/2,(cb[-1]+cb[-2])/2
    candidates=[[xa]*T,[xb]+[F(1)]*(T-1)]
    def flips(base,x):
        assert sum(base)/M>=F(1,2)
        return sum((sum(base)-v+x)/M<F(1,2) for v in base)
    rows=[[flips(base,x) for x in row] for base,row in zip([a,b],candidates)]
    caps=[flips(base,F(0)) for base in [a,b]]
    assert rows==[[1]*T,[1]+[0]*(T-1)] and caps==[T+1,T]
    return dict(T=T,M=M,bases=[[str(v) for v in a],[str(v) for v in b]],
                candidate_scores=[[str(v) for v in r] for r in candidates],rows=rows,caps=caps,budget=T)

def exhaustive(x):
    T=x['T'];rows=x['rows'];caps=x['caps'];states=[]
    def cap(v):return 2 if sum(v)<=T else int(min(v)<=T)
    for q in range(1<<(2*T)):
        lo=[sum(v for r,v in enumerate(row) if q>>(i*T+r)&1) for i,row in enumerate(rows)]
        up=[lo[i]+(T-bin(q>>(i*T)&((1<<T)-1)).count('1'))*p for i,p in enumerate(caps)]
        states.append((q,bin(q).count('1'),cap(up),cap(lo)))
    joint=min(q for mask,q,vl,vu in states if vl==vu)
    am=min(q for mask,q,vl,vu in states if vl>=1)
    bm=min(q for mask,q,vl,vu in states if vu<=1)
    aa=[mask for mask,q,vl,vu in states if q==am and vl>=1]
    bb=[mask for mask,q,vl,vu in states if q==bm and vu<=1]
    union=min(bin(a|b).count('1') for a in aa for b in bb)
    assert (joint,am,bm,union)==(T+1,T-1,T+1,2*T)
    return dict(subsets=len(states),joint=joint,safety=am,exclusion=bm,union=union)

def main(output=None):
    records=[]
    for T in [2,4,6,8,10,12,20]:
        x=realization(T)
        v=certificate(x['rows'],x['caps'],T)
        u=union_certificate(x['rows'],x['caps'],T)
        x['primary_union_attempt']=u
        if u['status']!='OPTIMAL':
            u=union_certificate(x['rows'],x['caps'],T,presolve=False)
            x['presolve_off_retry']=u
        assert v['joint_optimal'] and v['queries']==T+1
        assert u['status']=='OPTIMAL' and u['union_minimum']==u['split_minimum']==2*T
        if T<=8:x['independent_subsets']=exhaustive(x)
        records.append(x)
    result=dict(status='PASS_RATIONAL_REALIZATION_AND_STRICT_SEPARATION_CHECK',
                claim='Qjoint=T+1, best separately optimal union=2T; T even>=2',
                rational_families=7,exhaustive_cases=4,maximum_exhaustive_entries=16,
                construction_not_empirical_NLP_evidence=True,records=records)
    if output is not None:
        with Path(output).open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(result['status'])

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,help='New receipt path; existing files are never overwritten')
 a=p.parse_args()
 if a.output is not None and a.output.exists():p.error('--output must name a new file')
 main(a.output)

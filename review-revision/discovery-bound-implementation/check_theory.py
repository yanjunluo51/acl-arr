from pathlib import Path
from fractions import Fraction as F
import json,itertools
import numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1];P=R/'review-revision/granularity-risk-implementation'
# Same right-ECDF and reference order-statistic rule, with fixed reference data.
refraw=np.array([((np.arange(20)+3*j)%20)+1 for j in range(14)])
ref=np.array([np.searchsorted(np.sort(a),a,side='right')/20 for a in refraw])
cutoff=float(np.max(np.sort(ref[:7],axis=0)[3]));assert cutoff==.6
records=[];positions=0
for h in range(3):
 k=20*h+17;N=20*k;m=7*h+6;T=M=7;bH=(2*k*7*7)//10;b=bH//4;K=m*T
 assert b==K-1 and bH==196*h+166
 base=np.zeros((7,N));base[:4,:m]=.75;base[4:,:m]=.25;base[:,m:k]=.75;base[:,k:]=.25
 selected=np.median(base,axis=0)>=cutoff;assert selected.sum()==k
 for pos in range(K):
  cand=np.full((T,N),.25);cand[pos%T,pos//T]=.75
  counts=np.zeros((T,N),int)
  for r in range(T):
   for j in range(M):
    changed=base.copy();changed[j]=cand[r]
    counts[r]+=(np.median(changed,axis=0)>=cutoff)!=selected
  assert counts[:,:m].sum()==4*(K-1) and np.count_nonzero(counts[:,:m]==0)==1
  assert not counts[:,m:].any();assert counts.sum()<=bH<4*K
  # No observations: upper capacity k-1, optimistic k. Agreement: both k.
  assert (b//T)+(k-m)==k-1
  assert 4*K-4<=bH
  positions+=1
 records.append(dict(h=h,k=k,N=N,m=m,T=T,bH=bH,b=b,active_entries=K,offline_exact=1,deterministic_worst=K,randomized_lower=str(F(K+1,2)),initial_gap=1,primary_epsilon=(k+49)//50,primary_queries=0))
# Exact arithmetic checks of all formulas, including large indices.
for h in list(range(1001))+[10**6,10**12]:
 k=20*h+17;m=7*h+6;K=7*m;bH=(2*k*49)//10
 assert bH//4==K-1 and 4*(K-1)<=bH<4*K
 assert F(K*(K+1)//2,K)==F(K+1,2)
# Check exact full-column iff criterion against saved minima on every layout.
import sys
sys.path.insert(0,str(P));from run_layout import transformed
raw={}
for x in map(json.loads,(R/'outputs/full-mean-grid-20261005/records.jsonl').open()):raw[x['dataset'],x['split'],x['q']]=x

def cap(a,b):
 total=0;n=0
 for v in sorted(map(int,a)):
  if total+v>b:break
  total+=v;n+=1
 return n
out=[]
for a in map(json.loads,(P/'layout-records.jsonl').open()):
 x=raw[a['dataset'],a['split'],a['q']];f=transformed(np.array(x['rows'],int),a['layout']);p=np.array(x['caps']);full=f.sum(1);b=x['budget']
 delta=[cap(full-f[:,r],b)-cap(full+p-f[:,r],b) for r in range(f.shape[1])]
 gamma=cap(full-f.min(1),b)-cap(full+p-f.max(1),b)
 assert gamma<=min(delta)
 assert (min(delta)>a['epsilon'])==(a['joint']==a['T'])
 out.append(dict(dataset=a['dataset'],split=a['split'],q=a['q'],layout=a['layout'],stopping=a['stopping'],gamma=gamma,min_omission_gap=min(delta),epsilon=a['epsilon'],full_columns=a['joint']==a['T']))
(D/'column-necessity-check.json').write_text(json.dumps(out,indent=2))
result=dict(status='PASS_SCOPED_CONSTRUCTED_SCORE_AND_COLUMN_CHECKS',fixed_parameters={'M':7,'T':7,'q':'1/20','alpha':'1/10','cutoff':'3/5'},reference_outputs=20,reference_right_ecdf_realization=True,explicit_score_agreement_positions=positions,integer_formula_indices=1003,instances=records,column_targets=len(out),column_full=sum(x['full_columns'] for x in out),randomized_claim='Analytic averaging over all agreement locations; finite checks do not replace proof',positive_tolerance_bound=False,new_nlp_evidence=False)
(D/'theory-check.json').write_text(json.dumps(result,indent=2));print(result)

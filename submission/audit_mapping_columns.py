"""Separate arithmetic replay of mapping and whole-column certificates.

No acquisition solver imports. Same assistant, not human proof certification.
"""
from pathlib import Path
from fractions import Fraction
from functools import lru_cache
import argparse, gzip, hashlib, json, math, multiprocessing, random, time
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/mapping-column'


@lru_cache(maxsize=3)
def load_panel(panel):
    file = ('rb2_ranked_panel.json' if panel == 'RewardBench2' else
            'wmt23_metric_panel.json' if panel.startswith('WMT23') else
            'wmt24_'+panel.split('-',1)[1]+'_panel.json')
    z=json.loads((ROOT/'data'/file).read_text())
    cols=[i for i,s in enumerate(z.get('systems',[0,1,2,3]))
          if panel!='WMT23_without_synthetic_ref' or s!='synthetic_ref']
    a=np.array([[np.asarray(z['scores'][m][i])[cols] for i in z['prompt_ids']]
                for m in z['models']],dtype=float).reshape(len(z['models']),-1)
    return z,a,len(cols)


@lru_cache(maxsize=4)
def context(panel,rep,fraction,mode):
    z,a,g=load_panel(panel)
    external=panel.startswith('WMT24')
    seed=924000 if external else 20260815 if panel=='RewardBench2' else 87000
    units=list(dict.fromkeys(z['source_document_ids'])) if external else list(range(len(z['prompt_ids'])))
    random.Random(seed+rep).shuffle(units);n=len(units)//3
    parts=[units[:max(1,int(Fraction(fraction)*n))],units[2*n:]]
    if external:
        ix=[np.array([i*g+j for i,d in enumerate(z['source_document_ids'])
                      if d in set(part) for j in range(g)]) for part in parts]
    else:
        ix=[np.array([i*g+j for i in part for j in range(g)]) for part in parts]
    rr,tt=ix;ref=[];test=[]
    for row in a:
        sr=np.sort(row[rr])
        def transform(v):
            upper=np.searchsorted(sr,v,side='right')
            if mode=='right':return upper/len(sr)
            lower=np.searchsorted(sr,v,side='left')
            return (lower+upper)/(2*len(sr))
        ref.append(transform(row[rr]));test.append(transform(row[tt]))
    return np.array(ref),np.array(test),seed


def consensus(a,agg):
    if agg=='median':return np.sort(a,axis=0)[len(a)//2]
    out=np.zeros(a.shape[1])
    for j in range(len(a)):out+=a[j]
    return out/len(a)


def geometry(base,other,t,agg):
    selected=consensus(base,agg)>=t
    f=np.zeros(other.shape,dtype=np.int64)
    for c in range(len(other)):
        for j in range(len(base)):
            v=base.copy();v[j]=other[c]
            f[c]+=(consensus(v,agg)>=t)!=selected
    ends=np.where(selected,0.,1.)
    p=np.zeros(base.shape[1],dtype=np.int64)
    for j in range(len(base)):
        v=base.copy();v[j]=ends
        p+=(consensus(v,agg)>=t)!=selected
    return selected,p,f


def cap(values,b):
    return int(np.count_nonzero(np.cumsum(np.sort(values),dtype=np.int64)<=b))


@njit(cache=True,fastmath=False)
def hist_capacity(hist,b):
    consumed=0;count=hist[0]
    for value in range(1,len(hist)):
        limit=consumed+value*hist[value]
        if limit>b:
            return count+(b-consumed)//value
        consumed=limit;count+=hist[value]
    return count


@njit(cache=True,fastmath=False)
def first_entry_stops(items,answers,p,T,b,eps):
    lo=np.zeros(len(p),dtype=np.int64);hi=T*p.copy()
    lh=np.zeros(T*7+1,dtype=np.int64);uh=lh.copy()
    for i in range(len(p)):lh[0]+=1;uh[hi[i]]+=1
    ft=-1;fe=-1
    for step in range(len(items)+1):
        gap=hist_capacity(lh,b)-hist_capacity(uh,b)
        if gap<=eps and ft<0:ft=step
        if gap==0 and fe<0:fe=step
        if step==len(items):break
        i=items[step];v=answers[step]
        lh[lo[i]]-=1;uh[hi[i]]-=1
        lo[i]+=v;hi[i]-=p[i]-v
        lh[lo[i]]+=1;uh[hi[i]]+=1
    return ft,fe


def reference_column_order(ref,test,threshold,agg,p,selected):
    sr,pr,fr=geometry(ref[:7],ref[7:],threshold,agg)
    def design(base,endpoint):
        return np.column_stack((np.ones(base.shape[1]),base.T,
                consensus(base,agg)-threshold,np.ptp(base,axis=0),endpoint/7))
    x=design(ref[:7],pr);xt=design(test[:7],p)
    penalty=np.eye(x.shape[1]);penalty[0,0]=0
    coefficient=np.linalg.solve(np.einsum('ni,nj->ij',x,x,optimize=False)+penalty,
                                np.einsum('ni,nj->ij',x,fr.T,optimize=False))
    pred=np.clip(np.einsum('ni,ij->nj',xt,coefficient,optimize=False),0,p[:,None])
    active=selected & (p>0)
    ticks=np.rint(pred[active]*10**12).astype(np.int64)
    benefit=np.sum(p[active,None]*10**12-ticks,axis=0)
    return np.lexsort((np.arange(len(ref)-7),-benefit))


def audit(z):
    panel,rep,fraction,mode,agg,q=z['key']
    ref,test,seed=context(panel,rep,fraction,mode)
    base,hidden=test[:7],test[7:];T,N=hidden.shape
    threshold=float(np.sort(consensus(ref[:7],agg))[-max(1,round(q*ref.shape[1]))])
    assert threshold==z['geometry']['threshold']
    sel,p,f=geometry(base,hidden,threshold,agg);cost=f.sum(axis=0)
    k=max(1,round(q*N));b=2*k*7*T//10;eps=math.ceil(.02*sel.sum())
    V=cap(cost[sel],b);g=z['geometry'];ids=np.flatnonzero(sel & (p>0))
    assert g['reference_entries']==ref.shape[1] and g['n_test_items']==N
    assert g['selected_count']==sel.sum() and g['active_selected_items']==len(ids)
    assert g['zero_retained']==cap((T*p)[sel],b) and g['V_star']==V
    rows={(r['method'],r['stopping']):r for r in z['records']}
    paths=answers=stops=columns=0
    for path in z['paths']:
        method=path['method'];column=method.startswith('column_')
        trace=path['trace'];paths+=1
        if column:
            assert len(set(trace))==len(trace) and all(0<=c<T for c in trace)
            order=(np.arange(T) if method=='column_fixed' else
                   np.random.default_rng(seed+rep+99173+571921).permutation(T) if method=='column_random' else
                   reference_column_order(ref,test,threshold,agg,p,sel))
            assert trace==order[:len(trace)].tolist()
            lo=np.zeros(len(ids),dtype=np.int64);hi=T*p[ids].copy();first_tol=first_exact=None
            for step in range(len(trace)+1):
                gap=cap(lo,b)-cap(hi,b)
                if first_tol is None and gap<=eps:first_tol=step
                if first_exact is None and gap==0:first_exact=step
                if step<len(trace):
                    lo+=f[trace[step],ids];hi-=p[ids]-f[trace[step],ids]
            assert first_tol==path['two_percent_stop']['columns']
            assert first_exact==path['exact_stop']['columns']==len(trace)
            columns+=len(trace)
        else:
            t=np.array(trace,dtype=np.int64).reshape(-1,3)
            assert len(np.unique(t[:,0]*N+t[:,1]))==len(t)
            assert np.all((0<=t[:,0]) & (t[:,0]<T))
            assert np.all(sel[t[:,1]] & (p[t[:,1]]>0))
            assert np.array_equal(t[:,2],f[t[:,0],t[:,1]])
            inv=np.zeros(N,dtype=np.int64);inv[ids]=np.arange(len(ids))
            ft,fe=first_entry_stops(inv[t[:,1]],t[:,2],p[ids],T,b,eps)
            assert ft==path['two_percent_stop']['queries']
            assert fe==path['exact_stop']['queries']==len(trace)
            answers+=len(t)
        for stopping,st in [('two_percent_gap',path['two_percent_stop']),('exact_gap',path['exact_stop'])]:
            row=rows[(method,stopping)];n=st['queries']
            lo=np.zeros(N,dtype=np.int64);hi=T*p.copy()
            if column:
                assert n==st['columns']*N
                revealed=trace[:st['columns']]
                assert row['candidate_columns_touched']==st['columns']
                assert row['active_fraction'] is None
                assert row['relevant_active_entries_revealed']==st['columns']*len(ids)
                if revealed:
                    lo[ids]=f[revealed][:,ids].sum(axis=0)
                    hi[ids]-=len(revealed)*p[ids]-lo[ids]
                assert not any(field in row for field in ['offline_exact_certificate','offline_exact_safe_part','offline_exact_exclusion_part'])
            else:
                t=np.array(trace[:n],dtype=np.int64).reshape(-1,3)
                np.add.at(lo,t[:,1],t[:,2]);np.add.at(hi,t[:,1],t[:,2]-p[t[:,1]])
                assert row['candidate_columns_touched']==len(np.unique(t[:,0]))
                assert row['active_fraction']==(n/(len(ids)*T) if len(ids) else 0)
            mask=np.array(st['mask'],dtype=bool)
            vlo=cap(hi[sel],b);vhi=cap(lo[sel],b)
            assert (vlo,vhi,vhi-vlo)==(st['V_lower'],st['V_upper'],st['gap'])
            assert vlo<=V<=vhi and int((mask & sel).sum())==vlo
            assert hi[mask].sum()<=b and cost[mask].sum()<=b
            assert not np.any(mask & ~sel & (p>0))
            assert st['upper_selected_cost']==hi[mask & sel].sum()
            assert row['queries']==n and row['V_star']==V
            assert row['V_lower']==vlo and row['V_upper']==vhi
            assert row['returned_count']==vlo and row['selected_count']==int(sel.sum())
            assert row['selected_coverage']==(vlo/int(sel.sum()) if sel.any() else None)
            assert row['selected_over_k']==int(sel.sum())/k
            assert row['certificate_gap']==vhi-vlo
            assert row['realized_regret']==V-vlo and V-vlo<=row['epsilon']
            assert row['panel_fraction']==n/(N*T)
            setup=(7+T)*ref.shape[1]+7*N
            assert row['setup_entries']==setup and row['total_entries']==setup+n
            assert abs(row['risk']-cost[mask].sum()/(2*k*7*T))<1e-12
            if agg=='median' and not column:
                zz=np.sort(cost[sel & (p>0)]//4);bb=b//4;L=cap(zz,bb)
                S=max(0,L*T-bb);E=0
                if L<len(zz):
                    level=next(v for v in range(T+1) if np.minimum(zz[:L+1],v).sum()>=bb+1)
                    E=bb+1+(len(zz)-L-1)*level
                assert (row['offline_exact_certificate'],row['offline_exact_safe_part'],row['offline_exact_exclusion_part'])==(S+E,S,E)
                if stopping=='exact_gap':assert n>=S+E
            stops+=1
    return len(z['paths']),answers,stops,columns


def main(workers):
    start=time.monotonic();execution=json.loads((OUT/'execution.json').read_text())
    assert execution['status']=='PASS_FULL_EXECUTION_PENDING_SEPARATE_ARITHMETIC_AUDIT'
    protocol=json.loads((OUT/'protocol.json').read_text())
    for p,h in {**protocol['source_bindings'],**protocol['solver_bindings']}.items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    totals=np.zeros(4,dtype=np.int64);cases=0
    def items():
        with gzip.open(OUT/'traces.jsonl.gz','rt') as log:
            for line in log:yield json.loads(line)
    with multiprocessing.get_context('spawn').Pool(workers) as pool:
        for value in pool.imap(audit,items(),chunksize=2):
            totals+=value;cases+=1
            if cases%960==0:print('audited',cases,'seconds',round(time.monotonic()-start,1),flush=True)
    assert cases==11520 and int(totals[0])==51840 and int(totals[2])==103680
    data=json.loads((OUT/'results.json').read_text())
    records=data['records'];assert len(records)==103680
    old=[]
    for file in ['query_metrics.json','review-external/results.json']:
        old.extend(json.loads((ROOT/'outputs'/file).read_text())['query_records'])
    lookup={(r['dataset'],r['split'],r['aggregator'],r['q'],r['method'],r['stopping']):r for r in old}
    baseline_matches=0
    for r in records:
        if r['reference_fraction']=='1' and r['cdf']=='right' and not r['method'].startswith('column_'):
            key=(r['dataset'],r['split'],r['aggregator'],r['q'],r['method'],r['stopping']);o=lookup[key]
            for field in ['queries','V_star','V_lower','V_upper','certificate_gap','realized_regret','returned_count','selected_count']:
                assert r[field]==o[field],(key,field,r[field],o[field])
            baseline_matches+=1
    assert baseline_matches==15360
    result={'status':'PASS_SEPARATE_ARITHMETIC_REPLAY_AND_BASELINE_FIDELITY',
            'cases':cases,'paths':int(totals[0]),'entry_answers':int(totals[1]),
            'stop_states':int(totals[2]),'columns':int(totals[3]),
            'baseline_records_identical':baseline_matches,'runtime_seconds':time.monotonic()-start,
            'scope':'Same assistant, separate code without acquisition imports; not human review or actual model execution',
            'bindings':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['outputs/mapping-column/results.json','outputs/mapping-column/traces.jsonl.gz','scripts/mapping_column_experiments.py','submission/audit_mapping_columns.py']}}
    (ROOT/'review-revision/mapping-column/arithmetic-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4)
    main(p.parse_args().workers)

"""Independent panel arithmetic and trace audit; no acquisition-code imports."""
from pathlib import Path
import gzip,hashlib,json,math,random
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def capacity(w,b):
    s=0;n=0
    for v in sorted(map(int,w)):
        if s+v>b:break
        s+=v;n+=1
    return n


def consensus(a,agg):
    if agg=='median':return np.median(a,axis=0)
    s=np.zeros(a.shape[1])
    for row in a:s=s+row
    return s/a.shape[0]


def context(panel,agg,rep,q,cache):
    if panel not in cache:
        f='rb2_ranked_panel.json' if panel=='RewardBench2' else 'wmt23_metric_panel.json'
        z=json.loads((ROOT/'data'/f).read_text());names=z['models'];ids=z['prompt_ids']
        cols=[j for j,s in enumerate(z.get('systems',[0,1,2,3])) if panel!='WMT23_without_synthetic_ref' or s!='synthetic_ref']
        a=np.array([[np.array(z['scores'][m][i])[cols] for i in ids] for m in names],dtype=float).reshape(len(names),-1)
        cache[panel]=(z,a,len(cols))
    z,raw,g=cache[panel];order=list(range(len(z['prompt_ids'])));seed=20260815 if panel=='RewardBench2' else 87000
    random.Random(seed+rep).shuffle(order);third=len(order)//3
    ir=np.array([i*g+j for i in order[:third] for j in range(g)])
    it=np.array([i*g+j for i in order[2*third:] for j in range(g)])
    # Reference-only maps are reconstructed independently.
    rr=np.array([np.searchsorted(np.sort(row[ir]),row[ir],side='right')/len(ir) for row in raw])
    tt=np.array([np.searchsorted(np.sort(row[ir]),row[it],side='right')/len(ir) for row in raw])
    base=tt[:7];cand=tt[7:];T=len(cand);N=len(it);H=7*T;k=max(1,round(q*N));b=(2*k*H)//10
    t=np.sort(consensus(rr[:7],agg))[-max(1,round(q*len(ir)))];sel=consensus(base,agg)>=t
    if agg=='median':
        votes=(base>=t).sum(axis=0);boundary=(votes==3)|(votes==4)
        p=np.where(boundary,4,0)
        flips=4*boundary[None,:]*np.where(sel[None,:],cand<t,cand>=t)
    else:
        flips=np.zeros((T,N),dtype=int);p=np.zeros(N,dtype=int)
        for j in range(7):
            v=base.copy();v[j]=np.where(sel,0,1)
            p+=(consensus(v,agg)>=t)!=sel
            for c in range(T):
                v=base.copy();v[j]=cand[c]
                flips[c]+=(consensus(v,agg)>=t)!=sel
    F=flips.sum(axis=0);assert np.all(flips<=p)
    return dict(p=p,F=F,flips=flips,selected=sel,T=T,N=N,H=H,k=k,b=b,V=capacity(F[sel],b))


def main():
    x=json.loads((ROOT/'outputs/query_metrics.json').read_text());protocol=x['protocol']
    cfg={(p,a,r,q) for p in protocol['panels'] for a in protocol['aggregators'] for r in range(protocol['splits']) for q in protocol['quantiles']}
    expected={c+(m,) for c in cfg for m in protocol['acquisition_methods']}
    assert len(cfg)==960 and len(expected)==3840
    assert len(x['query_records'])==7680 and len(x['baseline_records'])==5760
    assert {(r['dataset'],r['aggregator'],r['split'],r['q'],r['method']) for r in x['query_records']}==expected
    assert len({(r['dataset'],r['aggregator'],r['split'],r['q'],r['method'],r['stopping']) for r in x['query_records']})==7680
    keys=set();cache={};last=None;c=None;queries=0;states_checked=0;crc_violations=0
    with gzip.open(ROOT/'outputs/query_traces.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line);key=tuple(z['key']);assert key in expected and key not in keys;keys.add(key)
            if key[:4]!=last:c=context(*key[:4],cache);last=key[:4]
            N=c['N'];p=c['p'];sel=c['selected'];lo=np.zeros(N,dtype=int);hi=c['T']*p.copy();observed=set()
            saved={}
            for st in z['states']+[z['two_percent_stop'],z['exact_stop']]:saved.setdefault(st['queries'],[]).append(st)
            for index in range(len(z['trace'])+1):
                for st in saved.get(index,[]):
                    mask=np.array(st['mask'],dtype=bool)
                    assert mask.shape==(N,)
                    assert np.sum(hi[mask])<=c['b'] and np.sum(c['F'][mask])<=c['b']
                    assert st['upper_selected_cost']==np.sum(hi[mask & sel])
                    Vlo=capacity(hi[sel],c['b']);Vhi=capacity(lo[sel],c['b'])
                    assert Vlo==st['V_lower'] and Vhi==st['V_upper'] and st['gap']==Vhi-Vlo
                    assert Vlo<=c['V']<=Vhi and np.sum(mask & sel)==Vlo
                    assert np.all(~(mask & ~sel & (p>0)))
                    states_checked+=1
                if index==len(z['trace']):break
                candidate,item,flip=z['trace'][index]
                assert sel[item] and p[item]>0 and (candidate,item) not in observed
                observed.add((candidate,item));assert flip==c['flips'][candidate,item]
                lo[item]+=flip;hi[item]-=p[item]-flip
                assert lo[item]<=c['F'][item]<=hi[item]
                queries+=1
            assert z['two_percent_stop']['gap']<=math.ceil(.02*np.sum(sel))
            assert z['exact_stop']['gap']==0 and z['exact_stop']['V_lower']==c['V']
    assert keys==expected
    for r in x['baseline_records']:
        if r['method']!='envelope_crc':assert r['risk']<=.1+1e-12
        else:crc_violations+=r['risk']>.1+1e-12
    for r in x['query_records']:
        assert r['risk']<=.1+1e-12 and r['realized_regret']<=r['epsilon']
        assert r['queries']<=r['active_entries']
        assert r['active_fraction']==(r['queries']/r['active_entries'] if r['active_entries'] else 0)
        assert r['panel_fraction']==r['queries']/(r['n_test_items']*r['T'])
        if r['aggregator']=='median' and r['stopping']=='exact_gap':assert r['queries']>=r['offline_exact_certificate']
    report={'status':'PASS_SCOPED_INDEPENDENT_ARITHMETIC_AND_COVERAGE','configurations':len(cfg),'query_paths':len(keys),'replayed_query_answers':queries,'saved_states':states_checked,'baseline_records':5760,'query_records':7680,'crc_over_budget_batch_records':crc_violations,'mask_budgets_and_retention_gaps':'PASS','median_closed_form_checked_by':'scripts/test_query_selection.py exhaustive complete certificates','scope':'Different arithmetic implementation by the same assistant; not human proof certification or completeness of literature search.'}
    (ROOT/'submission/query-results-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()

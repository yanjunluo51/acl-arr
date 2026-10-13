"""Independent score-matrix arithmetic, first-stop and full-grid audit.

No acquisition, optimization-runner, or query_selection imports. This is a
separate implementation by the same assistant, not independent human review.
"""
from pathlib import Path
from fractions import Fraction
from functools import lru_cache
import argparse,gzip,hashlib,json,math,random,time
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parents[1]


def capacity(cost,b):
    sums=np.cumsum(np.sort(np.asarray(cost,dtype=np.int64)))
    return int(np.searchsorted(sums,b,side='right'))


def aggregate(a,agg):
    if agg=='median':return np.median(a,axis=0)
    s=np.zeros(a.shape[1])
    for row in a:s=s+row
    return s/len(a)


def topk(a,k):
    z=np.zeros(len(a),dtype=bool);z[np.lexsort((np.arange(len(a)),a))[-k:]]=True
    return z

@lru_cache(maxsize=4)
def raw(panel):
    z=json.loads((ROOT/'data'/('rb2_ranked_panel.json' if panel=='RewardBench2' else 'wmt23_metric_panel.json')).read_text())
    cols=[j for j,s in enumerate(z.get('systems',[0,1,2,3])) if panel!='WMT23_without_synthetic_ref' or s!='synthetic_ref']
    a=np.array([[np.array(z['scores'][m][i])[cols] for i in z['prompt_ids']] for m in z['models']],dtype=float).reshape(len(z['models']),-1)
    return z,a,len(cols)

@lru_cache(maxsize=8)
def mapped(panel,rep):
    z,a,g=raw(panel);order=list(range(len(z['prompt_ids'])));seed=20260815 if panel=='RewardBench2' else 87000
    random.Random(seed+rep).shuffle(order);third=len(order)//3
    ref=np.array([i*g+j for i in order[:third] for j in range(g)])
    test=np.array([i*g+j for i in order[2*third:] for j in range(g)])
    rr=np.array([np.searchsorted(np.sort(row[ref]),row[ref],side='right')/len(ref) for row in a])
    tt=np.array([np.searchsorted(np.sort(row[ref]),row[test],side='right')/len(ref) for row in a])
    return rr,tt,seed,g


@lru_cache(maxsize=4)
def external_mapped(panel,rep):
    lp=panel[6:];z=json.loads((ROOT/'data'/f'wmt24_{lp}_panel.json').read_text());g=len(z['systems'])
    a=np.array([[z['scores'][m][i] for i in z['prompt_ids']] for m in z['models']],dtype=float).reshape(len(z['models']),-1)
    docnames=list(dict.fromkeys(z['source_document_ids']));random.Random(924000+rep).shuffle(docnames);third=len(docnames)//3
    reference=set(docnames[:third]);test=set(docnames[2*third:]);assert reference.isdisjoint(test)
    ir=np.array([i*g+j for i,d in enumerate(z['source_document_ids']) if d in reference for j in range(g)])
    it=np.array([i*g+j for i,d in enumerate(z['source_document_ids']) if d in test for j in range(g)])
    rr=np.array([np.searchsorted(np.sort(row[ir]),row[ir],side='right')/len(ir) for row in a])
    tt=np.array([np.searchsorted(np.sort(row[ir]),row[it],side='right')/len(ir) for row in a])
    goldraw=json.loads((ROOT/'data'/f'wmt24_{lp}_mqm.json').read_text());assert goldraw['systems']==z['systems'] and goldraw['prompt_ids']==z['prompt_ids']
    gold=np.array([goldraw['mqm'][i] for i in z['prompt_ids']],dtype=float).ravel()[it]
    return rr,tt,924000,g,gold


def context(panel,pool,rep,agg,q):
    if panel.startswith('WMT24-'):rr,tt,seed,g,gold=external_mapped(panel,rep)
    else:rr,tt,seed,g=mapped(panel,rep);gold=None
    P=pool['indices'];R=[i for i in range(len(tt)) if i not in P];base=tt[P];cand=tt[R]
    M=len(P);T=len(R);N=tt.shape[1];H=M*T;k=max(1,round(q*N));t=np.sort(aggregate(rr[P],agg))[-max(1,round(q*rr.shape[1]))]
    score=aggregate(base,agg);sel=score>=t;fixed=topk(score,k);p=np.zeros(N,dtype=int)
    bits=np.empty((M,T,N),dtype=bool);fixedbits=np.empty_like(bits)
    for j in range(M):
        v=base.copy();v[j]=np.where(sel,0.,1.);p+=(aggregate(v,agg)>=t)!=sel
        for r in range(T):
            v=base.copy();v[j]=cand[r];a=aggregate(v,agg)
            bits[j,r]=(a>=t)!=sel;fixedbits[j,r]=topk(a,k)!=fixed
    f=bits.sum(axis=0);F=f.sum(axis=0);assert np.all(f<=p)
    tie=np.random.default_rng(seed+rep+700001).permutation(N)
    return dict(gold=gold,N=N,M=M,T=T,H=H,k=k,p=p,F=F,f=f,sel=sel,score=score,tie=tie,bits=bits,fixed=fixed,fixedbits=fixedbits,fixedF=fixedbits.sum(axis=(0,1)))

@njit(cache=True,fastmath=False)
def first_stops(trace,p,selected,T,budgets,epsilon):
    n=len(p);size=T*np.max(p)+1;lo=np.zeros(n,dtype=np.int64);hi=T*p.copy();lh=np.zeros(size,dtype=np.int64);uh=lh.copy()
    for i in range(n):
        if selected[i]:lh[0]+=1;uh[hi[i]]+=1
    tol=np.full(len(budgets),-1,dtype=np.int64);exact=tol.copy()
    for step in range(len(trace)+1):
        for a in range(len(budgets)):
            if exact[a]>=0:continue
            lc=0;uc=0;ls=0;us=0
            for cost in range(size):
                if cost==0:lc=lh[0];uc=uh[0]
                else:
                    lt=min(lh[cost],max(0,(budgets[a]-ls)//cost));ut=min(uh[cost],max(0,(budgets[a]-us)//cost))
                    lc+=lt;uc+=ut;ls+=lt*cost;us+=ut*cost
            gap=lc-uc
            if tol[a]<0 and gap<=epsilon:tol[a]=step
            if gap==0:exact[a]=step
        if step==len(trace):break
        candidate,item,flip=trace[step];lh[lo[item]]-=1;uh[hi[item]]-=1
        lo[item]+=flip;hi[item]-=p[item]-flip;lh[lo[item]]+=1;uh[hi[item]]+=1
    return tol,exact


def validate_metrics(r,mask,c,fixed=False):
    bits=c['fixedbits'] if fixed else c['bits'];sel=c['fixed'] if fixed else c['sel'];F=c['fixedF'] if fixed else c['F']
    ret=mask & sel;n=int(ret.sum());chosen=c['panel']=='RewardBench2'
    risk=int(F[mask].sum())/(2*c['k']*c['H']);pair=bits[:,:,mask].sum(axis=2)/(2*c['k'])
    values={'risk':risk,'coverage':float(mask.mean()),'selected_coverage':n/int(sel.sum()) if sel.any() else None,'returned_count':n,'selected_count':int(sel.sum()),'selected_review_count':int((sel & ~mask).sum()),'nonselected_review_count':int((~sel & ~mask).sum()),'selected_risk':int(F[ret].sum())/(2*c['k']*c['H']),'nonselected_risk':int(F[mask & ~sel].sum())/(2*c['k']*c['H']),'returned_over_k':n/c['k'],'replacement_max_risk':float(pair.max()),'replacement_over_alpha_fraction':float(np.mean(pair>r['alpha']+1e-12))}
    labels=np.tile([1,0,0,0],c['N']//4) if chosen else None
    values['precision']=float(labels[ret].mean()) if chosen and n else None;values['preferred_yield']=int(labels[ret].sum()) if chosen else None
    if chosen and n:
        matched=np.lexsort((c['tie'],-c['score']))[:n];values['matched_k_precision_delta']=values['precision']-float(labels[matched].mean())
    if c['gold'] is not None:
        gold=c['gold'];observed=np.isfinite(gold);retobs=ret & observed
        match=np.zeros(c['N'],dtype=bool);match[np.lexsort((c['tie'],-c['score']))[:n]]=True;mo=match & observed
        mean=float(gold[retobs].mean()) if retobs.any() else None;other=float(gold[mo].mean()) if mo.any() else None;J=int(retobs.sum())
        ao=np.flatnonzero(observed)[np.lexsort((c['tie'][observed],-c['score'][observed]))[:J]];am=float(gold[ao].mean()) if J else None
        values.update(mqm_observed_return_count=J,mqm_return_observed_fraction=J/n if n else None,mqm_return_mean=mean,mqm_matched_k_observed_count=int(mo.sum()),mqm_matched_k_mean=other,mqm_matched_k_mean_delta=mean-other if mean is not None and other is not None else None,mqm_annotated_count_comparator_mean=am,mqm_annotated_count_delta=mean-am if mean is not None else None)
    for k,v in values.items():assert r[k]==v,(k,r[k],v)
    assert abs(float(pair.mean())-risk)<1e-12


def audit(experiment):
    start=time.monotonic();out=ROOT/'outputs'/('review-'+experiment);x=json.loads((out/'results.json').read_text());p=x['protocol'];methods=p['acquisition_methods'];nbase=6
    if experiment=='external':
        p={**p,'panels':['WMT24-'+lp for lp in p['language_priority']],'pool_definitions':{'WMT24-'+lp:[{'id':'alphabetical','indices':list(range(7))}] for lp in p['language_priority']}};nbase=5
    cfg={(panel,pool['id'],rep,agg,q) for panel in p['panels'] for pool in p['pool_definitions'][panel] for rep in range(p['splits']) for agg in p['aggregators'] for q in p['quantiles']}
    pools={(panel,pool['id']):pool for panel in p['panels'] for pool in p['pool_definitions'][panel]}
    qr={(r['dataset'],r['pool_id'],r['split'],r['aggregator'],r['q'],r['alpha'],r['method'],r['stopping']):r for r in x['query_records']}
    br={(r['dataset'],r['pool_id'],r['split'],r['aggregator'],r['q'],r['alpha'],r['method']):r for r in x['baseline_records']}
    alphas=[float(Fraction(a)) for a in p['alphas']]
    assert len(qr)==len(x['query_records'])==len(cfg)*len(alphas)*len(methods)*2
    assert len(br)==len(x['baseline_records'])==len(cfg)*len(alphas)*nbase
    keys=set();answers=states=violations=checked_baselines=paths=0
    with gzip.open(out/'traces.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line);key=tuple(z['key']);assert key in cfg and key not in keys;keys.add(key)
            panel,poolid,rep,agg,q=key;c=context(panel,pools[(panel,poolid)],rep,agg,q);c['panel']=panel;budgets=[(2*c['k']*c['H']*Fraction(a).numerator)//Fraction(a).denominator for a in p['alphas']]
            for entry in z['baseline_masks']:
                r=br[key+(entry['alpha'],entry['method'])];b=budgets[alphas.index(entry['alpha'])];mask=np.array(entry['mask'],dtype=bool)
                validate_metrics(r,mask,c,entry['method']=='fixed_count_batch_selected_optimum');assert r['integer_budget']==b
                if entry['method']=='envelope_crc':violations+=r['risk']>r['alpha']+1e-12
                else:assert r['risk']<=r['alpha']+1e-12
                checked_baselines+=1
            assert len(z['trace'])==len(methods) and {path['method'] for path in z['trace']}==set(methods)
            for path in z['trace']:
                trace=np.array(path['trace'],dtype=np.int64).reshape(-1,3);paths+=1
                if len(trace):
                    r,i,flip=trace.T;assert np.all(c['sel'][i] & (c['p'][i]>0));assert np.array_equal(flip,c['f'][r,i]);assert len(np.unique(r*c['N']+i))==len(trace)
                epsilon=math.ceil(.02*c['sel'].sum());tol,exact=first_stops(trace,c['p'],c['sel'],c['T'],np.array(budgets,dtype=np.int64),epsilon)
                assert len(path['budgets'])==len(alphas)
                saved={}
                for a,entry in enumerate(path['budgets']):
                    assert entry['alpha']==alphas[a] and entry['integer_budget']==budgets[a]
                    assert entry['two_percent_stop']['queries']==tol[a] and entry['exact_stop']['queries']==exact[a] and tol[a]>=0 and exact[a]>=0
                    for st in entry['states']+[entry['two_percent_stop'],entry['exact_stop']]:saved.setdefault(st['queries'],[]).append((a,st))
                    for stop,st in [('two_percent_gap',entry['two_percent_stop']),('exact_gap',entry['exact_stop'])]:
                        r=qr[key+(alphas[a],path['method'],stop)];validate_metrics(r,np.array(st['mask'],dtype=bool),c)
                        V=capacity(c['F'][c['sel']],budgets[a]);assert r['V_star']==V and r['V_lower']==st['V_lower'] and r['V_upper']==st['V_upper']
                        assert r['queries']==st['queries'] and r['certificate_gap']==st['gap'] and r['realized_regret']==V-st['V_lower'] and r['realized_regret']<=r['epsilon']
                        active=int(np.sum(c['sel'] & (c['p']>0)))*c['T'];assert r['active_entries']==active and r['active_fraction']==(r['queries']/active if active else 0)
                        assert r['panel_fraction']==r['queries']/(c['N']*c['T'])
                        if agg=='median':
                            zz=np.sort(c['F'][c['sel'] & (c['p']>0)]//((c['M']+1)//2));b=budgets[a]//((c['M']+1)//2);L=capacity(zz,b);S=max(0,L*c['T']-b);E=0
                            if L<len(zz):
                                level=next(t for t in range(c['T']+1) if np.minimum(zz[:L+1],t).sum()>=b+1);E=b+1+(len(zz)-L-1)*level
                            assert (r['offline_exact_certificate'],r['offline_exact_safe_part'],r['offline_exact_exclusion_part'])==(S+E,S,E)
                            if stop=='exact_gap':assert r['queries']>=S+E
                lo=np.zeros(c['N'],dtype=int);hi=c['T']*c['p'].copy()
                for step in range(len(trace)+1):
                    for a,st in saved.get(step,[]):
                        mask=np.array(st['mask'],dtype=bool);b=budgets[a];Vlo=capacity(hi[c['sel']],b);Vhi=capacity(lo[c['sel']],b);V=capacity(c['F'][c['sel']],b)
                        assert (st['V_lower'],st['V_upper'],st['gap'])==(Vlo,Vhi,Vhi-Vlo)
                        assert Vlo<=V<=Vhi and np.sum(mask & c['sel'])==Vlo and np.sum(hi[mask])<=b and np.sum(c['F'][mask])<=b
                        assert st['upper_selected_cost']==np.sum(hi[mask & c['sel']]) and np.all(~(mask & ~c['sel'] & (c['p']>0)));states+=1
                    if step<len(trace):
                        r,i,v=trace[step];lo[i]+=v;hi[i]-=c['p'][i]-v;answers+=1;assert lo[i]<=c['F'][i]<=hi[i]
            if len(keys)%80==0:print('audit',experiment,'cases',len(keys),'seconds',round(time.monotonic()-start,1),flush=True)
    assert keys==cfg and checked_baselines==len(br)
    report={'status':'PASS_SCOPED_INDEPENDENT_ARITHMETIC_FIRST_STOP_AND_FULL_GRID','experiment':experiment,'configuration_cases':len(cfg),'risk_budget_configurations':len(cfg)*len(alphas),'shared_paths':paths,'replayed_answers':answers,'saved_states_checked':states,'baseline_records_checked':checked_baselines,'query_records_checked':len(qr),'crc_over_budget_records':violations,'runtime_seconds':time.monotonic()-start,'source_results_sha256':hashlib.sha256((out/'results.json').read_bytes()).hexdigest(),'scope':'Separate arithmetic implementation by same assistant; no human certification, full literature certification, model runtime or redistribution permission.'}
    (ROOT/'review-revision'/(experiment+'-independent-audit.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('experiment',choices=['budget','composition','external']);a=p.parse_args();audit(a.experiment)

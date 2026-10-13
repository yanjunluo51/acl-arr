"""Parallel independent case arithmetic audit; no acquisition-code imports."""
from audit_review_results import context,capacity,validate_metrics,first_stops,ROOT
from fractions import Fraction
import argparse,gzip,hashlib,json,math,multiprocessing,time
import numpy as np


def audit_case(task):
    z,p,methods,pool,baseline_rows,query_rows=task
    key=tuple(z['key']);alphas=[float(Fraction(a)) for a in p['alphas']]
    pools={(key[0],key[1]):pool}
    br={(r['dataset'],r['pool_id'],r['split'],r['aggregator'],r['q'],r['alpha'],r['method']):r for r in baseline_rows}
    qr={(r['dataset'],r['pool_id'],r['split'],r['aggregator'],r['q'],r['alpha'],r['method'],r['stopping']):r for r in query_rows}
    answers=states=violations=checked_baselines=paths=0
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
    return key,answers,states,violations,checked_baselines,paths


def audit(experiment,workers):
    start=time.monotonic();out=ROOT/'outputs'/('review-'+experiment);x=json.loads((out/'results.json').read_text());p=x['protocol'];methods=p['acquisition_methods'];nbase=6
    if experiment=='external':
        p={**p,'panels':['WMT24-'+lp for lp in p['language_priority']],'pool_definitions':{'WMT24-'+lp:[{'id':'alphabetical','indices':list(range(7))}] for lp in p['language_priority']}};nbase=5
    cfg={(panel,pool['id'],rep,agg,q) for panel in p['panels'] for pool in p['pool_definitions'][panel] for rep in range(p['splits']) for agg in p['aggregators'] for q in p['quantiles']}
    pools={(panel,pool['id']):pool for panel in p['panels'] for pool in p['pool_definitions'][panel]}
    qr={};br={}
    for r in x['query_records']:qr.setdefault((r['dataset'],r['pool_id'],r['split'],r['aggregator'],r['q']),[]).append(r)
    for r in x['baseline_records']:br.setdefault((r['dataset'],r['pool_id'],r['split'],r['aggregator'],r['q']),[]).append(r)
    assert set(qr)==set(br)==cfg
    alphas=[float(Fraction(a)) for a in p['alphas']]
    qrecords=sum(map(len,qr.values()));brecords=sum(map(len,br.values()))
    assert qrecords==len(cfg)*len(alphas)*len(methods)*2 and brecords==len(cfg)*len(alphas)*nbase
    for key in cfg:
        assert len({(r['alpha'],r['method'],r['stopping']) for r in qr[key]})==len(qr[key])
        assert len({(r['alpha'],r['method']) for r in br[key]})==len(br[key])
    inputkeys=set()
    def inputs():
        with gzip.open(out/'traces.jsonl.gz','rt') as f:
            for line in f:
                z=json.loads(line);key=tuple(z['key']);assert key in cfg and key not in inputkeys;inputkeys.add(key)
                yield z,p,methods,pools[key[:2]],br[key],qr[key]
    keys=set();answers=states=violations=checked_baselines=paths=0
    with multiprocessing.get_context('spawn').Pool(workers) as pool:
        for key,a,s,v,b,n in pool.imap(audit_case,inputs(),chunksize=4):
            assert key not in keys;keys.add(key);answers+=a;states+=s;violations+=v;checked_baselines+=b;paths+=n
            if len(keys)%160==0:print('parallel audit',experiment,'cases',len(keys),'seconds',round(time.monotonic()-start,1),flush=True)
    assert inputkeys==keys==cfg and checked_baselines==brecords
    report={'status':'PASS_SCOPED_INDEPENDENT_ARITHMETIC_FIRST_STOP_AND_FULL_GRID','experiment':experiment,'configuration_cases':len(cfg),'risk_budget_configurations':len(cfg)*len(alphas),'shared_paths':paths,'replayed_answers':answers,'saved_states_checked':states,'baseline_records_checked':checked_baselines,'query_records_checked':qrecords,'crc_over_budget_records':violations,'runtime_seconds':time.monotonic()-start,'workers':workers,'source_results_sha256':hashlib.sha256((out/'results.json').read_bytes()).hexdigest(),'scope':'Separate arithmetic implementation by same assistant; no human certification, full literature certification, model runtime or redistribution permission.'}
    (ROOT/'review-revision'/(experiment+'-independent-audit.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('experiment',choices=['budget','composition','external']);p.add_argument('--workers',type=int,default=4);a=p.parse_args();audit(a.experiment,a.workers)

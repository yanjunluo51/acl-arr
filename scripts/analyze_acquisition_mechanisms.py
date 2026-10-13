"""Post-path diagnostics of complete frozen acquisition methods on six panels.

No scoring inference, new policy, tuning, or modification of old scientific files.
All test replies are checked; saved stopping masks/frontiers remain the target.
"""
import csv,gzip,hashlib,json,math,statistics,time
from pathlib import Path
from fractions import Fraction
from functools import lru_cache
import numpy as np
from scipy.stats import rankdata
from mapping_column_experiments import map_scores
from query_selection import aggregate,endpoint_cost,all_flips,fit_prior,capacity
from run_tolerance_sensitivity import configurations
from tolerance_certificates import minimum_gap_certificate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/acquisition-mechanisms'
SPEC=ROOT/'review-revision/score-observation-implementation/protocol.json'
TAUS=[Fraction(0),Fraction(1,50),Fraction(1,10)]


def corr(x,y):
    x,y=np.asarray(x,float),np.asarray(y,float)
    if len(x)<2 or np.ptp(x)==0 or np.ptp(y)==0:return None
    return float(np.corrcoef(rankdata(x),rankdata(y))[0,1])


@lru_cache(maxsize=16)
def mapped(panel,rep):return map_scores(panel,rep,'1','right')


def prepare(key):
    panel,agg,rep,q=key
    ref,test,seed,_,_=mapped(panel,rep)
    base,hidden=test[:7],test[7:];T,N=hidden.shape
    cutoff=np.sort(aggregate(ref[:7],agg))[-max(1,round(q*ref.shape[1]))]
    selected=aggregate(base,agg)>=cutoff;p=endpoint_cost(base,cutoff,agg)
    f=all_flips(base,hidden,cutoff,agg);assert np.all(f<=p)
    prior=fit_prior(ref[:7],ref[7:],base,cutoff,p,agg)
    ids=np.flatnonzero(selected & (p>0));m=len(ids);S=int(selected.sum());free=S-m
    local=np.full(N,-1,np.int64);local[ids]=np.arange(m)
    truth=f[:,ids].T;pred=prior[ids];lp=p[ids];cost=f.sum(axis=0)
    k=max(1,round(q*N));budget=2*k*7*T//10
    tie=np.random.default_rng(seed+rep+700001).permutation(N)
    quantized=panel.startswith('WMT24')
    ticks=np.rint(pred*10**12).astype(np.int64) if quantized else pred
    mae=float(np.mean(np.abs(pred-truth)/lp[:,None])) if m else None
    rho=corr(pred.sum(axis=1),truth.sum(axis=1))
    z=cost[ids]//4 if agg=='median' else None
    witnesses={tau:minimum_gap_certificate(z,T,budget//4,math.ceil(tau*S))['queries'] if z is not None else None for tau in TAUS}
    return locals()


def main():
    spec=json.loads(SPEC.read_text());OUT.mkdir(exist_ok=False)
    start=time.monotonic();bindings={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in spec['frozen_inputs']}
    (OUT/'execution.json').write_text(json.dumps({'status':'RUNNING','input_bindings':bindings},indent=2)+'\n')
    saved={}
    for x in csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open()):
        tau=Fraction(x['tau'])
        if tau in TAUS:saved[(x['dataset'],x['aggregator'],int(x['split']),float(x['q']),x['method'],tau)]=x
    cases={};cache=None;c=None;paths=answers=choicechecks=0;seen=set()
    for key,method,trace,oldtol,oldexact in configurations():
        assert (*key,method) not in seen;seen.add((*key,method))
        if key!=cache:c=prepare(key);cache=key
        panel,agg,rep,q=key;N,T,m=c['N'],c['T'],c['m']
        tr=np.asarray(trace,np.int64).reshape(-1,3)
        assert len(tr)==oldexact['queries']
        assert len({(int(r),int(i)) for r,i,_ in tr})==len(tr)
        if len(tr):
            assert np.all(c['local'][tr[:,1]]>=0)
            assert np.array_equal(c['f'][tr[:,0],tr[:,1]],tr[:,2])
        stops={tau:saved[(*key,method,tau)] for tau in TAUS}
        targets=set(int(x['queries']) for x in stops.values())
        if method=='reference_priority':targets|={max(0,int(x['queries'])-1) for x in stops.values()}
        low=np.zeros(m,np.int64);upper=T*c['lp'].copy();known=np.zeros((m,T),bool);snap={}
        for step in range(max(targets,default=0)+1):
            if step in targets:
                vlo=c['free']+capacity(upper,c['budget']);vhi=c['free']+capacity(low,c['budget'])
                snapshot={'V_lower':vlo,'V_upper':vhi,'gap':vhi-vlo}
                if method=='reference_priority':
                    remain=np.any(~known,axis=1);prediction=low+np.where(known,0,c['pred']).sum(axis=1)
                    snapshot['remaining_normalized_total_mae']=float(np.mean(np.abs(prediction[remain]-c['truth'].sum(axis=1)[remain])/(T*c['lp'][remain]))) if remain.any() else None
                    snapshot['remaining_row_rho']=corr(prediction[remain],c['truth'].sum(axis=1)[remain])
                    if step<len(tr) and remain.any():
                        estimates=low*10**12+np.where(known,0,c['ticks']).sum(axis=1) if c['quantized'] else low+np.where(known,0,c['pred']).sum(axis=1)
                        candidates=np.flatnonzero(remain)
                        i=int(min(candidates,key=lambda a:(estimates[a],c['tie'][c['ids'][a]])))
                        remaining=np.flatnonzero(~known[i]);r=int(min(remaining,key=lambda a:(c['ticks'][i,a],int(a))))
                        assert int(tr[step,0])==r and int(tr[step,1])==int(c['ids'][i]),(key,step,'priority reconstruction mismatch')
                        choicechecks+=1
                snap[step]=snapshot
            if step==max(targets,default=0):break
            r,full,f=map(int,tr[step]);i=int(c['local'][full]);assert not known[i,r]
            known[i,r]=True;low[i]+=f;upper[i]-=int(c['lp'][i])-f
        for tau,x in stops.items():
            Q=int(x['queries']);st=snap[Q];epsilon=math.ceil(tau*c['S'])
            assert st['V_lower']==int(x['returned_count']) and st['V_upper']==int(x['V_upper']) and st['gap']==int(x['certificate_gap'])<=epsilon
            w=c['witnesses'][tau]
            if w is not None:assert int(x['offline_gap_certificate'])==w and Q>=w
            ck=(*key,str(tau))
            a=cases.setdefault(ck,{'dataset':panel,'aggregator':agg,'split':rep,'q':q,'tau':str(tau),'epsilon':epsilon,'active_rows':m,'selected_count':c['S'],'invariant_fraction':c['free']/c['S'] if c['S'] else None,'flip_mae':c['mae'],'initial_row_rho':c['rho'],'Q_epsilon':w})
            a[method+'_queries']=Q
            if method=='reference_priority':
                before=snap[max(0,Q-1)];a['prestop_remaining_mae']=before['remaining_normalized_total_mae'];a['prestop_row_rho']=before['remaining_row_rho']
                if Q:assert before['gap']>epsilon
                a['reference_witness_overhead']=Q-w if w is not None else None
        paths+=1;answers+=len(tr)
        if paths%320==0:print('paths',paths,'seconds',round(time.monotonic()-start,1),flush=True)
    assert paths==7680 and len(cases)==5760 and len(saved)==23040
    rows=list(cases.values());groups={}
    for x in rows:
        assert all(m+'_queries' in x for m in spec['methods'])
        x['reference_minus_width']=x['reference_priority_queries']-x['largest_width_queries']
        x['reference_minus_fixed']=x['reference_priority_queries']-x['fixed_queries']
        x['reference_strict_best']=int(x['reference_priority_queries']<min(x[m+'_queries'] for m in spec['methods'] if m!='reference_priority'))
        groups.setdefault((x['dataset'],x['aggregator'],x['q'],x['tau']),[]).append(x)
    fields=['flip_mae','initial_row_rho','prestop_remaining_mae','prestop_row_rho','invariant_fraction','Q_epsilon','reference_witness_overhead','reference_minus_width','reference_minus_fixed']+[m+'_queries' for m in spec['methods']]
    summaries=[]
    for key,g in sorted(groups.items()):
        assert len(g)==40 and {x['split'] for x in g}==set(range(40))
        a=dict(zip(['dataset','aggregator','q','tau'],key),splits=40,reference_strict_best=sum(x['reference_strict_best'] for x in g),reference_beats_width=sum(x['reference_minus_width']<0 for x in g))
        for f in fields:
            values=[x[f] for x in g if x[f] is not None];a[f]=statistics.fmean(values) if values else None;a[f+'_defined']=len(values)
        pairs=[(x['flip_mae'],x['reference_minus_width']) for x in g if x['flip_mae'] is not None]
        a['mae_vs_extra_queries_rho']=corr(*zip(*pairs)) if pairs else None
        summaries.append(a)
    for name,data in [('split_diagnostics.csv',rows),('summary.csv',summaries)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    (OUT/'results.json').write_text(json.dumps({'protocol':spec,'records':rows,'cells':summaries},indent=2,allow_nan=False)+'\n')
    assert bindings=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in bindings}
    result={'status':'PASS_FULL_FROZEN_PATH_MECHANISM_DIAGNOSTICS','configuration_cases':1920,'paths':paths,'saved_stop_states_checked':len(saved),'paired_records':len(rows),'summary_cells':len(summaries),'cached_replies_checked':answers,'reference_choices_reconstructed':choicechecks,'new_policy_or_inference':False,'elapsed_seconds':time.monotonic()-start,'input_bindings':bindings}
    (OUT/'execution.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='input_bindings'},indent=2))

if __name__=='__main__':main()

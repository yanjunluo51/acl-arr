"""Complete review-driven budget and composition experiments.

The acquisition rules are unchanged. Budget-independent paths are shared, with
separate first stopping states; scores still enter the solver only via callback.
"""
from pathlib import Path
from fractions import Fraction
from functools import lru_cache
import argparse,csv,gzip,heapq,json,math,multiprocessing,random,statistics,time
import numpy as np
from query_selection import aggregate,endpoint_cost,fit_prior,flips,prefix,metrics,exact_offline_certificate,summary
from analyze import calibrate_envelope,topk
ROOT=Path(__file__).resolve().parents[1]
METHODS=['fixed','random','largest_width','reference_priority']


def capacities(hist,budgets):
    costs=np.cumsum(hist*np.arange(len(hist)),dtype=np.int64)
    counts=np.cumsum(hist,dtype=np.int64)
    index=np.searchsorted(costs,budgets,side='right')
    before=np.maximum(index-1,0)
    values=counts[before].copy()
    partial=index<len(hist)
    values[partial]+=(budgets[partial]-costs[before[partial]])//index[partial]
    return values


def solve_multi(base,selected,p,prior,threshold,agg,T,budgets,tie,method,seed,query,checkpoints,epsilon):
    ids=np.flatnonzero(selected & (p>0));free=int(np.sum(selected & (p==0)))
    lp=p[ids];m=len(ids);total=m*T;nb=len(budgets)
    lower=np.zeros(m,dtype=np.int64);upper=T*lp.copy();known=np.zeros((m,T),dtype=bool)
    estimate=prior[ids].copy();size=T*int(p.max(initial=0))+1
    lh=np.bincount(lower,minlength=size);uh=np.bincount(upper,minlength=size)
    targets=sorted(set(math.ceil(v*total) for v in checkpoints)|{total})
    states=[[] for _ in budgets];tolerant=[None]*nb;exact=[None]*nb;trace=[]
    candidates=np.arange(T)
    if method=='reference_priority':
        candidate_order=[np.lexsort((candidates,-(lp[i]-estimate[i]))) for i in range(m)]
        heap=[(float(np.sum(estimate[i])),int(tie[ids[i]]),i) for i in range(m)]
    elif method=='largest_width':heap=[(-int(upper[i]),int(tie[ids[i]]),i) for i in range(m)]
    else:heap=[]
    heapq.heapify(heap);nseen=np.zeros(m,dtype=int)
    fixed_rows=np.argsort(tie[ids]);random_order=np.random.default_rng(seed).permutation(total)

    def snapshot(a,vlo,vhi):
        mask=(p==0).copy();keep=prefix(upper,int(budgets[a]),tie[ids]);mask[ids[keep]]=True
        return {'queries':len(trace),'V_lower':int(vlo),'V_upper':int(vhi),'gap':int(vhi-vlo),
                'mask':mask.tolist(),'upper_selected_cost':int(upper[keep].sum())}

    for step in range(total+1):
        vlo=free+capacities(uh,budgets);vhi=free+capacities(lh,budgets);gap=vhi-vlo
        for a in range(nb):
            if exact[a] is not None:continue
            save=step in targets or (tolerant[a] is None and gap[a]<=epsilon) or gap[a]==0
            if not save:continue
            st=snapshot(a,vlo[a],vhi[a])
            if tolerant[a] is None and st['gap']<=epsilon:tolerant[a]=st
            if gap[a]==0:exact[a]=st
            if step in targets:states[a].append(st)
        if all(s is not None for s in exact):break
        assert step<total
        if method=='fixed':i=int(fixed_rows[step//T]);c=step%T
        elif method=='random':i,c=divmod(int(random_order[step]),T)
        else:
            _,_,i=heapq.heappop(heap)
            c=int(candidate_order[i][nseen[i]]) if method=='reference_priority' else int(nseen[i])
        assert not known[i,c]
        item=int(ids[i]);score=query(c,item)
        f=int(lp[i]) if agg=='median' and score<threshold else (0 if agg=='median' else flips(base[:,item],score,threshold,agg))
        assert 0<=f<=lp[i]
        lh[lower[i]]-=1;uh[upper[i]]-=1
        lower[i]+=f;upper[i]-=lp[i]-f;lh[lower[i]]+=1;uh[upper[i]]+=1
        known[i,c]=True;nseen[i]+=1;trace.append([c,item,f])
        if method in ('reference_priority','largest_width') and nseen[i]<T:
            key=float(lower[i]+np.sum(np.where(known[i],0.,estimate[i]))) if method=='reference_priority' else -int(upper[i]-lower[i])
            heapq.heappush(heap,(key,int(tie[item]),i))
    for a in range(nb):
        assert tolerant[a] is not None and exact[a] is not None
        seen={s['queries'] for s in states[a]}
        for target in targets:
            if target not in seen:states[a].append({**exact[a],'budget_checkpoint_queries':target})
    return trace,states,tolerant,exact


@lru_cache(maxsize=4)
def raw_panel(panel):
    file='rb2_ranked_panel.json' if panel=='RewardBench2' else 'wmt23_metric_panel.json'
    z=json.loads((ROOT/'data'/file).read_text());models=z['models'];gids=z['prompt_ids']
    cols=[i for i,s in enumerate(z.get('systems',[0,1,2,3])) if panel!='WMT23_without_synthetic_ref' or s!='synthetic_ref']
    a=np.array([[np.array(z['scores'][m][gid])[cols] for gid in gids] for m in models],dtype=float).reshape(len(models),-1)
    assert np.isfinite(a).all()
    return z,a,len(cols)


@lru_cache(maxsize=8)
def mapped_panel(panel,rep):
    z,raw,g=raw_panel(panel);seed=20260815 if panel=='RewardBench2' else 87000
    order=list(range(len(z['prompt_ids'])));random.Random(seed+rep).shuffle(order);third=len(order)//3
    groups=[order[:third],order[third:2*third],order[2*third:]]
    idx=[np.array([a*g+b for a in part for b in range(g)]) for part in groups]
    mapped=np.array([np.searchsorted(np.sort(row[idx[0]]),row,side='right')/len(idx[0]) for row in raw])
    return [mapped[:,ix] for ix in idx],g,seed,idx


def swap_geometry(base,cand,t,agg):
    old=aggregate(base,agg)>=t
    bits=np.empty((len(base),len(cand),base.shape[1]),dtype=bool)
    for j in range(len(base)):
        for c in range(len(cand)):
            v=base.copy();v[j]=cand[c];bits[j,c]=(aggregate(v,agg)>=t)!=old
    return bits,bits.sum(axis=0)


def diagnostics(cost,selected,mask,H,k,labels,bits,alpha,consensus,tie):
    d=metrics(cost,selected,mask,H,k,labels)
    risks=np.sum(bits[:,:,mask],axis=2)/(2*k)
    assert abs(float(risks.mean())-d['risk'])<1e-12
    d.update(replacement_max_risk=float(risks.max()),replacement_over_alpha_fraction=float(np.mean(risks>alpha+1e-12)))
    if labels is not None and d['returned_count']:
        matched=np.lexsort((tie,-consensus))[:d['returned_count']]
        d['matched_k_precision_delta']=d['precision']-float(labels[matched].mean())
    return d


def case(task):
    panel,pool,rep,agg,q,alphas,checkpoints=task
    mapped,g,seed,idx=mapped_panel(panel,rep);poolidx=pool['indices'];M=len(poolidx)
    remaining=[i for i in range(mapped[0].shape[0]) if i not in poolidx]
    ref,cal,test=[a[poolidx] for a in mapped];cr=mapped[0][remaining];cc=mapped[1][remaining];hidden=mapped[2][remaining]
    T=len(remaining);H=M*T;N=test.shape[1];k=max(1,round(q*N));tie=np.random.default_rng(seed+rep+700001).permutation(N)
    alpha_values=[float(Fraction(a)) for a in alphas]
    budgets=np.array([(2*k*H*Fraction(a).numerator)//Fraction(a).denominator for a in alphas],dtype=np.int64)
    t=np.sort(aggregate(ref,agg))[-max(1,round(q*ref.shape[1]))];consensus=aggregate(test,agg);sel=consensus>=t
    p=endpoint_cost(test,t,agg);bits,f=swap_geometry(test,hidden,t,agg);cost=f.sum(axis=0)
    assert np.all(f<=p);_,fc=swap_geometry(cal,cc,t,agg);cal_cost=fc.sum(axis=0)
    prior=fit_prior(ref,cr,test,t,p,agg);epsilon=math.ceil(.02*np.sum(sel));total=int(np.sum(sel & (p>0)))*T
    labels=np.tile([1,0,0,0],N//4) if panel=='RewardBench2' else None
    fixed=topk(consensus,k);fixed_bits=np.empty_like(bits)
    for j in range(M):
        for c in range(T):
            v=test.copy();v[j]=hidden[c];fixed_bits[j,c]=topk(aggregate(v,agg),k)!=fixed
    fixed_cost=fixed_bits.sum(axis=(0,1));baseline=[];queries=[];logs=[]
    common={'dataset':panel,'pool_id':pool['id'],'pool_indices':poolidx,'aggregator':agg,'split':rep,'q':q,
            'k':k,'M':M,'H':H,'T':T,'n_test_items':N,'active_selected_items':total//T,
            'candidate_reference_entries':T*ref.shape[1],'pool_reference_entries':M*ref.shape[1],'pool_test_entries':M*N}
    baseline_masks=[]
    for a,alpha in enumerate(alpha_values):
        b=int(budgets[a]);zero=(p==0).copy();sopt=zero.copy()
        sopt[np.flatnonzero(sel)[prefix(cost[sel],b,tie[sel])]]=True
        zero[np.flatnonzero(sel)[prefix((T*p)[sel],b,tie[sel])]]=True
        uniform=np.zeros(N,dtype=bool)
        for v in np.unique(cost):
            mask=cost<=v
            if int(cost[mask].sum())>b:break
            uniform=mask
        fkeep=np.zeros(N,dtype=bool);fkeep[np.flatnonzero(fixed)[prefix(fixed_cost[fixed],b,tie[fixed])]]=True
        lam=calibrate_envelope(cal_cost/H,g,N/(2*k),alpha=alpha)
        masks=[('zero_query_structural',zero,sel,cost,bits),('envelope_crc',cost/H<=lam,sel,cost,bits),
               ('batch_uniform_threshold',uniform,sel,cost,bits),('batch_max_cardinality',prefix(cost,b,tie),sel,cost,bits),
               ('batch_selected_optimum',sopt,sel,cost,bits),('fixed_count_batch_selected_optimum',fkeep,fixed,fixed_cost,fixed_bits)]
        for method,mask,target,w,pairs in masks:
            if method!='envelope_crc':assert np.sum(w[mask])<=b
            row={**common,'alpha':alpha,'alpha_rational':alphas[a],'integer_budget':b,'method':method,
                 'certificate':'expectation_crc' if method=='envelope_crc' else 'realized_batch',
                 'candidate_test_entries':0 if method=='zero_query_structural' else N*T,
                 'candidate_calibration_entries':T*cal.shape[1] if method=='envelope_crc' else 0,
                 'pool_calibration_entries':M*cal.shape[1] if method=='envelope_crc' else 0,
                 **diagnostics(w,target,mask,H,k,labels,pairs,alpha,consensus,tie)}
            baseline.append(row);baseline_masks.append({'alpha':alpha,'method':method,'mask':mask.tolist()})
    for method in METHODS:
        observed=set()
        def query(c,i):
            assert (c,i) not in observed;observed.add((c,i));return float(hidden[c,i])
        trace,states,tolerant,exact=solve_multi(test,sel,p,prior,t,agg,T,budgets,tie,method,seed+rep+99173,query,checkpoints,epsilon)
        for c,i,v in trace:assert f[c,i]==v
        answers={'method':method,'trace':trace,'budgets':[]}
        for a,alpha in enumerate(alpha_values):
            b=int(budgets[a]);V=int(np.sum(sel & baseline_masks_to_mask(baseline_masks,alpha,'batch_selected_optimum')))
            for stopping,st in [('two_percent_gap',tolerant[a]),('exact_gap',exact[a])]:
                mask=np.array(st['mask'],dtype=bool);assert np.sum(cost[mask])<=b
                assert st['V_lower']<=V<=st['V_upper'] and np.sum(mask & sel)==st['V_lower']
                eps=epsilon if stopping=='two_percent_gap' else 0;assert V-st['V_lower']<=eps
                row={**common,'alpha':alpha,'alpha_rational':alphas[a],'integer_budget':b,'method':method,'stopping':stopping,
                     'epsilon':eps,'queries':st['queries'],'active_entries':total,'active_fraction':st['queries']/total if total else 0,
                     'panel_fraction':st['queries']/(N*T),'V_star':V,'V_lower':st['V_lower'],'V_upper':st['V_upper'],
                     'certificate_gap':st['gap'],'realized_regret':V-st['V_lower'],
                     **diagnostics(cost,sel,mask,H,k,labels,bits,alpha,consensus,tie)}
                if agg=='median':
                    factor=(M+1)//2;Q,S,E=exact_offline_certificate(cost[sel & (p>0)]//factor,T,b//factor)
                    row.update(offline_exact_certificate=Q,offline_exact_safe_part=S,offline_exact_exclusion_part=E)
                    if stopping=='exact_gap':assert st['queries']>=Q
                queries.append(row)
            answers['budgets'].append({'alpha':alpha,'integer_budget':b,'states':states[a],'two_percent_stop':tolerant[a],'exact_stop':exact[a]})
        logs.append(answers)
    return {'key':[panel,pool['id'],rep,agg,q],'baseline':baseline,'query':queries,'trace':logs,'baseline_masks':baseline_masks}


def baseline_masks_to_mask(masks,alpha,method):
    return np.array(next(x['mask'] for x in masks if x['alpha']==alpha and x['method']==method),dtype=bool)


def tasks(protocol):
    for panel in protocol['panels']:
        for pool in protocol['pool_definitions'][panel]:
            for rep in range(protocol['splits']):
                for agg in protocol['aggregators']:
                    for q in protocol['quantiles']:yield(panel,pool,rep,agg,q,protocol['alphas'],protocol['checkpoints'])


def run(experiment,workers):
    protocol_path=ROOT/'review-revision'/(experiment+'-protocol.json');protocol=json.loads(protocol_path.read_text())
    out=ROOT/'outputs'/('review-'+experiment);out.mkdir(parents=True,exist_ok=True)
    assert not (out/'results.json').exists(),'Preserve completed execution; do not overwrite it'
    (out/'execution.json').write_text(json.dumps({'status':'RUNNING','experiment':experiment},indent=2)+'\n')
    start=time.monotonic();baseline=[];queries=[];original_checks=0
    if experiment=='budget':
        old=json.loads((ROOT/'outputs/query_metrics.json').read_text())
        old_b={(x['dataset'],x['split'],x['aggregator'],x['q'],x['method']):x for x in old['baseline_records']}
        old_q={(x['dataset'],x['split'],x['aggregator'],x['q'],x['method'],x['stopping']):x for x in old['query_records']}
        prior_traces=gzip.open(ROOT/'outputs/query_traces.jsonl.gz','rt')
    shared_paths=0;total_answers=0;cases=0
    with gzip.open(out/'traces.jsonl.gz','wt',compresslevel=1) as log,multiprocessing.get_context('spawn').Pool(workers) as pool:
        for result in pool.imap(case,tasks(protocol),chunksize=4):
            if experiment=='budget':
                for label,rows,expected in [('baseline',result['baseline'],old_b),('query',result['query'],old_q)]:
                    for row in rows:
                        if row['alpha']!=.1:continue
                        key=(row['dataset'],row['split'],row['aggregator'],row['q'],row['method'])
                        if label=='query':key+=(row['stopping'],)
                        oldrow=expected[key]
                        assert all(row[k]==v for k,v in oldrow.items()),(label,key,{k:(v,row.get(k)) for k,v in oldrow.items() if row.get(k)!=v})
                        original_checks+=1
                for path in result['trace']:
                    previous=json.loads(next(prior_traces));panel,poolid,rep,agg,q=result['key']
                    assert previous['key']==[panel,agg,rep,q,path['method']]
                    target=next(b for b in path['budgets'] if b['alpha']==.1)
                    assert path['trace'][:target['exact_stop']['queries']]==previous['trace']
                    assert target['states']==previous['states'] and target['two_percent_stop']==previous['two_percent_stop'] and target['exact_stop']==previous['exact_stop']
                    original_checks+=1
            baseline.extend(result.pop('baseline'));queries.extend(result.pop('query'))
            shared_paths+=len(result['trace']);total_answers+=sum(len(p['trace']) for p in result['trace'])
            log.write(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n');cases+=1
            if cases%40==0:print(experiment,'cases',cases,'seconds',round(time.monotonic()-start,1),flush=True)
    if experiment=='budget':assert next(prior_traces,None) is None;prior_traces.close()
    fields=['risk','selected_coverage','returned_count','selected_review_count','precision','matched_k_precision_delta',
            'replacement_max_risk','replacement_over_alpha_fraction','queries','active_fraction','panel_fraction',
            'V_star','certificate_gap','realized_regret','offline_exact_certificate','offline_exact_safe_part','offline_exact_exclusion_part']
    bf=[f for f in fields if f not in ['queries','active_fraction','panel_fraction','V_star','certificate_gap','realized_regret','offline_exact_certificate','offline_exact_safe_part','offline_exact_exclusion_part']]
    keys=['dataset','pool_id','aggregator','q','alpha','method']
    payload={'protocol':protocol,'numpy':np.__version__,'baseline_records':baseline,'query_records':queries,
             'baseline_cells':summary(baseline,keys,bf),'query_cells':summary(queries,keys+['stopping'],fields)}
    (out/'results.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    for name in ('baseline','query'):
        rows=payload[name+'_cells']
        with (out/(name+'_cells.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=sorted(set().union(*(set(x) for x in rows))));w.writeheader();w.writerows(rows)
    receipt={'status':'PASS_FULL_EXECUTION_PENDING_INDEPENDENT_AUDIT','experiment':experiment,'configuration_cases':cases,
             'risk_budget_configurations':cases*len(protocol['alphas']),'shared_acquisition_paths':shared_paths,
             'separately_stopped_budget_paths':shared_paths*len(protocol['alphas']),'recorded_answers':total_answers,
             'baseline_records':len(baseline),'query_records':len(queries),'original_complete_record_state_trace_equalities':original_checks,
             'runtime_seconds':time.monotonic()-start,'runtime_scope':'local cached-score replay'}
    (out/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('experiment',choices=['budget','composition']);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    try:run(a.experiment,a.workers)
    except BaseException as e:
        out=ROOT/'outputs'/('review-'+a.experiment);out.mkdir(parents=True,exist_ok=True)
        (out/'execution.json').write_text(json.dumps({'status':'FAILED','error_type':type(e).__name__,'error':str(e)},indent=2)+'\n');raise

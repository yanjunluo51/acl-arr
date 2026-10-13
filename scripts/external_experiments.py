"""Frozen score-inspection method on document-grouped WMT24 panels."""
from pathlib import Path
from fractions import Fraction
from functools import lru_cache
import csv,gzip,json,math,multiprocessing,random,time
import numpy as np
from review_accelerated import swap_geometry,diagnostics,METHODS
from review_priority import solve_multi_quantized
from query_selection import aggregate,endpoint_cost,fit_prior,prefix,exact_offline_certificate,summary
from analyze import topk
ROOT=Path(__file__).resolve().parents[1]

@lru_cache(maxsize=3)
def raw(panel):
    lp=panel.removeprefix('WMT24-');z=json.loads((ROOT/'data'/f'wmt24_{lp}_panel.json').read_text());g=len(z['systems'])
    a=np.array([[z['scores'][m][i] for i in z['prompt_ids']] for m in z['models']],dtype=float).reshape(len(z['models']),-1)
    return z,a,g

@lru_cache(maxsize=5)
def mapped(panel,rep):
    z,a,g=raw(panel);docs=list(dict.fromkeys(z['source_document_ids']));random.Random(924000+rep).shuffle(docs);third=len(docs)//3
    groups=[set(docs[:third]),set(docs[third:2*third]),set(docs[2*third:])]
    idx=[np.array([i*g+j for i,d in enumerate(z['source_document_ids']) if d in part for j in range(g)]) for part in groups]
    assert all(len(ix) for ix in idx) and len(set.union(*groups))==len(docs)
    mapped=np.array([np.searchsorted(np.sort(row[idx[0]]),row,side='right')/len(idx[0]) for row in a])
    return [mapped[:,ix] for ix in idx],idx


def quality(mask,sel,score,tie,gold):
    returned=mask & sel;K=int(returned.sum());observed=np.isfinite(gold);retobs=returned & observed
    matched=np.zeros(len(mask),dtype=bool);matched[np.lexsort((tie,-score))[:K]]=True;matobs=matched & observed
    mean=float(gold[retobs].mean()) if retobs.any() else None;other=float(gold[matobs].mean()) if matobs.any() else None
    # A second descriptive comparison fixes the number of annotated returned
    # outputs. It compares only the observed-label subpopulation, not full K.
    J=int(retobs.sum());annotated_order=np.flatnonzero(observed)[np.lexsort((tie[observed],-score[observed]))[:J]]
    annmean=float(gold[annotated_order].mean()) if J else None
    return {'mqm_observed_return_count':J,'mqm_return_observed_fraction':J/K if K else None,'mqm_return_mean':mean,
            'mqm_matched_k_observed_count':int(matobs.sum()),'mqm_matched_k_mean':other,
            'mqm_matched_k_mean_delta':mean-other if mean is not None and other is not None else None,
            'mqm_annotated_count_comparator_mean':annmean,'mqm_annotated_count_delta':mean-annmean if mean is not None else None}


def case(task):
    panel,rep,agg,q=task;mapped_scores,idx=mapped(panel,rep);ref,cal,test=[a[:7] for a in mapped_scores];cr,hidden=mapped_scores[0][7:],mapped_scores[2][7:]
    M=7;T=len(hidden);H=M*T;N=test.shape[1];k=max(1,round(q*N));b=(2*k*H)//10;tie=np.random.default_rng(924000+rep+700001).permutation(N)
    t=np.sort(aggregate(ref,agg))[-max(1,round(q*ref.shape[1]))];score=aggregate(test,agg);sel=score>=t
    p=endpoint_cost(test,t,agg);bits,f=swap_geometry(test,hidden,t,agg);cost=f.sum(axis=0);assert np.all(f<=p)
    prior=fit_prior(ref,cr,test,t,p,agg);epsilon=math.ceil(.02*sel.sum());total=int(np.sum(sel & (p>0)))*T
    fixed=topk(score,k);fb=np.empty_like(bits)
    for j in range(M):
        for c in range(T):
            v=test.copy();v[j]=hidden[c];fb[j,c]=topk(aggregate(v,agg),k)!=fixed
    fc=fb.sum(axis=(0,1));common={'dataset':panel,'pool_id':'alphabetical','pool_indices':list(range(7)),'aggregator':agg,'split':rep,'q':q,'alpha':.1,'alpha_rational':'1/10','integer_budget':b,'M':M,'T':T,'H':H,'k':k,'n_test_items':N,'active_selected_items':total//T,'candidate_reference_entries':T*ref.shape[1],'pool_reference_entries':M*ref.shape[1],'pool_test_entries':M*N}
    zero=p==0;sopt=zero.copy();sopt[np.flatnonzero(sel)[prefix(cost[sel],b,tie[sel])]]=True
    zero[np.flatnonzero(sel)[prefix((T*p)[sel],b,tie[sel])]]=True
    uniform=np.zeros(N,dtype=bool)
    for value in np.unique(cost):
        mask=cost<=value
        if cost[mask].sum()>b:break
        uniform=mask
    fkeep=np.zeros(N,dtype=bool);fkeep[np.flatnonzero(fixed)[prefix(fc[fixed],b,tie[fixed])]]=True
    baselines=[];queryrows=[];masks=[];logs=[];quality_inputs=[]
    for method,mask,target,w,pairs in [('zero_query_structural',zero,sel,cost,bits),('batch_uniform_threshold',uniform,sel,cost,bits),('batch_max_cardinality',prefix(cost,b,tie),sel,cost,bits),('batch_selected_optimum',sopt,sel,cost,bits),('fixed_count_batch_selected_optimum',fkeep,fixed,fc,fb)]:
        assert w[mask].sum()<=b;row={**common,'method':method,'certificate':'realized_batch','candidate_test_entries':0 if method=='zero_query_structural' else N*T,'candidate_calibration_entries':0,'pool_calibration_entries':0,**diagnostics(w,target,mask,H,k,None,pairs,.1,score,tie)}
        baselines.append(row);masks.append({'alpha':.1,'method':method,'mask':mask.tolist()});quality_inputs.append((row,mask,target))
    V=int(np.sum(sopt & sel))
    for method in METHODS:
        seen=set()
        def query(c,i):
            assert (c,i) not in seen;seen.add((c,i));return float(hidden[c,i])
        trace,states,tol,exact=solve_multi_quantized(test,sel,p,prior,t,agg,T,np.array([b]),tie,method,924000+rep+99173,query,[0,.1,.25,.5,1],epsilon,priority_scale=10**12)
        for c,i,v in trace:assert f[c,i]==v
        for stop,st in [('two_percent_gap',tol[0]),('exact_gap',exact[0])]:
            mask=np.array(st['mask'],dtype=bool);assert cost[mask].sum()<=b and st['V_lower']<=V<=st['V_upper'];eps=epsilon if stop=='two_percent_gap' else 0
            row={**common,'method':method,'stopping':stop,'epsilon':eps,'queries':st['queries'],'active_entries':total,'active_fraction':st['queries']/total if total else 0,'panel_fraction':st['queries']/(N*T),'V_star':V,'V_lower':st['V_lower'],'V_upper':st['V_upper'],'certificate_gap':st['gap'],'realized_regret':V-st['V_lower'],**diagnostics(cost,sel,mask,H,k,None,bits,.1,score,tie)}
            if agg=='median':
                Q,S,E=exact_offline_certificate(cost[sel & (p>0)]//4,T,b//4);row.update(offline_exact_certificate=Q,offline_exact_safe_part=S,offline_exact_exclusion_part=E)
                if stop=='exact_gap':assert st['queries']>=Q
            queryrows.append(row);quality_inputs.append((row,mask,sel))
        logs.append({'method':method,'trace':trace,'budgets':[{'alpha':.1,'integer_budget':b,'states':states[0],'two_percent_stop':tol[0],'exact_stop':exact[0]}]})
    # Only after all four paths and all masks are fixed is native MQM loaded.
    z,a,g=raw(panel);lp=panel.removeprefix('WMT24-');goldraw=json.loads((ROOT/'data'/f'wmt24_{lp}_mqm.json').read_text());assert goldraw['systems']==z['systems'] and goldraw['prompt_ids']==z['prompt_ids']
    gold=np.array([goldraw['mqm'][i] for i in z['prompt_ids']],dtype=float).ravel()[idx[2]]
    for row,mask,target in quality_inputs:row.update(quality(mask,target,score,tie,gold))
    return {'key':[panel,'alphabetical',rep,agg,q],'baseline':baselines,'query':queryrows,'trace':logs,'baseline_masks':masks}


def main(workers):
    protocol=json.loads((ROOT/'review-revision/external-panel-protocol.json').read_text());out=ROOT/'outputs/review-external';out.mkdir(parents=True,exist_ok=True);assert not (out/'results.json').exists()
    assert protocol['reference_priority_numerics']['fixed_point_scale']==10**12
    start=time.monotonic();br=[];qr=[];answers=paths=cases=0
    tasks=[('WMT24-'+lp,r,a,q) for lp in protocol['language_priority'] for r in range(protocol['splits']) for a in protocol['aggregators'] for q in protocol['quantiles']]
    (out/'execution.json').write_text(json.dumps({'status':'RUNNING'},indent=2)+'\n')
    with gzip.open(out/'traces.jsonl.gz','wt',compresslevel=1) as log,multiprocessing.get_context('spawn').Pool(workers) as pool:
        for z in pool.imap(case,tasks,chunksize=2):
            br.extend(z.pop('baseline'));qr.extend(z.pop('query'));answers+=sum(len(p['trace']) for p in z['trace']);paths+=len(z['trace']);cases+=1
            log.write(json.dumps(z,separators=(',',':'),allow_nan=False)+'\n')
            if cases%40==0:print('external cases',cases,'seconds',round(time.monotonic()-start,1),flush=True)
    fields=['risk','selected_coverage','returned_count','queries','active_fraction','panel_fraction','V_star','certificate_gap','realized_regret','replacement_max_risk','replacement_over_alpha_fraction','mqm_observed_return_count','mqm_return_observed_fraction','mqm_return_mean','mqm_matched_k_mean_delta','mqm_annotated_count_delta']
    payload={'protocol':protocol,'baseline_records':br,'query_records':qr,'baseline_cells':summary(br,['dataset','aggregator','q','method'],fields),'query_cells':summary(qr,['dataset','aggregator','q','method','stopping'],fields)}
    (out/'results.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    for name in ['baseline','query']:
        rows=payload[name+'_cells']
        with (out/(name+'_cells.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=sorted(set().union(*(set(x) for x in rows))));w.writeheader();w.writerows(rows)
    receipt={'status':'PASS_FULL_EXECUTION_PENDING_INDEPENDENT_AUDIT','configuration_cases':cases,'query_paths':paths,'recorded_answers':answers,'baseline_records':len(br),'query_records':len(qr),'CRC':'Not run: unequal document groups do not justify existing equal-output-unit guarantee','runtime_seconds':time.monotonic()-start,'runtime_scope':'Cached-score replay'}
    (out/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    try:main(a.workers)
    except BaseException as e:
        out=ROOT/'outputs/review-external';out.mkdir(parents=True,exist_ok=True);(out/'execution.json').write_text(json.dumps({'status':'FAILED','error_type':type(e).__name__,'error':str(e)},indent=2)+'\n');raise

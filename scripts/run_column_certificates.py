"""Full 960-instance offline-column study; frozen NLP protocols are unchanged."""
from pathlib import Path
import argparse, csv, json, math, multiprocessing, time
import numpy as np
from mapping_column_experiments import map_scores, column_order
from query_selection import (aggregate, endpoint_cost, fit_prior, capacity,
                             exact_offline_certificate)
from column_certificate import exact_columns, verify_minimality, certify_subset
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/column-certificates'


def group(task):
    panel,rep,cases=task
    ref,test,seed,_,_=map_scores(panel,rep,'1','right')
    base,hidden=test[:7],test[7:]
    T,N=hidden.shape
    result=[]
    for old,online in cases:
        q=old['q'];k=max(1,round(q*N));B=2*k*7*T//10;b=B//4
        threshold=float(np.sort(aggregate(ref[:7],'median'))[-max(1,round(q*ref.shape[1]))])
        selected=aggregate(base,'median')>=threshold
        p=endpoint_cost(base,threshold,'median');ids=selected & (p>0)
        y=(hidden[:,ids].T<threshold).astype(np.int64)
        m=len(y);free=int(np.sum(selected & (p==0)))
        Q,safe,exclusion=exact_offline_certificate(y.sum(axis=1),T,b)
        assert old['integer_budget']==B and old['threshold']==threshold
        assert old['selected_count']==int(selected.sum())
        assert old['active_selected_items']==m and old['offline_exact_certificate']==Q
        assert old['V_star']==free+capacity(y.sum(axis=1),b)
        prior=fit_prior(ref[:7],ref[7:],base,threshold,p,'median')
        for method,count in online.items():
            order=column_order(method,p,selected,prior,T,seed+rep+99173)
            first=None;a=0
            for n in range(T+1):
                lo,hi=certify_subset(y,b,a)
                if lo==hi:
                    first=n;break
                a |= 1 << int(order[n])
            assert first==count,(panel,rep,q,method,first,count)
        witness=exact_columns(y,b,Q,min(online.values()))
        audit_count=verify_minimality(y,b,witness)
        assert all(n>=witness['K_col'] for n in online.values())
        result.append({'dataset':panel,'split':rep,'q':q,'alpha':.1,'cdf':'right',
                       'reference_fraction':'1','aggregator':'median','stopping':'exact_gap',
                       'N':N,'T':T,'m':m,'m0':free,'bit_budget':b,'V_star':old['V_star'],
                       'Q_entry':Q,'Q_safe':safe,'Q_exclusion':exclusion,
                       **witness,'minimality_predecessor_subsets_checked':audit_count,
                       'score_entry_cost':N*witness['K_col'],
                       'online_column_counts':online,
                       'online_overhead':{meth:n/witness['K_col'] if witness['K_col'] else None
                                          for meth,n in online.items()}})
    return result


def main(workers):
    spec=json.loads((ROOT/'review-revision/certificate-granularity/protocol.json').read_text())
    from hashlib import sha256
    for p,digest in spec['input_bindings'].items():
        assert sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
    old=json.loads((ROOT/'outputs/mapping-column/results.json').read_text())
    geometries=[x for x in old['geometry'] if x['aggregator']=='median' and
                x['reference_fraction']=='1' and x['cdf']=='right']
    columns={}
    for x in old['records']:
        if x['aggregator']=='median' and x['method'].startswith('column_') and x['stopping']=='exact_gap':
            key=(x['dataset'],x['split'],x['q'])
            columns.setdefault(key,{})[x['method']]=x['candidate_columns_touched']
    tasks=[]
    for panel in spec['panels']:
        for rep in range(40):
            cases=[(x,columns[(panel,rep,x['q'])]) for x in geometries
                   if x['dataset']==panel and x['split']==rep]
            assert len(cases)==4 and all(len(v)==3 for _,v in cases)
            tasks.append((panel,rep,cases))
    OUT.mkdir(exist_ok=False)
    (OUT/'protocol.json').write_text(json.dumps(spec,indent=2)+'\n')
    start=time.monotonic();records=[]
    with (OUT/'records.jsonl').open('w') as log:
        with multiprocessing.get_context('spawn').Pool(workers) as pool:
            for batch in pool.imap(group,tasks,chunksize=1):
                for row in batch:
                    records.append(row);log.write(json.dumps(row,separators=(',',':'))+'\n')
                if len(records)%80==0:
                    state={'status':'RUNNING','instances':len(records),'total':960,
                           'seconds':round(time.monotonic()-start,2)}
                    (OUT/'execution.json').write_text(json.dumps(state)+'\n')
                    print(json.dumps(state),flush=True)
    assert len(records)==960
    (OUT/'results.json').write_text(json.dumps({'protocol':spec,'records':records},separators=(',',':'))+'\n')
    summary=[]
    for panel in spec['panels']:
        for q in [.05,.1,.2,.3]:
            cell=[x for x in records if x['dataset']==panel and x['q']==q]
            pos=[x for x in cell if x['K_col']>0]
            row={'dataset':panel,'q':q,'splits':40,'positive_witness_splits':len(pos),
                 'zero_witness_splits':40-len(pos),'mean_K_col':float(np.mean([x['K_col'] for x in cell])),
                 'mean_Q_entry':float(np.mean([x['Q_entry'] for x in cell])),
                 'mean_minimum_panel_fraction':float(np.mean([x['K_col']/x['T'] for x in cell]))}
            for method in ['column_fixed','column_random','column_reference']:
                a=[x['online_overhead'][method] for x in pos]
                row[method+'_mean_count']=float(np.mean([x['online_column_counts'][method] for x in cell]))
                row[method+'_median_ratio']=float(np.median(a)) if a else None
                row[method+'_p90_ratio']=float(np.quantile(a,.9)) if a else None
                row[method+'_max_ratio']=max(a) if a else None
            summary.append(row)
    with (OUT/'cells.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    done={'status':'PASS_EXACT_COLUMN_WITNESSES_AND_FULL_PREDECESSOR_AUDIT',
          'instances':960,'cells':24,'all_existing_column_stops_replayed':2880,
          'exact_witnesses_verified':960,'smaller_subset_exclusion_audited':960,
          'runtime_seconds':time.monotonic()-start,'physical_model_execution':False,
          'human_proof_review':False}
    (OUT/'execution.json').write_text(json.dumps(done,indent=2)+'\n');print(json.dumps(done),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4)
    main(p.parse_args().workers)

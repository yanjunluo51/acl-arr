"""Full six-panel, four-depth, forty-split column cost sensitivity."""
from pathlib import Path
import csv,hashlib,json,math,multiprocessing,time
import numpy as np
from mapping_column_experiments import map_scores,column_order
from query_selection import aggregate,endpoint_cost,fit_prior
from column_certificate import certify_subset
from tolerance_certificates import minimum_gap_certificate
from cost_column_certificates import minimum_cost_columns

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/acceptance-review-implementation'


def group(task):
    panel,rep,cases=task
    ref,test,seed,_,_=map_scores(panel,rep,'1','right')
    base,hidden=test[:7],test[7:];T,N=hidden.shape
    results=[]
    for old,geometry,saved in cases:
        q=old['q'];threshold=geometry['threshold'];budget=old['bit_budget']
        assert threshold==float(np.sort(aggregate(ref[:7],'median'))[-max(1,round(q*ref.shape[1]))])
        selected=aggregate(base,'median')>=threshold;p=endpoint_cost(base,threshold,'median')
        active=selected&(p>0);y=(hidden[:,active].T<threshold).astype(np.int64)
        assert len(y)==old['m'] and N==old['N'] and T==old['T']
        epsilon=math.ceil(.02*int(selected.sum()))
        qeps=minimum_gap_certificate(y.sum(axis=1),T,budget,epsilon)['queries']
        solved=minimum_cost_columns(y,budget,epsilon,[old['Q_entry'],qeps],old['subset_mask'])
        assert solved['column_counts'][0][0]==old['K_col']
        prior=fit_prior(ref[:7],ref[7:],base,threshold,p,'median')
        orders={method:column_order(method,p,selected,prior,T,seed+rep+99173)
                for method in ['column_fixed','column_random','column_reference']}
        for t,stop in enumerate(['exact_gap','two_percent_gap']):
            for j,profile in enumerate(['uniform','ascending','descending']):
                prices=solved['prices'][j];minimum=solved['minimum_costs'][t][j]
                row={'dataset':panel,'split':rep,'q':q,'alpha':.1,'stopping':stop,'epsilon':0 if t==0 else epsilon,
                     'N':N,'m':len(y),'T':T,'bit_budget':budget,'profile':profile,'price_scale':2*T-1,
                     'prices':prices,'minimum_cost':minimum,'minimum_normalized_cost':minimum/(2*T-1),
                     'minimum_columns':solved['column_counts'][t][j],
                     'subset_mask':solved['subset_masks'][t][j],
                     'uniform_minimum_columns':solved['column_counts'][t][0],
                     'subsets_evaluated':solved['subsets_evaluated'],
                     'cheaper_subsets_checked':solved['cheaper_subsets_independently_checked']}
                for method,order in orders.items():
                    st=saved[method,stop];count=st['candidate_columns_touched'];subset=sum(1<<int(c) for c in order[:count])
                    lo,hi=certify_subset(y,budget,subset)
                    assert hi-lo<=row['epsilon'] and st['queries']==count*N
                    if count:
                        previous=sum(1<<int(c) for c in order[:count-1]);plo,phi=certify_subset(y,budget,previous)
                        assert phi-plo>row['epsilon']
                    paid=sum(prices[int(c)] for c in order[:count]);assert paid>=minimum
                    row[method+'_cost']=paid
                    row[method+'_cost_ratio']=paid/minimum if minimum else None
                results.append(row)
    return results


def main():
    input_files=['outputs/column-certificates/results.json','outputs/mapping-column/results.json',
                 'data/rb2_ranked_panel.json','data/wmt23_metric_panel.json',
                 'data/wmt24_en-de_panel.json','data/wmt24_en-es_panel.json','data/wmt24_ja-zh_panel.json']
    bindings={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in input_files}
    old=json.loads((ROOT/input_files[0]).read_text())['records']
    mapping=json.loads((ROOT/input_files[1]).read_text())
    geo={(v['dataset'],v['split'],v['q']):v for v in mapping['geometry'] if v['aggregator']=='median' and v['reference_fraction']=='1' and v['cdf']=='right'}
    stops={}
    for v in mapping['records']:
        if v['aggregator']=='median' and v['method'].startswith('column_'):
            stops.setdefault((v['dataset'],v['split'],v['q']),{})[v['method'],v['stopping']]=v
    panels=list(dict.fromkeys(v['dataset'] for v in old));tasks=[]
    for panel in panels:
        for rep in range(40):
            cases=[(v,geo[panel,rep,v['q']],stops[panel,rep,v['q']]) for v in old if v['dataset']==panel and v['split']==rep]
            assert len(cases)==4;tasks.append((panel,rep,cases))
    protocol={'status':'FROZEN_BEFORE_COST_REPLAY','panels':panels,'splits':40,'depths':[.05,.1,.2,.3],
              'pooling':'median','cdf':'right','reference_fraction':'1','alpha':.1,'stops':['exact_gap','two_percent_gap'],
              'price_profiles':['uniform','ascending','descending'],'prices':'[2T-1]*T, [T+2r], reverse [T+2r]; common total T(2T-1)',
              'interpretation':'Declared additive cost sensitivity, not measured scoring time, provider fees or new online policy.',
              'input_bindings':bindings}
    (OUT/'cost-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    records=[];start=time.monotonic()
    with multiprocessing.get_context('spawn').Pool(3) as pool:
        for batch in pool.imap(group,tasks,chunksize=1):
            records.extend(batch)
            if len(records)%480==0:print(json.dumps({'records':len(records),'total':5760,'seconds':time.monotonic()-start}),flush=True)
    assert len(records)==5760
    cells=[]
    for panel in panels:
        for q in [.05,.1,.2,.3]:
            for stop in ['exact_gap','two_percent_gap']:
                for profile in ['uniform','ascending','descending']:
                    rows=[v for v in records if (v['dataset'],v['q'],v['stopping'],v['profile'])==(panel,q,stop,profile)]
                    assert len(rows)==40
                    row={'dataset':panel,'q':q,'stopping':stop,'profile':profile,'splits':40,
                         'positive_cost_splits':sum(v['minimum_cost']>0 for v in rows),
                         'cost_optimum_uses_more_columns':sum(v['minimum_columns']>v['uniform_minimum_columns'] for v in rows)}
                    for field in ['minimum_normalized_cost','minimum_columns','uniform_minimum_columns']:
                        row['mean_'+field]=float(np.mean([v[field] for v in rows]))
                    for method in ['column_fixed','column_random','column_reference']:
                        ratios=[v[method+'_cost_ratio'] for v in rows if v[method+'_cost_ratio'] is not None]
                        row[method+'_mean_cost_ratio']=float(np.mean(ratios)) if ratios else None
                    cells.append(row)
    (OUT/'cost-results.json').write_text(json.dumps({'protocol':protocol,'records':records,'cells':cells},allow_nan=False,separators=(',',':'))+'\n')
    with (OUT/'cost-cells.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(cells[0]));writer.writeheader();writer.writerows(cells)
    for n,h in bindings.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
    receipt={'status':'PASS_COMPLETE_COST_SENSITIVITY_AND_CHEAPER_SUBSET_AUDIT','instances':960,'records':len(records),'cells':len(cells),
             'all_uniform_exact_minima_match_existing_column_witnesses':True,'new_online_policy':False,'real_scoring_cost_measurements':False,
             'original_stops_verified':5760,'seconds':time.monotonic()-start}
    (OUT/'cost-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()

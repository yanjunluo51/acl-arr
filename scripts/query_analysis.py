"""Post-protocol descriptive analyses; never used for acquisition or stopping."""
from pathlib import Path
import gzip,json,random,statistics
import numpy as np
from query_selection import aggregate
ROOT=Path(__file__).resolve().parents[1]


def avg(v):return statistics.fmean(v) if v else None


def main():
    x=json.loads((ROOT/'outputs/query_metrics.json').read_text())
    groups={};paired={}
    for r in x['query_records']:
        key=(r['dataset'],r['aggregator'],r['q'],r['stopping'])
        paired.setdefault(key,{}).setdefault(r['split'],{})[r['method']]=r
    for key,by_split in sorted(paired.items()):
        rows=[]
        for method in x['protocol']['acquisition_methods']:
            all_rows=[v[method] for v in by_split.values()]
            nontrivial=[v[method] for v in by_split.values() if v['fixed']['queries']>0]
            wins=sum(v[method]['queries']<min(v[m]['queries'] for m in ['fixed','random','largest_width']) for v in by_split.values())
            rows.append({'method':method,'zero_query_fraction':avg([r['queries']==0 for r in all_rows]),
                         'nontrivial_splits':len(nontrivial),
                         'nontrivial_mean_queries':avg([r['queries'] for r in nontrivial]),
                         'nontrivial_active_fraction':avg([r['active_fraction'] for r in nontrivial]),
                         'mean_queries':avg([r['queries'] for r in all_rows]),
                         'mean_active_fraction':avg([r['active_fraction'] for r in all_rows]),
                         'mean_panel_fraction':avg([r['panel_fraction'] for r in all_rows]),
                         'mean_selected_coverage':avg([r['selected_coverage'] for r in all_rows]),
                         'mean_actual_regret':avg([r['realized_regret'] for r in all_rows]),
                         'strict_wins_over_all_three_simple':wins,
                         'mean_exact_certificate':avg([r['offline_exact_certificate'] for r in all_rows]) if key[1]=='median' else None,
                         'exact_queries_minus_offline':avg([r['queries']-r['offline_exact_certificate'] for r in all_rows]) if key[1]=='median' and key[3]=='exact_gap' else None})
        groups['|'.join(map(str,key))]={'dataset':key[0],'aggregator':key[1],'q':key[2],'stopping':key[3],'methods':rows}
    violations=[]
    for dataset in x['protocol']['panels']:
      for agg in x['protocol']['aggregators']:
       for q in x['protocol']['quantiles']:
        rs=[r for r in x['baseline_records'] if r['dataset']==dataset and r['aggregator']==agg and r['q']==q]
        violations.append({'dataset':dataset,'aggregator':agg,'q':q,
                           'crc_over_budget_splits':sum(r['risk']>0.1+1e-12 for r in rs if r['method']=='envelope_crc'),
                           'batch_violations':sum(r['risk']>0.1+1e-12 for r in rs if r['method']!='envelope_crc')})
    # Matched-throughput quality: RB only. These labels are never solver inputs.
    blob=json.loads((ROOT/'data/rb2_ranked_panel.json').read_text());models=blob['models'];gids=blob['prompt_ids']
    raw=np.array([blob['scores'][m][pid] for m in models for pid in gids]).reshape(len(models),-1)
    consensus_cache={};quality=[]
    for rep in range(40):
        order=list(range(len(gids)));random.Random(20260815+rep).shuffle(order)
        third=len(order)//3;groups0=order[:third];groups2=order[2*third:]
        refidx=np.array([a*4+b for a in groups0 for b in range(4)])
        testidx=np.array([a*4+b for a in groups2 for b in range(4)])
        mapped=np.array([np.searchsorted(np.sort(raw[m,refidx]),raw[m,testidx],side='right')/len(refidx) for m in range(7)])
        mapped_ref=np.array([np.searchsorted(np.sort(raw[m,refidx]),raw[m,refidx],side='right')/len(refidx) for m in range(7)])
        tie=np.random.default_rng(20260815+rep+700001).permutation(len(testidx))
        labels=np.tile([1,0,0,0],len(groups2))
        for agg in ['median','mean']:
            c=aggregate(mapped,agg);cref=aggregate(mapped_ref,agg)
            for q in x['protocol']['quantiles']:
                t=np.sort(cref)[-max(1,round(q*len(refidx)))]
                consensus_cache[rep,agg,q]=(c>=t,np.lexsort((tie,c)),labels)
    with gzip.open(ROOT/'outputs/query_traces.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line);dataset,agg,rep,q,method=z['key']
            if dataset!='RewardBench2':continue
            selected,rank,labels=consensus_cache[rep,agg,q]
            for stopping,s in [('two_percent_gap',z['two_percent_stop']),('exact_gap',z['exact_stop'])]:
                keep=selected & np.asarray(s['mask'],dtype=bool);K=int(keep.sum())
                compare=rank[-K:] if K else np.array([],dtype=int)
                precision=float(labels[keep].mean()) if K else None
                topk_precision=float(labels[compare].mean()) if K else None
                quality.append({'dataset':dataset,'aggregator':agg,'split':rep,'q':q,'method':method,'stopping':stopping,'K':K,
                                'precision':precision,'same_K_score_precision':topk_precision,
                                'precision_delta':precision-topk_precision if K else None,
                                'preferred_yield':int(labels[keep].sum())})
    grouped_quality=[]
    for agg in ['median','mean']:
      for q in x['protocol']['quantiles']:
       for method in x['protocol']['acquisition_methods']:
        for stop in ['two_percent_gap','exact_gap']:
         rs=[r for r in quality if (r['aggregator'],r['q'],r['method'],r['stopping'])==(agg,q,method,stop)]
         grouped_quality.append({'aggregator':agg,'q':q,'method':method,'stopping':stop,'splits':len(rs),
                                 **{k:avg([r[k] for r in rs if r[k] is not None]) for k in ['K','precision','same_K_score_precision','precision_delta','preferred_yield']}})
    result={'scope':'Descriptive post-protocol diagnostics; overlapping split summaries are not population inference; no method tuning.',
            'cells':list(groups.values()),'baseline_budget_checks':violations,
            'quality_records':quality,'quality_cells':grouped_quality,
            'same_K_baseline_certificate':None,
            'same_K_ties':'same fixed label-blind seed as selected retention tie priorities'}
    (ROOT/'outputs/query_analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('descriptive cells',len(groups),'quality records',len(quality))


if __name__=='__main__':main()

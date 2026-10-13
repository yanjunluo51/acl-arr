"""Independent raw-label recalculation, with no experiment-loader imports."""
from pathlib import Path
import gzip,hashlib,json,random
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/acceptance-review-implementation'


def main():
    result=json.loads((OUT/'wmt23-quality-results.json').read_text())
    panel=json.loads((ROOT/'data/wmt23_metric_panel.json').read_text())
    labels={}
    for line in (OUT/'wmt23-official/human-scores/en-de.mqm.seg.score').read_text().splitlines():
        s,v=line.split();labels.setdefault(s,[]).append(float(v) if v!='None' else float('nan'))
    paths={}
    with gzip.open(ROOT/'outputs/query_traces.jsonl.gz','rt') as f:
        for line in f:
            v=json.loads(line)
            if v['key'][0].startswith('WMT23'):
                paths[tuple(v['key'])]=v
    context={};checked=0;baselines=0
    for row in result['records']:
        dataset,agg,rep,q=(row[k] for k in ['dataset','aggregator','split','q'])
        key=dataset,agg,rep,q
        if key not in context:
            systems=[s for s in panel['systems'] if dataset!='WMT23_without_synthetic_ref' or s!='synthetic_ref']
            columns=[panel['systems'].index(s) for s in systems]
            groups=list(range(557));random.Random(87000+rep).shuffle(groups)
            reference,test=groups[:185],groups[370:]
            raw=np.array([[panel['scores'][m][panel['prompt_ids'][i]][j] for i in range(557) for j in columns] for m in panel['models']])
            rr=np.array([i*len(systems)+j for i in reference for j in range(len(systems))])
            tt=np.array([i*len(systems)+j for i in test for j in range(len(systems))])
            full=np.array([np.searchsorted(np.sort(v[rr]),v[tt],side='right')/len(rr) for v in raw])
            mapped=full[:7]
            mappedref=np.array([np.searchsorted(np.sort(v[rr]),v[rr],side='right')/len(rr) for v in raw[:7]])
            def consensus(values):
                if agg=='median':return np.median(values,axis=0)
                value=np.zeros(values.shape[1])
                for v in values:value+=v
                return value/len(values)
            if agg=='median':c,cr=consensus(mapped),consensus(mappedref)
            else:
                c=np.zeros(mapped.shape[1]);cr=np.zeros(mappedref.shape[1])
                for v in mapped:c+=v
                for v in mappedref:cr+=v
                c/=7;cr/=7
            threshold=sorted(cr)[-max(1,round(q*len(rr)))];selected=c>=threshold
            endpoint=np.zeros(len(tt),int);cost=np.zeros(len(tt),int)
            for j in range(7):
                swapped=mapped.copy();swapped[j]=np.where(selected,0.,1.)
                endpoint+=((consensus(swapped)>=threshold)!=selected)
                for candidate in full[7:]:
                    swapped[j]=candidate
                    cost+=((consensus(swapped)>=threshold)!=selected)
            gold=np.array([labels[s][i] if s in labels else np.nan for i in test for s in systems])
            tie=np.random.default_rng(87000+rep+700001).permutation(len(tt))
            order=sorted(range(len(tt)),key=lambda i:(-c[i],tie[i]))
            annotated_order=[i for i in order if np.isfinite(gold[i])]
            budget=(2*max(1,round(q*len(tt)))*7*(len(full)-7))//10
            context[key]=selected,gold,order,annotated_order,endpoint,cost,tie,budget,len(full)-7
        selected,gold,order,annotated_order,endpoint,cost,tie,budget,T=context[key]
        if row['stopping']=='baseline':
            values=T*endpoint if row['method']=='zero_query' else cost
            ranked=sorted(np.flatnonzero(selected),key=lambda i:(int(values[i]),tie[i]))
            keep=np.zeros(len(selected),bool);used=0
            for i in ranked:
                if used+int(values[i])>budget:break
                used+=int(values[i]);keep[i]=True
            baselines+=1
        else:
            v=paths[dataset,agg,rep,q,row['method']]
            field='exact_stop' if row['stopping']=='exact_gap' else 'two_percent_stop'
            keep=selected & np.asarray(v[field]['mask'],bool)
        observed=np.flatnonzero(keep & np.isfinite(gold));K=len(observed)
        assert row['K']==int(keep.sum()) and row['K_annotated']==K
        mean=float(np.mean(gold[observed])) if K else None
        matched=float(np.mean(gold[annotated_order[:K]])) if K else None
        assert mean==row['MQM'] and matched==row['label_matched_MQM']
        assert row['label_matched_delta']==(mean-matched if K else None)
        checked+=1
    assert checked==6400 and baselines==1280
    fields=['queries','K','K_annotated','label_coverage','MQM','label_matched_MQM','label_matched_delta','total_K_comparator_annotated','total_K_comparator_MQM']
    checked_cells=0
    for cell in result['cells']:
        rows=[v for v in result['records'] if all(v[k]==cell[k] for k in ['dataset','aggregator','q','method','stopping'])]
        for field in fields:
            values=[v[field] for v in rows if v[field] is not None]
            expected=float(np.mean(values)) if values else None
            assert expected==cell[field]
            checked_cells+=1
    receipt={'status':'PASS_INDEPENDENT_RAW_MQM_AND_FIXED_MASK_CHECKS','query_records_recomputed':checked-baselines,'baseline_records_recomputed':baselines,'summary_values_recomputed':checked_cells,
             'population_inference':False,'human_annotation_verified':False}
    (OUT/'wmt23-quality-independent.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()

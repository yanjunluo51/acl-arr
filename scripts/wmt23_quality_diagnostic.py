"""Label-only analysis of the complete frozen original WMT23 acquisition paths."""
from pathlib import Path
import csv, gzip, hashlib, json, math
import numpy as np
from review_experiments import mapped_panel
from query_selection import aggregate, endpoint_cost, all_flips, prefix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'review-revision/acceptance-review-implementation'
DATA = OUT/'wmt23-official'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def score_file(path):
    result = {}
    for line in path.read_text().splitlines():
        system, value = line.split()
        result.setdefault(system, []).append(np.nan if value == 'None' else float(value))
    return result


def main():
    panel = json.loads((ROOT/'data/wmt23_metric_panel.json').read_text())
    systems, ids = panel['systems'], panel['prompt_ids']
    compared = 0
    for metric in panel['models']:
        raw = score_file(DATA/'metric-scores/en-de'/f'{metric}-refA.seg.score')
        for j, system in enumerate(systems):
            assert len(raw[system]) == len(ids)
            for i, pid in enumerate(ids):
                assert pid == f'seg{i:04d}'
                assert raw[system][i] == panel['scores'][metric][pid][j], (metric, system, i)
                compared += 1
    assert compared == 173784
    assert len((DATA/'sources/en-de.txt').read_text().splitlines()) == len(ids)
    gold = score_file(DATA/'human-scores/en-de.mqm.seg.score')
    assert all(len(gold[s]) == len(ids) for s in systems if s in gold)
    aligned = np.array([[gold[s][i] if s in gold else np.nan for s in systems]
                        for i in range(len(ids))], dtype=float)
    assert 'synthetic_ref' not in gold
    assert np.isnan(aligned[:, systems.index('synthetic_ref')]).all()
    assert np.isfinite(aligned).sum() == 5520
    alignment = {'status':'PASS_EXACT_SYSTEM_AND_FULL_SCORE_ORDER_ALIGNMENT',
                 'official_metric_entries_matched':compared, 'segments':len(ids),
                 'systems':systems, 'annotated_outputs':5520,'possible_outputs':len(ids)*len(systems),
                 'missing_systems':[s for s in systems if s not in gold],
                 'official_files_manifest_sha256':sha(OUT/'wmt23-official-files.json'),
                 'panel_sha256':sha(ROOT/'data/wmt23_metric_panel.json'),
                 'gold_sha256':sha(DATA/'human-scores/en-de.mqm.seg.score'),
                 'higher_is_better':True,
                 'limitations':'Mechanical identity/order validation; no human reannotation or redistribution authorization.'}
    (OUT/'wmt23-label-alignment.json').write_text(json.dumps(alignment,indent=2)+'\n')
    records, cache = [], {}
    old = json.loads((ROOT/'outputs/query_metrics.json').read_text())
    old_query = {(v['dataset'],v['aggregator'],v['split'],v['q'],v['method'],v['stopping']):v for v in old['query_records']}
    bindings = {p:sha(ROOT/p) for p in ['data/wmt23_metric_panel.json','outputs/query_traces.jsonl.gz','outputs/query_metrics.json']}

    def context(dataset, agg, rep, q):
        key = dataset, agg, rep, q
        if key not in cache:
            mapped, g, seed, idx = mapped_panel(dataset, rep)
            ref, _, test = mapped
            base, hidden = test[:7], test[7:]
            threshold = np.sort(aggregate(ref[:7],agg))[-max(1,round(q*ref.shape[1]))]
            consensus = aggregate(base,agg)
            selected = consensus >= threshold
            p = endpoint_cost(base,threshold,agg)
            cost = all_flips(base,hidden,threshold,agg).sum(axis=0)
            tie = np.random.default_rng(seed+rep+700001).permutation(test.shape[1])
            cols = [j for j,s in enumerate(systems) if dataset != 'WMT23_without_synthetic_ref' or s != 'synthetic_ref']
            labels = aligned[:,cols].reshape(-1)[idx[2]]
            budget = (2*max(1,round(q*test.shape[1]))*7*len(hidden))//10
            cache[key] = selected, p, cost, tie, consensus, labels, budget, len(hidden)
        return cache[key]

    def add(dataset,agg,rep,q,method,stop,mask,queries,expected=None):
        selected,p,cost,tie,c,labels,b,T = context(dataset,agg,rep,q)
        mask=np.asarray(mask,dtype=bool)
        keep=selected & mask
        assert int(cost[mask].sum())<=b
        annotated=keep & np.isfinite(labels)
        K,Klab=int(keep.sum()),int(annotated.sum())
        order=np.lexsort((tie,-c))
        available_order=order[np.isfinite(labels[order])]
        comparator=available_order[:Klab]
        full_comparator=order[:K]
        full_annotated=full_comparator[np.isfinite(labels[full_comparator])]
        assert len(comparator)==Klab
        if expected is not None:
            assert expected['queries']==queries and expected['returned_count']==K
        quality=float(labels[annotated].mean()) if Klab else None
        matched=float(labels[comparator].mean()) if Klab else None
        records.append({'dataset':dataset,'aggregator':agg,'split':rep,'q':q,'method':method,'stopping':stop,
                        'queries':queries,'K':K,'K_annotated':Klab,'label_coverage':Klab/K if K else None,
                        'MQM':quality,'label_matched_MQM':matched,
                        'label_matched_delta':quality-matched if Klab else None,
                        'total_K_comparator_annotated':len(full_annotated),
                        'total_K_comparator_MQM':float(labels[full_annotated].mean()) if len(full_annotated) else None})

    baseline_done=set(); path_count=0
    with gzip.open(ROOT/'outputs/query_traces.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line);dataset,agg,rep,q,method=z['key']
            if not dataset.startswith('WMT23'):continue
            selected,p,cost,tie,c,labels,b,T=context(dataset,agg,rep,q)
            key=dataset,agg,rep,q
            if key not in baseline_done:
                for baseline,w,queries in [('zero_query',T*p,0),('full_information',cost,len(cost)*T)]:
                    mask=(p==0).copy();rows=np.flatnonzero(selected)
                    mask[rows[prefix(w[rows],b,tie[rows])]]=True
                    add(dataset,agg,rep,q,baseline,'baseline',mask,queries)
                baseline_done.add(key)
            for stop,field in [('two_percent_gap','two_percent_stop'),('exact_gap','exact_stop')]:
                s=z[field];expected=old_query[dataset,agg,rep,q,method,stop]
                add(dataset,agg,rep,q,method,stop,s['mask'],s['queries'],expected)
            path_count+=1
    assert len(baseline_done)==640 and path_count==2560 and len(records)==6400
    keys=sorted({(v['dataset'],v['aggregator'],v['q'],v['method'],v['stopping']) for v in records})
    cells=[]
    for key in keys:
        rows=[v for v in records if (v['dataset'],v['aggregator'],v['q'],v['method'],v['stopping'])==key]
        assert len(rows)==40
        cell=dict(zip(['dataset','aggregator','q','method','stopping'],key));cell['splits']=40
        for field in ['queries','K','K_annotated','label_coverage','MQM','label_matched_MQM','label_matched_delta','total_K_comparator_annotated','total_K_comparator_MQM']:
            values=[v[field] for v in rows if v[field] is not None]
            cell[field]=float(np.mean(values)) if values else None
        cell['positive_labeled_splits']=sum(v['K_annotated']>0 for v in rows)
        cells.append(cell)
    (OUT/'wmt23-quality-results.json').write_text(json.dumps({'alignment':alignment,'input_bindings':bindings,'records':records,'cells':cells,
        'scope':'Post hoc MQM diagnostic of fixed original masks. Means concern labeled outputs; matched comparator uses the same labeled count. No fitting, reselection, imputation or population inference.'},allow_nan=False,separators=(',',':'))+'\n')
    with (OUT/'wmt23-quality-cells.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(cells[0]));writer.writeheader();writer.writerows(cells)
    for p,h in bindings.items():assert sha(ROOT/p)==h
    receipt={'status':'PASS_COMPLETE_FIXED_MASK_WMT23_QUALITY_DIAGNOSTIC','paths':path_count,'records':len(records),'cells':len(cells),
             'original_masks_and_query_counts_preserved':True,'new_model_inference':False,'quality_used_for_tuning':False,'missing_labels_imputed':False}
    (OUT/'wmt23-quality-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()

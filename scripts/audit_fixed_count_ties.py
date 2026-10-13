"""Cached-score diagnostic of the unchanged native-index fixed-count rule.

This is a baseline-list diagnostic, not a replacement-risk rerun or a new
quality result for certified retention. No candidate test scores are read.
"""
from pathlib import Path
import csv,json,random
import numpy as np
from query_selection import aggregate,features,endpoint_cost,prefix
from analyze import topk
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/fixed-count-tie-audit'

def main():
    blob=json.loads((ROOT/'data/rb2_ranked_panel.json').read_text())
    gids=blob['prompt_ids'];models=blob['models'][:7]
    raw=np.asarray([[blob['scores'][m][i] for i in gids] for m in models],dtype=float).reshape(7,-1)
    records=[];permutation_checks=0
    for rep in range(40):
        order=list(range(len(gids)));random.Random(20260815+rep).shuffle(order)
        third=len(order)//3
        ref_ids=np.asarray([i*4+j for i in order[:third] for j in range(4)])
        test_ids=np.asarray([i*4+j for i in order[2*third:] for j in range(4)])
        ref=np.asarray([np.searchsorted(np.sort(row[ref_ids]),row[ref_ids],side='right')/len(ref_ids) for row in raw])
        base=np.asarray([np.searchsorted(np.sort(row[ref_ids]),row[test_ids],side='right')/len(ref_ids) for row in raw])
        N=len(test_ids);label=np.tile([1,0,0,0],N//4).astype(bool)
        tie=np.random.default_rng(20260815+rep+700001).permutation(N)
        perm=np.random.default_rng(20260815+rep+880001).permutation(N)
        for agg in ['median','mean']:
            consensus=aggregate(base,agg);refcons=aggregate(ref,agg)
            for q in [.05,.1,.2,.3]:
                k=max(1,round(q*N));t=np.sort(refcons)[-max(1,round(q*len(ref_ids)))];p=endpoint_cost(base,t,agg)
                native=topk(consensus,k)
                blinded=np.zeros(N,dtype=bool);blinded[np.lexsort((tie,consensus))[-k:]]=True
                boundary=np.sort(consensus)[-k];same=consensus==boundary
                strictly_above=int(np.sum(consensus>boundary));needed=k-strictly_above
                # Covariance under item reindexing for the main method's
                # features and zero-query solver, with priorities transported.
                assert np.array_equal(features(base[:,perm],t,p[perm],agg),features(base,t,p,agg)[perm])
                selected=consensus>=t;B=(2*k*49)//10
                def initial(bs,pr,ss):
                    keep=(pr==0).copy();ids=np.flatnonzero(ss)
                    keep[ids[prefix((7*pr)[ids],B,bs[ids])]]=True
                    return keep
                assert np.array_equal(initial(tie[perm],p[perm],selected[perm]),initial(tie,p,selected)[perm])
                permutation_checks+=1
                records.append({'split':rep,'aggregator':agg,'q':q,'N':N,'k':k,
                    'boundary_tie_count':int(same.sum()),'slots_from_boundary_tie':needed,
                    'tie_is_split':0<needed<int(same.sum()),
                    'native_preferred_count':int(label[native].sum()),
                    'label_blind_preferred_count':int(label[blinded].sum()),
                    'native_minus_label_blind_preferred_count':int(label[native].sum())-int(label[blinded].sum()),
                    'list_symmetric_difference':int(np.sum(native!=blinded))})
    OUT.mkdir(exist_ok=False)
    with (OUT/'records.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    cells=[]
    for agg in ['median','mean']:
        for q in [.05,.1,.2,.3]:
            a=[x for x in records if x['aggregator']==agg and x['q']==q]
            cells.append({'aggregator':agg,'q':q,'splits':len(a),'split_tie_cases':sum(x['tie_is_split'] for x in a),
                'different_list_cases':sum(x['list_symmetric_difference']>0 for x in a),
                'mean_native_minus_label_blind_preferred_count':float(np.mean([x['native_minus_label_blind_preferred_count'] for x in a])),
                'mean_list_symmetric_difference':float(np.mean([x['list_symmetric_difference'] for x in a]))})
    summary={'status':'PASS_SCOPED_FIXED_COUNT_TIE_DIAGNOSTIC','records':len(records),'permutation_checks':permutation_checks,
        'cells':cells,'original_baseline_unchanged':True,'candidate_test_scores_read':False,
        'scope':'Original pool, right ECDF, all 40 RewardBench splits and four depths; baseline-list sensitivity only, not committed masks or replacement-risk comparison.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

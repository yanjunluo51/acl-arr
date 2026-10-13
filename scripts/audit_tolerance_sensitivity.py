"""Independent sorted-cost verification of each new mask and first stop.

No Numba histogram or gap-witness formula is used to verify stopping. The
protocol's score reduction is shared to preserve its floating tie convention.
"""
import base64
from fractions import Fraction
import gzip
import json
from pathlib import Path
import statistics

import numpy as np
from mapping_column_experiments import map_scores
from query_selection import aggregate, endpoint_cost

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/tolerance-sensitivity'


def sorted_capacity(cost,b):
    return int(np.count_nonzero(np.cumsum(np.sort(cost),dtype=np.int64)<=b))


def original_paths():
    with gzip.open(ROOT/'outputs/query_traces.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line)
            yield tuple(z['key']),z['trace']
    with gzip.open(ROOT/'outputs/review-external/traces.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line);panel,pool,rep,agg,q=z['key']
            for p in z['trace']:
                yield (panel,agg,rep,q,p['method']),p['trace']


def main():
    result=json.loads((OUT/'results.json').read_text())
    rows=result['records'];spec=result['protocol']
    records={}
    for r in rows:
        key=(r['dataset'],r['aggregator'],r['split'],r['q'],r['method'])
        records.setdefault(key,{})[r['tau']]=r
    masks={}
    with gzip.open(OUT/'stopping_masks.jsonl.gz','rt') as f:
        for line in f:
            z=json.loads(line);masks[tuple(z['key'])]=z
    assert len(records)==7680 and len(masks)==46080
    last_config=None;checked=pred=0
    for key,trace in original_paths():
        panel,agg,rep,q,method=key
        if key[:4]!=last_config:
            ref,test,seed,_,_=map_scores(panel,rep,'1','right')
            base,hidden=test[:7],test[7:]
            T,N=hidden.shape;H=7*T;k=max(1,round(q*N));b=2*k*H//10
            threshold=np.sort(aggregate(ref[:7],agg))[-max(1,round(q*ref.shape[1]))]
            selected=aggregate(base,agg)>=threshold
            p=endpoint_cost(base,threshold,agg)
            full=np.zeros((T,N),dtype=np.int64)
            for r in range(T):
                for member in range(7):
                    replacement=base.copy();replacement[member]=hidden[r]
                    full[r]+=(aggregate(replacement,agg)>=threshold)!=selected
            cost=full.sum(axis=0)
            V=sorted_capacity(cost[selected],b)
            tie=np.random.default_rng(seed+rep+700001).permutation(N)
            last_config=key[:4]
        rr=records.pop(key)
        tr=np.asarray(trace,dtype=np.int64).reshape(-1,3)
        if len(tr):assert np.array_equal(full[tr[:,0],tr[:,1]],tr[:,2])
        targets={r['queries'] for r in rr.values()}
        targets.update(r['queries']-1 for r in rr.values() if r['queries']>0)
        lower=np.zeros(N,dtype=np.int64);upper=T*p.copy();cursor=0;states={}
        for step in sorted(targets):
            block=tr[cursor:step]
            if len(block):
                np.add.at(lower,block[:,1],block[:,2])
                np.add.at(upper,block[:,1],block[:,2]-p[block[:,1]])
            cursor=step
            assert np.all(lower<=cost) and np.all(cost<=upper)
            vlo=sorted_capacity(upper[selected],b);vhi=sorted_capacity(lower[selected],b)
            assert vlo<=V<=vhi
            states[step]=(vlo,vhi)
            if step in {r['queries'] for r in rr.values()}:
                ids=np.flatnonzero(selected)
                order=np.lexsort((tie[ids],upper[ids]))
                accepted=ids[order[np.cumsum(upper[ids[order]],dtype=np.int64)<=b]]
                expected=(p==0).copy();expected[accepted]=True
                for tau,r in rr.items():
                    if r['queries']!=step:continue
                    packed=masks.pop((*key,tau))
                    mask=np.unpackbits(np.frombuffer(base64.b64decode(packed['mask_packbits_base64']),dtype=np.uint8))[:N].astype(bool)
                    assert np.array_equal(mask,expected)
                    assert int(np.sum(mask & selected))==r['returned_count']==vlo
                    assert vhi==r['V_upper'] and vhi-vlo==r['certificate_gap']
                    assert int(cost[mask].sum())==r['true_cost']
                    assert int(upper[mask].sum())==r['upper_cost']<=b
                    e=Fraction(tau);S=int(selected.sum())
                    eps=(e.numerator*S+e.denominator-1)//e.denominator
                    assert eps==r['epsilon'] and vhi-vlo<=eps
                    assert V-vlo==r['realized_regret']<=eps
                    assert r['risk']==r['true_cost']/(2*k*H)<=.1
                    if step:
                        prev=states[step-1]
                        assert prev[1]-prev[0]>eps
                        pred+=1
                    checked+=1
        assert states[len(tr)][0]==states[len(tr)][1]==V
        counts=[rr[t]['queries'] for t in spec['tolerances']]
        assert counts==sorted(counts,reverse=True)
        if checked%1920==0:print('verified stop records',checked,flush=True)
    assert not records and not masks and checked==46080
    groups={}
    for r in rows:
        key=(r['dataset'],r['aggregator'],r['q'],r['method'],r['tau'])
        groups.setdefault(key,[]).append(r)
    for c in result['cells']:
        key=(c['dataset'],c['aggregator'],c['q'],c['method'],c['tau'])
        group=groups.pop(key)
        for field in ['queries','active_fraction','panel_fraction','zero_query','returned_count','selected_coverage',
                      'certificate_gap','realized_regret','epsilon','effective_tolerance','saving_from_exact',
                      'offline_gap_certificate','query_to_gap_witness']:
            values=[r[field] for r in group if r[field] is not None]
            expected=statistics.fmean(values) if values else None
            assert expected==c[field] and len(values)==c[field+'_defined_splits']
    assert not groups
    receipt={'status':'PASS_INDEPENDENT_SORTED_COST_STOPPING_AND_MASK_CHECKS',
             'stopping_masks_checked':checked,'positive_query_predecessors_checked':pred,
             'summary_cells_reaggregated':1152,'budget_violations':0,
             'mean_accumulation':'original left-to-right protocol',
             'independent_of_numba_histograms':True,'scope':'Saved panels and new fixed-path sensitivity, not human proof certification.'}
    (OUT/'independent-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()

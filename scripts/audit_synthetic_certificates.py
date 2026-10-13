"""Replay every synthetic observation and first stopping state independently."""
from pathlib import Path
import argparse,gzip,json,math
import numpy as np
from column_certificate import capacity_sorted,exact_columns,verify_minimality
from query_selection import aggregate,endpoint_cost,flips,exact_offline_certificate


def main(out):
    z=json.loads((out/'results.json').read_text())
    geos={}
    for g in z['geometry']:geos.setdefault(g['key'],{})[g['bit_budget']]=g
    panels={};stops=0;paths=0;answers=0
    with gzip.open(out/'traces.jsonl.gz','rt') as f:
        for line in f:
            row=json.loads(line);key=row['key']
            if key not in panels:
                p=np.load(out/'inputs'/f'{key}.npz')
                base=p['base'];hidden=p['candidates'];selected=aggregate(base,'median')>=.5
                endpoints=endpoint_cost(base,.5,'median')
                # Explicit M-swap path verifies the shortcut opposition costs.
                values=np.array([[flips(base[:,i],hidden[c,i],.5,'median')
                                  for i in range(base.shape[1])] for c in range(len(hidden))])
                panels[key]=(base,hidden,selected,endpoints,values)
            base,hidden,selected,p,values=panels[key]
            N=base.shape[1];T=len(hidden);eps=math.ceil(.02*selected.sum())
            column=row['method'].startswith('column_')
            if column:
                states=[(row['bit_budget']*4,row['tolerant'],'two_percent_gap'),
                        (row['bit_budget']*4,row['exact'],'exact_gap')]
            else:
                states=[]
                for B,tol,exact in zip([0,geos[key][0]['m']*T//5*4,geos[key][0]['m']*T//2*4],row['tolerant'],row['exact']):
                    states += [(B,tol,'two_percent_gap'),(B,exact,'exact_gap')]
            saved={}
            lower=np.zeros(N,dtype=np.int64);seen=np.zeros((T,N),dtype=bool)
            for step in range(len(row['trace'])+1):
                n=step*N if column else step
                upper=lower+(T-seen.sum(axis=0))*p
                for B,st,stop in states:
                    lo=capacity_sorted(upper[selected],B);hi=capacity_sorted(lower[selected],B)
                    limit=eps if stop=='two_percent_gap' else 0
                    if (B,stop) not in saved and hi-lo<=limit:saved[B,stop]=n
                    if st['queries']==n:
                        mask=np.asarray(st['mask'],dtype=bool)
                        assert (lo,hi,hi-lo)==(st['V_lower'],st['V_upper'],st['gap'])
                        assert int(upper[mask].sum())<=B
                        assert int(np.sum(mask&selected))==lo
                        assert saved[B,stop]==n
                        stops+=1
                if step==len(row['trace']):break
                if column:
                    c=row['trace'][step];assert not seen[c].any()
                    seen[c,:]=True;lower+=values[c];answers+=N
                else:
                    c,i,value=row['trace'][step]
                    assert selected[i] and p[i]>0 and not seen[c,i]
                    assert value==int(values[c,i]);seen[c,i]=True;lower[i]+=value;answers+=1
            paths+=1
    assert paths==2496 and stops==8064
    # Recompute all row and column witnesses; check general order-statistic condition.
    for key,gs in geos.items():
        base,hidden,selected,p,values=panels[key]
        y=(hidden[:,selected&(p>0)].T<.5).astype(int);m,T=y.shape
        for b,g in gs.items():
            Q=exact_offline_certificate(y.sum(axis=1),T,b)[0];assert Q==g['Q_entry']
            witness=exact_columns(y,b,Q);assert witness['K_col']==g['K_col']
            verify_minimality(y,b,witness)
            cols=g['columns'];o=np.sort(y[:,cols].sum(axis=1));L=capacity_sorted(y.sum(axis=1),b)
            assert int(o[:L].sum())+L*(T-len(cols))<=b
            assert L==m or int(o[:L+1].sum())>b
    receipt={'status':'PASS_INDEPENDENT_SYNTHETIC_OBSERVATION_AND_FIRST_STOP_REPLAY',
             'paths':paths,'first_stop_states':stops,'score_observations_checked':answers,
             'explicit_single_replacement_costs_checked':sum(x[4].size for x in panels.values()),
             'exact_witness_instances':576,'no_real_panel_reads':True}
    (out/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);main(p.parse_args().out)

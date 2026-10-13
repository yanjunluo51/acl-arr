"""Self-contained controlled benchmark using complete manuscript solvers.

No real score panel, label or network access is needed. Reference inputs and test
inputs are separately generated. Test truth enters acquisition only via oracles.
"""
from pathlib import Path
from fractions import Fraction
import argparse, csv, gzip, itertools, json, math, time
import numpy as np
from query_selection import (aggregate, endpoint_cost, all_flips, fit_prior,
                             exact_offline_certificate, capacity)
from review_accelerated import solve_multi
from mapping_column_experiments import solve_columns
from column_certificate import exact_columns, verify_minimality
ROOT=Path(__file__).resolve().parents[1]


def make_panel(m,T,d,layout,seed):
    rng=np.random.default_rng(seed)
    pattern=rng.permutation(T)
    y=np.zeros((m,T),dtype=np.int64)
    for i in range(m):
        cols=(pattern[:d] if layout=='shared' else
              np.roll(pattern,i%T)[:d] if layout=='cyclic' else rng.choice(T,d,replace=False))
        y[i,cols]=1
    N=m+48
    base=rng.uniform(.1,.3,(7,N))
    base[:4,:m]=rng.uniform(.65,.95,(4,m))
    base[0,::5][:m//5]=.5  # Some boundary membership votes tie at the cutoff.
    base[:5,m:m+16]=rng.uniform(.65,.95,(5,16))
    base[:2,m+16:m+32]=rng.uniform(.65,.95,(2,16))
    base[:3,m+32:]=rng.uniform(.65,.95,(3,16))
    candidates=rng.uniform(.1,.95,(T,N))
    candidates[:,:m]=np.where(y.T==1,.25,.75)
    # Agreement at exactly the included cutoff, without changing any bit.
    ties=(y.T==0)&(np.indices((T,m)).sum(axis=0)%11==0)
    candidates[:,:m][ties]=.5
    assert np.array_equal((candidates[:,:m].T<.5).astype(int),y)
    selected=aggregate(base,'median')>=.5
    p=endpoint_cost(base,.5,'median')
    assert int(selected.sum())==m+16 and np.all(p[:m]==4)
    assert np.all(p[m:m+32]==0) and np.all(p[m+32:]==4)
    assert int(np.sum(selected&(p>0)))==m
    return base,candidates,y


def main(out):
    spec=json.loads((ROOT/'review-revision/certificate-granularity/synthetic-protocol.json').read_text())
    from hashlib import sha256
    for p,digest in spec['solver_bindings'].items():
        assert sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
    out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir()
    (out/'protocol.json').write_text(json.dumps(spec,indent=2)+'\n')
    records=[];geometry=[];start=time.monotonic();pair_check={}
    with gzip.open(out/'traces.jsonl.gz','wt') as log:
        for m,T,d,layout,rep in itertools.product(spec['m'],spec['T'],spec['oppositions_per_row'],spec['layouts'],range(spec['seeds'])):
            seed=spec['seed_base']+rep+1000*m+100*T+10*d
            base,hidden,y=make_panel(m,T,d,layout,seed)
            ref,ref_candidates,_=make_panel(m,T,d,layout,seed+4000001)
            selected=aggregate(base,'median')>=.5;p=endpoint_cost(base,.5,'median')
            prior=fit_prior(ref,ref_candidates,base,.5,p,'median')
            N=base.shape[1];k=m;budgets=np.array([0,m*T//5,m*T//2],dtype=np.int64)*4
            tie=np.random.default_rng(seed+19001).permutation(N)
            eps=math.ceil(.02*selected.sum())
            costs=all_flips(base,hidden,.5,'median').sum(axis=0)
            assert np.array_equal(costs[:m],4*y.sum(axis=1))
            key=f'm{m}-T{T}-d{d}-{layout}-seed{rep}'
            np.savez_compressed(out/'inputs'/f'{key}.npz',base=base,candidates=hidden,
                                reference_base=ref,reference_candidates=ref_candidates,opposition_bits=y)
            Qs=[];witnesses=[]
            for B in budgets:
                b=int(B)//4;Q=exact_offline_certificate(y.sum(axis=1),T,b)[0]
                w=exact_columns(y,b,Q);verify_minimality(y,b,w)
                Qs.append(Q);witnesses.append(w)
                pair=(m,T,d,rep,b)
                if pair in pair_check:assert pair_check[pair]==Q
                else:pair_check[pair]=Q
                alpha=Fraction(int(B),2*k*7*T)
                assert (2*k*7*T*alpha.numerator)//alpha.denominator==int(B)
                geometry.append({'key':key,'m':m,'T':T,'d':d,'layout':layout,'rep':rep,
                                 'N':N,'k':k,'alpha_rational':str(alpha),'bit_budget':b,
                                 'Q_entry':Q,**w,'score_entry_cost':N*w['K_col']})
            def add(method,a,stop,st,trace,w):
                B=int(budgets[a]);mask=np.asarray(st['mask'],dtype=bool)
                V=capacity(costs[selected],B)
                assert st['V_lower']<=V<=st['V_upper'] and int(costs[mask].sum())<=B
                assert int(np.sum(mask&selected))==st['V_lower']
                assert st['gap']<=(eps if stop=='two_percent_gap' else 0)
                if stop=='exact_gap':assert st['V_lower']==V
                col=method.startswith('column_')
                if stop=='exact_gap':
                    assert (st['columns']>=w['K_col']) if col else (st['queries']>=Qs[a])
                records.append({'key':key,'m':m,'T':T,'d':d,'layout':layout,'rep':rep,
                                'bit_budget':B//4,'method':method,'stopping':stop,
                                'queries':st['queries'],'columns':st.get('columns'),
                                'V_lower':st['V_lower'],'V_upper':st['V_upper'],'V_star':V,
                                'gap':st['gap'],'Q_entry':Qs[a],'K_col':w['K_col']})
            for method in spec['entry_methods']:
                seen=set()
                def query(c,i):
                    assert (c,i) not in seen;seen.add((c,i));return hidden[c,i]
                trace,_,tolerant,exact=solve_multi(base,selected,p,prior,.5,'median',T,budgets,tie,method,seed,query,[0,1],eps)
                # Independent row-cost replay checks every revealed entry and stop.
                for c,i,f in trace:assert f==int(p[i])*(hidden[c,i]<.5)
                for a,w in enumerate(witnesses):
                    for stop,st in [('two_percent_gap',tolerant[a]),('exact_gap',exact[a])]:
                        add(method,a,stop,st,trace,w)
                log.write(json.dumps({'key':key,'method':method,'trace':trace,
                                      'tolerant':tolerant,'exact':exact})+'\n')
            for method in spec['column_methods']:
                for a,w in enumerate(witnesses):
                    seen=set()
                    def query_column(c):
                        assert c not in seen;seen.add(c);return hidden[c].copy()
                    trace,tol,exact=solve_columns(base,selected,p,prior,.5,'median',T,int(budgets[a]),tie,method,seed,query_column,eps)
                    for stop,st in [('two_percent_gap',tol),('exact_gap',exact)]:add(method,a,stop,st,trace,w)
                    log.write(json.dumps({'key':key,'method':method,'bit_budget':int(budgets[a])//4,
                                          'trace':trace,'tolerant':tol,'exact':exact})+'\n')
            if len(geometry)%96==0:
                state={'status':'RUNNING','instances':len(geometry),'total':576,
                       'seconds':round(time.monotonic()-start,2)}
                (out/'execution.json').write_text(json.dumps(state)+'\n');print(json.dumps(state),flush=True)
    assert len(geometry)==576 and len(records)==8064
    (out/'results.json').write_text(json.dumps({'protocol':spec,'geometry':geometry,'records':records},separators=(',',':'))+'\n')
    cells=[]
    for m,T,d,layout in itertools.product(spec['m'],spec['T'],spec['oppositions_per_row'],spec['layouts']):
        for b in [0,m*T//5,m*T//2]:
            a=[z for z in geometry if (z['m'],z['T'],z['d'],z['layout'],z['bit_budget'])==(m,T,d,layout,b)]
            assert len(a)==8
            cells.append({'m':m,'T':T,'d':d,'layout':layout,'bit_budget':b,'seeds':8,
                          'mean_Q_entry':float(np.mean([z['Q_entry'] for z in a])),
                          'mean_K_col':float(np.mean([z['K_col'] for z in a])),
                          'min_K_col':min(z['K_col'] for z in a),'max_K_col':max(z['K_col'] for z in a)})
    with (out/'cells.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(cells[0]));writer.writeheader();writer.writerows(cells)
    final={'status':'PASS_COMPLETE_SYNTHETIC_SOLVERS_AND_EXACT_WITNESSES',
           'generated_panels':192,'instances':576,'stop_records':8064,
           'entry_paths':768,'column_paths':1728,'input_panels_saved':True,
           'full_methods_unchanged':True,'no_third_party_score_reads':True,
           'runtime_seconds':time.monotonic()-start,'runtime_scope':'information replay, not model inference'}
    (out/'execution.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(final),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'outputs/synthetic-certificates')
    main(p.parse_args().out)

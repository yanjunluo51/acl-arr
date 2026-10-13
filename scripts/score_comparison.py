"""Grouped SCoRE-MDR adaptation of the same replacement-churn loss.

Proposition 4.4 (gamma=alpha) implemented with integer risk sums. Groups are
whole prompts/source segments; no within-group iid assumption or batch safety
is asserted. Whole-group acceptance restricts the available selection actions.
"""
from pathlib import Path
from fractions import Fraction
import argparse,csv,json,multiprocessing,time
import numpy as np
from review_accelerated import mapped_panel,swap_geometry,diagnostics
from query_selection import aggregate,endpoint_cost,fit_prior,summary
ROOT=Path(__file__).resolve().parents[1]

def accept(cal_cost,cal_score,test_score,N,k,H,g,alpha):
    a=Fraction(alpha);n=len(cal_cost);order=np.argsort(cal_score,kind='stable');s=cal_score[order]
    cumulative=np.r_[0,np.cumsum(cal_cost[order],dtype=np.int64)]
    chosen=cumulative[np.searchsorted(s,test_score,side='right')]
    lhs=(g*H+chosen)*N*a.denominator;rhs=(n+1)*2*k*g*H*a.numerator
    return lhs<=rhs

def score_for_groups(prior,selected,H,g):
    estimate=(prior.sum(axis=1)*selected).reshape(-1,g).sum(axis=1)/H
    reward=selected.reshape(-1,g).sum(axis=1)
    return np.divide(estimate,reward,out=np.ones_like(estimate),where=reward>0)

def case(task):
    panel,rep,agg,q=task;mapped,g,seed,idx=mapped_panel(panel,rep);ref,cal,test=[a[:7] for a in mapped];cr,cc,hidden=[a[7:] for a in mapped]
    M=7;T=len(hidden);H=M*T;N=test.shape[1];k=max(1,round(q*N));tie=np.random.default_rng(seed+rep+700001).permutation(N)
    t=np.sort(aggregate(ref,agg))[-max(1,round(q*ref.shape[1]))];cons=aggregate(test,agg);sel=cons>=t;selc=aggregate(cal,agg)>=t
    pc=endpoint_cost(cal,t,agg);p=endpoint_cost(test,t,agg);prc=fit_prior(ref,cr,cal,t,pc,agg);prt=fit_prior(ref,cr,test,t,p,agg)
    cs=score_for_groups(prc,selc,H,g);ts=score_for_groups(prt,sel,H,g)
    _,cf=swap_geometry(cal,cc,t,agg);cal_group_cost=(cf.sum(axis=0)*selc).reshape(-1,g).sum(axis=1)
    decisions=[]
    for a in ['1/50','1/20','1/10','3/20','1/5']:
        accepted=accept(cal_group_cost,cs,ts,N,k,H,g,a);mask=(sel & np.repeat(accepted,g))|(p==0)
        decisions.append((a,mask,accepted))
    # Decisions above use calibration losses and visible risk predictions only.
    bits,f=swap_geometry(test,hidden,t,agg);cost=f.sum(axis=0);labels=np.tile([1,0,0,0],N//4) if panel=='RewardBench2' else None
    rows=[];saved=[]
    for a,mask,accepted in decisions:
        alpha=float(Fraction(a));row={'dataset':panel,'split':rep,'aggregator':agg,'q':q,'alpha':alpha,'alpha_rational':a,'method':'grouped_SCoRE_MDR','certificate':'conditional_expected_churn','group_size':g,'calibration_groups':len(cs),'test_groups':len(ts),'accepted_groups':int(accepted.sum()),'M':M,'T':T,'H':H,'k':k,'n_test_items':N,'candidate_test_entries':0,'candidate_calibration_entries':T*cal.shape[1],'pool_calibration_entries':M*cal.shape[1],'candidate_reference_entries':T*ref.shape[1],'pool_reference_entries':M*ref.shape[1],'pool_test_entries':M*N,**diagnostics(cost,sel,mask,H,k,labels,bits,alpha,cons,tie)}
        rows.append(row);saved.append({'alpha':alpha,'mask':mask.tolist(),'accepted_groups':accepted.tolist()})
    return {'key':[panel,rep,agg,q],'rows':rows,'calibration_group_integer_cost':cal_group_cost.tolist(),'calibration_scores':cs.tolist(),'test_scores':ts.tolist(),'decisions':saved}

def main(workers):
    p=json.loads((ROOT/'review-revision/score-protocol.json').read_text());out=ROOT/'outputs/review-score';out.mkdir(parents=True,exist_ok=True);assert not (out/'results.json').exists();start=time.monotonic();rows=[];cases=[]
    tasks=[(panel,r,a,q) for panel in p['panels'] for r in range(40) for a in ['median','mean'] for q in [.05,.1,.2,.3]]
    with multiprocessing.get_context('spawn').Pool(workers) as pool:
        for z in pool.imap(case,tasks,chunksize=4):rows.extend(z.pop('rows'));cases.append(z)
    payload={'protocol':p,'records':rows,'cells':summary(rows,['dataset','aggregator','q','alpha'],['risk','selected_coverage','returned_count','precision','matched_k_precision_delta','accepted_groups'])}
    (out/'results.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n');(out/'decision-audit-input.json').write_text(json.dumps(cases,separators=(',',':'),allow_nan=False)+'\n')
    with (out/'cells.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=sorted(set().union(*(set(c) for c in payload['cells']))));w.writeheader();w.writerows(payload['cells'])
    receipt={'status':'PASS_COMPLETE_EXECUTION_PENDING_AUDIT','configuration_cases':len(cases),'budget_records':len(rows),'runtime_seconds':time.monotonic()-start,'scope':'Same churn loss, grouped acceptance action, expectation guarantee conditional on group exchangeability; no realized batch guarantee or physical model execution'}
    (out/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=2);a=p.parse_args();main(a.workers)

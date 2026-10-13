"""Separate exact-rational decision and native churn arithmetic audit for SCoRE."""
from pathlib import Path
from fractions import Fraction
import itertools,json,random,time
import numpy as np
from audit_review_results import context,validate_metrics,raw,aggregate
ROOT=Path(__file__).resolve().parents[1]

def calibration_cost(panel,rep,agg,q):
    z,a,g=raw(panel);order=list(range(len(z['prompt_ids'])));seed=20260815 if panel=='RewardBench2' else 87000
    random.Random(seed+rep).shuffle(order);third=len(order)//3;ir=np.array([i*g+j for i in order[:third] for j in range(g)]);ic=np.array([i*g+j for i in order[third:2*third] for j in range(g)])
    rr=np.array([np.searchsorted(np.sort(row[ir]),row[ir],side='right')/len(ir) for row in a]);cc=np.array([np.searchsorted(np.sort(row[ir]),row[ic],side='right')/len(ir) for row in a]);t=np.sort(aggregate(rr[:7],agg))[-max(1,round(q*len(ir)))];sel=aggregate(cc[:7],agg)>=t;F=np.zeros(len(ic),dtype=int)
    for j in range(7):
        for r in range(7,len(a)):
            v=cc[:7].copy();v[j]=cc[r];F+=(aggregate(v,agg)>=t)!=sel
    return (F*sel).reshape(-1,g).sum(axis=1)

def main():
    start=time.monotonic();out=ROOT/'outputs/review-score';x=json.loads((out/'results.json').read_text());logs=json.loads((out/'decision-audit-input.json').read_text());rows={(r['dataset'],r['split'],r['aggregator'],r['q'],r['alpha']):r for r in x['records']};assert len(logs)==960 and len(rows)==4800
    keys=set();checks=violations=0
    for z in logs:
        panel,rep,agg,q=z['key'];key=tuple(z['key']);assert key not in keys;keys.add(key);c=context(panel,{'indices':list(range(7))},rep,agg,q);c['panel']=panel
        g=4 if panel=='RewardBench2' else (12 if panel.endswith('without_synthetic_ref') else 13);cf=calibration_cost(panel,rep,agg,q);assert cf.tolist()==z['calibration_group_integer_cost'];cs=np.array(z['calibration_scores']);ts=np.array(z['test_scores']);assert np.all((cs>=0)&(cs<=1)) and np.all((ts>=0)&(ts<=1))
        for decision,a in zip(z['decisions'],['1/50','1/20','1/10','3/20','1/5']):
            alpha=Fraction(a);target=alpha*Fraction(2*c['k'],c['N']);expected=[]
            for score in ts:
                # Direct Proposition 4.4 arithmetic, not the runner's sorted shortcut.
                numerator=g*c['H']+int(cf[cs<=score].sum());left=Fraction(numerator,(len(cf)+1)*g*c['H']);expected.append(left<=target);checks+=1
            assert expected==decision['accepted_groups'];mask=(c['sel'] & np.repeat(expected,g))|(c['p']==0);assert mask.tolist()==decision['mask'];r=rows[key+(float(alpha),)];validate_metrics(r,mask,c);assert r['candidate_test_entries']==0 and r['certificate']=='conditional_expected_churn';violations+=r['risk']>float(alpha)+1e-12
        if len(keys)%80==0:print('SCoRE audit cases',len(keys),'seconds',round(time.monotonic()-start,1),flush=True)
    # Exhaustive leave-one-out symmetry check for the stated finite calibration
    # construction. This is arithmetic support, not a new exchangeability theorem.
    symmetry=0;rng=random.Random(88271)
    for _ in range(100):
        loss=[Fraction(rng.randrange(11),10) for i in range(8)];score=[rng.randrange(4) for i in range(8)]
        for alpha in [Fraction(1,20),Fraction(1,5),Fraction(1,2)]:
            accepted=[]
            for test in range(8):
                numerator=1+sum(loss[i] for i in range(8) if i!=test and score[i]<=score[test]);accepted.append(numerator/8<=alpha)
            assert sum(loss[i]*accepted[i] for i in range(8))/8<=alpha;symmetry+=1
    report={'status':'PASS_SCOPED_EXACT_RATIONAL_DECISIONS_AND_NATIVE_CHURN','configuration_cases':len(keys),'records':len(rows),'group_decisions_checked':checks,'leave_one_out_symmetry_arithmetic_checks':symmetry,'observed_over_budget_records':violations,'runtime_seconds':time.monotonic()-start,'scope':'Grouped adaptation only; existing theorem conditional on group exchangeability. Over-budget fixed batches do not refute expectation control.'}
    (ROOT/'review-revision/score-independent-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()

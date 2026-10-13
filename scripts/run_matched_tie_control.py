"""Successor paired cached-score control. Never modifies native evidence or queries.

Both baseline and every complete-batch replacement use the same low-priority-
first label-blind key as the original retained-mask solver. Quality labels are
not loaded. Full-information optima are separate from entry-query certificates.
"""
from pathlib import Path
from functools import lru_cache
import argparse,csv,hashlib,json,multiprocessing,time
import numpy as np
from query_selection import aggregate,prefix
from analyze import topk
from review_accelerated import mapped_panel
from external_experiments import mapped as external_mapped
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/matched-tie-control'
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh']

def select(score,k,tie):
    out=np.zeros(len(score),dtype=bool)
    out[np.lexsort((tie,-score))[:k]]=True
    return out

@lru_cache(maxsize=2)
def geometry(panel,rep,agg):
    if panel.startswith('WMT24'):
        maps,_=external_mapped(panel,rep);seed=924000
    else:
        maps,_,seed,_=mapped_panel(panel,rep)
    ref,test=maps[0],maps[2];base=test[:7];candidates=test[7:]
    sw=[]
    for j in range(7):
        for cand in candidates:
            x=base.copy();x[j]=cand;sw.append(aggregate(x,agg))
    return aggregate(ref[:7],agg),aggregate(base,agg),np.array(sw),len(candidates),seed

def describe(bits,baseline,budget,tie,k):
    costs=bits.sum(axis=0,dtype=np.int64)
    ids=np.flatnonzero(baseline);mask=np.zeros(len(baseline),dtype=bool)
    mask[ids[prefix(costs[ids],budget,tie[ids])]]=True
    spent=int(costs[mask].sum());H=len(bits)
    assert spent<=budget
    risks=bits[:,mask].sum(axis=1)/(2*k)
    assert abs(float(risks.mean())-spent/(2*k*H))<1e-12
    return mask,{'selected_count':int(baseline.sum()),'returned_count':int(mask.sum()),
        'selected_coverage':float(mask.sum()/baseline.sum()) if baseline.any() else None,
        'risk':spent/(2*k*H),'integer_spent':spent,'replacement_max_risk':float(risks.max()),
        'replacement_over_alpha_fraction':float(np.mean(risks>.1+1e-12)),
        'full_list_churn':int(costs.sum())/(2*k*H),
        'selected_cost_sha256':hashlib.sha256(costs.astype('<i8').tobytes()).hexdigest()}

def case(task):
    panel,rep,agg,q=task;ref,base,sw,T,seed=geometry(panel,rep,agg)
    N=len(base);k=max(1,round(q*N));H=7*T;budget=(2*k*H)//10
    tie=np.random.default_rng(seed+rep+700001).permutation(N)
    cutoff=np.sort(ref)[-max(1,round(q*len(ref)))];frozen=base>=cutoff
    old=topk(base,k);new=select(base,k,tie)
    fb=(sw>=cutoff)!=frozen
    ob=np.array([topk(x,k)!=old for x in sw]);nb=np.array([select(x,k,tie)!=new for x in sw])
    # Top-k has exactly k memberships in every replacement, hence an even distance.
    assert np.all(ob.sum(axis=1)%2==0) and np.all(nb.sum(axis=1)%2==0)
    assert all(select(x,k,tie).sum()==k for x in sw)
    fm,fd=describe(fb,frozen,budget,tie,k)
    om,od=describe(ob,old,budget,tie,k);nm,nd=describe(nb,new,budget,tie,k)
    common={'dataset':panel,'split':rep,'aggregator':agg,'q':q,'alpha':.1,'N':N,'M':7,'T':T,'H':H,'k':k,'cutoff':float(cutoff),'integer_budget':budget}
    rows=[{**common,'rule':rule,**d} for rule,d in [('frozen_cutoff',fd),('fixed_native',od),('fixed_matched',nd)]]
    union=int(np.sum(fm|nm));pair={**common,'native_to_matched_baseline_changes':int(np.sum(old!=new)),
        'native_to_matched_mask_changes':int(np.sum(om!=nm)),
        'native_to_matched_replacement_changes':int(np.sum(ob!=nb)),
        'native_to_matched_returned_delta':nd['returned_count']-od['returned_count'],
        'native_to_matched_risk_delta':nd['risk']-od['risk'],
        'matched_minus_frozen_returned':nd['returned_count']-fd['returned_count'],
        'native_minus_frozen_returned':od['returned_count']-fd['returned_count'],
        'matched_minus_frozen_coverage':nd['selected_coverage']-fd['selected_coverage'] if fd['selected_coverage'] is not None else None,
        'matched_frozen_baseline_symmetric_difference':int(np.sum(new!=frozen)),
        'matched_frozen_returned_jaccard':float(np.sum(fm&nm)/union) if union else 1.,
        'returned_comparison_sign_changed':bool(np.sign(nd['returned_count']-fd['returned_count'])!=np.sign(od['returned_count']-fd['returned_count']))}
    masks={'key':[panel,rep,agg,q],'N':N,'frozen':np.packbits(fm).tolist(),'native':np.packbits(om).tolist(),'matched':np.packbits(nm).tolist()}
    return rows,pair,masks

def csvwrite(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main(workers,output_dir=None):
    global OUT
    if output_dir is not None:OUT=Path(output_dir).resolve()
    assert json.loads((ROOT/'review-revision/html-review-implementation/pre-edit-checks.json').read_text())['status']=='PASS_THREE_PRE_EDIT_CHECKS'
    OUT.mkdir(exist_ok=False)
    (OUT/'protocol.json').write_text(json.dumps({'panels':PANELS,'configurations':1920,'alpha':'1/10','q':[.05,.1,.2,.3],
       'tie_order':'np.lexsort((tie,-consensus))[:k] for baseline AND every replacement',
       'native_control_preserved':True,'labels_loaded':False,'models_called':False,'online_query_protocol_changed':False,
       'claim_scope':'Full-information selection sensitivity with matched output tie priority; different baseline tasks remain.'},indent=2)+'\n')
    (OUT/'execution.json').write_text(json.dumps({'status':'RUNNING','completed':0})+'\n');start=time.monotonic()
    tasks=[(p,r,a,q) for p in PANELS for r in range(40) for a in ['median','mean'] for q in [.05,.1,.2,.3]]
    rows=[];pairs=[];masks=[]
    with multiprocessing.get_context('spawn').Pool(workers) as pool:
        for i,(rs,p,m) in enumerate(pool.imap(case,tasks,chunksize=8),1):
            rows.extend(rs);pairs.append(p);masks.append(m)
            if i%80==0:
                print('completed',i,'of',len(tasks),flush=True)
                (OUT/'execution.json').write_text(json.dumps({'status':'RUNNING','completed':i})+'\n')
    assert len(pairs)==1920 and len(rows)==5760
    csvwrite(OUT/'records.csv',rows);csvwrite(OUT/'paired.csv',pairs)
    (OUT/'masks.json').write_text(json.dumps(masks,separators=(',',':'))+'\n')
    cells=[]
    for p in PANELS:
        for a in ['median','mean']:
            for q in [.05,.1,.2,.3]:
                ps=[x for x in pairs if x['dataset']==p and x['aggregator']==a and x['q']==q]
                cs=[x for x in rows if x['dataset']==p and x['aggregator']==a and x['q']==q]
                c={'dataset':p,'aggregator':a,'q':q,'splits':40,
                  'baseline_changed_splits':sum(x['native_to_matched_baseline_changes']>0 for x in ps),
                  'mask_changed_splits':sum(x['native_to_matched_mask_changes']>0 for x in ps),
                  'replacement_changed_splits':sum(x['native_to_matched_replacement_changes']>0 for x in ps),
                  'comparison_sign_changed_splits':sum(x['returned_comparison_sign_changed'] for x in ps)}
                for f in ['native_to_matched_returned_delta','native_to_matched_risk_delta','matched_minus_frozen_returned','native_minus_frozen_returned','matched_minus_frozen_coverage','matched_frozen_returned_jaccard']:
                    vals=[x[f] for x in ps if x[f] is not None];c[f]=float(np.mean(vals)) if vals else None
                for rule in ['frozen_cutoff','fixed_native','fixed_matched']:
                    for f in ['selected_count','returned_count','selected_coverage','risk','replacement_max_risk','replacement_over_alpha_fraction','full_list_churn']:
                        vals=[x[f] for x in cs if x['rule']==rule and x[f] is not None];c[rule+'_'+f]=float(np.mean(vals)) if vals else None
                cells.append(c)
    csvwrite(OUT/'cells.csv',cells)
    result={'status':'COMPLETE_PENDING_INDEPENDENT_RECONCILIATION','configurations':len(pairs),'records':len(rows),
      'cells':cells,'runtime_seconds':time.monotonic()-start,'quality_labels_loaded':False,'model_inference':False,
      'original_native_evidence_overwritten':False,'new_online_certificate':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (OUT/'execution.json').write_text(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cells'}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4)
    p.add_argument('--output-dir',type=Path,help='Fresh successor directory; never overwrites saved evidence')
    args=p.parse_args();main(args.workers,args.output_dir)

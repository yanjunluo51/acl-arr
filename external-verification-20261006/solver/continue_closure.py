"""Isolated append-only stronger attempts; never updates the published grid."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:
    os.environ[k]='1'
import sys,json,time,copy,multiprocessing,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from continue_full_mean_bounded import load,CLOSED
from bounded_threshold_certificate import certificate
from bounded_union_certificate import union_certificate
from joint_certificates import capacity
from audit_full_mean_grid import valuecheck
OUT=Path(__file__).resolve().parent

def solve(task):
    x,prior_levels=task
    old=copy.deepcopy(x);key=[x['dataset'],x['split'],x['q'],x['stopping']]
    name='-'.join(map(str,key));progress=OUT/(name+'.progress.jsonl')
    attempts={};start=time.monotonic()
    def save(event):
        with progress.open('a') as f:f.write(json.dumps(event,separators=(',',':'))+'\n')
    try:
        for kind,sep in [('joint',False),('separate',True)]:
            if x[kind]['joint_optimal']:continue
            rows,caps,B,eps=x['rows'],x['caps'],x['budget'],x['epsilon']
            active=[r for r,p in zip(rows,caps) if p];m=len(active)
            L=capacity(list(map(sum,active)),B);pmax=min(L,m-eps-1)+eps+1
            levels=[t for t in range(max(map(sum,active),default=0)+1)
                    if pmax*t-sum(max(0,t-sum(r)) for r in active)>=B+1] or [0]
            calls=copy.deepcopy(prior_levels.get(kind,{}));best=x[kind]
            for t in levels:
                if t not in calls:
                    r=certificate(rows,caps,B,eps,seconds=20,separated=sep,fixed_threshold=t,presolve=False,incumbent=best,relaxation=True)
                    calls[t]={'threshold':t,'attempts':[r],'result':r}
            kind_start=time.monotonic()
            for t in sorted(levels,key=lambda t:calls[t]['result']['joint_lower_bound']):
                if calls[t]['result']['joint_lower_bound']>=best['objective']:continue
                remaining=600-(time.monotonic()-kind_start)
                if remaining<1:break
                r=certificate(rows,caps,B,eps,seconds=min(180,remaining),separated=sep,
                    fixed_threshold=t,presolve=True,incumbent=best,improving_only=True)
                valuecheck(x,r,sep);calls[t]['attempts'].append(r)
                if r['objective']<best['objective']:best=r
                lb=max(calls[t]['result']['joint_lower_bound'],r['joint_lower_bound'])
                calls[t]['result']=dict(r,joint_lower_bound=min(lb,r['objective']),
                    joint_optimal=lb>=r['objective'],status='OPTIMAL' if lb>=r['objective'] else 'UNRESOLVED')
                save({'kind':kind,'threshold':t,'result':r,'incumbent':best['objective']})
            # All thresholds remain covered, including levels not retried.
            for t in levels:
                r=calls[t]['result'];lb=min(r['joint_lower_bound'],best['objective'])
                if r['objective']>best['objective']:
                    r=dict(best,joint_lower_bound=lb,joint_optimal=lb>=best['objective'],status='OPTIMAL' if lb>=best['objective'] else 'UNRESOLVED')
                calls[t]['result']=r
            low=min(calls[t]['result']['joint_lower_bound'] for t in levels)
            x[kind]=dict(best,joint_lower_bound=low,joint_optimal=low>=best['objective'],status='OPTIMAL' if low>=best['objective'] else 'UNRESOLVED',scope='global_exhaustive_thresholds')
            valuecheck(x,x[kind],sep);attempts[kind]=[calls[t] for t in levels]
            save({'kind':kind,'final':x[kind]})
        if x['joint']['joint_optimal'] and x['separate']['joint_optimal']:
            if x['joint']['objective']==x['separate']['objective']:
                x['union']={'status':'PROVED_BY_BOUND_SANDWICH','union_minimum':x['joint']['objective']}
            elif not x['union'] or x['union']['status'] not in CLOSED:
                u=union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],seconds=180,total_seconds=600,presolve=True,
                    certified_joint_minimum=x['joint']['objective'],preferred_target=x['joint']['V_lower']-x['caps'].count(0))
                save({'kind':'union','result':u})
                # Preserve a better old unresolved feasible witness if the new attempt is worse.
                if u['status'] in CLOSED or not x['union'] or u.get('union_minimum',float('inf'))<=x['union'].get('union_minimum',float('inf')):x['union']=u
        return {'key':key,'primary':old,'closed':x,'threshold_attempts':attempts,'seconds':time.monotonic()-start}
    except Exception:
        err={'key':key,'status':'FAILED_ATTEMPT','error':traceback.format_exc(),'seconds':time.monotonic()-start};save(err);return err

if __name__=='__main__':
    cases=load();prior={}
    for p in sorted((ROOT/'outputs/full-mean-grid-20261005').glob('closure-*.jsonl')):
        for r in map(json.loads,p.open()):
            for kind,aa in r['threshold_attempts'].items():prior.setdefault(tuple(r['key']),{})[kind]={a['threshold']:a for a in aa}
    pending=[x for x in cases.values() if not x['joint']['joint_optimal'] or not x['separate']['joint_optimal'] or not x['union'] or x['union']['status'] not in CLOSED]
    # Smaller targets first; scheduling does not change the instances or objective.
    pending.sort(key=lambda x:(x['stopping']!='exact',len(x['rows'])))
    (OUT/'pending.json').write_text(json.dumps([{'key':[x['dataset'],x['split'],x['q'],x['stopping']],'joint_lower':x['joint']['joint_lower_bound'],'joint_upper':x['joint']['objective']} for x in pending],indent=2))
    print('START',len(pending),flush=True)
    with (OUT/'candidate-closures.jsonl').open('x') as f,(OUT/'failed-attempts.jsonl').open('x') as err,multiprocessing.get_context('spawn').Pool(4) as pool:
        for r in pool.imap_unordered(solve,[(x,prior.get((x['dataset'],x['split'],x['q'],x['stopping']),{})) for x in pending]):
            target=err if r.get('status')=='FAILED_ATTEMPT' else f
            target.write(json.dumps(r,separators=(',',':'))+'\n');target.flush()
            print('DONE',r['key'],r.get('status') or [r['closed']['joint']['status'],(r['closed']['union'] or {}).get('status')],round(r['seconds'],1),flush=True)
    print('ALL_ATTEMPTS_TERMINAL',flush=True)

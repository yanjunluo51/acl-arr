"""Append-only exhaustive threshold closure of completed primary records."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import json,math,multiprocessing,sys,time
from pathlib import Path
from threshold_target_certificate import certificate
from deduplicated_certificates import union_certificate
from joint_certificates import capacity
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/full-mean-grid-20261005'

def close(x):
    old=dict(x);rows,caps,B,eps=x['rows'],x['caps'],x['budget'],x['epsilon']
    active=[r for r,p in zip(rows,caps) if p];m=len(active);L=capacity(list(map(sum,active)),B)
    pmax=min(L,m-eps-1)+eps+1
    levels=[t for t in range(max(map(sum,active),default=0)+1)
            if pmax*t-sum(max(0,t-sum(r)) for r in active)>=B+1]
    if not levels:levels=[0]
    closures={}
    for kind,sep in [('joint',False),('separate',True)]:
        if x[kind]['joint_optimal']:continue
        calls=[];best=None
        for t in levels:
            v=certificate(rows,caps,B,eps,seconds=120,separated=sep,fixed_threshold=t)
            attempts=[v]
            if any(c.get('status')==2 for c in v['calls']):
                v=certificate(rows,caps,B,eps,seconds=120,separated=sep,fixed_threshold=t,presolve=False)
                attempts.append(v)
            calls.append(dict(threshold=t,attempts=attempts,result=v))
            if best is None or v['objective']<best['objective']:best=v
        lower=min(c['result']['joint_lower_bound'] for c in calls)
        proven=lower>=best['objective']
        x[kind]=dict(best,joint_lower_bound=lower,joint_optimal=proven,
                     status='OPTIMAL' if proven else 'UNRESOLVED',scope='global_exhaustive_thresholds')
        closures[kind]=calls
    if x['joint']['joint_optimal'] and x['separate']['joint_optimal']:
        if x['joint']['objective']==x['separate']['objective']:
            x['union']=dict(status='PROVED_BY_BOUND_SANDWICH',union_minimum=x['joint']['objective'])
        elif x['union'] is None or x['union']['status']!='OPTIMAL':
            x['union']=union_certificate(rows,caps,B,eps,seconds=300,presolve=False)
    return dict(key=[x['dataset'],x['split'],x['q'],x['stopping']],primary=old,closed=x,threshold_attempts=closures)

def main():
    existing={}
    for p in sorted(OUT.glob('closure-*.jsonl')):
        for line in p.open():
            x=json.loads(line);existing[tuple(x['key'])]=x['closed']
    allrows=[]
    for line in (OUT/'records.jsonl').open():
        try:x=json.loads(line)
        except json.JSONDecodeError:continue
        key=(x['dataset'],x['split'],x['q'],x['stopping']);x=existing.get(key,x)
        if not x['joint']['joint_optimal'] or not x['separate']['joint_optimal'] or x['union'] is None or x['union']['status']=='UNRESOLVED':allrows.append(x)
    name=time.strftime('closure-%Y%m%d-%H%M%S');path=OUT/(name+'.jsonl');assert not path.exists()
    start=time.monotonic();print('closure cases',len(allrows),flush=True)
    with path.open('w') as f,multiprocessing.get_context('spawn').Pool(4) as pool:
        for i,x in enumerate(pool.imap_unordered(close,allrows),1):
            f.write(json.dumps(x,separators=(',',':'))+'\n');f.flush()
            print(i,len(allrows),x['key'],x['closed']['joint']['status'],x['closed']['separate']['status'],round(time.monotonic()-start,1),flush=True)
    (OUT/(name+'.json')).write_text(json.dumps(dict(status='COMPLETED_CLOSURE_ATTEMPT_PENDING_AUDIT',cases=len(allrows),seconds=time.monotonic()-start),indent=2)+'\n')

if __name__=='__main__':
    if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
    main()

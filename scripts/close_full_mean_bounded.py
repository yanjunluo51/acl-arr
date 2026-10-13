"""Append-only full-grid closure using LP screening and incumbent cutoffs.

Every admissible threshold is retained in the receipt. Bounds from each
threshold are truncated by a globally feasible incumbent, so a skipped level
cannot create a false global optimality declaration.
"""
import os
for k in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[k] = '1'
import json, multiprocessing, sys, time
from pathlib import Path
from bounded_threshold_certificate import certificate
from deduplicated_certificates import union_certificate
from joint_certificates import capacity
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/full-mean-grid-20261005'

def close(task):
    x,progress_dir=task
    old=json.loads(json.dumps(x))
    rows,caps,B,eps=x['rows'],x['caps'],x['budget'],x['epsilon']
    active=[r for r,p in zip(rows,caps) if p]
    m=len(active);L=capacity(list(map(sum,active)),B)
    pmax=min(L,m-eps-1)+eps+1
    levels=[t for t in range(max(map(sum,active),default=0)+1)
            if pmax*t-sum(max(0,t-sum(r)) for r in active)>=B+1] or [0]
    closures={}
    name=f"{x['dataset']}-{x['split']}-{x['q']}-{x['stopping']}"
    for kind,sep in [('joint',False),('separate',True)]:
        if x[kind]['joint_optimal']:continue
        best=x[kind];calls={}
        for t in levels:
            r=certificate(rows,caps,B,eps,seconds=20,separated=sep,
                          fixed_threshold=t,presolve=False,incumbent=best,relaxation=True)
            calls[t]=dict(threshold=t,attempts=[r],result=r)
        for t in sorted(levels,key=lambda t:calls[t]['result']['joint_lower_bound']):
            if calls[t]['result']['joint_lower_bound']>=best['objective']:continue
            for seconds in [30,120]:
                r=certificate(rows,caps,B,eps,seconds=seconds,separated=sep,
                              fixed_threshold=t,presolve=False,incumbent=best,improving_only=True)
                prior=calls[t]['result']['joint_lower_bound']
                calls[t]['attempts'].append(r)
                # Both bounds hold for this level (truncated at a global witness).
                r=dict(r,joint_lower_bound=max(prior,r['joint_lower_bound']))
                r['joint_optimal']=r['joint_lower_bound']>=r['objective']
                r['status']='OPTIMAL' if r['joint_optimal'] else 'UNRESOLVED'
                calls[t]['result']=r
                if r['objective']<best['objective']:best=r
                if r['joint_lower_bound']>=best['objective']:break
            Path(progress_dir,f'{name}-{kind}.json').write_text(json.dumps(dict(
                key=[x['dataset'],x['split'],x['q'],x['stopping']],kind=kind,
                incumbent=best['objective'],levels_done=list(calls),calls=calls),separators=(',',':'))+'\n')
        lower=min(calls[t]['result']['joint_lower_bound'] for t in levels)
        lower=min(lower,best['objective'])
        proven=lower>=best['objective']
        x[kind]=dict(best,joint_lower_bound=lower,joint_optimal=proven,
                     status='OPTIMAL' if proven else 'UNRESOLVED',scope='global_exhaustive_thresholds')
        closures[kind]=[calls[t] for t in levels]
    if x['joint']['joint_optimal'] and x['separate']['joint_optimal']:
        if x['joint']['objective']==x['separate']['objective']:
            x['union']=dict(status='PROVED_BY_BOUND_SANDWICH',union_minimum=x['joint']['objective'])
        elif x['union'] is None or x['union']['status']!='OPTIMAL':
            x['union']=union_certificate(rows,caps,B,eps,seconds=300,presolve=False)
    return dict(key=[x['dataset'],x['split'],x['q'],x['stopping']],primary=old,
                closed=x,threshold_attempts=closures)

def main():
    cases={}
    for line in (OUT/'records.jsonl').open():
        x=json.loads(line);cases[(x['dataset'],x['split'],x['q'],x['stopping'])]=x
    for p in sorted(OUT.glob('closure-*.jsonl')):
        for line in p.open():
            r=json.loads(line);assert r['primary']==cases[tuple(r['key'])]
            cases[tuple(r['key'])]=r['closed']
    pending=[x for x in cases.values() if not x['joint']['joint_optimal'] or
             not x['separate']['joint_optimal'] or x['union'] is None or x['union']['status']=='UNRESOLVED']
    stamp=time.strftime('%Y%m%d-%H%M%S')
    path=OUT/f'closure-{stamp}.jsonl';assert not path.exists()
    progress=OUT/f'bounded-attempts-{stamp}';progress.mkdir()
    start=time.monotonic();print('Pending full-grid targets:',len(pending),flush=True)
    with path.open('w') as f,multiprocessing.get_context('spawn').Pool(4) as pool:
        for i,r in enumerate(pool.imap_unordered(close,[(x,str(progress)) for x in pending]),1):
            f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush()
            c=r['closed']
            print(i,len(pending),r['key'],c['joint']['status'],c['separate']['status'],
                  c['union']['status'] if c['union'] else None,round(time.monotonic()-start,1),flush=True)
    path.with_suffix('.json').write_text(json.dumps(dict(status='COMPLETED_CLOSURE_ATTEMPT_PENDING_AUDIT',
        cases=len(pending),seconds=time.monotonic()-start,progress_directory=str(progress.relative_to(ROOT))),indent=2)+'\n')

if __name__=='__main__':
    if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
    main()

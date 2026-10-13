"""Frozen comparison; never changes previous score or certificate records."""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[name]='1'
import argparse,json,multiprocessing,time,sys
from pathlib import Path
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
from deduplicated_certificates import union_certificate
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/deduplicated-evidence'

def sources():
    cases=[]
    for line in (ROOT/'outputs/joint-certificates/instances.jsonl').open():
        x=json.loads(line)
        if x['key'][1]!='mean':continue
        for r in x['records']:
            cases.append(dict(scope='small',dataset=r['dataset'],split=r['split'],q=r['q'],
                history=r['history'],epsilon=r['epsilon'],rows=x['flips'],caps=x['caps'],
                observed=x['observed'][r['history']],budget=r['budget'],N=r['N'],k=r['k'],T=r['T'],
                joint_minimum=r['queries'],additive_minimum=r['split_queries']))
    primary=[json.loads(line) for line in (ROOT/'outputs/outcome-joint-scale/records.jsonl').open()]
    index={(x['dataset'],x['split'],x['q'],x['requested_size']):x for x in primary}
    for line in (ROOT/'outputs/outcome-joint-scale/retry-records.jsonl').open():
        r=json.loads(line)
        if r['joint_optimal'] and r['separated_optimal']:
            key=tuple(r['primary_key']);index[key]=dict(index[key],**r)
    for x in index.values():
        if x['requested_size']!='full':continue
        assert x['joint_optimal'] and x['separated_optimal']
        cases.append(dict(scope='full',dataset=x['dataset'],split=x['split'],q=x['q'],history='empty',
            epsilon=0,rows=x['rows'],caps=x['caps'],observed=x['observed'],budget=x['budget'],N=x['N'],k=x['k'],T=x['T'],
            joint_minimum=x['queries'],additive_minimum=x['split_queries']))
    assert len(cases)==3936
    return cases

def task(case):
    spec=json.loads((ROOT/'review-revision/deduplicated-evidence-implementation/protocol.json').read_text())
    result=union_certificate(case['rows'],case['caps'],case['budget'],case['epsilon'],case['observed'],seconds=spec['seconds_per_solver'])
    if result['status']=='OPTIMAL':
        assert result['split_minimum']==case['additive_minimum']
        assert case['joint_minimum']<=result['union_minimum']<=case['additive_minimum']
    if case['scope']=='small':
        independent=union_certificate(case['rows'],case['caps'],case['budget'],case['epsilon'],case['observed'],seconds=spec['seconds_per_solver'],independent=True)
        if result['status']==independent['status']=='OPTIMAL':assert independent['union_minimum']==result['union_minimum'] and independent['split_minimum']==result['split_minimum']
        result['independent']=independent
    return dict(case,result=result,mode='fresh_optimization')

def main():
    assert not OUT.exists(),'Append-only experiment: do not replace a completed attempt'
    OUT.mkdir();cases=sources();fresh=[];inferred=[]
    for x in cases:
        if x['joint_minimum']==x['additive_minimum']:
            inferred.append(dict(x,mode='bound_sandwich',result=dict(status='PROVED_BY_EXISTING_BOUNDS',union_minimum=x['joint_minimum'])))
        else:fresh.append(x)
    start=time.monotonic();progress=dict(status='RUNNING',total_cases=len(cases),inferred=len(inferred),fresh_expected=len(fresh),fresh_done=0)
    def save():
        progress['elapsed_seconds']=time.monotonic()-start;(OUT/'run_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    save();print('inferred',len(inferred),'fresh',len(fresh),flush=True)
    with (OUT/'records.jsonl').open('w') as f:
        for x in inferred:f.write(json.dumps(x,separators=(',',':'))+'\n')
        f.flush()
        with multiprocessing.get_context('spawn').Pool(4) as pool:
            for x in pool.imap_unordered(task,fresh,chunksize=1):
                f.write(json.dumps(x,separators=(',',':'))+'\n');f.flush();progress['fresh_done']+=1;save()
                if progress['fresh_done']%40==0 or x['scope']=='full':print(progress['fresh_done'],'/',len(fresh),x['scope'],x['result']['status'],round(time.monotonic()-start,1),flush=True)
    progress['status']='COMPLETE_EXECUTION_PENDING_AUDIT';save()

if __name__=='__main__':main()

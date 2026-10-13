"""Complete original mean grid; append-only minimum-certificate attempts."""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']: os.environ[key]='1'
import argparse
import hashlib
import json
import math
import multiprocessing
import sys
import time
from pathlib import Path
import numpy as np
import psutil
from analyze_acquisition_mechanisms import prepare
from variable_target_certificate import certificate
from deduplicated_certificates import union_certificate
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'review-revision/evidence-discovery-implementation-20261005'
OUT=ROOT/'outputs/full-mean-grid-20261005'
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh']

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def task(key):
    panel, rep, q=key
    c=prepare((panel,'mean',rep,q))
    ids=np.flatnonzero(c['selected']);ids=ids[np.argsort(c['tie'][ids])]
    rows=c['f'][:,ids].T.tolist();caps=c['p'][ids].tolist()
    records=[]
    for stopping,eps in [('exact',0),('primary',math.ceil(.02*len(ids)))]:
        before=time.monotonic()
        value=certificate(rows,caps,c['budget'],eps,seconds=60)
        split=certificate(rows,caps,c['budget'],eps,seconds=60,separated=True)
        union=None
        if value['joint_optimal'] and split['joint_optimal'] and value['objective']==split['objective']:
            union=dict(status='PROVED_BY_BOUND_SANDWICH',union_minimum=value['objective'])
        elif value['joint_optimal'] and split['joint_optimal']:
            union=union_certificate(rows,caps,c['budget'],eps,seconds=120)
            if union['status']=='OPTIMAL':
                assert union['split_minimum']==split['objective']
                assert value['objective']<=union['union_minimum']<=split['objective']
        records.append(dict(dataset=panel,split=rep,q=q,stopping=stopping,epsilon=eps,
                N=c['N'],k=c['k'],T=c['T'],budget=c['budget'],alpha=.10,
                selected_count=len(ids),active_rows=sum(p>0 for p in caps),
                original_output_ids=ids.tolist(),rows=rows,caps=caps,observed=[0]*len(ids),
                history='empty',joint=value,separate=split,union=union,
                total_seconds=time.monotonic()-before,sampled_final_process_rss=psutil.Process().memory_info().rss))
    return records

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');a=parser.parse_args()
    if a.freeze:
        assert not (RUN/'full-mean-protocol.json').exists()
        sources=['scripts/variable_target_certificate.py','scripts/run_full_mean_grid.py','scripts/deduplicated_certificates.py','scripts/analyze_acquisition_mechanisms.py','scripts/mapping_column_experiments.py']
        spec=dict(panels=PANELS,splits=list(range(40)),q=[.05,.10,.20,.30],alpha=.10,
            stopping=['exact','primary'],epsilon='0 or ceil(.02*original_selected_count)',
            history='empty',full_original_N_and_family=True,expected_instances=960,expected_records=1920,
            workers=4,joint_seconds=60,separate_seconds=60,union_seconds_per_target_solver=120,
            baseline_and_policy_inputs_not_changed=True,preregistered_unseen_evaluation=False,
            setup_validation='160 finite independent enumerations and three existing full tasks',
            source_bindings={n:sha(ROOT/n) for n in sources})
        (RUN/'full-mean-protocol.json').write_text(json.dumps(spec,indent=2)+'\n');print('Frozen full 960-instance grid');return
    assert not OUT.exists();OUT.mkdir()
    spec=json.loads((RUN/'full-mean-protocol.json').read_text())
    assert all(sha(ROOT/n)==h for n,h in spec['source_bindings'].items())
    start=time.monotonic();progress=dict(status='RUNNING',records=0,expected_records=1920)
    def save():
        progress['elapsed_seconds']=time.monotonic()-start
        (OUT/'run_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    save();keys=[(p,s,q) for s in spec['splits'] for q in spec['q'] for p in PANELS]
    with (OUT/'records.jsonl').open('w') as f,multiprocessing.get_context('spawn').Pool(spec['workers']) as pool:
        for group in pool.imap_unordered(task,keys):
            for x in group:f.write(json.dumps(x,separators=(',',':'))+'\n')
            f.flush();progress['records']+=len(group);save()
            if progress['records']%80==0: print(progress['records'],'/1920',round(time.monotonic()-start,1),flush=True)
    assert progress['records']==1920
    progress['status']='COMPLETE_EXECUTION_PENDING_AUDIT';save()
    assert all(sha(ROOT/n)==h for n,h in spec['source_bindings'].items())

if __name__=='__main__':
    if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
    main()

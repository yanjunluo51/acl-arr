"""Full original mean panels with one method and its two component ablations."""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[key]='1'
import argparse,gzip,hashlib,json,math,multiprocessing,sys,time
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from frontier_priority import acquire
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'review-revision/evidence-discovery-implementation-20261005'
OUT=ROOT/'outputs/frontier-priority-20261005'
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh']

def task(key):
    started=time.monotonic();panel,rep,q=key;c=prepare((panel,'mean',rep,q))
    ids=c['ids'];ids=ids[np.argsort(c['tie'][ids])]
    truth=c['f'][:,ids].T;prior=c['prior'][ids];caps=c['p'][ids]
    free=c['S']-len(ids);paths=[]
    for mode in ['joint','safety','exclusion']:
        t=time.monotonic()
        path=acquire(caps,prior,c['budget'],math.ceil(.02*c['S']),lambda i,r:int(truth[i,r]),mode)
        path['seconds']=time.monotonic()-t
        for stop in path['stops'].values():stop['V_lower']+=free;stop['V_upper']+=free
        paths.append(path)
    return dict(dataset=panel,split=rep,q=q,N=c['N'],k=c['k'],T=c['T'],budget=c['budget'],
        selected_count=c['S'],active_rows=len(ids),free=free,original_output_ids=ids.tolist(),
        caps=caps.tolist(),paths=paths,total_seconds=time.monotonic()-started)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');a=parser.parse_args()
    if a.freeze:
        assert not (RUN/'frontier-protocol.json').exists()
        files=['scripts/frontier_priority.py','scripts/run_frontier_priority.py','scripts/query_selection.py','scripts/analyze_acquisition_mechanisms.py']
        spec=dict(panels=PANELS,splits=list(range(40)),q=[.05,.10,.20,.30],alpha=.10,
            pooling='mean',workers=3,instances=960,paths=2880,stops=5760,
            policy='frontier_priority',ablations=['safety','exclusion'],
            predictor='original reference-only ridge, sum-squared-error plus unit penalty, unpenalized intercept',
            prior_ticks='clipped to [0,p_i], rounded at 1e-12',
            target='estimated capacity clipped to [current Vminus+1,current Vplus]',
            safety='predicted cheapest target rows; upper-cost excess over budget',
            exclusion='target+1 lower-cost threshold deficit, threshold ceil(predicted order statistic)',
            utility='unit-weight sum of normalized predicted safety and exclusion deficit decreases',
            ties='original label-blind row tie order then candidate index, utility ticks 1e-12',
            fallback='largest current width if every predicted score is zero',
            acquisition_tolerance_independent=True,first_primary_and_exact_stops=True,
            hidden_test_scores_visible_only_in_query_callback=True,quality_labels_used=False,
            tuning_on_test_results=False,preregistered_unseen_evaluation=False,
            source_bindings={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files})
        (RUN/'frontier-protocol.json').write_text(json.dumps(spec,indent=2)+'\n');print('Frozen full frontier method and ablations');return
    spec=json.loads((RUN/'frontier-protocol.json').read_text());assert not OUT.exists();OUT.mkdir()
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in spec['source_bindings'].items())
    start=time.monotonic();progress=dict(status='RUNNING',instances=0,expected=960)
    def save():
        progress['elapsed_seconds']=time.monotonic()-start;(OUT/'run_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    save();keys=[(p,s,q) for s in spec['splits'] for q in spec['q'] for p in PANELS]
    with gzip.open(OUT/'traces.jsonl.gz','wt',compresslevel=1) as f,multiprocessing.get_context('spawn').Pool(spec['workers']) as pool:
        for x in pool.imap_unordered(task,keys):
            f.write(json.dumps(x,separators=(',',':'))+'\n');f.flush();progress['instances']+=1;save()
            if progress['instances']%40==0:print(progress['instances'],'/960',round(time.monotonic()-start,1),flush=True)
    assert progress['instances']==960
    progress['status']='COMPLETE_EXECUTION_PENDING_AUDIT';save()
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in spec['source_bindings'].items())

if __name__=='__main__':
    if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
    main()

"""Rebuild frozen inputs from pinned public sources on the reader's machine.

No third-party response text is written. Existing inputs are never overwritten.
Acquisition does not establish permission to redistribute downloaded scores.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RB_REV = 'b19c7033e964187d12e74a43a07f2d727a3d37e5'
WMT_REV = '56352a3d563d371622935c84974b3f215abeede3'

def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as f:
        return f.read()

def rb():
    models = json.loads((ROOT/'evidence/source-model-files.json').read_text())
    def one(entry):
        name, path = entry
        d = json.loads(fetch('https://huggingface.co/datasets/allenai/reward-bench-2-results/resolve/'+RB_REV+'/'+path))
        assert len(d['id']) == len(d['subset']) == len(d['scores'])
        keep = {}
        for pid, subset, scores in zip(d['id'], d['subset'], d['scores']):
            if subset == 'Ties' or len(scores) != 4:
                continue
            vals = [x[0] if isinstance(x,list) and len(x)==1 else x for x in scores]
            if all(isinstance(x,(float,int)) for x in vals):
                keep[str(pid)] = {'subset':subset, 'scores':list(map(float,vals))}
        return name, keep
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        per = dict(pool.map(one, models))
    common = sorted(set.intersection(*(set(per[m]) for m,_ in models)), key=int)
    out = {'models':[m for m,_ in models], 'prompt_ids':common,
           'subset':{p:per[models[0][0]][p]['subset'] for p in common},
           'scores':{m:{p:per[m][p]['scores'] for p in common} for m,_ in models},
           'source':'allenai/reward-bench-2-results eval-set-scores',
           'note':('items are (prompt, completion) pairs; the Ties subset and any '
                   'prompt without exactly four completions are excluded')}
    return json.dumps(out).encode('utf-8')

def pearson(a,b):
    n=len(a);ma=sum(a)/n;mb=sum(b)/n
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    da=sum((x-ma)**2 for x in a)**.5
    db=sum((y-mb)**2 for y in b)**.5
    return num/(da*db) if da and db else 0.

def wmt():
    url='https://huggingface.co/datasets/tttonyyy/mt-metrics-eval-v2/resolve/'+WMT_REV+'/mt-metrics-eval-v2.tgz'
    inside='mt-metrics-eval-v2/wmt23/metric-scores/en-de/'
    suffix='-refA.seg.score'
    raws={}
    with urllib.request.urlopen(url,timeout=60) as f:
        with tarfile.open(fileobj=f,mode='r|gz') as tf:
            for member in tf:
                if member.isfile() and member.name.startswith(inside) and member.name.endswith(suffix):
                    raws[Path(member.name).name[:-len(suffix)]]=tf.extractfile(member).read()
    seen,dropped={},{}
    order=[]
    for m in sorted(raws):
        digest=hashlib.sha256(raws[m]).hexdigest()
        if digest in seen:
            dropped[m]=seen[digest]
        else:
            seen[digest]=m;order.append(m)
    parsed={}
    for m in order:
        per={}
        for line in raws[m].decode('utf-8').splitlines():
            name,value=line.split('\t');per.setdefault(name,[]).append(float(value))
        parsed[m]=per
    common=set.intersection(*(set(parsed[m]) for m in order))
    union=set.union(*(set(parsed[m]) for m in order))
    systems=sorted(common);extra=sorted(union-common)
    n=len(parsed[order[0]][systems[0]])
    assert all(len(parsed[m][s])==n for m in order for s in systems)
    ids=['seg%04d'%i for i in range(n)]
    scores={m:{sid:[parsed[m][s][i] for s in systems] for i,sid in enumerate(ids)} for m in order}
    flat={m:[v for sid in ids for v in scores[m][sid]] for m in order}
    corr={m:pearson(flat['BLEURT-20'],flat[m]) for m in order}
    assert all(v>0 for v in corr.values())
    out={'models':order,'prompt_ids':ids,'systems':systems,
         'subset':{sid:'wmt23-en-de' for sid in ids},'scores':scores,
         'source':'WMT23 metrics task, en-de, reference-based submissions',
         'note':('items are (source segment, system) pairs; only refA '
                 'submissions are kept, byte-identical duplicates are dropped, '
                 'and every metric is verified to correlate positively with '
                 'BLEURT-20 before use'),
         'dropped_duplicates':dropped,'dropped_systems':extra,
         'orientation_check':{'anchor':'BLEURT-20','min_correlation':min(corr.values()),
                              'metric_at_min':min(corr,key=corr.get)}}
    return (json.dumps(out,indent=1,sort_keys=True)+'\n').encode('utf-8')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',type=Path,default=ROOT/'data')
    args=p.parse_args()
    expected=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,builder in [('rb2_ranked_panel.json',rb),('wmt23_metric_panel.json',wmt)]:
        target=args.output_dir/name
        digest=expected['data/'+name]
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest()==digest, 'Existing input differs; preserving it: '+str(target)
            print(name,'existing frozen input verified',flush=True)
            continue
        raw=builder()
        assert hashlib.sha256(raw).hexdigest()==digest, 'Pinned reconstruction differs; no file written: '+name
        with target.open('xb') as f:
            f.write(raw)
        print(name,'exact frozen input rebuilt',flush=True)
    print('Reconstruction completed. This does not clear redistribution rights.',flush=True)

if __name__=='__main__':
    main()

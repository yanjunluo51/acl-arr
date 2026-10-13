"""Independently bind admitted panels, reference-only orientation and frozen inputs."""
from pathlib import Path
import json, gzip, hashlib, collections, random
import numpy as np
P=Path(__file__).resolve().parent; R=P.parents[2]
spec=json.loads((P/'protocol.json').read_text())
for n,h in spec['source_bindings'].items():
    assert hashlib.sha256((R/'scripts'/n).read_bytes()).hexdigest()==h
counts={}; cases=set()
for lp in spec['panels']:
    z=np.load(P/f'{lp}.npz'); ids=z['ids']; systems=z['systems'].tolist()
    docs=['::'.join(s.split()) for s in (P/'raw-private/documents'/f'{lp}.docs').read_text().splitlines()]
    assert z['documents'].tolist()==[docs[i] for i in ids]
    for j,model in enumerate(z['models']):
        rows=collections.defaultdict(list)
        for s in (P/'raw-private/metric-scores'/lp/f'{model}-refA.seg.score').read_text().splitlines():
            system,v=s.split(); rows[system].append(float(v))
        values=np.array([[rows[s][i] for s in systems] for i in ids])
        assert np.array_equal(values,z['scores'][j]) and np.isfinite(values).all()
    units=list(dict.fromkeys(z['documents'].tolist()))
    random.Random(spec['seed']+1000*spec['panels'].index(lp)).shuffle(units)
    third=len(units)//3; groups=[set(units[:third]),set(units[third:2*third]),set(units[2*third:])]
    g=len(systems); positions=[[i*g+j for i,d in enumerate(z['documents']) if d in s for j in range(g)] for s in groups]
    raw=z['scores'].reshape(len(z['models']),-1); ref=raw[:,positions[0]]
    anchor=ref[z['models'].tolist().index('BLEURT-20')]; a=anchor-anchor.mean()
    # The sign of covariance equals that of correlation when both vary.
    direction=[-1 if float(np.dot(row-row.mean(),a))<0 else 1 for row in ref]
    for f in sorted((P/'cases').glob(lp+'_*.json.gz')):
        x=json.load(gzip.open(f,'rt')); key=(lp,x['pooling'],x['q']); assert key not in cases; cases.add(key)
        assert x['reference_output_ids']==positions[0] and x['test_output_ids']==positions[2]
        assert x['orientation']==direction
        assert x['models']==z['models'].tolist()
        assert x['N']==len(positions[2]) and x['T']==len(z['models'])-7
        assert x['k']==max(1,round(x['q']*x['N']))
        assert x['budget']==2*x['k']*7*x['T']//10
        oriented=raw*np.array(direction)[:,None]
        mapped=np.array([np.searchsorted(np.sort(r[positions[0]]),r[positions[2]],side='right')/len(positions[0]) for r in oriented])
        base=mapped[:7]
        def pool(v):
            if x['pooling']=='median': return np.sort(v,axis=0)[3]
            total=np.zeros(v.shape[1])
            for row in v: total=total+row
            return total/7
        selected=pool(base)>=x['cutoff']; cap=np.zeros(x['N'],dtype=int); flips=np.zeros((x['T'],x['N']),dtype=int)
        for i in range(7):
            a=base.copy();a[i]=np.where(selected,0.,1.);cap+=(pool(a)>=x['cutoff'])!=selected
            for j in range(x['T']):
                a=base.copy();a[i]=mapped[7+j];flips[j]+=(pool(a)>=x['cutoff'])!=selected
        seed=spec['seed']+1000*spec['panels'].index(lp)
        tie=np.random.default_rng(seed+700001).permutation(x['N'])
        selected_ids=np.flatnonzero(selected); selected_ids=selected_ids[np.argsort(tie[selected_ids])]
        assert x['rows']==flips[:,selected_ids].T.tolist() and x['caps']==cap[selected_ids].tolist()
        expected=set(spec['methods']) | (set(spec['mean_extra']) if x['pooling']=='mean' else set())
        assert set(x['policies'])==expected
    counts[lp]=dict(documents=len(units),reference_documents=len(groups[0]),calibration_documents=len(groups[1]),test_documents=len(groups[2]),test_outputs=len(positions[2]))
assert cases=={(p,a,q) for p in spec['panels'] for a in spec['pooling'] for q in spec['q']}
out=dict(status='PASS_SOURCE_BLOCKS_REFERENCE_ORIENTATION_AND_FROZEN_CASES',cases=len(cases),panels=counts,
         input_hashes={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [P/'protocol.json',P/'admission.json',*sorted(P.glob('*.npz')),*sorted((P/'cases').glob('*.gz'))]})
(P/'admission-check.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='input_hashes'},indent=2))

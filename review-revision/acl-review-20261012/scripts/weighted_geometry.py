"""Full-retention geometry under the seeded candidate weights for all 960 mean instances."""
import json, multiprocessing, numpy as np
from common import EXP, PANELS, QS, SPLITS, instance, capacity
def task(key):
    panel,rep,q=key; c=instance(panel,'mean',rep,q); T=c['T']
    rng=np.random.default_rng(31012027+1000*PANELS.index(panel)+10*rep+int(round(100*q)))
    w=rng.integers(1,4,size=T); W=int(w.sum()); budget=(2*c['k']*7*W)//10
    g=(c['truth']*w[None,:]); Lw=capacity(g.sum(axis=1),budget) if c['m'] else 0
    Lu=capacity(c['truth'].sum(axis=1),c['budget']) if c['m'] else 0
    return dict(dataset=panel,split=rep,q=q,m=int(c['m']),S=int(c['S']),eps=int(c['epsilon']),Lw=int(Lw),Lu=int(Lu),T=int(T))
if __name__=='__main__':
    keys=[(p,s,q) for q in QS for p in PANELS for s in SPLITS]
    with multiprocessing.get_context('spawn').Pool(4) as pool: R=pool.map(task,keys)
    (EXP/'outputs'/'weighted_geometry.json').write_text(json.dumps(R)+'\n')
    nu=sum(r['Lu']<r['m'] for r in R); nw=sum(r['Lw']<r['m'] for r in R)
    both=sum(r['Lu']<r['m'] and r['Lw']<r['m'] for r in R)
    print('nonfull uniform',nu,'weighted',nw,'both',both)
    import collections; print(collections.Counter((r['dataset'],r['q']) for r in R if r['Lw']<r['m']))
    print(sorted((r['m']*r['T'],r['dataset'],r['split'],r['q']) for r in R if r['Lw']<r['m'])[:10])

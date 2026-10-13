"""Official missing-information sentinel probes; descriptive, no pool filtering."""
from pathlib import Path
import json,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'review-revision/acquisition/extracted/mt-metrics-eval-v2/wmt24'

def read(p):
    out={}
    for line in p.read_text().splitlines():
        s,v=line.split();out.setdefault(s,[]).append(None if v=='None' else float(v))
    return out

def main():
    records=[];cached=json.loads((ROOT/'data/wmt24_sentinel_probes.json').read_text())['panels']
    for lp in ['en-de','en-es','ja-zh']:
        panel=json.loads((ROOT/'data'/f'wmt24_{lp}_panel.json').read_text());gold=json.loads((ROOT/'data'/f'wmt24_{lp}_mqm.json').read_text());ids=[int(i) for i in panel['prompt_ids']];systems=panel['systems'];ref=panel['reference']
        y=np.array([gold['mqm'][str(i)] for i in ids],dtype=float)
        for name in [f'sentinel-src-mqm-src',f'sentinel-ref-mqm-{ref}']:
            frozen=cached[lp];assert frozen['systems']==systems and frozen['paragraph_ids']==panel['prompt_ids']
            if name not in frozen['scores']:records.append({'language':lp,'probe':name,'status':'ABSENT_FROM_OFFICIAL_RELEASE'});continue
            x=np.array([[frozen['scores'][name][s][j] for s in systems] for j in range(len(ids))],dtype=float);observed=np.isfinite(y)&np.isfinite(x)
            pearson=float(np.corrcoef(x[observed],y[observed])[0,1]) if np.std(x[observed])>0 and np.std(y[observed])>0 else None
            pairs=tied=agree=0
            for r in range(len(ids)):
                ix=np.flatnonzero(observed[r])
                for a,b in itertools.combinations(ix,2):
                    if y[r,a]==y[r,b]:continue
                    pairs+=1;d=x[r,a]-x[r,b];tied+=d==0;agree+=.5 if d==0 else ((d>0)==(y[r,a]>y[r,b]))
            records.append({'language':lp,'probe':name,'status':'OBSERVED','annotated_entries':int(observed.sum()),'pooled_pearson':pearson,'within_paragraph_non_gold_tie_pairs':pairs,'within_paragraph_metric_tie_fraction':tied/pairs if pairs else None,'within_paragraph_pair_accuracy_ties_half':agree/pairs if pairs else None,'candidate_family_changed':False})
    out=ROOT/'outputs/review-sentinel';out.mkdir(exist_ok=True);(out/'results.json').write_text(json.dumps({'status':'PASS_DESCRIPTIVE_OFFICIAL_PROBE_DIAGNOSTIC','records':records,'scope':'Missing-information controls on observed native MQM only; pooled association is not evidence of translation discrimination or identification of invalid real evaluators. No candidate deletion or refitting.'},indent=2,allow_nan=False)+'\n');print(json.dumps(records,indent=2))
if __name__=='__main__':main()

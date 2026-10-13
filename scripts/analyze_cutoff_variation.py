"""Descriptive within-split cutoff spread; no population CI or pooled split SD."""
import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def summarize(root):
 rows=[json.loads(s) for s in (root/'outputs/cutoff-bootstrap/records.jsonl').open()];out=[]
 for panel in sorted({x['dataset'] for x in rows}):
  for agg in ['median','mean']:
   for arm in ['cutoff_only','maps_and_cutoff']:
    sd=[]
    for split in range(8):
     g=[x for x in rows if (x['dataset'],x['aggregator'],x['arm'],x['split'])==(panel,agg,arm,split)];assert len(g)==50 and len({x['draw'] for x in g})==50
     sd.append(statistics.stdev(x['cutoff'] for x in g))
    out.append(dict(dataset=panel,aggregator=agg,arm=arm,splits=8,draws_per_split=50,cutoff_sd_mean=statistics.fmean(sd),cutoff_sd_min=min(sd),cutoff_sd_max=max(sd)))
 return out
if __name__=='__main__':
 out=summarize(ROOT)
 with (ROOT/'outputs/cutoff-bootstrap/cutoff_variation.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
 print(json.dumps(dict(status='PASS_WITHIN_SPLIT_CUTOFF_VARIATION',cells=len(out),ddof=1,aggregation='mean of eight within-split 50-draw sample SDs',population_CI=False)))

"""Expose all independently replayed policies in the existing 48-row summary."""
from pathlib import Path
import csv,json,gzip
P=Path(__file__).resolve().parent
assert json.loads((P/'audit.json').read_text())['paths']==132
rows=list(csv.DictReader((P/'summary.csv').open()))
for row in rows:
    x=json.load(gzip.open(P/'cases'/f"{row['panel']}_{row['pooling']}_{float(row['q']):.2f}.json.gz",'rt'))
    for name,field in [('fixed','fixed_queries'),('random','random_queries'),('frontier_exclusion','exclusion_queries')]:
        row[field]=x['policies'].get(name,{}).get(row['stopping'],{}).get('queries','')
with (P/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

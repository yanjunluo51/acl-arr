"""Final deterministic count-display and editorial layer over original renderers."""
import json,re
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'manuscript/tables'
LABELS={'RewardBench 2':'RewardBench2','WMT23, 13 streams':'WMT23','WMT23, 12 streams':'WMT23_without_synthetic_ref'}
METHODS={'No queries':'zero_query_structural','Envelope CRC':'envelope_crc','Batch threshold':'batch_uniform_threshold','Batch cardinality':'batch_max_cardinality','Batch retention':'batch_selected_optimum','Fixed-count retention':'fixed_count_batch_selected_optimum'}
def avg(rows,field):
 assert len(rows)==40,(len(rows),field)
 vals=[Decimal(str(x[field])) for x in rows]
 assert all(v==int(v) for v in vals),field
 return format((sum(vals)/Decimal(len(vals))).quantize(Decimal('.1'),rounding=ROUND_HALF_UP),'.1f')
def main():
 x=json.loads((ROOT/'outputs/query_metrics.json').read_text());changed=[];checks=[]
 for path in sorted(T.glob('*.tex')):
  name=path.name;text=path.read_text();new=[]
  for line in text.splitlines():
   if ' & ' in line and line.rstrip().endswith(r'\\'):
    fields=line.rstrip()[:-2].rstrip().split(' & ')
    if name=='query-baselines.tex' and fields[0] in LABELS:
     panel=LABELS[fields[0]];q=.05;pool='median';method=METHODS[fields[1]]
     rows=[r for r in x['baseline_records'] if (r['dataset'],r['aggregator'],r['q'],r['method'])==(panel,pool,q,method)]
     fields[4]=avg(rows,'returned_count');checks.append([name,panel,pool,q,method,fields[4]])
    elif name.startswith('query-full-baselines-') and re.fullmatch(r'0\.\d+',fields[0]):
     ind,pool=name.removeprefix('query-full-baselines-').removesuffix('.tex').split('-')
     panel=x['protocol']['panels'][int(ind)];q=float(fields[0]);method=METHODS[fields[1]]
     rows=[r for r in x['baseline_records'] if (r['dataset'],r['aggregator'],r['q'],r['method'])==(panel,pool,q,method)]
     fields[4]=avg(rows,'returned_count');checks.append([name,panel,pool,q,method,fields[4]])
    elif name=='query-certificates.tex' and fields[0] in LABELS:
     panel=LABELS[fields[0]];q=float(fields[1])
     rows=[r for r in x['query_records'] if (r['dataset'],r['aggregator'],r['q'],r['method'],r['stopping'])==(panel,'median',q,'reference_priority','exact_gap')]
     fixed=[r for r in x['query_records'] if (r['dataset'],r['aggregator'],r['q'],r['method'],r['stopping'])==(panel,'median',q,'fixed','exact_gap')]
     fields[2:]=[avg(rows,k) for k in ['offline_exact_safe_part','offline_exact_exclusion_part','offline_exact_certificate']]+[avg(fixed,'queries'),avg(rows,'queries')]
     checks.append([name,panel,q,fields[2:]])
    elif name=='query-quality.tex' and fields[0] in ['median','mean']:
     pool,q,method=fields[0],float(fields[1]),fields[2].replace(r'\_','_')
     rows=[r for r in x['query_records'] if (r['dataset'],r['aggregator'],r['q'],r['method'],r['stopping'])==('RewardBench2',pool,q,method,'two_percent_gap')]
     fields[3]=avg(rows,'returned_count');checks.append([name,pool,q,method,fields[3]])
    line=' & '.join(fields)+r' \\'
   new.append(line)
  text2='\n'.join(new)+'\n'
  text2=text2.replace('after with the first quarter','after observing the first quarter')
  text2=text2.replace('All online traces meet this lower bound.','All online query counts are at least this matching lower bound.')
  if name in ['query-baselines.tex','query-quality.tex','query-certificates.tex'] or name.startswith('query-full-baselines-'):
   # Caption only: make display convention explicit without changing selection rounding.
   note='Count means use decimal half-up rounding after aggregating integer records. '
   if note not in text2:text2=text2.replace(r'\caption{',r'\caption{'+note,1)
  if text2!=text:path.write_text(text2);changed.append(name)
 (ROOT/'review-revision/editorial-integration-20261006/display-check.json').write_text(json.dumps(dict(status='PASS_INTEGER_COUNT_REAGGREGATION',count_cells=len(checks),changed=changed,cells=checks,selection_rounding_changed=False),indent=2)+'\n')
 print('Count display checked:',len(checks),'changed tables:',len(changed))
if __name__=='__main__':main()

"""Final review layer: exact integer-count rounding and evidence-bound captions.
Run after historical renderers. It refuses changed numerical bodies and does not
execute scorers, optimizers or acquisition policies.
"""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import csv,json,hashlib,re,collections
ROOT=Path(__file__).resolve().parents[1]; RUN=ROOT/'review-revision/editorial-precision-followthrough'
def fmt(v):return format(v.quantize(Decimal('.1'),rounding=ROUND_HALF_UP),'.1f')
def body(s):return '\n'.join(re.findall(r'\\midrule(.*?)\\bottomrule',s,re.S))
def main():
 z=json.loads((ROOT/'outputs/mapping-column/results.json').read_text());g=collections.defaultdict(list)
 for r in z['geometry']:
  if r['aggregator']=='median':g[(r['dataset'],r['q'],r['reference_fraction'],r['cdf'])].append(r)
 assert len(g)==144
 means={}
 for k,rs in g.items():
  assert len(rs)==40 and all(isinstance(r['offline_exact_certificate'],int) for r in rs)
  means[k]=Decimal(sum(r['offline_exact_certificate'] for r in rs))/40
 panels=z['protocol']['panels'];labels=['RewardBench 2','WMT23, 13 streams','WMT23, 12 streams','WMT24 en-de','WMT24 en-es','WMT24 ja-zh'];lookup=dict(zip(labels,panels))
 for name in ['mapping-summary.tex','mapping-all-depths.tex']:
  p=ROOT/'manuscript/tables'/name;s=p.read_text();lines=[];section=-1
  for line in s.splitlines():
   if line.startswith('\\begin{table'):section+=1
   if ' & ' in line and line.rstrip().endswith(r'\\'):
    v=line.rstrip()[:-2].rstrip().split(' & ')
    if (name=='mapping-summary.tex' and len(v)>1 and v[1]=='median') or (name=='mapping-all-depths.tex' and v[0]=='median'):
     panel=lookup[v[0]] if name=='mapping-summary.tex' else panels[section];q=.05 if name=='mapping-summary.tex' else float(v[1]);vals=[x for k,x in means.items() if k[:2]==(panel,q)];assert len(vals)==6
     lo,hi=fmt(min(vals)),fmt(max(vals));v[5]=lo if lo==hi else lo+'--'+hi;line=' & '.join(v)+r' \\'
   lines.append(line)
  p.write_text('\n'.join(lines)+'\n')
 specfile=RUN/'table-spec.json'
 if specfile.exists():
  for name,item in json.loads(specfile.read_text()).items():
   p=ROOT/name;digest=hashlib.sha256(body(p.read_text()).encode()).hexdigest()
   assert digest in item['allowed_numeric_sha256'],('different table results',name)
   p.write_text(item['content'])
 # Two matched tolerance cells from saved records: a diagnostic reaggregation.
 rows=list(csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open()));lines=[]
 for tau,label in [('1/50','.02'),('1/10','.10')]:
  vals=[]
  for method in ['fixed','random','largest_width','reference_priority']:
   rs=[x for x in rows if x['dataset']=='WMT23' and x['aggregator']=='mean' and float(x['q'])==.3 and x['tau']==tau and x['method']==method];assert len(rs)==40
   vals.append(fmt(Decimal(sum(int(x['queries']) for x in rs))/40))
  lines.append(label+' & '+' & '.join(vals)+r' \\')
 text=r'''\begin{table}[t]
\centering\small
\begin{tabular}{rrrrr}
\toprule
$\eta$ & Fixed & Random & Width & Ref. \\
\midrule
'''+ '\n'.join(lines)+r'''
\bottomrule
\end{tabular}
\caption{Mean queries on thirteen-stream WMT23, mean pooling, $q=.30$, $\alpha=.10$: the same 40 splits and fixed paths, with stopping gap $\lceil\eta|S_0|\rceil$. Counts are reaggregated from saved records and rounded half up. Width has the lowest mean at $.02$, fixed order at $.10$.}
\label{tab:tolerance-order-check}
\end{table}
'''
 (ROOT/'manuscript/tables/tolerance-order-check.tex').write_text(text)
 result=dict(status='PASS_PRECISION_TABLE_LAYER',median_protocol_means=144,integer_records=5760,tolerance_records=320,selection_rounding_changed=False,scorer_rerun=False)
 (RUN/'render-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()

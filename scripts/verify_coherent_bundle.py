"""Read saved evidence and verify the current coherent revision; optional clean replay."""
import argparse,csv,hashlib,json,subprocess,sys
from pathlib import Path
from fractions import Fraction
from verify_editorial_bundle import main as prior
ROOT=Path(__file__).resolve().parents[1]
def costcheck(root, audited_rows=None):
 # Bind cached audit rows to freshly checked original witnesses and closure chains.
 # A clean CSV plus a clean derived CSV is not enough if both drift together.
 if audited_rows is None:
  from audit_full_mean_grid import audit
  _,audited_rows=audit(root,source=False,write=False)
 orig=list(csv.DictReader((root/'outputs/full-mean-grid-20261005/audited_records.csv').open()))
 key=lambda x:(str(x['dataset']),str(x['split']),str(x['q']),str(x['stopping']))
 truth={key(r):{k:str(v) for k,v in r.items()} for r in audited_rows}
 lookup={key(r):r for r in orig}
 assert len(orig)==len(lookup)==len(truth)==1920 and lookup==truth,'cached audit differs from original witnesses'
 derived=list(csv.DictReader((root/'outputs/evidence-cost-contrasts/records.csv').open()))
 methods=['fixed','random','largest_width','reference_priority','frontier_joint','frontier_safety','frontier_exclusion']
 expected_keys={(*k,m) for k in lookup for m in methods};seen=set()
 def equal(actual,expected,label):
  assert set(actual)==set(expected),('schema',label,set(actual)^set(expected))
  for f,v in expected.items():
   if isinstance(v,Fraction):
    import math
    z=float(actual[f]);assert math.isfinite(z) and math.isclose(z,float(v),rel_tol=1e-12,abs_tol=1e-9),(label,f,actual[f],str(v))
   else:assert actual[f]==str(v),(label,f,actual[f],str(v))
 for r in derived:
  k=(*key(r),r['method']);assert k in expected_keys and k not in seen,k;seen.add(k);x=lookup[key(r)]
  q=int(x[r['method']+'_queries']);jl,ju,sl,su=[int(x[f]) for f in ['joint_lower','joint_upper','split_lower','split_upper']]
  jp,up=int(x['joint_proven']),int(x['union_proven']);u=int(x['union_minimum']) if up else None
  expected={f:x[f] for f in ['dataset','split','q','stopping','epsilon','N','k','T','budget','selected_count']}
  expected.update(history='empty',aggregator='mean',alpha='1/10',maps='full-reference right ECDF',query_unit='additional unit-cost entries',method=r['method'],joint_lower=jl,joint_upper=ju,joint_proven=jp,split_lower=sl,split_upper=su,union_proven=up,union_minimum=u if up else '',online_queries=q,dedup_saving=su-u if up else '',joint_gain=u-ju if up else '',online_excess_lower=max(0,q-ju),online_excess_upper=q-jl,online_excess=q-ju if jp else '',online_ratio=Fraction(q,ju) if jp and ju>0 else '',zero_minimum=int(jp and ju==0),unresolved_joint_gain_lower=0 if not up else '',unresolved_joint_gain_upper=su-jl if not up else '')
  equal(r,expected,k)
 assert seen==expected_keys and len(derived)==13440
 rows=list(csv.DictReader((root/'outputs/evidence-cost-contrasts/summary.csv').open()))
 expected_summaries={(p,s,m) for p in ['ALL']+sorted({x['dataset'] for x in orig}) for s in ['primary','exact'] for m in methods};seen_summary=set()
 for s in rows:
  sk=s['dataset'],s['stopping'],s['method'];assert sk in expected_summaries and sk not in seen_summary,sk;seen_summary.add(sk)
  g=[r for r in derived if r['stopping']==s['stopping'] and r['method']==s['method'] and (s['dataset']=='ALL' or r['dataset']==s['dataset'])]
  c=[r for r in g if int(r['union_proven'])]
  ratios=sorted(Fraction(int(r['online_queries']),int(r['joint_upper'])) for r in g if int(r['joint_proven']) and int(r['joint_upper'])>0)
  expected=dict(dataset=s['dataset'],stopping=s['stopping'],method=s['method'],tasks=len(g),closed_union=len(c),closed_joint=sum(int(r['joint_proven']) for r in g),zero_minima=sum(int(r['zero_minimum']) for r in g),positive_ratio_n=len(ratios))
  for f in ['dedup_saving','joint_gain','online_excess']:
   vals=[int(r[f]) for r in c];total=sum(vals)
   expected[f+'_sum_closed_union']=total;expected[f+'_mean_closed_union']=Fraction(total,len(c));expected[f+'_positive_closed_union']=sum(v>0 for v in vals)
  for bound in ['lower','upper']:expected['online_excess_mean_'+bound+'_all']=Fraction(sum(int(r['online_excess_'+bound]) for r in g),len(g))
  n=len(ratios);expected['online_ratio_median_positive']=(ratios[n//2] if n%2 else (ratios[n//2-1]+ratios[n//2])/2) if n else ''
  equal(s,expected,sk)
 assert seen_summary==expected_summaries and len(rows)==98,'missing or duplicate summary'
 return dict(targets=len(lookup),policy_records=len(derived),summaries=len(rows),unresolved_joint=sum(not int(r['joint_proven']) for r in orig),unresolved_union=sum(not int(r['union_proven']) for r in orig),fresh_witness_binding=True,all_record_and_summary_fields_checked=True)
def grids(root):
 import re
 p=root/'manuscript/supplement';data=json.loads((p/'result_grids.json').read_text());rows=list(csv.DictReader((p/'result_grids.csv').open()));n=0
 expected={f'{stem}-{i}-{pool}' for stem in ['query-full-baselines','review-budget','review-score'] for i in range(3) for pool in ['median','mean']};seen=set()
 for t in data['tables']:
  name=t['table_id'];assert name in expected and name not in seen,name;seen.add(name)
  src=(root/'manuscript/tables'/f'{name}.tex').read_text();assert t['source_latex']==src
  assert t['labels']==re.findall(r'\\label\{([^}]+)\}',src)
  independent=[]
  for no,line in enumerate(src.splitlines(),1):
   if '&' in line and line.rstrip().endswith(chr(92)*2):
    independent.append(dict(table_id=name,source_line=no,row_index=len(independent),cells_latex=[c.strip() for c in line.rstrip()[:-2].split('&')]))
  assert t['rows']==independent
  for r in independent:
   c=rows[n];assert c['table_id']==name and int(c['source_line'])==r['source_line'] and int(c['row_index'])==r['row_index']
   assert [c[f'cell_{i+1}_latex'] for i in range(len(r['cells_latex']))]==r['cells_latex']
   assert all(v=='' for k,v in c.items() if k.startswith('cell_') and int(k.split('_')[1])>len(r['cells_latex']));n+=1
 assert seen==expected and n==len(rows)==408
 return dict(tables=18,rows=n,lossless=True,unique_grid_inventory_and_source_rows_checked=True)
def main(root=ROOT,replay=False):
 result={'prior':prior(root,replay=replay),'costs':costcheck(root),'grids':grids(root)}
 if replay:
  files=list((root/'outputs/evidence-cost-contrasts').glob('*'))+list((root/'manuscript/supplement').glob('*'))+[root/'manuscript/tables/cost-contrasts.tex']
  hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
  for name in ['analyze_evidence_cost_contrasts.py','export_result_grids.py']:subprocess.run([sys.executable,str(root/'scripts'/name)],cwd=root,check=True,stdout=sys.stderr)
  assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
 result['status']='PASS_SAVED_EVIDENCE_COST_CONTRASTS_AND_GRID_SUPPLEMENT';return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--replay-tables',action='store_true');a=p.parse_args();print(json.dumps(main(replay=a.replay_tables),indent=2))

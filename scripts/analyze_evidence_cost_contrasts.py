"""Matched cost contrasts from saved complete-batch mean records; no solver calls."""
import csv,json,statistics
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/evidence-cost-contrasts'
METHODS=['fixed','random','largest_width','reference_priority','frontier_joint','frontier_safety','frontier_exclusion']
def writecsv(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def compute(root=ROOT):
 source=list(csv.DictReader((root/'outputs/full-mean-grid-20261005/audited_records.csv').open()))
 original={(r['dataset'],int(r['split']),float(r['q']),'exact' if r['tau']=='0' else 'primary',r['method']):r for r in csv.DictReader((root/'outputs/tolerance-sensitivity/stop_records.csv').open()) if r['aggregator']=='mean' and r['tau'] in ['0','1/50']}
 new={(r['dataset'],int(r['split']),float(r['q']),r['stopping'],'frontier_'+r['method']):r for r in csv.DictReader((root/'outputs/frontier-priority-20261005/records.csv').open())}
 records=[];seen=set()
 for x in source:
  key=x['dataset'],int(x['split']),float(x['q']),x['stopping'];assert key not in seen;seen.add(key)
  jl,ju,sl,su=[int(x[f]) for f in ['joint_lower','joint_upper','split_lower','split_upper']]
  jp,sp,up=[bool(int(x[f])) for f in ['joint_proven','split_proven','union_proven']]
  assert 0<=jl<=ju and sl<=su and (not jp or jl==ju) and (not sp or sl==su)
  u=int(x['union_minimum']) if up else None
  if up:assert jp and sp and jl<=u<=su
  for method in METHODS:
   q=int(x[method+'_queries']);saved=(new if method.startswith('frontier_') else original)[(*key,method)]
   assert q==int(saved['queries']) and q>=jl
   if not method.startswith('frontier_'):assert int(saved['integer_budget'])==int(x['budget']) and int(saved['selected_count'])==int(x['selected_count'])
   r={k:x[k] for k in ['dataset','split','q','stopping','epsilon','N','k','T','budget','selected_count']}
   r.update(history='empty',aggregator='mean',alpha='1/10',maps='full-reference right ECDF',query_unit='additional unit-cost entries',method=method,joint_lower=jl,joint_upper=ju,joint_proven=int(jp),split_lower=sl,split_upper=su,union_proven=int(up),union_minimum=u if up else '',online_queries=q,dedup_saving=su-u if up else '',joint_gain=u-ju if up else '',online_excess_lower=max(0,q-ju),online_excess_upper=q-jl,online_excess=q-ju if jp else '',online_ratio=q/ju if jp and ju>0 else '',zero_minimum=int(jp and ju==0),unresolved_joint_gain_lower=0 if not up else '',unresolved_joint_gain_upper=su-jl if not up else '')
   records.append(r)
 assert len(seen)==1920 and len(records)==13440
 summaries=[]
 for panel in ['ALL']+sorted({x['dataset'] for x in records}):
  for stop in ['primary','exact']:
   for method in METHODS:
    g=[x for x in records if (panel=='ALL' or x['dataset']==panel) and x['stopping']==stop and x['method']==method]
    c=[x for x in g if x['union_proven']];positive=[x['online_ratio'] for x in g if x['online_ratio']!='']
    r=dict(dataset=panel,stopping=stop,method=method,tasks=len(g),closed_union=len(c),closed_joint=sum(x['joint_proven'] for x in g),zero_minima=sum(x['zero_minimum'] for x in g),positive_ratio_n=len(positive))
    for name in ['dedup_saving','joint_gain','online_excess']:
     vals=[x[name] for x in c];r[name+'_sum_closed_union']=sum(vals);r[name+'_mean_closed_union']=statistics.fmean(vals);r[name+'_positive_closed_union']=sum(v>0 for v in vals)
    r['online_excess_mean_lower_all']=statistics.fmean(x['online_excess_lower'] for x in g);r['online_excess_mean_upper_all']=statistics.fmean(x['online_excess_upper'] for x in g)
    r['online_ratio_median_positive']=statistics.median(positive) if positive else ''
    summaries.append(r)
 return records,summaries

def render(root,summaries):
 names={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13','WMT23_without_synthetic_ref':'WMT23, 12','ALL':'All panels'}
 rows=[r for r in summaries if r['method']=='reference_priority']
 lines=[r'\begin{table*}[t]',r'\centering\small',r'\begin{tabular}{llrrrr}',r'\toprule',r'Panel & Stop & Closed / tasks & Dedup. & Joint & Discovery \\',r'\midrule']
 for r in rows:
  name=names.get(r['dataset'],r['dataset'].replace('_',r'\_'))
  values=[(Decimal(r[n+'_sum_closed_union'])/Decimal(r['closed_union'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for n in ['dedup_saving','joint_gain','online_excess']]
  lines.append(f"{name} & {r['stopping']} & {r['closed_union']} / {r['tasks']} & "+' & '.join(f'{v:.2f}' for v in values)+r' \\')
 lines += [r'\bottomrule',r'\end{tabular}',r'\caption{Complete-batch mean cost contrasts at $\alpha=.10$, all four depths. On the same closed-union tasks, columns average $Q_{\rm split}-Q_{\cup,\rm sep}$ (Dedup.), $Q_{\cup,\rm sep}-Q_{\rm joint}$ (Joint), and $Q_{\rm ref}-Q_{\rm joint}$ (Discovery), in score entries. These are separate contrasts, not additive components. Primary uses $\varepsilon=\lceil.02|S_0|\rceil$; exact uses zero. Empty histories, maps, budgets and stopping targets match. Machine-readable records retain all targets, bounds for unresolved minima, zero minima and all seven policies.}',r'\label{tab:cost-contrasts}',r'\end{table*}']
 (root/'manuscript/tables/cost-contrasts.tex').write_text('\n'.join(lines)+'\n')
def main():
 records,summaries=compute();OUT.mkdir(exist_ok=True)
 writecsv(OUT/'records.csv',records);writecsv(OUT/'summary.csv',summaries);render(ROOT,summaries)
 p=[r for r in summaries if r['dataset']=='ALL' and r['method']=='reference_priority']
 (OUT/'analysis.json').write_text(json.dumps(dict(status='MATCHED_SAVED_RECORD_ANALYSIS',records=len(records),targets=1920,policies=METHODS,reference_summary=p,new_scorer_or_solver_runs=False),indent=2)+'\n')
 print(json.dumps(p,indent=2))
if __name__=='__main__':main()

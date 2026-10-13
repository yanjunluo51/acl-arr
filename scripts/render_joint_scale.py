"""Rebuild four tables from saved resource, optimum and bootstrap evidence."""
import json,csv,statistics
from pathlib import Path
from render_joint_revision import table,PANELS,NAMES
ROOT=Path(__file__).resolve().parents[1]
def load(n):return json.loads((ROOT/n).read_text())
def main():
 rows=[]
 for x in load('outputs/joint-scale/audit.json')['summaries']:
  rows.append([str(x['size']),str(x['paired_proven'])+'/384',f"{x['runtime_median']:.3f}",f"{x['runtime_p90']:.3f}",f"{x['sampled_rss_p90_mib']:.1f}"])
 table('joint-dp-resources.tex',['Selected size','Both proved','Median (s)','90th pct. (s)','90th MiB'],rows,r'Cached row-state DP resource study: six panels, splits 0--7, $q\in\{.05,.30\}$, empty/quarter histories and exact/primary gaps give 384 instances per size. Subbatches reset $N,k,b_H$; full preserves the original test task. Both proved counts completed joint and separate minima. Limits are 100,000 reachable states, ten million transitions and 60 seconds shared by the two optimizations. Resource-limited rows retain valid witnesses without claiming minima. Times include unresolved attempts; RSS is sampled every 10 ms and includes Python, inputs and caches. Six concurrent workers share a workstation; these are not controlled speedup measurements.','tab:joint-dp-resources')
 dp=[json.loads(s) for s in (ROOT/'outputs/joint-scale/records.jsonl').open()];d=load('outputs/compact-joint-scale/audit.json')['summaries'];o=load('outputs/outcome-joint-scale/audit.json')['summaries'];rows=[]
 for a,b in zip(d,o):
  g=[x for x in dp if x['requested_size']==a['size'] and x['history']=='empty' and x['stopping']=='exact'];assert len(g)==96
  rows.append([str(a['size']),str(sum(x['joint_optimal'] and x['separated_optimal'] for x in g))+'/96',str(a['paired_proven'])+'/96',str(b['paired_proven'])+'/96',str(b['max_variables']),f"{b['runtime_median']:.3f}"])
 table('joint-compact-resources.tex',['Size','Row DP','Entry MILP','Outcome MILP','Max vars','Median (s)'],rows,r'Matching empty-history exact mean tasks at $\alpha=.10$: 96 cases per size. Counts require both joint and separate optima within the primary resource budget. Each MILP backend receives 60 seconds shared between these optimizations; DP additionally has state/transition limits. Outcome MILP groups equal integer flip contributions (Proposition~\ref{prop:compact-joint}); its median time includes unresolved attempts. It proves 573/576 pairs in the primary run. Append-only retries prove two more; exhaustive feasible-threshold decomposition proves the last joint minimum, completing all 576 pairs. Initial censoring remains in this table. Max vars counts the largest solved formulation, not a bound on solve time.','tab:joint-compact-resources')
 r=list(csv.DictReader((ROOT/'outputs/outcome-joint-scale/full_discovery_summary.csv').open()));d={(x['dataset'],float(x['q']),x['method']):x for x in r};rows=[]
 for p,n in zip(PANELS,NAMES):
  for q in [.05,.30]:
   a=d[p,q,'reference_priority'];assert a['splits']=='8' and a['positive_minima']=='8'
   rows.append([n,f'{q:.2f}',f"{float(a['minimum_mean']):.1f}"]+[f"{float(d[p,q,m]['ratio_mean']):.3f}" for m in ['fixed','random','largest_width','reference_priority']])
 table('joint-full-discovery.tex',['Panel',r'$q$',r'Mean $Q_{\rm joint}$','Fixed','Random','Width','Reference'],rows,r'Full-test mean entry minima and online discovery at exact stopping, $\alpha=.10$, splits 0--7. Every row averages eight original full tasks with positive minima; ratio columns average the splitwise $Q_{\rm online}/Q_{\rm joint}$, not a ratio of means. All four original query paths are unchanged. Across 96 minima and 384 paths, every online count is at least its matching minimum. Strict shared-proof savings occur in 4/96 tasks: 2,645 entries out of 435,876 separately minimized proof entries (0.607\%). These denominators are not used for positive-tolerance stops.','tab:joint-full-discovery')
 s=load('outputs/cutoff-bootstrap/audit.json')['summaries'];d={(x['dataset'],x['aggregator'],x['arm']):x for x in s};rows=[]
 for p,n in zip(PANELS,NAMES):
  for agg in ['median','mean']:
   a=d[p,agg,'cutoff_only'];b=d[p,agg,'maps_and_cutoff']
   rows.append([n,agg,f"{a['jaccard_median']:.3f}",f"{b['jaccard_median']:.3f}",f"{100*a['zero_stop_fraction']:.1f}",f"{100*b['zero_stop_fraction']:.1f}",str(a['median_exact_minimum_median']) if agg=='median' else '--',str(b['median_exact_minimum_median']) if agg=='median' else '--'])
 table('cutoff-bootstrap.tex',['Panel','Pool',r'$J_t$',r'$J_{\rm map+t}$',r'Zero $t$ (\%)',r'Zero map+$t$ (\%)',r'$Q_{0,t}$',r'$Q_{0,\rm map+t}$'],rows,r'Reference-group bootstrap at $q=.05$, $\alpha=.10$: 50 paired draws in each of eight splits, 400 instances per cell. $t$ resamples the reference-consensus cutoff while retaining original maps; map+$t$ refits ECDFs and cutoff on the same resampled prompt/source/document groups. Test groups and the evaluator family stay fixed. $J$ is median baseline-selection Jaccard against the original split. Zero reports the fraction meeting the primary count-gap stop without queries; $Q_0$ is the median matching exact entry minimum, reported only for median pooling. Every draw defines a changed fixed protocol. Percentiles in the saved records are descriptive bootstrap summaries, not population confidence intervals. No label-based tuning or new online acquisition is performed.','tab:cutoff-bootstrap')
if __name__=='__main__':main()

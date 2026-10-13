"""Render every current table and figure from completed query experiment files."""
from pathlib import Path
import json, math, statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype']=42
matplotlib.rcParams['svg.fonttype']='none'
matplotlib.rcParams['font.family']='serif'
matplotlib.rcParams['font.serif']=['Times New Roman','Times','cmr10']
matplotlib.rcParams['mathtext.fontset']='stix'
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
X=json.loads((ROOT/'outputs/query_metrics.json').read_text())
A=json.loads((ROOT/'outputs/query_analysis.json').read_text())
T=ROOT/'paper/tables';T.mkdir(exist_ok=True)
B={(r['dataset'],r['aggregator'],r['q'],r['method']):r for r in X['baseline_cells']}
Q={(r['dataset'],r['aggregator'],r['q'],r['method'],r['stopping']):r for r in X['query_cells']}
D={(r['dataset'],r['aggregator'],r['q'],r['stopping']):{m['method']:m for m in r['methods']} for r in A['cells']}
labels={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13 streams','WMT23_without_synthetic_ref':'WMT23, 12 streams'}
methods=['fixed','random','largest_width','reference_priority']
short={'zero_query_structural':'No queries','envelope_crc':'Envelope CRC','batch_uniform_threshold':'Batch threshold','batch_max_cardinality':'Batch cardinality','batch_selected_optimum':'Batch retention','fixed_count_batch_selected_optimum':'Fixed-count retention'}


def fmt(x,n=2):return '--' if x is None else f'{x:.{n}f}'


def table(file,caption,label,cols,head,rows):
    text='\\begin{table*}[t]\n\\centering\\small\n'
    text+='\\begin{tabular}{'+cols+'}\n\\toprule\n'+head+r' \\'+'\n\\midrule\n'
    text+='\n'.join(' & '.join(row)+r' \\' for row in rows)
    text+='\n\\bottomrule\n\\end{tabular}\n\\caption{'+caption+'}\n\\label{'+label+'}\n\\end{table*}\n'
    (T/file).write_text(text)


rows=[]
for panel in X['protocol']['panels']:
 for method in short:
    c=B[panel,'median',.05,method]
    rows.append([labels[panel],short[method],fmt(c['risk'],3),fmt(100*c['selected_coverage'],1),fmt(c['returned_count'],1),fmt(c['precision'],3)])
table('query-baselines.tex',r'Median, top-5\%, $\alpha=0.10$: full-information controls and the structural zero-query baseline. Selected coverage uses each rule\textquotesingle s own base list. CRC controls expectation; batch methods enforce the realized budget. Fixed count has a different base list. Counts and ratios are separately averaged over 40 splits. These WMT23 panels have no quality labels.', 'tab:baselines','llrrrr',r'Panel & Policy & Risk & Sel.\ cov.\ (\%) & Returned & Precision',rows)
rows=[]
for agg in X['protocol']['aggregators']:
 for panel in X['protocol']['panels']:
    vals=[Q[panel,agg,.05,m,'two_percent_gap'] for m in methods]
    ds=D[panel,agg,.05,'two_percent_gap']['fixed']
    rows.append([labels[panel],agg,fmt(100*ds['zero_query_fraction'],1)]+[fmt(100*r['active_fraction'],1) for r in vals]+[fmt(100*vals[-1]['selected_coverage'],1)])
table('query-stopping.tex',r'Top-5\% stopping at $V^+-V^-\le\lceil0.02|S_0|\rceil$. Z is the fraction of splits stopping without inspecting candidate test scores. The four strategy columns give mean inspections as a percentage of active selected entries ($mT$); their common structural pruning is already removed from this denominator. Ref.\ is reference priority. Coverage refers to its returned base-selected outputs.', 'tab:stopping','llrrrrrr',r'Panel & Pooling & Z (\%) & Fixed & Random & Width & Ref. & Cov.\ (\%)',rows)
rows=[]
for panel in X['protocol']['panels']:
 for q in [.05,.1]:
    ref=Q[panel,'median',q,'reference_priority','exact_gap'];fixed=Q[panel,'median',q,'fixed','exact_gap']
    rows.append([labels[panel],fmt(q,2),fmt(ref['offline_exact_safe_part'],1),fmt(ref['offline_exact_exclusion_part'],1),fmt(ref['offline_exact_certificate'],1),fmt(fixed['queries'],1),fmt(ref['queries'],1)])
table('query-certificates.tex',r'Median exact certification: offline agreement and opposition witnesses versus online inspections. Each column is a mean over 40 splits. The offline sum is an instance certificate cost, not a query budget attainable by an uninformed strategy. All online traces meet this lower bound.', 'tab:certificates','lrrrrrr',r'Panel & $q$ & Safety & Exclusion & Offline & Fixed & Ref.',rows)
for stop,file,lab in [('two_percent_gap','query-all-tolerant.tex','tab:all-tolerant'),('exact_gap','query-all-exact.tex','tab:all-exact')]:
 rows=[]
 for panel in X['protocol']['panels']:
  for agg in X['protocol']['aggregators']:
   for q in X['protocol']['quantiles']:
    vals=[Q[panel,agg,q,m,stop] for m in methods];d=D[panel,agg,q,stop]['fixed']
    rows.append([labels[panel],agg,fmt(q,2),fmt(100*d['zero_query_fraction'],1)]+[fmt(100*r['active_fraction'],1) for r in vals]+[fmt(100*vals[-1]['selected_coverage'],1),fmt(vals[-1]['certificate_gap'],1)])
 table(file,r'All configurations, '+('integer two-percent tolerance' if stop=='two_percent_gap' else 'exact gap-zero stopping')+r'. Strategy columns are mean active-entry inspection percentages; Z is the zero-query split percentage. Cov.\ and gap refer to reference priority. No independent-population inference is taken from these overlapping splits.',lab,'llrrrrrrrr',r'Panel & Pooling & $q$ & Z & Fixed & Random & Width & Ref. & Cov. & Gap',rows)
for index,panel in enumerate(X['protocol']['panels']):
 for agg in X['protocol']['aggregators']:
  rows=[]
  for q in X['protocol']['quantiles']:
   for method in short:
    c=B[panel,agg,q,method]
    rows.append([fmt(q,2),short[method],fmt(c['risk'],3),fmt(100*c['selected_coverage'],1),fmt(c['returned_count'],1),fmt(c['precision'],3)])
  table(f'query-full-baselines-{index}-{agg}.tex',labels[panel]+', '+agg+r': all depths and all full-information controls. Selected coverage denominators are policy-specific; precision is omitted without native quality labels.',f'tab:baseline-{index}-{agg}','llrrrr',r'$q$ & Policy & Risk & Sel.\ cov.\ (\%) & Returned & Precision',rows)
rows=[]
for agg in X['protocol']['aggregators']:
 for q in X['protocol']['quantiles']:
  for method in methods:
   c=next(v for v in A['quality_cells'] if (v['aggregator'],v['q'],v['method'],v['stopping'])==(agg,q,method,'two_percent_gap'))
   rows.append([agg,fmt(q,2),method.replace('_',r'\_'),fmt(c['K'],1),fmt(c['precision'],3),fmt(c['same_K_score_precision'],3),fmt(c['precision_delta'],4)])
table('query-quality.tex',r'RewardBench matched-throughput diagnostic. Each returned count $K$ is compared against the same-consensus top-$K$ rule with label-blind seeded tie priorities. The comparison has no risk certificate. This descriptive analysis was added after the inspection protocol; labels never enter acquisition or stopping.', 'tab:query-quality','lllr rrr',r'Pooling & $q$ & Strategy & $K$ & Precision & Top-$K$ & Difference',rows)
fig,axes=plt.subplots(2,3,figsize=(6.3,4.0),layout='constrained',sharex=True)
colors=['#666666','#D55E00','#0072B2','#CC79A7'];names=['Fixed','Random','Width','Reference']
markers=['o','s','^','D'];styles=['--',':','-.','-']
for row,agg in enumerate(['median','mean']):
 for col,panel in enumerate(X['protocol']['panels']):
  ax=axes[row,col]
  for method,color,name,marker,style in zip(methods,colors,names,markers,styles):
   ys=[]
   for frac in X['protocol']['inspection_checkpoints']:
    records=[r for r in X['checkpoint_records'] if r['dataset']==panel and r['aggregator']==agg and r['q']==.05 and r['method']==method and r['allowance_queries']==math.ceil(frac*r['active_selected_items']*r['T'])]
    assert len(records)==40,(panel,agg,method,frac,len(records))
    ys.append(statistics.fmean(r['selected_coverage'] for r in records))
   ax.plot(X['protocol']['inspection_checkpoints'],ys,color=color,marker=marker,linestyle=style,markersize=3,label=name,linewidth=1.2)
  opt=B[panel,agg,.05,'batch_selected_optimum']['selected_coverage']
  ax.axhline(opt,color='black',linestyle=':',linewidth=.8)
  ax.set_title(labels[panel]+' / '+agg,fontsize=9)
  ax.tick_params(labelsize=8);ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
  if col==0:ax.set_ylabel('Selected coverage',fontsize=9)
  if row==1:ax.set_xlabel('Allowed fraction of active entries',fontsize=9)
handles,legend_labels=axes[0,0].get_legend_handles_labels()
fig.legend(handles,legend_labels,loc='outside upper center',ncol=4,fontsize=9,frameon=False)
fig.savefig(ROOT/'paper/query-frontiers.pdf');fig.savefig(ROOT/'paper/query-frontiers.png',dpi=200);fig.savefig(ROOT/'paper/query-frontiers.svg')
# Text numbers are also generated, so no hand-transcribed result can drift.
macros=[]
for panel,prefix in [('RewardBench2','rb'),('WMT23','wmt'),('WMT23_without_synthetic_ref','excl')]:
 zero=B[panel,'median',.05,'zero_query_structural'];opt=B[panel,'median',.05,'batch_selected_optimum']
 ref=Q[panel,'median',.05,'reference_priority','two_percent_gap']
 macros += ['\\newcommand{\\'+prefix+'ZeroCov}{'+fmt(100*zero['selected_coverage'],1)+'}','\\newcommand{\\'+prefix+'OptCov}{'+fmt(100*opt['selected_coverage'],1)+'}','\\newcommand{\\'+prefix+'Active}{'+fmt(100*ref['active_fraction'],1)+'}']
(T/'query-numbers.tex').write_text('\n'.join(macros)+'\n')
print('Rendered current query figures and tables from complete outputs.')

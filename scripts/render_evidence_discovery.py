"""Render audited evidence-discovery tables with no values invented."""
import csv,json,statistics
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP,ROUND_FLOOR,ROUND_CEILING
ROOT=Path(__file__).resolve().parents[1];TAB=ROOT/'manuscript/tables'
NAMES={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13','WMT23_without_synthetic_ref':'WMT23, 12','WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
def read(name):return list(csv.DictReader((ROOT/'outputs'/name/'summary.csv').open()))
def n(v,d=1):return format(Decimal(str(v)).quantize(Decimal('1').scaleb(-d),rounding=ROUND_HALF_UP),f'.{d}f')
def table(cols,head,rows,caption,label):
 return '\n'.join([r'\begin{table*}[t]',r'\centering\small',r'\setlength{\tabcolsep}{4pt}',r'\begin{tabular}{'+cols+'}',r'\toprule',head+r' \\',r'\midrule',*[(' & '.join(row)+r' \\') for row in rows],r'\bottomrule',r'\end{tabular}',r'\caption{'+caption+'}',r'\label{'+label+'}',r'\end{table*}',''])
def main():
 assert json.loads((ROOT/'outputs/frontier-priority-20261005/audit.json').read_text())['instances']==960
 f=read('frontier-priority-20261005');ix={(r['dataset'],float(r['q']),r['stopping'],r['method']):r for r in f}
 for stop in ['primary','exact']:
  rows=[]
  for p,label in NAMES.items():
   for q in [.05,.1,.2,.3]:
    j,s,e=[ix[(p,q,stop,m)] for m in ['joint','safety','exclusion']]
    rows.append([label,n(q,2),*[n(j[k]) for k in ['reference_priority_queries','largest_width_queries','queries']],n(s['queries']),n(e['queries']),j['wins_reference']+'/'+j['losses_reference'],j['wins_width']+'/'+j['losses_width']])
  caption=r'Mean-pooling acquisition at '+(r'$V^+-V^-\le\lceil .02|S_0|\rceil$' if stop=='primary' else r'$V^+=V^-$')+r', $\alpha=.10$, on complete original batches. Query columns average entry counts across all 40 splits. Frontier balances safety and exclusion deficits; S-only and E-only omit one component. W/L counts Frontier strict wins/losses against Reference or Width; remaining splits tie. All methods use the same reference data, updates and certification target, and no quality labels. These descriptive comparisons do not establish a universally best policy.'
  (TAB/('frontier-'+stop+'.tex')).write_text(table('lrrrrrrrr',r'Panel & $q$ & Reference & Width & Frontier & S-only & E-only & W/L Ref. & W/L Width',rows,caption,'tab:frontier-'+stop))
 c=read('common-information-20261005');ix={(r['dataset'],r['aggregator'],float(r['q']),r['method']):r for r in c}
 labels={'zero_query_structural':'Zero','reference_priority':'Reference','envelope_crc':'CRC','grouped_score_mdr':'SCoRE'}
 # Resolve saved canonical SCoRE method without renaming records.
 scoremethods={r['method'] for r in c if r['certificate']=='expectation_mdr'}
 if not scoremethods:scoremethods={r['method'] for r in c if 'score' in r['method'].lower()}
 assert len(scoremethods)==1;score=next(iter(scoremethods));labels[score]='SCoRE'
 text=''
 for p in list(NAMES)[:3]:
  for pool in ['median','mean']:
   rows=[]
   for q in [.05,.1,.2,.3]:
    for method in ['zero_query_structural','reference_priority','envelope_crc',score]:
     r=ix[(p,pool,q,method)]
     rows.append([n(q,2),labels[method],n(r['returned_count']),n(float(r['selected_coverage'])*100),n(r['risk'],3),r['over_budget'],*[n(r['candidate_'+stage+'_over_NT'],3) for stage in ['reference','calibration','test','total']]])
   caption=NAMES[p]+', '+pool+r' pooling, $\alpha=.10$: common recorded churn and candidate-score accounting. $K$ is returned count; Cov.\ is selected coverage in percent; Over counts batches above budget out of 40. Ref., Cal., Test and Total are logical candidate entries divided by the same test $NT$; Total includes the three stages and can exceed one. Counts and ratios are splitwise means. Reference uses the primary count-gap stop. Zero and Reference give deterministic batch feasibility; CRC and SCoRE give expectation guarantees under group exchangeability, so Over does not refute these guarantees. SCoRE decides whole groups. Reference setup is charged as recorded, not minimized. Pool scores and panel-preprocessing reads are separate; full matrices used only for posthoc validation are outside selection-visible information. Full pool-stage counts accompany the records.'
   text+=table('rlrrrrrrrr',r'$q$ & Method & $K$ & Cov. & Risk & Over & Ref. & Cal. & Test & Total',rows,caption,'tab:common-'+p.replace('_','-')+'-'+pool)
 (TAB/'common-information.tex').write_text(text)
 p=read('protocol-evidence-20261005');rows=[]
 for panel,label in NAMES.items():
  for frac in ['1','1/2','1/4']:
   for cdf in ['right','midrank']:
    r=next(r for r in p if r['dataset']==panel and r['reference_fraction']==frac and r['cdf']==cdf and float(r['q'])==.05)
    rows.append([label,frac,'Right' if cdf=='right' else 'Mid',*[n(r[k]) for k in ['selected_count','initial_gap','invariant_retained','noninvariant_zero_retained','offline_exact_certificate']],n(r['base_list_jaccard'],3)])
 (TAB/'protocol-evidence.tex').write_text(table('lllrrrrrr',r'Panel & Ref. & ECDF & $|S_0|$ & Initial gap & Inv. & Noninv. & $Q_0$ & Jaccard',rows,r'Median protocol sensitivity at $q=.05$, $\alpha=.10$, means over 40 fixed test splits. Ref.\ is the fraction of reference groups. Initial gap is $|S_0|-V(u^{(0)})$; Inv.\ and Noninv.\ decompose zero-query retention. $Q_0$ is the matching exact entry minimum for each changed protocol. Jaccard compares its baseline selected set with full-reference right ECDF on the same split. These joint descriptions connect changed selection tasks to evidence requirements; they are not same-instance acquisition interventions or an endorsement of a mapping.', 'tab:protocol-evidence'))
 if (ROOT/'outputs/full-mean-grid-20261005/summary.csv').exists():
  rs=read('full-mean-grid-20261005')
  for stop in ['primary','exact']:
   rows=[]
   for panel,label in NAMES.items():
    for q in [.05,.1,.2,.3]:
     r=next(r for r in rs if r['dataset']==panel and float(r['q'])==q and r['stopping']==stop)
     bound=n(r['mean_joint_upper']) if int(r['joint_proven'])==40 else format(Decimal(r['mean_joint_lower']).quantize(Decimal('.1'),rounding=ROUND_FLOOR),'.1f')+'--'+format(Decimal(r['mean_joint_upper']).quantize(Decimal('.1'),rounding=ROUND_CEILING),'.1f')
     rows.append([label,n(q,2),bound,r['joint_proven'],r['positive_minima'],*[n(r[k+'_ratio'],3) if r[k+'_ratio'] else '--' for k in ['reference_priority','largest_width','frontier_joint']],r['joint_below_union']+'/'+r['union_proven']])
   caption=r'Full-batch mean evidence from empty history, $\alpha=.10$, '+(r'$\varepsilon=\lceil .02|S_0|\rceil$' if stop=='primary' else r'$\varepsilon=0$')+r'. All four depths and 40 original splits are included. $Q$ averages the matching minimum when all 40 are proved; otherwise it shows mean lower--upper bounds with outward-rounded endpoints. Proven counts closed joint minima; $n_+$ counts proved positive minima. Ref., Width and Frontier average $Q_{\rm online}/Q$ only on these $n_+$ matching instances, with zero minima excluded. Gain/n counts $Q_{\rm joint}<Q_{\cup,\rm sep}$ among n closed union comparisons. No unresolved upper bound is treated as a minimum. Candidate-test score entries are the cost unit.'
   (TAB/('full-mean-'+stop+'.tex')).write_text(table('lrrrrrrrr',r'Panel & $q$ & Mean $Q$ & Proven & $n_+$ & Ref. & Width & Frontier & Gain/n',rows,caption,'tab:full-mean-'+stop))
 print('Rendered frontier, common information, protocol and available full-mean summaries')
if __name__=='__main__':main()

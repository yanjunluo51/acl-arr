"""Main-text synthesis from audited complete-grid and acquisition records."""
import csv,json,statistics
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP,ROUND_FLOOR,ROUND_CEILING
ROOT=Path(__file__).resolve().parents[1];T=ROOT/'manuscript/tables'
NAMES={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13','WMT23_without_synthetic_ref':'WMT23, 12','WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
def fmt(x,n=1):return format(Decimal(str(x)).quantize(Decimal('1').scaleb(-n),rounding=ROUND_HALF_UP),f'.{n}f')
def main():
 rows=list(csv.DictReader((ROOT/'outputs/full-mean-grid-20261005/audited_records.csv').open()));assert len(rows)==1920
 out=[]
 for panel,label in NAMES.items():
  a=[r for r in rows if r['dataset']==panel];p=[r for r in a if r['stopping']=='primary'];e=[r for r in a if r['stopping']=='exact']
  assert len(a)==320 and len(p)==len(e)==160
  closed=sum(int(r['joint_proven']) for r in a)
  lo=statistics.fmean(int(r['joint_lower']) for r in p);hi=statistics.fmean(int(r['joint_upper']) for r in p)
  q=fmt(hi) if lo==hi else format((Decimal(sum(int(r['joint_lower']) for r in p))/len(p)).quantize(Decimal('.1'),rounding=ROUND_FLOOR),'.1f')+'--'+format((Decimal(sum(int(r['joint_upper']) for r in p))/len(p)).quantize(Decimal('.1'),rounding=ROUND_CEILING),'.1f')
  ratios=[]
  for group in [p,e]:
   good=[r for r in group if r['reference_priority_ratio']!=''];ratios.append(fmt(statistics.fmean(float(r['reference_priority_ratio']) for r in good),3) if good else '--')
  unions=[r for r in a if int(r['union_proven'])]
  gain=sum(int(r['joint_upper'])<int(r['union_minimum']) for r in unions)
  out.append(' & '.join([label,str(closed)+'/320',q,*ratios,str(gain)+'/'+str(len(unions))])+r' \\')
 text='\n'.join([r'\begin{table*}[t]',r'\centering\small',r'\begin{tabular}{lrrrrr}',r'\toprule',r'Panel & Closed targets & Primary $Q$ & Primary Ref./$Q$ & Exact Ref./$Q$ & Strict gain/closed unions \\',r'\midrule',*out,r'\bottomrule',r'\end{tabular}',r'\caption{Full-test mean evidence at $\alpha=.10$: four depths, 40 splits, and two count-gap targets per panel. Primary uses $\varepsilon=\lceil .02|S_0|\rceil$; exact uses zero. $Q$ is the mean primary minimum, or mean lower--upper bounds where unresolved; interval endpoints round outwards. Ratios average splitwise reference queries divided by proved positive matching minima, excluding zero and unresolved minima. Strict gain compares joint evidence with the best union of separately optimal witnesses. Full counts, bounds and per-depth results appear in Appendix~\ref{app:full-mean-grid}.}',r'\label{tab:full-mean-main}',r'\end{table*}',''])
 (T/'full-mean-main.tex').write_text(text)
 a=json.loads((ROOT/'outputs/full-mean-grid-20261005/audit.json').read_text());f=json.loads((ROOT/'outputs/frontier-priority-20261005/audit.json').read_text())
 unions=[r for r in rows if int(r['union_proven'])]
 vals={'fullMeanProven':str(a['joint_proven']),'fullMeanUnclosed':str(1920-a['joint_proven']),'fullMeanUnionProven':str(len(unions)),'fullMeanStrictGain':str(sum(int(r['joint_upper'])<int(r['union_minimum']) for r in unions)),'fullMeanJointSaving':str(sum(int(r['union_minimum'])-int(r['joint_upper']) for r in unions)),'frontierQueries':fmt(f['main_mean_queries']),'frontierRefQueries':fmt(f['main_mean_reference']),'frontierWidthQueries':fmt(f['main_mean_width']),'frontierWins':str(f['main_wins_reference']),'frontierLosses':str(f['main_losses_reference'])}
 sr=list(csv.DictReader((ROOT/'outputs/frontier-priority-20261005/summary.csv').open()))
 for key,method in [('frontierSafetyQueries','safety'),('frontierExclusionQueries','exclusion')]:vals[key]=fmt(statistics.fmean(float(r['queries']) for r in sr if r['stopping']=='primary' and r['method']==method))
 (T/'evidence-main-numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+(format(int(v), ',') if k in {'fullMeanProven','fullMeanUnionProven','fullMeanJointSaving'} else v)+'}' for k,v in vals.items())+'\n')
 print('Rendered main synthesis from 1920 matching targets.')
if __name__=='__main__':main()

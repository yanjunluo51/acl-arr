"""Reproduce complete 48-cell diagnostics at the original main tolerance."""
import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13 streams','WMT23_without_synthetic_ref':'WMT23, 12 streams','WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
def main():
 data=list(csv.DictReader((ROOT/'outputs/acquisition-mechanisms/summary.csv').open()))
 for agg in ['median','mean']:
  rows=[r for r in data if r['aggregator']==agg and r['tau']=='1/50'];assert len(rows)==24
  rows.sort(key=lambda r:(list(NAMES).index(r['dataset']),float(r['q'])))
  lines=[r'\begin{table*}[t]',r'\centering\small',r'\caption{Prediction and discovery diagnostics for '+agg+r' pooling, full-reference right ECDF, $\alpha=.10$ and $\varepsilon=\lceil.02|S_0|\rceil$. Each error statistic is defined on all 40 splits and averages them; query differences also average 40 splits. $\rho(n)$ is mean initial row-total rank correlation over the $n$ defined splits. Remaining error is measured just before reference stopping; $\Delta Q$ is reference minus largest-width queries. Wins count strict query reductions against width. Zero-query stops may contribute to prediction diagnostics when active rows remain.}',r'\label{tab:acquisition-'+agg+r'}',r'\begin{tabular}{lrrrrrr}',r'\toprule',r'Panel & $q$ & Entry error & $\rho(n)$ & Remaining error & $\Delta Q$ & Wins / 40 \\',r'\midrule']
  for i,r in enumerate(rows):
   if i and rows[i-1]['dataset']!=r['dataset']:lines.append(r'\addlinespace')
   def num(k,n=3):return f'{float(r[k]):.{n}f}' if r[k] else '--'
   rr=num('initial_row_rho')+f" ({r['initial_row_rho_defined']})"
   lines.append(f"{NAMES[r['dataset']]} & {float(r['q']):.2f} & {num('flip_mae')} & {rr} & {num('prestop_remaining_mae')} & {num('reference_minus_width',1)} & {r['reference_beats_width']} "+r'\\')
  lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table*}'])
  (ROOT/'manuscript/tables'/('acquisition-'+agg+'.tex')).write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()

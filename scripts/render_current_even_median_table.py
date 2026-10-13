"""Recreate the current even-median table from frozen records, retaining small positive means."""
from pathlib import Path
import argparse,csv,itertools,json,math,statistics,sys
ROOT=Path(__file__).resolve().parents[1]
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh']
NAMES=['RewardBench','WMT23 (13 streams)','WMT23 (12 streams)','WMT24 en--de','WMT24 en--es','WMT24 ja--zh']
CAPTION=r'\caption{Even-median joint evidence on complete test batches, averaging all four depths and 40 splits (160 targets) per row. Closed counts numerically closed minima; Zero counts zero-query certificates. Each target uses $\alpha=.10$ and either $\varepsilon=\lceil .02|S_0|\rceil$ (primary) or zero (exact). Mean lower and upper bounds include every target. The positive mean below 0.1 is shown to three decimals; an unresolved target is not replaced by a claimed minimum. Pools of size six and eight use the first members in the frozen evaluator order. Changing $M$ also changes the candidate family and cutoff, so these are separate certification tasks.}'
def render(root=ROOT):
 records=[json.loads(x) for x in (root/'outputs/even-median-panels-20261007/records.jsonl').open()];assert len(records)==3840
 assert len({tuple(r['key']) for r in records})==3840
 summaries={(r['panel'],int(r['M']),r['stop']):r for r in csv.DictReader((root/'manuscript/supplement/even_median_summary.csv').open())}
 lines=[r'\begin{table*}[t]',r'\centering\small',r'\begin{tabular}{lrrlrrrr}',r'\toprule',r'Panel & $M$ & $T$ & Stop & Closed & Zero & Mean LB & Mean UB \\',r'\midrule']
 for panel,M,stop in itertools.product(PANELS,[6,8],['primary','exact']):
  rows=[r for r in records if (r['key'][0],r['M'],r['key'][-1])==(panel,M,stop)];assert len(rows)==160
  closed=sum(r['result']['joint_optimal'] for r in rows);zero=sum(r['result']['queries']==0 for r in rows);T=rows[0]['T'];assert all(r['T']==T for r in rows)
  lb=statistics.mean(r['result']['joint_lower_bound'] for r in rows);ub=statistics.mean(r['result']['queries'] for r in rows)
  saved=summaries[panel,M,stop];assert int(saved['closed'])==closed and int(saved['zero_query'])==zero
  assert math.isclose(float(saved['mean_query_lower']),lb,rel_tol=0,abs_tol=1e-12) and math.isclose(float(saved['mean_query_upper']),ub,rel_tol=0,abs_tol=1e-12)
  fmt=lambda x:format(x,'.3f' if 0<x<.1 else '.1f')
  lines.append(f'{NAMES[PANELS.index(panel)]} & {M} & {T} & {stop} & {closed} & {zero} & {fmt(lb)} & {fmt(ub)}'+r' \\')
 lines.extend([r'\bottomrule',r'\end{tabular}',CAPTION,r'\label{tab:even-median-panels}',r'\end{table*}'])
 return '\n'.join(lines)+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();text=render()
 if a.output:a.output.write_text(text)
 else:assert text==(ROOT/'manuscript/tables/even-median-panels.tex').read_text(),'Table differs; use --output to inspect a fresh rendering'
 print(json.dumps(dict(status='PASS_FROZEN_RECORD_CSV_TABLE_AGREEMENT',targets=3840,table_rows=24,small_positive_mean=3/160,new_solver_runs=False)))
if __name__=='__main__':main()

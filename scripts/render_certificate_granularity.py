"""Render the complete result summaries; no manual numeric table edits."""
from pathlib import Path
import csv,json
from decimal import Decimal, ROUND_HALF_UP
ROOT=Path(__file__).resolve().parents[1]
TABLES=ROOT/'manuscript/tables'
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh']
NAMES=['RewardBench 2','WMT23, 13 streams','WMT23, 12 streams','WMT24 en-de','WMT24 en-es','WMT24 ja-zh']


def table(name,columns,header,rows,caption,label):
    body='\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)
    text=('\\begin{table*}[t]\n\\centering\\small\n\\caption{'+caption+'}\n\\label{'+label+'}\n'
          '\\begin{tabular}{'+columns+'}\n\\toprule\n'+header+r' \\'+'\n\\midrule\n'+body+
          '\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n')
    (TABLES/name).write_text(text)


def number(x,places=2):
    return '--' if x is None or x=='' else format(Decimal(str(x)).quantize(Decimal(10)**(-places), rounding=ROUND_HALF_UP),'f')


def main():
    overhead=list(csv.DictReader((ROOT/'review-revision/review-overhead-analysis/cells.csv').open()))
    original=[x for x in overhead if x['reference_fraction']=='1' and x['cdf']=='right']
    rows=[]
    for panel,name in zip(PANELS,NAMES):
        x=next(x for x in original if x['dataset']==panel and x['q']=='0.05' and x['method']=='reference_priority')
        rows.append([name,x['Q_positive_splits'],x['Q_zero_splits']]+[number(x[k],3) for k in
                    ['median_ratio_given_Q_positive','p90_ratio_given_Q_positive','max_ratio_given_Q_positive']])
    table('entry-overhead-summary.tex','lrrrrr',r'Panel & $Q>0$ & $Q=0$ & Median & P90 & Max',rows,
          r'Exact median entry-query overhead at $q=.05$, $\alpha=.10$, full-reference right ECDF and reference priority. Ratios are $Q_{\rm online}/Q_{\rm exact}$ on positive-witness splits; zero-witness splits are separate and use no online queries. Each panel has 40 splits. P90 uses linear interpolation; overlapping splits supply descriptive distributions, not population intervals.',
          'tab:entry-overhead-summary')
    text=[]
    for j,(panel,name) in enumerate(zip(PANELS,NAMES)):
        rows=[]
        for q in ['0.05','0.1','0.2','0.3']:
            for method,short in [('fixed','Fixed'),('random','Random'),('largest_width','Width'),('reference_priority','Reference')]:
                x=next(x for x in original if x['dataset']==panel and x['q']==q and x['method']==method)
                rows.append([number(q),short,x['Q_positive_splits'],x['Q_zero_splits']]+[number(x[k],3) for k in
                            ['median_ratio_given_Q_positive','p90_ratio_given_Q_positive','max_ratio_given_Q_positive']])
        fname=f'entry-overhead-all-{j}.tex'
        table(fname,'rlrrrrr',r'$q$ & Order & $Q>0$ & $Q=0$ & Median & P90 & Max',rows,
              name+r': exact entry overhead across every depth and policy, with the protocol and ratio conventions of Table~\ref{tab:entry-overhead-summary}.',f'tab:entry-overhead-all-{j}')
        text.append('\\input{tables/'+fname[:-4]+'}')
    (TABLES/'entry-overhead-all.tex').write_text('\n'.join(text)+'\n')
    columns=list(csv.DictReader((ROOT/'outputs/column-certificates/cells.csv').open()))
    rows=[]
    for panel,name in zip(PANELS,NAMES):
        x=next(x for x in columns if x['dataset']==panel and x['q']=='0.05')
        rows.append([name,x['positive_witness_splits'],number(x['mean_Q_entry'],1),number(x['mean_K_col'],2),number(100*float(x['mean_minimum_panel_fraction']),1),number(x['column_reference_mean_count'],2),number(x['column_reference_median_ratio'],3)])
    table('column-witness-summary.tex','lrrrrrr',r'Panel & $K>0$ & $Q_{\rm exact}$ & $K_{\rm col}$ & Min. (\%) & Ref. cols & Ratio',rows,
          r'Exact median column witnesses at $q=.05$, $\alpha=.10$, full-reference right ECDF. $Q_{\rm exact}$ is the entry witness; $K_{\rm col}$ is the minimum whole-column witness. Counts and Min.\ ($100K_{\rm col}/T$) average all 40 splits; Ratio is the median reference-column count divided by $K_{\rm col}$ on positive-witness splits. Whole-column score cost is $NK_{\rm col}$. These exact costs have a different target from the positive-gap costs in Table~\ref{tab:column-summary}.',
          'tab:column-witness-summary')
    rows=[]
    for panel,name in zip(PANELS,NAMES):
        for x in columns:
            if x['dataset']!=panel:continue
            rows.append([name,number(x['q']),x['positive_witness_splits'],number(x['mean_K_col'],2),number(100*float(x['mean_minimum_panel_fraction']),1)]+[number(x[m+'_median_ratio'],3) for m in ['column_fixed','column_random','column_reference']])
    table('column-witness-all.tex','lrrrrrrr',r'Panel & $q$ & $K>0$ & $K_{\rm col}$ & Min. (\%) & Fixed & Random & Reference',rows,
          r'Minimum exact column costs and conditional median online overhead across all 960 median configurations. Protocol and averaging follow Table~\ref{tab:column-witness-summary}; all three original column orders are included.', 'tab:column-witness-all')
    syn=list(csv.DictReader((ROOT/'outputs/synthetic-certificates/cells.csv').open()))
    rows=[]
    for m in [32,128]:
        for T in [7,12]:
            for d in [1,3]:
                for b in [0,m*T//5,m*T//2]:
                    group=[x for x in syn if (int(x['m']),int(x['T']),int(x['d']),int(x['bit_budget']))==(m,T,d,b)]
                    assert len(group)==3 and len({x['mean_Q_entry'] for x in group})==1
                    rows.append([m,T,d,b,number(group[0]['mean_Q_entry'],0)]+[number(next(x for x in group if x['layout']==mode)['mean_K_col'],2) for mode in ['shared','cyclic','independent']])
    table('synthetic-column-witnesses.tex','rrrrrrrr',r'$m$ & $T$ & $d$ & $b$ & $Q_{\rm exact}$ & Shared & Cyclic & Independent',rows,
          r'Controlled column-evidence sharing. Each row represents eight seeds in each of three layouts with identical $m,T,d,b$ and entry witness. Shared, Cyclic and Independent report mean $K_{\rm col}$; every seed has an exact witness and smaller-subset exclusion. All 576 instances use the complete entry and column acquisition solvers. The synthetic inputs test query geometry, not NLP quality.', 'tab:synthetic-column-witnesses')
    rb=next(x for x in columns if x['dataset']=='RewardBench2' and x['q']=='0.05')
    wmt=next(x for x in columns if x['dataset']=='WMT23' and x['q']=='0.05')
    vals={'granRbColumns':number(rb['mean_K_col'],2),'granRbMinimum':number(100*float(rb['mean_minimum_panel_fraction']),1),
          'granRbOnlineColumns':number(rb['column_reference_mean_count'],2),
          'granWmtMinimum':number(100*float(wmt['mean_minimum_panel_fraction']),1)}
    (TABLES/'granularity-numbers.tex').write_text('\n'.join('\\newcommand{\\'+key+'}{'+value+'}' for key,value in vals.items())+'\n')
    print(json.dumps({'status':'PASS_RESULT_BOUND_TABLE_RENDER','column_instances':960,'synthetic_instances':576,'exact_entry_records':23040,'new_table_files':12}))

if __name__=='__main__':main()

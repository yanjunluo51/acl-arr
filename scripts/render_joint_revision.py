"""Deterministic evidence tables for joint certificates and interventions."""
import csv,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TAB=ROOT/'manuscript/tables'
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh']
NAMES=['RewardBench 2','WMT23, 13 streams','WMT23, 12 streams','WMT24 en-de','WMT24 en-es','WMT24 ja-zh']

def table(name,head,rows,caption,label):
    cols='l'+'r'*(len(head)-1)
    body=['\\begin{table*}[t]','\\centering\\small',r'\begin{tabular}{'+cols+'}',r'\toprule',' & '.join(head)+r' \\',r'\midrule']
    body+=[' & '.join(row)+r' \\' for row in rows]
    body+=[r'\bottomrule',r'\end{tabular}',r'\caption{'+caption+'}',r'\label{'+label+'}',r'\end{table*}','']
    (TAB/name).write_text('\n'.join(body))

def main():
    r=list(csv.DictReader((ROOT/'outputs/joint-certificates/panel_summary.csv').open()))
    d={(x['dataset'],x['aggregator'],float(x['q']),x['history'],int(x['epsilon'])):x for x in r}
    rows=[]
    for panel,n in zip(PANELS,NAMES):
        for q in [.05,.1,.2,.3]:
            a=d[panel,'mean',q,'empty',0];b=d[panel,'mean',q,'quarter',0]
            rows.append([n,f'{q:.2f}',f"{float(a['queries']):.2f}",f"{float(a['split_queries']):.2f}",a['strict_sharing_benefit'],f"{float(b['queries']):.2f}",f"{float(b['split_queries']):.2f}",b['strict_sharing_benefit']])
    table('joint-small-batches.tex',['Panel',r'$q$',r'$Q_{\rm joint}$',r'$Q_{\rm split}$','Shared / 40',r'$Q_{\rm joint}(\mathcal O)$',r'$Q_{\rm split}(\mathcal O)$','Shared / 40'],rows,'Exact mean entry certificates on the predefined subbatches of at most four baseline-selected outputs. Each row averages 40 splits, retaining original maps, cutoff and all candidates while resetting $N$, $k$ and $b_H$ for this subbatch. The first group starts empty; the second starts with the first quarter of eligible cells in seeded row and candidate-index order. $Q_{\\rm split}$ adds independently minimized safety and exclusion sizes over the same safe-target range; Shared counts strict joint savings. All minima are independently checked. These are not minima for the original full test batches.','tab:joint-small')
    ds=list(csv.DictReader((ROOT/'outputs/joint-certificates/discovery_summary.csv').open()));d={(x['dataset'],x['aggregator'],float(x['q']),int(x['epsilon']),x['method']):x for x in ds};rows=[]
    for panel,n in zip(PANELS,NAMES):
        for e in [0,1]:
            a=d[panel,'mean',.05,e,'reference_priority'];rat=[]
            for method in ['fixed','random','largest_width','reference_priority']:
                x=d[panel,'mean',.05,e,method];assert x['positive_minima']==a['positive_minima'];rat.append(f"{float(x['mean_ratio']):.3f}" if x['mean_ratio'] else '--')
            rows.append([n,str(e),f"{float(a['minimum']):.2f}",a['positive_minima']]+rat)
    table('joint-discovery.tex',['Panel',r'$\varepsilon$',r'Mean $Q_{\rm joint}$',r'$n_+$','Fixed','Random','Width','Reference'],rows,r'Mean-pooling discovery ratios on the same predefined subbatches at $q=.05$, $\alpha=.10$. The four policies use their original full definitions, including WMT24 priority ties. Ratio columns average $Q_{\rm online}/Q_{\rm joint}$ over the $n_+$ splits with positive matching minima; zero minima have undefined ratios. Counts and certificate gaps concern this separate small-batch task, not the full-panel acquisition records.','tab:joint-discovery')
    src=list(csv.DictReader((ROOT/'outputs/query-mechanism-interventions/summary.csv').open()));d={(x['dataset'],x['aggregator'],float(x['q']),x['method'],x['stopping']):x for x in src};rows=[]
    for panel,n in zip(PANELS,NAMES):
        for q in [.05,.1,.2,.3]:
            a=d[panel,'mean',q,'reference_priority','primary'];rows.append([n,f'{q:.2f}',f"{float(a['queries']):.1f}",f"{float(a['queries'])-float(a['delta_width']):.1f}"]+[f"{float(d[panel,'mean',q,m,'primary']['queries']):.1f}" for m in ['oracle_row','oracle_candidate','oracle_both']])
    table('query-interventions.tex',['Panel',r'$q$','Reference','Width','True row','True candidate','Both'],rows,r'Same-instance mean-pooling interventions on the complete original batches, averaging 40 splits. All use $\alpha=.10$ and first stop at $V^+-V^-\le\lceil .02|S_0|\rceil$. True row uses the true row total in the reference row-priority formula; True candidate orders a chosen row by true flip contribution; Both combines them. These full-information interventions diagnose query order and are not deployable policies. They leave the maps, cutoff, endpoint bounds, budget and stopping target fixed. Complete median and exact-stop summaries accompany the code.','tab:query-interventions')
if __name__=='__main__':main()

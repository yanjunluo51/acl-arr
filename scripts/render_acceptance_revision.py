"""Deterministic tables for all predeclared depths and both stopping targets."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/acceptance-review-implementation';TABLES=ROOT/'manuscript/tables'
PANELS={'RewardBench2':'RewardBench','WMT23':'WMT23 (13)','WMT23_without_synthetic_ref':'WMT23 (12)',
        'WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}

def decimal(value, places):
    displayed = f'{value:.{places}f}'
    return f'{0:.{places}f}' if float(displayed) == 0 else displayed


def table(filename,columns,header,rows,caption,label):
    text='\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{'+columns+'}\n\\toprule\n'+header+' \\\\\n\\midrule\n'
    text+=''.join(' & '.join(row)+' \\\\\n' for row in rows)
    text+='\\bottomrule\n\\end{tabular}\n\\caption{'+caption+'}\n\\label{'+label+'}\n\\end{table*}\n'
    (TABLES/filename).write_text(text)


def main():
    quality=json.loads((OUT/'wmt23-quality-results.json').read_text())['cells']
    rows=[]
    for panel in ['WMT23','WMT23_without_synthetic_ref']:
        for pooling in ['median','mean']:
            for q in [.05,.1,.2,.3]:
                c=next(v for v in quality if v['dataset']==panel and v['aggregator']==pooling and v['q']==q and v['method']=='reference_priority' and v['stopping']=='two_percent_gap')
                rows.append([PANELS[panel],pooling,f'{q:.2f}',f"{c['K']:.1f}",f"{c['K_annotated']:.1f}",f"{100*c['label_coverage']:.1f}",decimal(c['MQM'],4),decimal(c['label_matched_delta'],4)])
    table('wmt23-native-quality.tex','llrrrrrr',r'Panel & Pooling & $q$ & $K$ & $K_{\rm lab}$ & Obs. (\%) & MQM & $\Delta$',rows,
          r'Post hoc WMT23 MQM diagnostic for the original reference-priority positive-gap stop, $\alpha=.10$, full-reference right ECDF. $K$ counts all returned outputs and $K_{\rm lab}$ the labeled ones. Obs. averages splitwise labeled fractions. MQM is higher-is-better on labeled outputs; $\Delta$ subtracts the consensus-ranked comparator with the same labeled count. Each row averages 40 overlapping splits; no population inference or missing-label imputation is made. All four acquisition methods, both stops and the two controls are included in the reproducibility results.',
          'tab:wmt23-native-quality')
    cost=json.loads((OUT/'cost-results.json').read_text())['cells']
    for stop,filename,label in [('exact_gap','column-cost-exact.tex','tab:column-cost-exact'),('two_percent_gap','column-cost-tolerant.tex','tab:column-cost-tolerant')]:
        rows=[]
        for panel in PANELS:
            for q in [.05,.1,.2,.3]:
                cs=[next(v for v in cost if v['dataset']==panel and v['q']==q and v['stopping']==stop and v['profile']==profile) for profile in ['uniform','ascending','descending']]
                rows.append([PANELS[panel],f'{q:.2f}']+[f"{v['mean_minimum_normalized_cost']:.3f}" for v in cs]+[f"{v['column_reference_mean_cost_ratio']:.3f}" if v['column_reference_mean_cost_ratio'] is not None else '--' for v in cs]+[str(cs[1]['cost_optimum_uses_more_columns'])+'/'+str(cs[2]['cost_optimum_uses_more_columns'])])
        caption=(r'Exact-stop' if stop=='exact_gap' else r'Positive-gap-stop')+r' column-cost sensitivity under the original median protocol and $\alpha=.10$. Uniform, ascending and descending prices have the same mean, normalized to one. The three $C$ columns average minimum costs over all 40 splits. The $R$ columns average reference-order cost divided by the matching optimum over positive-cost splits. More reports ascending/descending split counts where a minimum-cost witness uses more columns than the minimum-count witness. Undefined ratios remain missing. Prices are declared action-cost models, not measured scoring times or fees.'
        table(filename,'lrrrrrrrr',r'Panel & $q$ & $C_0$ & $C_\uparrow$ & $C_\downarrow$ & $R_0$ & $R_\uparrow$ & $R_\downarrow$ & More',rows,caption,label)
    print('rendered 3 new tables; original 60 tables unchanged')


if __name__=='__main__':main()

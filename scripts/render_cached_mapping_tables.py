"""Regenerate mapping/column tables from frozen, saved summaries only.
No NLP score input is loaded; original full renderer remains unchanged.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import csv, hashlib, json, statistics, sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/mapping-column'
TABLES=ROOT/'manuscript/tables'
NAMES={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13 streams',
       'WMT23_without_synthetic_ref':'WMT23, 12 streams',
       'WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}


def span(values,scale=1,digits=1):
    a,b=min(values)*scale,max(values)*scale
    if isinstance(a,Decimal):
        unit=Decimal(1).scaleb(-digits)
        lo,hi=[format(x.quantize(unit,rounding=ROUND_HALF_UP),f'.{digits}f') for x in [a,b]]
        return lo if lo==hi else lo+'--'+hi
    if round(a,digits)==round(b,digits):return f'{a:.{digits}f}'
    return f'{a:.{digits}f}--{b:.{digits}f}'


def table(columns,rows,caption,label):
    return '\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{'+columns+'}\n\\toprule\n'+rows+'\\bottomrule\n\\end{tabular}\n\\caption{'+caption+'}\n\\label{'+label+'}\n\\end{table*}\n'


def save_csv(file,rows):
    with file.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=sorted(set().union(*(r.keys() for r in rows))))
        w.writeheader();w.writerows(rows)


def main():
    audit=json.loads((ROOT/'review-revision/mapping-column/arithmetic-audit.json').read_text())
    assert audit['status']=='PASS_SEPARATE_ARITHMETIC_REPLAY_AND_BASELINE_FIDELITY'
    assert hashlib.sha256((OUT/'results.json').read_bytes()).hexdigest()==audit['bindings']['outputs/mapping-column/results.json']
    z=json.loads((OUT/'results.json').read_text());cells=z['cells'];records=z['records']
    exact_groups={}
    for row in z['geometry']:
        if row['aggregator']=='median':
            key=(row['dataset'],row['q'],row['reference_fraction'],row['cdf'])
            exact_groups.setdefault(key,[]).append(row['offline_exact_certificate'])
    assert len(exact_groups)==144 and all(len(v)==40 for v in exact_groups.values())
    exact_means={k:Decimal(sum(v))/Decimal(len(v)) for k,v in exact_groups.items()}

    groups={}
    keys=['dataset','reference_fraction','cdf','aggregator','q','method','stopping']
    for r in records:groups.setdefault(tuple(r[k] for k in keys),[]).append(r)
    comparisons=0
    for cell in cells:
        rs=groups[tuple(cell[k] for k in keys)];assert len(rs)==40
        for field,value in cell.items():
            if field in keys or field=='splits':continue
            vals=[r[field] for r in rs if r.get(field) is not None]
            expected=statistics.fmean(vals) if vals else None
            assert expected==value,(field,expected,value)
            comparisons+=1
    saved=json.loads((OUT/'base_list_diagnostics.json').read_text())
    diagnostics=saved['records'];dc=saved['cells']
    assert len(diagnostics)==11520 and len(dc)==288
    dkeys=['dataset','reference_fraction','cdf','aggregator','q']
    dg={}
    for row in diagnostics:dg.setdefault(tuple(row[k] for k in dkeys),[]).append(row)
    for row in dc:
        group=dg[tuple(row[k] for k in dkeys)];assert len(group)==row['splits']==40
        for field in ['base_list_jaccard','membership_difference_fraction','cutoff_tie_selected_fraction']:
            values=[r[field] for r in group if r[field] is not None]
            assert (statistics.fmean(values) if values else None)==row[field]
    dlookup={tuple(row[k] for k in dkeys):row for row in dc}
    def entry(panel,agg,q):
        return [r for r in cells if r['dataset']==panel and r['aggregator']==agg and r['q']==q
                and r['method']=='reference_priority' and r['stopping']=='two_percent_gap']
    def mapping_row(panel,agg,q,with_panel):
        rs=entry(panel,agg,q)
        jac=[dlookup[(panel,r['reference_fraction'],r['cdf'],agg,q)]['base_list_jaccard'] for r in rs]
        values=[NAMES[panel],agg] if with_panel else [agg,f'{q:.2f}']
        values += [span([r['selected_over_k'] for r in rs],digits=2),
                   span([r['zero_selected_coverage'] for r in rs],100),
                   span([r['active_fraction'] for r in rs],100),
                   span([exact_means[(panel, q, r['reference_fraction'], r['cdf'])] for r in rs]) if agg=='median' else '--',
                   span(jac,digits=2)]
        return ' & '.join(values)+' \\\\\n'
    mapping_header='Panel & Pooling & $|S_0|/k$ & Zero (\\%) & Active (\\%) & $Q_{\\rm exact}$ & Jaccard \\\\\n\\midrule\n'
    rows=mapping_header+''.join(mapping_row(panel,agg,.05,True) for panel in z['protocol']['panels'] for agg in ['median','mean'])
    caption=('Mapping sensitivity at nominal 5\\% selection, $\\alpha=.10$. Each range is the minimum and maximum of 40-split means across six reference protocols: full, half or quarter reference groups, each with right or midrank ECDF ties. Test groups and methods are unchanged. Zero is structural selected coverage; Active is reference-priority inspection divided by $mT$ at the two-percent retention gap. $Q_{\\rm exact}$ is the median entry-oracle offline witness, with a different exact stopping target. Jaccard compares base lists with the full-reference right-ECDF protocol. Ranges describe configurations, not confidence intervals.')
    (TABLES/'mapping-summary.tex').write_text(table('llrrrrr',rows,caption,'tab:mapping-summary'))
    all_mapping=[]
    for number,panel in enumerate(z['protocol']['panels']):
        rows='Pooling & $q$ & $|S_0|/k$ & Zero (\\%) & Active (\\%) & $Q_{\\rm exact}$ & Jaccard \\\\\n\\midrule\n'
        rows+=''.join(mapping_row(panel,agg,q,False) for agg in ['median','mean'] for q in [.05,.1,.2,.3])
        all_mapping.append(table('lrrrrrr',rows,NAMES[panel]+': all four mapping-sensitivity depths. Ranges use the six reference protocols and 40-split means defined in Table~\\ref{tab:mapping-summary}. Active inspections use the positive-gap stop; the entry-oracle witness uses exact optimality.','tab:mapping-all-'+str(number)))
    (TABLES/'mapping-all-depths.tex').write_text('\n'.join(all_mapping))
    def col_row(panel,agg,q,with_panel):
        base=next(r for r in entry(panel,agg,q) if r['reference_fraction']=='1' and r['cdf']=='right')
        columns={r['method']:r for r in cells if r['dataset']==panel and r['aggregator']==agg and r['q']==q
                 and r['method'].startswith('column_') and r['stopping']=='two_percent_gap'}
        values=[NAMES[panel],agg] if with_panel else [agg,f'{q:.2f}']
        values += [f'{100*base["panel_fraction"]:.2f}',f'{base["candidate_columns_touched"]:.1f}']
        values += [f'{100*columns[m]["panel_fraction"]:.1f}' for m in ['column_fixed','column_random','column_reference']]
        values += [f'{columns["column_reference"]["candidate_columns_touched"]:.1f}',str(base['T']) if 'T' in base else str(next(r['T'] for r in records if r['dataset']==panel))]
        return ' & '.join(values)+' \\\\\n'
    rows='Panel & Pooling & Entry (\\%) & Touched & Fixed (\\%) & Random (\\%) & Ref. (\\%) & Cols. & $T$ \\\\\n\\midrule\n'
    rows+=''.join(col_row(panel,agg,.05,True) for panel in z['protocol']['panels'] for agg in ['median','mean'])
    caption=('Whole-evaluator queries at nominal 5\\%, $\\alpha=.10$, full-reference right-ECDF mapping and the two-percent gap. Entry is reference-priority entry inspection; Touched counts its distinct candidate test columns. Fixed, Random and Ref. are whole-column orders, each charging $N$ test scores per queried evaluator. All percentages divide by $NT$; Cols. is the reference column count and $T$ the candidate-family size. Counts and ratios are separately averaged over 40 splits. Equal certificate criteria permit different masks within the retention tolerance. No inference time is measured.')
    (TABLES/'column-summary.tex').write_text(table('llrrrrrrr',rows,caption,'tab:column-summary'))
    all_columns=[]
    for number,panel in enumerate(z['protocol']['panels']):
        rows='Pooling & $q$ & Entry (\\%) & Touched & Fixed (\\%) & Random (\\%) & Ref. (\\%) & Cols. & $T$ \\\\\n\\midrule\n'
        rows+=''.join(col_row(panel,agg,q,False) for agg in ['median','mean'] for q in [.05,.1,.2,.3])
        all_columns.append(table('lrrrrrrrr',rows,NAMES[panel]+': whole-column controls at every depth, using the 40-split, $\\alpha=.10$, positive-gap protocol of Table~\\ref{tab:column-summary}. Percentages use all candidate-test entries, including nonactive scores acquired by a column.','tab:column-all-'+str(number)))
    (TABLES/'column-all-depths.tex').write_text('\n'.join(all_columns))
    receipt={'status':'PASS_EVIDENCE_BOUND_RENDER','cell_scalar_comparisons':comparisons,
             'post_execution_base_list_diagnostic_cases':len(diagnostics),
             'tables':['mapping-summary.tex','mapping-all-depths.tex','column-summary.tex','column-all-depths.tex']}
    (ROOT/'review-revision/mapping-column/table-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    print('Full WMT23 median, q=.05:')
    for r in dc:
        if r['dataset']=='WMT23' and r['aggregator']=='median' and r['q']==.05:print(r)


if __name__=='__main__':main()

"""Successor captions and descriptive mechanism table; frozen renderers stay intact.

Run original renderers only in an isolated legacy tree; these distributed base
TeX files preserve their complete numeric output plus subsequent verified tables.
This renderer changes explanatory captions and two nonnumeric column headers.
It independently checks that every old numeric table body is preserved.
"""
from pathlib import Path
import csv,json,re
from decimal import Decimal,ROUND_HALF_UP
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'review-revision/editorial-implementation'

def main():
    caps=json.loads((D/'caption-overrides.json').read_text());seen=set();bodies=0
    for p in (D/'table-bases').glob('*.tex'):
        source=p.read_text()
        def change(m):
            key=m.group(2)
            if key in caps:
                seen.add(key);return '\\caption{'+caps[key]+'}\n\\label{'+key+'}'
            return m.group(0)
        text=re.sub(r'\\caption\{(.*?)\}\s*\\label\{([^}]+)\}',change,source,flags=re.S)
        # Header wording changes: values and all remaining tabular bytes unchanged.
        if p.name.startswith('query-all-'):text=text.replace(' & Gap',r' & Gap (outputs)')
        if p.name.startswith('review-replacement-'):text=text.replace(' & Max &',r' & Mean max &')
        old=re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',source,re.S)
        new=re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',text,re.S)
        assert old==[v.replace(' & Gap (outputs)',' & Gap').replace(' & Mean max &',' & Max &') for v in new],p
        bodies+=len(old)
        (ROOT/'manuscript/tables'/p.name).write_text(text)
    assert seen==set(caps),set(caps)-seen
    names={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13 streams','WMT23_without_synthetic_ref':'WMT23, 12 streams','WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
    rows=list(csv.DictReader((ROOT/'review-revision/editorial-audit/zero-query-decomposition.csv').open()));assert len(rows)==48
    def pct(x):return str((Decimal(x)*100).quantize(Decimal('.1'),rounding=ROUND_HALF_UP))
    tables=[]
    for agg in ['median','mean']:
        body=[]
        for panel in names:
            for row in sorted((x for x in rows if x['dataset']==panel and x['aggregator']==agg),key=lambda x:float(x['q'])):
                inv=float(row['invariant_selected_fraction']);bud=float(row['budget_retained_noninvariant_fraction']);zero=float(row['zero_query_selected_coverage'])
                assert abs(inv+bud-zero)<1e-12
                assert int(row['splits'])==40
                vals=[names[panel],row['q']]+[pct(row[k]) for k in ['invariant_selected_fraction','budget_retained_noninvariant_fraction','zero_query_selected_coverage','zero_query_stopping_fraction']]
                body.append(' & '.join(vals)+r' \\')
        tables.append('\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{lrrrrr}\n\\toprule\nPanel & $q$ & Invariant & Budget & Zero & Z \\\\\n\\midrule\n'+'\n'.join(body)+'\n\\bottomrule\n\\end{tabular}\n\\caption{'+agg.capitalize()+r' pooling, $\alpha=.10$, full-reference right ECDF, original evaluator pools. Invariant and Budget are selected-output shares retained through $p_i=0$ and budget-admissible $p_i>0$, respectively. Their sum is zero-query selected coverage (Zero); each fraction divides by $|S_0|$ before averaging 40 splits. Z is the percentage of splits stopping at zero queries under $\lceil.02|S_0|\rceil$ outputs. All columns are percentages, rounded separately.}'+ '\n\\label{tab:zero-decomposition'+('' if agg=='median' else '-mean')+'}\n\\end{table*}\n')
    (ROOT/'manuscript/tables/zero-query-decomposition.tex').write_text('\n'.join(tables))
    receipt={'status':'PASS_EDITORIAL_TABLE_RENDER','overridden_captions':len(seen),'preserved_tabular_bodies':bodies,'decomposition_cells':len(rows),'no_new_model_inference':True}
    (D/'table-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()

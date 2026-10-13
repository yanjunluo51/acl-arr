"""Render complete audited review evidence; never invent or transcribe values."""
from pathlib import Path
import hashlib,json,statistics
import numpy as np
import matplotlib
matplotlib.use('Agg');matplotlib.rcParams['pdf.fonttype']=42;matplotlib.rcParams['svg.fonttype']='none';matplotlib.rcParams['svg.hashsalt']='arr-review-evidence-1'
matplotlib.rcParams['font.family']='serif'
matplotlib.rcParams['font.serif']=['Times New Roman','Times','cmr10']
matplotlib.rcParams['mathtext.fontset']='stix'
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];TABLES=ROOT/'paper/tables';TABLES.mkdir(exist_ok=True)
PANELS=['RewardBench2','WMT23','WMT23_without_synthetic_ref'];LABELS=dict(zip(PANELS,['RewardBench 2','WMT23, 13 streams','WMT23, 12 streams']))
METHODS=['fixed','random','largest_width','reference_priority'];SHORT=dict(zip(METHODS,['Fixed','Random','Width','Reference']))

def mean(rows,field):
    v=[r[field] for r in rows if r.get(field) is not None];return statistics.fmean(v) if v else None

def fmt(v,d=1):
    # Decimal half-up after snapping float noise (Appendix B); binary f-strings send exact ties down.
    if v is None:return '--'
    from decimal import Decimal,ROUND_HALF_UP
    x=Decimal(repr(float(v))).quantize(Decimal('1e-9'),rounding=ROUND_HALF_UP).quantize(Decimal(1).scaleb(-d),rounding=ROUND_HALF_UP)
    return f'{(Decimal(0) if x==0 else x):.{d}f}'

def choose(rows,**keys):return [r for r in rows if all(r[k]==v for k,v in keys.items())]

def table(name,caption,label,cols,head,rows):
    s='\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{'+cols+'}\n\\toprule\n'+head+r' \\'+'\n\\midrule\n'
    s+='\n'.join(' & '.join(row)+r' \\' for row in rows)+'\n\\bottomrule\n\\end{tabular}\n\\caption{'+caption+'}\n\\label{'+label+'}\n\\end{table*}\n';(TABLES/name).write_text(s)


def budget_figure(b):
    # All budget settings, no selected best-alpha view.
    fig,axes=plt.subplots(1,3,figsize=(6.3,2.35),layout='constrained',sharex=True,sharey=True)
    colors=['#666666','#D55E00','#0072B2','#CC79A7'];markers=['o','s','^','D'];styles=['--',':','-.','-']
    for ax,panel in zip(axes,PANELS):
        for method,color,marker,style in zip(METHODS,colors,markers,styles):
            ys=[100*mean(choose(b['query_records'],dataset=panel,aggregator='median',q=.05,alpha=alpha,method=method,stopping='two_percent_gap'),'active_fraction') for alpha in [.02,.05,.1,.15,.2]]
            ax.plot([.02,.05,.1,.15,.2],ys,label=SHORT[method],color=color,marker=marker,linestyle=style,linewidth=1.1,markersize=3)
        ax.set_xticks([.02,.05,.1,.15,.2],['.02','.05','.10','.15','.20']);ax.set_title(LABELS[panel],fontsize=9);ax.set_xlabel(r'Risk budget $\alpha$',fontsize=9);ax.tick_params(labelsize=8);ax.set_ylim(-2,102);ax.grid(alpha=.16);ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Active entries inspected (%)',fontsize=9);handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside upper center',ncol=4,fontsize=9,frameon=False)
    for ext in ['pdf','png','svg']:fig.savefig(ROOT/'paper'/('review-budgets.'+ext),dpi=200)
    plt.close(fig)


def main():
    data={};bindings={}
    for e in ['budget','composition','external','score','sentinel']:
        path=ROOT/'outputs'/('review-'+e)/'results.json';data[e]=json.loads(path.read_text());bindings[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        if e!='sentinel':
            a=json.loads((ROOT/'review-revision'/(e+'-independent-audit.json')).read_text());assert a['status'].startswith('PASS_')
            if 'source_results_sha256' in a:assert a['source_results_sha256']==bindings[str(path.relative_to(ROOT))]
    b=data['budget'];c=data['composition'];e=data['external'];s=data['score'];macros=[];analysis={'sources':bindings,'composition':[]}
    budget_figure(b)
    for index,panel in enumerate(PANELS):
        for agg in ['median','mean']:
            rows=[]
            for q in [.05,.1,.2,.3]:
                for alpha in [.02,.05,.1,.15,.2]:
                    sel={'dataset':panel,'aggregator':agg,'q':q,'alpha':alpha};z=choose(b['baseline_records'],**sel,method='zero_query_structural');op=choose(b['baseline_records'],**sel,method='batch_selected_optimum');r=choose(b['query_records'],**sel,method='reference_priority',stopping='two_percent_gap')
                    rows.append([fmt(q,2),fmt(alpha,2),fmt(100*mean(z,'selected_coverage')),fmt(100*mean(op,'selected_coverage')),fmt(100*mean(r,'selected_coverage')),fmt(100*mean(r,'active_fraction')),fmt(mean(r,'queries'))])
            table(f'review-budget-{index}-{agg}.tex',LABELS[panel]+', '+agg+r': all risk budgets and depths, 40 split means. Zero and optimum are structural and full-information selected coverage. Ref.\ uses the integer two-percent gap. Inspection percentages use active entries; all methods and exact stops are in the complete result files.','tab:review-budget-'+str(index)+'-'+agg,'rrrrrrr',r'$q$ & $\alpha$ & Zero (\%) & Opt. (\%) & Ref. (\%) & Active (\%) & Queries',rows)
    # Composition is summarized at the pool level, then across all 20 random pools.
    comp_rows=[];comp_main=[]
    for panel in PANELS:
        definitions=c['protocol']['pool_definitions'][panel];random_pools=[p for p in definitions if p['id'].startswith('random')];assert len(random_pools)==20
        for agg in ['median','mean']:
            for q in [.05,.1,.2,.3]:
                entries=[]
                for pool in random_pools:
                    sel={'dataset':panel,'pool_id':pool['id'],'aggregator':agg,'q':q};z=choose(c['baseline_records'],**sel,method='zero_query_structural');r=choose(c['query_records'],**sel,method='reference_priority',stopping='two_percent_gap');w=choose(c['query_records'],**sel,method='largest_width',stopping='two_percent_gap')
                    assert len(z)==len(r)==len(w)==40
                    rr={a['split']:a for a in r};ww={a['split']:a for a in w}
                    entries.append({'pool':pool['id'],'zero_coverage':mean(z,'selected_coverage'),'reference_active':mean(r,'active_fraction'),'reference_coverage':mean(r,'selected_coverage'),'reference_minus_width_active':mean(r,'active_fraction')-mean(w,'active_fraction'),'paired_reference_width_wins':sum(rr[i]['queries']<ww[i]['queries'] for i in rr)/40})
                v=np.array([z['reference_active'] for z in entries]);zz=np.array([z['zero_coverage'] for z in entries]);d=np.array([z['reference_minus_width_active'] for z in entries]);quant=np.quantile(v,[.1,.5,.9])*100
                row=[LABELS[panel],agg,fmt(q,2),fmt(100*float(np.median(zz))),fmt(float(quant[1])),f'{quant[0]:.1f}--{quant[2]:.1f}',fmt(100*float(np.median(d)))]
                comp_rows.append(row)
                if q==.05:comp_main.append(row[:2]+row[3:])
                analysis['composition'].append({'dataset':panel,'aggregator':agg,'q':q,'pool_summaries':entries,'median_reference_active_percent':float(quant[1]),'reference_active_10_90_percent':[float(quant[0]),float(quant[2])],'median_reference_minus_width_percentage_points':100*float(np.median(d))})
    cap=r'Random evaluator composition at $\alpha=.10$. Each of 20 pools has 40 splits. Zero is median pool-wise structural selected coverage. Ref.\ is median pool-wise mean active inspection percentage, with descriptive 10th--90th percentiles. $\Delta$ is reference minus width in percentage points; positive means more inspections. These quantiles are not confidence intervals.'
    table('review-composition.tex',r'Top-5\% '+cap,'tab:review-composition','llrrrr',r'Panel & Pooling & Zero (\%) & Ref. (\%) & 10--90\% & $\Delta$ Width',comp_main)
    # Split full composition table by aggregator to avoid one oversized float.
    for agg in ['median','mean']:
        table('review-composition-'+agg+'.tex',agg+': '+cap,'tab:review-composition-'+agg,'llrrrrr',r'Panel & Pooling & $q$ & Zero (\%) & Ref. (\%) & 10--90\% & $\Delta$ Width',[r for r in comp_rows if r[1]==agg])
    balanced=[]
    for panel in PANELS[1:]:
        pools=[p for p in c['protocol']['pool_definitions'][panel] if not p['id'].startswith('random')];assert len(pools)==1
        for agg in ['median','mean']:
            for q in [.05,.1,.2,.3]:
                sel={'dataset':panel,'pool_id':pools[0]['id'],'aggregator':agg,'q':q};z=choose(c['baseline_records'],**sel,method='zero_query_structural');rs=[choose(c['query_records'],**sel,method=m,stopping='two_percent_gap') for m in METHODS]
                balanced.append([LABELS[panel],agg,fmt(q,2),fmt(100*mean(z,'selected_coverage'))]+[fmt(100*mean(r,'active_fraction')) for r in rs])
    table('review-balanced.tex',r'WMT metadata-defined pool with three surface-overlap metrics and four remaining metrics. All depths, $\alpha=.10$, 40 split means. Zero is structural selected coverage; the strategy columns are active inspection percentages. No claim is made that the remaining category is exclusively learned.','tab:review-balanced','llrrrrrr',r'Panel & Pooling & $q$ & Zero & Fixed & Random & Width & Ref.',balanced)
    ext_main=[];quality_rows=[];ext_all=[]
    for lp in ['en-de','en-es','ja-zh']:
        panel='WMT24-'+lp
        for agg in ['median','mean']:
            for q in [.05,.1,.2,.3]:
                sel={'dataset':panel,'aggregator':agg,'q':q};z=choose(e['baseline_records'],**sel,method='zero_query_structural');op=choose(e['baseline_records'],**sel,method='batch_selected_optimum');r=choose(e['query_records'],**sel,method='reference_priority',stopping='two_percent_gap');assert len(r)==40
                row=[lp,agg,fmt(q,2),fmt(100*mean(z,'selected_coverage')),fmt(100*mean(op,'selected_coverage')),fmt(100*mean(r,'selected_coverage')),fmt(100*mean(r,'active_fraction'))]
                ext_all.append(row)
                if q==.05:ext_main.append(row[:2]+row[3:])
                quality_rows.append([lp,agg,fmt(q,2),fmt(100*mean(r,'mqm_return_observed_fraction')),fmt(mean(r,'mqm_return_mean'),4),fmt(mean(r,'mqm_matched_k_mean_delta'),4),fmt(mean(r,'mqm_annotated_count_delta'),4)])
    table('review-external.tex',r'WMT24, top-5\%, $\alpha=.10$, 40 document-grouped splits. Percentages compare structural zero-query, full-information optimum and reference-priority selected coverage. Active entries inspected remove structural pruning. Every language was admitted by the frozen metadata/finite-score rule.','tab:review-external','llrrrr',r'Language & Pooling & Zero & Opt. & Ref. & Active',ext_main)
    table('review-external-all.tex',r'WMT24 all depths; $\alpha=.10$, 40 document-grouped split means. Coverage and active inspection are percentages.','tab:review-external-all','llrrrrr',r'Language & Pooling & $q$ & Zero & Opt. & Ref. & Active',ext_all)
    for agg in ['median','mean']:
        table('review-mqm-'+agg+'.tex',agg+r': native MQM diagnostic after reference-priority stopping. Obs.\ is the percentage of returned outputs with gold. MQM values use the official higher-is-better score scale. $\Delta K$ compares observed-label means of the original matched-$K$ lists; $\Delta J$ fixes the number $J$ of annotated returned outputs and compares within the observed-label subpopulation. Neither controls quality or imputes missing labels.','tab:review-mqm-'+agg,'llrrrrr',r'Language & Pooling & $q$ & Obs. (\%) & MQM & $\Delta K$ & $\Delta J$',[r for r in quality_rows if r[1]==agg])
    score_rows=[]
    for panel in PANELS:
        for agg in ['median','mean']:
            for q in [.05,.1,.2,.3]:
                for alpha in [.02,.05,.1,.15,.2]:
                    rr=choose(s['records'],dataset=panel,aggregator=agg,q=q,alpha=alpha);assert len(rr)==40
                    score_rows.append([LABELS[panel],agg,fmt(q,2),fmt(alpha,2),fmt(mean(rr,'risk'),3),fmt(100*mean(rr,'selected_coverage')),str(sum(r['risk']>alpha+1e-12 for r in rr))])
    for index,panel in enumerate(PANELS):
        for agg in ['median','mean']:
            table(f'review-score-{index}-{agg}.tex',LABELS[panel]+', '+agg+r': grouped SCoRE-MDR adapted to the same churn. $\alpha$ uses the nominal original normalization; SCoRE target is $\alpha/B$. Risk and coverage are 40-split means. Over counts realized batches over budget and does not refute expectation control. Full calibration candidate scores are used; test selection uses no candidate test entries.','tab:review-score-'+str(index)+'-'+agg,'rrrrr',r'$q$ & $\alpha$ & Risk & Sel. (\%) & Over / 40',[r[2:] for r in score_rows if r[0]==LABELS[panel] and r[1]==agg])
    # Replacement-wise risk is diagnostic, not the constrained average loss.
    for agg in ['median','mean']:
        rows=[]
        for panel in PANELS+['WMT24-en-de','WMT24-en-es','WMT24-ja-zh']:
            source=b if panel in PANELS else e
            for q in [.05,.1,.2,.3]:
                sel={'dataset':panel,'aggregator':agg,'q':q,'alpha':.1,'method':'reference_priority','stopping':'two_percent_gap'}
                rr=choose(source['query_records'],**sel);assert len(rr)==40
                rows.append([LABELS.get(panel,panel.replace('WMT24-','WMT24 ')),fmt(q,2),fmt(mean(rr,'risk'),3),fmt(mean(rr,'replacement_max_risk'),3),fmt(100*mean(rr,'replacement_over_alpha_fraction'))])
        table('review-replacement-'+agg+'.tex',agg+r': reference-priority returns at $\alpha=.10$, all depths. Avg.\ is replacement-average churn; max is the per-split maximum over the declared family, averaged across splits. Over is the mean percentage of replacements exceeding .10. Only Avg.\ is constrained.','tab:review-replacement-'+agg,'lrrrr',r'Panel & $q$ & Avg. & Max & Over (\%)',rows)
    costs=[]
    for panel in PANELS:
        sel={'dataset':panel,'aggregator':'median','q':.05,'alpha':.1}
        rr=choose(b['query_records'],**sel,method='reference_priority',stopping='two_percent_gap')
        full=choose(b['baseline_records'],**sel,method='batch_selected_optimum')
        crc=choose(b['baseline_records'],**sel,method='envelope_crc')
        score=choose(s['records'],**sel)
        for label,z in [('Reference',rr),('Full batch',full),('CRC',crc),('SCoRE',score)]:
            shared=mean(z,'candidate_reference_entries')+mean(z,'pool_reference_entries')+mean(z,'pool_test_entries')
            cal=sum(mean(z,f) or 0 for f in ['candidate_calibration_entries','pool_calibration_entries'])
            test=mean(z,'queries') if label=='Reference' else mean(z,'candidate_test_entries')
            costs.append([LABELS[panel],label,fmt(shared,0),fmt(cal,0),fmt(test,1),fmt(shared+cal+test,1)])
    table('review-workload.tex',r'Top-5\%, median, $\alpha=.10$: logical score-entry accounting in the shared fitted-map protocol. Setup includes pool/candidate reference entries and pool test entries. Cal.\ includes pool/candidate calibration entries; Test includes candidate test entries. Values are 40-split means, not runtime measurements. Structural zero-query certification can use endpoint bounds without candidate reference scores; no setup-optimality claim is made.','tab:review-workload','llrrrr',r'Panel & Method & Setup & Cal. & Test & Total',costs)
    sentinel=data['sentinel']['records'];rows=[]
    for r in sentinel:
        if r['status']=='OBSERVED':rows.append([r['language'],'Source' if 'sentinel-src' in r['probe'] else 'Reference',fmt(r['pooled_pearson'],3),str(r['within_paragraph_non_gold_tie_pairs']),fmt(100*r['within_paragraph_metric_tie_fraction']),fmt(r['within_paragraph_pair_accuracy_ties_half'],3)])
    table('review-sentinel.tex',r'Official missing-information sentinel probes on native annotated WMT24 entries. Pooled Pearson can be positive despite complete within-paragraph ties across MT systems. Pair accuracy assigns one half to metric ties and excludes human-score ties. This descriptive diagnostic changes no candidate family and does not identify invalid real metrics.','tab:review-sentinel','llrrrr',r'Language & Probe & Pearson & Pairs & Metric ties (\%) & Accuracy',rows)
    # Publication numerals are generated from complete records.
    def macro(name,value,d=1):macros.append('\\newcommand{\\'+name+'}{'+fmt(value,d)+'}')
    for panel,pre in zip(PANELS,['rb','wmt','excl']):
        for a,tag in [(.02,'Low'),(.05,'Middle'),(.2,'High')]:
            r=choose(b['query_records'],dataset=panel,aggregator='median',q=.05,alpha=a,method='reference_priority',stopping='two_percent_gap');macro(pre+tag+'Active',100*mean(r,'active_fraction'))
    for lp,pre in [('en-de','de'),('en-es','es'),('ja-zh','zh')]:
        for agg,tag in [('median','Median'),('mean','Mean')]:
            rr=choose(e['query_records'],dataset='WMT24-'+lp,aggregator=agg,q=.05,method='reference_priority',stopping='two_percent_gap');macro(pre+tag+'Active',100*mean(rr,'active_fraction'))
    for agg,tag in [('median','Median'),('mean','Mean')]:
        rr=choose(s['records'],dataset='RewardBench2',aggregator=agg,q=.05,alpha=.1);macro('scoreRb'+tag+'Cov',100*mean(rr,'selected_coverage'))
    cr=next(z for z in analysis['composition'] if z['dataset']=='WMT23' and z['aggregator']=='median' and z['q']==.05)
    macro('compWmtMedianActive',cr['median_reference_active_percent']);macro('compWmtMedianLow',cr['reference_active_10_90_percent'][0]);macro('compWmtMedianHigh',cr['reference_active_10_90_percent'][1])
    (TABLES/'review-numbers.tex').write_text('\n'.join(macros)+'\n')
    (ROOT/'outputs/review-analysis.json').write_text(json.dumps(analysis,indent=2)+'\n');(ROOT/'review-revision/render-source-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    print('PASS rendered complete audited grids',flush=True)
if __name__=='__main__':main()

"""Last idempotent layer: integer count means, captions, deduplicated evidence."""
from pathlib import Path
import csv,json,re
from decimal import Decimal,ROUND_HALF_UP
from audit_deduplicated_evidence import audit
ROOT=Path(__file__).resolve().parents[1];TAB=ROOT/'manuscript/tables'
def mean(values):return format((Decimal(sum(values))/Decimal(len(values))).quantize(Decimal('.1'),rounding=ROUND_HALF_UP),'.1f') if values else '--'
def caption(s,text):return re.sub(r'\\caption\{.*?\}\n\\label',lambda m:r'\caption{'+text+'}\n'+r'\label',s,count=1,flags=re.S)
def main():
    rs=list(csv.DictReader((ROOT/'outputs/query-mechanism-interventions/records.csv').open()))
    names={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13 streams','WMT23_without_synthetic_ref':'WMT23, 12 streams','WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
    p=TAB/'query-interventions.tex';s=p.read_text();lines=s.splitlines()
    rowlines=[]
    for panel,label in names.items():
        for q in [.05,.10,.20,.30]:
            groups={m:[r for r in rs if r['dataset']==panel and r['aggregator']=='mean' and float(r['q'])==q and r['method']==m and r['stopping']=='primary'] for m in ['reference_priority','oracle_row','oracle_candidate','oracle_both']}
            assert all(len(g)==40 for g in groups.values())
            counts=[mean([int(x['queries']) for x in groups['reference_priority']]),mean([int(x['width_queries']) for x in groups['reference_priority']])]+[mean([int(x['queries']) for x in groups[m]]) for m in ['oracle_row','oracle_candidate','oracle_both']]
            rowlines.append(' & '.join([label,f'{q:.2f}']+counts)+r' \\')
    start=s.index(r'\midrule')+len(r'\midrule');end=s.index(r'\bottomrule');s=s[:start]+'\n'+'\n'.join(rowlines)+'\n'+s[end:]
    s=caption(s,r'Same-instance mean-pooling interventions on complete original batches. Entries are mean candidate--output query counts over 40 splits, computed from integer sums with decimal half-up rounding. All use $\alpha=.10$ and first stop at $V^+-V^-\le\lceil .02|S_0|\rceil$. True row replaces predicted row totals in reference priority; True candidate uses true within-row flip contributions; Both combines them. These full-information diagnostics keep maps, cutoff, initial endpoint bounds, update rules, budget and stopping target fixed. They are not deployable policies. Median and exact-stop summaries accompany the code.')
    p.write_text(s)
    count=mean([int(x['queries']) for x in rs if x['dataset']=='WMT23' and x['aggregator']=='mean' and float(x['q'])==.05 and x['method']=='oracle_row' and x['stopping']=='primary'])
    (TAB/'deduplicated-numbers.tex').write_text(r'\newcommand{\trueRowWmtMeanQueries}{'+format(Decimal(count),',.1f')+'}\n')
    records=list(csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open()))
    shortnames={'RewardBench 2':'RewardBench2','WMT23, 13':'WMT23','WMT23, 12':'WMT23_without_synthetic_ref','WMT24 en-de':'WMT24-en-de','WMT24 en-es':'WMT24-en-es','WMT24 ja-zh':'WMT24-ja-zh'}
    for pool in ['mean','median']:
        for stopping in ['tolerant','exact']:
            p=TAB/f'nontrivial-{pool}-{stopping}.tex';out=[]
            for line in p.read_text().splitlines():
                if ' & ' in line and line.strip().endswith(r'\\'):
                    v=line.split(' & ')
                    if v[0] in shortnames and len(v)==10:
                        panel=shortnames[v[0]];q=float(v[1]);tau=.02 if stopping=='tolerant' else 0
                        for column,method in [(3,'fixed'),(4,'random'),(5,'largest_width'),(6,'reference_priority')]:
                            g=[x for x in records if x['dataset']==panel and x['aggregator']==pool and float(x['q'])==q and float(x['tau_value'])==tau and x['method']==method and int(x['queries'])>0]
                            assert len(g)==int(v[2]);v[column]=mean([int(x['queries']) for x in g])
                        v[8]=mean([int(x['returned_count']) for x in g]);v[9]=mean([int(x['certificate_gap']) for x in g])+r' \\'
                        line=' & '.join(v)
                out.append(line)
            s='\n'.join(out)+'\n';s=s.replace('Counts and ratios are averaged separately.','Integer count means use decimal half-up rounding; ratios are averaged separately.');p.write_text(s)
    for name in ['review-external.tex','review-external-all.tex']:
        p=TAB/name;s=p.read_text()
        if 'Ref.\\ stops' not in s:s=s.replace(r'\caption{',r'\caption{Ref.\ stops at $V^+-V^-\le\lceil .02|S_0|\rceil$; Opt.\ uses full information. ',1)
        p.write_text(s)
    for name in ['review-mqm-median.tex','review-mqm-mean.tex']:
        p=TAB/name;s=p.read_text().replace('both MQM means use only its annotated subset.','each MQM mean uses the annotated outputs in its own list.');p.write_text(s)
    p=TAB/'joint-small-batches.tex';s=p.read_text().replace('Shared / 40',r'\shortstack{$Q_{\rm joint}<Q_{\rm split}$\\splits/40}').replace('Shared counts strict joint savings.','Strict-gain columns count splits below the additive upper bound, not entry counts.').replace('The first group starts empty; the second starts','The first group starts empty; the second reports minimum additional entries after');p.write_text(s)
    p=TAB/'joint-discovery.tex';s=caption(p.read_text(), r'Mean-pooling discovery ratios from empty history on the same predefined subbatches at $q=.05$, $\alpha=.10$. The four policies use their original full definitions, including WMT24 priorities. Policy columns average $Q_{\rm online}/Q_{\rm joint}$ over the $n_+$ splits with positive matching minima; zero minima have undefined ratios. Mean $Q_{\rm joint}$ counts entry observations; policy columns are dimensionless mean splitwise ratios. Counts and certificate gaps concern this separate small-batch task, not the full-panel acquisition records.');p.write_text(s)
    p=TAB/'joint-full-discovery.tex';s=p.read_text()
    s=s.replace('Full-test mean entry minima and online discovery at exact stopping', 'Full-test mean entry minima and online discovery from empty history at exact stopping')
    s=s.replace('Strict shared-proof savings occur in 4/96 tasks: 2,645 entries out of 435,876 separately minimized proof entries (0.607\\%).',r'Mean $Q_{\rm joint}$ counts entry observations; policy columns are dimensionless. Joint minima are below the additive sum in 4/96 tasks, by 2,645 of 435,876 separately counted entries (0.607\%). The best deduplicated comparison is in Table~\ref{tab:deduplicated-summary}.')
    dr=list(csv.DictReader((ROOT/'outputs/outcome-joint-scale/full_discovery_records.csv').open()));new=[]
    reverse={v:k for k,v in names.items()}
    for line in s.splitlines():
        v=line.split(' & ')
        if len(v)==7 and v[0] in reverse and line.strip().endswith(r'\\'):
            g=[r for r in dr if r['dataset']==reverse[v[0]] and float(r['q'])==float(v[1]) and r['method']=='reference_priority'];assert len(g)==8
            v[2]=mean([int(r['minimum']) for r in g]);line=' & '.join(v)
        new.append(line)
    p.write_text('\n'.join(new)+'\n')
    p=TAB/'matched-tie-control.tex';s=p.read_text().replace(r'$\Delta K$ &',r'\shortstack{$\Delta K_{\rm tie}$\\Matched--Native} &');p.write_text(s)
    result,cases=audit(ROOT,False)
    rows=[]
    for r in result['summaries']:
        label='Full' if r['scope']=='full' else 'Small'
        rows.append(' & '.join([label,r['history'],str(r['epsilon']),str(r['instances']),str(r['joint_below_union']),str(r['double_count_reduction']),str(r['genuine_joint_reduction'])])+r' \\')
    s='\n'.join([r'\begin{table*}[t]',r'\centering\small',r'\begin{tabular}{llrrrrr}',r'\toprule',r'Task & History & $\varepsilon$ & $n$ & $Q_{\rm joint}<Q_{\cup,\rm sep}$ & Double count & Joint reduction \\',r'\midrule',*rows,r'\bottomrule',r'\end{tabular}',r'\caption{Mean entry evidence: separating deduplication from joint optimization. The strict-gain column counts instances. Double count sums $Q_{\rm split}-Q_{\cup,\rm sep}$; Joint reduction sums $Q_{\cup,\rm sep}-Q_{\rm joint}$ in additional entry observations. Each small row covers six panels, four depths and 40 splits, with the original reset subbatch budget. Full tasks preserve the original test batch and budget at two depths and eight splits per panel. All component ties are optimized; equal joint/additive cases use the proved bound sandwich. Histories are not charged again.}',r'\label{tab:deduplicated-summary}',r'\end{table*}',''])
    strict=[x for x in cases if x['scope']=='full' and x['joint_minimum']<x['result']['union_minimum']]
    rows=[' & '.join([names[x['dataset']],str(x['split']),f"{x['q']:.2f}",str(x['joint_minimum']),str(x['result']['union_minimum']),str(x['additive_minimum'])])+r' \\' for x in sorted(strict,key=lambda x:(x['dataset'],x['split'],x['q']))]
    s+='\n'.join([r'\begin{table*}[t]',r'\centering\small',r'\begin{tabular}{lrrrrr}',r'\toprule',r'Panel & Split & $q$ & $Q_{\rm joint}$ & $Q_{\cup,\rm sep}$ & $Q_{\rm split}$ \\',r'\midrule',*rows,r'\bottomrule',r'\end{tabular}',r'\caption{The four full mean instances with joint minima below optimally deduplicated separate witnesses. All use empty history, exact stopping and $\alpha=.10$. The other 92 full tasks have equality throughout. Both outcome-count and binary-entry programs prove these union optima; original time-limited attempts remain in the records. All costs count entry observations, not scorer calls or execution time.}',r'\label{tab:deduplicated-full}',r'\end{table*}',''])
    (TAB/'deduplicated-evidence.tex').write_text(s)
    print('Rendered deduplicated evidence, affected count means and final captions')
if __name__=='__main__':main()

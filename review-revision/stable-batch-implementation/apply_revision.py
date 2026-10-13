from pathlib import Path
import json,re
D=Path(__file__).resolve().parent;R=D.parents[1];changes=[]
def edit(name,old,new):
 p=R/name;s=p.read_text();assert s.count(old)==1,(name,old[:100]);p.write_text(s.replace(old,new));changes.append(dict(file=name,old=old,new=new))
app=(R/'manuscript/appendix.tex').read_text();start=app.index('\\begin{table}[t]',app.index('Table~\\ref{tab:joint-example} instantiates'));end=app.index('\\end{table}',start)+len('\\end{table}')
table=app[start:end]
edit('manuscript/appendix.tex',table,'')
old=r'''An entry with true flip contribution $f_{ir}$ raises its row's lower cost by $f_{ir}$ and reduces its upper cost by $p_i-f_{ir}$. Flip counts are integers. Mean pooling can have $0<f_{ir}<p_i$, so one query contributes to both proofs. For a realizable mean pool with $M=7$, $T=6$ and flip budget $b_H=6$, two selected rows have caps seven and six and contributions $(1,1,1,1,1,1)$ and $(1,0,0,0,0,0)$. Minimum safety reveals the second row's five zeros; excluding both rows needs all seven positive entries. Their best union has twelve entries. Querying all six first-row entries and the second row's positive entry instead retains the first row and excludes both, using seven entries (Appendix~\ref{app:deduplicated}).'''
new=r'''An entry with true flip contribution $f_{ir}$ raises its row's lower cost by $f_{ir}$ and reduces its upper cost by $p_i-f_{ir}$. Mean pooling can have integer $0<f_{ir}<p_i$, so one query contributes to both proofs. Table~\ref{tab:joint-example} shows how changing the retained row reduces the evidence union from twelve entries to seven. Appendix~\ref{app:deduplicated} realizes these contributions as mean scores and proves minimality.'''+ '\n\n'+table
edit('manuscript/main.tex',old,new)
edit('manuscript/main.tex',r'''Unobserved scores range over $[0,1]$ without cross-entry constraints.''',r'''Unobserved scores range freely over $[0,1]$; this is a completion set, not a statistical independence assumption.''')
old=r'''Our target is evidence for a fixed certification task.'''
new=r'''Predictive churn concerns model updates and training-sample changes \citep{watsondaniels2025predictive,prastalo2026reducing}; fixed-threshold routing can change even with matching class predictions \citep{kim2026lottery}. We instead measure the score evidence needed to certify retention for a fixed batch and replacement family.'''
edit('manuscript/main.tex',old,new)
old=r'''The average constraint does not require every replacement to satisfy the same budget $\alpha$.'''
new=r'''This is an average replacement allowance, not a per-replacement limit or a review-capacity quota.'''
edit('manuscript/main.tex',old,new)
old=r'''Fixed-count selection changes the size constraint; batch-feasible and calibrated controls provide different guarantees.'''
new=r'''Across 15,360 certified masks at $\alpha=.10$, 6,985 have an individual replacement risk above $.10$, despite meeting the average budget (Appendix~\ref{app:review-replacement}). Fixed-count selection changes the size constraint; batch-feasible and calibrated controls provide different guarantees.'''
# Resolve the actual enclosing appendix label rather than inventing a reference.
a=(R/'manuscript/appendix.tex').read_text();pos=a.index('\\paragraph{Risk across individual replacements.}');labels=re.findall(r'\\label\{([^}]+)\}',a[:pos]);print('risk nearest label',labels[-1]);new=new.replace('app:review-replacement',labels[-1])
edit('manuscript/main.tex',old,new)
old=r'''All 114 non-full-retention targets require every candidate column. A realizable mean example nevertheless permits strict column gain (Appendix~\ref{app:mean-even-columns}).'''
new=r'''All 114 non-full-retention targets require every candidate column. Proposition~\ref{prop:all-columns} characterizes this requirement by the gap after omitting each column; its range condition explains 101 targets. A realizable mean example nevertheless permits strict column gain (Appendix~\ref{app:mean-even-columns}).'''
edit('manuscript/main.tex',old,new)
old=r'''The column range condition forces full revelation in 101/114 non-full-retention targets under any within-row permutation (Proposition~\ref{prop:all-columns}). Query grouping can therefore prevent savings even when entries share evidence.'''
new=r'''The column range condition survives every within-row permutation of candidate scores. Query grouping can therefore prevent savings even when entries share evidence.'''
edit('manuscript/main.tex',old,new)
old=r'''Across 960 primary targets, joint savings average 5.34 entries; reference queries exceed joint minima by 809.58 (Table~\ref{tab:cost-contrasts}). Short witnesses need not be easy to find: at fixed $M=T=7$, $q=.05$, $\alpha=.10$, exact discovery can require queries linear in batch size despite a one-entry certificate (Proposition~\ref{prop:fixed-discovery}). This construction stops immediately at the primary tolerance and does not explain the measured overhead.'''
new=r'''Across 960 primary targets, joint savings average 5.34 entries; reference queries exceed joint minima by 809.58 (Table~\ref{tab:cost-contrasts}). At fixed $M=T=7$, $q=.05$, $\alpha=.10$ and the primary tolerance, a two-entry certificate can still require online discovery cost linear in batch size (Proposition~\ref{prop:positive-discovery}). This worst-case obstruction leaves the empirical causes of overhead to be established. Same-instance interventions show that exact row or candidate predictions alone need not improve a fixed query rule (Appendix~\ref{app:query-interventions}).'''
edit('manuscript/main.tex',old,new)
needle=r'\paragraph{Fixed query actions.}'
edit('manuscript/appendix.tex',needle,(D/'positive-discovery.tex').read_text()+needle)
# Official bibliography exports; no guessed author, venue or publication status.
p=R/'manuscript/references.bib';old=p.read_text();items=json.loads((D/'citation-entries.json').read_text());new=old+'\n\n'+'\n\n'.join(x['bib'] for x in items)+'\n';edit('manuscript/references.bib',old,new)
(D/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')

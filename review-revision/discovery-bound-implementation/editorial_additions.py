from pathlib import Path
import json
D=Path(__file__).resolve().parent;R=D.parents[1];changes=json.loads((D/'changes.json').read_text())
(D/'editorial-three-pass.json').write_text(json.dumps({'source':'Existing Proposition strict-joint, T=6, M=7, budget6, caps7/6; no new scientific setting. Online source abstracts checked for three existing citations.','arithmetic':'Safety five zeros on row2 gives upper6. Exclusion seven positives gives lower total7>6. Joint same seven observations make row1 upper6. Union12 and joint7.','spine':'One existing example becomes a visual comparison; no new objective. Literature comparison kept in local assessment rather than a new manuscript section.'},indent=2))
p=R/'manuscript/appendix.tex';s=p.read_text()
old=r'This construction isolates a choice of safety witness: the independently shortest proof certifies the second row, whereas the joint optimum certifies the first. Its count reduction is not double counting. Exact rational score checks and independent query-subset enumeration verify the construction; NLP reductions above remain measured on their own fixed panels.'
new=r'''Table~\ref{tab:joint-example} instantiates the construction at $T=6$. The separately shortest safety proof retains row~2; joint optimization retains row~1 using evidence already needed for exclusion. Exact rational score checks and independent query-subset enumeration verify the construction; NLP reductions above remain measured on their own fixed panels.
\begin{table}[t]
\centering\small
\begin{tabular}{@{}lccr@{}}
\toprule
Evidence & Row 1 & Row 2 & Entries\\
\midrule
Minimum safety & \texttt{......} & \texttt{.00000} & 5\\
Minimum exclusion & \texttt{111111} & \texttt{1.....} & 7\\
Best separate union & \texttt{111111} & \texttt{100000} & 12\\
Joint & \texttt{111111} & \texttt{1.....} & 7\\
\bottomrule
\end{tabular}
\caption{The same two-row mean example as Section~\ref{sec:median}, with caps $(7,6)$ and flip budget six. Digits denote revealed contributions; dots denote unqueried entries. Joint evidence makes row~1's upper cost six and the combined lower cost seven, certifying retention of one row and excluding both.}
\label{tab:joint-example}
\end{table}'''
assert s.count(old)==1;p.write_text(s.replace(old,new));changes.append(dict(file='manuscript/appendix.tex',old=old,new=new));(D/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')

from pathlib import Path
import json,difflib
D=Path(__file__).resolve().parent;R=D.parents[1];changes=json.loads((D/'changes.json').read_text())
def edit(name,a,b):
 p=R/name;s=p.read_text();assert s.count(a)==1,(name,a[:50]);p.write_text(s.replace(a,b));changes.append(dict(file=name,old=a,new=b))
edit('manuscript/main.tex','Mixed frontier results leave reliable online improvement unresolved. Future work could study evidence-location predictions and online query bounds under explicit assumptions.','Discovery overhead remains much larger than the savings from joint optimization.')
a=(R/'manuscript/appendix.tex').read_text();start=a.index(r'\paragraph{A condition forcing every column.}');end=a.index(r'\paragraph{Changing column layout',start);old=a[start:end];new=old.replace(r'$a_i=\min_r f_{ir}$ and $d_i=\max_r f_{ir}$',r'$\underline f_i=\min_r f_{ir}$ and $\overline f_i=\max_r f_{ir}$').replace('V(F-a)-V(F+p-d)',r'V(F-\underline f)-V(F+p-\overline f)').replace(r'$a_i\le f_{ir}\le d_i$',r'$\underline f_i\le f_{ir}\le\overline f_i$').replace('$F,a,d,p$',r'$F,\underline f,\overline f,p$')
new=new.replace(r''' V(F-f_{\cdot r})-V(F+p-f_{\cdot r})
 \ge V(F-\underline f)-V(F+p-\overline f).''',r''' \begin{aligned}
 &V(F-f_{\cdot r})-V(F+p-f_{\cdot r})\\
 &\qquad\ge V(F-\underline f)-V(F+p-\overline f).
 \end{aligned}''')
edit('manuscript/appendix.tex',old,new)
(D/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
diff=''
for name in ['manuscript/main.tex','manuscript/appendix.tex']:
 diff+=''.join(difflib.unified_diff((D/'before'/name).read_text().splitlines(True),(R/name).read_text().splitlines(True),fromfile='before/'+name,tofile=name))
(D/'source.diff').write_text(diff)

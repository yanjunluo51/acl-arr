from pathlib import Path
import json,difflib
D=Path(__file__).resolve().parent;R=D.parents[1];p=R/'manuscript/main.tex';s=p.read_text();changes=json.loads((D/'changes.json').read_text())
pairs=[(r'Choosing the retained set changes the evidence needed for safety and exclusion. A longer safety proof can therefore shorten their union, as the fixed-$M$ construction and restricted near-full criterion demonstrate.',r'Choosing the retained set couples safety and exclusion. Joint optimization can favor a longer safety proof when it shortens their combined evidence.'),(r'Joint evidence can certify stable retention with fewer scores than the best union of separately minimum proofs. Our characterizations and realizable separations establish this distinction. NLP entry gains are limited, with none on matching mean column targets. Certificate minima benchmark acquisition; reliable online attainment remains open.',r'Joint evidence can certify stable retention with fewer scores than the best union of separately minimum proofs. NLP entry gains are limited and absent on matching mean column targets. Certificate minima benchmark acquisition; reliable online attainment remains open.'),(r'On RewardBench~2 and five WMT panels, strict gains occur in 89 of 1,920 mean entry targets and none of the matching column targets. Online policies generally need more queries.',r'Experiments on RewardBench~2 and five WMT panels find limited mean entry gains, none on matching column targets, and generally higher online query counts.')]
for a,b in pairs:
 assert s.count(a)==1;s=s.replace(a,b);changes.append(dict(file='manuscript/main.tex',old=a,new=b))
p.write_text(s);(D/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
diff=''
for name in ['manuscript/main.tex','manuscript/appendix.tex']:
 diff+=''.join(difflib.unified_diff((D/'before'/name).read_text().splitlines(True),(R/name).read_text().splitlines(True),fromfile='before/'+name,tofile=name))
(D/'source.diff').write_text(diff)

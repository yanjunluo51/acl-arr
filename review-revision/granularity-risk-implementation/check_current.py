from pathlib import Path
import json,hashlib,re
import fitz,numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 changes=json.loads((D/'changes.json').read_text())
 for name in ['manuscript/main.tex','manuscript/appendix.tex']:
  s=(D/'before'/name).read_text()
  for x in changes:
   if x['file']==name:
    assert s.count(x['old'])==1;s=s.replace(x['old'],x['new'])
  assert s==(R/name).read_text(),name
 main=(R/'manuscript/main.tex').read_text();app=(R/'manuscript/appendix.tex').read_text()
 def expand(s):return re.sub(r'\\input\{([^}]+)\}',lambda m:expand((R/'manuscript'/(m.group(1)+'.tex')).read_text()),s)
 full=expand(main);labels=re.findall(r'\\label\{([^}]+)\}',full);assert len(labels)==len(set(labels));assert set(re.findall(r'\\(?:ref|pageref)\{([^}]+)\}',full))<=set(labels)
 cited={k for g in re.findall(r'\\cite\w*\*?(?:\[[^]]*\])*\{([^}]+)\}',full) for k in g.split(',')};keys=set(re.findall(r'@\w+\s*\{\s*([^,]+),',(R/'manuscript/references.bib').read_text()));assert cited<=keys and len(cited)==46
 # Every pre-existing formal block remains verbatim. Exactly one proposition
 # and its proof were added; no old theorem is silently strengthened.
 pat=r'\\begin\{(theorem|lemma|corollary|proposition|proof)\}.*?\\end\{\1\}'
 added=0
 for name,s in [('main.tex',main),('appendix.tex',app)]:
  old=[x.group() for x in re.finditer(pat,(D/'before/manuscript'/name).read_text(),re.S)];new=[x.group() for x in re.finditer(pat,s,re.S)]
  for block in old:assert block in new;new.remove(block)
  added+=len(new)
 assert added==2
 log=(R/'manuscript/main.log').read_text(errors='replace')
 for flag in ['Overfull','undefined references','undefined citations','multiply defined','LaTeX Error','Label(s) may have changed']:assert flag not in log,flag
 doc=fitz.open(R/'manuscript/main.pdf');assert 'Conclusion' in doc[7].get_text();assert doc[8].get_text().startswith('Limitations\n');assert '??' not in ''.join(p.get_text() for p in doc)
 outside=[];collision=[];fonts=set()
 for pi,p in enumerate(doc):
  black=[];numbers=[]
  for b in p.get_text('rawdict')['blocks']:
   for line in b.get('lines',[]):
    for sp in line['spans']:
     if sp['color']==0:
      for c in sp['chars']:
       if c['c'].strip():
        rect=fitz.Rect(c['bbox']);black.append(list(rect))
        if rect.x0<67.866 or rect.x1>p.rect.width-67.866:outside.append([pi+1,c['c']])
     elif sp['color']==12566463 and ''.join(c['c'] for c in sp['chars']).isdigit():numbers.extend(fitz.Rect(c['bbox']) for c in sp['chars'])
  boxes=np.array(black).reshape(-1,4)
  for n in numbers:
   if ((boxes[:,0]<n.x1)&(boxes[:,2]>n.x0)&(boxes[:,1]<n.y1)&(boxes[:,3]>n.y0)).any():collision.append(pi+1)
  for f in p.get_fonts():
   if f[0] not in fonts:assert f[2]!='Type3' and doc.extract_font(f[0])[3];fonts.add(f[0])
 assert not outside,outside[:5];assert not collision,collision[:5]
 words=len(main.split('\\begin{abstract}')[1].split('\\end{abstract}')[0].split());assert words<=200
 layout=json.loads((D/'layout-audit.json').read_text());risk=json.loads((D/'risk-audit.json').read_text())
 assert layout['targets']==570 and layout['condition_coverage']=={'primary':45,'exact':56}
 assert risk['masks']==15360 and risk['any_over_masks']==6985 and risk['average_budget_violations']==0
 out=dict(status='PASS_SCOPED_GRANULARITY_RISK_REVISION',pdf_pages=len(doc),technical_main_pages=8,limitations_page=9,abstract_words=words,citations=len(cited),font_margin_line_number_checks=True,existing_formal_blocks_unchanged=True,new_sufficient_condition=True,general_necessity_characterization=False,layout_targets=570,risk_masks=15360,finite_condition_checks=layout['finite_integer_instances'],new_model_inference=False,source_hashes={f:sha(R/f) for f in ['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','manuscript/references.bib']})
 (D/'current-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

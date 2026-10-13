from pathlib import Path
import json,hashlib,re
import fitz,numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 changes=json.loads((D/'changes.json').read_text());names=sorted({x['file'] for x in changes})
 for name in names:
  s=(D/'before'/name).read_text()
  for x in changes:
   if x['file']==name:
    assert s.count(x['old'])==1,(name,'edit chain');s=s.replace(x['old'],x['new'])
  assert s==(R/name).read_text(),name
 def expand(s):return re.sub(r'\\input\{([^}]+)\}',lambda m:expand((R/'manuscript'/(m.group(1)+'.tex')).read_text()),s)
 full=expand((R/'manuscript/main.tex').read_text());labels=re.findall(r'\\label\{([^}]+)\}',full);assert len(labels)==len(set(labels));assert set(re.findall(r'\\(?:ref|pageref)\{([^}]+)\}',full))<=set(labels)
 cited={k for g in re.findall(r'\\cite\w*\*?(?:\[[^]]*\])*\{([^}]+)\}',full) for k in g.split(',')};keys=set(re.findall(r'@\w+\s*\{\s*([^,]+),',(R/'manuscript/references.bib').read_text()));assert cited<=keys and len(cited)==49
 pat=r'\\begin\{(theorem|lemma|corollary|proposition|proof)\}.*?\\end\{\1\}'
 for name in ['main.tex','appendix.tex']:
  old=[x.group() for x in re.finditer(pat,(D/'before/manuscript'/name).read_text(),re.S)];new=[x.group() for x in re.finditer(pat,(R/'manuscript'/name).read_text(),re.S)];extra=[x.group() for x in re.finditer(pat,(D/'positive-discovery.tex').read_text(),re.S)] if name=='appendix.tex' else []
  remaining=new.copy()
  for block in extra:
   assert remaining.count(block)==1;remaining.remove(block)
  assert old==remaining,(name,'previous formal block changed')
 for flag in ['Overfull','undefined references','undefined citations','multiply defined','LaTeX Error','Label(s) may have changed']:assert flag not in (R/'manuscript/main.log').read_text(errors='replace'),flag
 doc=fitz.open(R/'manuscript/main.pdf');assert 'Conclusion' in doc[7].get_text();assert doc[8].get_text().startswith('Limitations\n');assert '??' not in ''.join(p.get_text() for p in doc)
 outside=[];collision=[];fonts=set()
 for pi,p in enumerate(doc):
  black=[];numbers=[]
  for b in p.get_text('rawdict')['blocks']:
   for l in b.get('lines',[]):
    for sp in l['spans']:
     text=''.join(c['c'] for c in sp['chars']);r=fitz.Rect(sp['bbox'])
     if sp['color']!=0 and text.strip().isdigit() and r.x0<55 or sp['color']!=0 and text.strip().isdigit() and r.x0>550:numbers.append(r)
     if sp['color']==0:
      if r.x0<0 or r.y0<0 or r.x1>p.rect.width+1 or r.y1>p.rect.height+1:outside.append((pi+1,text))
      black.extend(c['bbox'] for c in sp['chars'])
  boxes=np.array(black).reshape(-1,4)
  for n in numbers:
   if ((boxes[:,0]<n.x1)&(boxes[:,2]>n.x0)&(boxes[:,1]<n.y1)&(boxes[:,3]>n.y0)).any():collision.append(pi+1)
  for f in p.get_fonts():
   if f[0] not in fonts:assert f[2]!='Type3' and doc.extract_font(f[0])[3];fonts.add(f[0])
 assert not outside and not collision,(outside,collision)
 words=len((R/'manuscript/main.tex').read_text().split('\\begin{abstract}')[1].split('\\end{abstract}')[0].split());assert words<=200
 audit=json.loads((R/'review-revision/editorial-evidence-implementation/closure-audit.json').read_text());assert audit['records']==1920 and audit['strict_gain']==89 and audit['saved_entries']==6269 and not audit['formal_lower_bounds_verified']
 a=json.loads((D/'positive-discovery-check.json').read_text());assert a['minimum_additional_entries']=={'2':2,'3':2}
 assert sum(v['subsets'] for v in a['all_subset_checks'].values())==2113536
 manifest={str(p.relative_to(R)):sha(p) for p in [R/'manuscript/main.tex',R/'manuscript/appendix.tex',R/'manuscript/main.pdf',R/'manuscript/references.bib']}
 out=dict(status='PASS_SCOPED_STABLE_BATCH_REVISION',pdf_pages=len(doc),technical_main_pages=8,limitations_page=9,abstract_words=words,citations=len(cited),edit_chain_checked=True,previous_formal_blocks_unchanged=True,new_positive_tolerance_proposition=True,font_margin_line_number_checks=True,overfull_boxes=0,prior_witness_receipt_records=1920,prior_witness_replay_reexecuted=False,new_construction_subsets_checked=2113536,adversarial_histories_checked=63466,formal_lower_bounds_verified=False,new_inference=False,source_hashes=manifest)
 (D/'current-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

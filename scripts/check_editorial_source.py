"""Check live manuscript, preserved scientific inputs, PDF geometry and source bindings."""
from pathlib import Path
import difflib,hashlib,json,re
import fitz,numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/editorial-integration-20261006';OLD=ROOT/'history/before-editorial-integration-20261006'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 pre=json.loads((ROOT/'review-revision/evidence-discovery-implementation-20261005/pre-edit-checks.json').read_text())
 for n,h in pre['protected_scientific_outputs'].items():assert sha(ROOT/n)==h,n
 m=(ROOT/'manuscript/main.tex').read_text();a=(ROOT/'manuscript/appendix.tex').read_text()
 assert not any(ord(c)<32 and c not in '\n\t\r' for c in m+a)
 assert 'The four original orders are shared across budgets' in m and 'Frontier depends on the budget.' in m
 assert 'in solved comparisons' in m and 'unit-cost operations' in a
 assert 'after with' not in m+a and 'require quality evidence' not in m
 factor=json.loads((OUT/'factor-two-check.json').read_text());assert factor['saved_matched_cases']==3936 and factor['independent_finite_cases']==84
 assert r'Q_{\rm split}\le 2Q_{\rm joint}' in a and 'asymptotically tight even after optimal deduplication' in a
 bib=(ROOT/'manuscript/references.bib').read_text();keys=re.findall(r'@\w+\s*\{\s*([^,]+)',bib);cites={k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}',m+a) for k in cs.split(',')};assert cites<=set(keys) and len(keys)==len(set(keys))
 def expand(s):return re.sub(r'\\input\{([^}]+)\}',lambda x:expand((ROOT/'manuscript'/(x.group(1)+'.tex')).read_text()),s)
 expanded=expand(m);labels=re.findall(r'\\label\{([^}]+)\}',expanded);assert len(labels)==len(set(labels))
 refs=re.findall(r'\\(?:ref|pageref)\{([^}]+)\}',expanded);assert set(refs)<=set(labels),set(refs)-set(labels)
 blocks=re.findall(r'\\begin\{table\*?\}.*?\\end\{table\*?\}',expanded,re.S);assert all(b.index(r'\caption')>b.index(r'\begin{tabular}') for b in blocks)
 abstract=m.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0];words=len(abstract.replace('~',' ').split());assert words<=200
 doc=fitz.open(ROOT/'manuscript/main.pdf');texts=[p.get_text() for p in doc]
 ending=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t));lim=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t));assert ending<=8 and lim>=ending
 normalized=lambda t:re.sub(r'[^A-Za-z]','',t).lower()
 assert 'theguaranteeconcernsretentionunderthedeclaredchurnbudget' in normalized(''.join(texts[:8])),'Conclusion spills beyond eight pages'
 assert '??' not in '\n'.join(texts) and not re.search(r'/(Users|home)/','\n'.join(texts)) and not doc.metadata.get('author','')
 log=(ROOT/'manuscript/main.log').read_text(errors='replace');assert 'Overfull' not in log and 'undefined' not in log
 outside=[];collisions=[];fonts=set()
 for pi,p in enumerate(doc):
  black=[];numbers=[]
  for b in p.get_text('rawdict')['blocks']:
   for line in b.get('lines',[]):
    for span in line['spans']:
     if span['color']==0:
      for c in span['chars']:
       if c['c'].strip():
        rect=fitz.Rect(c['bbox']);black.append(rect)
        if rect.x0<67.866 or rect.x1>p.rect.width-67.866:outside.append([pi+1,c['c'],list(rect)])
     elif ''.join(c['c'] for c in span['chars']).isdigit():numbers.extend(fitz.Rect(c['bbox']) for c in span['chars'])
  boxes=np.array([list(x) for x in black]).reshape(-1,4)
  for n in numbers:
   if ((boxes[:,0]<n.x1)&(boxes[:,2]>n.x0)&(boxes[:,1]<n.y1)&(boxes[:,3]>n.y0)).any():collisions.append([pi+1,list(n)])
  for f in p.get_fonts():
   if f[0] not in fonts:assert f[2]!='Type3' and doc.extract_font(f[0])[3];fonts.add(f[0])
 assert not outside,outside[:8];assert not collisions,collisions[:8]
 audit=json.loads((ROOT/'outputs/full-mean-grid-20261005/audit.json').read_text())
 numbers=(ROOT/'manuscript/tables/evidence-main-numbers.tex').read_text()
 assert r'\newcommand{\fullMeanProven}{'+str(audit['joint_proven'])+'}' in numbers
 assert r'\newcommand{\fullMeanUnionProven}{'+str(audit['union_proven'])+'}' in numbers
 visual=OUT/'visual';visual.mkdir(exist_ok=True)
 terms=['Full-test mean certificates','Complete full-test mean','Joint evidence beyond','strict joint','Certificate-directed acquisition','Full-test mean entry','Common information','Protocol changes and median']
 pages=sorted(set(list(range(1,10))+[i+1 for i,t in enumerate(texts) if any(x.lower() in t.lower() for x in terms)]))
 for i in pages:doc[i-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(visual/f'page-{i}.png')
 for n in ['main.tex','appendix.tex','references.bib']:
  old=(OLD/'manuscript'/n).read_text();new=(ROOT/'manuscript'/n).read_text();(OUT/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before/'+n,tofile='after/'+n)))
 result=dict(status='PASS_SCOPED_EDITORIAL_SOURCE_AND_PDF',technical_main_pages=ending,limitations_start_page=lim,total_pdf_pages=len(doc),abstract_words=words,table_source_files=len(list((ROOT/'manuscript/tables').glob('*.tex'))),tables=len(blocks),captions_below_tables=True,overfull_boxes=0,undefined_references=0,outside_horizontal_margins=0,line_number_collisions=0,embedded_fonts=True,citation_key_integrity=True,cited_keys=len(cites),protected_scientific_outputs=len(pre['protected_scientific_outputs']),factor_two_bound_and_tight_family=True,joint_proven=audit['joint_proven'],union_proven=audit['union_proven'],rendered_pages=pages,human_proof_certified=False,complete_redistribution_authorized=False)
 files=['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','manuscript/references.bib']+[str(p.relative_to(ROOT)) for p in (ROOT/'manuscript/tables').glob('*.tex')];result['artifact_hashes']={n:sha(ROOT/n) for n in sorted(files)}
 (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='artifact_hashes'},indent=2))
if __name__=='__main__':main()

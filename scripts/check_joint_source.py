"""Successor checks: preserved old statements/data, new witnesses and clean PDF."""
from pathlib import Path
import difflib,hashlib,json,re
import fitz,numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/joint-certificate-implementation';OLD=ROOT/'history/before-joint-certificate-review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    for section in ['frozen_hashes','protected_hashes']:
        for n,h in pre[section].items():assert sha(ROOT/n)==h,n
    m=(ROOT/'manuscript/main.tex').read_text();a=(ROOT/'manuscript/appendix.tex').read_text();bm=(OLD/'manuscript/main.tex').read_text();ba=(OLD/'manuscript/appendix.tex').read_text()
    for env in ['theorem','proposition','corollary','lemma']:
        pat=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
        old=re.findall(pat,bm+ba,re.S);new=re.findall(pat,m+a,re.S)
        for statement in old:assert statement in new,(env,statement[:150])
    assert re.findall(r'\\begin\{algorithm\}.*?\\end\{algorithm\}',bm,re.S)==re.findall(r'\\begin\{algorithm\}.*?\\end\{algorithm\}',m,re.S)
    assert 'polynomial in the explicit counts' in a and 'pseudo-polynomial' in a
    assert r'\label{thm:joint}' in m and r'\label{lem:order-threshold}' in a
    assert not any(ord(c)<32 and c not in '\n\t\r' for c in m+a)
    assert (ROOT/'manuscript/references.bib').read_bytes()==(OLD/'manuscript/references.bib').read_bytes()
    bib=(ROOT/'manuscript/references.bib').read_text();keys=re.findall(r'@\w+\s*\{\s*([^,]+)',bib);cites={k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}',m+a) for k in cs.split(',')};assert cites<=set(keys) and len(keys)==len(set(keys))
    for p in (OLD/'manuscript/tables').glob('*.tex'):
        assert p.read_bytes()==(ROOT/'manuscript/tables'/p.name).read_bytes(),p.name
    assert len(list((ROOT/'manuscript/tables').glob('*.tex')))==71
    def expand(s):return re.sub(r'\\input\{([^}]+)\}',lambda x:expand((ROOT/'manuscript'/(x.group(1)+'.tex')).read_text()),s)
    blocks=re.findall(r'\\begin\{table\*?\}.*?\\end\{table\*?\}',expand(m),re.S);assert len(blocks)==83 and all(b.index(r'\caption')>b.index(r'\begin{tabular}') for b in blocks)
    abstract=m.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0];words=len(abstract.replace('~',' ').split());assert words<200
    doc=fitz.open(ROOT/'manuscript/main.pdf');texts=[p.get_text() for p in doc];ending=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t));lim=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t));assert ending<=8 and lim>=ending
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
    visual=OUT/'visual';visual.mkdir(exist_ok=True)
    pages=sorted(set(list(range(1,9))+[i+1 for i,t in enumerate(texts) if any(x in t for x in ['Joint entry evidence','Joint-certificate validation','Same-instance row','Exact mean entry certificates','Mean-pooling discovery ratios','Same-instance mean-pooling interventions'])]))
    for i in pages:doc[i-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(visual/f'page-{i}.png')
    for n in ['main.tex','appendix.tex']:
        old=(OLD/'manuscript'/n).read_text();new=(ROOT/'manuscript'/n).read_text();(OUT/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before/'+n,tofile='after/'+n)))
    result={'status':'PASS_SCOPED_JOINT_SOURCE_AND_PDF_CHECKS','technical_main_pages':ending,'limitations_start_page':lim,'total_pdf_pages':len(doc),'abstract_words':words,'old_formal_statements_preserved':True,'original_algorithm_preserved':True,'original_table_sources_byte_preserved':68,'table_source_files':71,'tables':83,'captions_below_tables':True,'new_joint_theorem':True,'new_threshold_lemma':True,'citation_key_integrity':True,'bibliography_preserved':True,'overfull_boxes':0,'undefined_references':0,'outside_horizontal_margins':0,'line_number_collisions':0,'embedded_fonts':True,'rendered_pages':pages,'frozen_inputs_preserved':len(pre['frozen_hashes']),'protected_historical_files_preserved':len(pre['protected_hashes']),'human_proof_certified':False,'full_novelty_certified':False,'complete_redistribution_authorized':False}
    files=['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','manuscript/references.bib']+[str(p.relative_to(ROOT)) for p in (ROOT/'manuscript/tables').glob('*.tex')]
    result['artifact_hashes']={n:sha(ROOT/n) for n in sorted(files)};(OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='artifact_hashes'},indent=2))
if __name__=='__main__':main()

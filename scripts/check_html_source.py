"""Current source/math/values/visual checks with explicitly allowed proof repairs."""
from pathlib import Path
import difflib,hashlib,json,re
import fitz,numpy as np
from check_commitment_stopping_revision import displays
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/html-review-implementation';OLD=ROOT/'history/before-html-review-20261005'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    for n,h in pre['protected_hashes'].items():assert sha(ROOT/n)==h,n
    for n,h in pre['frozen_hashes'].items():assert sha(ROOT/n)==h,n
    m=(ROOT/'manuscript/main.tex').read_text();a=(ROOT/'manuscript/appendix.tex').read_text()
    bm=(OLD/'manuscript/main.tex').read_text();ba=(OLD/'manuscript/appendix.tex').read_text()
    assert displays(m)==displays(bm)
    old_displays=displays(ba);new_displays=displays(a);remaining=new_displays.copy()
    for d in old_displays:remaining.remove(d)
    assert len(remaining)==2,'Only DP recurrence and its G evaluation are new displays'
    for env in ['theorem','proposition','corollary','lemma']:
        pat=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
        old_statements=re.findall(pat,bm+ba,re.S);new_statements=re.findall(pat,m+a,re.S)
        assert len(old_statements)==len(new_statements),(env,'statement count')
        for x,y in zip(old_statements,new_statements):
            y=y.replace('If no $L$-row set is feasible under true costs, no such certificate exists.',
                        'For an infeasible target, no such certificate exists.')
            assert re.findall(r'\$(.*?)\$',x,re.S)==re.findall(r'\$(.*?)\$',y,re.S),(env,'formal math')
    assert re.findall(r'\\begin\{algorithm\}.*?\\end\{algorithm\}',bm,re.S)==re.findall(r'\\begin\{algorithm\}.*?\\end\{algorithm\}',m,re.S)
    assert r'Safety requires at least $\max(0,sT-b)$' in a
    assert r'$2\min(k,N-k)$' in a and 'no $p$-row set feasible under any consistent completion' in a
    assert 'provisional masks after queries' in m and 'statistical quality claims must account' in a
    assert not re.search(r'\\clearpage\s*\\section\*\{Limitations\}',m)
    assert not any(ord(c)<32 and c not in '\n\t\r' for c in m+a)
    assert 'AUTHOR CHECK' not in m+a and 'every saved stopping count bounds' not in a
    bib=(ROOT/'manuscript/references.bib').read_text()
    normalized_bib=re.sub(r'(@inproceedings\{fermanian2025transductive,.*?\n\})',lambda match:match.group().replace('  volume    = {38},\n','').replace('  doi       = {10.52202/085713-0212},\n',''),bib,flags=re.S)
    assert normalized_bib.rstrip()==(OLD/'manuscript/references.bib').read_text().rstrip()
    keys=re.findall(r'@\w+\s*\{\s*([^,]+)',bib)
    cites={k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}',m+a) for k in cs.split(',')}
    assert len(keys)==len(set(keys)) and cites<=set(keys)
    tables=[];captionchanged=[]
    for p in (OLD/'manuscript/tables').glob('*.tex'):
        old=p.read_text();new=(ROOT/'manuscript/tables'/p.name).read_text()
        # Every old tabular remains byte-for-byte equal; only surrounding prose moves.
        pattern=r'\\begin\{tabular\}.*?\\end\{tabular\}'
        assert re.findall(pattern,old,re.S)==re.findall(pattern,new,re.S),p.name
        if old!=new:captionchanged.append(p.name)
        tables.append(p.name)
    assert len(tables)==67 and len(list((ROOT/'manuscript/tables').glob('*.tex')))==68
    def expand(s):
        return re.sub(r'\\input\{([^}]+)\}',lambda x:expand((ROOT/'manuscript'/(x.group(1)+'.tex')).read_text()),s)
    blocks=re.findall(r'\\begin\{table\*?\}.*?\\end\{table\*?\}',expand(m),re.S)
    assert len(blocks)==80
    assert all(b.index(r'\caption')>b.index(r'\begin{tabular}') for b in blocks)
    abstract=m.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
    abstract_words=len(abstract.replace('~',' ').split());assert abstract_words<200
    pdf=fitz.open(ROOT/'manuscript/main.pdf');texts=[p.get_text() for p in pdf]
    conclusion=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t))
    limitations=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t))
    ending=next(i+1 for i,t in enumerate(texts) if 'Qualityandexecutionsavingsrequireseparateevidence' in re.sub(r'[^A-Za-z]','',t))
    assert conclusion<=ending<=8 and limitations>=ending
    assert '??' not in '\n'.join(texts) and not re.search(r'/(Users|home)/','\n'.join(texts))
    assert not pdf.metadata.get('author','')
    log=(ROOT/'manuscript/main.log').read_text(errors='replace');assert 'Overfull' not in log and 'undefined' not in log
    outside=[];collisions=[];fonts=set()
    for pi,p in enumerate(pdf):
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
            if f[0] not in fonts:assert f[2]!='Type3' and pdf.extract_font(f[0])[3];fonts.add(f[0])
    assert not outside,outside[:8]
    assert not collisions,collisions[:8]
    visual=OUT/'visual';visual.mkdir(exist_ok=True)
    inspect=list(range(1,10))+[i+1 for i,t in enumerate(texts) if 'Matched label-blind top-k control' in t or 'dense implementation' in t]
    for i in sorted(set(inspect)):pdf[i-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(visual/f'page-{i}.png')
    for n in ['main.tex','appendix.tex']:
        old=(OLD/'manuscript'/n).read_text();new=(ROOT/'manuscript'/n).read_text()
        (OUT/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before/'+n,tofile='after/'+n)))
    result={'status':'PASS_SCOPED_HTML_SOURCE_AND_PDF_CHECKS','technical_main_pages':ending,'limitations_start_page':limitations,
      'total_pdf_pages':len(pdf),'abstract_words':abstract_words,'frozen_entries_preserved':len(pre['frozen_hashes']),
      'protected_files_preserved':len(pre['protected_hashes']),'old_table_files':67,'old_tabular_bodies_byte_preserved':True,
      'table_source_files':68,'tables':80,'captions_below_table':True,'caption_changed_files':captionchanged,
      'new_DP_displays':2,'main_displays_preserved':True,'formal_statement_math_preserved':True,'algorithm_preserved':True,
      'allowed_proof_repairs':['A.5 sT-b','M.4 exclusion quantifier and p>m endpoint'],
      'bibliography_keys_preserved':True,'verified_bibliography_metadata_added':['fermanian2025transductive:volume38, DOI'],
      'citation_key_integrity':True,'complete_citation_support_audit':False,
      'overfull_boxes':0,'undefined_references':0,'outside_horizontal_margins':0,'line_number_collisions':0,'embedded_fonts':True,
      'rendered_for_inspection':sorted(set(inspect)),'human_proof_certified':False,'full_novelty_certified':False,
      'complete_redistribution_authorized':False,'uploaded_or_submitted':False}
    bound=['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','manuscript/references.bib']
    bound += [str(p.relative_to(ROOT)) for p in (ROOT/'manuscript/tables').glob('*.tex')]
    result['artifact_hashes']={n:sha(ROOT/n) for n in sorted(bound)}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

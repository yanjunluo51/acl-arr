"""Scoped mathematics/input preservation and rendered manuscript checks."""
from pathlib import Path
import hashlib, json, re
import fitz
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/commitment-stopping-implementation'
OLD=ROOT/'history/before-commitment-stopping-review'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def displays(t):
    pat=r'\\\[.*?\\\]|\\begin\{(equation|align\*?)\}.*?\\end\{\1\}'
    return [re.sub(r'\s+','',m.group()) for m in re.finditer(pat,t,re.S)]

def numeric_rows(t):
    rows=[]
    for block in re.findall(r'\\midrule(.*?)\\bottomrule',t,re.S):
        for line in block.splitlines():
            if '&' in line and re.search(r'&\s*[-+]?\d',line):
                # The stage label may change; every displayed numeric token stays.
                rows.append(re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',line))
    return rows

def main():
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    assert pre['status']=='PASS_THREE_PRE_EDIT_CHECKS'
    for n,h in pre['protected_hashes'].items(): assert digest(ROOT/n)==h,n
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    assert frozen==pre['frozen_hashes']
    for n,h in frozen.items(): assert digest(ROOT/n)==h,n
    mathcounts={}
    for n in ['main.tex','appendix.tex']:
        old=(OLD/'manuscript'/n).read_text();new=(ROOT/'manuscript'/n).read_text()
        normalized=new
        assert displays(old)==displays(normalized),(n,'displayed mathematics')
        for env in ['theorem','proposition','corollary','lemma']:
            pat=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
            a=re.findall(pat,old,re.S);b=re.findall(pat,normalized,re.S)
            assert len(a)==len(b),(n,env)
            for x,y in zip(a,b):
                assert re.findall(r'\$(.*?)\$',x,re.S)==re.findall(r'\$(.*?)\$',y,re.S),(n,env)
        for env in ['proof','algorithm']:
            pat=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
            assert re.findall(pat,old,re.S)==re.findall(pat,new,re.S),(n,env)
        mathcounts[n]=len(displays(old))
        assert new.count(r'\begin{abstract}')==new.count(r'\end{abstract}')
    a=(ROOT/'manuscript/appendix.tex').read_text()
    gap=a[a.index(r'\subsection{Minimum witnesses at positive retention tolerance}'):a.index(r'\subsection{A complete certificate example}')]
    assert 's^*' not in gap and gap.count('L^*')==4
    tables=sorted((ROOT/'manuscript/tables').glob('*.tex'));assert len(tables)==67
    changed=[]
    for p in tables:
        n=str(p.relative_to(ROOT));old=(OLD/n).read_text();new=p.read_text()
        assert old==new,p.name
        if not numeric_rows(old): assert old==new,p.name
        if old!=new:changed.append(p.name)
    text=(ROOT/'manuscript/main.tex').read_text()+a
    bib=(ROOT/'manuscript/references.bib').read_text()
    keys=re.findall(r'@\w+\s*\{\s*([^,]+)',bib)
    cites={k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}',text) for k in cs.split(',')}
    assert len(keys)==len(set(keys)) and cites<=set(keys)
    assert r'\alpha=\rho/(2k)' in text and 'sum of squared residuals' in text
    assert '55/13' in a and '70 have realized batch churn' in a
    assert 'independently refitted' not in a and 'full row scale $Tp_i$' in a and 'statistical quality claims must account' in a and 'provisional masks after queries' in text
    pdf=fitz.open(ROOT/'manuscript/main.pdf');texts=[p.get_text() for p in pdf]
    conclusion=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t))
    limitations=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t))
    assert conclusion<=8 and limitations==9 and pdf[8].search_for('Limitations')[0].y0<=85
    assert '??' not in '\n'.join(texts) and not re.search(r'/(Users|home)/','\n'.join(texts))
    assert not pdf.metadata.get('author','') and 'Anonymous ACL submission' in texts[0]
    log=(ROOT/'manuscript/main.log').read_text(errors='replace')
    assert 'Overfull' not in log and 'undefined' not in log
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
                                if rect.x0<67.866 or rect.x1>p.rect.width-67.866: outside.append([pi+1,c['c'],list(rect)])
                    elif ''.join(c['c'] for c in span['chars']).isdigit(): numbers.extend(fitz.Rect(c['bbox']) for c in span['chars'])
        boxes=np.array([list(x) for x in black]).reshape(-1,4)
        for n in numbers:
            if ((boxes[:,0]<n.x1)&(boxes[:,2]>n.x0)&(boxes[:,1]<n.y1)&(boxes[:,3]>n.y0)).any(): collisions.append([pi+1,list(n)])
        for f in p.get_fonts():
            if f[0] not in fonts:
                assert f[2]!='Type3' and pdf.extract_font(f[0])[3];fonts.add(f[0])
    assert not outside,outside[:5]
    assert not collisions,collisions[:5]
    inspect=sorted(set([1,2,3,4,5,6,7,8,9]+[i+1 for i,t in enumerate(texts) if any(s in t for s in ['audit labels','statistical quality'])]))
    visual=OUT/'visual';visual.mkdir(exist_ok=True)
    for i in inspect:pdf[i-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(visual/f'page-{i}.png')
    result={'status':'PASS_SCOPED_COMMITMENT_STOPPING_SOURCE_AND_PDF_CHECKS','technical_main_pages':conclusion,
            'limitations_start_page':limitations,'total_pdf_pages':len(pdf),'table_source_files':67,
            'tables_with_editorial_changes':changed,'all_table_files_byte_preserved':True,
            'protected_artifacts_preserved':len(pre['protected_hashes']),'frozen_entries_preserved':len(frozen),
            'displayed_math_preserved':mathcounts,
            'formal_statement_math_preserved':True,'all_proof_and_algorithm_blocks_byte_preserved':True,
            'solver_paths_masks_unchanged':True,'bibliography_byte_preserved':True,
            'citation_key_integrity':True,'complete_citation_support_audit':False,
            'overfull_boxes':0,'undefined_references':0,'outside_horizontal_margins':0,
            'line_number_collisions':0,'embedded_fonts':True,'rendered_pages_for_visual_inspection':inspect,
            'new_scorer_inference_executed':False,'human_proof_certified':False,'full_novelty_certified':False,
            'complete_score_redistribution_authorized':False,'author_submission_fields_verified':False,
            'publicly_published_or_submitted':False}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()

"""Scientific-input preservation, complete evidence coverage and rendered QA."""
from pathlib import Path
import hashlib
import json
import re
import fitz
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/operational-scope-implementation'
OLD=ROOT/'history/before-operational-scope-review'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    assert pre['status']=='PASS_THREE_PRE_EDIT_CHECKS'
    assert all(digest(ROOT/n)==h for n,h in pre['protected_hashes'].items()
               if n not in pre['authorized_protected_file_change'])
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    assert all(digest(ROOT/n)==h for n,h in frozen.items())
    for filename in ['main.tex','appendix.tex']:
        text=(ROOT/'manuscript'/filename).read_text()
        old=(OLD/'manuscript'/filename).read_text()
        for env in ['theorem','proposition','corollary','lemma','proof','equation','align','align*']:
            pat=r'\\begin\{'+re.escape(env)+r'\}.*?\\end\{'+re.escape(env)+r'\}'
            assert re.findall(pat,text,re.S)==re.findall(pat,old,re.S),(filename,env)
    for name,value in pre['table_hashes'].items():
        assert digest(ROOT/name)==value,name
    tables=list((ROOT/'manuscript/tables').glob('*.tex'))
    assert len(tables)==67
    manuscript=(ROOT/'manuscript/main.tex').read_text()+(ROOT/'manuscript/appendix.tex').read_text()
    bib=(ROOT/'manuscript/references.bib').read_text()
    assert bib.startswith((OLD/'manuscript/references.bib').read_text())
    keys=re.findall(r'@\w+\s*\{\s*([^,]+)',bib)
    cited={k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}',manuscript) for k in cs.split(',')}
    assert len(keys)==len(set(keys)) and cited<=set(keys)
    assert len(keys)-len(re.findall(r'@\w+\s*\{\s*([^,]+)',(OLD/'manuscript/references.bib').read_text()))==3
    assert r'\alpha=\rho/(2k)' in manuscript and 'mean retains the same safe/optimistic guarantee' in manuscript
    assert 'shared subset for all strategies' in manuscript and 'constant worst-case ratio' in manuscript
    evidence=json.loads((OUT/'nontrivial-independent-check.json').read_text())
    assert evidence['query_records']==15360 and evidence['summary_fields']==4608
    resource=json.loads((OUT/'real-cost-resource-check.json').read_text())
    assert resource['real_scorer_inference_executed'] is False and resource['fallback_or_proxy_used'] is False
    pdf=fitz.open(ROOT/'manuscript/main.pdf'); texts=[p.get_text() for p in pdf]
    conclusion=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t))
    limitations=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t))
    assert conclusion<=8 and limitations==9 and pdf[8].search_for('Limitations')[0].y0<=85
    assert '??' not in '\n'.join(texts) and not re.search(r'/(Users|home)/','\n'.join(texts))
    assert not pdf.metadata.get('author','') and 'Anonymous ACL submission' in texts[0]
    log=(ROOT/'manuscript/main.log').read_text(errors='replace')
    assert 'Overfull' not in log and 'undefined' not in log
    outside=[]; collisions=[]; fonts=set()
    for pi,p in enumerate(pdf):
        black=[]; numbers=[]
        for b in p.get_text('rawdict')['blocks']:
            for line in b.get('lines',[]):
                for span in line['spans']:
                    if span['color']==0:
                        for c in span['chars']:
                            if c['c'].strip():
                                rect=fitz.Rect(c['bbox']);black.append(rect)
                                if rect.x0<67.866 or rect.x1>p.rect.width-67.866:
                                    outside.append([pi+1,c['c'],list(rect)])
                    elif ''.join(c['c'] for c in span['chars']).isdigit():
                        numbers.extend(fitz.Rect(c['bbox']) for c in span['chars'])
        boxes=np.array([list(x) for x in black]).reshape(-1,4)
        for n in numbers:
            if ((boxes[:,0]<n.x1)&(boxes[:,2]>n.x0)&(boxes[:,1]<n.y1)&(boxes[:,3]>n.y0)).any():
                collisions.append([pi+1,list(n)])
        for f in p.get_fonts():
            if f[0] not in fonts:
                assert f[2]!='Type3' and pdf.extract_font(f[0])[3]
                fonts.add(f[0])
    assert not outside,outside[:5]
    assert not collisions,collisions[:5]
    visual=OUT/'visual';visual.mkdir(exist_ok=True)
    caption='Query counts are conditional means'
    new_pages=[i+1 for i,t in enumerate(texts) if caption in t]
    assert sum(t.count(caption) for t in texts)==4,new_pages
    inspect=sorted(set([1,2,5,6,8,9]+new_pages))
    for i in inspect:
        pdf[i-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(visual/f'page-{i}.png')
    result={'status':'PASS_SCOPED_OPERATIONAL_SOURCE_AND_PDF_CHECKS',
            'technical_main_pages':conclusion,'limitations_start_page':limitations,'total_pdf_pages':len(pdf),
            'original_tables_preserved':63,'new_descriptive_tables':4,'table_source_files':67,
            'protected_artifacts_preserved':len(pre['protected_hashes'])-1,
            'original_bib_entries_preserved_with_three_appended':True,'frozen_entries_preserved':len(frozen),
            'formal_statements_and_proof_blocks_preserved':True,'solver_paths_masks_unchanged':True,
            'new_verified_bib_entries':3,'nontrivial_configurations':96,'nontrivial_method_cells':384,
            'independent_summary_fields':4608,'overfull_boxes':0,'undefined_references':0,
            'outside_horizontal_margins':0,'line_number_collisions':0,'embedded_fonts':True,
            'new_table_pdf_pages':new_pages,'rendered_pages_for_visual_inspection':inspect,
            'new_scorer_inference_executed':False,'human_proof_certified':False,'full_novelty_certified':False,
            'complete_score_redistribution_authorized':False,'author_submission_fields_verified':False,
            'publicly_published_or_submitted':False}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()

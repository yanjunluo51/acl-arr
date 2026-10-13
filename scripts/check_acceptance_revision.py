"""Current evidence, protected-input, manuscript and rendered-PDF checks."""
from pathlib import Path
import hashlib, json, re
import fitz
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/acceptance-review-implementation'
OLD=ROOT/'history/before-acceptance-review'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n): return json.loads((OUT/n).read_text())

def main():
    protected=read('protected-inputs.json')
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    mismatches=[n for n,h in protected.items() if digest(ROOT/n)!=h]
    assert mismatches==['manuscript/references.bib'],mismatches
    # A new verified citation is an authorized append to the bibliography;
    # frozen score/path inputs and every old bibliography byte remain intact.
    assert (ROOT/'manuscript/references.bib').read_bytes().startswith((OLD/'manuscript/references.bib').read_bytes())
    assert all(digest(ROOT/n)==h for n,h in frozen.items())
    oldtables=list((OLD/'manuscript/tables').glob('*.tex'))
    assert len(oldtables)==60
    assert all(p.read_bytes()==(ROOT/'manuscript/tables'/p.name).read_bytes() for p in oldtables)
    assert len(list((ROOT/'manuscript/tables').glob('*.tex')))==63
    q=read('wmt23-quality-independent.json')
    assert q['status']=='PASS_INDEPENDENT_RAW_MQM_AND_FIXED_MASK_CHECKS'
    assert (q['query_records_recomputed'],q['baseline_records_recomputed'],q['summary_values_recomputed'])==(5120,1280,1440)
    costs=read('cost-execution.json');theory=read('residual-theory-check.json')
    assert costs['status']=='PASS_COMPLETE_COST_SENSITIVITY_AND_CHEAPER_SUBSET_AUDIT'
    assert (costs['instances'],costs['records'],costs['original_stops_verified'])==(960,5760,5760)
    assert theory['status']=='PASS_INDEPENDENT_RESIDUAL_AND_MIXED_ACTION_ENUMERATION'
    assert (theory['exhaustive_residual_checks'],theory['larger_random_residual_checks'],theory['mixed_action_comparisons'])==(200704,800,4032)
    oldcount=json.loads((ROOT/'ccfa-review-reports/five-followup-20261003/evidence-check.json').read_text())
    assert oldcount['table_total']==oldcount['exact_rational_comparison_total']==70
    main=(ROOT/'manuscript/main.tex').read_text();app=(ROOT/'manuscript/appendix.tex').read_text()
    before=(OLD/'manuscript/main.tex').read_text()
    for env in ['theorem','proposition','equation','align']:
        pattern=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
        assert re.findall(pattern,main,re.S)==re.findall(pattern,before,re.S),env
    assert app.split('\\section{Reproducible Experimental Specification}')[0]==(OLD/'manuscript/appendix.tex').read_text().split('\\section{Reproducible Experimental Specification}')[0]
    keys=re.findall(r'@\w+\s*\{\s*([^,]+)',(ROOT/'manuscript/references.bib').read_text())
    assert len(keys)==len(set(keys))
    cited={k.strip() for body in re.findall(r'\\cite\w*\{([^}]+)\}',main+app) for k in body.split(',')}
    assert cited<=set(keys)
    assert 'Q_\\varepsilon(\\mathcal O_A)' in main
    assert 'mean' in main and 'sharp for both pooling rules' in main
    assert 'same monotone-cost argument' in app and 'restricted full-information optimum' in app
    assert 'not measured scoring times or fees' in (ROOT/'manuscript/tables/column-cost-exact.tex').read_text()
    assert '28.3' in app and '77.3' in app
    doc=fitz.open(ROOT/'manuscript/main.pdf');texts=[p.get_text() for p in doc]
    whole='\n'.join(texts)
    assert '??' not in whole and not re.search(r'/(?:Users|home)/[^/\s]+',whole)
    assert doc.metadata.get('author','')=='' and 'Anonymous ACL submission' in texts[0]
    limits=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t))
    conclusion=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t))
    assert conclusion<=8 and limits<=9,(conclusion,limits)
    log=(ROOT/'manuscript/main.log').read_text(errors='replace')
    assert 'Overfull' not in log and 'undefined' not in log
    outside=[];collisions=[];checked_fonts=set()
    for pi,p in enumerate(doc):
        black=[];numbers=[]
        for block in p.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    chars=span['chars']
                    if span['color']==0:
                        for c in chars:
                            if c['c'].strip():
                                rect=fitz.Rect(c['bbox']);black.append(rect)
                                if rect.x0<70.866-3 or rect.x1>p.rect.width-70.866+3: outside.append([pi+1,c['c'],list(rect)])
                    elif ''.join(c['c'] for c in chars).isdigit():numbers.extend(fitz.Rect(c['bbox']) for c in chars)
        rectangles=np.array([list(c) for c in black]).reshape(-1,4)
        for n in numbers:
            overlap=(rectangles[:,0]<n.x1)&(rectangles[:,2]>n.x0)&(rectangles[:,1]<n.y1)&(rectangles[:,3]>n.y0)
            if overlap.any():collisions.append([pi+1,list(n)])
        for f in p.get_fonts():
            if f[0] not in checked_fonts:
                assert f[2]!='Type3' and len(doc.extract_font(f[0])[3])>0
                checked_fonts.add(f[0])
    assert not outside,outside[:8]
    assert not collisions,collisions[:8]
    result={'status':'PASS_SCOPED_ACCEPTANCE_REVISION_SOURCE_AND_PDF_CHECKS',
            'total_pdf_pages':len(doc),'technical_main_pages':conclusion,'limitations_start_page':limits,
            'original_60_table_files_byte_identical':True,'new_tables':3,
            'protected_artifacts_byte_preserved':len(protected)-1,'old_bibliography_bytes_preserved_as_prefix':True,
            'authorized_bibliography_append':True,'frozen_manifest_entries_preserved':len(frozen),
            'original_main_formal_statements_preserved':True,'original_appendix_proofs_preserved':True,
            'citation_keys_defined_and_unique':True,
            'original_overbudget_count':70,'font_embedding':True,'overfull_boxes':0,
            'undefined_references':0,'line_number_collisions':0,'outside_horizontal_margins':0,
            'full_novelty_certified':False,'human_proof_certified':False,
            'real_scoring_cost_experiment_executed':False,'complete_score_redistribution_authorized':False,
            'scope':'Source/record consistency and geometry checks; excludes general scientific certification and submission authority.'}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()

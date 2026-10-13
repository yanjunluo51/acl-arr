"""Current revision source, result, input-preservation and PDF checks."""
from pathlib import Path
import hashlib
import json
import re

import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/sentence-review-implementation'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    protected=json.loads((OUT/'protected-inputs.json').read_text())
    assert all(digest(ROOT/n)==h for n,h in protected.items())
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    assert all(digest(ROOT/n)==h for n,h in frozen.items())
    old=ROOT/'history/before-sentence-review-implementation/manuscript/tables'
    count=0
    for p in old.glob('*.tex'):
        oldbody=re.findall(r'\\midrule(.*?)\\bottomrule',p.read_text(),re.S)
        newbody=re.findall(r'\\midrule(.*?)\\bottomrule',(ROOT/'manuscript/tables'/p.name).read_text(),re.S)
        assert oldbody==newbody,p.name
        count+=1
    doc=fitz.open(ROOT/'manuscript/main.pdf')
    text=[p.get_text() for p in doc];whole='\n'.join(text)
    assert '??' not in whole
    assert doc.metadata.get('author','')==''
    assert 'Anonymous ACL submission' in text[0]
    assert re.search(r'/(?:Users|home)/[^/\s]+',whole) is None
    limits=next(i+1 for i,t in enumerate(text) if re.search(r'(^|\n)Limitations\n',t))
    assert limits<=8,limits
    log=(ROOT/'manuscript/main.log').read_text(errors='replace')
    assert 'Overfull' not in log and 'undefined' not in log
    outside=[];collisions=[]
    for page_i,p in enumerate(doc):
        black=[];numbers=[]
        for block in p.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    chars=span['chars']
                    if span['color']==0:
                        for c in chars:
                            if c['c'].strip():
                                rect=fitz.Rect(c['bbox']);black.append(rect)
                                if rect.x0<70.866-3 or rect.x1>p.rect.width-70.866+3:
                                    outside.append([page_i+1,c['c'],list(rect)])
                    elif ''.join(c['c'] for c in chars).isdigit():
                        numbers.extend(fitz.Rect(c['bbox']) for c in chars)
        for n in numbers:
            if any(n.intersects(c) for c in black):collisions.append([page_i+1,list(n)])
        for font in p.get_fonts():
            assert font[2]!='Type3' and len(doc.extract_font(font[0])[3])>0
    assert not outside,outside[:5]
    assert not collisions,collisions[:5]
    experiment=json.loads((ROOT/'outputs/tolerance-sensitivity/execution.json').read_text())
    independent=json.loads((ROOT/'outputs/tolerance-sensitivity/independent-check.json').read_text())
    assert experiment['status']=='PASS_FULL_FIXED_PATH_SENSITIVITY'
    assert independent['status']=='PASS_INDEPENDENT_SORTED_COST_STOPPING_AND_MASK_CHECKS'
    result={'status':'PASS_SCOPED_REVISION_SOURCE_AND_PDF_CHECKS','total_pdf_pages':len(doc),
            'technical_main_pages':8,'limitations_start_page':limits,
            'old_scientific_files_preserved':len(protected),'frozen_manifest_entries_preserved':len(frozen),
            'numeric_table_bodies_preserved':count,
            'font_embedding':True,'overfull_boxes':0,'undefined_references':0,
            'line_number_collisions':0,'outside_horizontal_margins':0,
            'original_2pct_and_exact_masks_preserved':True,
            'stopping_records_independently_checked':independent['stopping_masks_checked'],
            'full_novelty_certified':False,'human_proof_certified':False,
            'full_score_redistribution_authorized':False,'author_fields_verified':False,
            'scope':'Current artifacts and fixed-path results; general proof validity also needs external review.'}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

"""Current revision source, result, input-preservation and PDF checks."""
from pathlib import Path
import hashlib
import json
import re

import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/three-local-clarifications-implementation'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    protected=json.loads((OUT/'protected-inputs.json').read_text())
    assert all(digest(ROOT/n)==h for n,h in protected.items())
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    assert all(digest(ROOT/n)==h for n,h in frozen.items())
    old=ROOT/'history/before-three-local-clarifications/manuscript/tables'
    count=0;changed_captions=[]
    baseline=json.loads((OUT/'table-baseline.json').read_text())
    for p in old.glob('*.tex'):
        current=ROOT/'manuscript/tables'/p.name
        tabular='\n'.join(re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',current.read_text(),re.S))
        assert hashlib.sha256(tabular.encode()).hexdigest()==baseline[p.name]['tabular_sha256'],p.name
        if p.read_bytes()!=current.read_bytes():changed_captions.append(p.name)
        count+=1
    assert count==60 and len(changed_captions)==1
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
    mechanism=json.loads((ROOT/'outputs/acquisition-mechanisms/execution.json').read_text())
    metrics=json.loads((ROOT/'outputs/acquisition-mechanisms/independent-check.json').read_text())
    assert mechanism['status']=='PASS_FULL_FROZEN_PATH_MECHANISM_DIAGNOSTICS'
    assert metrics['status']=='PASS_INDEPENDENT_METRIC_AND_SUMMARY_CHECKS'
    assert len(list((ROOT/'manuscript/tables').glob('*.tex')))==60
    experiment=json.loads((ROOT/'outputs/tolerance-sensitivity/execution.json').read_text())
    independent=json.loads((ROOT/'outputs/tolerance-sensitivity/independent-check.json').read_text())
    assert experiment['status']=='PASS_FULL_FIXED_PATH_SENSITIVITY'
    assert independent['status']=='PASS_INDEPENDENT_SORTED_COST_STOPPING_AND_MASK_CHECKS'
    result={'status':'PASS_SCOPED_REVISION_SOURCE_AND_PDF_CHECKS','total_pdf_pages':len(doc),
            'technical_main_pages':8,'limitations_start_page':limits,
            'protected_artifacts_preserved':len(protected),'frozen_manifest_entries_preserved':len(frozen),
            'numeric_table_bodies_preserved':count,'caption_files_updated':len(changed_captions),'acquisition_paths':mechanism['paths'],'diagnostic_stop_states':mechanism['saved_stop_states_checked'],
            'font_embedding':True,'overfull_boxes':0,'undefined_references':0,
            'line_number_collisions':0,'outside_horizontal_margins':0,
            'original_2pct_and_exact_masks_preserved':True,
            'prior_stopping_records_check_preserved_by_hash':independent['stopping_masks_checked'],
            'full_novelty_certified':False,'human_proof_certified':False,
            'full_score_redistribution_authorized':False,'author_fields_verified':False,
            'scope':'Reviewed definition, claim, caption and exposition revision. All 60 numeric tables, frozen paths, masks and scientific inputs preserved. No new experiment or inference; no external certification.'}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

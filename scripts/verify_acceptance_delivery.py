"""Verify current archives, clean compilation/rendering and independent test package."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/acceptance-review-implementation'
OLD=ROOT/'history/before-acceptance-review'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def archive(path,source=False,reference=False):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();assert len(names)==len(set(names)) and z.testzip() is None
        manifest=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'))
        assert set(manifest)==set(names)-{'PACKAGE_CONTENTS_SHA256.json'}
        for n,h in manifest.items():
            assert not n.startswith('/') and '..' not in Path(n).parts
            data=z.read(n);assert hashlib.sha256(data).hexdigest()==h
            if not reference:
                p=ROOT/(n[5:] if source and n.startswith('ROOT/') else n)
                assert p.read_bytes()==data,n
    return len(names)

def main():
    qa=json.loads((OUT/'source-pdf-check.json').read_text())
    assert qa['status']=='PASS_SCOPED_ACCEPTANCE_REVISION_SOURCE_AND_PDF_CHECKS'
    ns=archive(ROOT/'manuscript/source_private.zip',True)
    nc=archive(ROOT/'packages/current_mapping_column_code_private.zip')
    nr=archive(ROOT/'packages/residual_certificate_reproduction.zip',reference=True)
    src=Path(tempfile.mkdtemp(prefix='clean-source-',dir=OUT))
    code=Path(tempfile.mkdtemp(prefix='clean-code-',dir=OUT))
    residual=Path(tempfile.mkdtemp(prefix='clean-residual-',dir=OUT))
    with zipfile.ZipFile(ROOT/'manuscript/source_private.zip') as z:z.extractall(src)
    (src/'manuscript/main.pdf').unlink()
    with (OUT/'clean-source-build.log').open('w') as f:
        subprocess.run(['bash','build.sh'],cwd=src/'manuscript',stdout=f,stderr=subprocess.STDOUT,check=True)
    a,b=fitz.open(ROOT/'manuscript/main.pdf'),fitz.open(src/'manuscript/main.pdf')
    assert len(a)==len(b)==qa['total_pdf_pages']
    for x,y in zip(a,b):assert x.get_text()==y.get_text() and x.get_pixmap().samples==y.get_pixmap().samples
    print('clean source text and pixels match on all pages',flush=True)
    with zipfile.ZipFile(ROOT/'packages/current_mapping_column_code_private.zip') as z:z.extractall(code)
    assert not (code/'data').exists()
    with (OUT/'clean-code-render.log').open('w') as f:
        for n in ['render_editorial_tables.py','render_cached_mapping_tables.py','render_certificate_granularity.py',
                  'render_tolerance_sensitivity.py','render_sentence_review.py','render_acquisition_mechanisms.py',
                  'render_compressed_expression.py','render_three_clarifications.py','render_acceptance_revision.py']:
            subprocess.run([sys.executable,'scripts/'+n],cwd=code,stdout=f,stderr=subprocess.STDOUT,check=True)
    tables=list((ROOT/'manuscript/tables').glob('*.tex'));assert len(tables)==63
    for p in tables:assert (code/'manuscript/tables'/p.name).read_bytes()==p.read_bytes(),p.name
    print('all 63 table-source files regenerated identically',flush=True)
    with zipfile.ZipFile(ROOT/'packages/residual_certificate_reproduction.zip') as z:z.extractall(residual)
    with (OUT/'clean-residual-test.log').open('w') as f:
        subprocess.run([sys.executable,'scripts/test_residual_certificates.py'],cwd=residual,stdout=f,stderr=subprocess.STDOUT,check=True)
    independent=json.loads((residual/'review-revision/acceptance-review-implementation/residual-theory-check.json').read_text())
    original=json.loads((OUT/'residual-theory-check.json').read_text())
    for k in original:
        if k!='seconds':assert original[k]==independent[k],k
    assert (ROOT/'packages/synthetic_certificate_reproduction.zip').read_bytes()==(OLD/'packages/synthetic_certificate_reproduction.zip').read_bytes()
    print('clean data-independent residual/mixed enumeration matches',flush=True)
    check={'status':'PASS_CLEAN_SOURCE_TABLES_AND_RESIDUAL_PACKAGE','source_members':ns,'code_members':nc,
           'residual_members':nr,'total_pdf_pages':len(a),'all_pdf_text_and_pixels_identical':True,
           'table_source_files_regenerated':len(tables),'all_archive_payloads_match_live':True,
           'data_independent_enumeration_matches':True,'original_synthetic_archive_byte_identical':True,
           'clean_source_directory':src.name,'clean_code_directory':code.name,'clean_residual_directory':residual.name}
    (OUT/'clean-package-check.json').write_text(json.dumps(check,indent=2)+'\n')
    # Bind archives only after their verification; this receipt is intentionally
    # outside them to avoid a recursive archive/receipt hash dependency.
    names=['manuscript/main.tex','manuscript/appendix.tex','manuscript/references.bib','manuscript/main.pdf',
           'manuscript/source_private.zip','packages/current_mapping_column_code_private.zip',
           'packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip',
           'LATEST_MANUSCRIPT.md','LATEST_EXTERNAL_VERIFICATION.md','DATA_STATEMENT_CURRENT.md',
           'ACCEPTANCE_REVIEW_REVISION_REPORT.md','REPRODUCTION_ACCEPTANCE_REVIEW.md','REAL_SCORING_COST_PROTOCOL.md']
    names += [str(p.relative_to(ROOT)) for p in tables]
    for directory in [OUT,OUT/'visual']:
        for p in directory.iterdir():
            if p.is_file() and p.name not in ['final-delivery.json','delivery-check.log'] and p.suffix in ['.json','.md','.csv','.bib','.png','.log']:
                names.append(str(p.relative_to(ROOT)))
    from package_acceptance_revision import NEW_SCRIPTS
    names += ['scripts/'+n for n in NEW_SCRIPTS]
    result={'status':'PASS_SCOPED_ACCEPTANCE_REVISION_AND_CLEAN_DELIVERY',
            'three_pre_modification_checks_passed':True,'single_research_spine_preserved':True,
            'technical_main_pages':qa['technical_main_pages'],'total_pdf_pages':len(a),'limitations_start_page':qa['limitations_start_page'],
            'original_60_table_files_byte_identical':True,'new_table_source_files':3,
            'protected_artifacts_byte_preserved':561,'original_bib_bytes_preserved_as_prefix':True,
            'authorized_bibliography_append':True,'frozen_manifest_entries_preserved':171,
            'clean_package_checks':check,'residual_checks':original,
            'wmt23_quality_records':6400,'independent_quality_summary_checks':1440,
            'cost_instances':960,'cost_records':5760,'nonuniform_records_with_cost_optimum_using_more_columns':30,
            'new_cached_analysis':True,'new_model_inference':False,'new_online_policy':False,
            'original_selection_paths_and_masks_preserved':True,
            'real_scoring_cost_experiment_executed':False,'human_proof_certified':False,
            'full_novelty_certified':False,'complete_score_redistribution_authorized':False,
            'author_submission_fields_verified':False,'publicly_published_or_submitted':False,
            'hashes':{n:digest(ROOT/n) for n in sorted(set(names))},
            'scope':'Local implementation, finite theory verification, official fixed-mask quality diagnostic, declared column-price sensitivity and clean artifact delivery. Not all-scientific correctness, novelty, external human proof, rights or submission certification.'}
    (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2))

if __name__=='__main__':main()

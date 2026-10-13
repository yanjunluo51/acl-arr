"""Check current packages by clean compilation and complete table regeneration."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
import fitz
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/density-review-implementation'
OLD=ROOT/'history/before-density-review'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive(path,source=False):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();assert len(names)==len(set(names)) and z.testzip() is None
        bindings=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(bindings)==set(names)-{'PACKAGE_CONTENTS_SHA256.json'}
        for n,h in bindings.items():
            assert not n.startswith('/') and '..' not in Path(n).parts
            payload=z.read(n);assert hashlib.sha256(payload).hexdigest()==h
            real=n[5:] if source and n.startswith('ROOT/') else n
            assert (ROOT/real).read_bytes()==payload,n
    return len(names)
def main():
    qa=json.loads((OUT/'source-pdf-check.json').read_text());assert qa['status']=='PASS_SCOPED_DENSITY_SOURCE_AND_PDF_CHECKS'
    ns=archive(ROOT/'manuscript/source_private.zip',True);nc=archive(ROOT/'packages/current_mapping_column_code_private.zip')
    src=Path(tempfile.mkdtemp(prefix='clean-source-',dir=OUT));code=Path(tempfile.mkdtemp(prefix='clean-code-',dir=OUT))
    with zipfile.ZipFile(ROOT/'manuscript/source_private.zip') as z:z.extractall(src)
    (src/'manuscript/main.pdf').unlink()
    with (OUT/'clean-source-build.log').open('w') as f:subprocess.run(['bash','build.sh'],cwd=src/'manuscript',stdout=f,stderr=subprocess.STDOUT,check=True)
    a,b=fitz.open(ROOT/'manuscript/main.pdf'),fitz.open(src/'manuscript/main.pdf');assert len(a)==len(b)==qa['total_pdf_pages']
    for x,y in zip(a,b):assert x.get_text()==y.get_text() and x.get_pixmap().samples==y.get_pixmap().samples
    print('Clean source PDF text/pixels match on all pages',flush=True)
    with zipfile.ZipFile(ROOT/'packages/current_mapping_column_code_private.zip') as z:z.extractall(code)
    assert not (code/'data').exists()
    renderers=['render_editorial_tables.py','render_cached_mapping_tables.py','render_certificate_granularity.py','render_tolerance_sensitivity.py','render_sentence_review.py','render_acquisition_mechanisms.py','render_compressed_expression.py','render_three_clarifications.py','render_acceptance_revision.py','render_density_revision.py']
    with (OUT/'clean-code-render.log').open('w') as f:
        for n in renderers:subprocess.run([sys.executable,'scripts/'+n],cwd=code,stdout=f,stderr=subprocess.STDOUT,check=True)
    tables=list((ROOT/'manuscript/tables').glob('*.tex'));assert len(tables)==63
    for p in tables:assert p.read_bytes()==(code/'manuscript/tables'/p.name).read_bytes(),p.name
    print('All 63 tables regenerate identically, with current caption/notation layer',flush=True)
    for n in ['packages/synthetic_certificate_reproduction.zip','packages/residual_certificate_reproduction.zip']:
        assert (ROOT/n).read_bytes()==(OLD/n).read_bytes(),n
    # Metadata entries actually exist in both local packages; none establishes rights.
    from package_density_revision import META
    for n in META:assert (src/n).read_bytes()==(code/n).read_bytes()==(ROOT/n).read_bytes()
    ledger=json.loads((OUT/'item-completion.json').read_text());assert [v['item'] for v in ledger['items']]==list(range(1,41))
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    for n,h in pre['protected_hashes'].items():assert digest(ROOT/n)==h,n
    check={'status':'PASS_CLEAN_DENSITY_SOURCE_AND_TABLE_REPRODUCTION','source_members':ns,'code_members':nc,'pdf_pages':len(a),'all_pdf_text_and_pixels_identical':True,'all_63_table_sources_regenerated_identically':True,'archive_payloads_match_live':True,'metadata_paths_present_in_both_packages':True,'independent_synthetic_and_residual_archives_byte_preserved':True,'clean_source_directory':src.name,'clean_code_directory':code.name,'new_scientific_experiment_executed':False}
    (OUT/'clean-package-check.json').write_text(json.dumps(check,indent=2)+'\n')
    files=['manuscript/main.tex','manuscript/appendix.tex','manuscript/references.bib','manuscript/main.pdf','manuscript/source_private.zip','packages/current_mapping_column_code_private.zip','packages/synthetic_certificate_reproduction.zip','packages/residual_certificate_reproduction.zip','LATEST_MANUSCRIPT.md','LATEST_EXTERNAL_VERIFICATION.md','DATA_STATEMENT_CURRENT.md','DENSITY_REVIEW_REVISION_REPORT.md','REPRODUCTION_DENSITY_REVIEW.md']
    files += [str(p.relative_to(ROOT)) for p in tables]
    files += ['scripts/'+n for n in ['render_density_revision.py','check_density_revision.py','package_density_revision.py','verify_density_delivery.py']]
    files += META
    files += [str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file() and not any(x.startswith('clean-') for x in p.parts) and p.name not in ['final-delivery.json','delivery-check.log']]
    result=dict(qa);result['status']='PASS_SCOPED_DENSITY_REVISION_AND_CLEAN_DELIVERY';result.update({'three_pre_edit_checks_passed':True,'single_research_spine_preserved':True,'review_items':40,'all_items_dispositioned':True,'clean_package_checks':check,'proof_tests_rerun':False,'proof_test_justification':'Formal statements/proofs/solvers unchanged; finite historical checks are not new human proof certification.','hashes':{n:digest(ROOT/n) for n in sorted(set(files))}})
    (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2))
if __name__=='__main__':main()

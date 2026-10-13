"""Author-side current delivery audit with a clean, independently usable bundle."""
import hashlib,json,re,shutil,subprocess,sys,zipfile
from pathlib import Path
import fitz
from package_latest_sentence_revision import DOCS,NEW_SCRIPTS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/latest-sentence-review-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive(path,live=False,source=False):
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(manifest)==set(z.namelist())-{'PACKAGE_CONTENTS_SHA256.json'}
        for n,h in manifest.items():
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            assert hashlib.sha256(z.read(n)).hexdigest()==h,n
            if live:
                real=n[5:] if source and n.startswith('ROOT/') else n
                assert sha(ROOT/real)==h,n
        return len(manifest)+1

def main():
    qa=json.loads((OUT/'source-pdf-check.json').read_text());assert qa['status']=='PASS_SCOPED_SENTENCE_REVIEW_SOURCE_AND_PDF_CHECKS'
    for n,h in qa['artifact_hashes'].items():assert sha(ROOT/n)==h,n
    counts={}
    for n,live,source in [('manuscript/source_private.zip',True,True),('packages/current_mapping_column_code_private.zip',True,False),('packages/current_anonymous_source.zip',False,True),('packages/current_anonymous_code.zip',False,False)]:counts[n]=archive(ROOT/n,live,source)
    clean=OUT/'clean';assert not clean.exists(),'Do not overwrite prior clean delivery evidence';clean.mkdir();src=clean/'source';code=clean/'code'
    for n,d in [('packages/current_anonymous_source.zip',src),('packages/current_anonymous_code.zip',code)]:
        with zipfile.ZipFile(ROOT/n) as z:z.extractall(d)
        home=Path.home().name.encode().lower()
        for p in d.rglob('*'):
            if p.is_file():assert home not in p.read_bytes().lower(),str(p.relative_to(d))
    for flag,name in [([], 'portable'),(['--replay-tables','--verify-optima'],'tables-and-optima')]:
        with (OUT/('clean-'+name+'.json')).open('w') as receipt,(OUT/('clean-'+name+'.log')).open('w') as log:
            subprocess.run([sys.executable,'scripts/verify_latest_sentence_bundle.py']+flag,cwd=code,check=True,stdout=receipt,stderr=log)
        z=json.loads((OUT/('clean-'+name+'.json')).read_text());assert z['status']=='PASS_PORTABLE_SENTENCE_REVIEW_SAVED_EVIDENCE'
    for p in (ROOT/'manuscript/tables').glob('*.tex'):assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
    # Optional optimizer is read-only; every packaged member must still match.
    manifest=json.loads((code/'PACKAGE_CONTENTS_SHA256.json').read_text())
    for n,h in manifest.items():assert sha(code/n)==h,n
    with (OUT/'clean-build.log').open('w') as log:subprocess.run(['bash','build.sh'],cwd=src/'manuscript',check=True,stdout=log,stderr=subprocess.STDOUT)
    with fitz.open(ROOT/'manuscript/main.pdf') as current,fitz.open(src/'manuscript/main.pdf') as rebuilt:
        assert len(current)==len(rebuilt)==qa['total_pdf_pages']
        for a,b in zip(current,rebuilt):
            assert a.get_text()==b.get_text()
            assert a.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples==b.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    for field in ['frozen_hashes','protected_hashes','scientific_output_hashes']:
        for n,h in pre[field].items():assert sha(ROOT/n)==h,n
    older_pre=json.loads((ROOT/'review-revision/joint-certificate-implementation/pre-edit-checks.json').read_text())
    for n in ['packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']:assert sha(ROOT/n)==older_pre['prior_delivery_hashes'][n]
    ledger=json.loads((OUT/'item-completion.json').read_text());assert len(ledger['items'])==67 and len({x['id'] for x in ledger['items']})==67 and len(ledger['whole_section_alternatives'])==4
    ex=json.loads((ROOT/'outputs/query-mechanism-interventions/independent-check.json').read_text());assert ex['actual_replies_checked']==21632445
    small=json.loads((ROOT/'outputs/joint-certificates/panel-independent-check.json').read_text());assert small['joint_and_separated_minima_checked']==7680 and small['certified_unresolved_instances']==0
    # Verify the exact text claims from records, using unrounded values first.
    import csv,statistics
    rows=list(csv.DictReader((ROOT/'outputs/joint-certificates/panel_records.csv').open()))
    exact=[x for x in rows if x['aggregator']=='mean' and x['history']=='empty' and x['epsilon']=='0'];assert len(exact)==960
    assert sum(int(x['sharing_saving'])>0 for x in exact)==186 and sum(int(x['sharing_saving']) for x in exact)==306
    ints=list(csv.DictReader((ROOT/'outputs/query-mechanism-interventions/records.csv').open()))
    g=[x for x in ints if x['dataset']=='WMT23' and x['aggregator']=='mean' and float(x['q'])==.3 and x['stopping']=='primary' and x['method']=='oracle_row']
    assert statistics.fmean(int(x['queries']) for x in g)==2180.3 and statistics.fmean(int(x['delta_width']) for x in g)==379.7
    report=(ROOT/'JOINT_CERTIFICATE_REVISION_REPORT.md').read_text();assert '186' in report and '379.7' in report and '1800.6' in report
    files=list(qa['artifact_hashes'])+DOCS+['scripts/'+n for n in NEW_SCRIPTS]+list(counts)
    for directory in [ROOT/'outputs/joint-certificates',ROOT/'outputs/query-mechanism-interventions',OUT]:
        files += [str(p.relative_to(ROOT)) for p in directory.iterdir() if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.gz','.diff','.md'] and p.name!='final-delivery.json']
    check={'status':'PASS_CLEAN_CURRENT_SOURCE_AND_CODE_DELIVERY','archive_members':counts,'clean_pdf_text_and_pixels_identical':True,'portable_default_passed':True,'all_71_tables_regenerated_exactly':True,'independent_7680_optima_recomputed_from_clean_package':True,'clean_code_manifest_unchanged_after_optima_and_table_checks':True,'known_personal_path_marker_scan_clean':True,'general_anonymity_certified':False,'original_numerical_inputs_required_for_saved_checks':False,'original_full_runtime_or_scorer_execution_claim':False,'uploaded_or_submitted':False}
    (OUT/'clean-package-check.json').write_text(json.dumps(check,indent=2)+'\n');files.append(str((OUT/'clean-package-check.json').relative_to(ROOT)))
    result=dict(qa);result.pop('artifact_hashes');result.update({'status':'PASS_SCOPED_SENTENCE_REVIEW_AND_CLEAN_DELIVERY','three_pre_edit_checks':True,'review_items_dispositioned':67,'whole_section_alternatives_dispositioned':4,'single_research_spine_preserved':True,'joint_finite_cases':7484,'small_batch_configurations':1920,'joint_minima':7680,'independently_recomputed_minima':small,'full_batch_interventions':ex,'new_model_inference':False,'original_acquisition_paths_overwritten':False,'original_numerical_results_overwritten':False,'original_scientific_output_files_verified':len(pre['scientific_output_hashes']),'open_field_items':['A02 historical pool generation API','A03 external reviewer access and redistribution','A04 original BLAS and platform','A06 complete citation support and version audit'],'clean_package_check':check,'full_novelty_certified':False,'complete_citation_support_audit':False,'human_proof_certified':False,'complete_redistribution_authorized':False,'original_scorer_checkpoint_identities_all_verified':False,'author_submission_fields_verified':False,'uploaded_or_submitted':False,'hashes':{n:sha(ROOT/n) for n in sorted(set(files))}})
    (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2))
if __name__=='__main__':main()

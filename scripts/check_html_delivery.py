"""Clean extraction, table replay, compilation, acquisition and anonymous copies."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,tempfile,zipfile
import fitz
from verify_interface_delivery import RENDERERS
from package_html_revision import DOCS,NEW_SCRIPTS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/html-review-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive(path,live=False,source=False):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();assert len(names)==len(set(names)) and z.testzip() is None
        bindings=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'))
        assert set(bindings)==set(names)-{'PACKAGE_CONTENTS_SHA256.json'}
        for n,h in bindings.items():
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==h
            if live:
                real=n[5:] if source and n.startswith('ROOT/') else n
                assert (ROOT/real).read_bytes()==raw,n
            else:assert Path.home().name.encode().lower() not in raw.lower(),n
    return len(names)
def main():
    qa=json.loads((OUT/'source-pdf-check.json').read_text());assert qa['status']=='PASS_SCOPED_HTML_SOURCE_AND_PDF_CHECKS'
    for n,h in qa['artifact_hashes'].items():assert sha(ROOT/n)==h,n
    ledger=json.loads((OUT/'item-completion.json').read_text());assert len(ledger['items'])==144
    for r in ledger['items']:assert r['completion'] in ['IMPLEMENTED_IN_CONTINUOUS_REVISION','VALID_WORDING_RETAINED_OR_CONDENSED','EXISTING_CORRECT_SCOPE_REVERIFIED']
    sources=archive(ROOT/'manuscript/source_private.zip',True,True);codes=archive(ROOT/'packages/current_mapping_column_code_private.zip',True)
    anon_source=archive(ROOT/'packages/html_review_anonymous_source.zip');anon_code=archive(ROOT/'packages/html_review_anonymous_code.zip')
    clean=Path(tempfile.mkdtemp(prefix='clean-current-',dir=OUT));src=clean/'source';code=clean/'code';src.mkdir();code.mkdir()
    with zipfile.ZipFile(ROOT/'packages/html_review_anonymous_source.zip') as z:z.extractall(src)
    with zipfile.ZipFile(ROOT/'packages/html_review_anonymous_code.zip') as z:z.extractall(code)
    # Test the command documented for recipients, before rebuilding PDF bytes.
    with (OUT/'clean-portable-check.json').open('w') as log:
        subprocess.run([sys.executable,'scripts/verify_html_bundle.py'],cwd=code,
                       stdout=log,check=True)
    portable=json.loads((OUT/'clean-portable-check.json').read_text())
    assert portable['status']=='PASS_PORTABLE_SAVED_BUNDLE_INTEGRITY'
    with (OUT/'clean-build.log').open('w') as log:
        subprocess.run(['bash','build.sh'],cwd=src/'manuscript',stdout=log,stderr=subprocess.STDOUT,check=True)
    with fitz.open(ROOT/'manuscript/main.pdf') as live,fitz.open(src/'manuscript/main.pdf') as rebuilt:
        assert len(live)==len(rebuilt)==qa['total_pdf_pages']
        for a,b in zip(live,rebuilt):
            assert a.get_text()==b.get_text()
            assert a.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples==b.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples
    layers=RENDERERS+['render_nontrivial_certification.py','render_main10_editorial.py','render_html_revision.py']
    with (OUT/'clean-portable-tables-check.json').open('w') as receipt, (OUT/'clean-tables.log').open('w') as log:
        subprocess.run([sys.executable,'scripts/verify_html_bundle.py','--replay-tables'],
                       cwd=code,stdout=receipt,stderr=log,check=True)
    portable_tables=json.loads((OUT/'clean-portable-tables-check.json').read_text())
    assert portable_tables['tables_regenerated']==68 and portable_tables['render_layers']==len(layers)
    for p in (ROOT/'manuscript/tables').glob('*.tex'):assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
    # Verify the missing acquisition dependencies explicitly, then validate freshly
    # network-rebuilt inputs through the clean extracted script without downloading twice.
    models=json.loads((code/'evidence/source-model-files.json').read_text());manifest=json.loads((code/'MANIFEST_SHA256.json').read_text())
    assert len(models)==14 and len({x[0] for x in models})==14
    assert all(isinstance(x[1],str) and x[1].startswith('eval-set-scores/') for x in models)
    fresh=clean/'freshly-acquired';fresh.mkdir()
    for name in ['rb2_ranked_panel.json','wmt23_metric_panel.json']:
        raw=OUT/'fresh-acquisition'/name;assert sha(raw)==manifest['data/'+name]
        shutil.copy2(raw,fresh/name)
    with (OUT/'clean-acquisition-check.log').open('w') as log:
        subprocess.run([sys.executable,'scripts/fetch_inputs.py','--output-dir',str(fresh)],cwd=code,stdout=log,stderr=subprocess.STDOUT,check=True)
    external=json.loads((OUT/'fresh-wmt24-check.json').read_text())
    assert external['status']=='PASS_EXACT_WMT24_PANEL_AND_MQM_RECONSTRUCTION'
    assert len(external['six_panel_label_hashes'])==6
    for n,h in external['six_panel_label_hashes'].items():assert sha(OUT/'fresh-wmt24'/n)==h,n
    # Script and its metadata dependencies must be present in the anonymous bundle.
    for n in ['scripts/fetch_external_inputs.py','scripts/prepare_external_panel.py',
        'review-revision/external-admission.json','review-revision/external-panel-protocol.json',
        'review-revision/acquisition/official-hosting.json']:assert (code/n).is_file(),n
    dictionary=(ROOT/'RESULT_DATA_DICTIONARY.md').read_text();included=[];excluded=[]
    for n in re.findall(r'`([^`]+)`',dictionary):
        if '/' not in n or not n.endswith(('.json','.csv','.gz')) or ';' in n:continue
        assert (ROOT/n).is_file(),n
        if 'traces.jsonl.gz' in n:excluded.append(n);assert not (code/n).exists()
        else:included.append(n);assert (code/n).is_file(),n
    check={'status':'PASS_CLEAN_ANONYMOUS_SOURCE_AND_CODE_ENGINEERING','source_members':sources,'code_members':codes,
       'anonymous_source_members':anon_source,'anonymous_code_members':anon_code,'pdf_text_and_pixels_identical':True,
       'portable_code_bundle_check':portable,
       'portable_table_replay_check':portable_tables,
       'table_files_regenerated':68,'render_layers':len(layers),'clean_fetch_dependencies_verified':True,
       'fresh_network_inputs_exact':2,'clean_extracted_existing_input_validation':True,
       'WMT24_fresh_local_archive_reconstruction_exact':6,'WMT24_fresh_network_archive_download':False,
       'dictionary_summary_files_in_bundle':included,'raw_trace_paths_documented_and_excluded':excluded,
       'known_personal_path_marker_scan_clean':True,'general_anonymity_certified':False,'clean_directory':str(clean.relative_to(OUT)),
       'anonymous_packages_uploaded':False,'redistribution_authorized':False}
    (OUT/'clean-package-check.json').write_text(json.dumps(check,indent=2)+'\n')
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    for n,h in pre['protected_hashes'].items():assert sha(ROOT/n)==h,n
    for n,h in pre['frozen_hashes'].items():assert sha(ROOT/n)==h,n
    for n in ['packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']:
        assert sha(ROOT/n)==pre['prior_delivery_hashes'][n]
    files=['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','manuscript/references.bib',
       'manuscript/source_private.zip','packages/current_mapping_column_code_private.zip',
       'packages/html_review_anonymous_source.zip','packages/html_review_anonymous_code.zip',
       'packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']+DOCS
    files += ['scripts/'+n for n in NEW_SCRIPTS]
    files += [str(p.relative_to(ROOT)) for p in (ROOT/'manuscript/tables').glob('*.tex')]
    for folder in [OUT,ROOT/'outputs/matched-tie-control']:
        files += [str(p.relative_to(ROOT)) for p in folder.glob('*') if p.is_file() and p.suffix in ['.json','.csv','.diff','.md'] and p.name!='final-delivery.json']
    result=dict(qa);result.update({'status':'PASS_SCOPED_HTML_REVISION_AND_PAIRED_CONTROL_DELIVERY',
       'review_items_dispositioned':144,'review_disposition_counts':ledger['counts'],'three_pre_edit_checks_passed':True,
       'single_research_spine_preserved':True,'new_cached_score_control_configurations':1920,
       'matched_control_audit':json.loads((ROOT/'outputs/matched-tie-control/independent-check.json').read_text()),
       'clean_package_check':check,'new_model_inference_executed':False,'original_acquisition_paths_changed':False,
       'original_native_results_overwritten':False,'human_proof_certified':False,'full_novelty_certified':False,
       'complete_redistribution_authorized':False,'author_submission_fields_verified':False,'uploaded_or_submitted':False,
       'hashes':{n:sha(ROOT/n) for n in sorted(set(files))}})
    (OUT/'final-delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='hashes'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

"""Successor private packages and separately redacted anonymous copies."""
from pathlib import Path
import hashlib,json,zipfile
from package_certificate_granularity import write_zip
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'history/before-html-review-20261005';OUT=ROOT/'review-revision/html-review-implementation'
DOCS=['LATEST_MANUSCRIPT.md','DATA_STATEMENT_CURRENT.md','HTML_REVIEW_REVISION_REPORT.md','REPRODUCTION_HTML_REVIEW.md','RESULT_DATA_DICTIONARY.md','ACQUISITION_INDEX.md','HTML_REVIEW_SELFCHECK_REPORT.md','requirements-audit.txt']
NEW_SCRIPTS=['preflight_html_revision.py','run_matched_tie_control.py','check_matched_tie_control.py',
 'revise_html_review.py','complete_html_precision.py','integrate_matched_control.py','render_html_revision.py',
 'check_html_source.py','package_html_revision.py','check_html_delivery.py','fetch_external_inputs.py','verify_html_bundle.py']
def main():
    source={};code={}
    for path,dest,src in [(OLD/'manuscript/source_private.zip',source,True),(OLD/'packages/current_mapping_column_code_private.zip',code,False)]:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n=='PACKAGE_CONTENTS_SHA256.json':continue
                real=n[5:] if src and n.startswith('ROOT/') else n
                assert (ROOT/real).is_file(),n
                dest[n]=(ROOT/real,n)
    for n in DOCS:source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
    p=ROOT/'manuscript/tables/matched-tie-control.tex';source[str(p.relative_to(ROOT))]=(p,str(p.relative_to(ROOT)))
    for p,_ in source.values():
        n=str(p.relative_to(ROOT));code[n]=(p,n)
    for n in ['MANIFEST_SHA256.json','evidence/source-model-files.json',
       'review-revision/external-panel-protocol.json','review-revision/external-admission.json',
       'review-revision/acquisition/official-hosting.json',
       'review-revision/acceptance-review-implementation/wmt23-official-files.json']:
        code[n]=(ROOT/n,n)
    for n in NEW_SCRIPTS:code['scripts/'+n]=(ROOT/'scripts'/n,'scripts/'+n)
    # The result dictionary promises full aggregate records, not only the inputs
    # needed to regenerate printed tables. Include those records explicitly.
    for n in ['outputs/query_metrics.json','outputs/query_analysis.json',
        'outputs/review-budget/results.json','outputs/review-composition/results.json',
        'outputs/review-external/results.json']:
        code[n]=(ROOT/n,n)
    for directory in [ROOT/'outputs/matched-tie-control',OUT]:
        for p in directory.glob('*'):
            if p.is_file() and p.suffix in ['.json','.csv','.diff'] and p.name not in ['final-delivery.json','clean-package-check.json','package-build.json']:
                n=str(p.relative_to(ROOT));code[n]=(p,n)
    # No new raw score matrices, official text/labels or raw NLP traces.
    assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz') or '/wmt23-official/' in n for n in code)
    ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()))
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
    redactions={};identity=Path.home().name.encode().lower();home=str(Path.home()).encode()
    for current,target in [('manuscript/source_private.zip','packages/html_review_anonymous_source.zip'),
                          ('packages/current_mapping_column_code_private.zip','packages/html_review_anonymous_code.zip')]:
        with zipfile.ZipFile(ROOT/current) as z,zipfile.ZipFile(ROOT/target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
            bindings={};changed=[]
            for n in z.namelist():
                if n=='PACKAGE_CONTENTS_SHA256.json':continue
                raw=z.read(n)
                if home in raw:
                    raw=raw.replace(str(ROOT).encode(),b'<PROJECT_ROOT>').replace(home,b'<LOCAL_USER_HOME>');changed.append(n)
                assert identity not in raw.lower(),n
                out.writestr(n,raw);bindings[n]=hashlib.sha256(raw).hexdigest()
            out.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(bindings,indent=2)+'\n')
            redactions[target]=changed
    result={'status':'PREPARED_PRIVATE_AND_SEPARATE_PATH_ANONYMOUS_PACKAGES','source_members':ns+1,'code_members':nc+1,
        'anonymous_copy_redactions':redactions,'raw_score_matrices_added':False,'original_private_history_redacted':False,
        'uploaded_or_submitted':False,'complete_redistribution_authorized':False,'general_anonymity_certified':False}
    (OUT/'package-build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

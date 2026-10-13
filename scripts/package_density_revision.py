"""Update the canonical local source/code packages without third-party matrices."""
from pathlib import Path
import json,zipfile
from package_certificate_granularity import write_zip
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'history/before-density-review'
OUT=ROOT/'review-revision/density-review-implementation'
DOCS=['LATEST_MANUSCRIPT.md','LATEST_EXTERNAL_VERIFICATION.md','DATA_STATEMENT_CURRENT.md','DENSITY_REVIEW_REVISION_REPORT.md','REPRODUCTION_DENSITY_REVIEW.md']
SCRIPTS=['render_density_revision.py','check_density_revision.py','package_density_revision.py','verify_density_delivery.py']
META=['review-revision/acquisition/official-hosting.json','review-revision/external-admission.json','review-revision/external-source-audit.json']
def main():
    source={}
    with zipfile.ZipFile(OLD/'manuscript/source_private.zip') as z:
        for n in z.namelist():
            if n=='PACKAGE_CONTENTS_SHA256.json':continue
            p=ROOT/(n[5:] if n.startswith('ROOT/') else n);assert p.is_file(),n;source[n]=(p,n)
    for n in DOCS:source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
    for n in META:source[n]=(ROOT/n,n)
    code={}
    with zipfile.ZipFile(OLD/'packages/current_mapping_column_code_private.zip') as z:
        for n in z.namelist():
            if n=='PACKAGE_CONTENTS_SHA256.json':continue
            p=ROOT/n;assert p.is_file(),n;code[n]=(p,n)
    for p,n in source.values():
        real=str(p.relative_to(ROOT));code[real]=(p,real)
    for n in SCRIPTS:
        rel='scripts/'+n;code[rel]=(ROOT/rel,rel)
    for n in ['source-pdf-check.json','source-edit-log.json','main-prose-check.json','appendix-prose-check.json','item-completion.json','manuscript.diff']:
        rel=str((OUT/n).relative_to(ROOT));code[rel]=(ROOT/rel,rel)
    for n in ['REVIEW_ASSESSMENT.md','evidence-check.json','review_input.txt']:
        rel='ccfa-review-reports/density-review-adjudication/'+n;code[rel]=(ROOT/rel,rel)
    assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz') or n=='outputs/review-external/traces.jsonl.gz' or '/wmt23-official/' in n for n in code)
    ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()))
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
    print(json.dumps({'source_members':ns+1,'code_members':nc+1,'third_party_matrices_added':False}))
if __name__=='__main__':main()

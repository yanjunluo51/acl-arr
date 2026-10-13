"""Update current private source/code artifacts without adding raw NLP inputs."""
from pathlib import Path
import json
import zipfile
from package_certificate_granularity import write_zip

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'history/before-operational-scope-review'
OUT=ROOT/'review-revision/operational-scope-implementation'
DOCS=['LATEST_MANUSCRIPT.md','LATEST_EXTERNAL_VERIFICATION.md','DATA_STATEMENT_CURRENT.md',
      'OPERATIONAL_REVIEW_REVISION_REPORT.md','REPRODUCTION_OPERATIONAL_REVIEW.md',
      'REAL_SCORING_COST_EXECUTION.md']
SCRIPTS=['analyze_nontrivial_certification.py','render_nontrivial_certification.py',
         'check_nontrivial_certification.py','audit_real_scorer_resources.py',
         'check_operational_revision.py','package_operational_revision.py','verify_operational_delivery.py']


def main():
    source,code={},{}
    with zipfile.ZipFile(OLD/'manuscript/source_private.zip') as z:
        for n in z.namelist():
            if n=='PACKAGE_CONTENTS_SHA256.json':continue
            p=ROOT/(n[5:] if n.startswith('ROOT/') else n)
            assert p.is_file(),n
            source[n]=(p,n)
    for p in (ROOT/'manuscript/tables').glob('nontrivial-*.tex'):
        n=str(p.relative_to(ROOT));source[n]=(p,n)
    for n in DOCS:source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
    with zipfile.ZipFile(OLD/'packages/current_mapping_column_code_private.zip') as z:
        for n in z.namelist():
            if n=='PACKAGE_CONTENTS_SHA256.json':continue
            assert (ROOT/n).is_file(),n
            code[n]=(ROOT/n,n)
    for p,_ in source.values():
        n=str(p.relative_to(ROOT));code[n]=(p,n)
    for n in SCRIPTS:code['scripts/'+n]=(ROOT/'scripts'/n,'scripts/'+n)
    for p in (ROOT/'outputs/nontrivial-certification').glob('*'):
        n=str(p.relative_to(ROOT));code[n]=(p,n)
    for p in OUT.glob('*'):
        if p.is_file() and p.suffix in ['.json','.txt','.bib','.diff'] and p.name not in ['final-delivery.json','clean-package-check.json']:
            n=str(p.relative_to(ROOT));code[n]=(p,n)
    for n in ['REVIEW_ASSESSMENT.md','evidence-check.json']:
        p=ROOT/'ccfa-review-reports/operational-scope-review'/n
        real=str(p.relative_to(ROOT));code[real]=(p,real)
    assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz')
                   or n=='outputs/review-external/traces.jsonl.gz' or '/wmt23-official/' in n for n in code)
    ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()))
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
    print(json.dumps({'source_members':ns+1,'code_members':nc+1,'raw_third_party_matrices_added':False}))


if __name__=='__main__':main()

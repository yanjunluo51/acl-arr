"""Refresh current private source/code bundles without third-party score inputs."""
import json
from pathlib import Path
import zipfile
from package_certificate_granularity import write_zip

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/information-certification-implementation'
PREVIOUS=ROOT/'history/before-information-certification-implementation'


def main():
    source={}
    with zipfile.ZipFile(PREVIOUS/'manuscript/source_private.zip') as old:
        for name in old.namelist():
            if name.startswith('ROOT/'):
                p=ROOT/name[5:];assert p.is_file();source[name]=(p,name)
    for p in (ROOT/'manuscript').rglob('*'):
        if p.is_file() and p.suffix in ['.tex','.bib','.bst','.sty','.pdf','.png','.svg','.sh']:
            name=str(p.relative_to(ROOT));source[name]=(p,name)
    for n in ['INFORMATION_CERTIFICATION_REVISION_REPORT.md',
              'INFORMATION_CERTIFICATION_SELF_CHECK.md','REPRODUCTION_TOLERANCE_CERTIFICATES.md']:
        source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
    code={}
    with zipfile.ZipFile(PREVIOUS/'packages/current_mapping_column_code_private.zip') as old:
        for name in old.namelist():
            if name=='PACKAGE_CONTENTS_SHA256.json':continue
            p=ROOT/name;assert p.is_file(),name;code[name]=(p,name)
    for p,_ in source.values():
        name=str(p.relative_to(ROOT));code[name]=(p,name)
    for name in ['tolerance_certificates.py','test_tolerance_certificates.py',
                 'run_tolerance_sensitivity.py','audit_tolerance_sensitivity.py',
                 'render_tolerance_sensitivity.py','check_information_certification_revision.py',
                 'package_information_certification_revision.py']:
        p=ROOT/'scripts'/name;n=str(p.relative_to(ROOT));code[n]=(p,n)
    for p in (ROOT/'outputs/tolerance-sensitivity').iterdir():
        if p.is_file():n=str(p.relative_to(ROOT));code[n]=(p,n)
    for name in ['protocol.json','precheck-three-pass.json','source-pdf-check.json',
                 'protected-inputs.json','literature-context.md','theory-check.json','visual-check.json']:
        p=OUT/name;assert p.is_file();n=str(p.relative_to(ROOT));code[n]=(p,n)
    assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz') or
                   n=='outputs/review-external/traces.jsonl.gz' for n in code)
    ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()))
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
    assert (ROOT/'packages/synthetic_certificate_reproduction.zip').read_bytes()==(PREVIOUS/'packages/synthetic_certificate_reproduction.zip').read_bytes()
    print(json.dumps({'source_members':ns+1,'code_members':nc+1,'synthetic_byte_identical':True}))


if __name__=='__main__':main()

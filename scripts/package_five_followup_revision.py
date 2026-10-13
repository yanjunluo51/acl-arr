"""Synchronize current private source/code bundles for four definition edits."""
import json
from pathlib import Path
import zipfile
from package_certificate_granularity import write_zip

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/five-followup-implementation'
PREVIOUS=ROOT/'history/before-five-followup-implementation'
DOCS=['FIVE_FOLLOWUP_REVISION_REPORT.md','FIVE_FOLLOWUP_SELF_CHECK.md',
      'REPRODUCTION_FIVE_FOLLOWUP.md']


def main():
    source={}
    with zipfile.ZipFile(PREVIOUS/'manuscript/source_private.zip') as old:
        for name in old.namelist():
            if name.startswith('ROOT/'):
                p=ROOT/name[5:];assert p.is_file();source[name]=(p,name)
    for p in (ROOT/'manuscript').rglob('*'):
        if p.is_file() and p.suffix in ['.tex','.bib','.bst','.sty','.pdf','.png','.svg','.sh']:
            name=str(p.relative_to(ROOT));source[name]=(p,name)
    for n in DOCS:source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
    code={}
    with zipfile.ZipFile(PREVIOUS/'packages/current_mapping_column_code_private.zip') as old:
        for name in old.namelist():
            if name=='PACKAGE_CONTENTS_SHA256.json':continue
            p=ROOT/name;assert p.is_file(),name;code[name]=(p,name)
    for p,_ in source.values():
        name=str(p.relative_to(ROOT));code[name]=(p,name)
    for name in ['check_five_followup_revision.py','package_five_followup_revision.py']:
        p=ROOT/'scripts'/name;n=str(p.relative_to(ROOT));code[n]=(p,n)
    for name in ['precheck-three-pass.json','protected-inputs.json','source-pdf-check.json',
                 'changes.json','visual-check.json','ridge-square-precheck.json','verify_delivery.py','implement.py']:
        p=OUT/name;assert p.is_file();n=str(p.relative_to(ROOT));code[n]=(p,n)
    for p in (ROOT/'ccfa-review-reports/five-followup-20261003').iterdir():
        if p.is_file() and p.suffix in ['.json','.py','.md']:
            n=str(p.relative_to(ROOT));code[n]=(p,n)
    assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz') or
                   n=='outputs/review-external/traces.jsonl.gz' for n in code)
    ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()))
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
    assert (ROOT/'packages/synthetic_certificate_reproduction.zip').read_bytes()==(PREVIOUS/'packages/synthetic_certificate_reproduction.zip').read_bytes()
    print(json.dumps({'source_members':ns+1,'code_members':nc+1,'synthetic_byte_identical':True}))


if __name__=='__main__':main()

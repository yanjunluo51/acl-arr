"""Current private artifacts and a small data-independent residual test package."""
from pathlib import Path
import json, zipfile
from package_certificate_granularity import write_zip

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/acceptance-review-implementation'
OLD=ROOT/'history/before-acceptance-review'
DOCS=['LATEST_MANUSCRIPT.md','LATEST_EXTERNAL_VERIFICATION.md','DATA_STATEMENT_CURRENT.md',
      'ACCEPTANCE_REVIEW_REVISION_REPORT.md','REPRODUCTION_ACCEPTANCE_REVIEW.md','REAL_SCORING_COST_PROTOCOL.md']
NEW_SCRIPTS=['residual_certificates.py','test_residual_certificates.py','cost_column_certificates.py',
             'run_cost_certificates.py','wmt23_quality_diagnostic.py','check_wmt23_quality.py',
             'render_acceptance_revision.py','finish_acceptance_revision.py',
             'check_acceptance_revision.py','package_acceptance_revision.py','verify_acceptance_delivery.py']
OMIT={'final-delivery.json','clean-package-check.json','clean-source-build.log','clean-code-render.log',
      'clean-residual-test.log','clean-validation.log','delivery-check.log','package-build.log'}

def main():
    source={}
    with zipfile.ZipFile(OLD/'manuscript/source_private.zip') as z:
        for n in z.namelist():
            if n.startswith('ROOT/'):
                p=ROOT/n[5:];assert p.is_file();source[n]=(p,n)
    for p in (ROOT/'manuscript').rglob('*'):
        if p.is_file() and p.suffix in ['.tex','.bib','.bst','.sty','.pdf','.png','.svg','.sh']:
            n=str(p.relative_to(ROOT));source[n]=(p,n)
    for n in DOCS:source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
    code={}
    with zipfile.ZipFile(OLD/'packages/current_mapping_column_code_private.zip') as z:
        for n in z.namelist():
            if n=='PACKAGE_CONTENTS_SHA256.json':continue
            p=ROOT/n;assert p.is_file();code[n]=(p,n)
    for p,_ in source.values():
        n=str(p.relative_to(ROOT));code[n]=(p,n)
    for name in NEW_SCRIPTS:
        p=ROOT/'scripts'/name;n=str(p.relative_to(ROOT));code[n]=(p,n)
    for p in OUT.iterdir():
        if p.is_file() and p.name not in OMIT and p.suffix in ['.json','.md','.csv','.bib','.log']:
            n=str(p.relative_to(ROOT));code[n]=(p,n)
    assert not any(n.startswith('data/') or 'wmt23-official/' in n or n.endswith('query_traces.jsonl.gz') or n=='outputs/review-external/traces.jsonl.gz' for n in code)
    ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()))
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
    assert (ROOT/'packages/synthetic_certificate_reproduction.zip').read_bytes()==(OLD/'packages/synthetic_certificate_reproduction.zip').read_bytes()
    independent=[(ROOT/'scripts'/n,'scripts/'+n) for n in ['residual_certificates.py','test_residual_certificates.py','tolerance_certificates.py']]
    independent += [(OUT/n,'reference-results/'+n) for n in ['residual-theory-check.json','mixed-example-check.json']]
    readme='''# Residual and mixed certificate checks

No third-party scores, MQM labels, model inference, network or TeX are required.
Recorded environment: Python 3.9.6 and NumPy 2.0.2.

Run from the extracted directory:
    python3 scripts/test_residual_certificates.py

The script independently enumerates partial states and query actions, then writes
review-revision/acceptance-review-implementation/residual-theory-check.json.
Compare counts/status with reference-results; timing is not a scientific result.
There are 200704 exhaustive residual comparisons, 800 larger random checks,
4032 mixed-action comparisons and 3136 empty-state matches. These validate
finite instances, not general novelty or independent human proof. Models use
median Boolean opposition, a fixed integer bit budget and positive additive
prices (rational prices may be scaled to integers). No online policy is claimed.
No new software license is assigned on behalf of the authors.
'''
    nr=write_zip(ROOT/'packages/residual_certificate_reproduction.zip',independent,
                 {'README.md':readme,'requirements.txt':'numpy==2.0.2\n'})
    print(json.dumps({'source_members':ns+1,'code_members':nc+1,'residual_members':nr+1,'original_synthetic_byte_identical':True}))

if __name__=='__main__':main()

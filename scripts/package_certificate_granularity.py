"""Current source/code archives plus a separate score-independent benchmark."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
DOCS=['LATEST_MANUSCRIPT.md','CERTIFICATE_GRANULARITY_REVISION_REPORT.md',
      'REPRODUCTION_CERTIFICATE_GRANULARITY.md','CERTIFICATE_GRANULARITY_SELF_CHECK.md',
      'DATA_STATEMENT_CURRENT.md','REPRODUCTION_EDITORIAL_REVISION.md',
      'EDITORIAL_REVISION_REPORT.md','EDITORIAL_SELF_CHECK.md']


def write_zip(target,files,extra=None):
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        manifest={}
        for source,name in sorted(files,key=lambda x:x[1]):
            payload=source.read_bytes();z.writestr(name,payload)
            manifest[name]=hashlib.sha256(payload).hexdigest()
        for name,text in (extra or {}).items():
            payload=text.encode();z.writestr(name,payload)
            manifest[name]=hashlib.sha256(payload).hexdigest()
        z.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(manifest,indent=2)+'\n')
    return len(manifest)


def main():
    source=[]
    for p in (ROOT/'manuscript').rglob('*'):
        if p.is_file() and p.suffix in ['.tex','.bib','.bst','.sty','.pdf','.png','.svg','.sh']:
            source.append((p,str(p.relative_to(ROOT))))
    source += [(ROOT/n,'ROOT/'+n) for n in DOCS]
    ns=write_zip(ROOT/'manuscript/source_private.zip',source)
    # Root docs have no artificial ROOT/ prefix in the code bundle.
    code=[(p,str(p.relative_to(ROOT))) for p,_ in source]
    code += [(p,str(p.relative_to(ROOT))) for p in (ROOT/'scripts').glob('*.py')]
    code += [(ROOT/n,n) for n in ['requirements.txt','requirements-checks.txt']]
    for directory in ['review-revision/certificate-granularity','review-revision/review-overhead-analysis',
                      'review-revision/mapping-column','review-revision/editorial-implementation',
                      'outputs/column-certificates','outputs/synthetic-certificates']:
        for p in (ROOT/directory).rglob('*'):
            if (p.is_file() and p.suffix in ['.json','.jsonl','.csv','.md','.py','.npz','.gz']
                    and '/pdf-qa/' not in str(p) and '/visual/' not in str(p)
                    and p.name not in ['package-check.json','revise_manuscript.py','final-delivery.json',
                                   'package-regression-check.json','clean-package-check.json','visual-check.json']):
                code.append((p,str(p.relative_to(ROOT))))
    for n in ['results.json','all_result_cells.csv','protocol.json','execution.json',
              'base_list_diagnostics.json','base_list_diagnostic_cells.csv']:
        p=ROOT/'outputs/mapping-column'/n;code.append((p,str(p.relative_to(ROOT))))
    for n in ['zero-query-decomposition.csv','analyze_saved_editorial_evidence.py','code-result-evidence.json']:
        p=ROOT/'review-revision/editorial-audit'/n;code.append((p,str(p.relative_to(ROOT))))
    # Table bases are presentation inputs and contain no third-party score matrix.
    for p in (ROOT/'review-revision/editorial-implementation/table-bases').glob('*.tex'):
        code.append((p,str(p.relative_to(ROOT))))
    # Ensure every archive member occurs once.
    code=list({n:(p,n) for p,n in code}.values())
    nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',code)
    names=['analyze.py','query_selection.py','review_accelerated.py','review_kernels.py',
           'review_priority.py','mapping_column_experiments.py','column_certificate.py',
           'run_synthetic_certificates.py','audit_synthetic_certificates.py','test_column_certificate.py']
    synthetic=[(ROOT/'scripts'/n,'scripts/'+n) for n in names]
    synthetic.append((ROOT/'review-revision/certificate-granularity/synthetic-protocol.json',
                      'review-revision/certificate-granularity/synthetic-protocol.json'))
    for p in (ROOT/'outputs/synthetic-certificates').rglob('*'):
        if p.is_file():synthetic.append((p,'reference-results/synthetic-certificates/'+str(p.relative_to(ROOT/'outputs/synthetic-certificates'))))
    readme='''# Score-independent certificate benchmark

This archive contains the complete manuscript entry and column solvers, a controlled score generator, saved generated inputs and reference results. No original RewardBench/WMT scores, human labels or network access are required. Synthetic panels test evidence sharing under the declared median completion model; they do not replace NLP evaluation.

The recorded environment is Python 3.9.6, NumPy 2.0.2 and Numba 0.60.0. Use a compatible Python 3.9-3.12 environment and install requirements if necessary:

```
python3 -m pip install -r requirements.txt
python3 scripts/test_column_certificate.py
python3 scripts/run_synthetic_certificates.py
python3 scripts/audit_synthetic_certificates.py outputs/synthetic-certificates
```

Run all 192 generated panels / 576 instances / 8,064 stopping states. The default run output is outputs/synthetic-certificates; it must not already exist. Reference results are in reference-results/synthetic-certificates. Compare generated arrays and results.json geometry/records; runtime or compression timestamps are not scientific outputs.

A query reveals one score or an entire N-score candidate column. No physical model inference occurs. Row costs and budgets are matched across shared, cyclic and independently generated column supports. Cutoff ties, interior and unselected rows remain present; reference panels have separate seeds. Calibration/quality labels are absent.

The source methods are the same full versions used in the manuscript. Some imported modules contain unrelated NLP loader functions; the benchmark calls none of them. The clean-isolation receipt in the parent project checks operation with no data/ directory.

Prepared for local author review. Providing this generated benchmark does not authorize redistribution of original score panels or certify author/third-party code ownership, external proof review or full novelty.
'''
    nn=write_zip(ROOT/'packages/synthetic_certificate_reproduction.zip',synthetic,
                 {'README.md':readme,'requirements.txt':'numpy==2.0.2\nnumba==0.60.0\n'})
    receipt={'status':'PACKAGED_PENDING_CLEAN_ISOLATED_VERIFICATION',
             'source_members':ns+1,'code_members':nc+1,'synthetic_members':nn+1,
             'raw_third_party_scores_included':False}
    (ROOT/'review-revision/certificate-granularity/package-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()

"""Prepare current local bundles; no raw third-party arrays or external release."""
from pathlib import Path
import hashlib,json,zipfile
from package_certificate_granularity import write_zip
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'history/before-deduplicated-evidence-review';OUT=ROOT/'review-revision/deduplicated-evidence-implementation'
DOCS=['README.md','DEDUPLICATED_EVIDENCE_REVISION_REPORT.md','REPRODUCTION_CURRENT.md','LATEST_MANUSCRIPT.md','ENVIRONMENT_AND_REPRODUCTION_INDEX.md','RESULT_DATA_DICTIONARY.md','DATA_STATEMENT_CURRENT.md','ACQUISITION_INDEX.md','requirements-joint.txt','requirements-audit.txt']
NEW_SCRIPTS=['deduplicated_certificates.py','check_deduplicated_backend.py','run_deduplicated_evidence.py','audit_deduplicated_evidence.py','integrate_deduplicated_revision.py','render_deduplicated_revision.py','verify_deduplicated_bundle.py','check_deduplicated_source.py','document_deduplicated_revision.py','package_deduplicated_revision.py','check_deduplicated_delivery.py']
def main():
 source={};code={}
 for path,dest,src in [(OLD/'manuscript/source_private.zip',source,True),(OLD/'packages/current_mapping_column_code_private.zip',code,False)]:
  with zipfile.ZipFile(path) as z:
   for n in z.namelist():
    if n=='PACKAGE_CONTENTS_SHA256.json':continue
    real=n[5:] if src and n.startswith('ROOT/') else n
    assert (ROOT/real).is_file(),n;dest[n]=(ROOT/real,n)
 for n in DOCS:source['ROOT/'+n]=(ROOT/n,'ROOT/'+n)
 for p in (ROOT/'manuscript/tables').glob('*.tex'):
  n=str(p.relative_to(ROOT));source[n]=(p,n)
 for p,_ in source.values():
  n=str(p.relative_to(ROOT));code[n]=(p,n)
 for n in NEW_SCRIPTS:code['scripts/'+n]=(ROOT/'scripts'/n,'scripts/'+n)
 for p in (ROOT/'outputs/deduplicated-evidence').iterdir():
  if p.is_file() and p.suffix in ['.json','.jsonl','.csv']:
   n=str(p.relative_to(ROOT));code[n]=(p,n)
 for p in OUT.iterdir():
  if p.is_file() and p.suffix in ['.json','.diff','.md'] and p.name not in ['final-delivery.json','package-build.json','clean-package-check.json'] and not p.name.startswith('clean-'):
   n=str(p.relative_to(ROOT));code[n]=(p,n)
 n='ccfa-review-reports/sentence-review-050812-assessment/adjudication.json';code[n]=(ROOT/n,n)
 assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz') for n in code)
 ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()));nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
 redactions={};identity=Path.home().name.encode().lower();home=str(Path.home()).encode()
 for current,target in [('manuscript/source_private.zip','packages/current_anonymous_source.zip'),('packages/current_mapping_column_code_private.zip','packages/current_anonymous_code.zip')]:
  with zipfile.ZipFile(ROOT/current) as z,zipfile.ZipFile(ROOT/target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
   bindings={};changed=[]
   for n in z.namelist():
    if n=='PACKAGE_CONTENTS_SHA256.json':continue
    raw=z.read(n)
    if home in raw:raw=raw.replace(str(ROOT).encode(),b'<PROJECT_ROOT>').replace(home,b'<LOCAL_USER_HOME>');changed.append(n)
    assert identity not in raw.lower(),n
    out.writestr(n,raw);bindings[n]=hashlib.sha256(raw).hexdigest()
   out.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(bindings,indent=2)+'\n');redactions[target]=changed
 result=dict(status='PREPARED_CURRENT_LOCAL_DEDUPLICATED_PACKAGES',source_members=ns+1,code_members=nc+1,anonymous_redactions=redactions,third_party_raw_arrays_added=False,uploaded_or_submitted=False,complete_redistribution_authorized=False,general_anonymity_certified=False)
 (OUT/'package-build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

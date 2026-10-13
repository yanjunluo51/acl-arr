"""Prepare local current archives without raw third-party score/response arrays."""
from pathlib import Path
import hashlib,json,zipfile
from package_certificate_granularity import write_zip
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'history/before-joint-scale-review';OUT=ROOT/'review-revision/joint-scale-implementation'
DOCS=['JOINT_SCALE_REVISION_REPORT.md','REPRODUCTION_CURRENT.md','LATEST_MANUSCRIPT.md','RESULT_DATA_DICTIONARY.md','DATA_STATEMENT_CURRENT.md','ACQUISITION_INDEX.md','requirements-joint.txt','requirements-audit.txt']
NEW_SCRIPTS=['analyze_cutoff_variation.py','joint_certificate_resources.py','run_joint_scale_experiment.py','audit_joint_scale_evidence.py','compact_joint_certificate.py','run_compact_joint_scale.py','run_outcome_joint_scale.py','retry_outcome_certificates.py','check_remaining_thresholds.py','outcome_threshold_certificate.py','check_compact_scale_evidence.py','run_cutoff_bootstrap.py','check_cutoff_bootstrap_independent.py','measure_outcome_memory.py','analyze_full_mean_certificates.py','integrate_joint_scale_theory.py','render_joint_scale.py','verify_joint_scale_bundle.py','check_new_joint_formulations.py','check_joint_scale_source.py','package_joint_scale.py','check_joint_scale_delivery.py']
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
 for directory in ['joint-scale','compact-joint-scale','outcome-joint-scale','cutoff-bootstrap']:
  for p in (ROOT/'outputs'/directory).iterdir():
   if p.is_file() and p.suffix in ['.json','.jsonl','.csv']:
    n=str(p.relative_to(ROOT));code[n]=(p,n)
 for p in OUT.iterdir():
  if p.is_file() and p.suffix in ['.json','.diff'] and p.name not in ['final-delivery.json','package-build.json','clean-package-check.json'] and not p.name.startswith('clean-'):
   n=str(p.relative_to(ROOT));code[n]=(p,n)
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
 result=dict(status='PREPARED_CURRENT_LOCAL_JOINT_SCALE_PACKAGES',source_members=ns+1,code_members=nc+1,anonymous_redactions=redactions,third_party_raw_arrays_added=False,uploaded_or_submitted=False,complete_redistribution_authorized=False,general_anonymity_certified=False)
 (OUT/'package-build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

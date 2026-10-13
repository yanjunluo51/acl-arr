"""Prepare current local private archives and separate path-anonymous copies."""
from pathlib import Path
import hashlib,json,zipfile
from package_certificate_granularity import write_zip
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'history/before-joint-certificate-review';OUT=ROOT/'review-revision/joint-certificate-implementation'
DOCS=['LATEST_MANUSCRIPT.md','JOINT_CERTIFICATE_REVISION_REPORT.md','REPRODUCTION_JOINT_CERTIFICATES.md','RESULT_DATA_DICTIONARY.md','DATA_STATEMENT_CURRENT.md','ACQUISITION_INDEX.md','requirements-joint.txt','requirements-audit.txt']
NEW_SCRIPTS=['joint_certificates.py','check_joint_certificates.py','run_joint_certificate_panels.py','check_joint_panels.py','analyze_joint_discovery.py','run_query_interventions.py','check_query_interventions.py','check_protocol_equivariance.py','integrate_joint_theory.py','integrate_joint_results.py','complete_joint_revision.py','render_joint_revision.py','verify_joint_bundle.py','check_joint_source.py','package_joint_revision.py','check_joint_delivery.py']

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
    for directory in [ROOT/'outputs/joint-certificates',ROOT/'outputs/query-mechanism-interventions']:
        for p in directory.iterdir():
            if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.gz']:
                n=str(p.relative_to(ROOT));code[n]=(p,n)
    for n in ['pre-edit-checks.json','protocol.json','protocol-check.json','source-pdf-check.json','prose-check.json','new-prose-check.json','item-completion.json','item-completion.csv','main.tex.diff','appendix.tex.diff']:
        p=OUT/n;assert p.is_file(),n;rel=str(p.relative_to(ROOT));code[rel]=(p,rel)
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
    result={'status':'PREPARED_CURRENT_PRIVATE_AND_PATH_ANONYMOUS_PACKAGES','source_members':ns+1,'code_members':nc+1,'anonymous_redactions':redactions,'new_derived_evidence_included':True,'original_raw_score_MQM_arrays_added':False,'uploaded_or_submitted':False,'complete_redistribution_authorized':False,'general_anonymity_certified':False}
    (OUT/'package-build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

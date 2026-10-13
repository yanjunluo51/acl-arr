"""Prepare local author source/code packages for the integrated evidence revision."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'review-revision/editorial-integration-20261006'
OLD=ROOT/'history/before-editorial-integration-20261006'
DOCS=['README.md','LATEST_MANUSCRIPT.md','REPRODUCTION_CURRENT.md','ENVIRONMENT_AND_REPRODUCTION_INDEX.md','RESULT_DATA_DICTIONARY.md','DATA_STATEMENT_CURRENT.md','ACQUISITION_INDEX.md','EDITORIAL_INTEGRATION_REPORT.md','EDITORIAL_SELFCHECK_REPORT.md']
OUTDIRS=['full-mean-grid-20261005','frontier-priority-20261005','common-information-20261005','protocol-evidence-20261005']

def write(path,members):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  h={}
  for n,p in sorted(members.items()):
   raw=p.read_bytes();z.writestr(n,raw);h[n]=hashlib.sha256(raw).hexdigest()
  z.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(h,indent=2)+'\n')
 return len(h)

def main():
 source={};code={}
 for archive,dest,src in [(OLD/'manuscript/source_private.zip',source,True),(OLD/'packages/current_mapping_column_code_private.zip',code,False)]:
  with zipfile.ZipFile(archive) as z:
   for n in z.namelist():
    if n=='PACKAGE_CONTENTS_SHA256.json':continue
    local=n[5:] if src and n.startswith('ROOT/') else n
    p=ROOT/local;assert p.is_file(),local;dest[n]=p
 for p in (ROOT/'manuscript/tables').glob('*.tex'):source[str(p.relative_to(ROOT))]=p
 for n in DOCS:source['ROOT/'+n]=ROOT/n
 for p in source.values():code[str(p.relative_to(ROOT))]=p
 for p in (ROOT/'scripts').glob('*.py'):code[str(p.relative_to(ROOT))]=p
 for directory in OUTDIRS:
  for p in (ROOT/'outputs'/directory).rglob('*'):
   if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.gz']:
    code[str(p.relative_to(ROOT))]=p
 for directory in [ROOT/'review-revision/evidence-discovery-implementation-20261005',ROOT/'review-revision/editorial-selfcheck-20261006',RUN]:
  for p in directory.iterdir():
   if p.is_file() and p.suffix in ['.json','.md','.log','.py'] and not p.name.startswith(('clean-','package-','final-')):
    code[str(p.relative_to(ROOT))]=p
 for p in (RUN/'citations').glob('*.json'):code[str(p.relative_to(ROOT))]=p
 for p in (ROOT/'visual-composer').glob('*.md'):code[str(p.relative_to(ROOT))]=p
 # Frozen source protocol imports and figure/table bases are already inherited.
 assert not any(n.startswith('data/') for n in code)
 ns=write(ROOT/'manuscript/source_private.zip',source)
 nc=write(ROOT/'packages/current_mapping_column_code_private.zip',code)
 # Anonymous copies remain LOCAL; no redistribution authorization is asserted.
 anonymous={}
 for src,dst in [('manuscript/source_private.zip','packages/current_anonymous_source.zip'),('packages/current_mapping_column_code_private.zip','packages/current_anonymous_code.zip')]:
  with zipfile.ZipFile(ROOT/src) as a,zipfile.ZipFile(ROOT/dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   h={};redacted=[]
   for n in a.namelist():
    if n=='PACKAGE_CONTENTS_SHA256.json':continue
    raw=a.read(n)
    if str(Path.home()).encode() in raw:
     raw=raw.replace(str(ROOT).encode(),b'<PROJECT_ROOT>').replace(str(Path.home()).encode(),b'<LOCAL_USER_HOME>');redacted.append(n)
    assert Path.home().name.encode().lower() not in raw.lower(),n
    z.writestr(n,raw);h[n]=hashlib.sha256(raw).hexdigest()
   z.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(h,indent=2)+'\n');anonymous[dst]=redacted
 receipt=dict(status='PREPARED_LOCAL_EDITORIAL_INTEGRATION_PACKAGES',source_members=ns,code_members=nc,anonymous_redactions=anonymous,raw_panel_arrays_included=False,derived_flip_outcomes_included=True,uploaded_or_submitted=False,complete_redistribution_authorized=False)
 (RUN/'package-build.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

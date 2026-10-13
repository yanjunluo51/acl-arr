"""Package the current revision locally; preserve prior archives in history."""
from pathlib import Path
import json,zipfile
from package_editorial_integration import write
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'review-revision/coherent-writing-implementation'
OLD=ROOT/'history/before-coherent-writing-implementation'
DOCS=['README.md','LATEST_MANUSCRIPT.md','REPRODUCTION_CURRENT.md','ENVIRONMENT_AND_REPRODUCTION_INDEX.md','RESULT_DATA_DICTIONARY.md','DATA_STATEMENT_CURRENT.md','RESPONSIBLE_NLP_CURRENT.md','COHERENT_REVISION_REPORT.md','COHERENT_SELFCHECK_REPORT.md']
def main(receipt=None):
 receipt=Path(receipt).resolve() if receipt else RUN/'package-build.json'
 if receipt.exists():raise FileExistsError('Existing package receipt is preserved; use --receipt with a new path')
 source={};code={}
 for archive,dest,src in [(OLD/'manuscript/source_private.zip',source,True),(OLD/'packages/current_mapping_column_code_private.zip',code,False)]:
  with zipfile.ZipFile(archive) as z:
   for n in z.namelist():
    if n=='PACKAGE_CONTENTS_SHA256.json':continue
    p=ROOT/(n[5:] if src and n.startswith('ROOT/') else n);assert p.is_file(),n;dest[n]=p
 for directory in ['manuscript/tables','manuscript/supplement']:
  for p in (ROOT/directory).iterdir():
   if p.is_file():source[str(p.relative_to(ROOT))]=p
 for n in DOCS:source['ROOT/'+n]=ROOT/n
 for p in source.values():code[str(p.relative_to(ROOT))]=p
 for p in (ROOT/'scripts').glob('*.py'):code[str(p.relative_to(ROOT))]=p
 for p in (ROOT/'outputs/evidence-cost-contrasts').iterdir():
  if p.is_file():code[str(p.relative_to(ROOT))]=p
 for p in RUN.iterdir():
  if p.is_file() and p.suffix in ['.py','.json','.csv'] and not p.name.startswith(('final-','package-','clean-')):code[str(p.relative_to(ROOT))]=p
 assert not any(n.startswith('data/') for n in code)
 counts={};counts['source']=write(ROOT/'manuscript/source_private.zip',source);counts['code']=write(ROOT/'packages/current_mapping_column_code_private.zip',code)
 for src,dst in [('manuscript/source_private.zip','packages/current_anonymous_source.zip'),('packages/current_mapping_column_code_private.zip','packages/current_anonymous_code.zip')]:
  import hashlib
  with zipfile.ZipFile(ROOT/src) as a,zipfile.ZipFile(ROOT/dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   h={}
   for n in a.namelist():
    if n=='PACKAGE_CONTENTS_SHA256.json':continue
    raw=a.read(n).replace(str(ROOT).encode(),b'<PROJECT_ROOT>').replace(str(Path.home()).encode(),b'<LOCAL_USER_HOME>')
    assert Path.home().name.encode().lower() not in raw.lower(),n
    z.writestr(n,raw);h[n]=hashlib.sha256(raw).hexdigest()
   z.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(h,indent=2)+'\n')
 result=dict(status='LOCAL_PACKAGES_PREPARED',members=counts,raw_arrays_included=False,derived_evidence_included=True,uploaded=False,complete_redistribution_authorized=False)
 receipt.parent.mkdir(parents=True,exist_ok=True)
 with receipt.open('x') as f:f.write(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--receipt');a=p.parse_args();main(a.receipt)

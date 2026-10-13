"""Synchronize current private source and code bundles without third-party inputs."""
import json,zipfile
from pathlib import Path
from package_certificate_granularity import write_zip
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/score-observation-implementation';OLD=ROOT/'history/before-score-observation-implementation'
DOCS=['SCORE_OBSERVATION_REVISION_REPORT.md','SCORE_OBSERVATION_SELF_CHECK.md','REPRODUCTION_SCORE_OBSERVATION.md','LATEST_MANUSCRIPT.md']
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
 for n in ['analyze_acquisition_mechanisms.py','check_acquisition_mechanisms.py','render_acquisition_mechanisms.py','check_score_observation_revision.py','package_score_observation_revision.py']:
  p=ROOT/'scripts'/n;name=str(p.relative_to(ROOT));code[name]=(p,name)
 for directory in [OUT,ROOT/'outputs/acquisition-mechanisms']:
  for p in directory.iterdir():
   if p.is_file() and p.suffix in ['.json','.py','.md','.csv','.log','.png','.bib'] and p.name not in ['final-delivery.json','clean-source-build.log','clean-code-render.log','delivery-check.log']:
    n=str(p.relative_to(ROOT));code[n]=(p,n)
 assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz') or n=='outputs/review-external/traces.jsonl.gz' for n in code)
 ns=write_zip(ROOT/'manuscript/source_private.zip',list(source.values()));nc=write_zip(ROOT/'packages/current_mapping_column_code_private.zip',list(code.values()))
 assert (ROOT/'packages/synthetic_certificate_reproduction.zip').read_bytes()==(OLD/'packages/synthetic_certificate_reproduction.zip').read_bytes()
 print(json.dumps({'source_members':ns+1,'code_members':nc+1,'synthetic_byte_identical':True}))
if __name__=='__main__':main()

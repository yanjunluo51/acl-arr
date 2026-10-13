"""Rebuild frozen WMT22 panel admission in a new directory from a legally acquired archive."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
import numpy as np
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();archive=a.archive.resolve();out=a.output.resolve()
 src=R/'review-revision/editorial-evidence-followthrough';manifest=json.loads((src/'confirmation/SOURCE_MANIFEST.json').read_text());assert sha(archive)==manifest['archive_sha256'],'Archive differs from admitted snapshot'
 assert not out.exists(),'Use a new output directory; existing work is never overwritten'
 p=out/'review-revision/editorial-evidence-followthrough';(p/'confirmation').mkdir(parents=True);(out/'scripts').mkdir()
 proto=json.loads((src/'confirmation/protocol.json').read_text())
 for name,h in proto['source_bindings'].items():
  source=R/'scripts'/name
  if sha(source)!=h:source=R/'review-revision/granularity-risk-selfcheck/before/scripts'/name
  assert sha(source)==h,(name,'No matching historical implementation');shutil.copy2(source,out/'scripts'/name)
 for name in ['prepare_confirmation.py','new-panel-metadata.json','confirmation/protocol.json']:shutil.copy2(src/name,p/name)
 link=out/proto['source_archive'];link.parent.mkdir(parents=True,exist_ok=True);link.symlink_to(archive)
 with (out/'rebuild.log').open('w') as f:subprocess.run([sys.executable,str(p/'prepare_confirmation.py')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 for name,h in manifest['extracted_files'].items():assert sha(p/'confirmation/raw-private'/name)==h,name
 current=json.loads((p/'confirmation/admission.json').read_text());expected=json.loads((src/'confirmation/admission.json').read_text());assert current==expected
 arrays=[]
 for lp in proto['panels']:
  z=np.load(p/'confirmation'/f'{lp}.npz')
  # Saved arrays are optional in the distributed package; compare when locally present.
  original=src/'confirmation'/f'{lp}.npz'
  if original.exists():
   old=np.load(original);assert set(z.files)==set(old.files)
   for key in z.files:assert np.array_equal(z[key],old[key]),(lp,key)
   arrays.append(lp)
 receipt=dict(status='PASS_FROZEN_ARCHIVE_TO_PANEL_RECONSTRUCTION',files_verified=len(manifest['extracted_files']),admission_manifest_match=True,local_array_comparisons=arrays,new_model_inference=False,full_trace_solver_reexecution=False,redistribution_permission=False)
 (out/'rebuild-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()

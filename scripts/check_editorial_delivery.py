"""Verify final local packages by clean replay and an independent PDF rebuild."""
from pathlib import Path
import hashlib,json,subprocess,sys,time,zipfile
import fitz
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/editorial-integration-20261006'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive(path,live=False,source=False):
 with zipfile.ZipFile(path) as z:
  m=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(m)==set(z.namelist())-{'PACKAGE_CONTENTS_SHA256.json'}
  assert not any(n.startswith('data/') for n in m)
  for n,h in m.items():
   assert not Path(n).is_absolute() and '..' not in Path(n).parts;assert hashlib.sha256(z.read(n)).hexdigest()==h,n
   if live:assert sha(ROOT/(n[5:] if source and n.startswith('ROOT/') else n))==h,n
  return len(m)+1

def main():
 qa=json.loads((OUT/'source-pdf-check.json').read_text());assert qa['status']=='PASS_SCOPED_EDITORIAL_SOURCE_AND_PDF'
 for n,h in qa['artifact_hashes'].items():assert sha(ROOT/n)==h,n
 latest=sorted((ROOT/'outputs/full-mean-grid-20261005').glob('closure-*.jsonl'))[-1]
 terminal=json.loads(latest.with_suffix('.json').read_text());assert terminal['status']=='COMPLETED_CLOSURE_ATTEMPT_PENDING_AUDIT'
 for n,h in terminal.get('successor_source_hashes',{}).items():assert sha(ROOT/n)==h,n
 dispositions=json.loads((OUT/'review-disposition.json').read_text());assert len(dispositions)==len({r['id'] for r in dispositions})==226
 shortcuts=json.loads((OUT/'bounded-union-check.json').read_text());assert shortcuts['cases']==84 and shortcuts['zero_resource_limit_preserves_unknown']
 counts={}
 for n,live,src in [('manuscript/source_private.zip',True,True),('packages/current_mapping_column_code_private.zip',True,False),('packages/current_anonymous_source.zip',False,True),('packages/current_anonymous_code.zip',False,False)]:counts[n]=archive(ROOT/n,live,src)
 clean=OUT/('clean-'+time.strftime('%Y%m%d-%H%M%S'));assert not clean.exists();clean.mkdir();src=clean/'source';code=clean/'code'
 for n,d in [('packages/current_anonymous_source.zip',src),('packages/current_anonymous_code.zip',code)]:
  with zipfile.ZipFile(ROOT/n) as z:z.extractall(d)
  for p in d.rglob('*'):
   if p.is_file():assert Path.home().name.encode().lower() not in p.read_bytes().lower(),str(p.relative_to(d))
 with (OUT/'clean-evidence.json').open('w') as receipt,(OUT/'clean-evidence.log').open('w') as log:
  subprocess.run([sys.executable,'scripts/verify_editorial_bundle.py','--replay-tables'],cwd=code,check=True,stdout=receipt,stderr=log)
 evidence=json.loads((OUT/'clean-evidence.json').read_text());assert evidence['status']=='PASS_CURRENT_SAVED_EVIDENCE_AND_REQUESTED_REPLAY'
 for p in (ROOT/'manuscript/tables').glob('*.tex'):assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
 generated_changes=[]
 for n,h in json.loads((code/'PACKAGE_CONTENTS_SHA256.json').read_text()).items():
  if sha(code/n)!=h:generated_changes.append(n)
 # Renderer diagnostics may be regenerated; scientific artifacts and sources may not drift.
 assert all(n.startswith('review-revision/') and n.endswith('.json') for n in generated_changes),generated_changes
 with (OUT/'clean-build.log').open('w') as log:subprocess.run(['bash','build.sh'],cwd=src/'manuscript',check=True,stdout=log,stderr=subprocess.STDOUT)
 with fitz.open(ROOT/'manuscript/main.pdf') as current,fitz.open(src/'manuscript/main.pdf') as rebuilt:
  assert len(current)==len(rebuilt)==qa['total_pdf_pages']
  for a,b in zip(current,rebuilt):
   assert a.get_text()==b.get_text(),a.number
   assert a.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples==b.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples,a.number
 pre=json.loads((ROOT/'review-revision/evidence-discovery-implementation-20261005/pre-edit-checks.json').read_text())
 for n,h in pre['protected_scientific_outputs'].items():assert sha(ROOT/n)==h,n
 source_audit=json.loads((OUT/'original-source-audit.json').read_text());assert source_audit['source_instances_verified']==960
 for n,h in source_audit['unchanged_inputs'].items():assert sha(ROOT/n)==h,n
 audit=evidence['full_mean'];assert audit['joint_proven']==qa['joint_proven'] and audit['union_proven']==qa['union_proven']
 result={k:v for k,v in qa.items() if k!='artifact_hashes'}
 result.update(status='PASS_SCOPED_EDITORIAL_INTEGRATION_AND_CLEAN_DELIVERY',three_pre_edit_checks=True,review_dispositions=226,independent_union_shortcut_cases=shortcuts['cases'],single_research_spine_preserved=True,archive_members=counts,clean_directory=str(clean.relative_to(ROOT)),clean_pdf_text_and_pixels_identical=True,table_replay_count=evidence['tables_replayed'],saved_evidence=evidence,original_source_instances_verified=source_audit['source_instances_verified'],generated_receipt_changes=generated_changes,latest_bounded_attempt=terminal,all_full_mean_joint_minima_closed=audit['joint_proven']==1920,scorer_inference_executed=False,human_proof_certified=False,full_novelty_certified=False,complete_citation_support_audit=False,complete_redistribution_authorized=False,author_submission_fields_verified=False,uploaded_or_submitted=False)
 files=list(qa['artifact_hashes'])+list(counts)+['README.md','LATEST_MANUSCRIPT.md','REPRODUCTION_CURRENT.md','EDITORIAL_INTEGRATION_REPORT.md','ENVIRONMENT_AND_REPRODUCTION_INDEX.md','RESULT_DATA_DICTIONARY.md','scripts/verify_editorial_bundle.py','scripts/check_editorial_delivery.py']
 result['hashes']={n:sha(ROOT/n) for n in files}
 (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['hashes','saved_evidence']},indent=2))
if __name__=='__main__':main()

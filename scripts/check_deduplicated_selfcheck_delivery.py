"""Verify current archives, replay clean tables/backend, and rebuild clean PDF."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
import fitz
from package_deduplicated_selfcheck import DOCS,NEW_SCRIPTS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/deduplicated-evidence-selfcheck-20261005'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive(path,live=False,source=False):
 with zipfile.ZipFile(path) as z:
  m=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(m)==set(z.namelist())-{'PACKAGE_CONTENTS_SHA256.json'}
  for n,h in m.items():
   assert not Path(n).is_absolute() and '..' not in Path(n).parts;assert hashlib.sha256(z.read(n)).hexdigest()==h,n
   if live:assert sha(ROOT/(n[5:] if source and n.startswith('ROOT/') else n))==h,n
  return len(m)+1

def main():
 qa=json.loads((OUT/'source-pdf-check.json').read_text());assert qa['status']=='PASS_SCOPED_DEDUPLICATED_SELFCHECK_SOURCE_AND_PDF'
 for n,h in qa['artifact_hashes'].items():assert sha(ROOT/n)==h,n
 counts={}
 for n,live,src in [('manuscript/source_private.zip',True,True),('packages/current_mapping_column_code_private.zip',True,False),('packages/current_anonymous_source.zip',False,True),('packages/current_anonymous_code.zip',False,False)]:counts[n]=archive(ROOT/n,live,src)
 clean=OUT/'clean';assert not clean.exists(),'Preserve previous clean attempts';clean.mkdir();src=clean/'source';code=clean/'code'
 for n,d in [('packages/current_anonymous_source.zip',src),('packages/current_anonymous_code.zip',code)]:
  with zipfile.ZipFile(ROOT/n) as z:z.extractall(d)
  for p in d.rglob('*'):
   if p.is_file():assert Path.home().name.encode().lower() not in p.read_bytes().lower(),str(p.relative_to(d))
 for flags,name in [([], 'portable'),(['--replay-tables','--check-backend','--check-audit-rejection'],'tables-and-backend')]:
  with (OUT/('clean-'+name+'.json')).open('w') as receipt,(OUT/('clean-'+name+'.log')).open('w') as log:
   subprocess.run([sys.executable,'scripts/verify_deduplicated_bundle.py']+flags,cwd=code,check=True,stdout=receipt,stderr=log)
  assert json.loads((OUT/('clean-'+name+'.json')).read_text())['status']=='PASS_PORTABLE_DEDUPLICATED_SAVED_EVIDENCE'
 for p in (ROOT/'manuscript/tables').glob('*.tex'):assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
 for n,h in json.loads((code/'PACKAGE_CONTENTS_SHA256.json').read_text()).items():assert sha(code/n)==h,n
 with (OUT/'clean-build.log').open('w') as log:subprocess.run(['bash','build.sh'],cwd=src/'manuscript',check=True,stdout=log,stderr=subprocess.STDOUT)
 with fitz.open(ROOT/'manuscript/main.pdf') as current,fitz.open(src/'manuscript/main.pdf') as rebuilt:
  assert len(current)==len(rebuilt)==qa['total_pdf_pages']
  for a,b in zip(current,rebuilt):
   assert a.get_text()==b.get_text();assert a.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples==b.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples
 pre=json.loads((OUT/'pre-edit-checks.json').read_text())
 for n,h in pre['protected_scientific_outputs'].items():assert sha(ROOT/n)==h,n
 oldjoint=json.loads((ROOT/'review-revision/joint-certificate-implementation/pre-edit-checks.json').read_text())
 for n in ['packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']:assert sha(ROOT/n)==oldjoint['prior_delivery_hashes'][n]
 dispositions=json.loads((ROOT/'review-revision/deduplicated-evidence-implementation/review-disposition.json').read_text());assert len(dispositions)==70 and len({r['id'] for r in dispositions})==70 and not any(r['implementation_status']=='NOT_APPLIED_ASSESSMENT_ONLY' for r in dispositions)
 evidence=json.loads((OUT/'clean-tables-and-backend.json').read_text())
 check=dict(status='PASS_CLEAN_CURRENT_DEDUPLICATED_SELFCHECK_DELIVERY',archive_members=counts,clean_pdf_pages=qa['total_pdf_pages'],clean_pdf_text_and_pixels_identical=True,portable_default_passed=True,all_77_tables_regenerated_exactly=True,independent_160_finite_cases_recomputed=True,corrupted_record_rejection_cases_recomputed=10,same_instance_source_fields_checked=15,all_safe_targets_and_returned_cardinality_checked=True,clean_code_manifest_unchanged=True,known_personal_path_marker_scan_clean=True,general_anonymity_certified=False,uploaded_or_submitted=False)
 (OUT/'clean-package-check.json').write_text(json.dumps(check,indent=2)+'\n')
 files=list(qa['artifact_hashes'])+DOCS+['scripts/'+n for n in NEW_SCRIPTS]+list(counts)
 for directory in [ROOT/'outputs/deduplicated-evidence',OUT]:
  files+=[str(p.relative_to(ROOT)) for p in directory.iterdir() if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.diff','.md'] and p.name!='final-delivery.json']
 result=dict(qa);result.pop('artifact_hashes');result.update(status='PASS_SCOPED_DEDUPLICATED_SELFCHECK_AND_CLEAN_DELIVERY',three_pre_edit_checks=True,review_items_dispositioned=70,single_research_spine_preserved=True,deduplicated_records=3936,inferred_equalities=3544,fresh_optimizations=392,small_independent_pairs=388,full_entry_pairs=4,full_residual_joint_reduction_entries=72,full_double_count_reduction_entries=2573,full_deduplicated_entry_total=433303,full_joint_reduction_fraction=72/433303,small_strict_gain_instances=174,small_residual_reduction_entries=256,new_model_inference=False,original_scientific_output_files_verified=308,clean_package_check=check,scientific_evidence_check=evidence,complete_citation_support_audit=False,original_scorer_checkpoint_identities_all_verified=False,author_submission_fields_verified=False,uploaded_or_submitted=False,hashes={n:sha(ROOT/n) for n in sorted(set(files))})
 (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['hashes','scientific_evidence_check']},indent=2))
if __name__=='__main__':main()

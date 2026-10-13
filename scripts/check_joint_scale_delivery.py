"""Clean extracted code verification and independently rebuilt PDF delivery."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
import fitz
from package_joint_scale import DOCS,NEW_SCRIPTS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/joint-scale-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive(path,live=False,source=False):
 with zipfile.ZipFile(path) as z:
  m=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(m)==set(z.namelist())-{'PACKAGE_CONTENTS_SHA256.json'}
  for n,h in m.items():
   assert not Path(n).is_absolute() and '..' not in Path(n).parts;assert hashlib.sha256(z.read(n)).hexdigest()==h,n
   if live:assert sha(ROOT/(n[5:] if source and n.startswith('ROOT/') else n))==h,n
  return len(m)+1

def main():
 qa=json.loads((OUT/'source-pdf-check.json').read_text());assert qa['status']=='PASS_SCOPED_JOINT_SCALE_SOURCE_AND_PDF'
 for n,h in qa['artifact_hashes'].items():assert sha(ROOT/n)==h,n
 counts={}
 for n,live,src in [('manuscript/source_private.zip',True,True),('packages/current_mapping_column_code_private.zip',True,False),('packages/current_anonymous_source.zip',False,True),('packages/current_anonymous_code.zip',False,False)]:counts[n]=archive(ROOT/n,live,src)
 clean=OUT/'clean';assert not clean.exists(),'Preserve previous extraction attempts';clean.mkdir();src=clean/'source';code=clean/'code'
 for n,d in [('packages/current_anonymous_source.zip',src),('packages/current_anonymous_code.zip',code)]:
  with zipfile.ZipFile(ROOT/n) as z:z.extractall(d)
  for p in d.rglob('*'):
   if p.is_file():assert Path.home().name.encode().lower() not in p.read_bytes().lower(),str(p.relative_to(d))
 for flags,name in [([], 'portable'),(['--replay-tables','--verify-optima'],'tables-and-optima')]:
  with (OUT/('clean-'+name+'.json')).open('w') as receipt,(OUT/('clean-'+name+'.log')).open('w') as log:
   subprocess.run([sys.executable,'scripts/verify_joint_scale_bundle.py']+flags,cwd=code,check=True,stdout=receipt,stderr=log)
  assert json.loads((OUT/('clean-'+name+'.json')).read_text())['status']=='PASS_PORTABLE_JOINT_SCALE_SAVED_EVIDENCE'
 for p in (ROOT/'manuscript/tables').glob('*.tex'):assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
 for n,h in json.loads((code/'PACKAGE_CONTENTS_SHA256.json').read_text()).items():assert sha(code/n)==h,n
 with (OUT/'clean-build.log').open('w') as log:subprocess.run(['bash','build.sh'],cwd=src/'manuscript',check=True,stdout=log,stderr=subprocess.STDOUT)
 with fitz.open(ROOT/'manuscript/main.pdf') as current,fitz.open(src/'manuscript/main.pdf') as rebuilt:
  assert len(current)==len(rebuilt)==qa['total_pdf_pages']
  for a,b in zip(current,rebuilt):
   assert a.get_text()==b.get_text();assert a.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples==b.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples
 pre=json.loads((OUT/'pre-edit-checks.json').read_text())
 for n,h in pre['original_output_hashes'].items():assert sha(ROOT/n)==h,n
 oldpre=json.loads((ROOT/'review-revision/latest-sentence-review-implementation/pre-edit-checks.json').read_text())
 for field in ['frozen_hashes','protected_hashes','scientific_output_hashes']:
  for n,h in oldpre[field].items():assert sha(ROOT/n)==h,n
 oldjoint=json.loads((ROOT/'review-revision/joint-certificate-implementation/pre-edit-checks.json').read_text())
 for n in ['packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']:assert sha(ROOT/n)==oldjoint['prior_delivery_hashes'][n]
 evidence=json.loads((OUT/'clean-tables-and-optima.json').read_text())
 check=dict(status='PASS_CLEAN_CURRENT_JOINT_SCALE_DELIVERY',archive_members=counts,clean_pdf_text_and_pixels_identical=True,portable_default_passed=True,all_75_tables_regenerated_exactly=True,independent_7680_old_minima_recomputed=True,both_new_formulations_recomputed_on_all_7680_tasks=True,clean_code_manifest_unchanged=True,known_personal_path_marker_scan_clean=True,general_anonymity_certified=False,uploaded_or_submitted=False)
 (OUT/'clean-package-check.json').write_text(json.dumps(check,indent=2)+'\n')
 files=list(qa['artifact_hashes'])+DOCS+['scripts/'+n for n in NEW_SCRIPTS]+list(counts)
 for directory in [ROOT/'outputs/joint-scale',ROOT/'outputs/compact-joint-scale',ROOT/'outputs/outcome-joint-scale',ROOT/'outputs/cutoff-bootstrap',OUT]:
  files+=[str(p.relative_to(ROOT)) for p in directory.iterdir() if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.diff','.md'] and p.name!='final-delivery.json']
 result=dict(qa);result.pop('artifact_hashes');result.update(status='PASS_SCOPED_JOINT_SCALE_REVISION_AND_CLEAN_DELIVERY',three_pre_edit_checks=True,review_items_dispositioned=29,single_research_spine_preserved=True,DP_scale_records=2304,DP_independent_subset_cases=396,compact_primary_pairs=573,compact_total_primary_cases=576,outcome_pairs_completed_after_append_only_followups=576,full_mean_minima=96,full_exact_online_records=384,full_strict_sharing_instances=4,full_aggregate_saving_fraction=2645/435876,bootstrap_records=9600,independent_bootstrap_reconstructed_cases=24,new_model_inference=False,original_online_paths_overwritten=False,original_numerical_results_overwritten=False,original_scientific_output_files_verified=276,clean_package_check=check,scientific_evidence_check=evidence,complete_citation_support_audit=False,original_scorer_checkpoint_identities_all_verified=False,author_submission_fields_verified=False,uploaded_or_submitted=False,hashes={n:sha(ROOT/n) for n in sorted(set(files))})
 (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['hashes','scientific_evidence_check']},indent=2))
if __name__=='__main__':main()

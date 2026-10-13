"""Verify artifact identity, saved evidence replay and clean PDF text/pixels."""
from pathlib import Path
import json,hashlib,subprocess,sys,zipfile,time,re
import fitz
from check_editorial_delivery import archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'review-revision/coherent-writing-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(output_dir=None):
 OUT=Path(output_dir).resolve() if output_dir else BASE
 # Never overwrite an earlier delivery or its clean-build receipts.
 if output_dir:
  OUT.mkdir(parents=True,exist_ok=False)
 elif (OUT/'final-delivery.json').exists():
  raise FileExistsError('Existing delivery is preserved; use --output-dir with a new directory')
 pre=json.loads((BASE/'pre-edit-checks.json').read_text());assert pre['status']=='PASS_THREE_PRE_EDIT_CHECKS'
 for n,h in pre['protected_scientific_outputs'].items():assert sha(ROOT/n)==h,n
 source=(ROOT/'manuscript/main.tex').read_text();app=(ROOT/'manuscript/appendix.tex').read_text()
 old=ROOT/'history/before-coherent-writing-implementation/manuscript'
 for name in ['main.tex','appendix.tex']:
  now=(ROOT/'manuscript'/name).read_text();before=(old/name).read_text()
  for env in ['theorem','proposition','lemma','proof','algorithmic']:
   pattern=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
   assert re.findall(pattern,now,re.S)==re.findall(pattern,before,re.S),(name,env)
 abstract=source.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
 assert len(abstract.split())<=200
 log=(ROOT/'manuscript/main.log').read_text(errors='replace')
 assert not any(x in log for x in ['Overfull','undefined references','undefined citations','LaTeX Error','Rerun to get cross-references right'])
 with fitz.open(ROOT/'manuscript/main.pdf') as pdf:
  assert len(pdf)==90
  assert 'Conclusion' in pdf[7].get_text() and 'Limitations' in pdf[8].get_text()
  assert pdf[8].get_text().startswith('Limitations')
 counts={}
 for n,live,src in [('manuscript/source_private.zip',True,True),('packages/current_mapping_column_code_private.zip',True,False),('packages/current_anonymous_source.zip',False,True),('packages/current_anonymous_code.zip',False,False)]:counts[n]=archive(ROOT/n,live,src)
 clean=OUT/('clean-'+time.strftime('%Y%m%d-%H%M%S'));clean.mkdir();src=clean/'source';code=clean/'code'
 for n,d in [('packages/current_anonymous_source.zip',src),('packages/current_anonymous_code.zip',code)]:
  with zipfile.ZipFile(ROOT/n) as z:z.extractall(d)
 with (OUT/'clean-evidence.json').open('w') as f,(OUT/'clean-evidence.log').open('w') as err:
  subprocess.run([sys.executable,'scripts/verify_coherent_bundle.py','--replay-tables'],cwd=code,stdout=f,stderr=err,check=True)
 e=json.loads((OUT/'clean-evidence.json').read_text());assert e['status']=='PASS_SAVED_EVIDENCE_COST_CONTRASTS_AND_GRID_SUPPLEMENT'
 for p in (ROOT/'manuscript/tables').glob('*.tex'):assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
 for p in (ROOT/'manuscript/supplement').iterdir():assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
 with (OUT/'clean-build.log').open('w') as f:subprocess.run(['bash','build.sh'],cwd=src/'manuscript',stdout=f,stderr=subprocess.STDOUT,check=True)
 with fitz.open(ROOT/'manuscript/main.pdf') as a,fitz.open(src/'manuscript/main.pdf') as b:
  assert len(a)==len(b)==90
  for x,y in zip(a,b):assert x.get_text()==y.get_text() and x.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples==y.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).samples,x.number
 for n,h in pre['protected_scientific_outputs'].items():assert sha(ROOT/n)==h,n
 result=dict(status='PASS_SCOPED_COHERENT_REVISION_AND_CLEAN_DELIVERY',pre_edit_checks=3,single_research_spine_preserved=True,pdf_pages=90,technical_main_pages=8,abstract_whitespace_words=len(abstract.split()),theorem_proof_algorithm_blocks_unchanged=True,protected_scientific_outputs=len(pre['protected_scientific_outputs']),tables_replayed=e['prior']['tables_replayed'],costs=e['costs'],grids=e['grids'],package_members=counts,clean_pdf_text_and_pixels_identical=True,clean_directory=str(clean.relative_to(ROOT)),remaining_joint=8,remaining_union=22,new_scoring_inference=False,new_solver_runs=False,human_proof_certified=False,full_novelty_certified=False,complete_redistribution_authorized=False,author_submission_fields_verified=False,uploaded_or_submitted=False)
 paths=['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','COHERENT_REVISION_REPORT.md','LATEST_MANUSCRIPT.md','REPRODUCTION_CURRENT.md','RESPONSIBLE_NLP_CURRENT.md','DATA_STATEMENT_CURRENT.md']+list(counts)
 result['hashes']={n:sha(ROOT/n) for n in paths}
 (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output-dir');a=p.parse_args();main(a.output_dir)

from pathlib import Path
import json,hashlib,zipfile,subprocess
import fitz
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 work=D/'delivery-clean';work.mkdir(exist_ok=False);expected=json.loads((D/'package-build.json').read_text())['archives'];out=dict(status='RUNNING',archives={},clean_builds={},human_proof_review=False,complete_rights_authorization=False,new_scorer_inference=False,uploaded=False)
 try:
  for name,meta in expected.items():
   path=R/name;assert sha(path)==meta['sha256'];source='source' in name;anon='anonymous' in name;kind='anonymous' if anon else 'private';dest=work/kind/('source' if source else 'code');dest.mkdir(parents=True)
   frozen=[]
   with zipfile.ZipFile(path) as z:
    ns=z.namelist();assert not any('/new-family-private/' in n for n in ns);assert len(ns)==len(set(ns));
    prefix='ROOT/' if source else ''
    for needed in ['scripts/render_current_even_median_table.py','review-revision/editorial-evidence-implementation/audit_delivery.py','review-revision/editorial-evidence-selfaudit/audit_delivery.py','review-revision/stable-batch-implementation/audit_delivery.py','review-revision/stable-batch-implementation/check_positive_discovery.py','review-revision/stable-batch-implementation/REPORT.md']:
     assert prefix+needed in ns,(name,needed,'missing portable verifier')
    binds=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(ns)==set(binds)|{'PACKAGE_CONTENTS_SHA256.json'}
    for n,h in binds.items():
     assert not Path(n).is_absolute() and '..' not in Path(n).parts
     rel=n[5:] if source and n.startswith('ROOT/') else n;local=R/rel
     active=rel.startswith('review-revision/review-current-implementation/solver/')
     if active:frozen.append(n)
     else:
      live=sha(local)
      if live!=h:
       assert anon,(name,n,'live mismatch');raw=local.read_bytes().replace(str(R).encode(),b'<PROJECT_ROOT>').replace(str(Path.home()).encode(),b'<LOCAL_USER_HOME>');assert hashlib.sha256(raw).hexdigest()==h,(name,n,'normalized mismatch')
     hh=hashlib.sha256();carry=b''
     with z.open(n) as f:
      for b in iter(lambda:f.read(1024*1024),b''):
       hh.update(b)
       if anon:
        needle=Path.home().name.encode().lower();assert needle not in (carry+b).lower(),(name,n);carry=b[-len(needle):]
     assert hh.hexdigest()==h,(name,n,'archive')
     if source:z.extract(n,dest)
    out['archives'][name]=dict(sha256=meta['sha256'],members=len(binds),content_hashes_verified=True,anonymous_byte_scan=anon,previously_archived_running_task_receipts=frozen)
   print('ARCHIVE_PASS',name,flush=True)
   if source:
    for ext in ['pdf','aux','bbl','blg','log','out','toc','fls','fdb_latexmk']:
     p=dest/'manuscript'/('main.'+ext)
     if p.exists():p.unlink()
    with (work/kind/'build.log').open('w') as log:subprocess.run(['bash','manuscript/build.sh'],cwd=dest,stdout=log,stderr=subprocess.STDOUT,check=True)
    curr=fitz.open(R/'manuscript/main.pdf');fresh=fitz.open(dest/'manuscript/main.pdf');assert len(curr)==len(fresh)==96
    for i,(a,b) in enumerate(zip(curr,fresh)):
     assert a.get_text()==b.get_text(),(kind,i,'text');assert a.get_pixmap(matrix=fitz.Matrix(1,1)).digest==b.get_pixmap(matrix=fitz.Matrix(1,1)).digest,(kind,i,'pixels')
    out['clean_builds'][kind]=dict(pages=96,text_pixels_match=True,raw_scorer_reexecution=False);print('CLEAN_PASS',kind,flush=True)
  out['status']='PASS_SCOPED_STABLE_BATCH_DELIVERY'
 except Exception as e:
  out['status']='FAILED';out['error']=repr(e);(D/'delivery-final.json').write_text(json.dumps(out,indent=2)+'\n');raise
 (D/'delivery-final.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()

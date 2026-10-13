from pathlib import Path
import json,hashlib,zipfile,subprocess
import fitz
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(cmd,cwd,log):
 with log.open('w') as f:res=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
 assert res.returncode==0,(cmd,str(log))
def main():
 work=D/'delivery-clean';work.mkdir(exist_ok=False);expected=json.loads((D/'package-build.json').read_text())['archives'];out=dict(status='RUNNING',archives={},clean_builds={},human_proof_review=False,complete_rights_authorization=False,new_scorer_inference=False,uploaded=False);sources={};codes={}
 try:
  for name,meta in expected.items():
   path=R/name;assert sha(path)==meta['sha256'];source='source' in name;anon='anonymous' in name;kind='anonymous' if anon else 'private';dest=work/kind/('source' if source else 'code');dest.mkdir(parents=True)
   with zipfile.ZipFile(path) as z:
    ns=z.namelist();assert len(ns)==len(set(ns));binds=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));assert set(ns)==set(binds)|{'PACKAGE_CONTENTS_SHA256.json'}
    for n,h in binds.items():
     assert not Path(n).is_absolute() and '..' not in Path(n).parts
     local=R/(n[5:] if source and n.startswith('ROOT/') else n);live=sha(local);normalized=None
     if live!=h:
      assert anon,(name,n);normalized=local.read_bytes().replace(str(R).encode(),b'<PROJECT_ROOT>').replace(str(Path.home()).encode(),b'<LOCAL_USER_HOME>');assert hashlib.sha256(normalized).hexdigest()==h,(name,n,'live')
     hh=hashlib.sha256();carry=b''
     with z.open(n) as f:
      for b in iter(lambda:f.read(1024*1024),b''):
       hh.update(b)
       if anon:
        needle=Path.home().name.encode().lower();assert needle not in (carry+b).lower(),(name,n);carry=b[-len(needle):]
     assert hh.hexdigest()==h,(name,n,'archive')
     if source or n.startswith('manuscript/') or n.startswith('review-revision/granularity-risk-implementation/') or n in ['review-revision/evidence-structure-revision/column_union.py','outputs/full-mean-grid-20261005/records.jsonl']:
      dst=dest/n;dst.parent.mkdir(parents=True,exist_ok=True)
      if normalized is not None:dst.write_bytes(normalized)
      else:subprocess.run(['cp','-c',str(local),str(dst)],check=True)
    out['archives'][name]=dict(sha256=meta['sha256'],members=len(binds),hash_crc_live_binding=True,anonymous_byte_scan=anon)
   (sources if source else codes)[kind]=dest;print('ARCHIVE_PASS',name,flush=True)
  for kind,source in sources.items():
   for ext in ['pdf','aux','bbl','blg','log','out','toc','fls','fdb_latexmk']:
    p=source/'manuscript'/('main.'+ext)
    if p.exists():p.unlink()
   run(['bash','manuscript/build.sh'],source,work/kind/'build.log')
   curr=fitz.open(R/'manuscript/main.pdf');fresh=fitz.open(source/'manuscript/main.pdf');assert len(curr)==len(fresh)==92
   for i,(a,b) in enumerate(zip(curr,fresh)):
    assert a.get_text()==b.get_text(),(kind,i,'text');assert a.get_pixmap(matrix=fitz.Matrix(1,1)).digest==b.get_pixmap(matrix=fitz.Matrix(1,1)).digest,(kind,i,'pixels')
   code=codes[kind];(code/'manuscript/main.log').write_bytes((source/'manuscript/main.log').read_bytes())
   for script in ['audit_risk.py','audit_layout.py','check_current.py']:
    run(['/usr/bin/python3','review-revision/granularity-risk-implementation/'+script],code,work/kind/(script+'.log'))
   out['clean_builds'][kind]=dict(pages=92,text_pixels_match=True,current_check=True,risk_arithmetic_replay=True,column_predecessors_and_finite_replay=True,raw_scorer_reexecution=False);print('CLEAN_PASS',kind,flush=True)
  out['status']='PASS_SCOPED_GRANULARITY_RISK_DELIVERY'
 except Exception as e:
  out['status']='FAILED';out['error']=repr(e);(D/'delivery-final.json').write_text(json.dumps(out,indent=2)+'\n');raise
 (D/'delivery-final.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()

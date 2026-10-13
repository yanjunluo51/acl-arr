from pathlib import Path
import hashlib,json,subprocess,zipfile
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 assert json.loads((D/'current-check.json').read_text())['status']=='PASS_SCOPED_GRANULARITY_RISK_REVISION'
 previous=json.loads((R/'review-revision/review-current-implementation/delivery-final.json').read_text())['archives']
 newfiles=[p for p in D.rglob('*') if p.is_file() and not any(s in p.parts for s in ['__pycache__','packages-before','delivery-clean']) and p.suffix not in ['.png','.log'] and p.name not in ['package-build.json','delivery-final.json']]
 output={}
 names=['manuscript/source_private.zip','packages/current_mapping_column_code_private.zip','packages/current_anonymous_source.zip','packages/current_anonymous_code.zip']
 for name in names:
  path=R/name;source='source' in name;anon='anonymous' in name;assert sha(path)==previous[name]['sha256']
  backup=D/'packages-before'/name;backup.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['cp','-c',str(path),str(backup)],check=True)
  with zipfile.ZipFile(path,'a',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   old=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'));members={n:R/(n[5:] if source and n.startswith('ROOT/') else n) for n in old}
   for p in newfiles:members[('ROOT/' if source else '')+str(p.relative_to(R))]=p
   for n in ['LATEST_MANUSCRIPT.md','REPRODUCTION_CURRENT.md','LATEST_EXTERNAL_VERIFICATION.md','PARTITION_AND_ARTIFACT_INDEX.md']:members[('ROOT/' if source else '')+n]=R/n
   hashes={};changed={}
   for member,p in sorted(members.items()):
    h=sha(p)
    if anon and h!=old.get(member):
     raw=p.read_bytes().replace(str(R).encode(),b'<PROJECT_ROOT>').replace(str(Path.home()).encode(),b'<LOCAL_USER_HOME>');assert Path.home().name.encode().lower() not in raw.lower(),member;h=hashlib.sha256(raw).hexdigest()
    elif h!=old.get(member):raw=p.read_bytes()
    hashes[member]=h
    if h!=old.get(member):changed[member]=raw
   keep=set(members)-set(changed);z.filelist=[i for i in z.filelist if i.filename in keep];z.NameToInfo={i.filename:i for i in z.filelist}
   for n,raw in changed.items():z.writestr(n,raw)
   z.writestr('PACKAGE_CONTENTS_SHA256.json',json.dumps(hashes,indent=2)+'\n')
  output[name]=dict(sha256=sha(path),members=len(hashes),updated=len(changed));print(name,output[name],flush=True)
 (D/'package-build.json').write_text(json.dumps({'status':'PREPARED_PENDING_AUDIT','archives':output},indent=2)+'\n')
if __name__=='__main__':main()

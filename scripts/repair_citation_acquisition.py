"""Separate usable primary content from redirects; preserve all prior responses."""
from pathlib import Path
import json,hashlib,urllib.request,concurrent.futures
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/editorial-integration-20261006/citations'
f=OUT/'current-citation-sources.json';d=json.loads(f.read_text());backup=OUT/'acquisition-before-content-check.json'
if not backup.exists():backup.write_text(f.read_text())
urls={
'charikar2002priced':('https://research.google/pubs/query-strategies-for-priced-information/','PRIMARY_METADATA_ONLY'),
'fagin2003optimal':('https://www.wisdom.weizmann.ac.il/~naor/PAPERS/middle_agg.pdf','PRIMARY_FULL_TEXT'),
'goerigk2015robustqueries':('https://eprints.lancs.ac.uk/id/eprint/76539/','PRIMARY_METADATA_AND_ABSTRACT'),
'erlebach2015survey':('https://bulletin.eatcs.org/index.php/beatcs/article/download/335/317','PRIMARY_FULL_TEXT'),
'bates2021rcps':('https://people.eecs.berkeley.edu/~angelopoulos/publications/downloads/rcps.pdf','PRIMARY_FULL_TEXT')}
def repair(r):
 p=ROOT/r['path'] if r.get('path') else None
 if p and p.suffix=='.html':
  soup=BeautifulSoup(p.read_bytes(),'html.parser')
  for x in soup(['script','style','noscript']):x.decompose()
  r['visible_text_characters']=len(soup.get_text(' ',strip=True))
  if r['visible_text_characters']<100:r['status']='REDIRECT_OR_EMPTY_STUB'
 if r['key'] not in urls:return r
 url,scope=urls[r['key']];attempt={'url':url}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:raw=response.read(12000000);attempt['resolved_url']=response.url
  ext='pdf' if raw.startswith(b'%PDF') else 'html'
  if ext=='html':
   soup=BeautifulSoup(raw,'html.parser')
   for x in soup(['script','style','noscript']):x.decompose()
   assert len(soup.get_text(' ',strip=True))>500,'no substantive content'
  else:assert len(raw)>10000,'short PDF'
  p=OUT/(r['key']+'-content.'+ext);p.write_bytes(raw)
  r['prior_response']={k:r[k] for k in ['status','path','sha256','resolved_url'] if k in r}
  r['prior_response_content_type']=r.pop('content_type',None)
  r['detected_content_type']='application/pdf' if ext=='pdf' else 'text/html'
  r.update(status='FETCHED',path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),resolved_url=attempt['resolved_url'],acquisition_scope=scope)
  attempt['status']='CONTENT_ACQUIRED'
 except Exception as e:attempt.update(status='ACCESS_UNRESOLVED',error=str(e))
 r['content_fallback_attempt']=attempt;return r
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:d['records']=list(pool.map(repair,d['records']))
d['content_validation']='Redirect-only responses excluded. Abstract/metadata and full-text access are distinct; neither establishes complete citation support.'
d['status_counts']={s:sum(r['status']==s for r in d['records']) for s in sorted(set(r['status'] for r in d['records']))}
f.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(d['status_counts']))
for r in d['records']:
 if r['key'] in urls:print(r['key'],r['status'],r.get('acquisition_scope'),r.get('content_fallback_attempt'))

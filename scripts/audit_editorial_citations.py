"""Acquire current primary bibliographic pages for cited keys; never invent fields."""
import re,json,hashlib,urllib.request,concurrent.futures
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/editorial-integration-20261006/citations';OUT.mkdir(exist_ok=True)
bib=(ROOT/'manuscript/references.bib').read_text();positions=list(re.finditer(r'(?m)^\s*@\w+\s*\{([^,]+)',bib));entries={m[1]:bib[m.start():positions[i+1].start() if i+1<len(positions) else len(bib)] for i,m in enumerate(positions)}
text=(ROOT/'manuscript/main.tex').read_text()+(ROOT/'manuscript/appendix.tex').read_text();keys=sorted(set(k.strip() for x in re.findall(r'\\cite\w*\{([^}]+)\}',text) for k in x.split(',')))
class Meta(HTMLParser):
 def __init__(self):super().__init__();self.data={}
 def handle_starttag(self,tag,attrs):
  d=dict(attrs);key=d.get('name',d.get('property',''))
  if tag=='meta' and (key.startswith('citation_') or key.lower().startswith('dc.')):self.data.setdefault(key,[]).append(d.get('content',''))
def fetch(k):
 e=entries[k]
 existing=OUT/'current-citation-sources.json'
 if existing.exists():
  old=next((r for r in json.loads(existing.read_text())['records'] if r['key']==k and r['status']=='FETCHED'),None)
  if old:return old
 u=re.search(r'\burl\s*=\s*["{]([^"}]+)',e,re.I)
 if not u:return dict(key=k,status='NO_PRIMARY_URL_IN_BIB',context_certified=False)
 url=u[1];a=dict(key=k,url=url,context_certified=False)
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ResearchBibliographyAudit/1.0'})
  with urllib.request.urlopen(req,timeout=25) as r:raw=r.read(12000000);a['resolved_url']=r.url;a['content_type']=r.headers.get('Content-Type','')
  ext='pdf' if raw.startswith(b'%PDF') else 'html';f=OUT/(k+'.'+ext);f.write_bytes(raw)
  a.update(status='FETCHED',path=str(f.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest())
  if ext=='html':p=Meta();p.feed(raw.decode('utf-8',errors='replace'));a['metadata']=p.data
 except Exception as ex:a.update(status='ACCESS_UNRESOLVED',error=str(ex))
 return a
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:r=list(pool.map(fetch,keys))
(OUT/'current-citation-sources.json').write_text(json.dumps(dict(cited_keys=len(keys),records=r,scope='Current primary-page acquisition and metadata, not complete sentence-level citation support or novelty certification'),ensure_ascii=False,indent=2)+'\n')
print('Cited keys',len(keys),'fetched',sum(x['status']=='FETCHED' for x in r),'unresolved',[(x['key'],x.get('error')) for x in r if x['status']!='FETCHED'])

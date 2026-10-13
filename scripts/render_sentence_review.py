"""Apply the current editorial table layer after frozen-result renderers.
Reject different numerical bodies rather than attaching old captions to new results.
"""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def main():
 spec=json.loads((ROOT/'review-revision/sentence-review-implementation/table-spec.json').read_text())
 for name,item in spec.items():
  p=ROOT/name;s=p.read_text()
  h=hashlib.sha256('\n'.join(re.findall(r'\\midrule(.*?)\\bottomrule',s,re.S)).encode()).hexdigest()
  assert h==item['numeric_sha256'],('different results',name)
  p.write_text(item['content'])
 print(json.dumps({'status':'PASS_EDITORIAL_TABLE_LAYER','tables':len(spec),'numeric_bodies_unchanged':True}))
if __name__=='__main__':main()

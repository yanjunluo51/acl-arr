"""Final reviewed caption layer; must follow historical table renderers."""
from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review-revision/compressed-expression-implementation'
def main():
 spec=json.loads((OUT/'caption-spec.json').read_text())
 for name,item in spec.items():
  p=ROOT/'manuscript/tables'/name
  def body(s): return hashlib.sha256('\n'.join(re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',s,re.S)).encode()).hexdigest()
  assert body(p.read_text())==body(item['content'])==item['tabular_sha256'],name
  p.write_text(item['content'])
 print(json.dumps({'status':'PASS_REVIEWED_CAPTION_LAYER','table_files':len(spec),'captions':10,'numeric_values_and_headers_changed':False}))
if __name__=='__main__':main()

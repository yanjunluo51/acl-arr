"""Lossless display-grid supplement; original numeric records and renderers remain."""
import csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=[f'{stem}-{i}-{pool}' for stem in ['query-full-baselines','review-budget','review-score'] for i in range(3) for pool in ['median','mean']]
def export(root=ROOT):
 out=root/'manuscript/supplement';out.mkdir(exist_ok=True);tables=[];rows=[]
 for name in NAMES:
  text=(root/'manuscript/tables'/f'{name}.tex').read_text();tab={'table_id':name,'labels':re.findall(r'\\label\{([^}]+)\}',text),'source_latex':text,'rows':[]}
  for no,line in enumerate(text.splitlines(),1):
   if '&' in line and line.rstrip().endswith(r'\\'):
    cells=[c.strip() for c in line.rstrip()[:-2].split('&')]
    # Preserve multirow/header LaTeX rather than pretending each string is a raw estimate.
    row=dict(table_id=name,source_line=no,row_index=len(tab['rows']),cells_latex=cells);tab['rows'].append(row);rows.append(row)
  tables.append(tab)
 payload=dict(format='lossless-display-grids-v1',scope='All 18 moved grids, including headers, captions, units, failures and adverse results. Rounded display values are not raw per-split records.',tables=tables)
 (out/'result_grids.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 maxcols=max(len(r['cells_latex']) for r in rows)
 with (out/'result_grids.csv').open('w',newline='') as f:
  fields=['table_id','source_line','row_index']+[f'cell_{i+1}_latex' for i in range(maxcols)];w=csv.DictWriter(f,fields);w.writeheader()
  for r in rows:w.writerow(dict({k:r[k] for k in fields[:3]},**{f'cell_{i+1}_latex':v for i,v in enumerate(r['cells_latex'])}))
 # Exact round-trip checks include captions, not only numeric cells.
 reread=json.loads((out/'result_grids.json').read_text())
 for t in reread['tables']:assert t['source_latex']==(root/'manuscript/tables'/f"{t['table_id']}.tex").read_text()
 assert len(list(csv.DictReader((out/'result_grids.csv').open())))==len(rows)
 (out/'README.md').write_text('''# Complete result grids

`result_grids.csv` provides every displayed row from the 18 grids moved out of the reading PDF. Columns contain LaTeX cell text, including headers; `table_id`, source line and row index preserve grouping. Empty trailing cells are padding, not missing scientific outcomes. Rounded table entries must not be treated as original observations.

`result_grids.json` retains complete table source, captions, units, headers and labels, allowing exact reconstruction. Baseline grids are `query-full-baselines-*`; five-budget acquisition grids are `review-budget-*`; grouped-SCoRE grids are `review-score-*`. Panel indices 0/1/2 denote RewardBench 2, WMT23 thirteen-stream and WMT23 twelve-stream panels. Pooling is explicit in each name. All configurations are retained.

Unrounded records and table renderers remain in the local code package; see `RESULT_DATA_DICTIONARY.md` and the current reproduction guide. These display files supplement the definitions and representative results in the manuscript, rather than replacing them. Regenerate with `python3 scripts/export_result_grids.py` after replaying table renderers. Original `.tex` grids also remain in `manuscript/tables/`.

This local packaging does not assert complete redistribution permission for underlying or derived third-party data.
''')
 return dict(tables=len(tables),rows=len(rows),lossless_table_source=True)
if __name__=='__main__':print(json.dumps(export(),indent=2))

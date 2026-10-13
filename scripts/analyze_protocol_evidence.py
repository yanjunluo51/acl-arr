"""Connect existing protocol geometries to matching median evidence; no rerun."""
import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/protocol-evidence-20261005'
def main():
 assert not OUT.exists();OUT.mkdir()
 x=json.loads((ROOT/'outputs/mapping-column/results.json').read_text())
 d=json.loads((ROOT/'outputs/mapping-column/base_list_diagnostics.json').read_text())
 def key(r):return tuple(r[n] for n in ['dataset','split','reference_fraction','cdf','aggregator','q'])
 diagnostics={key(r):r for r in d['records']};records=[]
 for r in x['geometry']:
  if r['aggregator']!='median':continue
  z={n:r[n] for n in ['dataset','split','reference_fraction','cdf','aggregator','q','selected_count','active_selected_items','zero_retained','V_star','offline_exact_certificate']}
  z.update(initial_gap=r['selected_count']-r['zero_retained'],invariant_retained=r['selected_count']-r['active_selected_items'],noninvariant_zero_retained=r['zero_retained']-(r['selected_count']-r['active_selected_items']),**{n:diagnostics[key(r)][n] for n in ['base_list_jaccard','cutoff_tie_selected_fraction']})
  assert 0<=z['noninvariant_zero_retained']<=z['active_selected_items'] and 0<=z['initial_gap']
  assert z['offline_exact_certificate'] is not None;records.append(z)
 assert len(records)==5760
 groups={}
 for r in records:groups.setdefault(tuple(r[n] for n in ['dataset','reference_fraction','cdf','q']),[]).append(r)
 cells=[]
 for k,g in sorted(groups.items()):
  assert len(g)==40
  z=dict(zip(['dataset','reference_fraction','cdf','q'],k),splits=40)
  for n in ['selected_count','active_selected_items','zero_retained','V_star','offline_exact_certificate','initial_gap','invariant_retained','noninvariant_zero_retained','base_list_jaccard','cutoff_tie_selected_fraction']:z[n]=statistics.fmean(r[n] for r in g)
  cells.append(z)
 for n,data in [('records.csv',records),('summary.csv',cells)]:
  with (OUT/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 receipt=dict(status='PASS_EXISTING_PROTOCOL_GEOMETRY_AND_MATCHING_MEDIAN_EVIDENCE',records=5760,cells=144,original_protocol_unchanged=True,new_query_runs=False,mean_protocol_minima_claimed=False)
 (OUT/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

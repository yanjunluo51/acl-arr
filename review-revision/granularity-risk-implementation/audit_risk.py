from pathlib import Path
import json,csv,collections,math
D=Path(__file__).resolve().parent

def main():
 rows=list(map(json.loads,(D/'risk-records.jsonl').open()));assert len(rows)==15360
 groups=collections.defaultdict(list);seen=set()
 for r in rows:
  key=tuple(r[k] for k in ['dataset','aggregator','split','q','method','stopping']);assert key not in seen;seen.add(key)
  counts=r['flip_counts'];assert len(counts)==r['H'] and all(isinstance(c,int) and c>=0 for c in counts)
  den=2*r['k'];assert 10*sum(counts)<=den*len(counts)
  assert r['over_replacements']==sum(10*c>den for c in counts)
  assert math.isclose(r['max_risk'],max(counts)/den,abs_tol=1e-15)
  assert math.isclose(r['average_risk'],sum(counts)/(den*len(counts)),abs_tol=1e-15)
  assert math.isclose(r['over_fraction'],r['over_replacements']/len(counts),abs_tol=1e-15)
  sortedc=sorted(counts);p=.95*(len(counts)-1);lo=math.floor(p);hi=math.ceil(p);quant=(sortedc[lo]*(hi-p)+sortedc[hi]*(p-lo))/den if hi!=lo else sortedc[lo]/den
  assert math.isclose(r['p95_risk'],quant,abs_tol=1e-14)
  groups[r['aggregator'],r['stopping'],r['method']].append(r)
 summary=[]
 for key,g in sorted(groups.items()):
  assert len(g)==960
  summary.append(dict(aggregator=key[0],stopping=key[1],method=key[2],masks=len(g),any_over_masks=sum(x['over_replacements']>0 for x in g),mean_average_risk=sum(x['average_risk'] for x in g)/len(g),mean_max_risk=sum(x['max_risk'] for x in g)/len(g),maximum_risk=max(x['max_risk'] for x in g),mean_over_fraction=sum(x['over_fraction'] for x in g)/len(g)))
 with (D/'risk-aggregate.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 out=dict(status='PASS_SCENARIO_RISK_ARITHMETIC',masks=len(rows),scenarios=sum(r['H'] for r in rows),any_over_masks=sum(r['over_replacements']>0 for r in rows),average_budget_violations=0,maximum_scenario_risk=max(r['max_risk'] for r in rows),native_replacement_reconstruction='run_risk.py reconstructs all member replacements and matches preexisting all_flips totals; this audit independently checks integer averages/quantiles and aggregate fields',independent_new_data=False)
 (D/'risk-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()

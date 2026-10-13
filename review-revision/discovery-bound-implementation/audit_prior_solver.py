from pathlib import Path
import json,sys
D=Path(__file__).resolve().parent;OUT=D/'solver-snapshot'
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
def capacity(cost,b):
 total=0;v=0
 for x in sorted(cost):
  if total+x>b:break
  total+=x;v+=1
 return v
def main():
 cases={tuple(x['key']):x for x in json.loads((OUT/'cases-private.json').read_text())};rr=[json.loads(l) for l in (OUT/'records.jsonl').open()];seen=set();checked=0;errors=[]
 for x in rr:
  key=(tuple(x['key']),x['profile']);assert key not in seen;seen.add(key);c=cases[tuple(x['key'])];rows=c['rows'];caps=c['caps'];T=len(rows[0]);b=c['budget'];eps=c['epsilon']
  def bounds(mask):
   assert mask>=0 and mask < 1<<(len(rows)*T)
   lo=[];hi=[]
   for i,row in enumerate(rows):
    m=(mask>>(i*T))&((1<<T)-1);v=sum(a for j,a in enumerate(row) if m>>j&1);lo.append(v);hi.append(v+(T-bin(m).count('1'))*caps[i])
   return capacity(hi,b),capacity(lo,b)
  if x['status']=='ERROR':errors.append(x['key']);continue
  for name in ['joint','separate']:
   v=x[name];lo,up=bounds(v['query_mask']);assert (lo,up)==(v['V_lower'],v['V_upper']) and up-lo<=eps
   assert v['queries']==bin(int(v['query_mask'])).count('1')
   assert bin(int(v['safe_mask'])).count('1')==lo
   assert sum(sum(rows[i]) for i in range(len(rows)) if int(v['safe_mask'])>>i&1)<=b
   checked+=1
  u=x['union']
  if 'union_mask' in u:
   assert u['union_mask']==u['safety_mask']|u['exclusion_mask'];assert bin(int(u['union_mask'])).count('1')==u['union_minimum'];lo,up=bounds(u['union_mask']);assert up-lo<=eps
   al,_=bounds(u['safety_mask']);_,bu=bounds(u['exclusion_mask']);free=sum(v==0 for v in caps);assert al>=u['safe_target']+free and bu<=u['safe_target']+eps+free;checked+=1
  if x['closed']:assert x['agrees'],('new closed discrepancy',x['key'],x['profile'])
 complete=len(rr)==202
 out=dict(status='PASS_COMPLETED_REPLAY' if complete and not errors else 'PASS_PARTIAL_REPLAY' if not errors else 'ERRORS_RETAINED',completed=len(rr),expected=202,closed=sum(x['closed'] for x in rr),agrees=sum(x['agrees'] for x in rr),unresolved=sum(not x['closed'] for x in rr),integer_witness_checks=checked,error_records=errors,all_requested_executions_complete=complete,all_optima_closed=complete and all(x['closed'] for x in rr),independent_integer_feasibility=True,numerical_lower_bounds_not_rational_proofs=True)
 (OUT/'audit-status.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()

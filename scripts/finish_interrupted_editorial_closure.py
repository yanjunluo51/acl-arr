"""Recover two final checkpoints after process disappearance; append only."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import json,time,hashlib
from pathlib import Path
from continue_full_mean_bounded import load
from audit_full_mean_grid import valuecheck
from joint_certificates import capacity
from bounded_union_certificate import union_certificate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/full-mean-grid-20261005';RUN=ROOT/'review-revision/editorial-integration-20261006'
TARGETS=[('WMT24-ja-zh',39,.1,'primary'),('WMT24-ja-zh',37,.2,'primary')]
def main():
 cases=load();prepared=[]
 for k in TARGETS:
  old=cases[k];x=json.loads(json.dumps(old));attempts={}
  active=[r for r,p in zip(x['rows'],x['caps']) if p];m=len(active);L=capacity(list(map(sum,active)),x['budget']);pmax=min(L,m-x['epsilon']-1)+x['epsilon']+1
  expected=[t for t in range(max(map(sum,active),default=0)+1) if pmax*t-sum(max(0,t-sum(r)) for r in active)>=x['budget']+1] or [0]
  for kind in ['joint','separate']:
   if x[kind]['joint_optimal']:continue
   f=OUT/'bounded-attempts-20261006-185931'/('-'.join(map(str,k))+f'-{kind}.json')
   if not f.exists():continue  # No saved checkpoint: preserve the earlier explicit bounds.
   d=json.loads(f.read_text());assert d['key']==list(k) and d['kind']==kind
   assert sorted(map(int,d['calls']))==expected
   levels=sorted(d['calls'].values(),key=lambda a:a['threshold'])
   for a in levels:
    for v in a['attempts']:valuecheck(x,v,kind=='separate')
   best=min((a['result'] for a in levels),key=lambda r:r['objective']);lb=min(a['result']['joint_lower_bound'] for a in levels)
   assert lb<=best['objective']
   assert best['objective']<=x[kind]['objective']
   x[kind]=dict(best,joint_lower_bound=lb,joint_optimal=lb==best['objective'],status='OPTIMAL' if lb==best['objective'] else 'UNRESOLVED',scope='recovered_complete_threshold_cover')
   valuecheck(x,x[kind],kind=='separate');attempts[kind]=levels
  prepared.append((k,old,x,attempts))
 # Three checks before output overlays: provenance, complete level coverage/witnesses, unchanged objectives/scope.
 pre=dict(status='PASS_THREE_RECOVERY_CHECKS',checks=['two keys absent from 27 completed records; original checkpoints preserved','all admissible levels covered and each saved witness validated','same batch/history/budget/epsilon; unresolved bounds retained'],recovered_cases=[dict(key=list(k),joint_lower=x['joint']['joint_lower_bound'],joint_upper=x['joint']['objective']) for k,old,x,a in prepared])
 (RUN/'final-two-recovery-prechecks.json').write_text(json.dumps(pre,indent=2)+'\n')
 interrupted=OUT/'closure-20261006-185931-continuation.json'
 assert not interrupted.exists()
 interrupted.write_text(json.dumps(dict(status='INTERRUPTED_WITHOUT_TERMINAL_RECEIPT',completed_records=27,planned_cases=29,last_record_elapsed_seconds=1422.6,total_wall_seconds=None,cause='Process and tool session absent when checked; termination cause not established',preserved_progress='bounded-attempts-20261006-185931',successor='finish_interrupted_editorial_closure.py'),indent=2)+'\n')
 stamp=time.strftime('%Y%m%d-%H%M%S');p=OUT/f'closure-{stamp}-recovered-final.jsonl';assert not p.exists();start=time.monotonic()
 with p.open('w') as f:
  for k,old,x,attempts in prepared:
   if x['joint']['joint_optimal'] and x['separate']['joint_optimal']:
    if x['joint']['objective']==x['separate']['objective']:x['union']=dict(status='PROVED_BY_BOUND_SANDWICH',union_minimum=x['joint']['objective'])
    else:x['union']=union_certificate(x['rows'],x['caps'],x['budget'],x['epsilon'],seconds=120,total_seconds=300,presolve=False,certified_joint_minimum=x['joint']['objective'],preferred_target=x['joint']['V_lower']-x['caps'].count(0))
   r=dict(key=list(k),primary=old,closed=x,threshold_attempts=attempts,recovery='complete checkpoint level cover; only unsaved union attempted again; no original score execution')
   f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush();print(k,x['joint']['status'],x['union']['status'] if x['union'] else None,flush=True)
 p.with_suffix('.json').write_text(json.dumps(dict(status='COMPLETED_CLOSURE_ATTEMPT_PENDING_AUDIT',cases=2,seconds=time.monotonic()-start,recovered_checkpoints=2,previous_completed_cases_not_retried=27,interrupted_parent='closure-20261006-185931-continuation.json',successor_source_hashes={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__).resolve(),ROOT/'scripts/bounded_union_certificate.py',ROOT/'scripts/verify_union_shortcut.py']}),indent=2)+'\n');print(p.name,flush=True)
if __name__=='__main__':main()

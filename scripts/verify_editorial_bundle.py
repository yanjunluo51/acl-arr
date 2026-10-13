"""Portable saved-evidence and deterministic display verification for current paper.
No original scorer execution; optional full table replay, no raw panel required.
"""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import argparse,ast,csv,gzip,hashlib,json,math,subprocess,sys
from pathlib import Path
import numpy as np
from audit_full_mean_grid import audit as full_audit
from audit_deduplicated_evidence import capacity
from run_tolerance_sensitivity import scan_path
from verify_deduplicated_bundle import main as prior
ROOT=Path(__file__).resolve().parents[1]
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)

def frontier(root):
 truth={}
 for x in map(json.loads,(root/'outputs/full-mean-grid-20261005/records.jsonl').open()):
  if x['stopping']=='exact':truth[x['dataset'],x['split'],x['q']]=x
 saved={(r['dataset'],int(r['split']),float(r['q']),r['method'],r['stopping']):r for r in csv.DictReader((root/'outputs/frontier-priority-20261005/records.csv').open())}
 replies=states=paths=0;seen=set()
 for r in map(json.loads,gzip.open(root/'outputs/frontier-priority-20261005/traces.jsonl.gz','rt')):
  key=(r['dataset'],r['split'],r['q']);assert key not in seen;seen.add(key);x=truth[key]
  ids={v:i for i,v in enumerate(x['original_output_ids'])};take=[ids[v] for v in r['original_output_ids']]
  rows=np.asarray(x['rows'],np.int64)[take];p=np.asarray(r['caps'],np.int64)
  assert p.tolist()==[x['caps'][i] for i in take] and np.all(p>0)
  assert r['free']==sum(v==0 for v in x['caps']) and r['free']+len(p)==x['selected_count']
  for f in ['N','k','T','budget','selected_count']:assert r[f]==x[f]
  for path in r['paths']:
   t=np.asarray(path['trace'],np.int64).reshape(-1,3)
   assert len({(int(i),int(j)) for i,j,_ in t})==len(t)
   assert not len(t) or np.array_equal(t[:,2],rows[t[:,0],t[:,1]])
   eps=math.ceil(.02*x['selected_count']);limits=np.array([eps,0],np.int64)
   stops=scan_path(p,t[:,[0,2]],x['T'],x['budget'],r['free'],limits)
   for j,name in enumerate(['primary','exact']):
    stop=path['stops'][name];assert tuple(stops[j])==(stop['queries'],stop['V_lower'],stop['V_upper'])
    sr=saved[(*key,path['mode'],name)]
    for field,col in [('queries','queries'),('V_lower','K'),('V_upper','V_upper')]:assert stop[field]==int(sr[col])
    q=stop['queries'];lo=np.zeros(len(p),np.int64);up=x['T']*p.copy()
    for i,_,v in t[:q]:lo[i]+=v;up[i]-=p[i]-v
    kept=[];remaining=x['budget']
    for i in sorted(range(len(up)),key=lambda i:(up[i],i)):
     if up[i]>remaining:break
     remaining-=int(up[i]);kept.append(i)
    assert len(kept)+r['free']==stop['V_lower']
    assert int(rows.sum(axis=1)[kept].sum())==int(sr['true_cost'])<=x['budget']
    assert int(up[kept].sum())==int(sr['upper_cost'])<=x['budget']
    states+=1
   paths+=1;replies+=len(t)
 assert len(seen)==960 and paths==2880 and states==5760 and replies==15838138
 return dict(instances=960,paths=paths,states=states,replies=replies,scope='saved integer outcomes, first stops and masks; scorer/source provenance uses separate original source audit')

def render_layers(root):
 tree=ast.parse((root/'scripts/verify_interface_delivery.py').read_text())
 old=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RENDERERS' for t in n.targets)))
 return old+['render_nontrivial_certification.py','render_main10_editorial.py','render_html_revision.py','render_joint_revision.py','render_latest_sentence_review.py','render_joint_scale.py','render_deduplicated_revision.py','render_evidence_discovery.py','render_evidence_main.py','render_editorial_integration.py']

def main(root=ROOT,replay=False,legacy=True):
 result={}
 if legacy:result['prior']=prior(root,manifest=False,replay=False)
 result['full_mean']=full_audit(root,source=False,write=False)[0]
 result['frontier']=frontier(root)
 if replay:
  before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'manuscript/tables').glob('*.tex')}
  for name in render_layers(root):subprocess.run([sys.executable,str(root/'scripts'/name)],cwd=root,check=True,stdout=sys.stderr)
  after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'manuscript/tables').glob('*.tex')}
  assert before==after,[n for n in before if before[n]!=after.get(n)]
  result['tables_replayed']=len(before)
 result['status']='PASS_CURRENT_SAVED_EVIDENCE_AND_REQUESTED_REPLAY'
 result['human_proof_certified']=False;result['complete_redistribution_authorized']=False
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--replay-tables',action='store_true');p.add_argument('--skip-legacy',action='store_true');a=p.parse_args()
 print(json.dumps(main(replay=a.replay_tables,legacy=not a.skip_legacy),indent=2))

"""Portable saved-evidence validation, with optional numerical reoptimization.
Default uses the standard library, no raw score panels or model/network calls.
"""
from fractions import Fraction
import argparse,ast,csv,hashlib,json,math,statistics,subprocess,sys
from pathlib import Path
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
from verify_latest_sentence_bundle import main as prior
from check_compact_scale_evidence import main as compact_checks,capacity,check

def lines(p):return [json.loads(s) for s in p.open()]
def j(p):return json.loads(p.read_text())
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-11),(a,b)
def main(root,manifest=True,replay=False,optima=False):
 root=root.resolve();old=prior(root,manifest,False,False);compact=compact_checks(root,False)
 dp=lines(root/'outputs/joint-scale/records.jsonl');assert len(dp)==2304
 for x in dp:
  T=x['T'];lo=[];up=[];assert len(x['rows'])==len(x['caps'])==len(x['observed'])
  for i,(r,p,o) in enumerate(zip(x['rows'],x['caps'],x['observed'])):
   assert all(isinstance(v,int) and 0<=v<=p<=7 for v in r) and len(r)==T
   new=x['query_mask']>>(i*T)&((1<<T)-1);assert not new&o;m=o|new
   lo.append(sum(v for a,v in enumerate(r) if m>>a&1));up.append(lo[-1]+(T-bin(m).count('1'))*p)
  assert x['query_mask']>>(len(x['rows'])*T)==0 and x['safe_mask']>>len(x['rows'])==0
  assert bin(x['query_mask']).count('1')==x['queries']
  assert (capacity(up,x['budget']),capacity(lo,x['budget']))==(x['V_lower'],x['V_upper'])
  assert x['V_upper']-x['V_lower']<=x['epsilon']
  assert sum(up[i] for i in range(len(up)) if x['safe_mask']>>i&1)<=x['budget']
  assert capacity(list(map(sum,x['rows'])),x['budget'])==x['true_optimum']
  assert x['budget']==2*x['k']*7*T//10 and x['k']==max(1,round(x['q']*x['N']))
 data=lines(root/'outputs/outcome-joint-scale/records.jsonl');idx={(x['dataset'],x['split'],x['q'],x['requested_size']):x for x in data}
 for r in lines(root/'outputs/outcome-joint-scale/retry-records.jsonl'):
  if r['joint_optimal'] and r['separated_optimal']:idx[tuple(r['primary_key'])]=dict(idx[tuple(r['primary_key'])],**r)
 th=j(root/'outputs/outcome-joint-scale/threshold-check.json');key=tuple(th['protocol']['primary_key']);x=idx[key];F=list(map(sum,x['rows']));p=capacity(F,x['budget'])+1
 expected=[t for t in range(7*x['T']+1) if p*t-sum(max(0,t-v) for v in F)>=x['budget']+1]
 assert expected==th['protocol']['screened_thresholds']==[r['threshold'] for r in th['records']]
 for r in th['records']:
  check(x,r);assert r['solver']['status']==0 and r['solver']['mip_gap']==0
  close(r['solver']['fun'],r['queries']);close(r['solver']['mip_dual_bound'],r['queries'])
 assert min(r['queries'] for r in th['records'])==th['global_lower_bound']==th['global_upper_bound']==555
 retry=next(r for r in lines(root/'outputs/outcome-joint-scale/retry-records.jsonl') if tuple(r['primary_key'])==key)
 assert retry['separated_optimal'];idx[key]=dict(dict(x,**th['best_witness']),split_queries=retry['split_queries'],separated_optimal=True,joint_optimal=True)
 assert len(idx)==576 and all(x['joint_optimal'] and x['separated_optimal'] for x in idx.values())
 full={(x['dataset'],x['split'],x['q']):x for x in idx.values() if x['requested_size']=='full'};assert len(full)==96
 saved={(r['dataset'],int(r['split']),float(r['q']),r['method']):r for r in csv.DictReader((root/'outputs/tolerance-sensitivity/stop_records.csv').open()) if r['aggregator']=='mean' and Fraction(r['tau'])==0}
 dr=list(csv.DictReader((root/'outputs/outcome-joint-scale/full_discovery_records.csv').open()));assert len(dr)==384
 groups={}
 for r in dr:
  k=(r['dataset'],int(r['split']),float(r['q']));w=full[k];o=saved[(*k,r['method'])]
  assert int(r['minimum'])==w['queries']>0 and int(r['separated_minimum'])==w['split_queries']
  assert int(r['exact_queries'])==int(o['queries'])>=w['queries'];assert int(o['returned_count'])==int(o['V_upper'])==w['V_lower']
  assert int(r['N'])==w['N'] and int(r['budget'])==w['budget'];close(r['ratio'],int(r['exact_queries'])/w['queries'])
  groups.setdefault((r['dataset'],float(r['q']),r['method']),[]).append(r)
 for c in csv.DictReader((root/'outputs/outcome-joint-scale/full_discovery_summary.csv').open()):
  g=groups[c['dataset'],float(c['q']),c['method']];assert len(g)==int(c['splits'])==int(c['positive_minima'])==8
  for name,field in [('minimum_mean','minimum'),('queries_mean','exact_queries'),('ratio_mean','ratio')]:close(c[name],statistics.fmean(float(r[field]) for r in g))
  assert int(c['strict_sharing'])==sum(int(r['sharing_saving'])>0 for r in g)
 assert sum(w['queries']<w['split_queries'] for w in full.values())==4
 assert sum(w['split_queries']-w['queries'] for w in full.values())==2645 and sum(w['split_queries'] for w in full.values())==435876
 bs=lines(root/'outputs/cutoff-bootstrap/records.jsonl');assert len(bs)==9600
 assert len({(x['dataset'],x['split'],x['draw'],x['arm'],x['aggregator']) for x in bs})==9600
 for x in bs:
  assert x['k']==max(1,round(.05*x['N'])) and x['budget']==2*x['k']*7*x['T']//10
  assert x['invariant_count']+x['active_rows']==x['selected_count']==x['V_initial_upper']
  assert x['initial_gap']==x['V_initial_upper']-x['V_initial_lower'] and x['epsilon']==math.ceil(.02*x['selected_count'])
  assert x['zero_query_stop']==(x['initial_gap']<=x['epsilon'])
  assert x['V_initial_lower']<=x['full_information_retained']<=x['V_initial_upper'] and 0<=x['selected_jaccard']<=1
  if x['aggregator']=='mean':assert x['median_exact_minimum'] is None and x['median_primary_minimum'] is None
  else:assert 0<=x['median_primary_minimum']<=x['median_exact_minimum']<=x['active_rows']*x['T']
 for c in j(root/'outputs/cutoff-bootstrap/audit.json')['summaries']:
  g=[x for x in bs if all(x[k]==c[k] for k in ['dataset','aggregator','arm'])];assert len(g)==c['cases']==400
  close(c['jaccard_median'],statistics.median(x['selected_jaccard'] for x in g));close(c['zero_stop_fraction'],sum(x['zero_query_stop'] for x in g)/400)
  for field in ['initial_gap','active_rows']:
   name='active_median' if field=='active_rows' else 'initial_gap_median';close(c[name],statistics.median(x[field] for x in g))
  if c['aggregator']=='median':
   for f in ['median_exact_minimum','median_primary_minimum']:close(c[f+'_median'],statistics.median(x[f] for x in g))
 assert j(root/'outputs/cutoff-bootstrap/independent-check.json')['full_test_cases_reconstructed']==24
 from analyze_cutoff_variation import summarize
 cv=list(csv.DictReader((root/'outputs/cutoff-bootstrap/cutoff_variation.csv').open()));expected=summarize(root);assert len(cv)==len(expected)==24
 for c,e in zip(cv,expected):
  for f,v in e.items():
   if isinstance(v,str):assert c[f]==v
   else:close(c[f],v)
 if optima:
  subprocess.run([sys.executable,str(root/'scripts/check_joint_panels.py'),'--no-write'],cwd=root,check=True,stdout=sys.stderr)
  subprocess.run([sys.executable,str(root/'scripts/check_new_joint_formulations.py')],cwd=root,check=True,stdout=sys.stderr)
 if replay:
  tree=ast.parse((root/'scripts/verify_interface_delivery.py').read_text());layers=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RENDERERS' for t in n.targets)))+['render_nontrivial_certification.py','render_main10_editorial.py','render_html_revision.py','render_joint_revision.py','render_latest_sentence_review.py','render_joint_scale.py']
  tables={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'manuscript/tables').glob('*.tex')};assert len(tables)==75
  for name in layers:subprocess.run([sys.executable,str(root/'scripts'/name)],cwd=root,check=True,stdout=sys.stderr)
  assert all(hashlib.sha256((root/'manuscript/tables'/n).read_bytes()).hexdigest()==h for n,h in tables.items())
 return dict(status='PASS_PORTABLE_JOINT_SCALE_SAVED_EVIDENCE',prior=old,compact_primary=compact,DP_witnesses=2304,completed_outcome_pairs_with_followups=576,full_mean_minima=96,full_exact_online_records=384,bootstrap_records=9600,independent_bootstrap_cases=24,tables_replayed=75 if replay else None,old_independent_minima_and_new_formulations_recomputed=optima,human_proof_certified=False,full_novelty_certified=False,complete_redistribution_authorized=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--author-live-check',action='store_true');p.add_argument('--replay-tables',action='store_true');p.add_argument('--verify-optima',action='store_true');a=p.parse_args();print(json.dumps(main(a.root,not a.author_live_check,a.replay_tables,a.verify_optima),indent=2))

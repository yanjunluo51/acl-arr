from pathlib import Path
import json,hashlib,sys
import numpy as np
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
D=Path(__file__).resolve().parent;S=D/'scale'
def main():
 spec=json.loads((S/'protocol.json').read_text());records=[json.loads(l) for l in (S/'records.jsonl').open()];assert len(records)==8
 assert {(x['N'],x['M'],x['T']) for x in records}=={(n,m,t) for n in spec['N'] for m in spec['M'] for t in spec['T']}
 for n,h in spec['frozen_hashes'].items():assert hashlib.sha256((S/'frozen'/n).read_bytes()).hexdigest()==h
 audited=[]
 for x in records:
  N,M,T=x['N'],x['M'],x['T'];assert x['status'] in ['OPTIMAL','UNRESOLVED'],x
  with np.load(S/f'input-{N}-{M}-{T}.npz') as z:base=z['base'];cand=z['candidate'];selected=z['selected'];saved=z['contributions'];caps=z['caps']
  rng=np.random.default_rng(spec['seed']+N+100*M+T);assert np.array_equal(base,rng.random((M,N)));assert np.array_equal(cand,rng.random((T,N)))
  base_selected=np.mean(base,axis=0)>=.5;assert np.array_equal(selected,base_selected);ids=np.flatnonzero(selected);f=np.zeros_like(saved);pp=np.zeros_like(caps)
  for j in range(M):
   changed=base.copy();changed[j]=0;pp+=~(np.mean(changed,axis=0)[ids]>=.5)
   for r in range(T):
    changed[j]=cand[r];f[r]+=~(np.mean(changed,axis=0)[ids]>=.5)
  assert np.array_equal(f,saved) and np.array_equal(pp,caps)
  b=x['budget'];assert b==2*x['k']*M*T//10
  def cap(v):
   total=n=0
   for a in sorted(map(int,v)):
    if total+a>b:break
    total+=a;n+=1
   return n
  qm=x['query_mask'];assert 0<=qm<(1<<(len(ids)*T));lo=[];hi=[]
  for i,row in enumerate(f.T):
   bits=(qm>>(i*T))&((1<<T)-1);v=sum(int(a) for r,a in enumerate(row) if (bits>>r)&1);lo.append(v);hi.append(v+(T-bin(bits).count('1'))*int(caps[i]))
  assert cap(lo)==cap(hi)==x['V_lower']==x['V_upper'];assert cap(f.sum(0))==x['true_optimum'];assert bin(qm).count('1')==x['queries'];assert sum(hi[i] for i in range(len(ids)) if (x['safe_mask']>>i)&1)<=b
  assert x['joint_lower_bound']<=x['queries']
  if x['joint_optimal']:assert x['joint_lower_bound']==x['queries']
  audited.append(dict(N=N,M=M,T=T,active=x['active_rows'],groups=x['groups'],selected=len(ids),true_count=x['true_optimum'],full_retention=x['true_optimum']==len(ids),lower=x['joint_lower_bound'],upper=x['queries'],closed=x['joint_optimal'],seconds=x['seconds'],peak_mib=x['peak_rss_bytes']/2**20,variables=x['max_variables'],constraints=x['max_constraints']))
 result=dict(status='PASS_SAVED_SCORE_AND_INTEGER_WITNESS_REPLAY',records=8,closed=sum(x['closed'] for x in audited),unresolved=sum(not x['closed'] for x in audited),full_retention=sum(x['full_retention'] for x in audited),records_audited=audited,solver_lower_bounds='numerical not rational proof',new_nlp=False,real_inference=False)
 (D/'scale-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

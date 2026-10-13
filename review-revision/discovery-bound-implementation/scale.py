"""Frozen full-outcome-program resource grid; synthetic scores, exact stop only."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,time,hashlib,subprocess,itertools,platform
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
D=Path(__file__).resolve().parent;R=D.parents[1]
def freeze():
 out=D/'scale';out.mkdir(exist_ok=False)
 f=out/'frozen';f.mkdir()
 raw=(R/'scripts/compact_joint_certificate.py').read_text()
 assert raw.count('options=dict(mip_rel_gap=0., time_limit=left)')==1
 raw=raw.replace('options=dict(mip_rel_gap=0., time_limit=left)','options=dict(mip_rel_gap=0., time_limit=left, threads=1, random_seed=0, presolve=True)')
 (f/'compact_joint_certificate.py').write_text(raw)
 (f/'joint_certificates.py').write_bytes((R/'scripts/joint_certificates.py').read_bytes())
 spec={'purpose':'Controlled resource scaling of complete joint outcome-count model, no inference or NLP claim','N':[2048,8192],'M':[7,15],'T':[17,65],'seed':731191,'generator':'PCG64(seed + N + 100*M + T); base MxN then candidate TxN iid Uniform(0,1). Fixed cutoff .5; mean pooling; selected base mean >=.5; exact explicit replacement flips. Nominal k=max(1,round(.30*N)); alpha=.10; all selected rows retained in optimization; no subsampling.','q':.30,'alpha':.10,'cutoff':.5,'epsilon':0,'joint_only':True,'seconds_including_model_work':60,'outer_timeout_seconds':180,'threads':1,'backend':'SciPy milp / bundled HiGHS; forwarded threads=1, random_seed=0, presolve=True, mip_rel_gap=0','expected':8,'one_seed_per_grid_point':'descriptive stress grid, not independent NLP replication','concurrent_load':'Original frozen tolerance experiment continues; elapsed times are load-dependent, not backend-speedup evidence','peak_memory':'resource.getrusage(RUSAGE_SELF).ru_maxrss bytes on Darwin; independent child per target, includes imports, scores, model and solver','frozen_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in f.iterdir()}}
 (out/'protocol.json').write_text(json.dumps(spec,indent=2)+'\n')
def child(N,M,T):
 import resource,numpy as np,scipy
 sys.path.insert(0,str(D/'scale/frozen'))
 import compact_joint_certificate as mod
 start=time.perf_counter();rng=np.random.default_rng(731191+N+100*M+T);base=rng.random((M,N));cand=rng.random((T,N));selected=base.mean(0)>=.5;ids=np.flatnonzero(selected);sums=base.sum(0);f=np.zeros((T,len(ids)),int)
 for r in range(T):
  for j in range(M):f[r]+=((sums[ids]-base[j,ids]+cand[r,ids])/M<.5)
 caps=np.zeros(len(ids),int)
 for j in range(M):caps+=((sums[ids]-base[j,ids])/M<.5)
 k=max(1,round(.30*N));b=2*k*M*T//10
 np.savez_compressed(D/'scale'/f'input-{N}-{M}-{T}.npz',base=base,candidate=cand,selected=selected,contributions=f,caps=caps)
 prep=time.perf_counter()-start;timings=[];orig=mod.milp
 def timed(*a,**kw):
  t=time.perf_counter();v=orig(*a,**kw);timings.append(time.perf_counter()-t);return v
 mod.milp=timed
 rows=f.T.tolist();result=mod.compact_certificate(rows,caps.tolist(),b,epsilon=0,separated=False,seconds=60,outcome_counts=True)
 # Independent membership expansion and explicit original-cost witness check.
 qm=result['query_mask'];lo=[];hi=[];count=0
 for i,row in enumerate(rows):
  bits=(qm>>(i*T))&((1<<T)-1);a=bits.bit_count() if hasattr(bits,'bit_count') else bin(bits).count('1');v=sum(x for r,x in enumerate(row) if (bits>>r)&1);lo.append(v);hi.append(v+(T-a)*int(caps[i]));count+=a
 def capacity(v):
  total=n=0
  for x in sorted(v):
   if total+x>b:break
   total+=x;n+=1
  return n
 assert count==result['queries'];assert capacity(lo)==capacity(hi);assert sum(hi[i] for i in range(len(rows)) if (result['safe_mask']>>i)&1)<=b
 record=dict(N=N,M=M,T=T,k=k,budget=b,selected_count=len(ids),active_rows=int((caps>0).sum()),groups=sum(len(set(row)) for row,p in zip(rows,caps) if p),preparation_seconds=prep,solver_seconds=sum(timings),model_and_validation_seconds=result['seconds']-sum(timings),peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,independent_integer_feasibility=True,**result)
 (D/'scale'/f'result-{N}-{M}-{T}.json').write_text(json.dumps(record)+'\n')
def run():
 out=D/'scale';spec=json.loads((out/'protocol.json').read_text());records=[]
 for N,M,T in itertools.product(spec['N'],spec['M'],spec['T']):
  target=out/f'result-{N}-{M}-{T}.json';assert not target.exists()
  for n,h in spec['frozen_hashes'].items():assert hashlib.sha256((out/'frozen'/n).read_bytes()).hexdigest()==h
  t=time.perf_counter()
  with (out/f'run-{N}-{M}-{T}.log').open('w') as log:
   try:
    r=subprocess.run(['/usr/bin/python3',str(__file__),'child',str(N),str(M),str(T)],stdout=log,stderr=subprocess.STDOUT,timeout=180)
    value=json.loads(target.read_text()) if r.returncode==0 else dict(N=N,M=M,T=T,status='ERROR',returncode=r.returncode)
   except subprocess.TimeoutExpired:value=dict(N=N,M=M,T=T,status='OUTER_TIMEOUT',elapsed_seconds=time.perf_counter()-t)
  records.append(value)
  with (out/'records.jsonl').open('a') as fp:fp.write(json.dumps(value)+'\n')
  (out/'progress.json').write_text(json.dumps(dict(status='COMPLETE_EXECUTION_PENDING_AUDIT' if len(records)==8 else 'RUNNING',completed=len(records),expected=8,closed=sum(x.get('joint_optimal',False) for x in records)),indent=2))
  print(len(records),value['status'],N,M,T,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='child':child(*map(int,sys.argv[2:]))
 else:run()

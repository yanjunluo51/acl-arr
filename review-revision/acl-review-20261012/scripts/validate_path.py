import csv,sys,numpy as np
from common import *
saved={}
for x in csv.DictReader(open(ROOT/'outputs/tolerance-sensitivity/stop_records.csv')):
    if x['method']=='reference_priority': saved[(x['dataset'],x['aggregator'],int(x['split']),float(x['q']),x['tau'])]=int(x['queries'])
bad=0;n=0
for panel in PANELS:
  for agg in ['mean','median']:
    for rep,q in [(0,.05),(7,.10),(3,.30)]:
      c=instance(panel,agg,rep,q);path=reference_path(c);T=c['T']
      def gap(t,c=c,path=path):
          low=np.zeros(c['m'],np.int64);up=T*c['lp'].copy()
          for i,r in path[:t]:
              f=c['truth'][i,r];low[i]+=f;up[i]-=c['lp'][i]-f
          return capacity(low,c['budget'])-capacity(up,c['budget'])
      for tau,eps in [('0',0),('1/50',c['epsilon'])]:
          mine=first_stop(len(path),gap,eps);ref=saved.get((panel,agg,rep,q,tau))
          n+=1;bad+=mine!=ref
          if mine!=ref: print('MISMATCH',panel,agg,rep,q,tau,mine,ref)
print('checked',n,'mismatch',bad)

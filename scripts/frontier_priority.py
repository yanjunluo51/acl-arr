"""Visible-information acquisition towards safety and exclusion deficits.

The selector sees caps, reference predictions and revealed history only.
Integer certificates and query callback are separate from its utility.
"""
import numpy as np
from numba import njit

@njit(cache=True)
def cap_hist(h, budget):
    count=h[0];left=budget
    for v in range(1,len(h)):
        take=min(h[v],left//v);count+=take;left-=take*v
        if take<h[v]:break
    return count

@njit(cache=True)
def choose(caps,predicted,known,lower,upper,lh,uh,budget,mode):
    m,T=predicted.shape
    vl,vh=cap_hist(uh,budget),cap_hist(lh,budget)
    estimate=lower*1000000000000
    for i in range(m):
        for r in range(T):
            if not known[i,r]:estimate[i]+=predicted[i,r]
    order=np.argsort(estimate,kind='mergesort')
    total=0;guess=0
    for i in order:
        if total+estimate[i]>budget*1000000000000:break
        total+=estimate[i];guess+=1
    target=min(vh,max(vl+1,guess))
    safe=np.zeros(m,np.bool_);need_s=-budget
    for j in range(target):safe[order[j]]=True;need_s+=upper[order[j]]
    threshold=0;need_e=0
    if target<m:
        threshold=(estimate[order[target]]+999999999999)//1000000000000
        need_e=budget+1-(target+1)*threshold
        for i in range(m):need_e+=max(0,threshold-lower[i])
    best=-1;bi=-1;br=-1
    for i in range(m):
        for r in range(T):
            if known[i,r]:continue
            f=predicted[i,r]/1000000000000.0;score=0.
            if mode!=2 and safe[i] and need_s>0:score+=(caps[i]-f)/need_s
            if mode!=1 and need_e>0:score+=min(f,max(0,threshold-lower[i]))/need_e
            tick=int(np.rint(score*1000000000000.0))
            if tick>best:best=tick;bi=i;br=r
    if best<=0:
        # A null predicted marginal cannot stop a deterministic certificate.
        width=-1
        for i in range(m):
            if upper[i]-lower[i]>width:
                for r in range(T):
                    if not known[i,r]:width=upper[i]-lower[i];bi=i;br=r;break
    return bi,br

def acquire(caps,prior,budget,epsilon,query,mode='joint'):
    caps=np.asarray(caps,np.int64);prior=np.asarray(prior,float)
    m,T=prior.shape
    assert m==len(caps) and all(caps>0)
    predicted=np.rint(np.clip(prior,0,caps[:,None])*10**12).astype(np.int64)
    known=np.zeros((m,T),bool);lower=np.zeros(m,np.int64);upper=T*caps.copy()
    limit=int(T*max(caps,default=0));lh=np.zeros(limit+1,np.int64);uh=lh.copy()
    lh[0]=m
    for v in upper:uh[v]+=1
    trace=[];stops={};variant={'joint':0,'safety':1,'exclusion':2}[mode]
    while True:
        vl,vh=int(cap_hist(uh,budget)),int(cap_hist(lh,budget));gap=vh-vl
        for name,eps in [('primary',epsilon),('exact',0)]:
            if name not in stops and gap<=eps:
                stops[name]=dict(queries=len(trace),V_lower=vl,V_upper=vh,gap=gap)
        if gap==0:break
        i,r=map(int,choose(caps,predicted,known,lower,upper,lh,uh,budget,variant))
        assert i>=0 and r>=0 and not known[i,r]
        f=int(query(i,r));assert 0<=f<=caps[i]
        lh[lower[i]]-=1;uh[upper[i]]-=1
        lower[i]+=f;upper[i]-=caps[i]-f
        lh[lower[i]]+=1;uh[upper[i]]+=1;known[i,r]=True
        trace.append([i,r,f])
    return dict(mode=mode,trace=trace,stops=stops)

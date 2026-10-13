"""WMT24 acquisition with explicitly fixed-point reference priorities.

Only the heuristic ordering is quantized; observed costs, budgets, frontiers and
masks retain exact integer arithmetic. Original panel implementation is intact.
"""
import heapq,math
import numpy as np
from query_selection import prefix
from review_accelerated import capacities
from review_kernels import mean_flips

def solve_multi_quantized(base,selected,p,prior,threshold,agg,T,budgets,tie,method,seed,query,checkpoints,epsilon,priority_scale=10**12):
    assert isinstance(priority_scale,int) and 0<priority_scale<=10**12
    ids=np.flatnonzero(selected & (p>0));free=int(np.sum(selected & (p==0)))
    lp=p[ids];m=len(ids);total=m*T;nb=len(budgets)
    lower=np.zeros(m,dtype=np.int64);upper=T*lp.copy();known=np.zeros((m,T),dtype=bool)
    estimate=np.rint(prior[ids]*priority_scale).astype(np.int64);size=T*int(p.max(initial=0))+1
    lh=np.bincount(lower,minlength=size);uh=np.bincount(upper,minlength=size)
    targets=sorted(set(math.ceil(v*total) for v in checkpoints)|{total})
    states=[[] for _ in budgets];tolerant=[None]*nb;exact=[None]*nb;trace=[]
    candidates=np.arange(T)
    if method=='reference_priority':
        candidate_order=[np.lexsort((candidates,estimate[i])) for i in range(m)]
        heap=[(int(np.sum(estimate[i])),int(tie[ids[i]]),i) for i in range(m)]
    elif method=='largest_width':heap=[(-int(upper[i]),int(tie[ids[i]]),i) for i in range(m)]
    else:heap=[]
    heapq.heapify(heap);nseen=np.zeros(m,dtype=int)
    fixed_rows=np.argsort(tie[ids]);random_order=np.random.default_rng(seed).permutation(total)

    def snapshot(a,vlo,vhi):
        mask=(p==0).copy();keep=prefix(upper,int(budgets[a]),tie[ids]);mask[ids[keep]]=True
        return {'queries':len(trace),'V_lower':int(vlo),'V_upper':int(vhi),'gap':int(vhi-vlo),
                'mask':mask.tolist(),'upper_selected_cost':int(upper[keep].sum())}

    for step in range(total+1):
        vlo=free+capacities(uh,budgets);vhi=free+capacities(lh,budgets);gap=vhi-vlo
        for a in range(nb):
            if exact[a] is not None:continue
            save=step in targets or (tolerant[a] is None and gap[a]<=epsilon) or gap[a]==0
            if not save:continue
            st=snapshot(a,vlo[a],vhi[a])
            if tolerant[a] is None and st['gap']<=epsilon:tolerant[a]=st
            if gap[a]==0:exact[a]=st
            if step in targets:states[a].append(st)
        if all(s is not None for s in exact):break
        assert step<total
        if method=='fixed':i=int(fixed_rows[step//T]);c=step%T
        elif method=='random':i,c=divmod(int(random_order[step]),T)
        else:
            _,_,i=heapq.heappop(heap)
            c=int(candidate_order[i][nseen[i]]) if method=='reference_priority' else int(nseen[i])
        assert not known[i,c]
        item=int(ids[i]);score=query(c,item)
        f=int(lp[i]) if agg=='median' and score<threshold else (0 if agg=='median' else mean_flips(base[:,item],score,threshold))
        assert 0<=f<=lp[i]
        lh[lower[i]]-=1;uh[upper[i]]-=1
        lower[i]+=f;upper[i]-=lp[i]-f;lh[lower[i]]+=1;uh[upper[i]]+=1
        known[i,c]=True;nseen[i]+=1;trace.append([c,item,f])
        if method in ('reference_priority','largest_width') and nseen[i]<T:
            key=int(lower[i])*priority_scale+int(np.sum(np.where(known[i],0,estimate[i]))) if method=='reference_priority' else -int(upper[i]-lower[i])
            heapq.heappush(heap,(key,int(tie[item]),i))
    for a in range(nb):
        assert tolerant[a] is not None and exact[a] is not None
        seen={s['queries'] for s in states[a]}
        for target in targets:
            if target not in seen:states[a].append({**exact[a],'budget_checkpoint_queries':target})
    return trace,states,tolerant,exact


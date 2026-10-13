"""Best union among all separately optimal safety/exclusion entry witnesses.

Offline true contributions, unit-cost additional entries, fixed observed history.
The outcome model aligns identical contributions within each row. An independent
small-batch model uses binary entries and enumerates row subsets, no threshold.
"""
import itertools
import math
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from joint_certificates import capacity


def union_certificate(rows, caps, budget, epsilon=0, observed=None,
                      seconds=120, independent=False, presolve=True, entry_counts=False):
    start = time.perf_counter()
    rows = [list(map(int, row)) for row in rows]
    caps = list(map(int, caps))
    observed = [0]*len(rows) if observed is None else list(map(int, observed))
    T = len(rows[0]) if rows else 0
    assert budget >= 0 and epsilon >= 0 and int(epsilon) == epsilon
    assert len(rows) == len(caps) == len(observed)
    assert all(len(row) == T and all(0 <= v <= p for v in row)
               for row, p in zip(rows, caps))
    ids = [i for i, p in enumerate(caps) if p > 0]
    rrows, pcaps, known = [rows[i] for i in ids], [caps[i] for i in ids], [observed[i] for i in ids]
    m = len(ids)
    assert not independent or m <= 4
    lo = [sum(v for r, v in enumerate(row) if o >> r & 1) for row, o in zip(rrows, known)]
    hi = [a+(T-bin(o).count('1'))*p for a, o, p in zip(lo, known, pcaps)]
    L = capacity(list(map(sum, rrows)), budget)
    cells, candidates = [], []
    for i, row in enumerate(rrows):
        values = {}
        for r, v in enumerate(row):
            if not known[i] >> r & 1:
                values.setdefault((r if independent or entry_counts else v), []).append(r)
        for _, rr in sorted(values.items()):
            cells.append((i, row[rr[0]]))
            candidates.append(rr)
    mult = list(map(len, candidates))
    calls = []

    def solve(s, mode, aopt=None, bopt=None):
        safety = mode != 'exclusion'
        exclusion = mode != 'safety' and s+epsilon+1 <= m
        if not safety and not exclusion:
            return dict(proven=True, value=0, query=[0]*len(cells), status=0)
        n = 0
        def variables(count):
            nonlocal n
            v = list(range(n, n+count)); n += count
            return v
        aa = variables(len(cells)) if safety else []
        bb = variables(len(cells)) if exclusion else []
        uu = variables(len(cells)) if mode == 'union' else []
        if safety:
            yy = variables(len(list(itertools.combinations(range(m), s)))) if independent else variables(m)
            zz = {} if independent else {g:variables(1)[0] for g,(i,v) in enumerate(cells) if pcaps[i] > v}
        else:
            yy, zz = [], {}
        ww = variables(m) if exclusion and not independent else []
        tt = variables(1)[0] if exclusion and not independent else None
        if n == 0:
            return dict(proven=True,value=0,query=[],A=[],B=[],status=0)
        objective = np.zeros(n); integer = np.zeros(n); low = np.zeros(n); up = np.ones(n)
        for v in aa+bb+uu:
            integer[v] = 1
        for vv in [aa,bb,uu]:
            if vv: up[vv] = mult
        integer[yy] = 1
        if zz:
            for g,v in zz.items(): up[v] = mult[g]
        if tt is not None:
            integer[tt] = 1; up[tt] = max(map(sum, rrows), default=0)
            up[ww] = T*max(pcaps, default=0)
        objective[uu if mode == 'union' else aa if safety else bb] = 1
        rr, cc, val, lower, upper = [], [], [], [], []
        def con(coef, lb=-np.inf, ub=np.inf):
            k = len(lower)
            for v,c in coef.items():
                if c: rr.append(k);cc.append(v);val.append(c)
            lower.append(lb);upper.append(ub)
        if safety and independent:
            subsets = list(itertools.combinations(range(m),s))
            con({y:1 for y in yy},1,1)
            for y, subset in zip(yy,subsets):
                need = max(0,sum(hi[i] for i in subset)-budget)
                coef = {aa[g]:pcaps[i]-v for g,(i,v) in enumerate(cells) if i in subset}
                coef[y] = -need; con(coef,lb=0)
        elif safety:
            con({y:1 for y in yy},s,s)
            coef = {y:hi[i] for i,y in enumerate(yy)}
            for g,z in zz.items():
                i,v = cells[g];coef[z] = -(pcaps[i]-v)
                con({z:1,aa[g]:-1},ub=0)
                con({z:1,yy[i]:-mult[g]},ub=0)
                con({z:1,aa[g]:-1,yy[i]:-mult[g]},lb=-mult[g])
            con(coef,ub=budget)
        if exclusion and independent:
            for subset in itertools.combinations(range(m),s+epsilon+1):
                con({bb[g]:v for g,(i,v) in enumerate(cells) if i in subset},
                    lb=budget+1-sum(lo[i] for i in subset))
        elif exclusion:
            coef = {tt:s+epsilon+1};coef.update({w:-1 for w in ww});con(coef,lb=budget+1)
            for i,w in enumerate(ww):
                coef = {w:1,tt:-1};coef.update({bb[g]:v for g,(j,v) in enumerate(cells) if i==j})
                con(coef,lb=-lo[i])
        if mode == 'union':
            con({a:1 for a in aa},aopt,aopt)
            if bb: con({b:1 for b in bb},bopt,bopt)
            else: assert bopt==0
            for g,u in enumerate(uu):
                con({u:1,aa[g]:-1},lb=0)
                if bb: con({u:1,bb[g]:-1},lb=0)
        matrix = coo_matrix((val,(rr,cc)),shape=(len(lower),n)).tocsc()
        result = milp(objective,integrality=integer,bounds=Bounds(low,up),
                      constraints=LinearConstraint(matrix,np.array(lower),np.array(upper)),
                      options={'mip_rel_gap':0.,'time_limit':seconds,'presolve':presolve})
        meta = dict(target=s,mode=mode,status=int(result.status),message=result.message,
                    optimality_gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None,
                    dual_bound=float(result.mip_dual_bound) if getattr(result,'mip_dual_bound',None) is not None else None,
                    variables=n,constraints=len(lower),presolve=presolve)
        calls.append(meta)
        if result.x is None: return dict(proven=False,value=None,status=int(result.status))
        av = [int(round(result.x[v])) for v in aa] if aa else [0]*len(cells)
        bv = [int(round(result.x[v])) for v in bb] if bb else [0]*len(cells)
        query = [max(a,b) for a,b in zip(av,bv)] if mode=='union' else av if safety else bv
        alower,aupper = lo.copy(),hi.copy(); blower=lo.copy()
        for g,(i,v) in enumerate(cells):
            assert 0<=av[g]<=mult[g] and 0<=bv[g]<=mult[g]
            aupper[i]-=av[g]*(pcaps[i]-v);blower[i]+=bv[g]*v
        if safety: assert capacity(aupper,budget)>=s
        if exclusion: assert capacity(blower,budget)<=s+epsilon
        if mode=='union': assert sum(av)==aopt and sum(bv)==bopt
        value = sum(query)
        # A time-limited incumbent may leave slack in the union epigraph.
        # Its actual A|B is feasible and no larger than the solver objective.
        # Only an optimal incumbent must make these two costs equal.
        solver_value = float(result.fun)
        assert abs(math.fsum(float(objective[v])*float(result.x[v])
                             for v in np.flatnonzero(objective))-solver_value) < 1e-5
        assert solver_value >= value-1e-5
        if mode != 'union':
            assert abs(solver_value-value) < 1e-5
        objective_consistent = abs(solver_value-value) < 1e-5
        invalid_optimum = result.status == 0 and not objective_consistent
        meta.update(solver_objective=solver_value,
                    feasible_witness_cost=value,
                    union_epigraph_slack=solver_value-value,
                    numerical_optimality_accepted=bool(result.status==0 and objective_consistent))
        if invalid_optimum:
            # An integer feasible union below a claimed optimum contradicts the
            # solver bound. Preserve it as an upper bound, never as a minimum.
            meta['rejected_dual_bound'] = meta['dual_bound']
            meta['dual_bound'] = None
            meta['validation_status'] = 'REJECTED_OPTIMAL_BOUND_BY_FEASIBLE_UNION'
        return dict(proven=bool(result.status==0 and objective_consistent),
                    value=value,A=av,B=bv,query=query,
                    status=4 if invalid_optimum else int(result.status))

    best=None; targets=[]
    for s in range(max(0,L-epsilon),L+1):
        a,b=solve(s,'safety'),solve(s,'exclusion')
        if not a['proven'] or not b['proven']:
            targets.append(dict(target=s,component_status='UNRESOLVED'));continue
        u=solve(s,'union',a['value'],b['value'])
        target=dict(target=s,safety_minimum=a['value'],exclusion_minimum=b['value'],
                    union_minimum=u['value'],proven=u['proven'])
        targets.append(target)
        if u['value'] is not None and (best is None or u['value']<best['value']):best=dict(u,target=s)
    proven=bool(best is not None and all(x.get('proven',False) for x in targets))
    if best is None:return dict(status='UNRESOLVED',targets=targets,solver_calls=calls,seconds=time.perf_counter()-start)
    def mask(q):
        return sum(1<<(ids[i]*T+r) for (i,_),rr,v in zip(cells,candidates,q) for r in rr[:v])
    A,B=mask(best['A']),mask(best['B']);U=A|B
    low,upper=[],[]
    for i,(row,p,o) in enumerate(zip(rows,caps,observed)):
        q=(U>>(i*T))&((1<<T)-1);assert not q&o;observed_q=q|o
        l=sum(v for r,v in enumerate(row) if observed_q>>r&1)
        low.append(l);upper.append(l+(T-bin(observed_q).count('1'))*p)
    kept=[];left=budget
    for i in sorted(range(len(rows)),key=lambda i:(upper[i],i)):
        if upper[i]>left:break
        kept.append(i);left-=upper[i]
    assert capacity(low,budget)-capacity(upper,budget)<=epsilon
    assert bin(U).count('1')==best['value']
    return dict(status='OPTIMAL' if proven else 'UNRESOLVED', union_minimum=best['value'],
                split_minimum=min((x['safety_minimum']+x['exclusion_minimum'] for x in targets if x.get('proven')),default=None),
                safety_mask=A,exclusion_mask=B,union_mask=U,safe_mask=sum(1<<i for i in kept),
                safe_target=best['target'],targets=targets,solver_calls=calls,
                seconds=time.perf_counter()-start,independent_subset_model=independent,
                entry_variables=bool(independent or entry_counts))

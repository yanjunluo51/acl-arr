"""Integer witness/accounting checks; no scores or solver needed."""
import json,csv,hashlib
from pathlib import Path
import sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
from check_deduplicated_source_bindings import validate_sources
def capacity(cost,b):
    left=b;n=0
    for v in sorted(cost):
        if v>left:break
        left-=v;n+=1
    return n

def key(x):return tuple(x[k] for k in ['scope','dataset','split','q','history','epsilon'])
def witness(case,r):
    T=case['T'];rows=case['rows'];caps=case['caps'];known=case['observed'];free=sum(p==0 for p in caps)
    for name in ['union_mask','safety_mask','exclusion_mask']:
        assert type(r[name]) is int and 0<=r[name]<1<<(len(rows)*T),(name,'invalid entry mask')
    assert type(r['safe_mask']) is int and 0<=r['safe_mask']<1<<len(rows),'invalid returned row mask'
    active=sum(p>0 for p in caps)
    L=capacity(list(map(sum,rows)),case['budget'])-free
    expected_targets=list(range(max(0,L-case['epsilon']),L+1))
    assert sorted(t['target'] for t in r['targets'])==expected_targets,'incomplete or duplicate safe-target range'
    calls=[(c['target'],c['mode']) for c in r['solver_calls']]
    assert len(calls)==len(set(calls)) and all(t in expected_targets and m in ['safety','exclusion','union'] for t,m in calls),'invalid solver-call coverage'
    for t in r['targets']:
        for mode,field in [('safety','safety_minimum'),('exclusion','exclusion_minimum'),('union','union_minimum')]:
            assert type(t[field]) is int and t[field]>=0
            if t[field]>0:assert (t['target'],mode) in calls,'positive minimum without solver receipt'
        if t['target']+case['epsilon']+1>active:assert t['exclusion_minimum']==0
    assert r['union_mask']==r['safety_mask']|r['exclusion_mask']
    assert bin(r['union_mask']).count('1')==r['union_minimum']
    target=next(x for x in r['targets'] if x['target']==r['safe_target'])
    assert bin(r['safety_mask']).count('1')==target['safety_minimum']
    assert bin(r['exclusion_mask']).count('1')==target['exclusion_minimum']
    def bounds(mask):
        lower=[];upper=[]
        assert mask>>(len(rows)*T)==0
        for i,(row,p,o) in enumerate(zip(rows,caps,known)):
            q=(mask>>(i*T))&((1<<T)-1);assert not q&o
            merged=q|o;lo=sum(v for a,v in enumerate(row) if merged>>a&1)
            lower.append(lo);upper.append(lo+(T-bin(merged).count('1'))*p)
        return lower,upper
    _,a=bounds(r['safety_mask']);b,_=bounds(r['exclusion_mask']);lo,up=bounds(r['union_mask'])
    assert capacity(a,case['budget'])>=r['safe_target']+free
    assert capacity(b,case['budget'])<=r['safe_target']+free+case['epsilon']
    assert capacity(lo,case['budget'])-capacity(up,case['budget'])<=case['epsilon']
    assert sum(up[i] for i in range(len(up)) if r['safe_mask']>>i&1)<=case['budget']
    assert bin(r['safe_mask']).count('1')==capacity(up,case['budget']),'returned mask does not realize safe capacity'
    assert r['union_minimum']==min(x['union_minimum'] for x in r['targets'])
    assert r['split_minimum']==min(x['safety_minimum']+x['exclusion_minimum'] for x in r['targets'])
    assert all(x['proven'] for x in r['targets'])
    assert all(x['status']==0 and 0<=x['optimality_gap']<1e-10 for x in r['solver_calls'])
    for c in r['solver_calls']:
        if c['mode']=='union':v=next(t['union_minimum'] for t in r['targets'] if t['target']==c['target'])
        else:v=next(t[c['mode']+'_minimum'] for t in r['targets'] if t['target']==c['target'])
        assert abs(c['dual_bound']-v)<1e-6

def audit(root,write=False):
    out=root/'outputs/deduplicated-evidence';records=[json.loads(s) for s in (out/'records.jsonl').open()]
    assert len(records)==len({key(x) for x in records})==3936
    validate_sources(root,records)
    index={key(x):x for x in records};unresolved=sum(x['result']['status']=='UNRESOLVED' for x in records)
    retries=[json.loads(s) for s in (out/'retry-records.jsonl').open()]
    for r in retries:
        k=tuple(r['primary_key']);assert index[k]['result']['status']=='UNRESOLVED'
        value=dict(r['result'],independent=index[k]['result']['independent']);index[k]=dict(index[k],result=value)
    full=[json.loads(s) for s in (out/'full-entry-check.jsonl').open()];assert len(full)==4
    full_unresolved=sum(r['result']['status']!='OPTIMAL' for r in full)
    full_index={tuple(r['primary_key']):r for r in full}
    full_retries=[json.loads(s) for s in (out/'full-entry-retry.jsonl').open()]
    for r in full_retries:
        assert full_index[tuple(r['primary_key'])]['result']['status']!='OPTIMAL'
        full_index[tuple(r['primary_key'])]=r
    full=list(full_index.values())
    for r in full:
        c=index[tuple(r['primary_key'])];assert r['result']['status']=='OPTIMAL';witness(c,r['result'])
        assert r['result']['union_minimum']==c['result']['union_minimum']
        assert r['result']['split_minimum']==c['additive_minimum']
    fresh=smallfresh=0
    for x in index.values():
        r=x['result'];assert x['joint_minimum']<=r['union_minimum']<=x['additive_minimum']
        if x['mode']=='bound_sandwich':assert x['joint_minimum']==x['additive_minimum']==r['union_minimum']
        else:
            fresh+=1;assert r['status']=='OPTIMAL';witness(x,r);assert r['split_minimum']==x['additive_minimum']
            if x['scope']=='small':
                smallfresh+=1;other=r['independent'];assert other['status']=='OPTIMAL';witness(x,other)
                assert other['union_minimum']==r['union_minimum'] and other['split_minimum']==r['split_minimum']
    assert fresh==392 and smallfresh==388
    groups={}
    for x in index.values():
        groups.setdefault((x['scope'],x['history'],x['epsilon']),[]).append(x)
    summaries=[]
    for k,g in sorted(groups.items()):
        summaries.append(dict(zip(['scope','history','epsilon'],k),instances=len(g),
            joint_sum=sum(x['joint_minimum'] for x in g),union_sum=sum(x['result']['union_minimum'] for x in g),
            additive_sum=sum(x['additive_minimum'] for x in g),
            joint_below_union=sum(x['joint_minimum']<x['result']['union_minimum'] for x in g),
            double_count_reduction=sum(x['additive_minimum']-x['result']['union_minimum'] for x in g),
            genuine_joint_reduction=sum(x['result']['union_minimum']-x['joint_minimum'] for x in g),
            fresh_optimized=sum(x['mode']=='fresh_optimization' for x in g)))
    result=dict(status='PASS_INTEGER_DEDUPLICATED_EVIDENCE_AUDIT',records=3936,
                inferred_equalities=3544,fresh_pairs=392,small_independent_pairs=388,
                full_entry_pairs=4,primary_unresolved=unresolved,append_only_closures=len(retries),
                full_entry_primary_unresolved=full_unresolved,full_entry_append_only_closures=len(full_retries),
                backend_exhaustive_cases=160,summaries=summaries,
                all_component_ties_optimized=True,human_proof_certified=False,new_model_inference=False)
    if write:
        (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
        with (out/'summary.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    return result,list(index.values())
if __name__=='__main__':
    r,_=audit(Path(__file__).resolve().parents[1],True);print(json.dumps(r,indent=2))

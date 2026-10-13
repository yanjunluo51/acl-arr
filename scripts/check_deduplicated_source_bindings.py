"""Standard-library linkage of each deduplicated task to its frozen sources."""
import json
from pathlib import Path
import sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
FIELDS=('scope','dataset','split','q','history','epsilon','rows','caps','observed','budget','N','k','T','joint_minimum','additive_minimum')
def key(r):return tuple(r[k] for k in ('scope','dataset','split','q','history','epsilon'))
def validate_sources(root,records):
    expected={}
    def add(r):
        k=key(r);assert k not in expected,('duplicate frozen source',k);expected[k]=r
    for line in (root/'outputs/joint-certificates/instances.jsonl').open():
        instance=json.loads(line)
        if instance['key'][1]!='mean':continue
        for r in instance['records']:
            assert (r['dataset'],r['aggregator'],r['split'],r['q'])==tuple(instance['key'])
            add(dict(scope='small',dataset=r['dataset'],split=r['split'],q=r['q'],history=r['history'],epsilon=r['epsilon'],rows=instance['flips'],caps=instance['caps'],observed=instance['observed'][r['history']],budget=r['budget'],N=r['N'],k=r['k'],T=r['T'],joint_minimum=r['queries'],additive_minimum=r['split_queries']))
    full={}
    for line in (root/'outputs/outcome-joint-scale/records.jsonl').open():
        r=json.loads(line);k=(r['dataset'],r['split'],r['q'],r['requested_size']);assert k not in full;full[k]=r
    for line in (root/'outputs/outcome-joint-scale/retry-records.jsonl').open():
        r=json.loads(line);k=tuple(r['primary_key']);assert k in full
        if r['joint_optimal'] and r['separated_optimal']:full[k]=dict(full[k],**r)
    for r in full.values():
        if r['requested_size']!='full':continue
        assert r['joint_optimal'] and r['separated_optimal'] and r['epsilon']==0 and r['history']=='empty'
        add(dict(scope='full',dataset=r['dataset'],split=r['split'],q=r['q'],history='empty',epsilon=0,rows=r['rows'],caps=r['caps'],observed=r['observed'],budget=r['budget'],N=r['N'],k=r['k'],T=r['T'],joint_minimum=r['queries'],additive_minimum=r['split_queries']))
    assert len(expected)==3936 and sum(k[0]=='full' for k in expected)==96
    actual={key(r):r for r in records};assert len(actual)==len(records)==3936 and set(actual)==set(expected)
    for k,r in actual.items():
        e=expected[k]
        for f in FIELDS:assert type(r[f]) is type(e[f]) and r[f]==e[f],('source mismatch',k,f)
        assert r['mode']==('bound_sandwich' if r['joint_minimum']==r['additive_minimum'] else 'fresh_optimization')
        assert type(r['T']) is int and r['T']>=1 and type(r['budget']) is int and r['budget']>=0
        assert type(r['epsilon']) is int and r['epsilon']>=0
        assert len(r['rows'])==len(r['caps'])==len(r['observed'])<=r['N']
        for row,p,o in zip(r['rows'],r['caps'],r['observed']):
            assert type(p) is int and p>=0 and type(o) is int and 0<=o<1<<r['T']
            assert len(row)==r['T'] and all(type(v) is int and 0<=v<=p for v in row)
    return dict(status='PASS_FROZEN_SOURCE_BINDINGS',records=3936,small=3840,full=96,fields_checked_per_record=len(FIELDS),original_sources_modified=False)
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];records=[json.loads(s) for s in (root/'outputs/deduplicated-evidence/records.jsonl').open()]
    print(json.dumps(validate_sources(root,records),indent=2))

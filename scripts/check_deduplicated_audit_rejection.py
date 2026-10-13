"""Ensure the audit rejects corrupted witness claims and source links."""
import copy,json
from pathlib import Path
import sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
from audit_deduplicated_evidence import audit,witness
from check_deduplicated_source_bindings import validate_sources
ROOT=Path(__file__).resolve().parents[1]
def main():
    result,cases=audit(ROOT,False)
    a=next(c for c in cases if c['mode']=='fresh_optimization' and c['result']['safe_mask'] and len(c['result']['targets'])>1)
    accepted=[];rejected=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):rejected.append(name)
        else:accepted.append(name)
    r=copy.deepcopy(a['result']);r['safe_mask']=0;reject('empty_returned_mask',lambda:witness(a,r))
    r=copy.deepcopy(a['result']);r['safe_mask']|=1<<len(a['rows']);reject('out_of_range_returned_row',lambda:witness(a,r))
    r=copy.deepcopy(a['result']);target=next(t['target'] for t in r['targets'] if t['target']!=r['safe_target']);r['targets']=[t for t in r['targets'] if t['target']!=target];r['solver_calls']=[c for c in r['solver_calls'] if c['target']!=target];reject('omitted_target_and_receipts',lambda:witness(a,r))
    r=copy.deepcopy(a['result']);r['targets'].append(copy.deepcopy(r['targets'][0]));reject('duplicated_target',lambda:witness(a,r))
    r=copy.deepcopy(a['result']);r['solver_calls']=[];reject('positive_minimum_without_receipts',lambda:witness(a,r))
    r=copy.deepcopy(a['result']);r['union_mask']=-1;reject('negative_entry_mask',lambda:witness(a,r))
    records=[json.loads(s) for s in (ROOT/'outputs/deduplicated-evidence/records.jsonl').open()]
    for field in ['budget','joint_minimum','observed','rows']:
        altered=copy.deepcopy(records);c=altered[0]
        if field in ['budget','joint_minimum']:c[field]+=1
        elif field=='observed':c[field][0]^=1
        else:c[field][0][0]+=1
        reject('changed_source_'+field,lambda:validate_sources(ROOT,altered))
    assert not accepted and len(rejected)==10,(accepted,rejected)
    print(json.dumps(dict(status='PASS_CORRUPTED_EVIDENCE_REJECTION',cases=10,rejected=rejected,actual_cases_preserved=True,current_result_summaries_unchanged=result==json.loads((ROOT/'outputs/deduplicated-evidence/audit.json').read_text())),indent=2))
if __name__=='__main__':main()

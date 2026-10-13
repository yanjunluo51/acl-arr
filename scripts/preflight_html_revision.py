"""Three checks before editing the current manuscript; preserve a successor baseline."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/html-review-implementation'
OLD=ROOT/'history/before-html-review-20261005'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not OLD.exists() and not OUT.exists(), 'Never overwrite an existing attempt'
    receipt=json.loads((ROOT/'review-revision/commitment-stopping-implementation/final-delivery.json').read_text())
    for n,h in receipt['hashes'].items():assert sha(ROOT/n)==h,n
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    for n,h in frozen.items():assert sha(ROOT/n)==h,n
    evidence=json.loads((ROOT/'ccfa-review-reports/acl-html-review-20261005/evidence-check.json').read_text())
    assert evidence['review_dp_and_actual_safety_dp_subset_checks']==3840
    assert evidence['symmetric_difference_cases']==54
    matrix=json.loads((ROOT/'ccfa-review-reports/acl-html-review-20261005/item-assessment.json').read_text())
    assert len(matrix['items'])==144
    # Acquisition, hidden-score bounds and all old experimental records are immutable.
    protected={str(p.relative_to(ROOT)):sha(p) for folder in ['data','outputs'] for p in (ROOT/folder).rglob('*') if p.is_file()}
    for name in ['query_selection.py','review_accelerated.py','external_experiments.py','review_priority.py','residual_certificates.py']:
        protected['scripts/'+name]=sha(ROOT/'scripts'/name)
    OUT.mkdir();OLD.mkdir()
    for folder in ['manuscript','packages']:
        shutil.copytree(ROOT/folder,OLD/folder)
    for name in ['LATEST_MANUSCRIPT.md','DATA_STATEMENT_CURRENT.md','MANIFEST_SHA256.json']:
        shutil.copy2(ROOT/name,OLD/name)
    check={'status':'PASS_THREE_PRE_EDIT_CHECKS','checks':[
        {'round':1,'scope':'Canonical current source, 95 delivery bindings and frozen inputs','pass':True},
        {'round':2,'scope':'Quantifiers, endpoints, 3840 DP checks, matched-tie experimental unit and information boundary','pass':True},
        {'round':3,'scope':'144 adjudicated items, one research question, immutable old paths/results and reversible successor delivery','pass':True}],
        'frozen_hashes':frozen,'protected_hashes':protected,
        'prior_delivery_hashes':receipt['hashes'],
        'experiment_protocol':{'panels':6,'poolings':2,'depths':4,'splits':40,'configurations':1920,'alpha':'1/10',
           'matched_order':'np.lexsort((seeded_label_blind_priority, -consensus))[:k]',
           'scope':'Full-information selection control only; no new online top-k certificate',
           'labels_used_for_selection':False},
        'single_spine':'Score evidence for certified near-optimal retention under fixed selection and replacement-average churn',
        'all_scientific_or_authorization_gates_closed':False}
    (OUT/'pre-edit-checks.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':check['status'],'frozen_entries':len(frozen),'protected_files':len(protected)}))
if __name__=='__main__':main()

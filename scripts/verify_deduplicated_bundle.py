"""Portable current evidence verification; optional deterministic table replay."""
import argparse,ast,hashlib,json,subprocess,sys
from pathlib import Path
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
from verify_joint_scale_bundle import main as prior
from audit_deduplicated_evidence import audit

def main(root,manifest=True,replay=False,backend=False,rejection=False):
    root=root.resolve();old=prior(root,manifest,False,False);new,_=audit(root,False)
    expected=json.loads((root/'outputs/deduplicated-evidence/audit.json').read_text());assert expected==new
    if backend:
        subprocess.run([sys.executable,'scripts/check_deduplicated_backend.py'],cwd=root,check=True,stdout=sys.stderr)
    if rejection:
        subprocess.run([sys.executable,'scripts/check_deduplicated_audit_rejection.py'],cwd=root,check=True,stdout=sys.stderr)
    if replay:
        tree=ast.parse((root/'scripts/verify_interface_delivery.py').read_text())
        layers=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RENDERERS' for t in n.targets)))
        layers+=['render_nontrivial_certification.py','render_main10_editorial.py','render_html_revision.py','render_joint_revision.py','render_latest_sentence_review.py','render_joint_scale.py','render_deduplicated_revision.py']
        tables={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'manuscript/tables').glob('*.tex')}
        assert len(tables)==77
        for name in layers:subprocess.run([sys.executable,'scripts/'+name],cwd=root,check=True,stdout=sys.stderr)
        assert all(hashlib.sha256((root/'manuscript/tables'/n).read_bytes()).hexdigest()==h for n,h in tables.items())
    return dict(status='PASS_PORTABLE_DEDUPLICATED_SAVED_EVIDENCE',prior=old,deduplicated=new,
                tables_replayed=77 if replay else None,exhaustive_backend_replayed=backend,
                same_instance_source_fields_checked=15,all_safe_targets_and_returned_cardinality_checked=True,
                corrupted_evidence_cases_rechecked=10 if rejection else None,
                raw_score_arrays_required=False,new_model_inference=False,human_proof_certified=False,
                full_novelty_certified=False,complete_redistribution_authorized=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--author-live-check',action='store_true');p.add_argument('--replay-tables',action='store_true');p.add_argument('--check-backend',action='store_true');p.add_argument('--check-audit-rejection',action='store_true');a=p.parse_args()
    print(json.dumps(main(a.root,not a.author_live_check,a.replay_tables,a.check_backend,a.check_audit_rejection),indent=2))

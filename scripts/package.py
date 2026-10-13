"""Package the full review-evidence revision as private local preparation copies."""
from pathlib import Path
import hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    patterns=['data/*.json','paper/*.tex','paper/*.bib','paper/*.sty','paper/*.bst','paper/tables/*.tex',
              'outputs/query_*.json','outputs/*_cells.csv','outputs/review-analysis.json',
              'outputs/review-*/results.json','outputs/review-*/*_cells.csv','outputs/review-*/execution.json',
              'outputs/review-*/traces.jsonl.gz','outputs/review-score/decision-audit-input.json',
              'novelty-development/*.md','novelty-development/EXECUTION_PROTOCOL.json',
              'review-revision/*-protocol.json','review-revision/*-independent-audit.json',
              'review-revision/*-three-pass.json','review-revision/external-admission.json',
              'review-revision/external-source-audit.json','review-revision/accelerated-preflight.json',
              'review-revision/render-source-bindings.json','review-revision/visual-contract.md',
              'review-revision/qa-ledger.md','review-revision/claim-evidence.md','review-revision/review-response.md',
              'review-revision/numeric-repair.md',
              'review-revision/status.json','review-revision/logic-verdict.txt','review-revision/venue-policy.json','review-revision/prose-*-current.json',
              'review-revision/acquisition/official-hosting.json','ccfa-review-reports/score-inspection-acl-arr-review.md']
    files={p for pattern in patterns for p in ROOT.glob(pattern)}
    scripts=['analyze','query_selection','test_query_selection','query_analysis','render_query','fetch_inputs',
             'review_experiments','review_accelerated','review_kernels','external_experiments','prepare_external_panel',
             'score_comparison','sentinel_diagnostics','render_review','review_priority','test_review_priority','check_pdf','package']
    names=['scripts/'+s+'.py' for s in scripts]+['scripts/run_all.sh','scripts/build_paper.sh',
           'outputs/query_traces.jsonl.gz','paper/main.pdf','paper/query-frontiers.pdf','paper/query-frontiers.png','paper/query-frontiers.svg',
           'paper/review-budgets.pdf','paper/review-budgets.png','paper/review-budgets.svg',
           'visual-composer/visual-contract.md','visual-composer/qa-ledger.md',
           'README.md','DATA_STATEMENT.md','REVISION_REPORT.md','requirements.txt','requirements-checks.txt',
           'evidence/source-model-files.json','submission/audit_query_results.py','submission/audit_theory_and_claims.py',
           'submission/audit_review_results.py','submission/audit_review_parallel.py','submission/audit_score_comparison.py',
           'submission/audit_external_sources.py','submission/verify_current_package.py','submission/verify_repaired_package.py',
           'submission/theory-and-claims-audit.json','submission/current-status.json','submission/pdf-check.json',
           'submission/query-results-audit.json','submission/query-claim-evidence.md','submission/proof-review-current.md',
           'submission/reference-audit-current.json','submission/author-checklist-draft.md','submission/metadata-draft.json']
    files.update(ROOT/n for n in names)
    # Historical parent receipts remain history; they cannot certify this extension.
    replay=ROOT/'submission/review-clean-reproduction.json'
    if replay.exists():files.add(replay)
    repaired=ROOT/'submission/review-repaired-reproduction.json'
    if repaired.exists():files.add(repaired)
    for p in files:
        assert p.is_file(),p
        if p.suffix in {'.py','.sh','.tex','.bib','.md','.json','.txt'}:
            assert not re.search(r'/(?:Users|home)/[^/\s]+',p.read_text(errors='replace')),p
    manifest={p.relative_to(ROOT).as_posix():digest(p) for p in sorted(files)}
    (ROOT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n');files.add(ROOT/'MANIFEST_SHA256.json')
    packages=ROOT/'packages';packages.mkdir(exist_ok=True)
    for kind in ['software','data']:
        selected=[p for p in files if (p.relative_to(ROOT).parts[0]=='data')==(kind=='data')]
        with zipfile.ZipFile(packages/('ARR_'+kind+'_private_review.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(selected):z.write(p,p.relative_to(ROOT).as_posix())
        print(kind,len(selected),'files',flush=True)
    # ARR's published software limit is 200 MB. Complete traces stay in the
    # private local replay packet; submission preparation contains executable
    # sources, frozen protocols, documentation and compact reports.
    light=[p for p in files if p.name!='MANIFEST_SHA256.json' and (p.relative_to(ROOT).parts[0] in {'scripts','paper','evidence'} or p.parent==ROOT or (p.relative_to(ROOT).parts[0]=='review-revision' and (p.name.endswith('-protocol.json') or p.name.endswith('-independent-audit.json') or p.name in {'external-admission.json','external-source-audit.json','claim-evidence.md','render-source-bindings.json','numeric-repair.md','review-response.md','qa-ledger.md','status.json','logic-verdict.txt'})) or (p.relative_to(ROOT).parts[0]=='submission' and (p.suffix=='.py' or p.name in {'query-results-audit.json','pdf-check.json','reference-audit-current.json','current-status.json','review-clean-reproduction.json','review-repaired-reproduction.json'})) or p.relative_to(ROOT).as_posix()=='novelty-development/EXECUTION_PROTOCOL.json')]
    light_manifest={p.relative_to(ROOT).as_posix():digest(p) for p in sorted(light)}
    light_manifest.update({n:sha for n,sha in manifest.items() if n.startswith('data/')})
    dest=packages/'ARR_software_submission_preparation_private.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(light):z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST_SHA256.json',json.dumps(light_manifest,indent=2)+'\n')
    assert dest.stat().st_size<200_000_000
    assert (packages/'ARR_data_private_review.zip').stat().st_size<200_000_000
    print('Submission preparation software/data below 200 MB; neither uploaded or rights-cleared',flush=True)
    proof={p for p in files if p.relative_to(ROOT).parts[0] in {'paper','novelty-development'}}
    proof.update(ROOT/n for n in ['scripts/test_query_selection.py','scripts/query_selection.py','scripts/analyze.py',
                                 'submission/proof-review-current.md','submission/query-results-audit.json',
                                 'submission/theory-and-claims-audit.json','review-revision/claim-evidence.md',
                                 'submission/current-status.json','outputs/query_validation.json'])
    with zipfile.ZipFile(packages/'proof_review_current_private.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(proof):z.write(p,p.relative_to(ROOT).as_posix())
    print('manifest',len(manifest),'entries; private local copies, no rights clearance',flush=True)

if __name__=='__main__':main()

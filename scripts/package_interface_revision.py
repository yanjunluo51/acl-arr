"""Refresh the existing private archives with the five local clarifications."""
from pathlib import Path
import json, zipfile
from package_certificate_granularity import write_zip

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'history/before-interface-review'
OUT = ROOT / 'review-revision/interface-review-implementation'
DOCS = ['LATEST_MANUSCRIPT.md', 'LATEST_EXTERNAL_VERIFICATION.md', 'DATA_STATEMENT_CURRENT.md',
        'INTERFACE_REVIEW_REVISION_REPORT.md', 'REPRODUCTION_INTERFACE_REVIEW.md',
        'INTERFACE_REVIEW_SELF_CHECK.md']
SCRIPTS = ['render_interface_revision.py', 'check_interface_revision.py',
           'package_interface_revision.py', 'verify_interface_delivery.py']
META = ['review-revision/acquisition/official-hosting.json',
        'review-revision/external-admission.json', 'review-revision/external-source-audit.json']


def main():
    source, code = {}, {}
    with zipfile.ZipFile(OLD / 'manuscript/source_private.zip') as z:
        for name in z.namelist():
            if name == 'PACKAGE_CONTENTS_SHA256.json':
                continue
            p = ROOT / (name[5:] if name.startswith('ROOT/') else name)
            assert p.is_file(), name
            source[name] = (p, name)
    for n in DOCS:
        source['ROOT/'+n] = (ROOT/n, 'ROOT/'+n)
    for n in META:
        source[n] = (ROOT/n, n)
    with zipfile.ZipFile(OLD / 'packages/current_mapping_column_code_private.zip') as z:
        for name in z.namelist():
            if name == 'PACKAGE_CONTENTS_SHA256.json':
                continue
            p = ROOT / name; assert p.is_file(), name
            code[name] = (p, name)
    for p, name in source.values():
        real = str(p.relative_to(ROOT)); code[real] = (p, real)
    for n in SCRIPTS:
        name = 'scripts/'+n; code[name] = (ROOT/name, name)
    for n in ['pre-edit-checks.json', 'source-pdf-check.json', 'item-completion.json',
              'main-prose-check.json', 'appendix-prose-check.json', 'prose-review.json',
              'visual-check.json', 'manuscript.diff']:
        name = str((OUT/n).relative_to(ROOT)); code[name] = (ROOT/name, name)
    for n in ['REVIEW_ASSESSMENT.md', 'evidence-check.json']:
        name = 'ccfa-review-reports/interface-cutoff-quality-regret-review/'+n
        code[name] = (ROOT/name, name)
    for n in ['pre-fix-checks.json', 'independent-check.json', 'run_independent_check.py']:
        name = 'review-revision/interface-independent-selfcheck/'+n
        code[name] = (ROOT/name, name)
    assert not any(n.startswith('data/') or n.endswith('query_traces.jsonl.gz')
                   or n == 'outputs/review-external/traces.jsonl.gz'
                   or '/wmt23-official/' in n for n in code)
    ns = write_zip(ROOT / 'manuscript/source_private.zip', list(source.values()))
    nc = write_zip(ROOT / 'packages/current_mapping_column_code_private.zip', list(code.values()))
    print(json.dumps({'source_members': ns+1, 'code_members': nc+1,
                      'third_party_matrices_added': False}))


if __name__ == '__main__':
    main()

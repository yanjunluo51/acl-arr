"""Update canonical source/code archives without mutating historic receipts."""
from pathlib import Path
import hashlib
import json
import zipfile

from package_certificate_granularity import DOCS, write_zip

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'review-revision/four-point-implementation'


def main():
    docs = DOCS + ['FOUR_POINT_REVISION_REPORT.md', 'FOUR_POINT_SELF_CHECK.md',
                   'REPRODUCTION_FOUR_POINT_REVISION.md']
    source = []
    for p in (ROOT / 'manuscript').rglob('*'):
        if p.is_file() and p.suffix in ['.tex', '.bib', '.bst', '.sty', '.pdf', '.png', '.svg', '.sh']:
            source.append((p, str(p.relative_to(ROOT))))
    source += [(ROOT / n, 'ROOT/' + n) for n in docs]
    source_count = write_zip(ROOT / 'manuscript/source_private.zip', source)
    previous = ROOT / 'history/before-four-point-implementation/packages/current_mapping_column_code_private.zip'
    code = {}
    with zipfile.ZipFile(previous) as z:
        for name in z.namelist():
            if name == 'PACKAGE_CONTENTS_SHA256.json':
                continue
            p = ROOT / name
            assert p.is_file(), name
            code[name] = (p, name)
    code.update({str(p.relative_to(ROOT)): (p, str(p.relative_to(ROOT))) for p, _ in source})
    for n in ['scripts/check_four_point_revision.py', 'scripts/check_four_point_pdf.py',
              'scripts/package_four_point_revision.py']:
        code[n] = (ROOT / n, n)
    for n in ['precheck-three-pass.json', 'regression-check.json', 'pdf-check.json',
              'visual-check.json', 'english-edit-log.md']:
        p = OUT / n
        assert p.is_file(), p
        name = str(p.relative_to(ROOT)); code[name] = (p, name)
    code_count = write_zip(ROOT / 'packages/current_mapping_column_code_private.zip', list(code.values()))
    synthetic = ROOT / 'packages/synthetic_certificate_reproduction.zip'
    old_synthetic = ROOT / 'history/before-four-point-implementation/packages/synthetic_certificate_reproduction.zip'
    assert synthetic.read_bytes() == old_synthetic.read_bytes()
    result = {'status': 'PACKAGED_PENDING_CLEAN_VERIFICATION',
              'source_members': source_count + 1, 'code_members': code_count + 1,
              'synthetic_archive_byte_identical': True,
              'raw_third_party_score_matrices_included': False,
              'sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in [
                  'manuscript/source_private.zip', 'packages/current_mapping_column_code_private.zip',
                  'packages/synthetic_certificate_reproduction.zip']}}
    (OUT / 'package-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

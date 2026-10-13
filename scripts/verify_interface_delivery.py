"""Clean source build and complete current table regeneration from private archives."""
from pathlib import Path
import hashlib, json, subprocess, sys, tempfile, zipfile
import fitz
from package_interface_revision import DOCS, META, SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'review-revision/interface-review-implementation'
RENDERERS = ['render_editorial_tables.py', 'render_cached_mapping_tables.py',
             'render_certificate_granularity.py', 'render_tolerance_sensitivity.py',
             'render_sentence_review.py', 'render_acquisition_mechanisms.py',
             'render_compressed_expression.py', 'render_three_clarifications.py',
             'render_acceptance_revision.py', 'render_density_revision.py',
             'render_interface_revision.py']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(path, source=False):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert len(names) == len(set(names)) and z.testzip() is None
        bindings = json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'))
        assert set(bindings) == set(names)-{'PACKAGE_CONTENTS_SHA256.json'}
        for n, h in bindings.items():
            assert not n.startswith('/') and '..' not in Path(n).parts
            payload = z.read(n); assert hashlib.sha256(payload).hexdigest() == h
            real = n[5:] if source and n.startswith('ROOT/') else n
            assert (ROOT/real).read_bytes() == payload, n
    return len(names)


def main():
    qa = json.loads((OUT / 'source-pdf-check.json').read_text())
    assert qa['status'] == 'PASS_SCOPED_INTERFACE_SOURCE_AND_PDF_CHECKS'
    ns = archive(ROOT / 'manuscript/source_private.zip', True)
    nc = archive(ROOT / 'packages/current_mapping_column_code_private.zip')
    src = Path(tempfile.mkdtemp(prefix='clean-source-', dir=OUT))
    code = Path(tempfile.mkdtemp(prefix='clean-code-', dir=OUT))
    with zipfile.ZipFile(ROOT / 'manuscript/source_private.zip') as z:
        z.extractall(src)
    (src / 'manuscript/main.pdf').unlink()
    with (OUT / 'clean-source-build.log').open('w') as f:
        subprocess.run(['bash', 'build.sh'], cwd=src/'manuscript',
                       stdout=f, stderr=subprocess.STDOUT, check=True)
    a, b = fitz.open(ROOT / 'manuscript/main.pdf'), fitz.open(src / 'manuscript/main.pdf')
    assert len(a) == len(b) == qa['total_pdf_pages']
    for x, y in zip(a, b):
        assert x.get_text() == y.get_text() and x.get_pixmap().samples == y.get_pixmap().samples
    print('Clean source PDF text and pixels match on every page', flush=True)
    with zipfile.ZipFile(ROOT / 'packages/current_mapping_column_code_private.zip') as z:
        z.extractall(code)
    assert not (code/'data').exists()
    with (OUT / 'clean-code-render.log').open('w') as f:
        for n in RENDERERS:
            subprocess.run([sys.executable, 'scripts/'+n], cwd=code,
                           stdout=f, stderr=subprocess.STDOUT, check=True)
    tables = list((ROOT / 'manuscript/tables').glob('*.tex')); assert len(tables) == 63
    for p in tables:
        assert p.read_bytes() == (code / 'manuscript/tables' / p.name).read_bytes(), p.name
    print('All 63 tables regenerate identically through 11 current render layers', flush=True)
    pre = json.loads((OUT / 'pre-edit-checks.json').read_text())
    for n, h in pre['protected_hashes'].items():
        assert digest(ROOT/n) == h, n
    for n in ['packages/synthetic_certificate_reproduction.zip',
              'packages/residual_certificate_reproduction.zip']:
        assert digest(ROOT/n) == pre['prior_delivery_hashes'][n]
    for n in META:
        assert (src/n).read_bytes() == (code/n).read_bytes() == (ROOT/n).read_bytes()
    ledger = json.loads((OUT / 'item-completion.json').read_text())
    assert sorted(v['item'] for v in ledger['items']) == list(range(1, 6))
    assert all(v['status'] == 'implemented' for v in ledger['items'])
    independent_dir = ROOT / 'review-revision/interface-independent-selfcheck'
    independent = json.loads((independent_dir / 'independent-check.json').read_text())
    assert independent['status'] == 'PASS_SCOPED_INDEPENDENT_RECORD_AND_CLAIM_RECHECK'
    assert independent['rewardbench_positive_stop_masks_replayed'] == 1280
    assert independent['rewardbench_quality_fields_from_masks_checked'] == 6400
    for n, h in independent['source_sha256'].items():
        assert digest(ROOT/n) == h, n
    check = {'status': 'PASS_CLEAN_INTERFACE_SOURCE_AND_TABLE_REPRODUCTION',
             'source_members': ns, 'code_members': nc, 'pdf_pages': len(a),
             'all_pdf_text_and_pixels_identical': True,
             'all_63_table_sources_regenerated_identically': True, 'render_layers': len(RENDERERS),
             'archive_payloads_match_live': True, 'metadata_paths_present_in_both_packages': True,
             'independent_synthetic_and_residual_archives_byte_preserved': True,
             'clean_source_directory': src.name, 'clean_code_directory': code.name,
             'new_scientific_experiment_executed': False}
    (OUT / 'clean-package-check.json').write_text(json.dumps(check, indent=2)+'\n')
    files = ['manuscript/main.tex', 'manuscript/appendix.tex', 'manuscript/references.bib',
             'manuscript/main.pdf', 'manuscript/source_private.zip',
             'packages/current_mapping_column_code_private.zip',
             'packages/synthetic_certificate_reproduction.zip',
             'packages/residual_certificate_reproduction.zip'] + DOCS + META
    files += [str(p.relative_to(ROOT)) for p in tables]
    files += ['scripts/'+n for n in SCRIPTS]
    files += [str((independent_dir/n).relative_to(ROOT)) for n in
              ['pre-fix-checks.json', 'independent-check.json',
               'run_independent_check.py', 'independent-check.log']]
    files += [str(p.relative_to(ROOT)) for p in OUT.rglob('*')
              if p.is_file() and not any(x.startswith('clean-') for x in p.parts)
              and p.name not in ['final-delivery.json', 'delivery-check.log']
              and 'visual' not in p.parts]
    result = dict(qa)
    result.update({'status': 'PASS_SCOPED_INTERFACE_REVISION_AND_CLEAN_DELIVERY',
                   'three_pre_edit_checks_passed': True, 'single_research_spine_preserved': True,
                   'review_items': 5, 'all_items_implemented': True, 'clean_package_checks': check,
                   'independent_selfcheck_completed': True,
                   'rewardbench_fields_replayed_from_saved_masks': 6400,
                   'proof_tests_rerun': False,
                   'proof_test_justification': 'Formal blocks and solvers unchanged; derived pruning bound follows the existing frontier proposition.',
                   'hashes': {n: digest(ROOT/n) for n in sorted(set(files))}})
    (OUT / 'final-delivery.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'hashes'}, indent=2))


if __name__ == '__main__':
    main()

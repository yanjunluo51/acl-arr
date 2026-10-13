"""Full-tree checks for the five local edits; no scientific experiment is run."""
from pathlib import Path
import hashlib, itertools, json, math, re, statistics
import fitz
import numpy as np
from render_interface_revision import CONDITIONS, NAMES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'review-revision/interface-review-implementation'
OLD = ROOT / 'history/before-interface-review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_rows(path):
    return [[v.strip() for v in line.split(r'\\')[0].split('&')]
            for line in path.read_text().splitlines()
            if re.match(r'^(median|mean|en-de|en-es|ja-zh) &', line)]


def quality_check():
    x = json.loads((ROOT / 'outputs/query_metrics.json').read_text())
    a = json.loads((ROOT / 'outputs/query_analysis.json').read_text())
    e = json.loads((ROOT / 'outputs/review-external/results.json').read_text())
    query = {(r['aggregator'], r['q'], r['method'], r['stopping'], r['split']): r
             for r in x['query_records'] if r['dataset'] == 'RewardBench2'}
    rb = 0
    for r in a['quality_records']:
        if r['stopping'] != 'two_percent_gap':
            continue
        z = query[r['aggregator'], r['q'], r['method'], r['stopping'], r['split']]
        assert z['alpha'] == .1 and z['epsilon'] == math.ceil(.02*z['selected_count'])
        assert z['certificate_gap'] <= z['epsilon'] and r['K'] == z['returned_count']
        rb += 1
    expected = []
    for agg, q, method in itertools.product(['median', 'mean'], [.05, .1, .2, .3],
                                           ['fixed', 'random', 'largest_width', 'reference_priority']):
        rows = [r for r in a['quality_records']
                if (r['aggregator'], r['q'], r['method'], r['stopping'])
                == (agg, q, method, 'two_percent_gap')]
        assert len(rows) == 40 and {r['split'] for r in rows} == set(range(40))
        c = {k: statistics.fmean(r[k] for r in rows if r[k] is not None)
             for k in ['K', 'precision', 'same_K_score_precision', 'precision_delta']}
        cached = next(r for r in a['quality_cells']
                      if (r['aggregator'], r['q'], r['method'], r['stopping'])
                      == (agg, q, method, 'two_percent_gap'))
        assert cached['splits'] == 40
        assert all(c[k] == cached[k] for k in c)
        expected.append([agg, f'{q:.2f}', method.replace('_', r'\_'), f"{c['K']:.1f}",
                         f"{c['precision']:.3f}", f"{c['same_K_score_precision']:.3f}",
                         f"{c['precision_delta']:.4f}"])
    assert expected == table_rows(ROOT / 'manuscript/tables/query-quality.tex')
    wmt = 0
    def fmt(v, d):
        return f'{(0.0 if round(v, d) == 0 else v):.{d}f}'
    for agg in ['median', 'mean']:
        expected = []
        for lp, q in itertools.product(['en-de', 'en-es', 'ja-zh'], [.05, .1, .2, .3]):
            rows = [r for r in e['query_records']
                    if (r['dataset'], r['aggregator'], r['q'], r['method'], r['stopping'])
                    == ('WMT24-'+lp, agg, q, 'reference_priority', 'two_percent_gap')]
            assert len(rows) == 40
            for r in rows:
                assert r['alpha'] == .1 and r['epsilon'] == math.ceil(.02*r['selected_count'])
                assert r['certificate_gap'] <= r['epsilon']
            vals = [statistics.fmean(r[k] for r in rows if r[k] is not None)
                    for k in ['mqm_return_observed_fraction', 'mqm_return_mean',
                              'mqm_matched_k_mean_delta', 'mqm_annotated_count_delta']]
            expected.append([lp, agg, fmt(q, 2), fmt(100*vals[0], 1)]
                            + [fmt(v, 4) for v in vals[1:]])
            wmt += len(rows)
        assert expected == table_rows(ROOT / ('manuscript/tables/review-mqm-'+agg+'.tex'))
    assert rb == 1280 and wmt == 960
    return {'rewardbench_records': rb, 'wmt24_reference_records': wmt,
            'table_rows_recomputed': 56, 'values_match': True,
            'rewardbench_summary_fields_independently_recomputed': 128,
            'wmt24_summary_fields_independently_recomputed': 96,
            'alpha': .1, 'stopping': 'two_percent_gap', 'epsilon': 'ceil(.02*selected_count)'}


def main():
    pre = json.loads((OUT / 'pre-edit-checks.json').read_text())
    assert pre['status'] == 'PASS_THREE_PRE_EDIT_CHECKS'
    for n, h in pre['protected_hashes'].items():
        assert digest(ROOT / n) == h, n
    frozen = json.loads((ROOT / 'MANIFEST_SHA256.json').read_text())
    for n, h in frozen.items():
        assert digest(ROOT / n) == h, n
    m, a = [(ROOT / ('manuscript/'+n+'.tex')).read_text() for n in ['main', 'appendix']]
    bm, ba = [(OLD / ('manuscript/'+n+'.tex')).read_text() for n in ['main', 'appendix']]
    for env in ['theorem', 'proposition', 'corollary', 'equation', 'align', 'proof']:
        pat = r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
        assert re.findall(pat, m+a, re.S) == re.findall(pat, bm+ba, re.S), env
    def cites(t):
        return {k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}', t) for k in cs.split(',')}
    assert cites(m+a) == cites(bm+ba)
    for command in ['label', 'section', 'subsection']:
        pat = r'\\'+command+r'\{([^}]+)\}'
        assert re.findall(pat, m+a) == re.findall(pat, bm+ba), command
    changed = []
    for p in (ROOT / 'manuscript/tables').glob('*.tex'):
        old = OLD / p.relative_to(ROOT)
        pat = r'\\begin\{tabular\}.*?\\end\{tabular\}'
        assert re.findall(pat, p.read_text(), re.S) == re.findall(pat, old.read_text(), re.S)
        if p.read_bytes() != old.read_bytes():
            changed.append(p.name)
    assert sorted(changed) == sorted(NAMES)
    assert len(list((ROOT / 'manuscript/tables').glob('*.tex'))) == 63
    for name in NAMES:
        assert (ROOT / 'manuscript/tables' / name).read_text().count(CONDITIONS) == 1
    assert r'k_{\rm ref}=\max(1,\operatorname{round}(qn_{\rm ref}))' in m
    assert 'seeded state for ties and random acquisition' in m and r'Use $\pi$' in m
    assert 'from initially visible information and query history' in m
    assert 'matches count, not a stability certificate' not in m
    assert 'not constrained by the churn budget' in m
    assert r'K\prime' not in a and r"K'=|S_0(P)\cap C'|" in a
    assert r"$V^+-K'$" in a and r"$\varepsilon+(K-K')$" in a
    assert 'exact certification or full-information evaluation' in a
    assert 'must be recomputed' not in a[a.index('For any certified mask'):a.index(r'\section{Exact Information Costs')]
    quality = quality_check()
    pdf = fitz.open(ROOT / 'manuscript/main.pdf')
    texts = [p.get_text() for p in pdf]
    assert '??' not in '\n'.join(texts)
    assert not pdf.metadata.get('author', '') and 'Anonymous ACL submission' in texts[0]
    conclusion = next(i+1 for i, t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n', t))
    limitations = next(i+1 for i, t in enumerate(texts) if re.search(r'(^|\n)Limitations\n', t))
    assert conclusion <= 8 and limitations == 9
    assert pdf[8].search_for('Limitations')[0].y0 <= 85
    log = (ROOT / 'manuscript/main.log').read_text(errors='replace')
    assert 'Overfull' not in log and 'undefined' not in log
    outside, collisions, fonts = [], [], set()
    for pi, p in enumerate(pdf):
        black, numbers = [], []
        for block in p.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    if span['color'] == 0:
                        for c in span['chars']:
                            if c['c'].strip():
                                rect = fitz.Rect(c['bbox']); black.append(rect)
                                if rect.x0 < 70.866-3 or rect.x1 > p.rect.width-70.866+3:
                                    outside.append([pi+1, c['c']])
                    elif ''.join(c['c'] for c in span['chars']).isdigit():
                        numbers.extend(fitz.Rect(c['bbox']) for c in span['chars'])
        boxes = np.array([list(c) for c in black]).reshape(-1, 4)
        for n in numbers:
            if ((boxes[:, 0] < n.x1) & (boxes[:, 2] > n.x0)
                & (boxes[:, 1] < n.y1) & (boxes[:, 3] > n.y0)).any():
                collisions.append([pi+1, list(n)])
        for f in p.get_fonts():
            if f[0] not in fonts:
                assert f[2] != 'Type3' and pdf.extract_font(f[0])[3]
                fonts.add(f[0])
    assert not outside, outside[:8]
    assert not collisions, collisions[:8]
    result = {'status': 'PASS_SCOPED_INTERFACE_SOURCE_AND_PDF_CHECKS',
              'technical_main_pages': conclusion, 'limitations_start_page': limitations,
              'total_pdf_pages': len(pdf), 'protected_artifacts_byte_preserved': len(pre['protected_hashes']),
              'frozen_manifest_entries_preserved': len(frozen), 'formal_blocks_preserved': True,
              'citations_and_structure_preserved': True, 'table_source_files': 63,
              'changed_caption_files': sorted(changed), 'unchanged_table_files': 60,
              'all_63_tabular_bodies_byte_preserved': True, 'quality_checks': quality,
              'overfull_boxes': 0, 'undefined_references': 0, 'embedded_fonts': True,
              'line_number_collisions': 0, 'outside_horizontal_margins': 0,
              'solver_paths_masks_and_scientific_results_unchanged': True,
              'new_scientific_experiment_executed': False, 'human_proof_certified': False,
              'full_novelty_certified': False, 'complete_score_redistribution_authorized': False,
              'author_submission_fields_verified': False, 'real_scoring_cost_experiment_executed': False,
              'publicly_published_or_submitted': False}
    (OUT / 'source-pdf-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

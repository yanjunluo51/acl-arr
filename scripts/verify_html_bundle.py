"""Portable integrity checks for the extracted current CODE bundle.

Uses saved evidence only. No private ZIPs, historical checkout, numerical input
panels, network calls or model inference are required. This does not certify
scientific validity, general anonymity or data redistribution rights.
"""
from pathlib import Path
from collections import Counter
import argparse, ast, csv, hashlib, itertools, json, math, subprocess, sys

PANELS = ['RewardBench2', 'WMT23', 'WMT23_without_synthetic_ref',
          'WMT24-en-de', 'WMT24-en-es', 'WMT24-ja-zh']
RULES = ['frozen_cutoff', 'fixed_native', 'fixed_matched']

def key(row):
    return row['dataset'], int(row['split']), row['aggregator'], float(row['q'])

def close(given, expected, where):
    if expected is None:
        assert given in (None, ''), (where, given, expected)
    else:
        value = float(given)
        assert math.isfinite(value) and math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12), (where, given, expected)

def boolean(value):
    assert value in (True, False, 'True', 'False'), value
    return value is True or value == 'True'

def sign(value):
    return (value > 0) - (value < 0)

def controls(root, results_dir=None):
    out = results_dir.resolve() if results_dir is not None else root / 'outputs/matched-tie-control'
    def read(name):
        with (out/name).open(newline='') as file:
            return list(csv.DictReader(file))
    rows, pairs, cells = read('records.csv'), read('paired.csv'), read('cells.csv')
    masks = json.loads((out/'masks.json').read_text())
    expected = set(itertools.product(PANELS, range(40), ['median', 'mean'], [.05, .1, .2, .3]))
    assert len(rows) == 5760 and len(pairs) == len(masks) == 1920 and len(cells) == 48
    records = {(key(r), r['rule']): r for r in rows}
    paired = {key(p): p for p in pairs}
    packed = {tuple(m['key']): m for m in masks}
    assert len(records) == len(rows) and set(records) == set(itertools.product(expected, RULES))
    assert len(paired) == len(pairs) and set(paired) == expected
    assert len(packed) == len(masks) and set(packed) == expected
    delta_fields = ['native_to_matched_returned_delta', 'native_to_matched_risk_delta',
                    'matched_minus_frozen_returned', 'native_minus_frozen_returned',
                    'matched_minus_frozen_coverage', 'matched_frozen_returned_jaccard']
    summary_fields = ['selected_count', 'returned_count', 'selected_coverage', 'risk',
                      'replacement_max_risk', 'replacement_over_alpha_fraction', 'full_list_churn']
    for k in sorted(expected):
        rs = {rule: records[k, rule] for rule in RULES}
        p, m = paired[k], packed[k]
        N, nominal, H, budget = (int(p[f]) for f in ['N', 'k', 'H', 'integer_budget'])
        assert N > 0 and nominal == max(1, round(k[3]*N))
        assert int(p['M']) == 7 and H == 7*int(p['T']) and budget == (2*nominal*H)//10
        assert int(m['N']) == N
        decoded = {}
        for rule, name in zip(RULES, ['frozen', 'native', 'matched']):
            r = rs[rule]
            for f in ['N', 'M', 'T', 'H', 'k', 'integer_budget', 'cutoff', 'alpha']:
                close(r[f], float(p[f]), (k, rule, f))
            close(r['alpha'], .1, (k, rule, 'alpha'))
            count, selected, spent = (int(r[f]) for f in ['returned_count', 'selected_count', 'integer_spent'])
            assert 0 <= count <= selected <= N and 0 <= spent <= budget
            if rule != 'frozen_cutoff': assert selected == nominal
            close(r['risk'], spent/(2*nominal*H), (k, rule, 'risk'))
            close(r['selected_coverage'], count/selected if selected else None, (k, rule, 'coverage'))
            assert float(r['risk']) <= float(r['replacement_max_risk']) + 1e-12
            assert 0 <= float(r['replacement_over_alpha_fraction']) <= 1
            assert len(r['selected_cost_sha256']) == 64 and set(r['selected_cost_sha256']) <= set('0123456789abcdef')
            bs = m[name]
            assert len(bs) == (N+7)//8 and all(type(b) is int and 0 <= b < 256 for b in bs)
            bits = [(b >> (7-i)) & 1 for b in bs for i in range(8)]
            assert not any(bits[N:]) and sum(bits[:N]) == count
            decoded[name] = bits[:N]
        frozen, native, matched = (rs[r] for r in RULES)
        md = int(matched['returned_count'])-int(native['returned_count'])
        mf = int(matched['returned_count'])-int(frozen['returned_count'])
        nf = int(native['returned_count'])-int(frozen['returned_count'])
        union = sum(a or b for a,b in zip(decoded['frozen'], decoded['matched']))
        intersection = sum(a and b for a,b in zip(decoded['frozen'], decoded['matched']))
        derived = [md, float(matched['risk'])-float(native['risk']), mf, nf,
                   float(matched['selected_coverage'])-float(frozen['selected_coverage']) if frozen['selected_coverage'] else None,
                   intersection/union if union else 1.]
        for f,v in zip(delta_fields, derived): close(p[f], v, (k, f))
        change = sum(a != b for a,b in zip(decoded['native'], decoded['matched']))
        assert int(p['native_to_matched_mask_changes']) == change
        assert boolean(p['returned_comparison_sign_changed']) == (sign(mf) != sign(nf))
        for field, cap in [('native_to_matched_baseline_changes', N), ('native_to_matched_replacement_changes', N*H), ('matched_frozen_baseline_symmetric_difference', N)]:
            assert 0 <= int(p[field]) <= cap
    saved = json.loads((out/'results.json').read_text())
    assert saved['configurations'] == 1920 and saved['records'] == 5760
    cell_key = lambda c: (c['dataset'], c['aggregator'], float(c['q']))
    csv_cells = {cell_key(c):c for c in cells}
    json_cells = {cell_key(c):c for c in saved['cells']}
    assert len(json_cells) == len(csv_cells) == len(saved['cells']) == 48
    assert set(csv_cells) == set(json_cells) == set(itertools.product(PANELS, ['median','mean'], [.05,.1,.2,.3]))
    for ck, c in csv_cells.items():
        ps = [p for k,p in paired.items() if (k[0],k[2],k[3]) == ck]
        cs = [r for (k,rule),r in records.items() if (k[0],k[2],k[3]) == ck]
        derived = {'splits':40,
            'baseline_changed_splits':sum(int(p['native_to_matched_baseline_changes'])>0 for p in ps),
            'mask_changed_splits':sum(int(p['native_to_matched_mask_changes'])>0 for p in ps),
            'replacement_changed_splits':sum(int(p['native_to_matched_replacement_changes'])>0 for p in ps),
            'comparison_sign_changed_splits':sum(boolean(p['returned_comparison_sign_changed']) for p in ps)}
        for f in delta_fields:
            vs = [float(p[f]) for p in ps if p[f] != '']
            derived[f] = math.fsum(vs)/len(vs) if vs else None
        for rule in RULES:
            for f in summary_fields:
                vs = [float(r[f]) for r in cs if r['rule'] == rule and r[f] != '']
                derived[rule+'_'+f] = math.fsum(vs)/len(vs) if vs else None
        assert set(c)-{'dataset','aggregator','q'} == set(derived)
        assert set(json_cells[ck]) == set(c)
        for f,v in derived.items():
            close(c[f],v,(ck,f,'csv')); close(json_cells[ck][f],v,(ck,f,'json'))
    counts = {'baseline_changed_configurations':sum(int(p['native_to_matched_baseline_changes'])>0 for p in pairs),
        'replacement_changed_configurations':sum(int(p['native_to_matched_replacement_changes'])>0 for p in pairs),
        'mask_changed_configurations':sum(int(p['native_to_matched_mask_changes'])>0 for p in pairs),
        'returned_ordering_sign_changed_configurations':sum(boolean(p['returned_comparison_sign_changed']) for p in pairs)}
    previous = json.loads((out/'independent-check.json').read_text())
    assert previous['status']=='PASS_SCOPED_MATCHED_TIE_CONTROL'
    assert previous['matched_optima_independently_recomputed']==96
    for f,v in counts.items(): assert previous[f] == v, (f,v)
    counts.update({'returned_count_changed_configurations':sum(int(p['native_to_matched_returned_delta'])!=0 for p in pairs),
                  'risk_changed_configurations':sum(float(p['native_to_matched_risk_delta'])!=0 for p in pairs)})
    return {'status':'PASS_ALL_SAVED_CONTROL_DERIVATIONS','records':5760,'paired_configurations':1920,
            'packed_masks_checked':5760,'summary_cells':48,'counts':counts,
            'oracle_independent_recomputation_scope':96,'all_oracle_costs_independently_recomputed':False}

def main(root, verify_manifest=True, replay_tables=False):
    root = root.resolve()
    member_count = None
    if verify_manifest:
        manifest = json.loads((root/'PACKAGE_CONTENTS_SHA256.json').read_text())
        for n,h in manifest.items():
            p = root/n
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            assert root in p.resolve().parents and p.is_file(), n
            assert hashlib.sha256(p.read_bytes()).hexdigest() == h, n
        member_count = len(manifest)
    result = controls(root)
    ledger = json.loads((root/'review-revision/html-review-implementation/item-completion.json').read_text())
    ids = [x['id'] for x in ledger['items']]
    assert len(ids) == len(set(ids)) == 144
    assert dict(Counter(x['completion'] for x in ledger['items'])) == ledger['counts']
    if replay_tables:
        # Read the single authoritative literal without importing its PDF/private
        # archive checker and unrelated dependencies into the portable command.
        tree = ast.parse((root/'scripts/verify_interface_delivery.py').read_text())
        renderer_nodes = [node.value for node in tree.body if isinstance(node,ast.Assign)
                          and any(isinstance(t,ast.Name) and t.id=='RENDERERS' for t in node.targets)]
        assert len(renderer_nodes)==1
        renderers = ast.literal_eval(renderer_nodes[0])
        assert len(renderers)==11 and all(type(n) is str and Path(n).name==n for n in renderers)
        layers = renderers + ['render_nontrivial_certification.py',
                             'render_main10_editorial.py', 'render_html_revision.py']
        tables = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (root/'manuscript/tables').glob('*.tex')}
        assert len(tables) == 68
        for name in layers:
            subprocess.run([sys.executable, str(root/'scripts'/name)],
                           cwd=root, check=True, stdout=sys.stderr)
        for name,h in tables.items():
            assert hashlib.sha256((root/'manuscript/tables'/name).read_bytes()).hexdigest() == h, name
        result['tables_regenerated'] = 68
        result['render_layers'] = len(layers)
    result.update({'status':'PASS_PORTABLE_SAVED_BUNDLE_INTEGRITY','manifest_members_checked':member_count,
        'review_dispositions':144,'private_archives_required':False,'historical_checkout_required':False,
        'numerical_input_panels_required':False,'human_proof_certified':False,
        'complete_redistribution_authorized':False,'scientific_validity_certified':False})
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--author-live-check', action='store_true', help='Skip extracted-bundle manifest in the author checkout only')
    parser.add_argument('--replay-tables', action='store_true', help='Requires the recorded analysis dependencies; replay all 14 layers')
    parser.add_argument('--control-results-dir', type=Path, help='Check this fresh experiment directory instead; skips bundle/ledger checks')
    args = parser.parse_args()
    if args.control_results_dir is not None:
        assert not args.replay_tables and not args.author_live_check
        result = controls(args.root.resolve(), args.control_results_dir)
    else:
        result = main(args.root, not args.author_live_check, args.replay_tables)
    print(json.dumps(result, indent=2))

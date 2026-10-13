"""Scoped editorial regression checks; full-local and package audits are explicit."""
from pathlib import Path
import argparse,csv,hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'review-revision/editorial-implementation'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full-local',action='store_true');ap.add_argument('--packages',action='store_true');args=ap.parse_args()
    main=(ROOT/'manuscript/main.tex').read_text();appendix=(ROOT/'manuscript/appendix.tex').read_text();baseline=json.loads((D/'mathematical-baseline.json').read_text())
    assert re.findall(r'\\begin\{theorem\}.*?\\end\{theorem\}',main,re.S)==baseline['main_theorems']
    assert re.findall(r'\\begin\{proposition\}.*?\\end\{proposition\}',main,re.S)==baseline['main_propositions']
    proof=appendix.split('\\section{Reproducible Experimental Specification}')[0]
    assert re.findall(r'\\\[.*?\\\]',proof,re.S)==baseline['proof_displays']
    guards={
        'main_stability':'normalized average membership churn',
        'main_single_score':'A query reveals one candidate--output test score',
        'main_boundary_domain':r'\sum_{i\in C\cap\mathcal B}z_i',
        'main_column_safety':r'\sum_{i=1}^{L}o_{(i)}(A)+L(T-|A|)\le b',
        'main_column_exclusion':r'\sum_{i=1}^{L+1}o_{(i)}(A)>b',
        'main_no_unqueried_inputs':'Unqueried candidate-test scores',
        'main_processed_panel':'The processed RewardBench~2 panel',
        'main_mapped_pooling':'all depths and both pooling rules',
        'main_mean_failure':'2,363.8 inspections',
        'main_quality_negative':'$-0.0009$, $-0.0046$, $-0.0027$ and $-0.0003$',
        'main_current_statement':r'DATA\_STATEMENT\_CURRENT.md'}
    for k,v in guards.items():assert v in main,k
    for v in ['With no cross-entry constraints','For $L=0<m$',r'$N=g n_{\rm test}$','Rounding precedes integer summation','added after an exact-replay failure','conditional on the 39 nonempty splits','Bidirectional Preference Entropy','Transductive Conformal Inference for Full Ranking',r'H|U\cap S_0|',r'(n_{<s}+n_{\le s})/(2n_{\rm ref})']:
        assert v in appendix,v
    assert main.count(r'\input{tables/review-composition}')==0 and appendix.count(r'\input{tables/review-composition}')==1
    assert main.index('Envelope CRC calibrates')>main.index(r'\subsection{Observable-risk controls}')
    assert main.index('Calibration and scoring workload')<main.index(r'\subsection{Quality and the meaning of savings}')
    keys=re.findall(r'@\w+\s*\{\s*([^,]+)',(ROOT/'manuscript/references.bib').read_text());assert len(keys)==len(set(keys))
    cited=set(k.strip() for body in re.findall(r'\\cite\w*\{([^}]+)\}',main+appendix) for k in body.split(','));assert cited<=set(keys)
    bodies=0
    for p in (D/'table-bases').glob('*.tex'):
        old=re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',p.read_text(),re.S)
        cur=re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',(ROOT/'manuscript/tables'/p.name).read_text(),re.S)
        clean=lambda x:x.replace(' & Gap (outputs)',' & Gap').replace(' & Mean max &',' & Max &')
        assert old==[clean(x) for x in cur],p.name;bodies+=len(old)
    rows=list(csv.DictReader((ROOT/'review-revision/editorial-audit/zero-query-decomposition.csv').open()));assert len(rows)==48
    for row in rows:
        assert int(row['splits'])==40
        assert abs(float(row['invariant_selected_fraction'])+float(row['budget_retained_noninvariant_fraction'])-float(row['zero_query_selected_coverage']))<1e-12
    protected=0
    if args.full_local:
        for n,h in json.loads((D/'precheck-three-pass.json').read_text())['protected_files'].items():
            assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n;protected+=1
        frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
        for n,h in frozen.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
    packages=[]
    if args.packages:
        for name in ['manuscript/source_private.zip','packages/current_mapping_column_code_private.zip','packages/synthetic_certificate_reproduction.zip']:
            with zipfile.ZipFile(ROOT/name) as z:
                assert len(z.namelist())==len(set(z.namelist()))
                manifest=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'))
                for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,(name,n)
                assert not any(n.startswith('data/') or n.endswith('data_private.zip') for n in z.namelist())
                if 'source_private' in name:assert 'ROOT/DATA_STATEMENT_CURRENT.md' in z.namelist()
                elif 'current_mapping' in name:assert 'DATA_STATEMENT_CURRENT.md' in z.namelist() and 'scripts/render_editorial_tables.py' in z.namelist()
                packages.append({'name':name,'verified_members':len(manifest)})
    out={'status':'PASS_SCOPED_EDITORIAL_REGRESSION_CHECKS','three_pre_edit_passes_recorded':True,'core_main_statements_and_proof_displays_preserved':True,'tabular_bodies_preserved':bodies,'decomposition_cells':48,'cited_keys':len(cited),'citation_keys_and_duplicate_check':'PASS; not full bibliographic/context verification','protected_scientific_files_verified':protected,'packages':packages,'human_proof_certified':False,'full_novelty_certified':False,'full_score_redistribution_authorized':False}
    (D/('package-regression-check.json' if args.packages else 'regression-check.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()

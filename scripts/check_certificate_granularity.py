"""Scoped source, data, witness-condition and table verification."""
from pathlib import Path
import csv,hashlib,json,re,zipfile
import numpy as np
from mapping_column_experiments import map_scores
from query_selection import aggregate,endpoint_cost
ROOT=Path(__file__).resolve().parents[1]


def main():
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    for p,h in frozen.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    original=json.loads((ROOT/'outputs/mapping-column/protocol.json').read_text())
    for p,h in {**original['source_bindings'],**original['solver_bindings']}.items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    rows=json.loads((ROOT/'outputs/column-certificates/results.json').read_text())['records']
    assert len(rows)==960
    checked=0
    for panel in original['panels']:
        for rep in range(40):
            ref,test,_,_,_=map_scores(panel,rep,'1','right')
            base,hidden=test[:7],test[7:]
            for z in [x for x in rows if x['dataset']==panel and x['split']==rep]:
                t=float(np.sort(aggregate(ref[:7],'median'))[-max(1,round(z['q']*ref.shape[1]))])
                selected=aggregate(base,'median')>=t;p=endpoint_cost(base,t,'median')
                y=(hidden[:,selected&(p>0)].T<t).astype(np.int64)
                assert len(y)==z['m']
                o=np.sort(y[:,z['columns']].sum(axis=1));L=z['L'];b=z['bit_budget'];a=z['K_col']
                assert int(o[:L].sum())+L*(z['T']-a)<=b
                assert L==len(y) or int(o[:L+1].sum())>b
                assert z['score_entry_cost']==z['N']*a
                if a==0:assert z['Q_entry']==0
                else:assert (z['Q_entry']+z['m']-1)//z['m']<=a<=min(z['T'],z['Q_entry'])
                checked+=1
    assert checked==960
    # New tables must regenerate identically from complete existing inputs.
    import render_certificate_granularity as renderer
    names=['entry-overhead-summary.tex','entry-overhead-all.tex']+[f'entry-overhead-all-{j}.tex' for j in range(6)]+['column-witness-summary.tex','column-witness-all.tex','synthetic-column-witnesses.tex','granularity-numbers.tex']
    before={n:(ROOT/'manuscript/tables'/n).read_bytes() for n in names}
    renderer.main()
    assert all((ROOT/'manuscript/tables'/n).read_bytes()==v for n,v in before.items())
    # Approved editorial captions and nonnumeric headers may change; numeric bodies and theorem statements remain exact.
    with zipfile.ZipFile(ROOT/'history/before-certificate-granularity/manuscript/source_private.zip') as old:
        preserved=0
        for n in old.namelist():
            if n.startswith('manuscript/tables/'):
                current=(ROOT/n).read_text();previous=old.read(n).decode()
                pattern=r'\\begin\{tabular\}.*?\\end\{tabular\}'
                clean=lambda v:v.replace(' & Gap (outputs)',' & Gap').replace(' & Mean max &',' & Max &')
                assert [clean(v) for v in re.findall(pattern,current,re.S)]==re.findall(pattern,previous,re.S),n
                # Macro files and includes have no captions and stay byte-identical.
                if not re.findall(pattern,previous,re.S):assert current==previous,n
                preserved+=1
    text=(ROOT/'manuscript/main.tex').read_text()+'\n'+(ROOT/'manuscript/appendix.tex').read_text()
    old_main=(ROOT/'history/before-certificate-granularity/manuscript/main.tex').read_text()
    current_main=(ROOT/'manuscript/main.tex').read_text()
    for kind in ['theorem','proposition']:
        pattern=r'\\begin\{'+kind+r'\}.*?\\end\{'+kind+r'\}'
        assert re.findall(pattern,old_main,re.S)==re.findall(pattern,current_main,re.S)
    keys=set(re.findall(r'@\w+\s*\{\s*([^,]+)',(ROOT/'manuscript/references.bib').read_text()))
    for body in re.findall(r'\\cite\w*\{([^}]+)\}',text):
        assert all(k.strip() in keys for k in body.split(',')),body
    assert 'megow2023set' in keys
    receipt={'status':'PASS_SCOPED_GRANULARITY_SOURCE_AND_NUMBER_CHECKS',
             'frozen_manifest_entries_unchanged':len(frozen),'column_condition_instances':checked,
             'new_tables_regenerated_identically':len(names),'old_table_numeric_bodies_preserved':preserved,
             'original_main_theorem_and_proposition_statements_identical':True,
             'old_acquisition_solvers_unchanged':True,'new_citation_key_exists':True,
             'new_theorem_human_certified':False,'complete_novelty_certified':False,
             'third_party_redistribution_authorized':False}
    (ROOT/'review-revision/certificate-granularity/source-number-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()

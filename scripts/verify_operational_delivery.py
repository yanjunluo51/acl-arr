"""Clean archive compilation/rendering plus current delivery bindings."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
import fitz
from verify_interface_delivery import RENDERERS
from package_operational_revision import DOCS,SCRIPTS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/operational-scope-implementation'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def check_archive(path,source=False):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();assert len(names)==len(set(names)) and z.testzip() is None
        bindings=json.loads(z.read('PACKAGE_CONTENTS_SHA256.json'))
        assert set(bindings)==set(names)-{'PACKAGE_CONTENTS_SHA256.json'}
        for n,h in bindings.items():
            assert not n.startswith('/') and '..' not in Path(n).parts
            payload=z.read(n);assert hashlib.sha256(payload).hexdigest()==h
            real=n[5:] if source and n.startswith('ROOT/') else n
            assert (ROOT/real).read_bytes()==payload,n
    return len(names)


def main():
    qa=json.loads((OUT/'source-pdf-check.json').read_text())
    assert qa['status']=='PASS_SCOPED_OPERATIONAL_SOURCE_AND_PDF_CHECKS'
    ns=check_archive(ROOT/'manuscript/source_private.zip',True)
    nc=check_archive(ROOT/'packages/current_mapping_column_code_private.zip')
    src=Path(tempfile.mkdtemp(prefix='clean-source-',dir=OUT))
    code=Path(tempfile.mkdtemp(prefix='clean-code-',dir=OUT))
    with zipfile.ZipFile(ROOT/'manuscript/source_private.zip') as z:z.extractall(src)
    (src/'manuscript/main.pdf').unlink()
    with (OUT/'clean-source-build.log').open('w') as f:
        subprocess.run(['bash','build.sh'],cwd=src/'manuscript',stdout=f,stderr=subprocess.STDOUT,check=True)
    with fitz.open(ROOT/'manuscript/main.pdf') as live,fitz.open(src/'manuscript/main.pdf') as clean:
        assert len(live)==len(clean)==qa['total_pdf_pages']
        for a,b in zip(live,clean):
            assert a.get_text()==b.get_text()
            assert a.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).samples==b.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).samples
    with zipfile.ZipFile(ROOT/'packages/current_mapping_column_code_private.zip') as z:z.extractall(code)
    renderers=RENDERERS+['render_nontrivial_certification.py']
    with (OUT/'clean-render.log').open('w') as f:
        for name in renderers:
            subprocess.run([sys.executable,'scripts/'+name],cwd=code,stdout=f,stderr=subprocess.STDOUT,check=True)
    tables=list((ROOT/'manuscript/tables').glob('*.tex'));assert len(tables)==67
    for p in tables:assert p.read_bytes()==(code/p.relative_to(ROOT)).read_bytes(),p.name
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    for n in ['packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']:
        assert digest(ROOT/n)==pre['prior_delivery_hashes'][n]
    checks={'status':'PASS_CLEAN_SOURCE_AND_67_TABLE_REGENERATION',
            'source_members':ns,'code_members':nc,'pdf_pages':qa['total_pdf_pages'],
            'all_pdf_text_and_pixels_identical':True,'table_files_regenerated':67,
            'render_layers':len(renderers),'archive_payloads_match_live':True,
            'independent_archives_preserved':True,'clean_source_directory':src.name,
            'clean_code_directory':code.name,'new_scorer_inference_executed':False}
    (OUT/'clean-package-check.json').write_text(json.dumps(checks,indent=2)+'\n')
    files=['manuscript/main.tex','manuscript/appendix.tex','manuscript/main.pdf','manuscript/references.bib',
           'manuscript/source_private.zip','packages/current_mapping_column_code_private.zip',
           'packages/residual_certificate_reproduction.zip','packages/synthetic_certificate_reproduction.zip']
    files+=DOCS+['scripts/'+n for n in SCRIPTS]+[str(p.relative_to(ROOT)) for p in tables]
    files+=[str(p.relative_to(ROOT)) for p in (ROOT/'outputs/nontrivial-certification').glob('*') if p.is_file()]
    files+=[str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file() and p.name not in ['final-delivery.json','delivery-check.log']]
    result=dict(qa)
    result.update({'status':'PASS_SCOPED_OPERATIONAL_REVISION_AND_CLEAN_DELIVERY',
                   'three_pre_edit_checks_passed':True,'single_research_spine_preserved':True,
                   'clean_package_checks':checks,'new_theory_or_online_algorithm_claimed':False,
                   'real_cost_experiment_executed':False,
                   'hashes':{n:digest(ROOT/n) for n in sorted(set(files))}})
    (OUT/'final-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2))


if __name__=='__main__':main()

"""Rebuild WMT24 numerical panels in isolation from the exact pinned archive.

No canonical data or admission receipt is overwritten. Original builder is
reused under a temporary root. The archive contains third-party material and
must be acquired locally; this helper does not grant redistribution permission.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,tarfile,tempfile
import prepare_external_panel as builder
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main(archive,output_dir,receipt):
    archive=archive.resolve();output_dir=output_dir.resolve()
    admission=json.loads((ROOT/'review-revision/external-admission.json').read_text())
    assert archive.stat().st_size==admission['archive_bytes'] and sha(archive)==admission['archive_sha256'], 'Different archive; frozen inputs remain untouched'
    with tempfile.TemporaryDirectory(prefix='wmt24-rebuild-') as name:
        work=Path(name);A=work/'review-revision/acquisition';A.mkdir(parents=True);(work/'data').mkdir()
        (A/'mt-metrics-eval-v2.tgz').symlink_to(archive)
        shutil.copy2(ROOT/'review-revision/acquisition/official-hosting.json',A/'official-hosting.json')
        shutil.copy2(ROOT/'review-revision/external-panel-protocol.json',work/'review-revision/external-panel-protocol.json')
        extracted=A/'extracted';extracted.mkdir();count=0
        with tarfile.open(archive,'r|gz') as tf:
            for member in tf:
                if not member.name.startswith('mt-metrics-eval-v2/wmt24/'):continue
                if not member.isfile():continue
                parts=Path(member.name).parts
                assert not Path(member.name).is_absolute() and '..' not in parts
                # Builder needs document/system/reference metadata plus numerical scores.
                if len(parts)<4 or parts[2] not in ['documents','references','system-outputs','metric-scores','human-scores']:continue
                target=extracted/member.name;target.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(member) as source,target.open('xb') as out:shutil.copyfileobj(source,out)
                count+=1
        builder.ROOT=work;builder.A=A;builder.D=extracted/'mt-metrics-eval-v2/wmt24';builder.main()
        generated=json.loads((work/'review-revision/external-admission.json').read_text())
        expected={}
        for p in admission['panels']:
            expected['wmt24_'+p['language']+'_panel.json']=p['panel_sha256']
            expected['wmt24_'+p['language']+'_mqm.json']=p['mqm_sha256']
        assert len(expected)==6
        for name,h in expected.items():assert sha(work/'data'/name)==h,name
        output_dir.mkdir(parents=True,exist_ok=True)
        for name,h in expected.items():
            p=output_dir/name
            if p.exists():assert sha(p)==h, 'Different existing input; preserving it: '+name
        written=[]
        for name,h in expected.items():
            p=output_dir/name
            if not p.exists():
                with p.open('xb') as f:f.write((work/'data'/name).read_bytes())
                written.append(name)
        result={'status':'PASS_EXACT_WMT24_PANEL_AND_MQM_RECONSTRUCTION','archive_sha256':admission['archive_sha256'],
          'six_panel_label_hashes':expected,'written':written,'extracted_file_count':count,
          'original_admission_unchanged':True,'labels_choose_admission':False,'redistribution_authorized':False}
        if receipt:
            receipt.parent.mkdir(parents=True,exist_ok=True)
            with receipt.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,default=ROOT/'data');p.add_argument('--receipt',type=Path)
    a=p.parse_args();main(a.archive,a.output_dir,a.receipt)

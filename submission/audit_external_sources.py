"""Independent exact coordinate check against the acquired official WMT24 files."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'review-revision/acquisition';D=A/'extracted/mt-metrics-eval-v2/wmt24'

def parse(path):
    out={}
    for line in path.read_text().splitlines():
        system,value=line.split();out.setdefault(system,[]).append(None if value=='None' else float(value))
    return out

def main():
    receipt=json.loads((ROOT/'review-revision/external-admission.json').read_text());assert hashlib.sha256((A/'mt-metrics-eval-v2.tgz').read_bytes()).hexdigest()==receipt['archive_sha256'];coords=goldvalues=sourcefiles=0;probe=json.loads((ROOT/'data/wmt24_sentinel_probes.json').read_text())['panels']
    for info in receipt['panels']:
        lp=info['language'];panel=json.loads((ROOT/'data'/f'wmt24_{lp}_panel.json').read_text());gold=json.loads((ROOT/'data'/f'wmt24_{lp}_mqm.json').read_text());assert panel['models']==info['models'] and panel['systems']==info['systems']
        for record in info['input_files']:
            assert hashlib.sha256((A/record['path']).read_bytes()).hexdigest()==record['sha256'];sourcefiles+=1
        docs=[line.split() for line in (D/'documents'/f'{lp}.docs').read_text().splitlines()];ids=list(map(int,panel['prompt_ids']));systems=panel['systems'];assert panel['source_document_ids']==[docs[i][1] for i in ids]
        refs={p.name[len(lp)+1:-4] for p in (D/'references').glob(lp+'.*.txt')};assert not set(systems)&refs
        seen={};names=[]
        for path in sorted((D/'metric-scores'/lp).glob('*-'+panel['reference']+'.seg.score'),key=lambda p:p.name[:-len('-'+panel['reference']+'.seg.score')]):
            values=parse(path);name=path.name[:-len('-'+panel['reference']+'.seg.score')];a=np.array([[values[s][i] for s in systems] for i in ids],dtype=float);assert np.isfinite(a).all();h=hashlib.sha256(a.tobytes()).hexdigest()
            if h in seen:assert info['exact_duplicate_streams'][name]==seen[h];continue
            seen[h]=name;names.append(name);assert np.array_equal(a,np.array([panel['scores'][name][str(i)] for i in ids]));coords+=a.size
        assert names==panel['models']
        human=parse(D/'human-scores'/f'{lp}.mqm.seg.score');assert gold['prompt_ids']==panel['prompt_ids'] and gold['systems']==systems
        for i in ids:
            for j,s in enumerate(systems):assert gold['mqm'][str(i)][j]==human.get(s,[None]*len(docs))[i];goldvalues+=1
        for record in probe[lp]['input_files']:
            path=A/'extracted/mt-metrics-eval-v2'/record['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'];v=parse(path);name=path.name[:-len('.seg.score')]
            assert all(probe[lp]['scores'][name][s]==[v[s][i] for i in ids] for s in systems);sourcefiles+=1
    result={'status':'PASS_EXACT_OFFICIAL_SOURCE_COORDINATES_AND_GOLD_ALIGNMENT','languages':3,'metric_coordinates_checked':coords,'native_gold_cells_including_missing_checked':goldvalues,'source_file_hashes_checked':sourcefiles,'archive_sha256':receipt['archive_sha256'],'scope':'Exact source-file correspondence; does not independently adjudicate human MQM ratings, evaluator training independence or all redistribution rights.'}
    (ROOT/'review-revision/external-source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()

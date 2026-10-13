"""Deterministic WMT24 admission and exact native MQM alignment.

MQM values never choose metrics, systems or paragraphs. No input text is copied
into the numeric panel. Archive contents are official, privately retained.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'review-revision/acquisition';D=A/'extracted/mt-metrics-eval-v2/wmt24'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def scores(p):
    out={}
    for line in p.read_text().splitlines():
        system,value=line.split();out.setdefault(system,[]).append(None if value=='None' else float(value))
    return out

def main():
    protocol=json.loads((ROOT/'review-revision/external-panel-protocol.json').read_text());report=[]
    for lp in protocol['language_priority']:
        used=[];ref='refB' if lp=='en-de' else 'refA';docs_path=D/'documents'/f'{lp}.docs';docrows=[x.split() for x in docs_path.read_text().splitlines()];N=len(docrows);used.append(docs_path)
        refs={p.name[len(lp)+1:-4] for p in (D/'references').glob(lp+'.*.txt')}
        system_files={p.stem:p for p in (D/'system-outputs'/lp).glob('*.txt')};system_names=set(system_files)-refs
        metric_files=sorted((D/'metric-scores'/lp).glob('*-'+ref+'.seg.score'));metric={p.name[:-(len(ref)+11)]:scores(p) for p in metric_files}
        # Suffix is '-REF.seg.score'; validate name extraction explicitly.
        metric={p.name.removesuffix('-'+ref+'.seg.score'):scores(p) for p in metric_files} if hasattr(str,'removesuffix') else {p.name[:-len('-'+ref+'.seg.score')]:scores(p) for p in metric_files}
        common=system_names.intersection(*(set(v) for v in metric.values()));systems=sorted(common)
        assert systems and len(metric)>=8,(lp,len(metric),len(systems))
        assert all(len(system_files[s].read_text().splitlines())==N for s in systems)
        assert all(len(v[s])==N for v in metric.values() for s in systems)
        arrays={m:np.array([v[s] for s in systems],dtype=float).T for m,v in metric.items()}
        finite=np.logical_and.reduce([np.isfinite(a).all(axis=1) for a in arrays.values()]);ids=np.flatnonzero(finite).tolist();assert len(ids)>0
        names=[];duplicates={};seen={}
        for m in sorted(arrays):
            signature=hashlib.sha256(arrays[m][ids].tobytes()).hexdigest()
            if signature in seen:duplicates[m]=seen[signature]
            else:seen[signature]=m;names.append(m)
        assert len(names)>=8
        out={'dataset':'WMT24-'+lp,'models':names,'prompt_ids':[str(i) for i in ids],'systems':systems,
             'source_document_ids':[docrows[i][1] for i in ids],'domains':[docrows[i][0] for i in ids],
             'scores':{m:{str(i):arrays[m][i].tolist() for i in ids} for m in names},
             'unit':'paragraph','reference':ref,'original_paragraph_ids':ids,'source':'Official maintainer migrated MTME archive'}
        target=ROOT/'data'/f'wmt24_{lp}_panel.json';target.write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')
        used+=metric_files+list((D/'references').glob(lp+'.*.txt'))+[system_files[s] for s in systems]
        # Gold loaded only after all admission choices are fixed above. It is a separate
        # post-protocol diagnostic artifact and unavailable to the query solver.
        goldpath=D/'human-scores'/f'{lp}.mqm.seg.score';gold=scores(goldpath);used.append(goldpath)
        for s in systems:
            if s in gold:assert len(gold[s])==N,(lp,s,len(gold[s]),N)
        aligned={str(i):[gold.get(s,[None]*N)[i] for s in systems] for i in ids}
        assert all(v is None or math.isfinite(v) for a in aligned.values() for v in a)
        gp=ROOT/'data'/f'wmt24_{lp}_mqm.json';gp.write_text(json.dumps({'dataset':out['dataset'],'systems':systems,'prompt_ids':out['prompt_ids'],'mqm':aligned,'higher_is_better':True,'alignment':'Official block order by exact system name and original 0-based paragraph id; absent values retained as None'},separators=(',',':'),allow_nan=False)+'\n')
        report.append({'language':lp,'status':'ADMITTED','reference':ref,'models':names,'base_pool':names[:7],'candidates':names[7:],'systems':systems,'excluded_human_references':sorted(refs),'systems_missing_from_some_metric_stream':sorted(system_names-common),'original_paragraph_count':N,'retained_paragraph_count':len(ids),'retained_document_count':len(set(out['source_document_ids'])),'removed_nonfinite_paragraph_ids':np.flatnonzero(~finite).tolist(),'exact_duplicate_streams':duplicates,'native_mqm_observed':sum(v is not None for a in aligned.values() for v in a),'native_mqm_possible':len(ids)*len(systems),'panel_sha256':sha(target),'mqm_sha256':sha(gp),'input_files':[{'path':str(p.relative_to(A)),'sha256':sha(p)} for p in sorted(set(used))]})
    receipt={'status':'PASS_METADATA_FINITE_SCORE_AND_NATIVE_GOLD_ALIGNMENT','archive_sha256':sha(A/'mt-metrics-eval-v2.tgz'),'archive_bytes':(A/'mt-metrics-eval-v2.tgz').stat().st_size,'source':json.loads((A/'official-hosting.json').read_text()),'panels':report,'limitations':'No claim of independent human annotation verification or universal derived-data redistribution rights. WMT24 is project-unseen after method freeze, not evaluator-training-uncontaminated.'}
    (ROOT/'review-revision/external-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in p.items() if k not in ['input_files','models','systems','candidates','base_pool']} for p in report],indent=2))
if __name__=='__main__':main()

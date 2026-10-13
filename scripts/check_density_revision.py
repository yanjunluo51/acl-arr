"""Scoped manuscript regression checks; no scientific experiment is executed."""
from pathlib import Path
import csv,hashlib,json,re
import fitz
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/density-review-implementation'
OLD=ROOT/'history/before-density-review'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(text):
    return [v.replace(r'\tau',r'\eta') for v in re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',text,re.S)]
def main():
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    assert pre['status']=='PASS_THREE_PRE_EDIT_CHECKS'
    for n,h in pre['protected_hashes'].items():assert digest(ROOT/n)==h,n
    frozen=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
    assert all(digest(ROOT/n)==h for n,h in frozen.items())
    m=(ROOT/'manuscript/main.tex').read_text();a=(ROOT/'manuscript/appendix.tex').read_text()
    bm=(OLD/'manuscript/main.tex').read_text();ba=(OLD/'manuscript/appendix.tex').read_text()
    for env in ['theorem','proposition','corollary','equation','align']:
        pat=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
        assert re.findall(pat,m,re.S)==re.findall(pat,bm,re.S),env
    proof=r'\\begin\{proof\}.*?\\end\{proof\}'
    assert re.findall(proof,a,re.S)==re.findall(proof,ba,re.S)
    def keys(t):return {k.strip() for cs in re.findall(r'\\cite\w*\{([^}]+)\}',t) for k in cs.split(',')}
    assert keys(m+a)==keys(bm+ba)
    assert digest(ROOT/'manuscript/references.bib')==digest(OLD/'manuscript/references.bib')
    changed=[];unchanged=[]
    for n,h in pre['table_hashes'].items():
        p=ROOT/n;old=OLD/n
        assert body(p.read_text())==body(old.read_text()),n
        if digest(p)==h:unchanged.append(n)
        else:changed.append(n)
    assert len(changed)+len(unchanged)==63
    assert r'\input{tables/review-composition}' not in a and r'\ref{tab:review-composition}' not in m+a
    assert r'\mathcal A=\{i\in S_0:p_i>0\}' in a and r'E_{\rm entry}=' in a and r'E_{\rm rem}(t)=' in a
    assert r'\tau' in m and r'\tau' not in a[a.index(r'\subsection{Diagnostic definitions'):]
    assert r'\eta' in a[a.index(r'\section{Retention Tolerance'):]
    assert 'initial state $t=0$' in a
    for name in ['acquisition-median.tex','acquisition-mean.tex']:
        t=(ROOT/'manuscript/tables'/name).read_text()
        assert r't=\max(0,Q-1)' in t and 'just before' not in t
    assert 'Median excess entry queries' in a and 'multiplicative discovery ratio' in a
    assert 'all six panels' in m[m.index(r'\subsection{WMT24 panels}'):]
    assert 'all six panels' not in m[:m.index(r'\subsection{WMT24 panels}')]
    assert 'Q_\\varepsilon(\\mathcal O_A)' in m and r'\label{prop:residual}' in a
    assert 'same target' in (ROOT/'manuscript/tables/column-cost-exact.tex').read_text() or 'not measured scoring times or fees' in (ROOT/'manuscript/tables/column-cost-exact.tex').read_text()
    assert m.index('invariant outputs account')<m.index(r'\subsection{Inspection and certificate size}')
    rows=list(csv.DictReader((ROOT/'outputs/acquisition-mechanisms/split_diagnostics.csv').open()))
    zero=[x for x in rows if int(x['reference_priority_queries'])==0]
    assert len(rows)==5760 and len(zero)==2388
    assert all(int(x['active_rows'])>0 and x['prestop_remaining_mae'] not in ['','None','null','nan'] for x in zero)
    refs=re.findall(r'@\w+\s*\{\s*([^,]+)',(ROOT/'manuscript/references.bib').read_text())
    assert len(refs)==len(set(refs)) and keys(m+a)<=set(refs)
    pdf=fitz.open(ROOT/'manuscript/main.pdf');texts=[p.get_text() for p in pdf]
    assert '??' not in '\n'.join(texts) and not re.search(r'/(Users|home)/','\n'.join(texts))
    assert not pdf.metadata.get('author','') and 'Anonymous ACL submission' in texts[0]
    conclusion=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Conclusion\n',t))
    limitations=next(i+1 for i,t in enumerate(texts) if re.search(r'(^|\n)Limitations\n',t))
    assert conclusion<=8 and limitations<=9,(conclusion,limitations)
    # Heading at the top of page nine proves that conclusion does not spill.
    assert pdf[limitations-1].search_for('Limitations')[0].y0<=85,'Technical conclusion spills beyond page eight'
    log=(ROOT/'manuscript/main.log').read_text(errors='replace')
    assert 'Overfull' not in log and 'undefined' not in log
    outside=[];collisions=[];fonts=set()
    for pi,p in enumerate(pdf):
        black=[];numbers=[]
        for block in p.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    if span['color']==0:
                        for c in span['chars']:
                            if c['c'].strip():
                                rect=fitz.Rect(c['bbox']);black.append(rect)
                                if rect.x0<70.866-3 or rect.x1>p.rect.width-70.866+3:outside.append([pi+1,c['c'],list(rect)])
                    elif ''.join(c['c'] for c in span['chars']).isdigit():numbers.extend(fitz.Rect(c['bbox']) for c in span['chars'])
        boxes=np.array([list(c) for c in black]).reshape(-1,4)
        for n in numbers:
            if ((boxes[:,0]<n.x1)&(boxes[:,2]>n.x0)&(boxes[:,1]<n.y1)&(boxes[:,3]>n.y0)).any():collisions.append([pi+1,list(n)])
        for f in p.get_fonts():
            if f[0] not in fonts:
                assert f[2]!='Type3' and pdf.extract_font(f[0])[3]
                fonts.add(f[0])
    assert not outside,outside[:8]
    assert not collisions,collisions[:8]
    result={'status':'PASS_SCOPED_DENSITY_SOURCE_AND_PDF_CHECKS','technical_main_pages':conclusion,'limitations_start_page':limitations,'total_pdf_pages':len(pdf),'protected_artifacts_byte_preserved':len(pre['protected_hashes']),'frozen_manifest_entries_preserved':len(frozen),'formal_main_blocks_preserved':True,'appendix_proof_blocks_preserved':True,'bibliography_and_citation_keys_preserved':True,'table_source_files':63,'changed_display_files':changed,'unchanged_table_files':len(unchanged),'all_63_numeric_tabular_bodies_unchanged_except_tau_to_eta':True,'duplicate_summary_removed_from_pdf_only':True,'zero_query_diagnostics_checked':len(zero),'new_scientific_experiments':False,'solver_paths_masks_unchanged':True,'overfull_boxes':0,'undefined_references':0,'embedded_fonts':True,'line_number_collisions':0,'outside_horizontal_margins':0,'real_scoring_cost_experiment_executed':False,'human_proof_certified':False,'full_novelty_certified':False,'complete_score_redistribution_authorized':False,'author_submission_fields_verified':False,'publicly_published_or_submitted':False,'scope':'Local review-driven prose/notation/structure regression checks, not scientific or external certification.'}
    (OUT/'source-pdf-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

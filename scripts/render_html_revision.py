"""Final table layer: preserve old values, lower captions, add paired controls."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/html-review-implementation'
def command_end(s,start):
    pos=s.index('{',start);depth=0
    for j in range(pos,len(s)):
        if s[j]=='{' and (j==0 or s[j-1]!='\\'):depth+=1
        if s[j]=='}' and (j==0 or s[j-1]!='\\'):
            depth-=1
            if depth==0:return j+1
    raise ValueError('Unbalanced caption')
def lower_caption(block):
    cap=block.index(r'\caption');tab=block.index(r'\begin{tabular}')
    if cap>tab:return block
    end=command_end(block,cap)
    caption=block[cap:end];block=block[:cap]+block[end:]
    label=re.search(r'\\label\{[^}]+\}',block)
    labeltext=label.group() if label else ''
    if label:block=block[:label.start()]+block[label.end():]
    pos=block.index(r'\end{tabular}')+len(r'\end{tabular}')
    return block[:pos]+'\n'+caption+'\n'+labeltext+block[pos:]
def main():
    assert json.loads((ROOT/'outputs/matched-tie-control/independent-check.json').read_text())['status']=='PASS_SCOPED_MATCHED_TIE_CONTROL'
    changed=[]
    for p in (ROOT/'manuscript/tables').glob('*.tex'):
        old=p.read_text()
        new=re.sub(r'\\begin\{table\*?\}.*?\\end\{table\*?\}',lambda m:lower_caption(m.group()),old,flags=re.S)
        if new!=old:p.write_text(new);changed.append(p.name)
    cells=json.loads((ROOT/'outputs/matched-tie-control/results.json').read_text())['cells']
    labels={'RewardBench2':'RewardBench 2','WMT23':'WMT23, 13','WMT23_without_synthetic_ref':'WMT23, 12','WMT24-en-de':'WMT24 en-de','WMT24-en-es':'WMT24 en-es','WMT24-ja-zh':'WMT24 ja-zh'}
    lines=[r'\begin{table*}[t]',r'\centering\small',r'\begin{tabular}{llrrrrrr}',r'\toprule',r'Panel & Pooling & $q$ & Frozen Cov. & Matched Cov. & $\Delta K$ & Masks/40 & Sign/40 \\',r'\midrule']
    for c in cells:
        lines.append(f"{labels[c['dataset']]} & {c['aggregator']} & {c['q']:.2f} & {100*c['frozen_cutoff_selected_coverage']:.1f} & {100*c['fixed_matched_selected_coverage']:.1f} & {c['native_to_matched_returned_delta']:.3f} & {c['mask_changed_splits']} & {c['comparison_sign_changed_splits']} \\\\")
    lines += [r'\bottomrule',r'\end{tabular}',r'\caption{Matched label-blind top-$k$ control, $\alpha=.10$, full information. Cov. averages splitwise selected coverage (\%) using each rule\textquotesingle s own baseline. $\Delta K$ is matched-minus-native returned count, averaged over 40 splits. Masks/40 counts changed retained sets under this tie change. Sign/40 counts changes in the sign of fixed-count-minus-frozen returned count; ties count as zero. This compares selection tasks, not online query orders. All baseline and replacement rankings use decreasing consensus and increasing seeded priority.}',r'\label{tab:matched-tie-control}',r'\end{table*}']
    (ROOT/'manuscript/tables/matched-tie-control.tex').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'captions_lowered_files':changed,'new_table_rows':len(cells),'old_numeric_rows_changed':False}))
if __name__=='__main__':main()

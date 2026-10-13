"""Current notation/caption layer, applied after the historical table renderers.

Only display notation and explanatory captions change. Numeric rows and cached
results retain their original representation, including the raw `tau` field.
"""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]

def transform(name,text):
    if name in ['tolerance-all.tex','tolerance-witness.tex']:
        text=text.replace(r'\tau',r'\eta')
    if name in ['acquisition-median.tex','acquisition-mean.tex']:
        text=text.replace('Remaining error is measured just before reference stopping;',
                          r'Remaining error uses $t=\max(0,Q-1)$, the initial state for zero-query stops;')
    def caption(match):
        content=match.group(0)
        content=content.replace('Exact median entry-query overhead','Exact median entry-query discovery ratios')
        content=content.replace('exact entry overhead across every depth','exact entry discovery ratios across every depth')
        content=content.replace('conditional median online overhead','conditional median online column-count ratios')
        return content
    # Captions end at the label or table body, not at their first nested brace.
    text=re.sub(r'\\caption\{.*?(?=\n\\label|\n\\end\{table)',caption,text,flags=re.S)
    return text

def main():
    changed=[]
    for p in (ROOT/'manuscript/tables').glob('*.tex'):
        old=p.read_text();new=transform(p.name,old)
        if old!=new:p.write_text(new);changed.append(p.name)
    print(json.dumps({'status':'PASS_DENSITY_DISPLAY_LAYER','changed_in_this_invocation':changed,'numeric_results_changed':False}))
if __name__=='__main__':main()

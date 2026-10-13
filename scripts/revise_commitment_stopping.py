"""Two approved clarifications, applied to canonical sources after preflight."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review-revision/commitment-stopping-implementation'
OLD=ROOT/'history/before-commitment-stopping-review/manuscript'

def main():
    pre=json.loads((OUT/'pre-edit-checks.json').read_text())
    assert pre['status']=='PASS_THREE_PRE_EDIT_CHECKS'
    edits={
      'main.tex':(
        'All strategies start from this mask.',
        'All strategies start from this zero-query solution and recompute provisional masks after queries. The safe count cannot decrease, but retained sets need not be nested. Commitments use the mask returned at stopping.'),
      'appendix.tex':(
        'If quality is audited after certification, report the audit separately; using those labels to select a stopping point requires an additional valid selection or calibration procedure.',
        r'Report post-certification quality audits separately. If audit labels select a stopping point, statistical quality claims must account for that choice. Under the fixed selection protocol, deterministic churn and count-gap guarantees hold at any chosen state satisfying the certificate conditions of Proposition~\ref{prop:stop}.')}
    for name,(old,new) in edits.items():
        text=(OLD/name).read_text()
        assert text.count(old)==1,(name,old)
        (ROOT/'manuscript'/name).write_text(text.replace(old,new))
    print(json.dumps({'status':'TWO_APPROVED_CLARIFICATIONS_WRITTEN',
                      'algorithm_modified':False,'experiments_modified':False}))

if __name__=='__main__':main()

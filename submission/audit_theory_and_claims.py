"""Compatibility entry for this revision's finite proof tests and query audit."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    tests=subprocess.run([sys.executable,'scripts/test_query_selection.py'],cwd=ROOT,capture_output=True,text=True,check=True)
    audit=subprocess.run([sys.executable,'submission/audit_query_results.py'],cwd=ROOT,capture_output=True,text=True,check=True)
    result={'revision':'partial-score-certificates-1','status':'PASS_SCOPED_CURRENT_THEORY_AND_CLAIMS',
            'finite_test_stdout':tests.stdout.strip(),
            'panel_audit':json.loads((ROOT/'submission/query-results-audit.json').read_text()),
            'claim_evidence':'submission/query-claim-evidence.md',
            'scope':'Finite certificate consistency and complete declared-family arithmetic; no human proof certification or novelty guarantee.'}
    (ROOT/'submission/theory-and-claims-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()

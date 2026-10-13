"""Final idempotent editorial layer; never changes numeric table rows."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def apply(p):
    s=p.read_text();old=s
    if p.name=='query-baselines.tex' or p.name.startswith('query-full-baselines-'):
        s=s.replace(' & Returned & Precision',r' & Returned (outputs) & Precision')
        if 'Risk denotes $R(C)$' not in s:
            s=s.replace(r'\caption{',r'\caption{Risk denotes $R(C)$; Returned is the mean output count $K$. ',1)
    if p.name.startswith('nontrivial-'):
        s=s.replace('Each configuration has 40 splits.','Each panel--depth setting has 40 splits.')
    if p.name=='matched-tie-control.tex':
        s=s.replace(r'$\Delta K$ & Masks/40 & Sign/40',r'$\Delta K$ & \shortstack{Changed\\sets/40} & \shortstack{Changed\\signs/40}')
        s=s.replace('Masks/40 counts changed retained sets','Changed sets/40 counts changed retained sets')
        s=s.replace('Sign/40 counts changes','Changed signs/40 counts changes')
        s=s.replace('ties count as zero.','a zero returned-count difference has sign zero.')
    if p.name=='query-prefix-example.tex':s=s.replace('first seeded split of full WMT23','first seeded split of thirteen-stream WMT23')
    if s!=old:p.write_text(s)
def main():
    for p in (ROOT/'manuscript/tables').glob('*.tex'):apply(p)
    print('Applied final table captions/headers; scientific rows unchanged')
if __name__=='__main__':main()

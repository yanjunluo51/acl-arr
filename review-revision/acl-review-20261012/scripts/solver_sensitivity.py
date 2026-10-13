"""Solver sensitivity of the outcome-grouped joint MILP on a stratified sample.

Four targets per panel x depth x stopping cell (seeded draw from the 1,920
audited mean targets) are re-solved from empty history with HiGHS presolve on
and off at 10 s and 60 s nominal limits. The recorded numerically closed
joint minimum is the reference value.
"""
import csv
import json
import multiprocessing
import random
import time
import numpy as np
import scipy.optimize
from common import EXP, ROOT, instance
import compact_joint_certificate as cj

PRESOLVE = {'value': True}
_milp = scipy.optimize.milp


def patched(*a, **kw):
    kw.setdefault('options', {})['presolve'] = PRESOLVE['value']
    return _milp(*a, **kw)


cj.milp = patched


def task(args):
    rec, presolve, limit = args
    PRESOLVE['value'] = presolve
    c = instance(rec['dataset'], 'mean', int(rec['split']), float(rec['q']))
    ids = np.flatnonzero(c['selected']); ids = ids[np.argsort(c['tie'][ids])]
    rows = c['f'][:, ids].T.tolist(); caps = c['p'][ids].tolist()
    eps = int(rec['epsilon'])
    t0 = time.monotonic()
    r = cj.compact_certificate(rows, caps, c['budget'], eps, separated=False, seconds=limit, outcome_counts=True)
    return dict(dataset=rec['dataset'], split=int(rec['split']), q=float(rec['q']), stopping=rec['stopping'],
                presolve=presolve, limit=limit, recorded=int(rec['joint_upper']), value=int(r['queries']),
                lower=int(r.get('joint_lower_bound', r['queries'])), proven=bool(r['joint_optimal']),
                seconds=time.monotonic() - t0, variables=int(r['max_variables']),
                constraints=int(r['max_constraints']), active=int(rec['active_rows']), T=int(rec['T']))


def main():
    recs = list(csv.DictReader((ROOT / 'outputs/full-mean-grid-20261005/audited_records.csv').open()))
    cells = {}
    for r in recs:
        cells.setdefault((r['dataset'], r['q'], r['stopping']), []).append(r)
    rng = random.Random(20261012)
    sample = [x for k in sorted(cells) for x in rng.sample(cells[k], 4)]
    jobs = [(x, p, l) for x in sample for p in (True, False) for l in (10.0, 60.0)]
    out = EXP / 'outputs' / 'solver_sensitivity.jsonl'
    with out.open('w') as f, multiprocessing.get_context('spawn').Pool(3) as pool:
        for i, res in enumerate(pool.imap_unordered(task, jobs)):
            f.write(json.dumps(res) + '\n'); f.flush()
            if i % 50 == 0:
                print(i, len(jobs), flush=True)


if __name__ == '__main__':
    main()

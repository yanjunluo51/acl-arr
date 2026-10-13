"""Re-solve the 48 non-full SummEval mean unions with HiGHS presolve off.

The original oracle run used default solver options. Presolve once returned an
incorrect union optimum on the original panels, which can create a spurious
strict joint gain. The joint value is an integer-checked feasible witness and
is not affected; only the union value is re-solved here.
"""
import json, math, multiprocessing, sys, time
from pathlib import Path
EXP = Path(__file__).resolve().parents[1]
ROOT = EXP.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deduplicated_certificates import union_certificate


def run(item):
    x, name, e, rec = item
    t0 = time.monotonic()
    u = union_certificate(rows=x['truth'], caps=x['caps'], budget=x['budget'], epsilon=e,
                          seconds=600, presolve=False)
    return dict(composition=x['composition'], q=x['q'], stop=name, status=u['status'],
                union_presolve_off=u.get('union_minimum'), union_recorded=rec['union']['union_minimum'],
                joint=rec['joint']['queries'], wall=round(time.monotonic() - t0, 2))


if __name__ == '__main__':
    xs = [json.loads(l) for l in (EXP / 'private/traces-private.jsonl').read_text().splitlines()]
    old = {(tuple(r['composition']), r['q'], r['stop']): r
           for r in map(json.loads, (EXP / 'private/summeval_mean_oracles_records.jsonl').read_text().splitlines())}
    jobs = [(x, n, e, old[(tuple(x['composition']), x['q'], n)])
            for x in xs if x['aggregator'] == 'mean' and sum(map(sum, x['truth'])) > x['budget']
            for n, e in [('primary', math.ceil(.02 * x['selected'])), ('exact', 0)]]
    assert len(jobs) == 48
    with multiprocessing.get_context('spawn').Pool(3) as pool, (EXP / 'outputs/summeval_union_recheck.jsonl').open('w') as f:
        for r in pool.imap_unordered(run, jobs):
            f.write(json.dumps(r) + '\n'); f.flush()

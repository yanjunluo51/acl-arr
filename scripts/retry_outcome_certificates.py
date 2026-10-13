"""Append-only higher-resource checks of unresolved primary outcome runs."""
import os
for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)  # Saved arbitrary-precision query masks.
import multiprocessing
import time
from pathlib import Path
from compact_joint_certificate import compact_certificate
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/outcome-joint-scale'


def task(x):
    value = compact_certificate(x['rows'], x['caps'], x['budget'],
                                seconds=600, outcome_counts=True)
    return dict(primary_key=[x['dataset'], x['split'], x['q'], x['requested_size']],
                seconds_limit=600, primary_record_preserved=True, **value)


def main():
    assert not (OUT/'retry-records.jsonl').exists()
    records = [json.loads(x) for x in (OUT/'records.jsonl').open()]
    cases = [x for x in records if x['status'] != 'OPTIMAL']
    protocol = dict(resource_followup=True, seconds=600, cases=[
        [x['dataset'], x['split'], x['q'], x['requested_size']] for x in cases],
        primary_60_second_results_unchanged=True, planned_before_retry_results=True)
    (OUT/'retry-protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    start = time.monotonic()
    progress = dict(status='RUNNING', cases=0, expected_cases=len(cases))
    def save():
        progress['elapsed_seconds'] = time.monotonic()-start
        (OUT/'retry-progress.json').write_text(json.dumps(progress, indent=2)+'\n')
    save()
    with (OUT/'retry-records.jsonl').open('w') as f, multiprocessing.get_context('spawn').Pool(3) as pool:
        for value in pool.imap_unordered(task, cases):
            f.write(json.dumps(value, separators=(',', ':'))+'\n'); f.flush()
            progress['cases'] += 1; save()
            print(value['primary_key'], value['status'], value['queries'], value['seconds'], flush=True)
    progress['status'] = 'COMPLETE_EXECUTION_PENDING_AUDIT'; save()


if __name__ == '__main__':
    main()

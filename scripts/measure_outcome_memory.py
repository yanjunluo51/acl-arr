"""Full-panel outcome-program RSS measurements on split zero of all panels."""
import os
for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
import gc
import json
import sys
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)
import threading
import time
from pathlib import Path
import psutil
from compact_joint_certificate import compact_certificate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/outcome-joint-scale'


def main():
    assert not (OUT/'memory-probes.json').exists()
    values = [json.loads(x) for x in (OUT/'records.jsonl').open()]
    cases = [x for x in values if x['split'] == 0 and x['requested_size'] == 'full']
    assert len(cases) == 12
    protocol = dict(cases=[[x['dataset'], x['q']] for x in cases],
                    sampling_interval_seconds=.01, entire_full_panel=True,
                    includes_python_inputs_solver_and_resident_cache=True,
                    timing_not_a_controlled_speed_comparison=True)
    (OUT/'memory-protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    records = []
    for x in cases:
        gc.collect()
        process = psutil.Process(); done = threading.Event()
        memory = [process.memory_info().rss]
        def monitor():
            while not done.wait(.01):
                memory.append(process.memory_info().rss)
        thread = threading.Thread(target=monitor, daemon=True); thread.start()
        a = compact_certificate(x['rows'], x['caps'], x['budget'], outcome_counts=True)
        memory.append(process.memory_info().rss); done.set(); thread.join()
        if a['joint_optimal']:
            assert a['queries'] == x['queries']
        records.append(dict(dataset=x['dataset'], q=x['q'], active_rows=x['active_rows'],
                            rss_baseline_bytes=memory[0], sampled_peak_rss_bytes=max(memory),
                            status=a['status'], query_count=a['queries'], seconds=a['seconds']))
    (OUT/'memory-probes.json').write_text(json.dumps(dict(protocol=protocol, records=records), indent=2)+'\n')
    print('Recorded 12 full-panel sampled RSS measurements')


if __name__ == '__main__':
    main()

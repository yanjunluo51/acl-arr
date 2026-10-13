"""Common recorded logical-score accounting; retains different guarantees."""
import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/common-information-20261005'

def main():
    assert not OUT.exists();OUT.mkdir()
    old=json.loads((ROOT/'outputs/query_metrics.json').read_text())
    score=json.loads((ROOT/'outputs/review-score/results.json').read_text())
    stops={}
    for x in csv.DictReader((ROOT/'outputs/tolerance-sensitivity/stop_records.csv').open()):
        if x['method']=='reference_priority' and x['tau']=='1/50':stops[(x['dataset'],x['aggregator'],int(x['split']),float(x['q']))]=x
    rows=[]
    common={}
    for x in old['baseline_records']:
        if x['method'] not in ['zero_query_structural','envelope_crc']:continue
        r=dict(x);key=(r['dataset'],r['aggregator'],r['split'],r['q'])
        rows.append(r)
        if r['method']=='zero_query_structural':
            common[key]=r
            st=stops[key]
            assert int(st['selected_count'])==r['selected_count']
            z=dict(r,method='reference_priority',candidate_test_entries=int(st['queries']),
                   returned_count=int(st['returned_count']),selected_coverage=float(st['selected_coverage']),
                   risk=float(st['risk']),certificate='deterministic_batch_count_gap',
                   epsilon=int(st['epsilon']),candidate_calibration_entries=0,pool_calibration_entries=0)
            rows.append(z)
    for x in score['records']:
        if abs(x['alpha']-.10)<1e-12:
            key=(x['dataset'],x['aggregator'],x['split'],x['q']);c=common[key]
            assert x['n_test_items']==c['n_test_items'] and x['selected_count']==c['selected_count']
            rows.append(dict(x))
    normalized=[]
    fields=['dataset','aggregator','split','q','method','certificate','n_test_items','T','k','selected_count','returned_count','selected_coverage','risk','candidate_reference_entries','candidate_calibration_entries','candidate_test_entries','pool_reference_entries','pool_calibration_entries','pool_test_entries']
    for r in rows:
        z={k:r[k] for k in fields};scale=r['n_test_items']*r['T']
        z['candidate_total_entries']=sum(r[k] for k in ['candidate_reference_entries','candidate_calibration_entries','candidate_test_entries'])
        z['pool_total_entries']=sum(r[k] for k in ['pool_reference_entries','pool_calibration_entries','pool_test_entries'])
        for part in ['reference','calibration','test','total']:z['candidate_'+part+'_over_NT']=z['candidate_'+part+'_entries']/scale
        z['over_budget']=int(r['risk']>.10+1e-12)
        normalized.append(z)
    assert len(normalized)==3840
    groups={}
    for r in normalized:groups.setdefault((r['dataset'],r['aggregator'],r['q'],r['method']),[]).append(r)
    summaries=[]
    for key,g in sorted(groups.items()):
        assert len(g)==40
        z=dict(zip(['dataset','aggregator','q','method'],key),splits=40,certificate=g[0]['certificate'])
        for field in ['returned_count','selected_coverage','risk','candidate_reference_over_NT','candidate_calibration_over_NT','candidate_test_over_NT','candidate_total_over_NT']:
            z[field]=statistics.fmean(r[field] for r in g)
        z['over_budget']=sum(r['over_budget'] for r in g);summaries.append(z)
    for name,data in [('records.csv',normalized),('summary.csv',summaries)]:
        with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    receipt=dict(status='PASS_COMMON_RECORDED_INFORMATION_AND_RISK_ACCOUNTING',records=3840,summary_cells=96,
        panels=3,pooling_rules=2,depths=4,splits=40,alpha=.10,reference_primary_gap=True,
        guarantees_not_equalized=True,grouped_SCORE_unequal_WMT24_not_added=True,
        candidate_reference_setup_charged_as_recorded_not_claimed_minimal=True,
        posthoc_full_matrix_for_validation_not_selection_visible_information=True,new_inference=False)
    (OUT/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()

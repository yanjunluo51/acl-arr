"""Independent reply, mask and first-stop checks for all intervention paths."""
import csv,gzip,json,math,time
from pathlib import Path
import numpy as np
from analyze_acquisition_mechanisms import prepare
from run_tolerance_sensitivity import scan_path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/query-mechanism-interventions'

def check_choice(c,p):
    truth=c['truth'];T=c['T'];m=c['m'];lp=c['lp'];known=np.zeros((m,T),bool);low=np.zeros(m,np.int64)
    row_oracle=p['method'] in ('oracle_row','oracle_both');cand_oracle=p['method'] in ('oracle_candidate','oracle_both')
    estimate=truth if row_oracle else c['ticks'];scale=1 if row_oracle or not c['quantized'] else 10**12
    rank=truth if cand_oracle else c['ticks'];n=0
    for i,r,f in p['trace']:
        candidates=np.flatnonzero(~known.all(axis=1));total=low*scale+np.where(known,0,estimate).sum(axis=1)
        expect=int(candidates[np.lexsort((c['tie'][c['ids'][candidates]],total[candidates]))[0]])
        rr=np.flatnonzero(~known[expect]);cr=int(rr[np.lexsort((rr,rank[expect,rr]))[0]])
        assert i==expect and r==cr,(p['method'],n,i,r,expect,cr)
        known[i,r]=True;low[i]+=f;n+=1
    return n

def main():
    start=time.monotonic();records=list(csv.DictReader((OUT/'records.csv').open()));assert len(records)==15360
    saved={(x['dataset'],x['aggregator'],int(x['split']),float(x['q']),x['method'],x['stopping']):x for x in records}
    paths=replies=choices=cases=0
    with gzip.open(OUT/'traces.jsonl.gz','rt') as log:
        for line in log:
            case=json.loads(line);key=tuple(case['key']);c=prepare(key);eps=math.ceil(c['S']/50)
            assert case['caps']==c['lp'].tolist() and case['budget']==c['budget'] and case['free']==c['free']
            for p in case['paths']:
                tr=np.asarray(p['trace'],np.int64).reshape(-1,3)
                assert len({(i,r) for i,r,_ in p['trace']})==len(tr)
                assert np.all(c['truth'][tr[:,0],tr[:,1]]==tr[:,2])
                states=scan_path(c['lp'],tr[:,[0,2]],c['T'],c['budget'],c['free'],np.array([eps,0],np.int64))
                assert len(tr)==states[1,0]
                lo=np.zeros(c['m'],np.int64);up=c['T']*c['lp'].copy();cursor=0
                for j,stop in enumerate(('primary','exact')):
                    st=p['stops'][stop];Q,vl,vh=map(int,states[j]);assert (Q,vl,vh)==(st['queries'],st['V_lower'],st['V_upper'])
                    s=saved[(*key,p['method'],stop)]
                    for f in ['queries','V_lower','V_upper','gap','epsilon','upper_cost','true_cost']:assert int(s[f])==st[f]
                    while cursor<Q:
                        i,r,f=map(int,tr[cursor]);lo[i]+=f;up[i]-=int(c['lp'][i])-f;cursor+=1
                    # Independent stable upper prefix, not the runner's helper.
                    order=sorted(range(c['m']),key=lambda i:(int(up[i]),int(c['tie'][c['ids'][i]])))
                    remaining=c['budget'];mask=np.zeros(c['m'],bool)
                    for i in order:
                        if up[i]>remaining:break
                        remaining-=int(up[i]);mask[i]=True
                    expected=np.unpackbits(np.frombuffer(bytes.fromhex(st['active_mask']),np.uint8))[:c['m']].astype(bool)
                    assert np.array_equal(mask,expected) and c['free']+int(mask.sum())==vl
                    assert int(up[mask].sum())==st['upper_cost'] and int(c['truth'].sum(axis=1)[mask].sum())==st['true_cost']<=st['upper_cost']<=c['budget']
                if key[2]==0:choices+=check_choice(c,p)
                paths+=1;replies+=len(tr)
            cases+=1
            if cases%160==0:print(cases,round(time.monotonic()-start,1),flush=True)
    assert cases==1920 and paths==7680
    receipt={'status':'PASS_FULL_INTERVENTION_REPLY_MASK_FIRST_STOP_AUDIT','configuration_cases':cases,'paths_checked':paths,'stop_records_checked':len(records),'actual_replies_checked':replies,'choice_steps_independently_checked':choices,'choice_configurations':48,'full_information_oracle_diagnostic_only':True,'elapsed_seconds':time.monotonic()-start}
    (OUT/'independent-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

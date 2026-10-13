"""Portable saved-evidence validation of current source/code delivery.

Default checks use only the standard library and saved derived observations.
--verify-optima requires scipy and independently solves all small-batch minima.
--replay-tables requires the recorded numerical dependencies. No private history,
raw input panels, network calls or model inference are needed for these modes.
"""
import argparse,ast,csv,hashlib,itertools,json,math,statistics,subprocess,sys
from pathlib import Path
from verify_html_bundle import main as prior_checks

def read(path):return list(csv.DictReader(path.open()))
def capacity(values,b):
    return max(bin(mask).count('1') for mask in range(1<<len(values)) if sum(v for i,v in enumerate(values) if (mask>>i)&1)<=b)
def close(a,b):
    if b is None:assert a in (None,'')
    else:assert math.isclose(float(a),b,rel_tol=1e-11,abs_tol=1e-11),(a,b)
def summary_check(rows,cells,keys,fields,extra):
    groups={}
    for x in rows:groups.setdefault(tuple(x[k] for k in keys),[]).append(x)
    assert len(groups)==len(cells)
    for cell in cells:
        k=tuple(cell[a] for a in keys);g=groups[k];assert len(g)==40 and len({x['split'] for x in g})==40
        assert int(cell['splits'])==40
        for f in fields:close(cell[f],statistics.fmean(float(x[f]) for x in g))
        for name,fun in extra.items():close(cell[name],fun(g))

def joint(root):
    out=root/'outputs/joint-certificates';cases={};count=0
    for line in (out/'instances.jsonl').open():
        z=json.loads(line);k=tuple(z['key']);assert k not in cases;cases[k]=z
        rows,caps=z['flips'],z['caps'];m=len(rows);T=len(rows[0]);assert 1<=m<=4
        assert len(z['original_output_ids'])==len(set(z['original_output_ids']))==m
        assert all(0<=v<=caps[i] for i,row in enumerate(rows) for v in row)
        for x in z['records']:
            obs=z['observed'][x['history']];query=x['query_mask'];masks=[]
            for i,o in enumerate(obs):
                new=(query>>(i*T))&((1<<T)-1);assert not new&o;masks.append(new|o)
            assert int(x['queries'])==sum(bin(a).count('1')-bin(b).count('1') for a,b in zip(masks,obs))
            lo=[sum(v for r,v in enumerate(row) if (masks[i]>>r)&1) for i,row in enumerate(rows)]
            up=[lo[i]+(T-bin(masks[i]).count('1'))*caps[i] for i in range(m)]
            b=x['budget'];e=x['epsilon'];vl,vh=capacity(up,b),capacity(lo,b)
            assert (vl,vh)==(x['V_lower'],x['V_upper']) and vh-vl<=e
            assert capacity([sum(v) for v in rows],b)==x['true_optimum']
            assert sum(up[i] for i in range(m) if (x['safe_mask']>>i)&1)<=b
            assert x['split_queries']>=x['queries'] and x['sharing_saving']==x['split_queries']-x['queries']
            assert x['N']==m and x['T']==T and x['k']==max(1,round(x['q']*m)) and b==2*x['k']*7*T//10
            count+=1
    expected=set(itertools.product(['RewardBench2','WMT23','WMT23_without_synthetic_ref','WMT24-en-de','WMT24-en-es','WMT24-ja-zh'],['mean','median'],range(40),[.05,.1,.2,.3]))
    assert set(cases)==expected and count==7680
    rows=read(out/'panel_records.csv');assert len(rows)==count
    index={(*k,x['history'],x['epsilon']):x for k,z in cases.items() for x in z['records']}
    for x in rows:
        k=(x['dataset'],x['aggregator'],int(x['split']),float(x['q']),x['history'],int(x['epsilon']));y=index[k]
        for f in x:
            if isinstance(y[f],str):assert x[f]==y[f]
            else:close(x[f],y[f])
    summary_check(rows,read(out/'panel_summary.csv'),['dataset','aggregator','q','history','epsilon'],['queries','split_queries','sharing_saving','true_optimum','dual_use_fraction','observed_entries'],{'strict_sharing_benefit':lambda g:sum(int(x['sharing_saving'])>0 for x in g),'positive_minima':lambda g:sum(int(x['queries'])>0 for x in g)})
    discovery=read(out/'discovery_records.csv');assert len(discovery)==15360;dindex={(x['dataset'],x['aggregator'],int(x['split']),float(x['q']),x['method'],int(x['epsilon'])):x for x in discovery};paths=0;replies=0
    for line in (out/'discovery_paths.jsonl').open():
        z=json.loads(line);k=tuple(z['key']);case=cases[k];truth=case['flips'];caps=case['caps'];T=len(truth[0]);m=len(truth);b=case['records'][0]['budget']
        for p in z['paths']:
            lo=[0]*m;up=[T*v for v in caps];seen=set();first={}
            for step in range(len(p['trace'])+1):
                vl,vh=capacity(up,b),capacity(lo,b)
                for e in (0,1):
                    if e not in first and vh-vl<=e:first[e]=(step,vl,vh)
                if step==len(p['trace']):break
                r,i,f=p['trace'][step];assert (i,r) not in seen and f==truth[i][r] and caps[i]>0;seen.add((i,r));lo[i]+=f;up[i]-=caps[i]-f
            for e,st in [(0,p['exact']),(1,p['primary'])]:
                step,vl,vh=first[e];assert (step,vl,vh)==(st['queries'],st['V_lower'],st['V_upper'])
                # Recompute this state's mask and its returned count.
                lower=[0]*m;upper=[T*v for v in caps]
                for r,i,f in p['trace'][:step]:lower[i]+=f;upper[i]-=caps[i]-f
                order=sorted(range(m),key=lambda i:(upper[i],z['ties'][i]));remaining=b;mask=[False]*m
                for i in order:
                    if upper[i]>remaining:break
                    remaining-=upper[i];mask[i]=True
                assert mask==st['mask'] and sum(mask)==vl
                x=dindex[(*k,p['method'],e)];minimum=index[(*k,'empty',e)]['queries']
                assert int(x['queries'])==step and int(x['minimum'])==minimum and step>=minimum
                close(x['discovery_ratio'],step/minimum if minimum else None)
            paths+=1;replies+=len(p['trace'])
    assert paths==7680
    summary_check(discovery,read(out/'discovery_summary.csv'),['dataset','aggregator','q','epsilon','method'],['queries','minimum'],{'positive_minima':lambda g:sum(int(x['minimum'])>0 for x in g),'mean_ratio':lambda g:statistics.fmean(float(x['discovery_ratio']) for x in g if x['discovery_ratio']) if any(x['discovery_ratio'] for x in g) else None,'max_ratio':lambda g:max((float(x['discovery_ratio']) for x in g if x['discovery_ratio']),default=None)})
    return {'instances':len(cases),'witnesses':count,'small_batch_policy_paths':paths,'small_batch_replies':replies,'raw_scores_required':False}

def interventions(root):
    out=root/'outputs/query-mechanism-interventions';rows=read(out/'records.csv');assert len(rows)==15360
    for x in rows:
        for name in ['queries','reference_queries','width_queries','fixed_queries','delta_reference','delta_width','V_lower','V_upper','gap','epsilon','upper_cost','true_cost']:x[name]=int(x[name])
        assert x['queries']<=int(x['active_rows'])*int(x['T'])
        assert x['delta_reference']==x['queries']-x['reference_queries'] and x['delta_width']==x['queries']-x['width_queries']
        assert x['V_upper']-x['V_lower']==x['gap']<=x['epsilon']
        assert x['true_cost']<=x['upper_cost']<=int(x['budget'])
        if x['method']=='reference_priority':assert x['delta_reference']==0
    summary_check(rows,read(out/'summary.csv'),['dataset','aggregator','q','method','stopping'],['queries','delta_reference','delta_width','V_lower','V_upper','gap','upper_cost','true_cost'],{'strict_improvements_reference':lambda g:sum(x['delta_reference']<0 for x in g),'strict_losses_reference':lambda g:sum(x['delta_reference']>0 for x in g)})
    proof=json.loads((out/'independent-check.json').read_text());assert proof['status']=='PASS_FULL_INTERVENTION_REPLY_MASK_FIRST_STOP_AUDIT' and proof['stop_records_checked']==len(rows)
    return {'records':len(rows),'summary_cells':384,'full_reply_audit_receipt':proof}

def main(root,manifest=True,replay=False,optima=False):
    root=root.resolve();old=prior_checks(root,manifest,False);a=joint(root);b=interventions(root)
    if optima:subprocess.run([sys.executable,str(root/'scripts/check_joint_panels.py'),'--no-write'],cwd=root,check=True,stdout=sys.stderr)
    if replay:
        tree=ast.parse((root/'scripts/verify_interface_delivery.py').read_text());nodes=[n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RENDERERS' for t in n.targets)];layers=ast.literal_eval(nodes[0])+['render_nontrivial_certification.py','render_main10_editorial.py','render_html_revision.py','render_joint_revision.py','render_latest_sentence_review.py']
        tables={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'manuscript/tables').glob('*.tex')};assert len(tables)==71
        for name in layers:subprocess.run([sys.executable,str(root/'scripts'/name)],cwd=root,check=True,stdout=sys.stderr)
        for n,h in tables.items():assert hashlib.sha256((root/'manuscript/tables'/n).read_bytes()).hexdigest()==h,n
    return {'status':'PASS_PORTABLE_SENTENCE_REVIEW_SAVED_EVIDENCE','prior_controls':old,'joint':a,'interventions':b,'independent_optima_recomputed':optima,'tables_regenerated':71 if replay else None,'render_layers':16 if replay else None,'human_proof_certified':False,'scientific_validity_certified':False,'complete_redistribution_authorized':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--author-live-check',action='store_true');p.add_argument('--replay-tables',action='store_true');p.add_argument('--verify-optima',action='store_true');a=p.parse_args();print(json.dumps(main(a.root,not a.author_live_check,a.replay_tables,a.verify_optima),indent=2))

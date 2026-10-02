"""Read-only source audit; writes exclusively to a new review directory."""
from pathlib import Path
import sys, json, hashlib, importlib.util, math, io, re, struct
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
sys.dont_write_bytecode = True

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / '호진파일/outputs/데이터_저장'
OUT = BASE / 'outputs/independent_hand_review_20261002'
OUT.mkdir(parents=True, exist_ok=True)
EXPERIMENTS = BASE.parent / 'experiments'
sys.path.insert(0, str(EXPERIMENTS / 'v13'))
spec = importlib.util.spec_from_file_location('prior_audit', EXPERIMENTS / 'v14/allsessions_audit.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
import qv13

def finite(v):
    if isinstance(v, dict): return {str(k): finite(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)): return [finite(x) for x in v]
    if isinstance(v, np.generic): v = v.item()
    if isinstance(v, float) and not math.isfinite(v): return None
    return v

def read(p): return pd.read_csv(p, encoding='utf-8-sig')
def one(d, suffix): return next(d.glob('Session_*' + suffix))
def corr(x,y):
    x,y=np.asarray(x,float),np.asarray(y,float)
    ok=np.isfinite(x)&np.isfinite(y)
    if ok.sum()<3 or np.std(x[ok])==0 or np.std(y[ok])==0: return None
    return float(np.corrcoef(x[ok],y[ok])[0,1])
def gap_stats(frame):
    a=np.sort(np.unique(np.asarray(frame,int)))
    dif=np.diff(a)
    missing=int(np.maximum(dif-1,0).sum())
    return {'observed':len(a),'span':int(a[-1]-a[0]+1),'missing':missing,
            'missing_pct':100*missing/(a[-1]-a[0]+1),'max_jump':int(dif.max()) if len(dif) else 0}

inventory=[]
for p in sorted(DATA.rglob('*')):
    if not p.is_file(): continue
    h=hashlib.sha256()
    with p.open('rb') as f:
        while chunk:=f.read(1024*1024): h.update(chunk)
    entry={'file':str(p.relative_to(DATA)),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
    if p.suffix=='.csv':
        df=read(p); entry.update(rows=len(df),columns=len(df.columns),column_names=list(df.columns))
    elif p.suffix=='.json':
        j=json.loads(p.read_text(encoding='utf-8-sig')); entry['keys']=list(j)
    elif p.suffix=='.png':
        with Image.open(p) as im: entry.update(width=im.width,height=im.height)
    elif p.suffix=='.avi':
        with p.open('rb') as f: head=f.read(100000)
        k=head.find(b'avih')
        if k>=0:
            vals=struct.unpack('<14I',head[k+8:k+64])
            entry.update(header_fps=1e6/vals[0] if vals[0] else None,header_frames=vals[4],width=vals[8],height=vals[9])
    inventory.append(entry)
pd.DataFrame([{k:v for k,v in a.items() if k!='column_names'} for a in inventory]).to_csv(OUT/'file_inventory.csv',index=False,encoding='utf-8-sig')

sessions=[]; summary=[]; trials=[]; split_checks=[]; l2=[]
for session_i,d in enumerate(sorted(x for x in DATA.iterdir() if x.is_dir())):
    meta=json.loads(one(d,'_metadata.json').read_text(encoding='utf-8-sig'))
    ts=read(one(d,'_trials_summary.csv')); raw=read(one(d,'_continuous_raw.csv'))
    lm=read(one(d,'_landmarks.csv')); dc=read(one(d,'_distance_comparison.csv'))
    fq=read(one(d,'_frame_quality.csv')); vt=read(d/'video_timestamps.csv')
    group=meta['subject']['group']; label=['Healthy','Patient_before','Patient_after'][session_i]
    ts=ts.assign(session=d.name,label=label,group=group)
    summary.append(ts)
    rec={'session':d.name,'label':label,'group':group,'affected_side':meta['subject']['affected_side'],
         'trial_ids':list(ts.Trial.unique()),'trial_count':ts.Trial.nunique(),'summary_rows':len(ts),
         'metadata_video':meta['video'],'landmark_unique_frames':lm.Frame_ID.nunique(),
         'quality_frames':len(fq),'timestamps_frames':len(vt),'raw_rows':len(raw),
         'raw_time_range':[raw.time_s.min(),raw.time_s.max()],
         'time_range_video':[vt.elapsed_s.min(),vt.elapsed_s.max()],
         'rs_landmark_ok_pct':100*(lm.RS_Status=='ok').mean(),
         'missing_root_videos':[v for v in meta['video']['files'] if not (d/v).exists()],
         'calibrated_mga_missing_pct':100*ts.MGA_mm_3D_cal.isna().mean(),
         'interrupted_rows':int(ts.Interrupted.sum()),'frame_quality_no_hands_pct':100*fq.hands.isna().mean(),
         'trial_hand_stats':{},'quality_time_vs_video':{},'hardware_by_trial_hand':[]}
    matched=fq.merge(vt,left_on='frame_id',right_on='frame_id')
    delta=matched.time-matched.elapsed_s
    rec['quality_time_vs_video']={'n':len(matched),'offset_median':delta.median(),'offset_min':delta.min(),'offset_max':delta.max()}
    for h in ('Left','Right'):
        q=qv13.run_pilot(str(d),hand=h,rest_mode='fallback')
        strict=qv13.run_pilot(str(d),hand=h,rest_mode='strict')
        hts=ts[ts.Hand==h]
        rec['trial_hand_stats'][h]={'n':len(hts),'tam_median':hts.TAM_total_deg.median(),
            'seg_rate_median':np.median([r['seg_rate'] for r in q['records']]),
            'fallback_pass_count':sum(r['pass'] for r in q['records']),
            'strict_baseline_unavailable_count':sum('segment_baseline_unavailable' in r['reasons'] for r in strict['records']),
            'dt_ref_prior_per_hand':q['session_dt_ref_s'],'rs_valid_rate_median':hts.RS_Valid_Rate.median()}
        for qr in q['records']:
            no=int(qr['trial'].split('_')[-1]); tr=hts[hts.Trial==f'Trial #{no}'].iloc[0]
            item={'session':d.name,'label':label,'group':group,'hand':h,'trial':no,
                'tam':tr.TAM_total_deg,'duration':tr.Duration_s,'cycles':tr.Cycles,
                'seg_rate':qr['seg_rate'],'fallback_q_pass':qr['pass'],'reasons':qr['reasons']}
            sr=raw[(raw.hand==h)&(raw.Trial==f'Trial #{no}')]
            # Some source files use Trial #N; index records check this explicitly.
            if sr.empty: sr=raw[(raw.hand==h)&(raw.time_s>=tr.Start_s)&(raw.time_s<=tr.End_s)]
            ids=sr.Frame_ID.unique()
            if len(ids)>1:
                item['saved_id']=gap_stats(ids)
                hd=dc[(dc.Hand==h)&dc.Frame_ID.isin(ids)].drop_duplicates('Frame_ID').sort_values('Frame_ID')
                item['hardware_color']=gap_stats(hd.Color_Frame_Number.dropna())
                item['hardware_depth']=gap_stats(hd.Depth_Frame_Number.dropna())
                times=hd.capture_monotonic_s.to_numpy()
                item['capture_dt_median']=float(np.median(np.diff(times)))
                item['capture_dt_max']=float(np.max(np.diff(times)))
                rr=sr.sort_values('Frame_ID')
                t=rr.time_s.to_numpy(); a=rr.Index_PIP_filt.to_numpy()
                dt=np.diff(t); da=np.diff(a); valid=(dt>0)&np.isfinite(da)
                item['recomputed_pip_peak_abs_speed']=float(np.max(np.abs(da[valid]/dt[valid])))
                item['duplicate_or_nonpositive_raw_dt_count']=int((dt<=0).sum())
                capture=rr[['Frame_ID','Index_PIP_filt']].merge(hd[['Frame_ID','capture_monotonic_s']],on='Frame_ID').sort_values('Frame_ID')
                dt_capture=np.diff(capture.capture_monotonic_s)
                da_capture=np.diff(capture.Index_PIP_filt)
                good=(dt_capture>0)&np.isfinite(da_capture)
                item['capture_clock_pip_peak_abs_speed']=float(np.max(np.abs(da_capture[good]/dt_capture[good])))
                # robust joint ranges without rewriting source summaries
                cs=[c for c in rr if c.endswith('_filt') and any(c.startswith(f+'_') for f in ('Thumb','Index','Middle','Ring','Pinky')) and 'Abd' not in c and c!='Thumb_CMC_filt']
                item['robust_tam_p95_p5']=float((rr[cs].quantile(.95)-rr[cs].quantile(.05)).sum())
                flex=180-rr[cs]
                item['current_f_sum14_p95']=float(flex.sum(axis=1,min_count=14).quantile(.95))
            trials.append(item)
    # Compare every split CSV row to the session source on its frame/hand keys.
    source_tables={'_continuous_raw.csv':raw,'_landmarks.csv':lm,'_distance_comparison.csv':dc,'_trials_summary.csv':ts.drop(columns=['session','label','group']), '_frame_quality.csv':fq}
    for p in sorted((d/'split').rglob('*.csv')):
        suffix=next((k for k in source_tables if p.name.endswith(k)),None)
        if suffix is None: continue
        child=read(p); parent=source_tables[suffix]
        keys=[c for c in ('Frame_ID','Hand','hand','Landmark_ID','Trial') if c in child and c in parent]
        if keys:
            z=child.merge(parent,on=keys,how='left',suffixes=('_child','_parent'),indicator=True)
            mismatches=0
            for col in child.columns:
                if col in keys or col not in parent: continue
                left,right=z[col+'_child'],z[col+'_parent']
                same=left.eq(right)|(left.isna()&right.isna())
                if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
                    same|=np.isclose(left,right,equal_nan=True)
                mismatches+=int((~same).sum())
            split_checks.append({'session':d.name,'file':str(p.relative_to(d)), 'child_rows':len(child),'join_rows':len(z),'unmatched':int((z._merge=='left_only').sum()),'mismatching_cells':mismatches})
    for p in sorted((d/'L2_metric').glob('*.json')):
        j=json.loads(p.read_text(encoding='utf-8-sig')); no=int(j['trial'].split('_')[-1]); hand=j['hand']
        src=ts[(ts.Trial==f'Trial #{no}')&(ts.Hand==hand)].iloc[0]
        l2.append({'trial':no,'hand':hand,'l2_sparc':j['m4_sparc'],'app_sparc':src.SPARC,'l2_m1_mga':j['m1_mga_mm'],'summary_mga3d':src.MGA_mm_3D,'summary_mp_raw_mga':src.MP_MGA_raw_mm,'status':j['q']['sparc_status']})
    sessions.append(rec)

all_summary=pd.concat(summary,ignore_index=True)
portfolio={}
for grp,x in all_summary.groupby('group'):
    metrics=[]
    for col in prior.CANDIDATES:
        values=pd.to_numeric(x[col],errors='coerce')
        ratios=[]
        for _,g in x.groupby(['session','Task','Hand']):
            v=pd.to_numeric(g[col],errors='coerce').dropna()
            if len(v)>=3 and abs(v.mean())>1e-9: ratios.append(1.96*np.sqrt(2)*v.std(ddof=1)/abs(v.mean())*100)
        ratio=float(np.median(ratios)) if ratios else None
        miss=100*values.isna().mean(); valid=values.dropna()
        viol=100*np.mean([not prior.plausible(col,v) for v in valid]) if len(valid) else None
        ok=miss<=20 and ratio is not None and ratio<=50 and viol is not None and viol<=5
        metrics.append({'metric':col,'variation_ratio_pct':ratio,'missing_pct':miss,'physical_violation_pct':viol,'pass':bool(ok)})
    # Cross-check against original function, never its main()/write paths.
    rows=x.rename(columns={'session':'_s','group':'_g'}).to_dict('records')
    original=prior.portfolio(rows,grp)
    for a,b in zip(metrics,original['metrics']):
        assert a['pass']==(b['verdict']=='편입가능')
        if a['variation_ratio_pct'] is not None: assert abs(a['variation_ratio_pct']-b['mdc_pct'])<1e-8
    portfolio[grp]={'rows':len(x),'pass_count':sum(a['pass'] for a in metrics),'metrics':metrics}
flips=[{'metric':h['metric'],'healthy':h,'patient':p} for h,p in zip(portfolio['Healthy']['metrics'],portfolio['Patient']['metrics']) if h['pass']!=p['pass']]
t=pd.DataFrame(trials)
correlations={'pooled':corr(t.tam,t.seg_rate),'patient_only':corr(t[t.group=='Patient'].tam,t[t.group=='Patient'].seg_rate),'by_session_hand':[]}
for (s,h),g in t.groupby(['session','hand']):
    correlations['by_session_hand'].append({'session':s,'hand':h,'n':len(g),'r':corr(g.tam,g.seg_rate)})
for population,x in [('all',t),('patient',t[t.group=='Patient'])]:
    a=x.tam-x.groupby(['session','hand']).tam.transform('mean')
    b=x.seg_rate-x.groupby(['session','hand']).seg_rate.transform('mean')
    correlations[population+'_centered_session_hand']=corr(a,b)
    correlations[population+'_robust_tam']=corr(x.robust_tam_p95_p5,x.seg_rate)
    # Descriptive residual association after controlling session×hand, duration, cycles.
    design=pd.get_dummies(x['session']+'|'+x['hand'],dtype=float).to_numpy()
    design=np.column_stack([design,x.duration,x.cycles])
    ra=x.tam.to_numpy()-design@np.linalg.lstsq(design,x.tam.to_numpy(),rcond=None)[0]
    rb=x.seg_rate.to_numpy()-design@np.linalg.lstsq(design,x.seg_rate.to_numpy(),rcond=None)[0]
    correlations[population+'_residual_session_hand_duration_cycles']=corr(ra,rb)

result={'scope':'all files inventoried; all CSV/JSON read; AVI headers inspected; no full video adjudication',
        'file_counts':pd.Series([Path(a['file']).suffix for a in inventory]).value_counts().to_dict(),
        'sessions':sessions,'portfolio':portfolio,'flips':flips,'correlations':correlations,
        'trial_results':trials,'split_checks':split_checks,'l2_comparison':l2,'inventory':inventory}
(OUT/'independent_results.json').write_text(json.dumps(finite(result),ensure_ascii=False,indent=2),encoding='utf-8')
t.drop(columns=['saved_id','hardware_color','hardware_depth','reasons'],errors='ignore').to_csv(OUT/'trial_review.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(split_checks).to_csv(OUT/'split_consistency.csv',index=False,encoding='utf-8-sig')
print(json.dumps(finite({'file_counts':result['file_counts'],'portfolio_counts':{k:v['pass_count'] for k,v in portfolio.items()},'flip_count':len(flips),'correlations':correlations,
    'split_mismatch_files':sum(a['mismatching_cells']>0 or a['unmatched']>0 for a in split_checks)}),ensure_ascii=False,indent=2))

# Decode representative MJPEG frames from every available AVI without installing codecs.
# This is a sample visual inspection, not a frame-by-frame tracking adjudication.
tiles=[]
for p in sorted(DATA.rglob('*.avi')):
    content=p.read_bytes()
    starts=[m.start() for m in re.finditer(b'\xff\xd8\xff',content)]
    for frac in (.25,.5,.75):
        if not starts: continue
        start=starts[min(int(frac*len(starts)),len(starts)-1)]
        end=content.find(b'\xff\xd9',start)+2
        try:
            im=Image.open(io.BytesIO(content[start:end])).convert('RGB')
            im.thumbnail((360,205))
            tile=Image.new('RGB',(380,240),'white'); tile.paste(im,(10,25))
            label=('Session' if p.parent==p.parents[0] and p.name in ('original.avi','mediapipe.avi') else p.parent.name)+' '+('MP' if 'mediapipe' in p.name else 'original')+f' {frac:.0%}'
            ImageDraw.Draw(tile).text((8,5),label,fill='black')
            tiles.append(tile)
        except Exception: pass
if tiles:
    sheet=Image.new('RGB',(380*6,240*math.ceil(len(tiles)/6)), '#dddddd')
    for i,tile in enumerate(tiles): sheet.paste(tile,((i%6)*380,(i//6)*240))
    sheet.save(OUT/'available_video_samples.jpg')
print('Representative video frames decoded:',len(tiles))

"""Descriptive bilateral opening/closing coordination; no clinical cutoff."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'/'bilateral_sync_20261006'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'outputs'/'extension_comparison_20261006'/'plot_dependencies'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

configs={'권미사':{'source':ROOT/'outputs'/'extension_comparison_20261006'/'analysis.json','exclude':{'Before':[],'After':[3]}},
         '최병호':{'source':ROOT/'outputs'/'choi_byungho_before5_after9_20261006'/'analysis.json','exclude':{'Before':[1,4,7,8],'After':[]}}}
PIP=[f'{j}_PIP_filt' for j in ['Index','Middle','Ring','Pinky']]
records=[]; traces={}; manifest={}
def corr(x,y):
    if len(x)<20 or np.std(x)<1e-6 or np.std(y)<1e-6:return np.nan
    return float(np.corrcoef(x,y)[0,1])
for name,config in configs.items():
    sources=json.loads(config['source'].read_text(encoding='utf-8'))['sources'];manifest[name]={'sources':sources,'exclude':config['exclude']}
    for session,path in sources.items():
        df=pd.read_csv(path)
        df=df[df.Trial.str.startswith('Trial_')&df.Protocol_Valid.eq(1)].copy()
        df['trial_number']=df.Trial.str.extract(r'(\d+)$')[0].astype(int)
        df=df[~df.trial_number.isin(config['exclude'][session])]
        assert df[PIP].notna().all().all()
        df['pip_mean']=df[PIP].mean(axis=1)
        assert not df.duplicated(['trial_number','hand','Frame_ID']).any()
        for trial,g in df.groupby('trial_number'):
            l=g[g.hand.eq('Left')][['Frame_ID','capture_unix_s','time_s','pip_mean']]
            r=g[g.hand.eq('Right')][['Frame_ID','capture_unix_s','time_s','pip_mean']]
            p=l.merge(r,on='Frame_ID',suffixes=('_left','_right'),validate='one_to_one').sort_values('Frame_ID')
            assert np.allclose(p.capture_unix_s_left,p.capture_unix_s_right,rtol=0,atol=1e-5)
            t=p.capture_unix_s_left.to_numpy();t=t-t[0]
            assert np.all(np.diff(t)>0)
            left=p.pip_mean_left.to_numpy();right=p.pip_mean_right.to_numpy()
            zero=corr(left,right)
            # Do not interpolate over acquisition gaps greater than 250 ms.
            cuts=np.r_[0,np.flatnonzero(np.diff(t)>.25)+1,len(t)]
            blocks=list(zip(cuts[:-1],cuts[1:]));start,end=max(blocks,key=lambda ab:t[ab[1]-1]-t[ab[0]])
            tb=t[start:end];lb=left[start:end];rb=right[start:end]
            dt=float(np.median(np.diff(tb)))
            grid=np.arange(tb[0],tb[-1]+dt*.01,dt)
            lu=np.interp(grid,tb,lb);ru=np.interp(grid,tb,rb)
            maxlag=min(int(np.floor(.5/dt)),int(len(grid)*.25))
            scores=[]
            for k in range(-maxlag,maxlag+1):
                if k>0:x,y=lu[:-k],ru[k:]
                elif k<0:x,y=lu[-k:],ru[:k]
                else:x,y=lu,ru
                scores.append((corr(x,y),k))
            finite=[v for v in scores if np.isfinite(v[0])]
            best,k=max(finite,key=lambda v:(v[0],-abs(v[1])))
            records.append(dict(subject=name,session=session,trial=int(trial),paired_frames=len(p),
                correlation_r=zero,sync_index_100r=100*zero,lag_ms=k*dt*1000,abs_lag_ms=abs(k)*dt*1000,
                optimized_r=best,lag_at_search_boundary=abs(k)==maxlag,
                frame_interval_ms=dt*1000,gap_count=len(blocks)-1,lag_block_duration_s=tb[-1]-tb[0],
                left_rom_deg=left.max()-left.min(),right_rom_deg=right.max()-right.min()))
            traces[(name,session,int(trial))]=(t,left,right)
result=pd.DataFrame(records)
assert result.groupby(['subject','session']).size().to_dict()=={('권미사','Before'):7,('권미사','After'):8,('최병호','Before'):5,('최병호','After'):9}
result.to_csv(OUT/'trial_sync.csv',index=False,encoding='utf-8-sig')
summary=result.groupby(['subject','session'],sort=False).agg(n=('trial','size'),
    mean_r=('correlation_r','mean'),sd_r=('correlation_r','std'),
    mean_index=('sync_index_100r','mean'),sd_index=('sync_index_100r','std'),
    mean_abs_lag_ms=('abs_lag_ms','mean'),sd_abs_lag_ms=('abs_lag_ms','std'),
    mean_signed_lag_ms=('lag_ms','mean'),mean_optimized_r=('optimized_r','mean'),
    median_frame_interval_ms=('frame_interval_ms','median'),boundary_trials=('lag_at_search_boundary','sum')).reset_index()
summary.to_csv(OUT/'sync_summary.csv',index=False,encoding='utf-8-sig')
(OUT/'method_and_sources.json').write_text(json.dumps({'subjects':manifest,
 'signal':'mean of Index/Middle/Ring/Pinky *_PIP_filt',
 'sync':'Pearson r at matching Frame_ID, index = 100*r, NOT a percentage of synchronized time',
 'lag':'maximize Pearson r on uniform capture_unix_s grid within +/-500 ms; positive = Right lags Left; longest gap-free block; gaps >250 ms not bridged',
 'aggregation':'equal weight per trial; sample standard deviation; no statistical significance test'},ensure_ascii=False,indent=2),encoding='utf-8')

font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11,
 'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#CBD5E1','text.color':'#182B42',
 'axes.labelcolor':'#475569','xtick.color':'#475569','ytick.color':'#475569','svg.fonttype':'none'})
colors={'Before':'#2166AC','After':'#D97917'}
fig,axes=plt.subplots(1,2,figsize=(13,7))
fig.subplots_adjust(left=.09,right=.96,bottom=.25,top=.77,wspace=.30)
fig.suptitle('양손 동작의 동조성 · 권미사님과 최병호님',x=.06,y=.985,ha='left',fontsize=21,fontweight='bold')
fig.text(.06,.91,'네 손가락 PIP 평균각의 양손 파형 비교  |  점: 시행별 값  ·  큰 점과 오차막대: 평균 ± SD',fontsize=11)
for col,(metric,title,ylabel) in enumerate([('sync_index_100r','동시에 움직이는 파형의 유사도','동조지수 (100 × 상관계수 r)'),('abs_lag_ms','파형 정렬에 필요한 시간차','절대 시간차 (ms)')]):
    ax=axes[col]
    for i,name in enumerate(configs):
        for session,shift in [('Before',-.15),('After',.15)]:
            vals=result[(result.subject==name)&(result.session==session)][metric].to_numpy()
            x=i+shift
            ax.scatter(x+np.linspace(-.045,.045,len(vals)),vals,color=colors[session],s=28,alpha=.65,zorder=3)
            ax.errorbar(x,vals.mean(),yerr=vals.std(ddof=1),fmt='D',color=colors[session],ms=8,capsize=5,lw=2,zorder=4)
            ax.annotate(f'{vals.mean():.1f}',(x,vals.mean()),xytext=(-23 if session=='Before' else 23,0),textcoords='offset points',ha='right' if session=='Before' else 'left',va='center',fontsize=10)
    ax.set_xticks([0,1],['권미사\n전 7회 · 후 8회','최병호\n전 5회 · 후 9회']);ax.set_xlim(-.55,1.55)
    ax.set_ylabel(ylabel);ax.set_title(title,loc='left',fontsize=14,fontweight='bold',pad=14)
    ax.grid(axis='y',color='#E2E8F0',lw=.7);ax.set_axisbelow(True)
    if col==0:ax.set_ylim(min(-5,float(result[metric].min())-8),105)
    else:ax.set_ylim(bottom=0)
fig.legend(handles=[Line2D([0],[0],color=colors[s],marker='o',label=l,lw=0) for s,l in [('Before','미러테라피 전'),('After','미러테라피 후')]],loc='upper left',bbox_to_anchor=(.052,.877),ncol=2,frameon=False)
fig.text(.06,.15,'동조지수는 100r로 정의한 분석용 지수입니다. 실제 동기화 시간의 백분율이나 임상 평가 점수가 아닙니다.',fontsize=10)
fig.text(.06,.115,'시간차는 ±500 ms 범위에서 파형 상관이 최대가 되는 지연의 절대값입니다. 촬영 간격 정도의 해상도이며 반응시간이 아닙니다.',fontsize=10)
fig.text(.06,.08,'시행 선택: 권미사 후 3 제외. 최병호 전 1·4·7·8 제외, 후 전체 포함. 서로 다른 시행 수로 직접적인 치료 효과 비교는 제한됩니다.',fontsize=10)
fig.text(.06,.045,'두 지표는 양손의 개폐 타이밍과 형태를 비교합니다. 신전 범위·힘·정확도를 나타내지 않으며 유의성 검정은 하지 않았습니다.',fontsize=10)
for ext in ['png','pdf','svg']:fig.savefig(OUT/f'bilateral_sync_comparison.{ext}',dpi=220,facecolor='white')

fig,axes=plt.subplots(2,2,figsize=(13,8))
fig.subplots_adjust(left=.09,right=.96,bottom=.14,top=.80,hspace=.47,wspace=.26)
fig.suptitle('양손 파형 예시 · 각 조건의 중간 수준 시행',x=.06,y=.97,ha='left',fontsize=21,fontweight='bold')
fig.text(.06,.918,'각 조건에서 상관계수 중앙값에 가장 가까운 시행  |  손별 평균·표준편차로 정규화해 타이밍 비교',fontsize=11)
selected=[]
for i,name in enumerate(configs):
 for j,session in enumerate(['Before','After']):
    sub=result[(result.subject==name)&(result.session==session)]
    row=sub.loc[(sub.correlation_r-sub.correlation_r.median()).abs().idxmin()]
    t,l,r=traces[(name,session,int(row.trial))]
    ax=axes[i,j];ax.plot(t,(l-l.mean())/l.std(),c='#2166AC',lw=1.8,label='왼손')
    ax.plot(t,(r-r.mean())/r.std(),c='#D97917',lw=1.8,label='오른손')
    ax.set_title(f'{name} · '+('전' if session=='Before' else '후')+f' Trial {int(row.trial)}  |  r = {row.correlation_r:.3f}',loc='left',fontsize=12,fontweight='bold')
    ax.set_xlabel('시행 시작 후 촬영 시간 (s)');ax.set_ylabel('정규화 개폐각');ax.grid(color='#E2E8F0',lw=.7)
    selected.append({'subject':name,'session':session,'trial':int(row.trial)})
fig.legend(handles=[Line2D([0],[0],c='#2166AC',label='왼손'),Line2D([0],[0],c='#D97917',label='오른손')],loc='upper left',bbox_to_anchor=(.052,.885),ncol=2,frameon=False)
fig.text(.06,.045,'곡선이 함께 올라가고 내려가면 동조성이 높습니다. 정규화하므로 실제 양손 가동범위의 차이는 이 그림에서 비교할 수 없습니다.',fontsize=10)
for ext in ['png','pdf','svg']:fig.savefig(OUT/f'bilateral_waveform_examples.{ext}',dpi=220,facecolor='white')
print(summary.round(4).to_string(index=False))
print(result[['subject','session','trial','correlation_r','lag_ms','frame_interval_ms','gap_count','lag_at_search_boundary']].round(3).to_string(index=False))

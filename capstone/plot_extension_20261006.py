"""Recompute trial maxima; exclude the erroneous After Trial_3; plot results."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'outputs' / 'extension_comparison_20261006' / 'plot_dependencies'))
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs' / 'extension_comparison_20261006'
sources = json.loads((OUT / 'analysis.json').read_text(encoding='utf-8'))['sources']
JOINTS = ['Thumb_CMC','Thumb_MCP','Thumb_IP'] + [f'{f}_{j}' for f in ['Index','Middle','Ring','Pinky'] for j in ['MCP','PIP','DIP']]
names = {'Thumb':'엄지','Index':'검지','Middle':'중지','Ring':'약지','Pinky':'소지'}
labels = [names[j.split('_')[0]]+' '+j.split('_')[1]+('*' if j=='Thumb_CMC' else '') for j in JOINTS]
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,
    'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
    'axes.edgecolor':'#CBD5E1','text.color':'#182B42','axes.labelcolor':'#334155',
    'xtick.color':'#475569','ytick.color':'#334155','svg.fonttype':'none'})
BLUE, ORANGE = '#2166AC', '#D97917'
trialsets = {}
for session, path in sources.items():
    raw = pd.read_csv(path)
    rows = raw[raw.Trial.str.startswith('Trial_') & raw.Protocol_Valid.eq(1)].copy()
    if session=='After': rows=rows[rows.Trial.ne('Trial_3')]
    cols=[j+'_filt' for j in JOINTS]
    assert rows[cols].notna().all().all()
    trials=rows.groupby(['hand','Trial'])[cols].max()
    trials.columns=JOINTS
    assert all(len(trials.loc[h]) == (7 if session=='Before' else 8) for h in ['Left','Right'])
    assert session!='After' or 'Trial_3' not in trials.index.get_level_values('Trial')
    trialsets[session]=trials

records=[]
overall=[]
for hand in ['Left','Right']:
    b=trialsets['Before'].loc[hand]; a=trialsets['After'].loc[hand]
    for joint in JOINTS:
        records.append(dict(hand=hand,joint=joint,before_n=7,after_n=8,
            before_mean_deg=b[joint].mean(),before_sd_deg=b[joint].std(ddof=1),
            after_mean_deg=a[joint].mean(),after_sd_deg=a[joint].std(ddof=1),
            change_deg=a[joint].mean()-b[joint].mean(),
            before_peak_deg=b[joint].max(),after_peak_deg=a[joint].max()))
    overall.append(dict(hand=hand,before_mean=b.mean(axis=1).mean(),before_sd=b.mean(axis=1).std(),
        after_mean=a.mean(axis=1).mean(),after_sd=a.mean(axis=1).std(),change=a.values.mean()-b.values.mean()))
df=pd.DataFrame(records)
df.to_csv(OUT/'joint_extension_after_trial3_excluded.csv',index=False,encoding='utf-8-sig')
pd.concat([v.reset_index().assign(session=k) for k,v in trialsets.items()]).to_csv(
    OUT/'trial_maxima_after_trial3_excluded.csv',index=False,encoding='utf-8-sig')
(OUT/'analysis_after_trial3_excluded.json').write_text(json.dumps(
    {'sources':sources,'excluded':'After Trial_3: recording error, user confirmed',
     'angle_columns':'*_filt','n_before':7,'n_after':8,'results':records,'overall':overall},
    indent=2,ensure_ascii=False),encoding='utf-8')

def decorate(ax):
    ax.set_ylim(14.8,-0.8)
    ax.set_yticks(range(15),labels)
    ax.grid(axis='x',color='#E2E8F0',linewidth=.7)
    ax.set_axisbelow(True)
    for y in [2.5,5.5,8.5,11.5]: ax.axhline(y,color='#DCE4ED',lw=.8)

fig,axs=plt.subplots(2,2,figsize=(16,14),gridspec_kw={'width_ratios':[1.7,1]},layout=None)
fig.subplots_adjust(left=.09,right=.95,bottom=.12,top=.84,wspace=.29,hspace=.28)
fig.suptitle('미러테라피 전후 최대 신전각도',x=.07,y=.976,ha='left',fontsize=24,fontweight='bold')
fig.text(.07,.942,'각 시행의 관절별 최대각 평균 ± 표준편차  |  전 7회 · 후 8회  |  후 Trial 3 제외',fontsize=13)
fig.legend(handles=[Line2D([0],[0],color=BLUE,marker='o',label='미러테라피 전',lw=0),
    Line2D([0],[0],color=ORANGE,marker='o',label='미러테라피 후',lw=0)],
    loc='upper left',bbox_to_anchor=(.065,.925),ncol=2,frameon=False,fontsize=12)
for row,hand in enumerate(['Left','Right']):
    dat=df[df.hand.eq(hand)]; o=overall[row]; ax,delta=axs[row]
    title='환측 · 왼손' if hand=='Left' else '비마비측 · 오른손'
    ax.set_title(title+'   |   15개 관절 평균 '+f"{o['before_mean']:.2f}° → {o['after_mean']:.2f}° ({o['change']:+.2f}°)",
        loc='left',fontsize=13,pad=15,fontweight='bold')
    y=np.arange(15)
    for x0,x1,yi in zip(dat.before_mean_deg,dat.after_mean_deg,y): ax.plot([x0,x1],[yi,yi],color='#B8C6D5',lw=1.4)
    ax.errorbar(dat.before_mean_deg,y-.12,xerr=dat.before_sd_deg,fmt='o',color=BLUE,ms=5.5,capsize=3,lw=1.2)
    ax.errorbar(dat.after_mean_deg,y+.12,xerr=dat.after_sd_deg,fmt='o',color=ORANGE,ms=5.5,capsize=3,lw=1.2)
    ax.axvline(180,color='#64748B',ls='--',lw=1)
    ax.set_xlim(137,182); ax.set_xticks([140,150,160,170,180]); ax.set_xlabel('최대 신전각도 (°)  ·  180°에 가까울수록 더 펴짐')
    decorate(ax)
    vals=dat.change_deg.to_numpy()
    delta.barh(y,vals,color=[BLUE if v<0 else ORANGE for v in vals],height=.56)
    delta.axvline(0,color='#64748B',lw=1)
    delta.set_xlim(-10.5,6.4); delta.set_xticks([-10,-5,0,5]); delta.set_xlabel('평균 변화량 (°)  ·  후 - 전')
    delta.set_title('관절별 변화량',loc='left',fontsize=13,pad=15,fontweight='bold')
    decorate(delta); delta.set_yticklabels([]); delta.tick_params(axis='y',length=0)
    for yi,v in zip(y,vals): delta.text(v+(.18 if v>=0 else -.18),yi,f'{v:+.2f}',va='center',ha='left' if v>=0 else 'right',fontsize=10)
fig.text(.07,.07,'계산: 시행별 각 관절의 최대값 → 시행 간 평균·표본 SD. 휴식 제외, Protocol_Valid = 1, 저장된 *_filt 각도 사용.',fontsize=10,color='#475569')
fig.text(.07,.047,'* 엄지 CMC는 손목–CMC–MCP 사이각으로 굴곡·외전이 섞인 지표. 15개 관절 평균은 동시 신전각이 아닌 관절별 최대값의 평균.',fontsize=10,color='#475569')
fig.text(.07,.024,'처리 방식 참고: 별도 *_3D 열은 다른 처리 경로이며 이 그래프에 혼합하지 않았습니다. 변화량에 대한 유의성 검정은 수행하지 않았습니다.',fontsize=10,color='#475569')
for ext in ['png','svg','pdf']: fig.savefig(OUT/f'maximum_extension_comparison.{ext}',dpi=220,facecolor='white')
plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(13,8))
fig.subplots_adjust(left=.10,right=.96,bottom=.18,top=.78,wspace=.30)
fig.suptitle('관절별 최고 피크 신전각도',x=.06,y=.97,ha='left',fontsize=22,fontweight='bold')
fig.text(.06,.902,'전 7회 · 후 8회 중 각 관절이 도달한 최고값  |  후 Trial 3 제외  |  *_filt 각도',fontsize=12)
fig.legend(handles=[Line2D([0],[0],color=BLUE,marker='o',label='미러테라피 전',lw=0),
    Line2D([0],[0],color=ORANGE,marker='o',label='미러테라피 후',lw=0)],loc='upper left',bbox_to_anchor=(.055,.878),ncol=2,frameon=False)
for ax,hand in zip(axs,['Left','Right']):
    dat=df[df.hand.eq(hand)]; y=np.arange(15)
    for b,a,yi in zip(dat.before_peak_deg,dat.after_peak_deg,y): ax.plot([b,a],[yi,yi],color='#B8C6D5',lw=1.5)
    ax.scatter(dat.before_peak_deg,y-.10,c=BLUE,s=35,zorder=3)
    ax.scatter(dat.after_peak_deg,y+.10,c=ORANGE,s=35,zorder=3)
    decorate(ax); ax.set_xlim(140,182); ax.set_xticks([140,150,160,170,180]); ax.axvline(180,color='#64748B',ls='--',lw=1)
    ax.set_title('환측 · 왼손' if hand=='Left' else '비마비측 · 오른손',loc='left',fontweight='bold',pad=12)
    ax.set_xlabel('최고 피크각 (°)')
fig.text(.06,.07,'최고 피크는 한 번이라도 기록된 최대값이며, 시행별 최대각의 평균과 다릅니다. 각 관절의 최고값은 서로 다른 시점에 나타날 수 있습니다.',fontsize=10)
fig.text(.06,.035,'* 엄지 CMC는 굴곡·외전이 섞인 측정 지표입니다.',fontsize=10)
for ext in ['png','svg','pdf']: fig.savefig(OUT/f'peak_extension_comparison.{ext}',dpi=220,facecolor='white')
plt.close(fig)
print(pd.DataFrame(overall).round(4).to_string(index=False))
print('Saved figures and numerical data to',OUT)

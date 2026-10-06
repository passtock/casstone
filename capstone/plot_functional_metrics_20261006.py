from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'/'extension_comparison_20261006'
sys.path.insert(0,str(OUT/'plot_dependencies'))
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
sources=json.loads((OUT/'analysis.json').read_text(encoding='utf-8'))['sources']
metrics=[('MGA_cm','최대 파지폭 (모델 추정)','cm'),
 ('Thumb_PalmarAbd_max_deg','엄지 최대 장측 외전각','°'),
 ('Ext_Speed_deg_s','최고 신전 각속도','°/s'),
 ('Flex_Speed_deg_s','최고 굴곡 각속도','°/s'),
 ('Index_ROM_deg','검지 PIP 가동범위','°'),
 ('TAM_Thumb_deg','엄지 TAM (MCP ROM + IP ROM)','°')]
extra=[('Ext_Speed_p95_deg_s','신전 각속도 P95','°/s'),('Flex_Speed_p95_deg_s','굴곡 각속도 P95','°/s')]
data={}
for session,path in sources.items():
    summary_path=Path(path.replace('continuous_raw','trials_summary'))
    df=pd.read_csv(summary_path)
    if session=='After':df=df[df.Trial.ne('Trial #3')]
    assert all(len(df[df.Hand.eq(h)])==(7 if session=='Before' else 8) for h in ['Left','Right'])
    data[session]=df
    # Verify nonvelocity summary values against the recorded filtered frames.
    frames=pd.read_csv(path)
    frames=frames[frames.Trial.str.startswith('Trial_') & frames.Protocol_Valid.eq(1)]
    if session=='After':frames=frames[frames.Trial.ne('Trial_3')]
    for _,r in df.iterrows():
        trial='Trial_'+r.Trial.split('#')[1]
        g=frames[frames.hand.eq(r.Hand)&frames.Trial.eq(trial)]
        checks={'MGA_cm':g.Grip_Aperture_cm_filt.max(),
                'Thumb_PalmarAbd_max_deg':g.Thumb_PalmarAbd_filt.max(),
                'Index_ROM_deg':g.Index_PIP_filt.max()-g.Index_PIP_filt.min(),
                'TAM_Thumb_deg':sum(g[j].max()-g[j].min() for j in ['Thumb_MCP_filt','Thumb_IP_filt'])}
        for key,val in checks.items(): assert abs(r[key]-val)<.025,(session,r.Hand,trial,key,r[key],val)
records=[]
for hand in ['Left','Right']:
 for col,label,unit in metrics+extra:
    b=data['Before'].loc[data['Before'].Hand.eq(hand),col]
    a=data['After'].loc[data['After'].Hand.eq(hand),col]
    assert b.notna().all() and a.notna().all()
    records.append(dict(hand=hand,metric=col,label=label,unit=unit,before_n=len(b),after_n=len(a),
        before_mean=b.mean(),before_sd=b.std(),after_mean=a.mean(),after_sd=a.std(),
        change=a.mean()-b.mean(),percent_change=(a.mean()/b.mean()-1)*100))
results=pd.DataFrame(records)
results.to_csv(OUT/'functional_metrics_after_trial3_excluded.csv',index=False,encoding='utf-8-sig')
pd.concat([df.assign(session=s) for s,df in data.items()]).to_csv(OUT/'functional_metric_trials_after_trial3_excluded.csv',index=False,encoding='utf-8-sig')
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11,
 'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#CBD5E1',
 'text.color':'#182B42','axes.labelcolor':'#475569','xtick.color':'#475569','ytick.color':'#334155','svg.fonttype':'none'})
BLUE,ORANGE='#2166AC','#D97917'
fig,axes=plt.subplots(3,2,figsize=(14,11))
fig.subplots_adjust(left=.12,right=.96,top=.80,bottom=.17,hspace=.76,wspace=.34)
fig.suptitle('미러테라피 전후 손 벌림·운동학 지표',x=.06,y=.97,ha='left',fontsize=23,fontweight='bold')
fig.text(.06,.923,'시행별 지표의 평균 ± 표준편차  |  전 7회 · 후 8회  |  잘못 녹화된 후 Trial 3 제외',fontsize=12)
fig.legend(handles=[Line2D([0],[0],color=BLUE,marker='o',lw=0,label='미러테라피 전'),
 Line2D([0],[0],color=ORANGE,marker='o',lw=0,label='미러테라피 후')],loc='upper left',bbox_to_anchor=(.052,.901),frameon=False,ncol=2)
for ax,(col,label,unit) in zip(axes.flat,metrics):
    sub=results[results.metric.eq(col)]
    ax.set_title(label,loc='left',fontsize=13,fontweight='bold',pad=28)
    for y,hand in enumerate(['Left','Right']):
        r=sub[sub.hand.eq(hand)].iloc[0]
        ax.plot([r.before_mean,r.after_mean],[y,y],color='#B8C6D5',lw=1.5)
        ax.errorbar(r.before_mean,y-.10,xerr=r.before_sd,fmt='o',color=BLUE,capsize=4,ms=6,lw=1.3)
        ax.errorbar(r.after_mean,y+.10,xerr=r.after_sd,fmt='o',color=ORANGE,capsize=4,ms=6,lw=1.3)
    ax.text(0,1.10,'  /  '.join(('환측' if r.hand=='Left' else '비마비측')+f' {r.percent_change:+.1f}%' for r in sub.itertuples()),
        transform=ax.transAxes,fontsize=11,color='#475569')
    ax.set_yticks([0,1],['환측(좌)','비마비측(우)']); ax.set_ylim(1.5,-.5)
    ax.set_xlim(left=0,right=float(max((sub.before_mean+sub.before_sd).max(),(sub.after_mean+sub.after_sd).max()))*1.12)
    ax.set_xlabel(unit); ax.grid(axis='x',color='#E2E8F0',lw=.7); ax.set_axisbelow(True); ax.tick_params(axis='y',length=0)
fig.text(.06,.095,'속도: 네 손가락 PIP 평균각에서 산출한 시행별 최고 각속도. 반응시간이나 움직임의 정확도를 나타내지는 않습니다.',fontsize=10,color='#475569')
fig.text(.06,.067,'파지폭: 엄지 끝–검지 끝 거리의 모델 추정값. 손 길이 보정값이 없어 실제 절대 cm로 확정할 수 없습니다.',fontsize=10,color='#475569')
fig.text(.06,.039,'전후 변화는 관찰 결과이며, 단일 피험자의 1회 세션만으로 치료의 인과적 효과를 확인한 것은 아닙니다.',fontsize=10,color='#475569')
for ext in ['png','pdf','svg']:fig.savefig(OUT/f'functional_metrics_comparison.{ext}',dpi=220,facecolor='white')
print(results.round(4).to_string(index=False))

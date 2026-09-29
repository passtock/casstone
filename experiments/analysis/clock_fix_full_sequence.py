# -*- coding: utf-8 -*-
"""시계 복구 5단계 완주 (20260915, PIP 정의 유지).

① Frame_ID 대응 무결성
② 시계별 시간 간격 점검 (비단조·중복·긴 공백)
③ 속도 재계산 — 시계 5종 × PIP, peak·P95 병기
④ SPARC 재계산 — 시계별
⑤ C1·C2·C3 재평가 — '시계 선택 민감도'로
출력: experiments/results/clock_fix_full_sequence.txt
"""
import csv, glob, io, os, sys, math, numpy as np
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
D='capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남'
L=[]
def out(s=""): L.append(s)

# ── 로드
dc=os.path.join(D,[f for f in os.listdir(D) if f.endswith('_distance_comparison.csv')][0])
DCR=list(csv.DictReader(open(dc,encoding='utf-8-sig')))
byfid={}
dup_fid=0
for r in DCR:
    k=r['Frame_ID']
    if k in byfid: dup_fid+=1
    byfid[k]=r
raw=[r for r in csv.DictReader(open([f for f in glob.glob(D+'/*continuous_raw.csv') if 'split' not in f.split(os.sep)][0],encoding='utf-8-sig'))]
TRI=[r for r in raw if r['Trial']!='Rest']
PIP=['Index_PIP_filt','Middle_PIP_filt','Ring_PIP_filt','Pinky_PIP_filt']
CLOCKS=[('time_s',1.0,'원래(PC time.time-t_session)'),
        ('capture_monotonic_s',1.0,'PC perf_counter'),
        ('capture_unix_s',1.0,'PC time.time'),
        ('Color_Timestamp_ms',0.001,'RealSense get_timestamp'),
        ('Depth_Timestamp_ms',0.001,'RealSense depth get_timestamp')]

out("="*100); out("시계 복구 5단계 완주 — 20260915 (26세 남) · Task1 · 8시행 × 양손 · PIP 정의 유지"); out("="*100)

# ── ① Frame_ID 대응
out(); out("### ① Frame_ID 대응 무결성 ###")
fids=[r['Frame_ID'] for r in TRI]
miss=[f for f in fids if f not in byfid]
uniq=len(set(fids))
out(f"  continuous_raw 행 {len(fids)} · 고유 Frame_ID {uniq} · distance_comparison 행 {len(DCR)} (Frame_ID 중복 {dup_fid})")
out(f"  distance_comparison 에 없는 Frame_ID: {len(miss)}")
# Frame_ID 정렬성
try:
    fi=[int(f) for f in fids]
    noninc=sum(1 for a,b in zip(fi,fi[1:]) if b<=a)
    out(f"  Frame_ID 비증가 쌍(행 순서): {noninc}")
except Exception as e:
    out(f"  Frame_ID 정수 변환 실패: {e}")

# ── ② 시간 간격 점검
out(); out("### ② 시계별 시간 간격 점검 (8시행×양손) ###")
out(f"{'시계':<24}{'n':>6}{'dt<=0':>8}{'dt<0.01':>9}{'dt>0.5s':>9}{'중앙dt(s)':>10}")
G=defaultdict(list)
for r in TRI: G[(r['Trial'],r['hand'])].append(r)
clock_series={}
for cname,sc,desc in CLOCKS:
    segs={}
    for k,rl in G.items():
        if cname=='time_s': t=np.array([float(r['time_s']) for r in rl])
        else: t=np.array([float(byfid[r['Frame_ID']][cname])*sc for r in rl if r['Frame_ID'] in byfid])
        segs[k]=t
    allt=np.concatenate([np.diff(v) for v in segs.values() if len(v)>1])
    clock_series[cname]=segs
    out(f"{desc:<24}{len(allt):>6}{int((allt<=0).sum()):>8}{int((allt<0.01).sum()):>9}{int((allt>0.5).sum()):>9}{np.median(allt):>10.4f}")

# ── 유틸
def mono(t):
    t=np.asarray(t,float)
    return t if len(t)<2 else np.maximum.accumulate(t+np.arange(len(t))*1e-9)
def sparc(vel,times,fc=10.0):
    if vel is None or len(vel)<20 or np.all(np.abs(vel)<1e-4): return None
    dt=float(np.mean(np.diff(mono(times))))
    if not np.isfinite(dt) or dt<=0: return None
    mag=np.abs(np.fft.rfft(vel)); fr=np.fft.rfftfreq(len(vel),d=dt)
    m=fr<=fc; f_s,m_s=fr[m],mag[m]
    if len(f_s)<3 or float(np.max(m_s))<1e-7: return None
    m_s=m_s/np.max(m_s)
    return float(-np.sum(np.sqrt((np.diff(f_s)/fc)**2+np.diff(m_s)**2)))

# ── ③④ 재계산
out(); out("### ③④ 시계별 재계산 (PIP 각속도 · SPARC) ###")
res={}
for cname,sc,desc in CLOCKS:
    per=defaultdict(dict)
    for k in sorted(G.keys()):
        rl=G[k]
        if cname=='time_s':
            t=np.array([float(r['time_s']) for r in rl])
            flex=np.array([np.mean([float(r[j]) for j in PIP]) for r in rl])
        else:
            ok=[r for r in rl if r['Frame_ID'] in byfid]
            t=np.array([float(byfid[r['Frame_ID']][cname])*sc for r in ok])
            flex=np.array([np.mean([float(r[j]) for j in PIP]) for r in ok])
        o=np.argsort(t); t,f=mono(t[o]),flex[o]
        vel=np.gradient(f,t)
        per[k]=dict(peak=float(np.max(-vel)), p95=float(np.percentile(-vel,95)),
                    epeak=float(np.max(vel)), ep95=float(np.percentile(vel,95)),
                    sparc=sparc(vel,t))
    res[cname]=per
out(f"{'시계':<22}{'peak 중앙':>10}{'peak범위':>18}{'P95 중앙':>10}{'P95범위':>18}{'SPARC 중앙':>12}{'SPARC범위':>20}")
for cname,sc,desc in CLOCKS:
    pk=[v['peak'] for v in res[cname].values()]; q=[v['p95'] for v in res[cname].values()]
    sp=[v['sparc'] for v in res[cname].values() if v['sparc'] is not None]
    sp_s=f"{np.median(sp):.2f} [{min(sp):.2f},{max(sp):.2f}]" if sp else "-"
    out(f"{desc[:20]:<22}{np.median(pk):>10.1f}{('[%.0f,%.0f]'%(min(pk),max(pk))):>18}"
        f"{np.median(q):>10.1f}{('[%.0f,%.0f]'%(min(q),max(q))):>18}{sp_s:>32}")

# ── ⑤ C1·C2·C3 민감도
out(); out("### ⑤ C1·C2·C3 — 시계 선택 민감도 ###")
def mdc_pct(vals,hand_keys):
    rs=[]
    for h in hand_keys:
        v=[x for k,x in vals.items() if k[1]==h and x is not None]
        if len(v)<3: continue
        m=np.mean(v); 
        if abs(m)<1e-9: continue
        rs.append(1.96*math.sqrt(2)*np.std(v,ddof=1)/abs(m)*100)
    return float(np.median(rs)) if rs else None
hands=['Right','Left']
rows=[]
for metric,getter in [('Flex_P95',lambda d:d['p95']),('Flex_Peak',lambda d:d['peak']),
                      ('Ext_P95',lambda d:d['ep95']),('SPARC',lambda d:d['sparc'])]:
    line={'metric':metric}
    for cname,sc,desc in CLOCKS:
        vals={k:getter(v) for k,v in res[cname].items()}
        line[desc]=mdc_pct(vals,hands)
    rows.append(line)
out(f"{'지표':<12}" + "".join(f"{d[:14]:>16}" for _,_,d in CLOCKS))
for line in rows:
    out(f"{line['metric']:<12}" + "".join(
        (f"{line[d]:.1f}" if line[d] is not None else "-").rjust(16) for _,_,d in CLOCKS))
out()
out("판정(≤50·수동아님): 위 값이 시계 선택에 따라 50을 넘나들면 판정이 뒤집힌다.")
io.open('experiments/results/clock_fix_full_sequence.txt','w',encoding='utf-8').write("\n".join(L)+"\n")
print("\n".join(L)); print("\n[saved] experiments/results/clock_fix_full_sequence.txt")

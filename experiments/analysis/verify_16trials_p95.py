# -*- coding: utf-8 -*-
"""전체 16개 시행(8시행×양손, Rest 제외)에서 시계 교체가 peak/P95에 미치는 영향."""
import csv, glob, io, os, sys, numpy as np
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
D='capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남'
dc=os.path.join(D,[f for f in os.listdir(D) if f.endswith('_distance_comparison.csv')][0])
by={}
for r in csv.DictReader(open(dc,encoding='utf-8-sig')):
    by[r['Frame_ID']]=r
p=[f for f in glob.glob(D+'/*continuous_raw.csv') if 'split' not in f.split(os.sep)][0]
rows=[r for r in csv.DictReader(open(p,encoding='utf-8-sig')) if r['Trial']!='Rest']
PIP=['Index_PIP_filt','Middle_PIP_filt','Ring_PIP_filt','Pinky_PIP_filt']
G=defaultdict(list)
for r in rows: G[(r['Trial'],r['hand'])].append(r)
print("시행×손 그룹:",len(G)," 총 행:",len(rows))
print()
print(f"{'Trial':<9}{'Hand':<7}{'peak_mono':>10}{'peak_dev':>10}{'dPeak%':>8}{'P95_mono':>10}{'P95_dev':>9}{'dP95%':>8}")
dP=[];dQ=[]
for k in sorted(G.keys()):
    rl=G[k]
    ok=[r for r in rl if r['Frame_ID'] in by and by[r['Frame_ID']].get('Color_Timestamp_ms') not in (None,'')]
    if len(ok)<10: print(f"{k[0]:<9}{k[1]:<7}  (조인 부족 {len(ok)})"); continue
    flex=np.array([np.mean([float(r[j]) for j in PIP]) for r in ok])
    tm=np.array([float(by[r['Frame_ID']]['capture_monotonic_s']) for r in ok])
    td=np.array([float(by[r['Frame_ID']]['Color_Timestamp_ms'])/1000.0 for r in ok])
    om=np.argsort(tm); od=np.argsort(td)
    vm=np.gradient(flex[om],tm[om]); vd=np.gradient(flex[od],td[od])
    pm,p95m=np.max(-vm),np.percentile(-vm,95)
    pd_,p95d=np.max(-vd),np.percentile(-vd,95)
    dp=abs(pd_-pm)/pm*100; dq=abs(p95d-p95m)/p95m*100
    dP.append(dp); dQ.append(dq)
    print(f"{k[0]:<9}{k[1]:<7}{pm:>10.1f}{pd_:>10.1f}{dp:>8.1f}{p95m:>10.1f}{p95d:>9.1f}{dq:>8.1f}")
print()
print("### 변화율 요약 (피드백 제시값: peak 중앙 19.6 / 최대 57.0 · P95 중앙 30.7 / 최대 92.5) ###")
print(f"  peak  중앙 {np.median(dP):.1f}%  최대 {np.max(dP):.1f}%")
print(f"  P95   중앙 {np.median(dQ):.1f}%  최대 {np.max(dQ):.1f}%")
print()
print("### 시간 간격 비단조 개수 (Rest 제외, 8시행×양손) ###")
tot=0; bad=0; badu=0
for k,rl in G.items():
    t=np.array([float(r['time_s']) for r in rl]); d=np.diff(t)
    tot+=len(d); bad+=int((d<=0).sum())
    tu=np.array([float(r['capture_unix_s']) for r in rl]); du=np.diff(tu)
    badu+=int((du<=0).sum())
print(f"  time_s        : 비증가 {bad}/{tot}   (피드백 제시 242/1915)")
print(f"  capture_unix_s: 비증가 {badu}/{tot}")

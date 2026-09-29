# -*- coding: utf-8 -*-
import csv, glob, io, os, sys, numpy as np
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
p=[f for f in glob.glob('capstone/호진파일/outputs/데이터_저장/20260915*/*continuous_raw.csv') if 'split' not in f.split(os.sep)][0]
rows=[r for r in csv.DictReader(open(p,encoding='utf-8-sig')) if r['Trial']=='Trial_1' and r['hand']=='Right']
PIP=['Index_PIP_filt','Middle_PIP_filt','Ring_PIP_filt','Pinky_PIP_filt']
MCP=['Index_MCP_filt','Middle_MCP_filt','Ring_MCP_filt','Pinky_MCP_filt']
def mono(t):
    t=np.asarray(t,float)
    return t if len(t)<2 else np.maximum.accumulate(t+np.arange(len(t))*1e-9)
print("### 대조표 (Trial_1 Right) ###")
print("%-42s%12s" % ("계산 방식","peak(-vel) °/s"))
for name,joints,clock in [
  ("원래 정의 PIP + time_s(=_mono)",PIP,'time_s'),
  ("[오진] MCP  + capture_unix_s",MCP,'capture_unix_s'),
  ("[피드백] PIP + capture_unix_s",PIP,'capture_unix_s'),
  ("[피드백] PIP + capture_monotonic_s",PIP,'capture_monotonic_s'),
]:
    f=[r for r in csv.DictReader(open(p,encoding='utf-8-sig')) if r['Trial']=='Trial_1' and r['hand']=='Right']
    t=np.array([float(r[clock]) for r in f])
    if clock=='time_s': t=mono(t)
    flex=np.array([np.mean([float(r[j]) for j in joints]) for r in f])
    vel=np.gradient(flex,t)
    print("%-42s%12.1f" % (name,np.max(-vel)))
print()
print("### 프레임 중복 여부: dt==0 인 쌍의 Frame_ID ###")
f=[r for r in csv.DictReader(open(p,encoding='utf-8-sig')) if r['Trial']=='Trial_1' and r['hand']=='Right']
have_fid = 'Frame_ID' in f[0]
print("  Frame_ID 컬럼 존재:",have_fid)
if have_fid:
    t=np.array([float(r['time_s']) for r in f]); fid=[r['Frame_ID'] for r in f]
    d=np.diff(t)
    dup=[i for i in range(len(d)) if d[i]<=0]
    print("  dt<=0 쌍:",len(dup))
    for i in dup[:6]:
        print(f"    idx{i}: Frame {fid[i]}->{fid[i+1]}  t={t[i]:.6f}->{t[i+1]:.6f}  mono={f[i]['capture_monotonic_s']}")
    print("  Frame_ID가 연속인가:",all(int(fid[i+1])-int(fid[i])==1 for i in range(len(fid)-1)))
print()
print("### capture_monotonic_s 단조성 / 역행 / 긴 공백 ###")
for clock in ['capture_unix_s','capture_monotonic_s']:
    t=np.array([float(r[clock]) for r in f]); d=np.diff(t)
    print(f"  {clock:<22} dt<=0:{int((d<=0).sum())}  dt<0.01:{int((d<0.01).sum())}  dt>0.2:{int((d>0.2).sum())}  중앙:{np.median(d):.4f}")
print()
print("### 두 시계의 차이(drift) — 세션 중 시계 점프 여부 ###")
t1=np.array([float(r['capture_unix_s']) for r in f]); t2=np.array([float(r['capture_monotonic_s']) for r in f])
d1=np.diff(t1); d2=np.diff(t2)
print("  |dt_unix - dt_mono| 최대:",round(float(np.max(np.abs(d1-d2))),6),"초")
print("  dt_unix 합:",round(float(t1[-1]-t1[0]),3),"s   dt_mono 합:",round(float(t2[-1]-t2[0]),3),"s")

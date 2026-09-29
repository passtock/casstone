# -*- coding: utf-8 -*-
import csv, glob, io, os, sys, numpy as np
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
D='capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남'
dc=os.path.join(D,[f for f in os.listdir(D) if f.endswith('_distance_comparison.csv')][0])
dcr=list(csv.DictReader(open(dc,encoding='utf-8-sig')))
print("### distance_comparison: 손별(both interleaved) vs 같은 손만 ###")
for hand in ['Right','Left']:
    rr=[r for r in dcr if r.get('Hand')==hand]
    for col,sc in [('capture_monotonic_s',1.0),('capture_unix_s',1.0),('Color_Timestamp_ms',0.001)]:
        v=[float(r[col]) for r in rr if r.get(col) not in (None,'')]
        if len(v)<3: continue
        d=np.diff(np.array(v))
        print(f"  {hand:<6}{col:<22} n={len(v)}  dt<=0:{int((d<=0).sum())}  dt<0.01:{int((d<0.01).sum())}  중앙:{np.median(d):.5f}s")
    print()
print("### continuous_raw.csv(손 분리 저장)의 같은 손 중복 ###")
p=[f for f in glob.glob(D+'/*continuous_raw.csv') if 'split' not in f.split(os.sep)][0]
rows=[r for r in csv.DictReader(open(p,encoding='utf-8-sig')) if r['hand']=='Right']
for col in ['time_s','capture_unix_s']:
    v=np.array([float(r[col]) for r in rows]); d=np.diff(v)
    print(f"  {col:<22} n={len(v)}  dt<=0:{int((d<=0).sum())}  dt<0.01:{int((d<0.01).sum())}  중앙:{np.median(d):.5f}s")
print()
print("### 핵심 판정: 중복이 'PC 시계'에만 있는가, '장치 시계'에도 있는가 ###")
rr=[r for r in dcr if r.get('Hand')=='Right']
for col,sc in [('capture_monotonic_s',1.0),('Color_Timestamp_ms',0.001),('Depth_Timestamp_ms',0.001)]:
    v=[float(r[col])*sc for r in rr if r.get(col) not in (None,'')]
    d=np.diff(np.array(v))
    tag = "중복 있음 ← PC 시계 결함" if (d<=0).sum()>0 else "중복 없음 ← 정상"
    print(f"  {col:<22} dt<=0={int((d<=0).sum()):4d}   {tag}")

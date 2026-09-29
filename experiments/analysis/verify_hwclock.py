# -*- coding: utf-8 -*-
import csv, glob, io, os, sys, numpy as np
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
D='capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남'
dc=os.path.join(D,[f for f in os.listdir(D) if f.endswith('_distance_comparison.csv')][0])
dcr=list(csv.DictReader(open(dc,encoding='utf-8-sig')))
print("distance_comparison.csv 행:",len(dcr))
print("컬럼:",list(dcr[0].keys()))
by={}
for r in dcr: by[r['Frame_ID']]=r
for col in ['capture_monotonic_s','capture_unix_s','Color_Timestamp_ms','Depth_Timestamp_ms']:
    v=[float(r[col]) for r in dcr if r.get(col) not in (None,'')]
    if len(v)<3: print(f"  {col}: 값 없음"); continue
    t=np.array(v); d=np.diff(t)
    print(f"  {col:<22} n={len(t)}  dt<=0:{int((d<=0).sum())}  dt<0.01:{int((d<0.01).sum())}  중앙:{np.median(d):.6f}  단위추정={'ms' if np.median(d)>5 else 's'}")
print()
p=[f for f in glob.glob(D+'/*continuous_raw.csv') if 'split' not in f.split(os.sep)][0]
rows=[r for r in csv.DictReader(open(p,encoding='utf-8-sig')) if r['Trial']=='Trial_1' and r['hand']=='Right']
PIP=['Index_PIP_filt','Middle_PIP_filt','Ring_PIP_filt','Pinky_PIP_filt']
MCP=['Index_MCP_filt','Middle_MCP_filt','Ring_MCP_filt','Pinky_MCP_filt']
print("### 대조 (Trial_1 Right) — Frame_ID 조인 ###")
print("%-46s%11s%11s" % ("방식","peak(°)","P95(°)"))
for label,joints,key,scale in [
    ("PIP + capture_monotonic_s (PC perf_counter)",PIP,'capture_monotonic_s',1.0),
    ("PIP + Color_Timestamp_ms (장치 하드웨어)",PIP,'Color_Timestamp_ms',0.001),
    ("PIP + Depth_Timestamp_ms (장치 하드웨어)",PIP,'Depth_Timestamp_ms',0.001),
    ("MCP + Color_Timestamp_ms (장치 하드웨어)",MCP,'Color_Timestamp_ms',0.001),
]:
    ok=[(i,r) for i,r in enumerate(rows) if r['Frame_ID'] in by and by[r['Frame_ID']].get(key) not in (None,'')]
    t=np.array([float(by[r['Frame_ID']][key])*scale for _,r in ok])
    f=np.array([np.mean([float(r[j]) for j in joints]) for _,r in ok])
    o=np.argsort(t); t,f=t[o],f[o]
    vel=np.gradient(f,t)
    print("%-46s%11.1f%11.1f" % (label,np.max(-vel),np.percentile(-vel,95)))

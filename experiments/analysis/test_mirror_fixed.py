# -*- coding: utf-8 -*-
"""Mirror_therapy_fixed.py 의 수정 함수를 실데이터로 검증 (원본과 대조)."""
import ast, csv, glob, io, os, sys, numpy as np
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
SRC='capstone/호진파일/Mirror_therapy_fixed.py'
tree=ast.parse(io.open(SRC,encoding='utf-8').read())
want={'_dedup_time','ang_velocity','sparc','split_segments','cycle_bounds','sparc_cycle_mean'}
mods=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in want]
ns={'np':np,'DT_MIN_S':0.005,'VALID_GAP_MAX_S':0.5,'SPARC_VBAR':0.05,
    'SPARC_FC_MAX_HZ':10.0,'CYCLE_HYST':0.15,'CYCLE_MIN_RANGE':15.0}
for n in mods:
    exec(compile(ast.Module(body=[n],type_ignores=[]),'<x>','exec'),ns)
print("추출한 함수:",sorted(n.name for n in mods))
print()
D='capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남'
byfid={}
for r in csv.DictReader(open(os.path.join(D,[f for f in os.listdir(D) if f.endswith('_distance_comparison.csv')][0]),encoding='utf-8-sig')):
    byfid[(r['Frame_ID'],r['Hand'])]=r
raw=[r for r in csv.DictReader(open([f for f in glob.glob(D+'/*continuous_raw.csv') if 'split' not in f.split(os.sep)][0],encoding='utf-8-sig')) if r['Trial']!='Rest']
PIP=['Index_PIP_filt','Middle_PIP_filt','Ring_PIP_filt','Pinky_PIP_filt']
G=defaultdict(list)
for r in raw: G[(r['Trial'],r['hand'])].append(r)
print("### Trial_1 Right — 고정본 함수 vs 원본 방식 ###")
rl=G[('Trial_1','Right')]
flex=np.array([np.mean([float(r[j]) for j in PIP]) for r in rl])
for label,t in [('원래 time_s(벽시계) [롤백해서 1e-9 비교]', np.array([float(r['time_s']) for r in rl])),
                ('수집 단조 r[mono] (고정본 시간축)', np.array([float(byfid[(r['Frame_ID'],r['hand'])]['capture_monotonic_s']) for r in rl]))]:
    av=ns['ang_velocity'](t,flex)
    if av is None: print(f"  {label:<38} ang_velocity=None (전부 제거/이상)"); continue
    tt,ff,_=ns['_dedup_time'](t,flex)
    vel=np.gradient(ff,tt)
    sp_abs=ns['sparc'](np.abs(vel),tt)
    sp_cyc=ns['sparc_cycle_mean'](np.abs(vel),tt,flex=ff)
    print(f"  {label}")
    print(f"     n={av['n']} dropped={av['dropped']}  peak={av['peak']:.1f}  P95={av['p95']:.1f}  "
          f"peak_ext={av['peak_ext']:.1f}  P95_ext={av['p95_ext']:.1f}")
    print(f"     SPARC(전체, |v|, 적응컷오프)={sp_abs if sp_abs is None else round(sp_abs,3)}   "
          f"SPARC(사이클평균)={sp_cyc if sp_cyc is None else round(sp_cyc,3)}")
print()
print("### 고정본으로 16시행 재계산 (수집 단조 시계, PIP) ###")
print(f"{'Trial':<9}{'Hand':<7}{'peak':>9}{'P95':>8}{'SPARC전체':>11}{'SPARC사이클':>12}{'drop':>6}{'seg':>5}")
pk=[];q5=[];sp1=[];sp2=[]
for k in sorted(G.keys()):
    rl=G[k]
    t=np.array([float(byfid[(r['Frame_ID'],r['hand'])]['capture_monotonic_s']) for r in rl if (r['Frame_ID'],r['hand']) in byfid])
    f=np.array([np.mean([float(r[j]) for j in PIP]) for r in rl if (r['Frame_ID'],r['hand']) in byfid])
    av=ns['ang_velocity'](t,f)
    tt,ff,_=ns['_dedup_time'](t,f)
    vel=np.gradient(ff,tt)
    a=ns['sparc'](np.abs(vel),tt); b=ns['sparc_cycle_mean'](np.abs(vel),tt,flex=ff)
    segs=len(ns['split_segments'](tt))
    pk.append(av['peak']); q5.append(av['p95']); sp1.append(a); sp2.append(b)
    print(f"{k[0]:<9}{k[1]:<7}{av['peak']:>9.1f}{av['p95']:>8.1f}"
          f"{(f'{a:.2f}' if a is not None else '-'):>11}{(f'{b:.2f}' if b is not None else '-'):>12}"
          f"{av['dropped']:>6}{segs:>5}")
print()
print(f"  peak   중앙 {np.median(pk):.1f}  범위 [{min(pk):.0f}, {max(pk):.0f}]")
print(f"  P95    중앙 {np.median(q5):.1f}  범위 [{min(q5):.0f}, {max(q5):.0f}]")
sp1v=[x for x in sp1 if x is not None]; sp2v=[x for x in sp2 if x is not None]
print(f"  SPARC(전체)  중앙 {np.median(sp1v):.2f}  범위 [{min(sp1v):.2f}, {max(sp1v):.2f}]")
print(f"  SPARC(사이클) 중앙 {np.median(sp2v):.2f}  범위 [{min(sp2v):.2f}, {max(sp2v):.2f}]")
print(f"  참고: 구 파이프라인 SPARC 중앙 -8.64  /  원논문 주기운동 예시는 사이클 분할 사용")

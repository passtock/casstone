# -*- coding: utf-8 -*-
"""지표 편입 조건 — 정정판 (C2 = MDC, C4 = 주입 민감도).

정정 사유(2026-09-28, 사용자 질의):
  · C2를 'CV ≤ 25%'로 잡은 것은 (a) 문헌 근거가 없고 (b) 방법론적으로 틀렸다.
    CV는 피험자 간 변동을 섞는다. 반복성은 MDC(test-retest) 또는 ICC로 잰다.
    → C2 = MDC95 / |mean| ≤ 50%   (Wagner 2008: 취약 지표는 50% 이상 변해야 진짜 변화;
                                     그 논문의 MDC 범위 7.4–98.9%)
  · C4를 'u/기저 P95 > 0.10' 규칙에 연결한 것은 잘못된 차용이었다.
    그 규칙은 '오차 대 신호 비율'(u)이고, 동적범위(IQR/median)와 다른 양이다.
    → C4 = 개입 민감도: 주입(bias 1u = 기저의 10%)이 그 지표 P95를 ≥10% 움직이는가
           (계획서 §3-16: burst는 P95를 ≤2.6%밖에 못 움직여 "실험 무효")
           ※ u 미측정 상태이므로 C4는 '보류(pending)'로 표기한다.

데이터: capstone/호진파일/.../trials_summary.csv (비장애인 2명)
출력:   experiments/results/metric_portfolio_check_v2.txt
"""
import csv, glob, os, math, io, sys, statistics as st
from collections import defaultdict

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/metric_portfolio_check_v2.txt"

LIM = {"angle_max": 180.0, "finger_tam_max": 360.0, "tam5_max": 1500.0,
       "speed_max": 2000.0, "sparc_max": 0.0, "mga_min": 0.0, "mga_max": 250.0,
       "time_max": 120.0}
ANGLE = ["Index_ROM_deg", "Index_ROM_3D_deg", "RS_Index_ROM_deg",
         "Thumb_CMC_ROM_deg", "Thumb_PalmarAbd_max_deg", "Thumb_PalmarAbd_ROM_deg",
         "Thumb_RadialAbd_max_deg", "Thumb_RadialAbd_ROM_deg",
         "ROM_Thumb_CMC_deg", "ROM_Thumb_MCP_deg", "ROM_Thumb_IP_deg",
         "ROM_Index_MCP_deg", "ROM_Index_PIP_deg", "ROM_Index_DIP_deg",
         "ROM_Middle_MCP_deg", "ROM_Middle_PIP_deg", "ROM_Middle_DIP_deg",
         "ROM_Ring_MCP_deg", "ROM_Ring_PIP_deg", "ROM_Ring_DIP_deg",
         "ROM_Pinky_MCP_deg", "ROM_Pinky_PIP_deg", "ROM_Pinky_DIP_deg"]
FINGER_TAM = ["TAM_Thumb_deg", "TAM_Index_deg", "TAM_Middle_deg", "TAM_Ring_deg", "TAM_Pinky_deg"]
SPEED = ["Flex_Speed_deg_s", "Ext_Speed_deg_s"]
SPARC = ["SPARC"]
MGA = ["MGA_cm", "MGA_mm_3D", "MGA_mm_3D_cal", "MP_MGA_raw_mm", "RS_MGA_raw_mm", "RS_MGA_p95_mm"]
TIME = ["Duration_s", "Cycle_Period_s", "Valid_Duration_s"]
CANDIDATES = ANGLE + FINGER_TAM + ["TAM_total_deg"] + SPEED + SPARC + MGA + TIME

def fnum(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except Exception:
        return None

def plausible(col, v):
    if v is None: return None
    if col == "TAM_total_deg": return 0.0 <= v <= LIM["tam5_max"]
    if col in FINGER_TAM: return 0.0 <= v <= LIM["finger_tam_max"]
    if col in ANGLE: return 0.0 <= v <= LIM["angle_max"]
    if col in SPEED: return 0.0 <= v <= LIM["speed_max"]
    if col in SPARC: return v <= LIM["sparc_max"]
    if col in MGA: return LIM["mga_min"] <= v <= LIM["mga_max"]
    if col in TIME: return 0.0 < v <= LIM["time_max"]
    return True

rows = []
for f in glob.glob(os.path.join(ROOT, "*", "*_trials_summary.csv")):
    if "/split/" in f.replace("\\", "/"): continue
    with open(f, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            r["_s"] = os.path.basename(os.path.dirname(f)); rows.append(r)
G = defaultdict(list)
for r in rows:
    G[(r["_s"], r.get("Task", "?"), r.get("Hand", "?"))].append(r)

def mdc_ratio(vals):
    """MDC95 / |mean| × 100  (반복시행 기준)"""
    v = [x for x in vals if x is not None]
    if len(v) < 3: return None
    m = st.mean(v)
    if abs(m) < 1e-9: return None
    sd = st.stdev(v)                       # 표본 SD (within-subject 반복)
    mdc = 1.96 * math.sqrt(2) * sd
    return mdc / abs(m) * 100.0

lines = []
def out(s=""): lines.append(s)
out("=" * 92)
out("지표 편입 조건 — 정정판:  C2 = MDC95/|mean| ≤ 50%   (구판 C2 = CV ≤ 25% 폐기)")
out("=" * 92)
out("정정 사유: CV는 피험자 간 변동을 섞어 반복성 지표로 부적합 → MDC(test-retest)로 교체.")
out("           근거: Wagner 2008 (계획서 §3-7) — 취약 지표는 50% 이상 변해야 '진짜 변화', MDC 7.4–98.9%.")
out()
hdr = f"{'지표':<26}{'n':>4}{'결측%':>7}{'MDC95/mean%':>13}{'물리위반%':>10}  판정(C1·C2·C3)"
out(hdr); out("-" * len(hdr))
res = []
for col in CANDIDATES:
    allv, miss, viol = [], 0, 0
    for k, g in G.items():
        for r in g:
            v = fnum(r.get(col))
            if v is None: miss += 1; continue
            if plausible(col, v) is False: viol += 1
            allv.append(v)
    n_tot = sum(len(g) for g in G.values()); n_val = len(allv)
    miss_rate = miss / n_tot * 100 if n_tot else None
    viol_rate = viol / n_val * 100 if n_val else None
    rs = [mdc_ratio([fnum(r.get(col)) for r in g]) for g in G.values()]
    rs = [x for x in rs if x is not None]
    mdc = st.median(rs) if rs else None
    ok1 = miss_rate is not None and miss_rate <= 20
    ok2 = mdc is not None and mdc <= 50
    ok3 = viol_rate is not None and viol_rate <= 5
    verdict = "편입가능" if (ok1 and ok2 and ok3) else "조건미달"
    res.append((col, n_val, miss_rate, mdc, viol_rate, verdict, (ok1, ok2, ok3)))
    out(f"{col:<26}{n_val:>4}{(f'{miss_rate:.0f}' if miss_rate is not None else '-'):>7}"
        f"{(f'{mdc:.1f}' if mdc is not None else '-'):>13}"
        f"{(f'{viol_rate:.0f}' if viol_rate is not None else '-'):>10}  {verdict} {ok1,ok2,ok3}")
out()
out("### 구판(CV) 대비 판정이 뒤바뀐 지표 ###")
CV_OLD = {"Thumb_CMC_ROM_deg": 18.1, "ROM_Index_MCP_deg": 13.4, "ROM_Index_DIP_deg": 16.0,
          "ROM_Middle_MCP_deg": 7.9, "ROM_Middle_PIP_deg": 9.2, "ROM_Middle_DIP_deg": 3.0,
          "ROM_Ring_MCP_deg": 15.0, "ROM_Ring_DIP_deg": 7.0, "ROM_Pinky_MCP_deg": 16.4,
          "ROM_Pinky_PIP_deg": 11.9, "ROM_Pinky_DIP_deg": 10.9, "MP_MGA_raw_mm": 7.4,
          "TAM_Pinky_deg": 7.5, "TAM_Thumb_deg": 7.2}
for col, n, m, d, v, vd, oks in res:
    if col in CV_OLD and vd != "편입가능":
        out(f"  ⚠ {col}: 구판 CV {CV_OLD[col]}% (통과) → 정정 MDC {d:.1f}% (미달)")
out()
out("### C4 (개입 민감도) — 보류 ###")
out("  주입(bias 1u = 기저의 10%)이 P95를 ≥10% 움직여야 함. 계획서 §3-16: burst는 ≤+2.6%로 '실험 무효'.")
out("  → u(실제 오차) 미측정 상태이므로 C4는 '보류(pending)'. 치구 135기록 후 확정.")
out()
out("### ICC(피험자 간 일반화)는 왜 개발군이 필요한가 ###")
out("  · 반복성(MDC)은 1명 × 반복시행만으로 계산된다 — 위 표가 그 결과다.")
out("  · ICC는 between-subject 분산이 필요하다. 파일럿은 피험자 2명 → df=1 → 추정 불안정.")
out("  · 정본의 비장애인 개발군 = 6명(§4.1). '6'은 통계 도출값이 아니라 정본의 설계 선택이다.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
print("\n".join(lines)); print("\n[saved]", OUT)

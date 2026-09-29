# -*- coding: utf-8 -*-
"""사용자 보고 계산의 독립 재현 — 20260915(26세 남) 단일 세션.

사용자가 제시한 사양:
  C1 결측률 = 결측 기록 ÷ 16 × 100            (≤20%)
  C2 반복성 = 손별 [1.96×√2×표본SD ÷ |평균| × 100] 의 **양손 중앙값**  (≤50%)
  C3 물리위반 = 허용범위 위반값 ÷ 유효값 × 100  (≤5%)
※ 이전(내) 계산과의 차이: 나는 양손을 합쳐 SD를 냈다(집단 간 분산 포함).
   사용자 방식이 '조건별 반복성' 정의에 더 맞다. 그래서 두 값을 나란히 낸다.

출력: experiments/results/replicate_20260915_userSpec.txt
"""
import csv, glob, io, math, os, sys, statistics as st

SRC = "capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남"
OUT = "experiments/results/replicate_20260915_userSpec.txt"

fd = glob.glob(os.path.join(SRC, "*_trials_summary.csv"))[0]
all_rows = list(csv.DictReader(open(fd, encoding="utf-8-sig")))
rows = [r for r in all_rows if r["Task"] == "Task 1"]
N = len(rows)  # 16

ID_COLS = {"Trial", "Hand", "Task", "Trial_Mode", "Start_s", "End_s", "Requested_Duration_s",
           "Interrupted", "RS_Landmarks_Mean", "RS_Dist_Median_m", "Valid_Duration_s",
           "Duration_s", "Cycles", "Samples", "RS_Valid_Samples", "Paired_Samples",
           "RS_Valid_Rate", "RS_minus_MP_mean_mm", "RS_MP_mean_abs_difference_mm"}

ANGLE = ["Index_ROM_deg", "Index_ROM_3D_deg", "RS_Index_ROM_deg", "Thumb_CMC_ROM_deg",
         "Thumb_PalmarAbd_max_deg", "Thumb_PalmarAbd_ROM_deg", "Thumb_RadialAbd_max_deg",
         "Thumb_RadialAbd_ROM_deg", "ROM_Thumb_CMC_deg", "ROM_Thumb_MCP_deg", "ROM_Thumb_IP_deg",
         "ROM_Index_MCP_deg", "ROM_Index_PIP_deg", "ROM_Index_DIP_deg", "ROM_Middle_MCP_deg",
         "ROM_Middle_PIP_deg", "ROM_Middle_DIP_deg", "ROM_Ring_MCP_deg", "ROM_Ring_PIP_deg",
         "ROM_Ring_DIP_deg", "ROM_Pinky_MCP_deg", "ROM_Pinky_PIP_deg", "ROM_Pinky_DIP_deg"]
FINGER_TAM = ["TAM_Thumb_deg", "TAM_Index_deg", "TAM_Middle_deg", "TAM_Ring_deg", "TAM_Pinky_deg"]
SPEED = ["Flex_Speed_deg_s", "Ext_Speed_deg_s"]
SPARC = ["SPARC"]
MGA = ["MGA_cm", "MGA_mm_3D", "MGA_mm_3D_cal", "MP_MGA_raw_mm", "RS_MGA_raw_mm", "RS_MGA_p95_mm"]


def f(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except Exception:
        return None


def violation(col, v):
    """물리적 허용범위를 벗어나면 True."""
    if col == "TAM_total_deg": return not (0.0 <= v <= 1500.0)
    if col in FINGER_TAM:      return not (0.0 <= v <= 360.0)
    if col in ANGLE:           return not (0.0 <= v <= 180.0)
    if col in SPEED:           return not (0.0 <= v <= 2000.0)
    if col in SPARC:           return not (v <= 0.0)
    if col in MGA:             return not (0.0 <= v <= 250.0)
    return False


def mdc_pct(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3: return None
    m = st.mean(v)
    if abs(m) < 1e-12: return None
    return 1.96 * math.sqrt(2) * st.stdev(v) / abs(m) * 100.0


# 지표 열 = 문자열로 파싱 가능한 수치 열 (식별자 제외)
cand = []
for c in rows[0].keys():
    if c in ID_COLS or c.startswith("Unnamed"): continue
    for r in rows:
        if f(r.get(c)) is not None: cand.append(c); break
cand = [c for c in cand if c not in ("Cycles",)]

lines = []
def out(s=""): lines.append(s)
out("=" * 104)
out("사용자 보고 계산의 독립 재현 — 20260915 (26세 남) · Task1 · 8시행 × 양손 = 16기록")
out("=" * 104)
out(f"원자료: {fd}")
out(f"지표 후보 열 수: {len(cand)}")
out()
hdr = (f"{'지표':<24}{'C1결측%':>9}{'C2(손별중앙)':>13}{'C2(양손통합)':>13}"
       f"{'C3위반%':>9}  판정")
out(hdr); out("-" * len(hdr))

n_pass = n_fail = 0
report = {}
for col in cand:
    vals = [f(r.get(col)) for r in rows]
    nmiss = sum(1 for x in vals if x is None)
    c1 = nmiss / N * 100
    L = [f(r.get(col)) for r in rows if r["Hand"] == "Left"]
    R = [f(r.get(col)) for r in rows if r["Hand"] == "Right"]
    ml, mr = mdc_pct(L), mdc_pct(R)
    c2_hand = st.median([x for x in (ml, mr) if x is not None]) if (ml is not None or mr is not None) else None
    c2_pool = mdc_pct(vals)
    valid = [x for x in vals if x is not None]
    viol = [x for x in valid if violation(col, x)]
    c3 = len(viol) / len(valid) * 100 if valid else None

    ok1 = c1 <= 20
    ok2 = (c2_hand is not None) and (c2_hand <= 50)
    ok3 = (c3 is not None) and (c3 <= 5)
    verdict = "통과" if (ok1 and ok2 and ok3) else ("사용불가" if c2_hand is None else "미달")
    if verdict == "통과": n_pass += 1
    else: n_fail += 1
    report[col] = (c1, c2_hand, c2_pool, c3, verdict)
    out("%-24s%9.1f%13s%13s%9s  %s" % (
        col, c1,
        ("%.1f" % c2_hand) if c2_hand is not None else "평가불가",
        ("%.1f" % c2_pool) if c2_pool is not None else "평가불가",
        ("%.1f" % c3) if c3 is not None else "평가불가", verdict))

out()
out(f"→ 통과 {n_pass} / 미달·불가 {n_fail}  (총 {len(cand)}개)")
out()
out("### 사용자가 제시한 값과 대조 ###")
CHK = [
    ("Index_ROM_deg", 0, 17.2, 0, "통과"),
    ("Index_ROM_3D_deg", 0, 11.4, 0, "통과"),
    ("TAM_total_deg", 0, 10.8, 0, "통과"),
    ("MGA_cm", 0, 17.6, 0, "통과"),
    ("Thumb_CMC_ROM_deg", 0, 53.6, 0, "미달"),
    ("Flex_Speed_deg_s", 0, 399.8, 100, "미달"),
    ("Ext_Speed_deg_s", 0, 252.7, 100, "미달"),
    ("SPARC", 0, 102.0, 0, "미달"),
    ("RS_MGA_p95_mm", 18.8, 102.1, 0, "미달"),
    ("MGA_mm_3D_cal", 100, None, None, "사용불가"),
]
out(f"{'지표':<24}{'보고 C1':>9}{'재현 C1':>9}{'보고 C2':>9}{'재현 C2':>9}{'보고 C3':>9}{'재현 C3':>9}  일치")
for col, c1, c2, c3, vd in CHK:
    if col not in report:
        out(f"{col:<24}  (이 세션 열에 없음)")
        continue
    r1, r2h, r2p, r3, rv = report[col]
    def close(a, b, tol=0.6):
        if a is None and b is None: return True
        if a is None or b is None: return False
        return abs(a - b) <= tol
    ok = close(c1, r1) and close(c2, r2h) and (close(c3, r3) if c3 is not None else r3 is None)
    out("%-24s%9s%9.1f%9s%9s%9s%9s  %s" % (
        col, c1, r1, c2 if c2 is not None else "-",
        ("%.1f" % r2h) if r2h is not None else "-",
        c3 if c3 is not None else "-",
        ("%.1f" % r3) if r3 is not None else "-",
        "✅" if ok else "❌"))
out()
out("### C2 추정량 차이: 손별 중앙값 vs 양손 통합 ###")
out(f"{'지표':<24}{'손별 중앙값':>13}{'양손 통합':>12}{'차이':>9}  의미")
for col in ["Index_ROM_deg", "TAM_total_deg", "MGA_cm", "Thumb_CMC_ROM_deg",
            "SPARC", "Flex_Speed_deg_s", "Ext_Speed_deg_s"]:
    if col in report:
        _, h, p, _, _ = report[col]
        if h is not None and p is not None:
            out("%-24s%13.1f%12.1f%9.1f  %s" % (col, h, p, p - h,
                "손별이 더 보수적" if h > p else "통합이 더 보수적"))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
print("\n".join(lines)); print("\n[saved]", OUT)

# -*- coding: utf-8 -*-
"""추가 운동학 지표 편입 조건 — 파일럿 데이터 통계 검정.

목적: K1·K2는 무조건 포함. 그 외 후보 지표(TAM, ROM, MGA, SPARC, 속도 계열 등)는
      '조건'을 통과할 때만 실험에 편입한다. 그 조건을 파일럿 실데이터로 검정한다.

데이터: capstone/호진파일/outputs/데이터_저장/*/..._trials_summary.csv
        (비장애인 2명, Task1 맨손쥐기펴기 8시행 · Task3 원통형파지)

판정 기준(4개) — 전부 만족해야 편입:
  C1 결측률 ≤ 20%            (계산 가능성)
  C2 시행 간 CV ≤ 25%        (반복성)
  C3 물리적 타당성 위반 ≤ 5% (값이 말이 되는가)
  C4 동적범위 ≥ 10%          (기저 대비 변동이 있어야 개입 효과가 보임)

출력: experiments/results/metric_portfolio_check.txt
"""
import csv, glob, math, os, io, sys, statistics as st
from collections import defaultdict

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/metric_portfolio_check.txt"

# ── 물리적 타당성 상한 (초과 = 위반) ──────────────────────────
# 각도: 사람 손가락/손목 가동범위를 크게 넘는 값은 파이프라인 오류
LIM = {
    # 근거: 정상 MCP≈90°·PIP≈100°·DIP≈90°(AAOS) → 개별 관절 최대 ~120–140°
    "angle_max": 180.0,
    # 근거: 정상 TAM(digit 2-5) 260–270°, 최대 ~330°
    "finger_tam_max": 360.0,
    # 근거: 4지×270° + 엄지 ~130° ≈ 1210°, 최대 ~1370°
    "tam5_max": 1500.0,
    # 근거: 주먹 쥐기 0.5–1.0 s에 ~250–300° → 평균 300–600°/s, 피크 2–3배 여유
    "speed_max": 2000.0,
    # 근거: SPARC = -∫(...) ≤ 0 (Balasubramanian 2015). 양수 = 파이프라인 오류
    "sparc_max": 0.0,
    "mga_min": 0.0, "mga_max": 250.0,   # mm (엄지–검지 표면점 거리)
    "time_max": 120.0,                  # ARAT 항목 60초 제한 + 여유
}
ANGLE = ["Index_ROM_deg", "Index_ROM_3D_deg", "RS_Index_ROM_deg",
         "TAM_Thumb_deg", "TAM_Index_deg", "TAM_Middle_deg", "TAM_Ring_deg", "TAM_Pinky_deg",
         "Thumb_CMC_ROM_deg", "Thumb_PalmarAbd_max_deg", "Thumb_PalmarAbd_ROM_deg",
         "Thumb_RadialAbd_max_deg", "Thumb_RadialAbd_ROM_deg",
         "ROM_Thumb_CMC_deg", "ROM_Thumb_MCP_deg", "ROM_Thumb_IP_deg",
         "ROM_Index_MCP_deg", "ROM_Index_PIP_deg", "ROM_Index_DIP_deg",
         "ROM_Middle_MCP_deg", "ROM_Middle_PIP_deg", "ROM_Middle_DIP_deg",
         "ROM_Ring_MCP_deg", "ROM_Ring_PIP_deg", "ROM_Ring_DIP_deg",
         "ROM_Pinky_MCP_deg", "ROM_Pinky_PIP_deg", "ROM_Pinky_DIP_deg"]
ANGLE += ["TAM_total_deg"]          # 별도 상한 적용
SPEED = ["Flex_Speed_deg_s", "Ext_Speed_deg_s"]
SPARC = ["SPARC"]
MGA = ["MGA_cm", "MGA_mm_3D", "MGA_mm_3D_cal", "MP_MGA_raw_mm", "RS_MGA_raw_mm", "RS_MGA_p95_mm"]
# K1·K2 대리(파일럿 명명)
K1_PROXY = ["MGA_mm_3D_cal", "MGA_mm_3D"]
TIME = ["Duration_s", "Cycle_Period_s", "Valid_Duration_s"]
CANDIDATES = ANGLE + SPEED + SPARC + MGA + TIME


def fnum(s):
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def plausible(col, v):
    if v is None:
        return None
    if col == "TAM_total_deg":
        return 0.0 <= v <= LIM["tam5_max"]
    if col in ("TAM_Thumb_deg", "TAM_Index_deg", "TAM_Middle_deg", "TAM_Ring_deg", "TAM_Pinky_deg") or col.startswith("ROM_"):
        return 0.0 <= v <= LIM["finger_tam_max"] if col.startswith("TAM_") else 0.0 <= v <= LIM["angle_max"]
    if col in ANGLE:
        return 0.0 <= v <= LIM["angle_max"]
    if col in SPEED:
        return 0.0 <= v <= LIM["speed_max"]
    if col in SPARC:
        return v <= LIM["sparc_max"]
    if col in MGA:
        return LIM["mga_min"] <= v <= LIM["mga_max"]
    if col in TIME:
        return 0.0 < v <= LIM["time_max"]
    return True


# ── 데이터 로드 (세션 레벨 = 전체 시행 포함) ──────────────────
rows = []
for f in glob.glob(os.path.join(ROOT, "*", "*_trials_summary.csv")):
    if "/split/" in f.replace("\\", "/"):
        continue
    with open(f, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            r["_src"] = os.path.basename(os.path.dirname(f))
            rows.append(r)

groups = defaultdict(list)
for r in rows:
    groups[(r["_src"], r.get("Task", "?"), r.get("Hand", "?"))].append(r)

def cv(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    m = st.mean(vals)
    if abs(m) < 1e-12:
        return None
    return st.pstdev(vals) / abs(m) * 100.0

lines = []
def out(s=""):
    lines.append(s)

out("=" * 78)
out("추가 지표 편입 조건 검정 — 파일럿 실데이터 (비장애인 2명)")
out("=" * 78)
out(f"그룹(세션×과제×손) 수: {len(groups)}")
for k, v in sorted(groups.items()):
    out(f"  · {k[0]} | {k[1]} | {k[2]} : n_trials={len(v)}")
out()
out("판정 기준: C1 결측률≤20% · C2 시행간CV≤25% · C3 물리위반≤5% · C4 동적범위≥10%")
out()

summary = []
for col in CANDIDATES:
    allv, miss, viol = [], 0, 0
    for k, g in groups.items():
        for r in g:
            raw = r.get(col, "")
            v = fnum(raw)
            if v is None:
                miss += 1
                continue
            p = plausible(col, v)
            if p is False:
                viol += 1
            allv.append(v)
    n_tot = sum(len(g) for g in groups.values())
    n_val = len(allv)
    miss_rate = (miss / n_tot * 100) if n_tot else None
    viol_rate = (viol / n_val * 100) if n_val else None
    # 시행 간 CV (그룹 평균)
    cvs = [cv([fnum(r.get(col)) for r in g]) for g in groups.values()]
    cvs = [c for c in cvs if c is not None]
    cv_med = st.median(cvs) if cvs else None
    # 동적범위: (mean+1SD)/(mean-1SD) 상대 폭 — 여기서는 IQR/median 로 단순화
    if len(allv) >= 4:
        allv_s = sorted(allv)
        q1 = allv_s[len(allv_s)//4]; q3 = allv_s[3*len(allv_s)//4]
        med = st.median(allv_s)
        dyn = abs(q3 - q1) / abs(med) * 100 if abs(med) > 1e-12 else None
    else:
        dyn = None
    ok1 = (miss_rate is not None and miss_rate <= 20)
    ok2 = (cv_med is not None and cv_med <= 25)
    ok3 = (viol_rate is not None and viol_rate <= 5)
    ok4 = (dyn is not None and dyn >= 10)
    verdict = "편입가능" if (ok1 and ok2 and ok3 and ok4) else "조건미달"
    summary.append((col, n_val, miss_rate, cv_med, viol_rate, dyn, verdict,
                    (ok1, ok2, ok3, ok4)))

hdr = f"{'지표':<26}{'n':>4}{'결측%':>8}{'CV%':>8}{'물리위반%':>10}{'동적범위%':>10}  판정"
out(hdr); out("-" * len(hdr))
for c, n, m, k2, v, d, vd, oks in summary:
    out(f"{c:<26}{n:>4}{(f'{m:.0f}' if m is not None else '-'):>8}"
        f"{(f'{k2:.1f}' if k2 is not None else '-'):>8}"
        f"{(f'{v:.0f}' if v is not None else '-'):>10}"
        f"{(f'{d:.0f}' if d is not None else '-'):>10}  {vd} {oks}")
out()
out("### 결측 C1 / CV C2 / 물리 C3 / 동적범위 C4 실패 지표 ###")
for c, n, m, k2, v, d, vd, oks in summary:
    if vd != "편입가능":
        why = [n_ for n_, ok in zip("C1 C2 C3 C4".split(), oks) if not ok]
        out(f"  ✗ {c}  (실패: {', '.join(why)})")
out()
out("### K1·K2 대리 지표 상태 ###")
for c in K1_PROXY:
    r = [s for s in summary if s[0] == c]
    if r:
        c0, n, m, k2, v, d, vd, oks = r[0]
        out(f"  · {c0}: n={n} 결측={'-' if m is None else f'{m:.0f}%'} CV={'-' if k2 is None else f'{k2:.1f}%'} 물리위반={'-' if v is None else f'{v:.0f}%'} → {vd}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("\n[saved]", OUT)

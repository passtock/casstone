# -*- coding: utf-8 -*-
"""세션 하나의 trials_summary.csv 로 지표 편입 조건(C1·C2·C3)을 재검사.

사용: python experiments/analysis/metric_recheck_session.py "<세션폴더>"
근거: experiments/analysis/metric_portfolio_check_v2.py 와 동일 규칙
      (C1 결측≤20% · C2 MDC95/|mean|≤50% · C3 물리위반≤5%)
작성 2026-09-30.
"""
import csv
import glob
import io
import math
import os
import statistics as st
import sys
from collections import defaultdict

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
FINGER_TAM = ["TAM_Thumb_deg", "TAM_Index_deg", "TAM_Middle_deg",
              "TAM_Ring_deg", "TAM_Pinky_deg"]
SPEED = ["Flex_Speed_deg_s", "Ext_Speed_deg_s"]
SPARC = ["SPARC"]
MGA = ["MGA_cm", "MGA_mm_3D", "MGA_mm_3D_cal", "MP_MGA_raw_mm",
       "RS_MGA_raw_mm", "RS_MGA_p95_mm"]
TIME = ["Duration_s", "Cycle_Period_s", "Valid_Duration_s"]
CAND = ANGLE + FINGER_TAM + ["TAM_total_deg"] + SPEED + SPARC + MGA + TIME


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def plausible(col, v):
    if v is None:
        return None
    if col == "TAM_total_deg":
        return 0.0 <= v <= LIM["tam5_max"]
    if col in FINGER_TAM:
        return 0.0 <= v <= LIM["finger_tam_max"]
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


def mdc_ratio(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return None
    m = st.mean(v)
    if abs(m) < 1e-9:
        return None
    sd = st.stdev(v)
    return 1.96 * math.sqrt(2) * sd / abs(m) * 100.0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sess = sys.argv[1].rstrip("/\\")
    files = [p for p in glob.glob(os.path.join(sess, "*_trials_summary.csv"))]
    if not files:
        print("trials_summary.csv 없음: %s" % sess)
        return 1
    rows = []
    with io.open(files[0], encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            r["_s"] = os.path.basename(sess)
            rows.append(r)

    print("=" * 100)
    print("세션: %s" % os.path.basename(sess))
    print("파일: %s   (시행 %d건)" % (os.path.basename(files[0]), len(rows)))
    print("=" * 100)

    show = ["Trial", "Hand", "Task", "Trial_Mode", "Duration_s", "Cycles",
            "SPARC", "MGA_cm", "MGA_mm_3D", "MP_MGA_raw_mm", "TAM_total_deg",
            "Index_ROM_deg", "Samples", "Paired_Samples", "RS_Valid_Rate"]
    show = [c for c in show if c in rows[0]]
    print("\n[1] 시행별 값")
    print("  " + " | ".join("%s" % c for c in show))
    for r in rows:
        print("  " + " | ".join(str(r.get(c, ""))[:16] for c in show))

    G = defaultdict(list)
    for r in rows:
        G[(r.get("Task", "?"), r.get("Hand", "?"))].append(r)
    print("\n  그룹(Task×Hand) 수 = %d" % len(G))

    print("\n[2] 지표 편입 조건 재검사 (C1 결측<=20%% · C2 MDC95/|mean|<=50%% · C3 위반<=5%%)")
    hdr = "%-24s%6s%8s%14s%11s  %s" % ("지표", "n", "결측%", "MDC95/mean%", "위반%", "판정")
    print(hdr)
    print("-" * len(hdr))
    for col in CAND:
        allv, miss, viol = [], 0, 0
        for g in G.values():
            for r in g:
                v = fnum(r.get(col))
                if v is None:
                    miss += 1
                    continue
                if plausible(col, v) is False:
                    viol += 1
                allv.append(v)
        n_tot = sum(len(g) for g in G.values())
        n_val = len(allv)
        miss_rate = miss / n_tot * 100 if n_tot else None
        viol_rate = viol / n_val * 100 if n_val else None
        rs = [mdc_ratio([fnum(r.get(col)) for r in g]) for g in G.values()]
        rs = [x for x in rs if x is not None]
        mdc = st.median(rs) if rs else None
        ok1 = miss_rate is not None and miss_rate <= 20
        ok2 = mdc is not None and mdc <= 50
        ok3 = viol_rate is not None and viol_rate <= 5
        verdict = "편입가능" if (ok1 and ok2 and ok3) else "조건미달"
        mdc_s = "%.1f" % mdc if mdc is not None else "-"
        print("%-24s%6d%8s%14s%11s  %s %s" % (
            col, n_val,
            "%.0f" % miss_rate if miss_rate is not None else "-",
            mdc_s,
            "%.0f" % viol_rate if viol_rate is not None else "-",
            verdict, (ok1, ok2, ok3)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

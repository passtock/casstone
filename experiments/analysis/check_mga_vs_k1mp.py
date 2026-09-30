# -*- coding: utf-8 -*-
"""MGA(max) vs K1_mp(P95) 중복성 검사 — 같은 aperture 시계열의 max와 P95.

질문: "MGA와 K1_mp를 둘 다 넣어야 하나? 사실상 같은 것 아닌가?"
측정: 시행×손별로 MP aperture 시계열에서 max(=MGA)와 P95(=K1_mp)를 뽑아
      (a) 상관, (b) 비율(max/P95), (c) 각각의 반복성(MDC95/|mean|)을 본다.
작성 2026-09-30. 읽기 전용.
"""
import csv
import glob
import io
import math
import os
import statistics as st
import sys
from collections import defaultdict

TIP_T, TIP_I = "4", "8"


def d3(a, b):
    try:
        return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))
    except Exception:
        return None


def p95(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    pos = 0.95 * (len(v) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] * (1 - (pos - lo)) + v[hi] * (pos - lo)


def md_ratio(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return None
    m = st.mean(v)
    if abs(m) < 1e-9:
        return None
    return 1.96 * math.sqrt(2) * st.stdev(v) / abs(m) * 100.0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sess = sys.argv[1].rstrip("/\\")
    files = sorted(glob.glob(os.path.join(sess, "split", "*", "*", "*_landmarks.csv")))
    if not files:
        print("split/*/*/*_landmarks.csv 없음")
        return 1

    rows = []
    for f in files:
        trial = os.path.basename(os.path.dirname(f)).replace("Trial_", "T")
        rec = defaultdict(dict)
        with io.open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r.get("Landmark_ID") not in (TIP_T, TIP_I):
                    continue
                rec[(r.get("Hand"), r.get("Frame_ID"))][r["Landmark_ID"]] = (
                    r.get("MP_X_m"), r.get("MP_Y_m"), r.get("MP_Z_m"),
                    r.get("RS_X_m"), r.get("RS_Y_m"), r.get("RS_Z_m"), r.get("RS_Status"))
        for hand in sorted({k[0] for k in rec}):
            mp, rs = [], []
            for (h, fid), d in rec.items():
                if h != hand or TIP_T not in d or TIP_I not in d:
                    continue
                a, b = d[TIP_T], d[TIP_I]
                v = d3(a[:3], b[:3])
                if v is not None:
                    mp.append(v * 1000.0)
                if a[6] == "ok" and b[6] == "ok":
                    w = d3(a[3:6], b[3:6])
                    if w is not None:
                        rs.append(w * 1000.0)
            if len(mp) < 3:
                continue
            F = {"Trial": trial, "Hand": hand, "n": len(mp),
                 "mp_max": max(mp), "mp_p95": p95(mp), "mp_mean": st.mean(mp),
                 "rs_max": max(rs) if rs else None, "rs_p95": p95(rs) if rs else None}
            rows.append(F)
            print("%-4s %-6s n=%3d | MP max %6.1f  P95 %6.1f (비 %4.2f) | RS max %6s P95 %6s" % (
                trial, hand, F["n"], F["mp_max"], F["mp_p95"], F["mp_max"] / F["mp_p95"],
                ("%.1f" % F["rs_max"]) if F["rs_max"] else "-",
                ("%.1f" % F["rs_p95"]) if F["rs_p95"] else "-"))

    print("")
    print("[상관] 시행×손 전체에서 max vs P95")
    xs = [r["mp_max"] for r in rows]
    ys = [r["mp_p95"] for r in rows]
    if len(xs) >= 3:
        mx, my = st.mean(xs), st.mean(ys)
        cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
        sy = math.sqrt(sum((b - my) ** 2 for b in ys))
        print("  Pearson r = %.4f   (n=%d)" % (cov / (sx * sy), len(xs)))
        print("  평균 max/P95 비 = %.3f  (1.00 = 완전 중복)" % (st.mean([a / b for a, b in zip(xs, ys)])))
    print("")
    print("[반복성] 시행 간 MDC95/|mean| %  (C2 기준 ≤50%)")
    for hand in sorted({r["Hand"] for r in rows}):
        g = [r for r in rows if r["Hand"] == hand]
        print("  [%-6s] n=%d  MP_max=%.1f%%  MP_P95=%.1f%%  MP_mean=%.1f%%" % (
            hand, len(g),
            md_ratio([r["mp_max"] for r in g]) or -1,
            md_ratio([r["mp_p95"] for r in g]) or -1,
            md_ratio([r["mp_mean"] for r in g]) or -1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""게이트 중 어느 것이 실제로 프레임/랜드마크를 버리는지 손별로 집계.

앱(Mirror_therapy_clock_v3.py) 게이트 재현:
  1단(픽셀): depth_hole / depth_out_of_range / insufficient_depth / depth_edge(p10-p90 > 0.03 m)
  2단: depth_off_hand — 손 대표깊이(median)에서 12 cm 초과
  3단: implausible_span — 손목(0)에서 260 mm 초과
  지표: aperture(엄지4-검지8) > 150 mm → 폐기
작성 2026-09-30. 읽기 전용.
"""
import csv
import glob
import io
import math
import os
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TIPS = ("4", "8")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sess = sys.argv[1].rstrip("/\\")
    fs = glob.glob(os.path.join(sess, "*_landmarks.csv"))
    if not fs:
        print("landmarks.csv 없음")
        return 1

    # 프레임(Hand,Frame_ID) 단위로 21점 수집
    frames = defaultdict(dict)
    with io.open(fs[0], encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            key = (r.get("Hand"), r.get("Frame_ID"))
            frames[key][r.get("Landmark_ID")] = {
                "st": (r.get("RS_Status") or "").strip(),
                "rs": (r.get("RS_X_m"), r.get("RS_Y_m"), r.get("RS_Z_m")),
                "mp": (r.get("MP_X_m"), r.get("MP_Y_m"), r.get("MP_Z_m")),
            }

    def d3(a, b):
        try:
            return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))
        except Exception:
            return None

    stat = Counter()
    per_hand = defaultdict(Counter)
    n_ap_over = defaultdict(int)
    n_tip_ok = defaultdict(int)
    n_frame = defaultdict(int)
    span_bad = defaultdict(int)
    for (hand, fid), lm in frames.items():
        n_frame[hand] += 1
        for lid, v in lm.items():
            per_hand[hand][v["st"] or "(blank)"] += 1
        t, i = lm.get("4"), lm.get("8")
        if not t or not i:
            continue
        if t["st"] == "ok" and i["st"] == "ok":
            n_tip_ok[hand] += 1
            a_rs = d3(t["rs"], i["rs"])
            if a_rs is not None and a_rs * 1000 > 150.0:
                n_ap_over[hand] += 1
        # span 검사(RS)
        rs_pts = {k: v["rs"] for k, v in lm.items() if v["st"] == "ok"}
        if len(rs_pts) >= 5:
            xs = [p for p in rs_pts.values() if all(z is not None for z in p)]
            if len(xs) >= 5:
                org = xs[0]
                for p in xs:
                    dd = d3(p, org)
                    if dd is not None and dd * 1000 > 260.0:
                        span_bad[hand] += 1
                        break

    print("=" * 84)
    print("손별 프레임 수: %s" % {k: v for k, v in sorted(n_frame.items())})
    print("=" * 84)
    print("\n[1] 손별 RS_Status(21점 전부) 분포")
    for hand in sorted(per_hand):
        c = per_hand[hand]
        s = sum(c.values())
        print("  [%s] total=%d" % (hand, s))
        for k, v in c.most_common():
            print("        %-22s %7d (%.2f%%)" % (k, v, 100.0 * v / s))
    print("\n[2] 끝점(4·8) 둘 다 ok 인 프레임 / aperture>150mm / span>260mm")
    for hand in sorted(n_frame):
        nf = n_frame[hand]
        print("  [%s] 전체 %d | 두 끝점 ok %d (%.1f%%) | 그중 aperture>150mm %d | span>260mm 프레임 %d" % (
            hand, nf, n_tip_ok[hand], 100.0 * n_tip_ok[hand] / nf,
            n_ap_over[hand], span_bad[hand]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""앱 저장본(landmarks.csv)에서 MGA·tMGA를 직접 계산.

입력: 세션폴더 (split/<task>/<trial>/*_landmarks.csv 가 있어야 함)
출력: 시행×손별 MGA(mm)·tMGA(s)·tMGA_n(정규화) + 그룹별 반복성(MDC95/|mean|)
근거: 계획서 §12.2 (tMGA_n) · MGA_mm_3D 정의 · Yozbatiran/Jeannerod 맥락
작성 2026-09-30. 읽기 전용 — 앱/원자료를 수정하지 않는다.
"""
import csv
import glob
import io
import math
import os
import statistics as st
import sys
from collections import defaultdict

THUMB_TIP, INDEX_TIP = "4", "8"


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def dist3(a, b):
    if None in a or None in b:
        return None
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def md_ratio(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return None
    m = st.mean(v)
    if abs(m) < 1e-9:
        return None
    return 1.96 * math.sqrt(2) * st.stdev(v) / abs(m) * 100.0


def count_peaks(a, frac=0.5):
    """진폭의 frac 이상인 국소 최대 개수(대략적 cycle 수)."""
    if not a:
        return 0
    lo, hi = min(a), max(a)
    thr = lo + frac * (hi - lo)
    n = 0
    for i in range(1, len(a) - 1):
        if a[i] >= a[i - 1] and a[i] > a[i + 1] and a[i] >= thr:
            n += 1
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sess = sys.argv[1].rstrip("/\\")
    files = sorted(glob.glob(os.path.join(sess, "split", "*", "*", "*_landmarks.csv")))
    if not files:
        print("split/*/*/*_landmarks.csv 없음: %s" % sess)
        return 1

    print("=" * 96)
    print("세션: %s   (시행 %d개)" % (os.path.basename(sess), len(files)))
    print("=" * 96)
    hdr = ("%-8s %-6s %5s %9s %9s %9s %9s %9s %6s" %
           ("Trial", "Hand", "n", "MGA_MP", "tMGA_s", "tMGA_n", "MGA_RS", "RS유효율", "peaks"))
    print(hdr)
    print("-" * len(hdr))

    per = defaultdict(list)
    for f in files:
        trial = os.path.basename(os.path.dirname(f)).replace("Trial_", "T")
        rec = defaultdict(dict)
        with io.open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                lid = r.get("Landmark_ID")
                if lid not in (THUMB_TIP, INDEX_TIP):
                    continue
                key = (r.get("Frame_ID"), r.get("Hand"))
                rec[key][lid] = {
                    "t": fnum(r.get("time_s")),
                    "mp": (fnum(r.get("MP_X_m")), fnum(r.get("MP_Y_m")), fnum(r.get("MP_Z_m"))),
                    "rs": (fnum(r.get("RS_X_m")), fnum(r.get("RS_Y_m")), fnum(r.get("RS_Z_m"))),
                    "rs_ok": (r.get("RS_Status") == "ok"),
                }
        for hand in sorted({k[1] for k in rec}):
            rows = []
            for (fid, h), d in rec.items():
                if h != hand or THUMB_TIP not in d or INDEX_TIP not in d:
                    continue
                t = d[THUMB_TIP]["t"]
                a_mp = dist3(d[THUMB_TIP]["mp"], d[INDEX_TIP]["mp"])
                a_rs = None
                if d[THUMB_TIP]["rs_ok"] and d[INDEX_TIP]["rs_ok"]:
                    a_rs = dist3(d[THUMB_TIP]["rs"], d[INDEX_TIP]["rs"])
                rows.append((t, None if a_mp is None else a_mp * 1000.0,
                             None if a_rs is None else a_rs * 1000.0))
            rows = [r for r in rows if r[0] is not None]
            rows.sort()
            if len(rows) < 3:
                continue
            ts = [r[0] for r in rows]
            amp = [r[1] for r in rows]
            ars = [r[2] for r in rows]
            va = [x for x in amp if x is not None]
            if not va:
                continue
            mga_mp = max(va)
            i_pk = amp.index(mga_mp)
            t_mga = ts[i_pk]
            span = (ts[-1] - ts[0]) or 1e-9
            tmga_n = (t_mga - ts[0]) / span
            vrs = [x for x in ars if x is not None]
            mga_rs = max(vrs) if vrs else None
            rs_rate = len(vrs) / float(len(ars))
            peaks = count_peaks([x for x in amp if x is not None])
            print("%-8s %-6s %5d %9.1f %9.3f %9.3f %9s %9.3f %6d" % (
                trial, hand, len(va), mga_mp, t_mga, tmga_n,
                ("%.1f" % mga_rs) if mga_rs is not None else "-", rs_rate, peaks))
            per[hand].append((mga_mp, tmga_n, mga_rs))

    print("")
    print("[반복성] 시행 간 (MDC95/|mean| %) — C2 기준 ≤50%")
    for hand in sorted(per):
        gg = per[hand]
        r_mp = md_ratio([x[0] for x in gg])
        r_tn = md_ratio([x[1] for x in gg])
        r_rs = md_ratio([x[2] for x in gg])
        print("  %-6s MGA_MP=%s  tMGA_n=%s  MGA_RS=%s  (n=%d)" % (
            hand,
            ("%.1f" % r_mp) if r_mp is not None else "-",
            ("%.1f" % r_tn) if r_tn is not None else "-",
            ("%.1f" % r_rs) if r_rs is not None else "-", len(gg)))
    print("")
    print("⚠️ 이 세션은 Task1(자유 개폐)이며 시행 경계가 manual이다. tMGA는 '주기당 피크'라")
    print("   단일 reach-to-grasp(ARAT)에서의 tMGA와 의미가 다르다. 방향 확인용.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""세션의 깊이 유효성 실태를 손별·상태별로 집계.

입력: 세션폴더 (landmarks.csv)
출력: 손별 RS_Status 분포, MediaPipe(MP) 3D 존재율, RS_Depth_m 존재율, 프레임별 ok 비율
작성 2026-09-30. 읽기 전용.
"""
import csv
import glob
import io
import os
import sys
from collections import Counter, defaultdict

TIPS = {"4", "8"}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sess = sys.argv[1].rstrip("/\\")
    fs = glob.glob(os.path.join(sess, "*_landmarks.csv"))
    if not fs:
        print("landmarks.csv 없음")
        return 1
    f = fs[0]
    tot = Counter()
    per_hand = defaultdict(Counter)
    mp_present = Counter()
    rsD_present = Counter()
    frame_ok = defaultdict(lambda: [0, 0])   # hand -> [ok_rows, all_rows] (tip only)
    n = 0
    with io.open(f, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            lid = r.get("Landmark_ID")
            if lid not in TIPS:
                continue
            n += 1
            st = (r.get("RS_Status") or "(blank)").strip()
            hand = r.get("Hand")
            tot[st] += 1
            per_hand[hand][st] += 1
            if r.get("MP_X_m") not in ("", None):
                mp_present[hand] += 1
            if r.get("RS_Depth_m") not in ("", None):
                rsD_present[hand] += 1
            key = (hand, r.get("Frame_ID"))
            frame_ok[key][1] += 1
            if st == "ok":
                frame_ok[key][0] += 1

    print("=" * 84)
    print("파일: %s" % os.path.basename(f))
    print("엄지끝(4)+검지끝(8) 행 수: %d" % n)
    print("=" * 84)
    print("\n[1] 전체 RS_Status 분포")
    for k, v in tot.most_common():
        print("  %-24s %7d  (%.1f%%)" % (k, v, 100.0 * v / n))
    print("\n[2] 손별 RS_Status 분포")
    for hand in sorted(per_hand):
        c = per_hand[hand]
        s = sum(c.values())
        ok = c.get("ok", 0)
        print("  [%s] total=%d  ok=%d (%.1f%%)" % (hand, s, ok, 100.0 * ok / s if s else 0))
        for k, v in c.most_common():
            print("        %-24s %6d (%.1f%%)" % (k, v, 100.0 * v / s if s else 0))
    print("\n[3] 손별 파생값 존재율")
    for hand in sorted(mp_present):
        s = sum(per_hand[hand].values())
        print("  [%s] MP_X/Y/Z 존재 %d/%d (%.0f%%)   RS_Depth_m 존재 %d/%d (%.0f%%)" % (
            hand, mp_present[hand], s, 100.0 * mp_present[hand] / s,
            rsD_present[hand], s, 100.0 * rsD_present[hand] / s))
    print("\n[4] 프레임 단위(양 끝점 모두 ok) 비율")
    hb = defaultdict(lambda: [0, 0])
    for (hand, fid), (a, b) in frame_ok.items():
        hb[hand][0] += (1 if a == b else 0)
        hb[hand][1] += 1
    for hand in sorted(hb):
        both, tot_fr = hb[hand]
        print("  [%s] 두 끝점 모두 ok 인 프레임 %d/%d (%.0f%%)" % (
            hand, both, tot_fr, 100.0 * both / tot_fr if tot_fr else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())

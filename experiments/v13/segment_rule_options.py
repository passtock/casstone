# -*- coding: utf-8 -*-
"""v13 분절 규칙 후보의 효과 측정 (S1 처방 근거).

측정 대상(파일럿 8시행 × 좌우):
  · 프레임 기준 분절 불일치율을
      (a) 허용오차 = 고정 20%  vs  분절별 max(20%, 3×MAD)
      (b) 집계 = "1개 이상" vs "2개 이상" vs "3개 이상"
    조합마다 계산한다.
  · 기준선은 두 가지로 병기한다(파일럿에는 §6.3.1 정지구간이 없으므로):
      (i) 앞 15% 창   (ii) 전체 중앙값

주의: 이 측정은 **비장애인 파일럿**에서 수행했다. ARAT 점수·VLM 출력은 사용하지 않았다.
"""
from __future__ import annotations

import csv, glob, io, json, os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v12"))
from qv12 import SEGMENTS_15  # noqa: E402

BASE = "capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남"
TOL_FLOOR = 0.20
K_TOL = 3.0


def _load(f, hand):
    by = {}
    with io.open(f, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("Hand") or "").strip() != hand:
                continue
            try:
                fid = int(float(r["Frame_ID"])); lid = int(float(r["Landmark_ID"]))
            except (KeyError, TypeError, ValueError):
                continue
            try:
                by.setdefault(fid, {})[lid] = (float(r["MP_X_m"]), float(r["MP_Y_m"]), float(r["MP_Z_m"]))
            except (TypeError, ValueError):
                pass
    if len(by) < 20:
        return None
    fids = sorted(by)
    P = np.full((len(fids), 21, 3), np.nan)
    for i, fid in enumerate(fids):
        for lid, xyz in by[fid].items():
            P[i, lid] = xyz
    return P


def analyse(P):
    n = P.shape[0]
    out = {}
    for tag, base_sel in (("win", np.arange(n) < max(8, int(0.15 * n))), ("global", None)):
        rel, tol = {}, {}
        for seg in SEGMENTS_15:
            i, j = seg
            d = np.linalg.norm(P[:, i] - P[:, j], axis=-1)
            b = float(np.nanmedian(d if base_sel is None else d[base_sel]))
            if not np.isfinite(b) or b <= 0:
                continue
            r = np.abs(d - b) / b
            mad = float(np.nanmedian(np.abs(d - np.nanmedian(d))) / b)
            rel[seg] = r
            tol[seg] = max(TOL_FLOOR, K_TOL * mad)
        if not rel:
            continue
        frames = np.isfinite(list(rel.values())).all(axis=0)
        for tolname in ("fixed20", "per_seg"):
            t = np.full(P.shape[0], TOL_FLOOR) if tolname == "fixed20" else np.array([tol[s] for s in rel])
            bad = np.zeros((len(rel), P.shape[0]), bool)
            for k, s in enumerate(rel):
                bad[k] = np.isfinite(rel[s]) & (rel[s] > t[k])
            cnt = bad.sum(axis=0)
            for kmin in (1, 2, 3):
                rate = float(np.nanmean((cnt >= kmin) & frames)) if frames.any() else None
                out["%s_%s_k%d" % (tag, tolname, kmin)] = rate
    return out


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(BASE, "split", "*", "Trial_*", "*_landmarks.csv"))):
        for hand in ("Left", "Right"):
            P = _load(f, hand)
            if P is None:
                continue
            a = analyse(P)
            if a:
                a.update(trial=os.path.basename(os.path.dirname(f)), hand=hand, n=int(P.shape[0]))
                rows.append(a)
    keys = [k for k in rows[0] if k.startswith(("win_", "global_"))]
    summary = {}
    for k in keys:
        v = [r[k] for r in rows if r.get(k) is not None]
        summary[k] = {"median": round(float(np.median(v)), 3),
                      "min": round(float(min(v)), 3), "max": round(float(max(v)), 3)} if v else None
    res = {"provenance": {"session": os.path.basename(BASE), "n_records": len(rows),
                          "tol_floor": TOL_FLOOR, "k_tol": K_TOL,
                          "note": "비장애인 파일럿. ARAT 점수·VLM 출력 미사용.",
                          "baseline_note": "파일럿에는 §6.3.1 정지 2초가 없어 '앞 15% 창'과 '전체 중앙값'을 병기"},
           "per_record": rows, "summary": summary}
    io.open("experiments/results/v13_segment_rule_options.json", "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=2))

    print("프레임 기준 분절 불일치율 (중앙값 / 범위)  n=%d레코드" % len(rows))
    print("%-28s %8s %8s %8s" % ("조합", "중앙", "최소", "최대"))
    for k in keys:
        s = summary[k]
        if s:
            print("%-28s %8.3f %8.3f %8.3f" % (k, s["median"], s["min"], s["max"]))
    print()
    print("→ v13 후보: per_seg_k2 (분절별 허용오차 + 2개 이상 동시 위반)")
    for tag in ("win", "global"):
        s = summary.get("%s_per_seg_k2" % tag)
        if s:
            print("   %s_per_seg_k2 중앙 %.3f (기존 %s_fixed20_k1 중앙 %.3f)" % (
                tag, s["median"], tag, summary["%s_fixed20_k1" % tag]["median"]))


if __name__ == "__main__":
    sys.path.insert(0, "experiments/v12")
    main()

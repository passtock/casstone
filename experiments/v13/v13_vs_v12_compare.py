# -*- coding: utf-8 -*-
"""v12 규칙 vs v13 규칙 정량 비교 (같은 파일럿, 같은 전처리).

비교 대상
  R-v12   : 고정 tol=0.20, "1개 이상" 분절 위반        (v12 §8.2)
  R-v13f  : tol=0.20(개발군 미측정 → 하한), "2개 이상"  (v13 §8.2, 파일럿 실제 적용 가능한 상태)
  R-v13c  : tol_seg=max(0.20, 3×MAD_seg), "2개 이상"   (자기보정 **시뮬레이션** — 실제 개발군 아님)

기준선: 두 가지를 병기한다.
  · win    : 앞 2초 (진단용 대체 — 파일럿에는 §6.3.1 정지구간이 없다)
  · global : 전체 중앙값

주의: 개발군이 없으므로 R-v13c 는 "파일럿을 개발군으로 가정한" 자기보정이며 **확정값이 아니다**.
      ARAT 점수·VLM 출력은 사용하지 않았다.
"""
from __future__ import annotations

import glob, io, json, os, statistics, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from qv13 import (  # noqa: E402
    HAND_ALL_SEGS, TOL_FLOOR, K_TOL, MIN_SEG_AGREE, CAP_DEFAULT, CAP_PERCENTILE,
    _load_hand, _flat_tols, segment_frame_flags, segment_tolerances, calibrate_cap, session_dt_ref,
)

BASE = "capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남"


def seg_rate_windows(P, t, tol_map, rest_kind, min_agree):
    """두 기준선에서의 프레임 불일치율."""
    out = {}
    n = P.shape[0]
    rest_win = (np.arange(n) < max(8, int(round(2.0 / max(np.median(np.diff(t)), 1e-9)))))
    for tag, rest in (("win", rest_win), ("global", None)):
        if tag == "global":
            r = segment_frame_flags(P, t, tol_map, segments=HAND_ALL_SEGS, rest=None,
                                    min_agree=min_agree)
            # global 기준선 강제: rest=None 은 앞 2초를 쓰므로, 전체 중앙값 기준을 따로 계산
            r = _with_baseline(P, t, tol_map, "global", min_agree)
        else:
            r = _with_baseline(P, t, tol_map, "win", min_agree)
        out[tag] = (r["flags"].sum() / max(r["denom_frames"], 1)) if r["denom_frames"] else None
    return out


def _with_baseline(P, t, tol_map, kind, min_agree):
    """기준선을 '앞 2초' 또는 '전체 중앙값'으로 강제해 프레임 판정을 계산."""
    import qv13
    n = P.shape[0]
    if kind == "win":
        k = max(8, int(round(2.0 / max(np.median(np.diff(t)), 1e-9))))
        rest = np.zeros(n, bool); rest[:min(k, n)] = True
    else:
        rest = np.ones(n, bool)
    # qv13.segment_frame_flags 는 rest 마스크 안에서 '중앙값'을 기준으로 쓰므로,
    # rest=전체 를 주면 전체 중앙값 기준이 된다.
    return qv13.segment_frame_flags(P, t, tol_map, segments=HAND_ALL_SEGS, rest=rest,
                                    min_agree=min_agree)


def main():
    trials = []
    for f in sorted(glob.glob(os.path.join(BASE, "split", "*", "Trial_*", "*_landmarks.csv"))):
        for hand in ("Left", "Right"):
            r = _load_hand(f, hand)
            if r:
                trials.append((os.path.basename(os.path.dirname(f)), hand, r[0], r[1], r[2]))

    # 자기보정 시뮬레이션: 파일럿 전체를 개발군으로 가정
    sim = segment_tolerances([P for _, _, _, _, P in trials])
    flat = _flat_tols()

    rows = []
    for trial, hand, fid, t, P in trials:
        a = seg_rate_windows(P, t, flat, "win", 1)       # R-v12
        b = seg_rate_windows(P, t, flat, "win", 2)       # R-v13f
        c = seg_rate_windows(P, t, sim, "win", 2)        # R-v13c
        d = seg_rate_windows(P, t, flat, "global", 1)
        e = seg_rate_windows(P, t, flat, "global", 2)
        f_ = seg_rate_windows(P, t, sim, "global", 2)
        rows.append({"trial": trial, "hand": hand, "n": int(P.shape[0]),
                     "v12_win": a["win"], "v13f_win": b["win"], "v13c_win": c["win"],
                     "v12_global": d["global"], "v13f_global": e["global"],
                     "v13c_global": f_["global"]})

    def med(k):
        v = [r[k] for r in rows if r[k] is not None]
        return (round(statistics.median(v), 3), round(min(v), 3), round(max(v), 3)) if v else None

    dev_rates_win = [r["v13f_win"] for r in rows if r["v13f_win"] is not None]
    cap_sim = calibrate_cap(dev_rates_win)
    out = {
        "provenance": {"session": os.path.basename(BASE), "n_records": len(rows),
                       "tol_floor": TOL_FLOOR, "K_tol": K_TOL, "min_seg_agree": MIN_SEG_AGREE,
                       "note": "비장애인 파일럿. R-v13c 는 파일럿 자기보정 시뮬레이션(확정값 아님). "
                               "ARAT 점수·VLM 출력 미사용."},
        "tol_simulation": {str(k): v for k, v in sim.items()},
        "cap_simulation": cap_sim,
        "rate_median_min_max": {k: med(k) for k in
                                ("v12_win", "v13f_win", "v13c_win",
                                 "v12_global", "v13f_global", "v13c_global")},
        "improvement": {},
        "n_trials": len(rows),
        "per_record": rows,
    }
    for tag in ("win", "global"):
        a, b, c = (out["rate_median_min_max"]["v12_%s" % tag][0],
                   out["rate_median_min_max"]["v13f_%s" % tag][0],
                   out["rate_median_min_max"]["v13c_%s" % tag][0])
        out["improvement"][tag] = {
            "v12": a, "v13_floor": b, "v13_calibrated_sim": c,
            "reduction_v13floor_pct": round(100 * (a - b) / a, 1) if a else None,
            "reduction_v13cal_pct": round(100 * (a - c) / a, 1) if a else None,
        }
    io.open("experiments/results/v13_vs_v12_rule_comparison.json", "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=2))

    print("프레임 분절 불일치율 — 중앙값 (최소~최대)   n=%d레코드" % len(rows))
    print("%-34s %-22s %-22s" % ("규칙", "앞 2초 기준선", "전체 중앙값 기준선"))
    lbl = [("v12_", "R-v12  고정20% + 1개(v12 §8.2)"),
           ("v13f_", "R-v13f 20%(하한) + 2개"),
           ("v13c_", "R-v13c 분절별tol + 2개(자기보정)")]
    for pre, name in lbl:
        w, g = med(pre + "win"), med(pre + "global")
        print("%-34s %-22s %-22s" % (name, "%.3f (%.2f~%.2f)" % w, "%.3f (%.2f~%.2f)" % g))
    print()
    print("감소율(중앙값 기준):")
    for tag in ("win", "global"):
        i = out["improvement"][tag]
        print("  %-7s v12 %.3f → v13f %.3f (−%.1f%%) → v13c %.3f (−%.1f%%)" % (
            tag, i["v12"], i["v13_floor"], i["reduction_v13floor_pct"] or 0,
            i["v13_calibrated_sim"], i["reduction_v13cal_pct"] or 0))
    print()
    print("자기보정 시뮬레이션 tol_seg (엄지·검지 6):",
          {str(k): round(v["tol"], 3) for k, v in sim.items() if k in
           [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8)]})
    print("자기보정 시뮬레이션 상한 = %.3f (개발군 90백분위, n=%d)" % (cap_sim["cap"], cap_sim["n"]))


if __name__ == "__main__":
    sys.path.insert(0, "experiments/v13")
    main()

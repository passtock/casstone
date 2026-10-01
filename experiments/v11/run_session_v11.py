# -*- coding: utf-8 -*-
"""v11 — 세션 단위 실행 러너 (시행 폴더 순회 → L2 지표 + 구/신 Q 감사).

기존 코드를 수정하지 않고 v10 지표 정의 + v11 Q/Pose를 세션 전체에 적용한다.

실행:
  python experiments/v11/run_session_v11.py --session "<session dir>" \
      --pose "<session>/pose_landmarks.csv" --out summary.json
  # Pose가 없으면 pose_offline.py 로 먼저 만든다:
  python experiments/v11/pose_offline.py --video <session>/original.avi \
      --timestamps <session>/video_timestamps.csv --out <session>/pose_landmarks.csv
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import traceback

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "v10"))

import qrobust  # noqa: E402
from l2_metrics_v11 import process_trial_v11  # noqa: E402
from l2_metrics_v10 import load_landmarks_csv, WRIST  # noqa: E402


def find_trials(session_dir):
    pats = [os.path.join(session_dir, "split", "*", "Trial_*", "*_landmarks.csv"),
            os.path.join(session_dir, "**", "Trial_*", "*_landmarks.csv")]
    out = []
    for p in pats:
        out.extend(glob.glob(p, recursive=True))
    return sorted(set(out))


def run(session_dir, pose_path=None, td_mode="lean", anterior_axis=None, baseline_s=2.0,
        hands=("Left", "Right"), max_trials=None):
    files = find_trials(session_dir)
    if max_trials:
        files = files[:max_trials]
    rows = []
    for f in files:
        trial = os.path.basename(os.path.dirname(f))
        for hand in hands:
            rec = {"trial": trial, "hand": hand}
            try:
                r = process_trial_v11(f, hand=hand, pose_path=pose_path,
                                      anterior_axis=anterior_axis, baseline_s=baseline_s,
                                      td_mode=td_mode)
                m = r["metrics"]
                rec.update({
                    "mga_mm": m["M1_mga_mm"]["value"], "tam_deg": m["M2_tam_total_deg"]["value"],
                    "sparc": m["M4_sparc"]["value"], "sparc_src": m["M4_sparc"]["extra"]["source"],
                    "sparc_reason": m["M4_sparc"]["extra"]["reason"],
                    "td_mm": m["M5_td_mm"]["value"], "td_mode": m["M5_td_mm"]["extra"]["td_mode"],
                    "td_reason": m["M5_td_mm"]["extra"]["reason"],
                    "td_lean_mm": m["M5_td_mm"]["extra"]["TD_lean_mm"],
                    "q_hand": r["q"]["hand"]["pass"], "q_hand_reasons": r["q"]["hand"]["reasons"],
                    "q_wrist": r["q"]["wrist"]["pass"], "q_wrist_reasons": r["q"]["wrist"]["reasons"],
                    "q_trunk": r["q"]["trunk"]["pass"], "q_trunk_reasons": r["q"]["trunk"]["reasons"],
                    "fps_effective": r["fps_effective"], "median_dt_s": r["median_dt_s"],
                    "max_gap_ratio": r["q"]["wrist"]["max_gap_ratio"],
                    "missing_frac": r["q"]["wrist"]["missing_frac"],
                })
                # 구(v10 절대초) 규칙과의 대조
                hd = load_landmarks_csv(f, hand=hand)
                au = qrobust.audit_record(hd["t"])
                rec["q_wrist_old_pass"] = None if au is None else au["old_pass"]
                rec["old_ifr_v10"] = None if au is None else au["ifr_v10"]
                rec["old_max_dt_s"] = None if au is None else au["max_dt_s"]
            except Exception as e:  # noqa: BLE001
                rec["error"] = "%s: %s" % (type(e).__name__, e)
                rec["trace"] = traceback.format_exc()[-400:]
            rows.append(rec)

    ok = [r for r in rows if "error" not in r]
    summary = {
        "session": os.path.basename(session_dir), "n_files": len(files), "n_records": len(rows),
        "pose_used": pose_path, "td_mode": td_mode, "anterior_axis": anterior_axis,
        "aggregate": {
            "n_ok": len(ok),
            "td_non_null": sum(1 for r in ok if r["td_mm"] is not None),
            "sparc_non_null": sum(1 for r in ok if r["sparc"] is not None),
            "q_hand_pass": sum(1 for r in ok if r["q_hand"]),
            "q_wrist_pass_new": sum(1 for r in ok if r["q_wrist"]),
            "q_wrist_pass_old_v10": sum(1 for r in ok if r.get("q_wrist_old_pass") is True),
            "q_trunk_pass": sum(1 for r in ok if r["q_trunk"]),
            "fps_effective_range": [_rng([r["fps_effective"] for r in ok]),
                                    None] if ok else None,
        },
        "records": rows,
    }
    vals = [r["fps_effective"] for r in ok if r["fps_effective"]]
    summary["aggregate"]["fps_min"] = min(vals) if vals else None
    summary["aggregate"]["fps_max"] = max(vals) if vals else None
    for k in ("mga_mm", "tam_deg", "sparc", "td_mm", "td_lean_mm"):
        v = [r[k] for r in ok if r.get(k) is not None]
        summary["aggregate"][k + "_range"] = ([min(v), max(v)] if v else None)
    # Wrist Q 사유 집계
    from collections import Counter
    c = Counter()
    for r in ok:
        for reason in r.get("q_wrist_reasons", []):
            c[reason] += 1
    summary["aggregate"]["q_wrist_new_reasons"] = dict(c)
    return summary


def _rng(xs):
    return [min(xs), max(xs)] if xs else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="v11 세션 러너")
    ap.add_argument("--session", required=True)
    ap.add_argument("--pose", default=None)
    ap.add_argument("--td-mode", default="lean", choices=["lean", "forward"])
    ap.add_argument("--anterior-axis", default=None)
    ap.add_argument("--baseline-s", type=float, default=2.0)
    ap.add_argument("--hands", default="Left,Right")
    ap.add_argument("--max-trials", type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    axis = [float(x) for x in a.anterior_axis.split(",")] if a.anterior_axis else None
    pose = a.pose
    if pose is None:
        cand = os.path.join(a.session, "pose_landmarks.csv")
        pose = cand if os.path.exists(cand) else None
    res = run(a.session, pose_path=pose, td_mode=a.td_mode, anterior_axis=axis,
              baseline_s=a.baseline_s, hands=tuple(a.hands.split(",")), max_trials=a.max_trials)
    txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(txt)
        print("wrote %s" % a.out)
    print(json.dumps(res["aggregate"], ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

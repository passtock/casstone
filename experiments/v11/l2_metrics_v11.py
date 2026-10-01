# -*- coding: utf-8 -*-
"""v11 — v10 지표 정의 + 프레임레이트 견고 Q + Pose 기반 체간 (기존 코드 미수정).

기존 모듈을 **import 해서 재사용**하고, v10에서 막혔던 두 지점만 새로 구현한다.

  · M1(MGA) · M2(추정 TAM_total) · M4(SPARC) 계산      → `experiments/v10/l2_metrics_v10.py` 재사용
  · M5(TD) 체간                                        → v11에서 두 정의로 구현
        - `TD_lean`    : **축 불필요**. 골반 기준 상체 수평 변위의 최대 (mm)
        - `TD_forward` : v10 정의. 탁자 전방축 필요
  · Q                                                  → `experiments/v11/qrobust.py` (프레임레이트 무관)
  · Pose 입력                                          → `experiments/v11/pose_offline.py` 출력

## 왜 TD를 두 가지로 두는가
MediaPipe Pose world landmark의 원점은 **골반 중점**이다(실측 확인: hips mid ≈ 0).
따라서 world landmark로는 **전역 이동(의자 기준 앞으로 나감)** 이 지워지고,
**골반 기준 상체의 기울기**만 남는다.
  · ARAT 채점 정본은 "몸통이 등받이에서 **완전히 떨어짐**"을 2점 사유로 든다
    = 등받이 접촉 상실 = **상체가 골반 수직축에서 벗어남** → `TD_lean`이 직접 대응한다.
  · 전역 이동량이 필요하면 원시 depth + 내부파라미터로 RS_* 를 만들어 `TD_forward`를 쓴다.
두 값을 모두 내고 `td_mode`로 어느 쪽을 쓸지 표시한다.

실행:
  python experiments/v11/l2_metrics_v11.py --selftest
  python experiments/v11/l2_metrics_v11.py --landmarks <trial>_landmarks.csv --hand Right \
      --pose <session>/pose_landmarks.csv --out l2.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "v10"))
sys.path.insert(0, _HERE)

import qrobust  # noqa: E402
from l2_metrics_v10 import (  # noqa: E402   (기존 코드 재사용 — 수정하지 않음)
    WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP,
    compute_mga, compute_tam_total, compute_sparc, compute_td,
    load_landmarks_csv, load_pose_csv,
)
from pose_offline import POSE_L_SHOULDER, POSE_R_SHOULDER, POSE_L_WRIST, POSE_R_WRIST, \
    POSE_L_HIP, POSE_R_HIP  # noqa: E402


# =====================================================================
# 1. 체간: 두 정의
# =====================================================================
def compute_td_lean(t, shoulder_mid, hip_mid, baseline_s=2.0):
    """TD_lean (축 불필요): 골반 기준 상체 수평 변위의 구간 최대. (mm)

    = max_t( ||horizontal(P_shoulder_mid(t) − P_hip_mid(t))|| ) − 기준선
    등받이 접촉 상실(상체가 수직축에서 벗어남)에 직접 대응한다.
    """
    out = {"value": None, "unit": "mm", "reason": None, "baseline_mm": None,
           "baseline_sd_mm": None, "n_frames": 0, "series": None, "needs_axis": False}
    t = np.asarray(t, float)
    sm = np.asarray(shoulder_mid, float)
    hm = np.asarray(hip_mid, float)
    if sm.shape != hm.shape or sm.ndim != 2 or sm.shape[1] != 3:
        out["reason"] = "shape_mismatch"
        return out
    ok = np.isfinite(t) & np.isfinite(sm).all(axis=1) & np.isfinite(hm).all(axis=1)
    if ok.sum() < 5:
        out["reason"] = "insufficient_trunk_frames"
        return out
    t, sm, hm = t[ok], sm[ok], hm[ok]
    order = np.argsort(t, kind="stable")
    t, sm, hm = t[order], sm[order], hm[order]
    d = sm - hm
    # ⚠️ MediaPipe Pose world landmark: x=오른쪽, y=아래(수직), z=깊이.
    #    수평면은 (x, z)다. (x, y)를 쓰면 견장(수직) 성분이 섞인다.
    horiz = np.linalg.norm(d[:, [0, 2]], axis=1)
    base_sel = t <= (t[0] + baseline_s)
    if base_sel.sum() < 3:
        base_sel = np.zeros_like(t, dtype=bool)
        base_sel[:3] = True
    base = float(np.median(horiz[base_sel]))
    out.update({"value": float(np.max(horiz - base)) * 1000.0, "baseline_mm": base * 1000.0,
                "baseline_sd_mm": float(np.std(horiz[base_sel])) * 1000.0,
                "n_frames": int(t.size), "series": horiz - base, "reason": "ok"})
    return out


# =====================================================================
# 2. 시행 처리
# =====================================================================
def load_pose_by_frame(path, coord="MP"):
    """Pose CSV → Frame_ID 로 조회 가능한 배열.  (v10 load_pose_csv 는 fid 를 버리므로 v11에서 별도 파싱)

    반환: {"t","pos","valid","fid2row","n"}
    """
    cols = ("RS_X_m", "RS_Y_m", "RS_Z_m") if coord == "RS" else ("MP_X_m", "MP_Y_m", "MP_Z_m")
    by_frame = {}
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                fid = int(float(r.get("Frame_ID", r.get("frame_id", 0))))
                lid = int(float(r["Landmark_ID"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not (0 <= lid <= 32):
                continue
            by_frame.setdefault(fid, {})[lid] = r
    fids = sorted(by_frame)
    n = len(fids)
    t = np.full(n, np.nan)
    pos = np.full((n, 33, 3), np.nan)
    vis = np.full((n, 33), np.nan)
    for i, fid in enumerate(fids):
        for lid, r in by_frame[fid].items():
            pos[i, lid] = (_num(r.get(cols[0])), _num(r.get(cols[1])), _num(r.get(cols[2])))
            v = _num(r.get("visibility", r.get("Visibility")))
            vis[i, lid] = 1.0 if not np.isfinite(v) else v
        ts = by_frame[fid].get(POSE_L_SHOULDER, {}).get("time_s")
        tv = _num(ts)
        if np.isfinite(tv):
            t[i] = tv
    if not np.isfinite(t).any():
        t = np.arange(n, dtype=float)
    valid = np.isfinite(pos).all(axis=2) & (vis >= 0.5)
    return {"t": t, "pos": pos, "valid": valid, "fid2row": {f: i for i, f in enumerate(fids)}, "n": n}


def _num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _align_pose_to_frames(pose, frame_ids):
    """시행의 Frame_ID 목록에 Pose를 **Frame_ID 로** 맞춘다.

    반환: 압축된 (t, pos, valid) + 커버리지 정보. 매칭 안 된 프레임은 제외한다
    (시계열과 좌표를 같은 길이로 유지해 Q/지표 계산이 어긋나지 않게 한다).
    """
    if pose is None:
        return None
    want = np.asarray(frame_ids, int)
    m = pose["fid2row"]
    idx = np.array([m.get(int(f), -1) for f in want], dtype=int)
    hit = idx >= 0
    coverage = float(hit.mean()) if hit.size else 0.0
    if coverage < 0.5:
        # Frame_ID 매칭 실패 → 순서 정렬 폴백(경고 플래그)
        n = min(pose["n"], len(want))
        return {"t": pose["t"][:n], "pos": pose["pos"][:n], "valid": pose["valid"][:n],
                "aligned": False, "coverage": coverage, "mode": "index_fallback",
                "n_pose": pose["n"], "n_frame_ids": int(len(want))}
    sel = idx[hit]
    return {"t": pose["t"][sel], "pos": pose["pos"][sel], "valid": pose["valid"][sel],
            "aligned": True, "coverage": coverage, "mode": "frame_id",
            "n_pose": pose["n"], "n_frame_ids": int(len(want)), "n_matched": int(hit.sum())}


def process_trial_v11(landmarks_path, hand=None, pose_path=None, anterior_axis=None,
                      baseline_s=2.0, td_mode="lean", q=None, sparc_dt_mode="median"):
    hand_d = load_landmarks_csv(landmarks_path, hand=hand)
    m1 = compute_mga(hand_d["pos"])
    m2 = compute_tam_total(hand_d["pos"])

    pose_raw = load_pose_by_frame(pose_path, coord="MP") if pose_path else None
    pose = _align_pose_to_frames(pose_raw, hand_d["frame_ids"]) if pose_raw is not None else None

    # ---- M4: 손목 경로(Hands와 분리) ----
    wrist_src, wt, wpos = "hands_wrist", hand_d["t"], hand_d["pos"][:, WRIST]
    if pose is not None:
        wl = POSE_R_WRIST if str(hand_d["hand"]).upper().startswith("R") else POSE_L_WRIST
        if np.isfinite(pose["pos"][:, wl]).any():
            wrist_src, wt, wpos = "pose_wrist", pose["t"], pose["pos"][:, wl]
    m4 = compute_sparc(wt, wpos, dt_mode=sparc_dt_mode)
    m4["source"] = wrist_src

    # ---- M5: 체간 (두 정의) ----
    td_lean = {"value": None, "reason": "no_pose", "baseline_mm": None, "baseline_sd_mm": None,
               "n_frames": 0}
    td_fwd = {"value": None, "reason": "no_pose", "baseline_sd_mm": None, "n_frames": 0}
    trunk_q = None
    if pose is not None:
        sm = 0.5 * (pose["pos"][:, POSE_L_SHOULDER] + pose["pos"][:, POSE_R_SHOULDER])
        hm = 0.5 * (pose["pos"][:, POSE_L_HIP] + pose["pos"][:, POSE_R_HIP])
        both = (np.isfinite(pose["pos"][:, POSE_L_SHOULDER]).all(axis=1)
                & np.isfinite(pose["pos"][:, POSE_R_SHOULDER]).all(axis=1))
        both_h = (np.isfinite(pose["pos"][:, POSE_L_HIP]).all(axis=1)
                  & np.isfinite(pose["pos"][:, POSE_R_HIP]).all(axis=1))
        vis_ok = (pose["valid"][:, POSE_L_SHOULDER] & pose["valid"][:, POSE_R_SHOULDER]
                  & pose["valid"][:, POSE_L_HIP] & pose["valid"][:, POSE_R_HIP])
        sel = both & both_h
        td_lean = compute_td_lean(pose["t"][sel], sm[sel], hm[sel], baseline_s=baseline_s)
        td_lean["valid_ratio"] = float(vis_ok.mean()) if vis_ok.size else 0.0
        td_fwd = compute_td(pose["t"][sel], sm[sel], anterior_axis if anterior_axis else None,
                            baseline_s=baseline_s)
        trunk_q = qrobust.q_trunk_robust(pose["t"], vis_ok, sm, hm, q=q, baseline_s=baseline_s)

    td = td_lean if td_mode == "lean" else td_fwd
    if td_mode == "forward" and not anterior_axis:
        td = {"value": None, "reason": "no_anterior_axis", "baseline_sd_mm": None, "n_frames": 0}

    # ---- Q (프레임레이트 견고) ----
    finite_hand = (np.isfinite(hand_d["pos"][:, THUMB_TIP, 0]) & np.isfinite(hand_d["pos"][:, INDEX_TIP, 0]))
    seg = np.linalg.norm(hand_d["pos"][:, WRIST] - hand_d["pos"][:, MIDDLE_MCP], axis=-1)
    q_hand = qrobust.q_hand_robust(hand_d["t"], finite_hand, seg, q=q, baseline_s=baseline_s)
    wrist_valid = np.isfinite(wpos).all(axis=1) if wpos.ndim == 2 else np.isfinite(wpos).all(axis=-1)
    q_wrist = qrobust.q_wrist_robust(wt, wrist_valid, pos=wpos, q=q, baseline_s=baseline_s)
    q_wrist["source"] = wrist_src
    if trunk_q is None:
        trunk_q = {"pass": False, "reasons": ["no_pose"], "valid_ratio": None, "baseline_sd_mm": None}

    metrics = {
        "M1_mga_mm": {"value": m1["value"], "unit": "mm", "q_pass": q_hand["pass"],
                      "extra": {"p95_secondary": m1["p95_secondary"], "n_over_150mm": m1["n_over_150mm"],
                                "capped": False}},
        "M2_tam_total_deg": {"value": m2["value"], "unit": "deg", "q_pass": q_hand["pass"],
                             "extra": {"n_frames_complete": m2["n_frames_complete"], "n_angles": 14}},
        "M4_sparc": {"value": m4["value"], "unit": "1", "q_pass": q_wrist["pass"],
                     "extra": {"source": m4["source"], "reason": m4["reason"], "fs": m4["fs"],
                               "n_speed_samples": m4["n_speed_samples"], "dt_mode": sparc_dt_mode}},
        "M5_td_mm": {"value": td.get("value"), "unit": "mm", "q_pass": trunk_q["pass"],
                     "extra": {"td_mode": td_mode, "reason": td.get("reason"),
                               "baseline_sd_mm": td.get("baseline_sd_mm"),
                               "n_frames": td.get("n_frames"),
                               "TD_lean_mm": td_lean.get("value"), "TD_forward_mm": td_fwd.get("value"),
                               "anterior_axis": list(anterior_axis) if anterior_axis else None}},
    }
    fps_rep = q_wrist
    return {
        "input": {"landmarks": os.path.basename(landmarks_path), "hand": hand_d["hand"],
                  "n_frames": int(hand_d["pos"].shape[0]),
                  "pose_aligned": None if pose is None else pose["aligned"],
                  "pose_align_mode": None if pose is None else pose.get("mode"),
                  "pose_coverage": None if pose is None else round(pose.get("coverage", 0.0), 4),
                  "n_pose_frames": None if pose is None else pose["n_pose"]},
        "metrics": metrics, "q": {"hand": q_hand, "wrist": q_wrist, "trunk": trunk_q},
        "fps_effective": fps_rep.get("fps_effective"), "median_dt_s": fps_rep.get("median_dt_s"),
        "sparc_series": m4.get("series"),
    }


# =====================================================================
# 3. 오라클
# =====================================================================
def _synth_pose_lean(path, F=200, fps=13.4, lean_mm=35.0, wrist_amp_m=0.10, hand="Right"):
    """골반 고정 + 상체가 정지 2초 후 전방(z)으로 lean_mm 만큼 기우는 합성 Pose.

    hips 23/24 = (0,0,0)  /  shoulders 11/12 = (±0.15, −0.30, −lean(t))
      → shoulder_mid − hip_mid = (0, −0.30, −lean)  → 수평성분 = |lean|
    """
    t = np.arange(F) / fps
    ramp = (lean_mm / 1000.0) * np.clip((t - 2.0) / 1.0, 0.0, 1.0)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Frame_ID", "time_s", "Landmark_ID", "visibility",
                    "MP_X_m", "MP_Y_m", "MP_Z_m", "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Status"])
        for i in range(F):
            for j in range(33):
                if j in (POSE_L_HIP, POSE_R_HIP):
                    x, y, z = (0.08 if j == POSE_L_HIP else -0.08), 0.0, 0.0
                elif j in (POSE_L_SHOULDER, POSE_R_SHOULDER):
                    x = 0.15 if j == POSE_L_SHOULDER else -0.15
                    y, z = -0.30, -ramp[i]
                elif j in (POSE_L_WRIST, POSE_R_WRIST):
                    mv = 0.05 * math.sin(2 * math.pi * 1.2 * (t[i] - 2.0)) if t[i] > 2.0 else 0.0
                    x, y, z = mv, 0.25, -0.25
                else:
                    x, y, z = 0.0, -0.1, -0.1
                w.writerow([i, "%.6f" % t[i], j, 0.95,
                            "%.6f" % x, "%.6f" % y, "%.6f" % z, "", "", "", "no_depth"])
    return t


def selftest():
    import tempfile
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    sys.path.insert(0, os.path.join(_HERE, "..", "v10"))
    from l2_metrics_v10 import _synth_hand_csv

    tmp = tempfile.mkdtemp(prefix="v11_l2_")
    lm13 = os.path.join(tmp, "h13_landmarks.csv")
    _synth_hand_csv(lm13, F=200, fps=13.4, amp_mm=80.0, hand="Right")
    pose = os.path.join(tmp, "p13.csv")
    _synth_pose_lean(pose, F=200, fps=13.4, lean_mm=35.0)

    r = process_trial_v11(lm13, hand="Right", pose_path=pose, td_mode="lean")

    # --- M1/M2는 v10과 동일해야 한다 ---
    chk("M1 ≈ 80 mm (v10 재사용, 샘플링 오차 허용)", abs(r["metrics"]["M1_mga_mm"]["value"] - 80.0) < 0.2,
        "%.4f" % r["metrics"]["M1_mga_mm"]["value"])
    chk("M2 완전신전 = 0 deg", abs(r["metrics"]["M2_tam_total_deg"]["value"]) < 1e-9)

    # --- M4: Pose 손목 우선 ---
    chk("M4 source = pose_wrist (Pose 있음)", r["metrics"]["M4_sparc"]["extra"]["source"] == "pose_wrist",
        r["metrics"]["M4_sparc"]["extra"]["source"])
    chk("M4 유한 SPARC ≤ 0", r["metrics"]["M4_sparc"]["value"] is not None
        and r["metrics"]["M4_sparc"]["value"] <= 0, str(r["metrics"]["M4_sparc"]["value"]))

    # --- ★ M5: 축 없이 lean 이 나온다 (P1 핵심) ---
    chk("★ TD_lean 이 축 없이 산출", r["metrics"]["M5_td_mm"]["extra"]["TD_lean_mm"] is not None,
        str(r["metrics"]["M5_td_mm"]["extra"]["TD_lean_mm"]))
    _td = r["metrics"]["M5_td_mm"]["value"]
    chk("★ TD_lean ≈ 35 mm", _td is not None and abs(_td - 35.0) < 0.5, "%.3f mm" % (_td if _td is not None else -1))
    chk("★ TD_lean 은 anterior_axis 불필요 표시",
        r["metrics"]["M5_td_mm"]["extra"]["anterior_axis"] is None)

    # --- ★ Q: 13.4 fps 에서 결측 없으면 통과 (P2 핵심) ---
    chk("★ Q 손 통과 @13.4fps", r["q"]["hand"]["pass"] is True, str(r["q"]["hand"]["reasons"]))
    chk("★ Q 손목 통과 @13.4fps (구규칙은 탈락)",
        r["q"]["wrist"]["pass"] is True, str(r["q"]["wrist"]["reasons"]) + " %s" % r["q"]["wrist"]["max_gap_ratio"])
    chk("★ Q 체간 통과 @13.4fps", r["q"]["trunk"]["pass"] is True, str(r["q"]["trunk"]["reasons"]))
    chk("fps_effective 보고", r["fps_effective"] is not None and 12 < r["fps_effective"] < 15,
        "%.2f" % (r["fps_effective"] or -1))

    # --- 구규칙(절대 초) 대조: jitter 있는 13.4fps 에서 구규칙은 탈락, 신규칙은 통과 ---
    t_j = qrobust._synth_times(13.4, 15.0, seed=1)
    au = qrobust.audit_record(t_j)
    chk("★ 구규칙은 13.4fps 에서 탈락(회귀 근거)", au is not None and au["old_pass"] is False,
        "" if au is None else "old_pass=%s max_dt=%.3f ifr=%.3f" % (au["old_pass"], au["max_dt_s"], au["ifr_v10"]))
    chk("★ 신규칙은 같은 조건에서 통과", qrobust.q_wrist_robust(t_j)["pass"] is True)

    # --- 30 fps 에서도 같은 판정 ---
    lm30 = os.path.join(tmp, "h30_landmarks.csv")
    _synth_hand_csv(lm30, F=450, fps=30.0, amp_mm=80.0, hand="Right")
    pose30 = os.path.join(tmp, "p30.csv")
    _synth_pose_lean(pose30, F=450, fps=30.0, lean_mm=35.0)
    r30 = process_trial_v11(lm30, hand="Right", pose_path=pose30, td_mode="lean")
    _td30 = r30["metrics"]["M5_td_mm"]["value"]
    chk("★ 30fps 에서도 TD_lean ≈ 35 mm", _td30 is not None and abs(_td30 - 35.0) < 0.5,
        "%.3f" % (_td30 if _td30 is not None else -1))
    chk("★ fps 간 Q 판정 일치", r["q"]["wrist"]["pass"] == r30["q"]["wrist"]["pass"])

    # --- Pose 없음: TD는 no_pose, 손목은 Hands 폴백 ---
    rn = process_trial_v11(lm13, hand="Right", pose_path=None)
    chk("Pose 없으면 TD 사유 no_pose", rn["metrics"]["M5_td_mm"]["extra"]["reason"] == "no_pose")
    chk("Pose 없으면 M4 source = hands_wrist",
        rn["metrics"]["M4_sparc"]["extra"]["source"] == "hands_wrist",
        rn["metrics"]["M4_sparc"]["extra"]["source"])

    # --- forward 모드: 축 없으면 no_anterior_axis, 축 주면 산출 ---
    rf = process_trial_v11(lm13, hand="Right", pose_path=pose, td_mode="forward")
    chk("forward 모드: 축 없으면 no_anterior_axis",
        rf["metrics"]["M5_td_mm"]["extra"]["reason"] == "no_anterior_axis",
        str(rf["metrics"]["M5_td_mm"]["extra"]["reason"]))
    rf2 = process_trial_v11(lm13, hand="Right", pose_path=pose, td_mode="forward",
                            anterior_axis=[0.0, 0.0, -1.0])
    _tdf = rf2["metrics"]["M5_td_mm"]["value"]
    chk("forward 모드: 축 주면 ≈ 35 mm", _tdf is not None and abs(_tdf - 35.0) < 0.5,
        "%.3f" % (_tdf if _tdf is not None else -1))
    chk("두 TD 정의가 같은 합성에서 일치",
        rf2["metrics"]["M5_td_mm"]["extra"]["TD_lean_mm"] is not None
        and abs(rf2["metrics"]["M5_td_mm"]["extra"]["TD_lean_mm"]
                - rf2["metrics"]["M5_td_mm"]["extra"]["TD_forward_mm"]) < 0.5)

    print("=" * 72)
    print("l2_metrics_v11 오라클")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="v11 L2 지표 (v10 정의 + 견고 Q + Pose 체간)")
    ap.add_argument("--landmarks")
    ap.add_argument("--hand", default=None)
    ap.add_argument("--pose", default=None)
    ap.add_argument("--anterior-axis", default=None, help="x,y,z")
    ap.add_argument("--td-mode", default="lean", choices=["lean", "forward"])
    ap.add_argument("--baseline-s", type=float, default=2.0)
    ap.add_argument("--sparc-dt-mode", default="median", choices=["median", "max_dt"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.landmarks:
        ap.error("--landmarks 또는 --selftest 필요")
    axis = [float(v) for v in a.anterior_axis.split(",")] if a.anterior_axis else None
    res = process_trial_v11(a.landmarks, hand=a.hand, pose_path=a.pose, anterior_axis=axis,
                            baseline_s=a.baseline_s, td_mode=a.td_mode, sparc_dt_mode=a.sparc_dt_mode)
    res.pop("sparc_series", None)
    txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(txt)
        print("wrote %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

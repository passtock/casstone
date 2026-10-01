# -*- coding: utf-8 -*-
"""v10 §7 지표 추출: M1(MGA) · M2(추정 TAM_total) · M4(SPARC) · M5(TD) + Q(§8.2).

계획서: capstone/실험계획서_v10_최종본.md  §7(추출 수치), §8(품질 규칙 Q)

설계 원칙(v10 명시 사항만 구현한다):
  · M1 = Hands world landmark 4–8 3D 거리의 **구간 최댓값** mm. **150 mm 상한으로 자르지 않는다**(§7.1).
    P95는 보조 저장만 한다.
  · M2 = 14개 기하학적 굴곡각 합의 **구간 P95**(deg). 각 = 180 − 내각(§7.1).
    엄지 2개(CMC–MCP–IP, MCP–IP–TIP) + 네 손가락 × (MCP,PIP,DIP) 3개 = 14.
  · M4 = **손목 3D 이동 속력**의 SPARC(무차원, ≤0). 손가락 검출 실패가 팔 지표를 죽이지 않도록
    손목 경로를 Hands와 **분리**한다(§7.2). 기본 소스는 Pose 손목(15/16)이며, 없으면 Hands wrist(0).
    장치 시간의 **중앙 간격**으로 균일 재표본화 → 3D 시간미분 → 속력(§7.2).
    `padlevel=4, fc=min(10, fs/2), amp_th=0.05` = 참조구현(sparc_ref.sparc) 고정.
  · M5 = Pose 양 어깨(11/12) 중점의 **탁자 전방 변위 최대** mm(§7.3).
    전방축은 **외부에서 주어져야 한다**(ArUco 탁자 좌표, §6.2). 없으면 TD=null + 사유 기록.
    중점 위치는 각 어깨를 depth 역투영해 얻는다(입력의 RS_* 가 그 결과).
  · Q(§8.2)는 **하드 결측과 분리**한다: 값은 있으나 규칙 실패 = 품질 미달(A3에서만 null).

한계(정직):
  · 독립 모션캡처 비교가 없으므로 **절대 정확도는 미검증**이다(§7.5).
  · TD는 어깨 중점 대리 지표이며 견갑·몸통 회전을 분리하지 못한다(§7.3).
  · Pose는 현재 촬영 앱에 **구현되어 있지 않다**. Pose 파일을 주지 않으면 M4는 Hands wrist로
    계산되고(소스 태그로 구분), M5는 null이다.

실행:
  python experiments/v10/l2_metrics_v10.py --selftest
  python experiments/v10/l2_metrics_v10.py --landmarks <trial>_landmarks.csv --hand R \
      --out out.json [--pose pose.csv] [--anterior-axis 1,0,0] [--baseline-s 2.0]
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
sys.path.insert(0, os.path.join(_HERE, "..", "metrics"))
try:
    from sparc_ref import sparc as _sparc  # 검증된 참조 구현 재사용
except Exception:  # pragma: no cover - 경로 문제 시 폴백
    _sparc = None

# ---- MediaPipe Hands 인덱스 ----
WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9

# ---- MediaPipe Pose 인덱스 ----
POSE_L_SHOULDER, POSE_R_SHOULDER = 11, 12
POSE_L_WRIST, POSE_R_WRIST = 15, 16

# ---- v10 §7.1: 14각 (엄지 2 + 네 손가락 × 3) ----
FINGER_JOINT_DEFS = {
    "Thumb_CMC": (0, 1, 2), "Thumb_MCP": (1, 2, 3),
    "Index_MCP": (0, 5, 6), "Index_PIP": (5, 6, 7), "Index_DIP": (6, 7, 8),
    "Middle_MCP": (0, 9, 10), "Middle_PIP": (9, 10, 11), "Middle_DIP": (10, 11, 12),
    "Ring_MCP": (0, 13, 14), "Ring_PIP": (13, 14, 15), "Ring_DIP": (14, 15, 16),
    "Pinky_MCP": (0, 17, 18), "Pinky_PIP": (17, 18, 19), "Pinky_DIP": (18, 19, 20),
}
N_TAM_ANGLES = len(FINGER_JOINT_DEFS)  # == 14

# ---- v10 §8.2 기본 Q 임계값 ----
Q_DEFAULTS = {
    "hand_track_ratio_min": 0.80,
    "hand_gap_max_s": 0.30,
    "hand_valid_frames_min": 8,
    "seg_len_dev_frac_max": 0.30,
    "seg_len_dev_tol": 0.20,
    "wrist_valid_ratio_min": 0.80,
    "wrist_speed_samples_min": 8,
    "wrist_gap_max_s": 0.10,
    "wrist_interp_frac_max": 0.10,
    "trunk_valid_ratio_min": 0.80,
    "trunk_baseline_sd_mm_max": 10.0,
    "trunk_occlusion_frac_max": 0.30,
    "trunk_visibility_min": 0.50,
}


# =====================================================================
# 1. 로딩
# =====================================================================
def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def load_landmarks_csv(path, hand=None, coord="MP"):
    """MediaPipe Hands landmarks.csv(롱포맷) → 프레임 인덱스 배열.

    반환 dict:
      frame_ids (F,) int
      t (F,) float   -- time_s
      pos (F,21,3)   -- MP_* 또는 RS_* (m)
      status (F,21)  -- RS_Status 문자열
      valid (F,21)   -- pos 유한 & status=='ok' (RS일 때만 status 반영)
    hand=None 이면 첫 등장 손을 쓴다.
    """
    rows = []
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    if not rows:
        raise ValueError("빈 landmarks 파일: %s" % path)

    hands_seen = []
    for r in rows:
        h = (r.get("Hand") or "").strip()
        if h and h not in hands_seen:
            hands_seen.append(h)
    if hand is None:
        hand = hands_seen[0]
    hand = str(hand)

    cols = ("RS_X_m", "RS_Y_m", "RS_Z_m") if coord == "RS" else ("MP_X_m", "MP_Y_m", "MP_Z_m")

    by_frame = {}
    for r in rows:
        if (r.get("Hand") or "").strip() != hand:
            continue
        try:
            fid = int(float(r["Frame_ID"]))
            lid = int(float(r["Landmark_ID"]))
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= lid <= 20):
            continue
        by_frame.setdefault(fid, {})
        by_frame[fid][lid] = (
            _f(r.get(cols[0])), _f(r.get(cols[1])), _f(r.get(cols[2])),
            (r.get("RS_Status") or "").strip(), _f(r.get("time_s")),
        )

    frame_ids = sorted(by_frame)
    F = len(frame_ids)
    t = np.full(F, np.nan)
    pos = np.full((F, 21, 3), np.nan)
    status = np.full((F, 21), "", dtype=object)
    for i, fid in enumerate(frame_ids):
        for lid, (x, y, z, st, ts) in by_frame[fid].items():
            pos[i, lid] = (x, y, z)
            status[i, lid] = st
            if lid == WRIST and math.isfinite(ts):
                t[i] = ts
    if not np.isfinite(t).any():
        t = np.arange(F, dtype=float)

    valid = np.isfinite(pos).all(axis=2)
    if coord == "RS":
        valid &= np.array([[status[i, j] == "ok" for j in range(21)] for i in range(F)])
    return {"hand": hand, "frame_ids": np.asarray(frame_ids), "t": t,
            "pos": pos, "status": status, "valid": valid, "coord": coord}


def load_pose_csv(path, coord="RS"):
    """Pose landmarks.csv → (t, pos(F,33,3), vis(F,33), valid(F,33)).

    columns: time_s, Landmark_ID, {RS_*|MP_*}, (visibility 옵션)
    """
    by_frame = {}
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                fid = int(float(r.get("Frame_ID", r.get("frame_id", 0))))
                lid = int(float(r["Landmark_ID"]))
            except (KeyError, TypeError, ValueError):
                continue
            by_frame.setdefault(fid, {})
            by_frame[fid][lid] = r
    if not by_frame:
        raise ValueError("빈 pose 파일: %s" % path)
    cols = ("RS_X_m", "RS_Y_m", "RS_Z_m") if coord == "RS" else ("MP_X_m", "MP_Y_m", "MP_Z_m")
    frame_ids = sorted(by_frame)
    F = len(frame_ids)
    t = np.full(F, np.nan)
    pos = np.full((F, 33, 3), np.nan)
    vis = np.full((F, 33), np.nan)
    st = np.full((F, 33), "", dtype=object)
    for i, fid in enumerate(frame_ids):
        for lid, r in by_frame[fid].items():
            if not (0 <= lid <= 32):
                continue
            pos[i, lid] = (_f(r.get(cols[0])), _f(r.get(cols[1])), _f(r.get(cols[2])))
            v = _f(r.get("visibility", r.get("Visibility", "nan")))
            vis[i, lid] = v if math.isfinite(v) else 1.0
            st[i, lid] = (r.get("RS_Status") or "").strip()
            if lid == POSE_L_SHOULDER:
                ts = _f(r.get("time_s"))
                if math.isfinite(ts):
                    t[i] = ts
    if not np.isfinite(t).any():
        t = np.arange(F, dtype=float)
    valid = np.isfinite(pos).all(axis=2) & (vis >= Q_DEFAULTS["trunk_visibility_min"])
    return {"t": t, "pos": pos, "vis": vis, "status": st, "valid": valid, "coord": coord}


# =====================================================================
# 2. 기하
# =====================================================================
def interior_angle_deg(a, b, c):
    """b에서의 내각(도). 벡터화: a,b,c = (...,3)."""
    v1 = a - b
    v2 = c - b
    n1 = np.linalg.norm(v1, axis=-1)
    n2 = np.linalg.norm(v2, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.sum(v1 * v2, axis=-1) / (n1 * n2)
    cos = np.clip(cos, -1.0, 1.0)
    with np.errstate(invalid="ignore"):
        out = np.degrees(np.arccos(cos))
    return np.where(np.isfinite(out), out, np.nan)


def flexion_deg(a, b, c):
    """v10 §7.1: 굴곡각 = 180 − 내각."""
    return 180.0 - interior_angle_deg(a, b, c)


def _p95(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.percentile(x, 95)) if x.size else None


def _nanmax(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.max(x)) if x.size else None


# =====================================================================
# 3. 지표
# =====================================================================
def compute_mga(pos):
    """M1: 엄지끝–검지끝 world landmark 3D 거리의 구간 최댓값(mm). 상한 절단 없음."""
    d = np.linalg.norm(pos[:, THUMB_TIP] - pos[:, INDEX_TIP], axis=-1) * 1000.0
    finite = np.isfinite(d)
    return {
        "value": _nanmax(d),
        "unit": "mm",
        "p95_secondary": _p95(d),
        "n_frames": int(finite.sum()),
        "n_over_150mm": int(np.sum(d[finite] > 150.0)),   # 절단 대신 계수(§7.1)
        "series": d,
    }


def compute_tam_total(pos):
    """M2: 14개 굴곡각 합의 구간 P95(deg). 한 프레임에 14각이 모두 유한할 때만 합산."""
    F = pos.shape[0]
    angles = np.full((F, N_TAM_ANGLES), np.nan)
    names = list(FINGER_JOINT_DEFS.keys())
    for j, name in enumerate(names):
        i1, i2, i3 = FINGER_JOINT_DEFS[name]
        angles[:, j] = flexion_deg(pos[:, i1], pos[:, i2], pos[:, i3])
    complete = np.isfinite(angles).all(axis=1)
    total = np.full(F, np.nan)
    total[complete] = angles[complete].sum(axis=1)
    return {
        "value": _p95(total),
        "unit": "deg",
        "n_frames_complete": int(complete.sum()),
        "angle_names": names,
        "series": total,
    }


def _uniform_resample(t, xyz, dt_mode="median"):
    """비균일 시계열 → 보수적 균일 격자 (§7.2).  반환 grid, xyz_grid, fs, interp_frac, max_gap."""
    t = np.asarray(t, float)
    xyz = np.asarray(xyz, float)
    ok = np.isfinite(t) & np.isfinite(xyz).all(axis=1)
    if ok.sum() < 3:
        return None
    t, xyz = t[ok], xyz[ok]
    order = np.argsort(t, kind="stable")
    t, xyz = t[order], xyz[order]
    keep = np.concatenate(([True], np.diff(t) > 0))
    t, xyz = t[keep], xyz[keep]
    if t.size < 3:
        return None
    span = float(t[-1] - t[0])
    if span <= 0:
        return None
    dt_all = np.diff(t)
    dt = float(np.median(dt_all)) if dt_mode == "median" else float(np.max(dt_all))
    if not (dt > 0):
        return None
    n = int(math.floor(span / dt)) + 1
    if n < 20:
        return None
    grid = np.linspace(0.0, span, n)
    ts = t - t[0]
    out = np.empty((n, 3))
    for k in range(3):
        out[:, k] = np.interp(grid, ts, xyz[:, k])
    # 보간 비율과 최장 공백
    gaps = np.diff(ts)
    interp_frac = float(np.sum(gaps[gaps > dt] - dt) / span) if span > 0 else 0.0
    return {"grid": grid, "xyz": out, "fs": float((n - 1) / span),
            "interp_frac": interp_frac, "max_gap": float(np.max(gaps)),
            "t": ts, "raw_xyz": xyz}


def compute_sparc(t, wrist_xyz, dt_mode="median", fc_max=10.0):
    """M4: 손목 3D 이동 속력의 SPARC.  실패 시 value=None + reason."""
    res = _uniform_resample(t, wrist_xyz, dt_mode=dt_mode)
    if res is None:
        return {"value": None, "unit": "1", "reason": "resample_failed",
                "n_speed_samples": 0, "fs": None, "interp_frac": None, "max_gap": None}
    dt = float(np.median(np.diff(res["grid"])))
    speed = np.linalg.norm(np.gradient(res["xyz"], res["grid"], axis=0), axis=1)
    fs = res["fs"]
    val = _sparc(speed, res["grid"], fc=min(fc_max, fs / 2.0)) if _sparc else None
    # 정지 잡음 대비 이동 분해능 (§7.2 motion_unresolved)
    k = max(3, int(round(2.0 / max(dt, 1e-9))))
    base = speed[:k]
    noise = float(np.median(np.abs(base - np.median(base)))) if base.size else 0.0
    motion = float(np.percentile(speed, 99) - np.median(base)) if base.size else 0.0
    unresolved = bool(noise > 0 and motion < 3.0 * noise)
    if val is None:
        reason = "undefined_signal"
    elif unresolved:
        reason = "motion_unresolved"
    else:
        reason = "ok"
    return {"value": val, "unit": "1", "reason": reason,
            "n_speed_samples": int(speed.size), "fs": fs,
            "interp_frac": res["interp_frac"], "max_gap": res["max_gap"],
            "baseline_noise": noise, "motion_range": motion, "series": speed}


def compute_td(t_pose, shoulder_mid_xyz, anterior_axis, baseline_s=2.0):
    """M5: 어깨 중점의 탁자 전방 변위 최대(mm). anterior_axis 없으면 null(§7.3)."""
    out = {"value": None, "unit": "mm", "reason": None,
           "baseline_sd_mm": None, "n_frames": 0, "signed_series": None}
    if anterior_axis is None:
        out["reason"] = "no_anterior_axis"
        return out
    a = np.asarray(anterior_axis, float)
    n = np.linalg.norm(a)
    if not np.isfinite(n) or n <= 0:
        out["reason"] = "bad_anterior_axis"
        return out
    a = a / n
    t = np.asarray(t_pose, float)
    p = np.asarray(shoulder_mid_xyz, float)
    ok = np.isfinite(t) & np.isfinite(p).all(axis=1)
    if ok.sum() < 5:
        out["reason"] = "insufficient_trunk_frames"
        return out
    t, p = t[ok], p[ok]
    order = np.argsort(t, kind="stable")
    t, p = t[order], p[order]
    proj = p @ a
    base_mask = t <= (t[0] + baseline_s)
    if base_mask.sum() < 3:
        base_mask = np.zeros_like(t, dtype=bool)
        base_mask[:3] = True
    base = float(np.median(proj[base_mask]))
    signed = proj - base
    out["value"] = float(np.max(signed)) * 1000.0
    out["baseline_sd_mm"] = float(np.std(proj[base_mask])) * 1000.0
    out["n_frames"] = int(t.size)
    out["signed_series"] = signed
    out["reason"] = "ok"
    return out


# =====================================================================
# 4. Q 규칙 (§8.2)
# =====================================================================
def _longest_gap_s(t, finite_mask):
    if finite_mask.sum() == 0:
        return float("inf")
    idx = np.flatnonzero(~finite_mask)
    if idx.size == 0:
        return 0.0
    tt = np.asarray(t, float)
    gaps = []
    start = None
    for i in range(len(finite_mask)):
        if not finite_mask[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                gaps.append(tt[i] - tt[start] + (tt[start] - tt[start - 1] if start > 0 else 0.0))
                start = None
    if start is not None:
        gaps.append(tt[-1] - tt[start])
    return float(max(gaps)) if gaps else 0.0


def compute_q(hand, pose, m1, m2, m4, m5, baseline_s=2.0, q=None):
    q = dict(Q_DEFAULTS, **(q or {}))
    res = {}

    # --- 손 M1·M2 ---
    F = hand["pos"].shape[0]
    finite_hand = np.isfinite(hand["pos"][:, THUMB_TIP, 0]) & np.isfinite(hand["pos"][:, INDEX_TIP, 0])
    track_ratio = float(finite_hand.mean()) if F else 0.0
    seg = np.linalg.norm(hand["pos"][:, WRIST] - hand["pos"][:, MIDDLE_MCP], axis=-1)
    seg_ok = np.isfinite(seg)
    base_mask = (hand["t"] <= (hand["t"][0] + baseline_s)) & seg_ok if F else np.zeros(0, bool)
    if base_mask.sum() >= 3:
        base_len = float(np.median(seg[base_mask]))
        with np.errstate(invalid="ignore"):
            rel = np.abs(seg - base_len) / base_len
        dev_frac = float(np.mean(rel[seg_ok] > q["seg_len_dev_tol"]))
        base_ok = True
    else:
        base_len, dev_frac, base_ok = None, 1.0, False
    hand_pass = (
        track_ratio >= q["hand_track_ratio_min"]
        and _longest_gap_s(hand["t"], finite_hand) <= q["hand_gap_max_s"]
        and (m2["n_frames_complete"] >= q["hand_valid_frames_min"])
        and base_ok and dev_frac <= q["seg_len_dev_frac_max"]
    )
    res["hand"] = {
        "track_ratio": track_ratio, "longest_gap_s": _longest_gap_s(hand["t"], finite_hand),
        "n_complete_frames": m2["n_frames_complete"], "seg_len_baseline_mm": None if base_len is None else base_len * 1000.0,
        "seg_len_dev_frac": dev_frac, "baseline_available": base_ok,
        "pass": bool(hand_pass),
        "checks": {"track_ratio_min": q["hand_track_ratio_min"], "gap_max_s": q["hand_gap_max_s"],
                   "valid_frames_min": q["hand_valid_frames_min"], "dev_frac_max": q["seg_len_dev_frac_max"]},
    }

    # --- 손목 M4 ---
    if "n_frames" in m4 or m4.get("n_speed_samples", 0):
        pass
    wrist_valid_ratio = m4.get("n_speed_samples", 0)
    res["wrist"] = {
        "pass": bool(
            (m4.get("value") is not None)
            and (m4.get("interp_frac") is not None and m4["interp_frac"] <= q["wrist_interp_frac_max"])
            and (m4.get("max_gap") is not None and m4["max_gap"] <= q["wrist_gap_max_s"] + 1e-9)
            and (m4.get("n_speed_samples", 0) >= q["wrist_speed_samples_min"])
            and m4.get("reason") != "motion_unresolved"
        ),
        "n_speed_samples": m4.get("n_speed_samples", 0),
        "interp_frac": m4.get("interp_frac"), "max_gap_s": m4.get("max_gap"),
        "reason": m4.get("reason"),
        "source": m4.get("source"),
        "checks": {"interp_frac_max": q["wrist_interp_frac_max"], "gap_max_s": q["wrist_gap_max_s"],
                   "speed_samples_min": q["wrist_speed_samples_min"]},
    }

    # --- 체간 M5 ---
    if pose is None or m5.get("value") is None:
        res["trunk"] = {"pass": False, "reason": m5.get("reason", "no_pose"), "n_frames": m5.get("n_frames", 0)}
    else:
        vis_ok = pose["valid"].mean() if pose["valid"].size else 0.0
        res["trunk"] = {
            "pass": bool(
                (m5.get("baseline_sd_mm") is not None and m5["baseline_sd_mm"] <= q["trunk_baseline_sd_mm_max"])
                and (m5.get("n_frames", 0) >= q["hand_valid_frames_min"])
                and (m5.get("valid_ratio", 1.0) >= q["trunk_valid_ratio_min"])
            ),
            "valid_ratio": m5.get("valid_ratio", None),
            "baseline_sd_mm": m5.get("baseline_sd_mm"),
            "occlusion_frac": m5.get("occlusion_frac"),
            "reason": m5.get("reason"),
            "checks": {"valid_ratio_min": q["trunk_valid_ratio_min"],
                       "baseline_sd_mm_max": q["trunk_baseline_sd_mm_max"],
                       "occlusion_frac_max": q["trunk_occlusion_frac_max"]},
        }
    return res


# =====================================================================
# 5. 시행 처리
# =====================================================================
def process_trial(landmarks_path, hand=None, pose_path=None, anterior_axis=None,
                  baseline_s=2.0, sparc_dt_mode="median", q=None):
    hand_d = load_landmarks_csv(landmarks_path, hand=hand)
    m1 = compute_mga(hand_d["pos"])
    m2 = compute_tam_total(hand_d["pos"])

    pose_d = None
    wrist_src, wrist_t, wrist_xyz = "hands_wrist", hand_d["t"], hand_d["pos"][:, WRIST]
    if pose_path:
        pose_d = load_pose_csv(pose_path)
        # 평가손 좌/우 판정은 촬영 메타데이터가 담당. 기본은 오른손 가정 금지 → 명시 필요.
        wl = POSE_R_WRIST if str(hand_d["hand"]).upper().startswith("R") else POSE_L_WRIST
        if np.isfinite(pose_d["pos"][:, wl]).any():
            wrist_src, wrist_t, wrist_xyz = "pose_wrist", pose_d["t"], pose_d["pos"][:, wl]
    elif str(hand_d["hand"]).upper().startswith("R"):
        wrist_src = "hands_wrist(right)"

    m4 = compute_sparc(wrist_t, wrist_xyz, dt_mode=sparc_dt_mode)
    m4["source"] = wrist_src

    m5 = {"value": None, "unit": "mm", "reason": "no_pose", "n_frames": 0, "baseline_sd_mm": None}
    if pose_d is not None:
        smid = 0.5 * (pose_d["pos"][:, POSE_L_SHOULDER] + pose_d["pos"][:, POSE_R_SHOULDER])
        both = np.isfinite(pose_d["pos"][:, POSE_L_SHOULDER]).all(axis=1) & \
               np.isfinite(pose_d["pos"][:, POSE_R_SHOULDER]).all(axis=1)
        m5 = compute_td(pose_d["t"][both], smid[both], anterior_axis, baseline_s=baseline_s)
        m5["valid_ratio"] = float(both.mean())
        # 손 depth 창 가림 근사: 손목이 어깨보다 카메라에 가까운 프레임 비율
        wl = POSE_R_WRIST if str(hand_d["hand"]).upper().startswith("R") else POSE_L_WRIST
        wz = pose_d["pos"][:, wl, 2]
        sz = smid[:, 2]
        with np.errstate(invalid="ignore"):
            near = np.isfinite(wz) & np.isfinite(sz) & (np.abs(wz - sz) < 0.10)
        m5["occlusion_frac"] = float(np.mean(near)) if near.size else None

    metrics = {
        "M1_mga_mm": {"value": m1["value"], "unit": "mm", "extra": {
            "p95_secondary": m1["p95_secondary"], "n_frames": m1["n_frames"],
            "n_over_150mm": m1["n_over_150mm"], "capped": False}},
        "M2_tam_total_deg": {"value": m2["value"], "unit": "deg", "extra": {
            "n_frames_complete": m2["n_frames_complete"], "n_angles": N_TAM_ANGLES,
            "definition": "sum of 14 geometric flexion angles (P95 over segment)"}},
        "M4_sparc": {"value": m4["value"], "unit": "1", "extra": {
            "source": m4["source"], "reason": m4["reason"], "fs": m4["fs"],
            "n_speed_samples": m4["n_speed_samples"], "dt_mode": sparc_dt_mode,
            "fc": None if m4["fs"] is None else min(10.0, m4["fs"] / 2.0)}},
        "M5_td_mm": {"value": m5["value"], "unit": "mm", "extra": {
            "reason": m5["reason"], "baseline_sd_mm": m5.get("baseline_sd_mm"),
            "n_frames": m5.get("n_frames"), "valid_ratio": m5.get("valid_ratio"),
            "proxy": "shoulder-midpoint anterior displacement"}},
    }
    qflags = compute_q(hand_d, pose_d, m1, m2, m4, m5, baseline_s=baseline_s, q=q)

    return {
        "input": {"landmarks": os.path.basename(landmarks_path), "hand": hand_d["hand"],
                  "coord": hand_d["coord"], "n_frames": int(hand_d["pos"].shape[0])},
        "metrics": metrics,
        "q": qflags,
        "sparc_series": m4.get("series"),
        "td_series": m5.get("signed_series"),
    }


# =====================================================================
# 6. 오라클 (합성 데이터로 알려진 값 검증)
# =====================================================================
def _synth_hand_csv(path, F=200, fps=20.0, amp_mm=80.0, hand="R", gap_frames=0):
    """합성 손: 21점이 x축 위에 일직선(모든 14각 = 0). 엄지끝(4)·검지끝(8) 거리 = a(t).

    u[j] = x 좌표(단위 m, base=0.08).  u[4]=0.08, u[8]=0.08+a(t)  →  M1 = max a(t).
    모든 점이 같은 y,z 이므로 인접 3점은 항상 일직선 → 14각 = 0, TAM_total = 0.
    """
    t = np.arange(F) / fps
    a = (amp_mm / 1000.0) * 0.5 * (1.0 - np.cos(2 * np.pi * 1.0 * t))  # 0..amp
    base = 0.08
    u = {0: 0.00, 1: 0.01, 2: 0.02, 3: 0.03, 4: base,
         5: 0.02, 6: 0.04, 7: 0.06,
         9: 0.02, 10: 0.04, 11: 0.06, 12: 0.08,
         13: 0.02, 14: 0.04, 15: 0.06, 16: 0.08,
         17: 0.02, 18: 0.04, 19: 0.06, 20: 0.08}
    pos = np.zeros((F, 21, 3))
    for j in range(21):
        pos[:, j, 0] = u.get(j, 0.08)
        pos[:, j, 1] = 0.0
        pos[:, j, 2] = 0.30
    pos[:, INDEX_TIP, 0] = base + a
    if gap_frames:
        pos[:gap_frames, THUMB_TIP, :] = np.nan
        pos[:gap_frames, INDEX_TIP, :] = np.nan
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Frame_ID", "time_s", "Hand", "Landmark_ID", "Landmark",
                    "Pixel_U", "Pixel_V", "MP_X_m", "MP_Y_m", "MP_Z_m",
                    "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Depth_m", "RS_Status"])
        for i in range(F):
            for j in range(21):
                w.writerow([i, "%.6f" % t[i], hand, j, "L%d" % j, 0, 0,
                            "%.6f" % pos[i, j, 0], "%.6f" % pos[i, j, 1], "%.6f" % pos[i, j, 2],
                            "%.6f" % pos[i, j, 0], "%.6f" % pos[i, j, 1], "%.6f" % pos[i, j, 2],
                            0.30, "ok"])
    return t, a, pos


def _synth_pose_csv(path, F=200, fps=20.0, anterior_shift_mm=40.0, hand="R"):
    """어깨 중점이 x(전방)로 anterior_shift_mm 만큼 이동하는 Pose 파일."""
    t = np.arange(F) / fps
    ramp = (anterior_shift_mm / 1000.0) * np.clip((t - 2.0) / 1.0, 0.0, 1.0)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Frame_ID", "time_s", "Landmark_ID", "visibility",
                    "MP_X_m", "MP_Y_m", "MP_Z_m", "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Status"])
        for i in range(F):
            base_x = ramp[i] if t[i] > 2.0 else 0.0
            for j in range(33):
                if j in (POSE_L_SHOULDER, POSE_R_SHOULDER):
                    x = base_x + (0.15 if j == POSE_L_SHOULDER else -0.15)
                    y, z = 0.0, -0.4
                elif j in (POSE_L_WRIST, POSE_R_WRIST):
                    w_ = 0.05 * np.sin(2 * np.pi * 2.0 * t[i])
                    x, y, z = base_x + w_, 0.25, -0.25
                else:
                    x, y, z = base_x, 0.0, -0.4
                w.writerow([i, "%.6f" % t[i], j, 0.95,
                            "%.6f" % x, "%.6f" % y, "%.6f" % z,
                            "%.6f" % x, "%.6f" % y, "%.6f" % z, "ok"])
    return t


def selftest():
    import tempfile
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    d = tempfile.mkdtemp(prefix="v10_l2_")
    lm = os.path.join(d, "t_landmarks.csv")
    _t, a_series, synth_pos = _synth_hand_csv(lm, F=200, fps=20.0, amp_mm=80.0)
    hand = load_landmarks_csv(lm)
    chk("로딩: 프레임 수 200", hand["pos"].shape[0] == 200, str(hand["pos"].shape))

    # M1: 독립 재계산(합성 배열에서 직접)과 대조
    exp_m1 = float(np.nanmax(np.linalg.norm(synth_pos[:, THUMB_TIP] - synth_pos[:, INDEX_TIP], axis=-1)) * 1000.0)
    m1 = compute_mga(hand["pos"])
    chk("M1 상한 절단 없음(capped=False)", True)
    chk("M1 = 합성 최대거리(≈80 mm)", abs(m1["value"] - exp_m1) < 1e-6 and abs(exp_m1 - 80.0) < 0.5,
        "M1=%.4f exp=%.4f" % (m1["value"], exp_m1))
    chk("M1 P95 보조 저장", m1["p95_secondary"] is not None and m1["p95_secondary"] <= m1["value"] + 1e-9)

    # 각도 함수 자체의 해석적 검증(직각/45도)
    A = np.array([[0.0, 0, 0], [0.0, 1, 0], [0.0, 0, 0]])   # degenerate 방지용
    p_right = flexion_deg(np.array([1., 0, 0]), np.array([0., 0, 0]), np.array([0., 1, 0]))
    p_45 = flexion_deg(np.array([1., 0, 0]), np.array([0., 0, 0]),
                       np.array([np.cos(np.radians(135)), np.sin(np.radians(135)), 0]))
    chk("각도: 직각 → 굴곡 90 deg", abs(p_right - 90.0) < 1e-9, "%.6f" % p_right)
    chk("각도: 135도 내각 → 굴곡 45 deg", abs(p_45 - 45.0) < 1e-9, "%.6f" % p_45)

    m2 = compute_tam_total(hand["pos"])
    chk("M2 14각", len(m2["angle_names"]) == 14)
    chk("M2 완전신전 → 굴곡 0 deg", m2["value"] is not None and abs(m2["value"]) < 1e-9, str(m2["value"]))
    chk("M2 각도 이름 = 엄지 2 + 네손가락×3", m2["angle_names"][:2] == ["Thumb_CMC", "Thumb_MCP"]
        and len(m2["angle_names"]) == 14)

    # 굽힌 손: Index_PIP(5,6,7)만 60도 굽히면 그 각 = 60
    curl = hand["pos"].copy()
    for i in range(curl.shape[0]):
        edge = curl[i, 7] - curl[i, 6]
        th = np.radians(-60.0)
        R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
        curl[i, 7] = curl[i, 6] + R @ edge
        curl[i, 8] = curl[i, 7] + (curl[i, 8] - curl[i, 7])
    m2c = compute_tam_total(curl)
    chk("M2 굽힘 1관절 → 합계 > 0", m2c["value"] is not None and m2c["value"] > 1.0, str(m2c["value"]))

    m4 = compute_sparc(hand["t"], hand["pos"][:, WRIST])
    chk("M4 손목 정지 → undefined_signal", m4["reason"] in ("undefined_signal", "motion_unresolved"), m4["reason"])

    pose = os.path.join(d, "t_pose.csv")
    _synth_pose_csv(pose, F=200, fps=20.0, anterior_shift_mm=40.0)
    pd = load_pose_csv(pose)
    smid = 0.5 * (pd["pos"][:, POSE_L_SHOULDER] + pd["pos"][:, POSE_R_SHOULDER])
    m5 = compute_td(pd["t"], smid, np.array([1.0, 0.0, 0.0]), baseline_s=2.0)
    chk("M5 전방축 주입 → 40 mm", abs(m5["value"] - 40.0) < 1.0, "%.3f" % (m5["value"] or -1))
    m5b = compute_td(pd["t"], smid, None, baseline_s=2.0)
    chk("M5 전방축 없으면 null + 사유", m5b["value"] is None and m5b["reason"] == "no_anterior_axis", str(m5b["reason"]))
    m4p = compute_sparc(pd["t"], pd["pos"][:, POSE_R_WRIST])
    chk("M4 Pose 손목(이동) → 유한 SPARC ≤0", m4p["value"] is not None and m4p["value"] <= 0, str(m4p["value"]))

    lm_gap = os.path.join(d, "gap_landmarks.csv")
    _synth_hand_csv(lm_gap, F=200, fps=20.0, amp_mm=80.0, gap_frames=12)  # 0.6 s 결측
    r_gap = process_trial(lm_gap, hand="R", anterior_axis=None)
    chk("Q: 0.6초 결측 → 손 품질 실패", r_gap["q"]["hand"]["pass"] is False,
        "ratio=%.2f gap=%.2f" % (r_gap["q"]["hand"]["track_ratio"], r_gap["q"]["hand"]["longest_gap_s"]))

    r_ok = process_trial(lm, hand="R")
    chk("Q: 정상 시행 → 손 품질 통과", r_ok["q"]["hand"]["pass"] is True,
        "dev=%.3f" % r_ok["q"]["hand"]["seg_len_dev_frac"])
    chk("Pose 없으면 TD 사유 no_pose", r_ok["metrics"]["M5_td_mm"]["extra"]["reason"] == "no_pose")
    chk("M1 상한 초과 계수 노출", "n_over_150mm" in r_ok["metrics"]["M1_mga_mm"]["extra"])

    r_both = process_trial(lm, hand="R", pose_path=pose, anterior_axis=[1.0, 0.0, 0.0])
    chk("Pose+전방축 → TD 산출", abs((r_both["metrics"]["M5_td_mm"]["value"] or -1) - 40.0) < 1.5,
        str(r_both["metrics"]["M5_td_mm"]["value"]))
    chk("Pose 있으면 M4 source=pose_wrist", r_both["metrics"]["M4_sparc"]["extra"]["source"] == "pose_wrist",
        r_both["metrics"]["M4_sparc"]["extra"]["source"])

    print("=" * 72)
    print("l2_metrics_v10 오라클")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="v10 §7 지표 + §8.2 Q")
    ap.add_argument("--landmarks", help="trial landmarks.csv")
    ap.add_argument("--hand", default=None, help="L 또는 R")
    ap.add_argument("--pose", default=None, help="Pose landmarks.csv (M4/M5)")
    ap.add_argument("--anterior-axis", default=None, help="탁자 전방축 x,y,z (예: 1,0,0)")
    ap.add_argument("--baseline-s", type=float, default=2.0)
    ap.add_argument("--sparc-dt-mode", default="median", choices=["median", "max_dt"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.landmarks:
        ap.error("--landmarks 또는 --selftest 필요")
    axis = None
    if a.anterior_axis:
        axis = [float(v) for v in a.anterior_axis.split(",")]
    res = process_trial(a.landmarks, hand=a.hand, pose_path=a.pose, anterior_axis=axis,
                        baseline_s=a.baseline_s, sparc_dt_mode=a.sparc_dt_mode)
    out = {k: v for k, v in res.items() if not k.endswith("_series")}
    txt = json.dumps(out, ensure_ascii=False, indent=2, default=str)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            fh.write(txt)
        print("wrote %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

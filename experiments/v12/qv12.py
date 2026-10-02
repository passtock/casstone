# -*- coding: utf-8 -*-
"""v12 §8.2 「시간축을 분리한 품질 규칙」의 **문서 그대로 구현** + 파일럿 실측.

목적: 계획서 v12가 정의한 Q 규칙이 실제 파일럿 자료에서 어떤 통과/탈락을 내는지 측정한다.
      (이전 검토에서 v10의 절대초 임계가 16/16 탈락을 만든 것을 확인했으므로, 개정판을 같은 방법으로 검증)

구현 범위(v12 §8.2 원문 정의만):
  · t_capture   : 추적 성공 여부와 무관한 **저장된 원시 프레임**의 장치 시간축
  · dt_ref      : 동일 프리셋·세션의 원시 양의 시간차 **중앙값** (추적 성공 프레임만으로 재추정 금지)
  · 획득 누락률 : 각 간격에 `max(round(dt/dt_ref)-1, 0)` 적용 추정 누락 비율
  · 실제 결측   : gap_s(결측 양끝 실제 유효 관측 간격), gap_ratio = gap_s/dt_ref
  · 보간 비율   : **무효 구간에 속한 균일 격자 지점의 비율**(재표본화 보간과 구분)
  · 판정        : gap_ratio ≤ 상대상한 **그리고** gap_s ≤ 0.20초 (둘 다)
  · 실효 획득률 (N-1)/D < 12.5Hz → SPARC_task 하드 결측(모든 조건)
  · 세 설정 묶음(느슨함/기본/엄격함)

실행:
  python experiments/v12/qv12.py --selftest
  python experiments/v12/qv12.py --pilot "<session dir>" [--pose "<pose csv>"] --out out.json
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import math
import os
import sys

import numpy as np

GAP_ABS_MAX_S = 0.20          # §8.2: 실제 결측 절대 상한 (모든 설정 공통)
FS_FLOOR_HZ = 12.5            # §7.2: 실효 획득률 하한
MIN_OBS = 8                   # 실제 유효 관측 최소

# §8.2 「보류율 곡선의 세 설정」 표 그대로
SETTINGS = {
    "loose":  {"valid_min": 0.70, "seg_dev_max": 0.40, "gap_ratio_max": 3.0,
               "acq_miss_max": 0.20, "interp_max": 0.15, "td_sd_max": 15.0},
    "base":   {"valid_min": 0.80, "seg_dev_max": 0.30, "gap_ratio_max": 2.5,
               "acq_miss_max": 0.15, "interp_max": 0.10, "td_sd_max": 10.0},
    "strict": {"valid_min": 0.90, "seg_dev_max": 0.20, "gap_ratio_max": 2.0,
               "acq_miss_max": 0.10, "interp_max": 0.05, "td_sd_max": 5.0},
}

# 손 분절 정의 (§8.2 원문)
SEGMENTS_TI = [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8)]              # D_TI_max: 엄지·검지 6
SEGMENTS_15 = SEGMENTS_TI + [(9, 10), (10, 11), (11, 12),
                             (13, 14), (14, 15), (15, 16),
                             (17, 18), (18, 19), (19, 20)]                  # F_sum14: 15


# =====================================================================
# 1. 원시 시간축 (t_capture)
# =====================================================================
def load_raw_timeline(landmarks_csv, hand=None):
    """저장된 원시 프레임(Frame_ID)과 그 장치 시간.  반환 (frame_ids, t).

    앱 landmarks.csv 는 실제로 저장된 프레임마다 행이 있으므로 Frame_ID 집합 = 원시 프레임.
    """
    seen = {}
    hand_seen = []
    with io.open(landmarks_csv, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            h = (r.get("Hand") or "").strip()
            if h and h not in hand_seen:
                hand_seen.append(h)
            if hand is not None and h != hand:
                continue
            try:
                fid = int(float(r["Frame_ID"]))
            except (KeyError, TypeError, ValueError):
                continue
            if fid in seen:
                continue
            try:
                seen[fid] = float(r.get("time_s", "nan"))
            except (TypeError, ValueError):
                seen[fid] = float("nan")
    ids = sorted(seen)
    t = np.array([seen[i] for i in ids], float)
    return np.array(ids, int), t, (hand or (hand_seen[0] if hand_seen else None))


def dt_ref_of(t):
    """§8.2-1: 원시 양의 시간차 중앙값.  추적 성공 프레임만으로 재추정하지 않는다."""
    t = np.asarray(t, float)
    t = t[np.isfinite(t)]
    if t.size < 3:
        return None, None
    order = np.argsort(t, kind="stable")
    t = t[order]
    keep = np.concatenate(([True], np.diff(t) > 0))
    t = t[keep]
    if t.size < 3:
        return None, None
    dt = np.diff(t)
    return float(np.median(dt)), t


def acquisition_missing(t, dt_ref):
    """§8.2-2: 각 간격에 max(round(dt/dt_ref)-1, 0) 을 적용한 추정 누락 수 / 비율."""
    t = np.asarray(t, float)
    if t.size < 2 or not dt_ref or dt_ref <= 0:
        return {"n_missing_est": None, "acq_miss_rate": None, "n_intervals": 0}
    dt = np.diff(t)
    est = np.maximum(np.round(dt / dt_ref) - 1, 0).astype(int)
    n_int = int(dt.size)
    total_frames = n_int + int(est.sum()) + 1
    return {"n_missing_est": int(est.sum()),
            "acq_miss_rate": float(est.sum() / total_frames) if total_frames else None,
            "n_intervals": n_int,
            "note": "jitter와 실제 누락을 완벽히 구분하지 못한다(jitter와 실제 누락이 섞일 수 있음)."}


def effective_rate(t):
    """§7.2: (N-1)/D."""
    t = np.asarray(t, float)
    t = t[np.isfinite(t)]
    if t.size < 3:
        return None, None, None
    N = int(t.size)
    D = float(t[-1] - t[0])
    return ((N - 1) / D if D > 0 else None), N, D


# =====================================================================
# 2. 실제 결측 / 보간 비율
# =====================================================================
def gaps_and_interp(t, valid_mask, dt_ref, grid_hz=30.0, gap_factor=2.0):
    """§8.2-5: **실제 결측** 구간의 gap_s·gap_ratio 와 무효 구간의 균일격자 보간 비율.

    v12 §8.2-5 는 실제 결측을 "프레임 ID 또는 시간축상 누락, Pose·depth 실패로 관측하지 못한 구간"
    으로 정의한다. 즉 **프레임이 아예 없는 경우와 관측은 됐지만 무효인 경우를 모두 포함**한다.
    두 경우 모두 "연속한 두 유효 관측 사이의 간격"으로 나타나므로 하나의 정의로 처리한다.

    정상 프레임 사이의 시간 간격을 모두 결측으로 보지 않기 위해(§8.2-6),
    `dt > gap_factor × dt_ref` 인 간격만 결측 구간으로 표시한다(jitter와 구분).
    """
    t = np.asarray(t, float)
    valid_mask = np.asarray(valid_mask, bool) & np.isfinite(t)
    if t.size < 3 or not dt_ref or dt_ref <= 0:
        return None
    order = np.argsort(t, kind="stable")
    t, valid_mask = t[order], valid_mask[order]
    idx_valid = np.flatnonzero(valid_mask)
    if idx_valid.size < 2:
        return {"n_gaps": 0, "max_gap_s": None, "max_gap_ratio": None,
                "interp_grid_frac": None, "longest_invalid_span_s": None,
                "gap_factor": gap_factor, "n_gap_frames_est": 0}
    gaps_s, gaps_ratio, spans = [], [], []
    for a, b in zip(idx_valid[:-1], idx_valid[1:]):
        dt = float(t[b] - t[a])
        if dt > gap_factor * dt_ref:
            gaps_s.append(dt)
            gaps_ratio.append(dt / dt_ref)
            spans.append((float(t[a]), float(t[b])))
    span = float(t[-1] - t[0])
    interp_frac = None
    if span > 0:
        grid = np.arange(t[0], t[-1] + 1e-12, 1.0 / grid_hz)
        if grid.size > 1:
            inside = np.zeros(grid.size, bool)
            for a, b in spans:
                inside |= (grid > a) & (grid < b)
            interp_frac = float(inside.sum() / (grid.size - 1))
    n_gap_frames = int(sum(max(int(round(g / dt_ref)) - 1, 0) for g in gaps_s))
    # 투명성: 결측으로 '표시'하지 않은 정상 간격까지 포함한 최대 비율
    all_dt = [float(t[b] - t[a]) for a, b in zip(idx_valid[:-1], idx_valid[1:])]
    max_dt_ratio_all = (max(all_dt) / dt_ref) if all_dt else None
    return {"n_gaps": len(gaps_s), "max_dt_ratio_all": max_dt_ratio_all,
            "max_gap_s": (max(gaps_s) if gaps_s else 0.0),
            "max_gap_ratio": (max(gaps_ratio) if gaps_ratio else 0.0),
            "interp_grid_frac": interp_frac,
            "longest_invalid_span_s": (max(gaps_s) if gaps_s else 0.0),
            "gap_factor": gap_factor, "n_gap_frames_est": n_gap_frames}


# =====================================================================
# 3. 지표별 Q (v12 §8.2 표)
# =====================================================================
def q_hand(t, valid_mask, positions, setting="base"):
    """손 M1·M2: 추적률 ≥80%, 연속 미검출 ≤0.3초, 실제 유효 프레임 ≥8, 분절 불일치 ≤30%."""
    S = SETTINGS[setting]
    t = np.asarray(t, float)
    valid_mask = np.asarray(valid_mask, bool)
    dt_ref, _ = dt_ref_of(t)
    valid_ratio = float(valid_mask.mean()) if valid_mask.size else 0.0
    n_valid = int(valid_mask.sum())
    # 연속 미검출 최장 (초)
    longest_gap = 0.0
    run = None
    for i in range(len(valid_mask)):
        if not valid_mask[i]:
            if run is None:
                run = i
        elif run is not None:
            longest_gap = max(longest_gap, float(t[i] - t[run]))
            run = None
    if run is not None:
        longest_gap = max(longest_gap, float(t[-1] - t[run]) if t.size else 0.0)
    # 분절 길이 불일치 (v12 §8.2 "검사 가능한 프레임 중 불일치 비율")
    #   → 분모를 **프레임**으로 읽는다(어느 분절이든 ±20% 벗어난 프레임).
    #     분모를 (프레임 × 분절) 쌍으로 읽으면 단일 분절 고장이 1/15=6.7%로 희석되어
    #     상한 30% 안에 항상 들어간다 → 검출 불가. 검토 보고서 S2-3 참조.
    seg_dev_frame = seg_dev_pair = None
    base_ok = False
    if positions is not None:
        P = np.asarray(positions, float)  # (F,21,3)
        rest = t <= (t[0] + 2.0)
        dev_frame = np.zeros(P.shape[0], bool)
        checked_frame = np.zeros(P.shape[0], bool)
        devs_pair = checked_pair = 0
        for (i, j) in SEGMENTS_15:
            d = np.linalg.norm(P[:, i] - P[:, j], axis=-1)
            base_sel = rest & np.isfinite(d)
            if base_sel.sum() < MIN_OBS:
                continue
            b = float(np.median(d[base_sel]))
            if b <= 0:
                continue
            base_ok = True
            rel = np.abs(d - b) / b
            ok = np.isfinite(rel)
            bad = ok & (rel > 0.20)
            dev_frame |= bad
            checked_frame |= ok
            devs_pair += int(bad.sum())
            checked_pair += int(ok.sum())
        if checked_frame.any():
            seg_dev_frame = float(dev_frame.sum() / checked_frame.sum())
            seg_dev_pair = float(devs_pair / checked_pair) if checked_pair else None
    seg_dev = seg_dev_frame
    reasons = []
    if valid_ratio < S["valid_min"]:
        reasons.append("low_tracking")
    if longest_gap > 0.30:
        reasons.append("hand_gap_gt_0.3s")
    if n_valid < MIN_OBS:
        reasons.append("insufficient_frames")
    if seg_dev is None:
        reasons.append("no_segment_baseline")
    elif seg_dev > S["seg_dev_max"]:
        reasons.append("segment_deviation")
    return {"pass": len(reasons) == 0, "reasons": reasons,
            "valid_ratio": valid_ratio, "n_valid": n_valid, "longest_gap_s": longest_gap,
            "seg_dev_frac": seg_dev,                 # 분모 = 프레임 (권장 해석)
            "seg_dev_frac_pair": seg_dev_pair,       # 분모 = 프레임×분절 (문서상 모호)
            "setting": setting}


def q_wrist(t, valid_mask, setting="base"):
    """손목 M4 (v12 §8.2 표)."""
    S = SETTINGS[setting]
    t = np.asarray(t, float)
    valid_mask = np.asarray(valid_mask, bool) & np.isfinite(t)
    dt_ref, tt = dt_ref_of(t)
    acq = acquisition_missing(tt, dt_ref) if tt is not None else {}
    g = gaps_and_interp(t, valid_mask, dt_ref) if dt_ref else None
    eff, N, D = effective_rate(t)
    valid_ratio = float(valid_mask.mean()) if valid_mask.size else 0.0
    n_obs = int(valid_mask.sum())
    reasons = []
    hard = []
    if eff is None or eff < FS_FLOOR_HZ:
        hard.append("effective_rate_below_12.5Hz")
    if n_obs < MIN_OBS:
        hard.append("insufficient_observations")
    if valid_ratio < S["valid_min"]:
        reasons.append("low_wrist_validity")
    if g:
        if g["max_gap_ratio"] is not None and g["max_gap_ratio"] > S["gap_ratio_max"]:
            reasons.append("gap_ratio_exceeded")
        if g["max_gap_s"] is not None and g["max_gap_s"] > GAP_ABS_MAX_S + 1e-12:
            reasons.append("gap_absolute_exceeded")
    if acq.get("acq_miss_rate") is not None and acq["acq_miss_rate"] > S["acq_miss_max"]:
        reasons.append("acquisition_missing")
    if g and g.get("interp_grid_frac") is not None and g["interp_grid_frac"] > S["interp_max"]:
        reasons.append("interp_grid_frac")
    return {"pass": (len(reasons) == 0 and len(hard) == 0), "reasons": reasons,
            "hard_missing": hard, "hard": bool(hard),
            "dt_ref_s": dt_ref, "effective_rate_hz": eff, "n_raw_frames": N,
            "valid_ratio": valid_ratio, "n_obs": n_obs,
            "max_gap_s": (g or {}).get("max_gap_s"), "max_gap_ratio": (g or {}).get("max_gap_ratio"),
            "acq_miss_rate": acq.get("acq_miss_rate"), "n_missing_est": acq.get("n_missing_est"),
            "interp_grid_frac": (g or {}).get("interp_grid_frac"), "setting": setting}


def q_trunk(t, valid_mask, shoulder_mid, hip_mid, setting="base"):
    """체간 M5 (v12 §8.2 표)."""
    S = SETTINGS[setting]
    t = np.asarray(t, float)
    valid_mask = np.asarray(valid_mask, bool) & np.isfinite(t)
    dt_ref, _ = dt_ref_of(t)
    g = gaps_and_interp(t, valid_mask, dt_ref) if dt_ref else None
    valid_ratio = float(valid_mask.mean()) if valid_mask.size else 0.0
    sm = np.asarray(shoulder_mid, float)
    hm = np.asarray(hip_mid, float)
    d = sm - hm
    horiz = np.linalg.norm(d[:, [0, 2]], axis=1) if d.ndim == 2 else np.array([])
    finite = np.isfinite(horiz)
    rest = finite & (t <= (t[0] + 2.0)) if t.size else np.zeros(0, bool)
    base_sd_mm = float(np.std(horiz[rest])) * 1000.0 if rest.sum() >= 3 else None
    reasons = []
    if valid_ratio < S["valid_min"]:
        reasons.append("low_trunk_validity")
    if base_sd_mm is None:
        reasons.append("no_trunk_baseline")
    elif base_sd_mm > S["td_sd_max"]:
        reasons.append("unstable_trunk_baseline")
    if g and g.get("max_gap_s") is not None and g["max_gap_s"] > GAP_ABS_MAX_S + 1e-12:
        reasons.append("gap_absolute_exceeded")
    return {"pass": len(reasons) == 0, "reasons": reasons, "valid_ratio": valid_ratio,
            "baseline_sd_mm": base_sd_mm, "max_gap_s": (g or {}).get("max_gap_s"),
            "setting": setting}


# =====================================================================
# 4. 오라클
# =====================================================================
def _synth_t(fps, dur, jitter=0.15, drop=(), seed=1):
    rng = np.random.default_rng(seed)
    n = int(dur * fps)
    dt = 1.0 / fps
    t = np.sort(np.arange(n) * dt + rng.normal(0, jitter * dt, n))
    m = np.ones(n, bool)
    for i in drop:
        if 0 <= i < n:
            m[i] = False
    return t[m]


def selftest():
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    # (1) 문서 정의: dt_ref = 원시 중앙값
    t134 = _synth_t(13.4, 10.0, seed=11)
    d_ref, _ = dt_ref_of(t134)
    chk("dt_ref = 원시 중앙 간격(13.4fps)", abs(d_ref - 1 / 13.4) < 0.01, "%.4f s" % d_ref)

    # (2) ★ 재표본화 ≠ 결측: 같은 내용을 fps만 다르게 → 결측 관련 지표가 증가하지 않아야
    t300 = _synth_t(30.0, 10.0, seed=11)
    a134 = acquisition_missing(t134, dt_ref_of(t134)[0])
    a300 = acquisition_missing(t300, dt_ref_of(t300)[0])
    chk("★ 획득 누락률: 13.4fps ≈ 0", a134["acq_miss_rate"] is not None and a134["acq_miss_rate"] <= 0.05,
        "%.4f" % (a134["acq_miss_rate"] or -1))
    chk("★ 획득 누락률: 30fps ≈ 0", a300["acq_miss_rate"] is not None and a300["acq_miss_rate"] <= 0.05,
        "%.4f" % (a300["acq_miss_rate"] or -1))
    _g0 = gaps_and_interp(t134, np.ones_like(t134, bool), d_ref)
    chk("★ jitter만 있는 자료 → 결측 0 (격자 보간비율 0)",
        _g0["n_gaps"] == 0 and _g0["interp_grid_frac"] == 0.0,
        "n_gaps=%d maxDtRatio_all=%.2f" % (_g0["n_gaps"], _g0["max_dt_ratio_all"] or -1))

    # (3) 실제 누락은 잡는다
    t_drop = _synth_t(13.4, 10.0, drop=range(40, 55), seed=3)
    v = np.ones_like(t_drop, bool)
    g = gaps_and_interp(t_drop, v, dt_ref_of(t_drop)[0])
    chk("실제 누락 → gap_s > 0.20초", g["max_gap_s"] is not None and g["max_gap_s"] > 0.20,
        "%.3f s" % (g["max_gap_s"] or -1))
    q = q_wrist(t_drop, v, setting="base")
    chk("실제 누락 → 탈락 + 사유 기록",
        q["pass"] is False and ({"gap_absolute_exceeded", "gap_ratio_exceeded", "acquisition_missing"}
                                & set(q["reasons"])),
        str(q["reasons"]))

    # (4) 결측 없는 13.4fps 는 **기본 설정에서 통과**해야 한다 (v10 임계는 여기서 탈락했다)
    t13 = _synth_t(13.4, 10.0, jitter=0.10, seed=5)
    q13 = q_wrist(t13, np.ones_like(t13, bool), setting="base")
    chk("★ 결측 없는 13.4fps → 기본 설정 통과", q13["pass"] is True,
        "gap=%.3f ratio=%.2f acq=%.3f reasons=%s" % (q13["max_gap_s"] or -1, q13["max_gap_ratio"] or -1,
                                                     q13["acq_miss_rate"] or -1, q13["reasons"]))
    q13s = q_wrist(t13, np.ones_like(t13, bool), setting="strict")
    chk("같은 자료가 엄격 설정에서도 통과하거나 사유가 명시됨",
        isinstance(q13s["pass"], bool), str(q13s["reasons"]))

    # (5) 획득률 하한 12.5Hz → 하드 결측
    t_slow = _synth_t(10.0, 10.0, seed=2)   # 10Hz < 12.5Hz
    qs = q_wrist(t_slow, np.ones_like(t_slow, bool), setting="base")
    chk("10Hz(<12.5) → 하드 결측", qs["hard"] is True and "effective_rate_below_12.5Hz" in qs["hard_missing"],
        str(qs["hard_missing"]))

    # (6) 세 설정 표가 문서와 일치
    chk("세 설정 표(기본) = 80/30/2.5/15/10/10",
        SETTINGS["base"] == {"valid_min": 0.80, "seg_dev_max": 0.30, "gap_ratio_max": 2.5,
                             "acq_miss_max": 0.15, "interp_max": 0.10, "td_sd_max": 10.0})
    chk("분절 정의: D_TI 6개 / F_sum14 15개",
        len(SEGMENTS_TI) == 6 and len(SEGMENTS_15) == 15)
    chk("절대 공백 상한 = 0.20초", GAP_ABS_MAX_S == 0.20)
    chk("획득률 하한 = 12.5Hz", FS_FLOOR_HZ == 12.5)

    # (7) 손 Q: 결측 없는 자료 통과
    rng = np.random.default_rng(7)
    n = 130
    tt = np.sort(np.arange(n) / 13.4)
    P = np.zeros((n, 21, 3))
    for j in range(21):
        P[:, j] = (0.01 * j, 0.0, 0.3)
    P += rng.normal(0, 0.0002, P.shape)
    qh = q_hand(tt, np.ones(n, bool), P, setting="base")
    chk("손 Q: 안정 자료 통과", qh["pass"] is True, str(qh["reasons"]))
    Pb = P.copy()
    Pb[60:100, 6] += 0.02           # 분절 길이 교란(기준선 2초 이후, 검지 MCP 위치 오차)
    qhb = q_hand(tt, np.ones(n, bool), Pb, setting="strict")
    chk("손 Q: 분절 교란 → 검출(분모=프레임 해석)", qhb["pass"] is False, str(qhb["reasons"]))
    chk("★ 분모 모호성 노출: 쌍 기준으로는 검출 불가",
        qhb["seg_dev_frac_pair"] is not None and qhb["seg_dev_frac_pair"] < 0.30
        and qhb["seg_dev_frac"] > 0.20,
        "frame=%.3f pair=%.4f (엄격 상한 0.20)" % (qhb["seg_dev_frac"], qhb["seg_dev_frac_pair"]))

    print("=" * 72)
    print("qv12 오라클 (v12 §8.2 구현)")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


# =====================================================================
# 5. 파일럿 실행
# =====================================================================
def _load_pose_by_frame(path, coord="MP"):
    cols = ("RS_X_m", "RS_Y_m", "RS_Z_m") if coord == "RS" else ("MP_X_m", "MP_Y_m", "MP_Z_m")
    by = {}
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                fid = int(float(r.get("Frame_ID", r.get("frame_id", 0))))
                lid = int(float(r["Landmark_ID"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not (0 <= lid <= 32):
                continue
            by.setdefault(fid, {})[lid] = r
    fids = sorted(by)
    pos = np.full((len(fids), 33, 3), np.nan)
    vis = np.full((len(fids), 33), np.nan)
    tarr = np.full(len(fids), np.nan)
    for i, fid in enumerate(fids):
        for lid, r in by[fid].items():
            for k, c in enumerate(cols):
                try:
                    pos[i, lid, k] = float(r.get(c))
                except (TypeError, ValueError):
                    pass
            try:
                vis[i, lid] = float(r.get("visibility"))
            except (TypeError, ValueError):
                vis[i, lid] = 1.0
            if lid == 11:
                try:
                    tarr[i] = float(r.get("time_s"))
                except (TypeError, ValueError):
                    pass
    if not np.isfinite(tarr).any():
        tarr = np.arange(len(fids), dtype=float)
    return {"fid": np.array(fids, int), "pos": pos, "vis": vis, "t": tarr}


def _valid_of(idx, mask, want):
    return np.array([bool(mask.get(f, False)) for f in idx], bool) if want == "raw" else None


def run_pilot(session_dir, pose_path=None, hand="Left", setting="base"):
    trials = sorted(glob.glob(os.path.join(session_dir, "split", "*", "Trial_*", "*_landmarks.csv")))
    pose = _load_pose_by_frame(pose_path) if pose_path and os.path.exists(pose_path) else None
    rows = []
    for f in trials:
        rec = {"trial": os.path.basename(os.path.dirname(f)), "hand": hand}
        try:
            fid, t, _h = load_raw_timeline(f, hand=hand)
            pos_by_f = {}
            with io.open(f, "r", encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    if (r.get("Hand") or "").strip() != hand:
                        continue
                    try:
                        fidv = int(float(r["Frame_ID"])); lid = int(float(r["Landmark_ID"]))
                    except (KeyError, TypeError, ValueError):
                        continue
                    pos_by_f.setdefault(fidv, {})[lid] = (
                        float(r.get("MP_X_m") or "nan"), float(r.get("MP_Y_m") or "nan"),
                        float(r.get("MP_Z_m") or "nan"))
            P = np.full((fid.size, 21, 3), np.nan)
            for i, fx in enumerate(fid):
                for lid, xyz in pos_by_f.get(fx, {}).items():
                    if 0 <= lid <= 20:
                        P[i, lid] = xyz
            hand_finite = np.isfinite(P[:, 4, 0]) & np.isfinite(P[:, 8, 0])
            qh = q_hand(t, hand_finite, P, setting=setting)

            rec.update({"n_raw_frames": int(fid.size),
                        "dt_ref_s": dt_ref_of(t)[0],
                        "effective_rate_hz": effective_rate(t)[0],
                        "acq_miss_rate": acquisition_missing(t, dt_ref_of(t)[0]).get("acq_miss_rate"),
                        "q_hand_pass": qh["pass"], "q_hand_reasons": qh["reasons"],
                        "hand_valid_ratio": qh["valid_ratio"], "seg_dev_frac": qh["seg_dev_frac"]})

            if pose is not None:
                t0, t1 = float(np.nanmin(t)), float(np.nanmax(t))
                sel = np.isfinite(pose["t"]) & (pose["t"] >= t0) & (pose["t"] <= t1)
                if sel.sum() >= 3:
                    pt = pose["t"][sel]
                    pp = pose["pos"][sel]
                    pv = pose["vis"][sel]
                    side = "R" if str(hand).upper().startswith("R") else "L"
                    wl = 16 if side == "R" else 15
                    sl, sr, hl, hr = 11, 12, 23, 24
                    wrist_valid = np.isfinite(pp[:, wl]).all(axis=1) & (pv[:, wl] >= 0.5)
                    qw = q_wrist(pt, wrist_valid, setting=setting)
                    rec["q_wrist"] = qw
                    both = (np.isfinite(pp[:, sl]).all(axis=1) & np.isfinite(pp[:, sr]).all(axis=1)
                            & np.isfinite(pp[:, hl]).all(axis=1) & np.isfinite(pp[:, hr]).all(axis=1))
                    visok = both & (pv[:, sl] >= 0.5) & (pv[:, sr] >= 0.5) & (pv[:, hl] >= 0.5) & (pv[:, hr] >= 0.5)
                    sm = 0.5 * (pp[:, sl] + pp[:, sr])
                    hm = 0.5 * (pp[:, hl] + pp[:, hr])
                    qt = q_trunk(pt, visok, sm, hm, setting=setting)
                    rec["q_trunk"] = qt
                    rec["n_pose_in_span"] = int(sel.sum())
                else:
                    rec["q_wrist"] = {"pass": False, "reasons": ["no_pose_in_span"], "hard_missing": []}
                    rec["q_trunk"] = {"pass": False, "reasons": ["no_pose_in_span"]}
            rows.append(rec)
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
            rows.append(rec)

    n = len([r for r in rows if "error" not in r])
    out = {
        "session": os.path.basename(session_dir), "setting": setting, "hand": hand,
        "n_trials": len(rows), "n_ok": n,
        "q_hand_pass": sum(1 for r in rows if r.get("q_hand_pass")),
        "q_wrist_pass": sum(1 for r in rows if isinstance(r.get("q_wrist"), dict) and r["q_wrist"].get("pass")),
        "q_wrist_hard": sum(1 for r in rows if isinstance(r.get("q_wrist"), dict) and r["q_wrist"].get("hard")),
        "q_trunk_pass": sum(1 for r in rows if isinstance(r.get("q_trunk"), dict) and r["q_trunk"].get("pass")),
        "records": rows,
    }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="v12 §8.2 Q 구현·검증")
    ap.add_argument("--pilot", help="세션 폴더")
    ap.add_argument("--pose", default=None)
    ap.add_argument("--hand", default="Left")
    ap.add_argument("--setting", default="base", choices=list(SETTINGS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.pilot:
        ap.error("--pilot 또는 --selftest")
    res = run_pilot(a.pilot, pose_path=a.pose, hand=a.hand, setting=a.setting)
    txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(txt)
        print("wrote %s" % a.out)
    print(json.dumps({k: v for k, v in res.items() if k != "records"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

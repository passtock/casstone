# -*- coding: utf-8 -*-
"""v11 — 프레임레이트에 견고한 품질 규칙 Q (계획서 v10 §8.2의 P2 문제 해결).

## 해결하는 문제
v10 §8.2는 손목 Q를 **절대 초 단위**로 정의한다.
    `max_gap ≤ 0.10 s`  ·  `interp_frac ≤ 0.10`
파일럿 실측(13.4 fps, 프레임 간격 중앙값 55 ms, 손 추적 100%)에서
**16/16(=100%) 시행이 탈락**했다. 임계가 30 fps(33 ms)를 전제한 값이기 때문이다.
(근거: `experiments/results/v10_wrist_q_audit_pilot.json`)

## 해결 방식
임계를 **관측된 표본 간격(median dt)의 배수**와 **결측률**로 다시 정의한다.

| 새 규칙 | 정의 | fps 의존성 |
|---|---|---|
| `max_gap_ratio` | `max(dt) / median(dt)` | 없음 |
| `missing_frac` | `1 − (관측 표본수−1)/(기대 표본수−1)`, 기대 = `span/median_dt + 1` | 없음 |
| `track_ratio` | 유효 프레임 비율 | 없음 |
| `motion_ratio` | 이동 범위 / 정지 잡음 | 없음 |

`interp_frac`(v10)은 "중앙 dt를 초과한 초과분의 합/구간"이라 **jitter만으로도 커진다**.
`missing_frac`은 "기대 격자 대비 실제로 빠진 표본 수"이므로 jitter와 결측을 구분한다.

## 금지 사항 강제
`calibrate()`는 **추적·운동학 통계만** 받는다. ARAT 점수·VLM 출력 필드가 들어오면 **예외를 던진다**
(계획서 v10 §8.2 "환자 본평가의 점수·VLM 정답률로 최적화하지 않는다").

실행:
  python experiments/v11/qrobust.py --selftest
  python experiments/v11/qrobust.py --audit-series <series.json>      # 구/신 탈락률 비교
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys

import numpy as np

# ---- 새 기본 임계값 (프레임레이트 무관) ----
QROBUST_DEFAULTS = {
    "track_ratio_min": 0.80,       # 유효 프레임 비율
    "max_gap_ratio_max": 2.50,     # max(dt) / median(dt)
    "missing_frac_max": 0.15,      # 기대 격자 대비 결측 비율
    "min_samples": 8,              # 속력/각도 표본 수
    "seg_len_dev_tol": 0.20,       # 정지 기준선 대비 분절 길이 허용 편차
    "seg_len_dev_frac_max": 0.30,  # 그 편차를 넘는 프레임 비율
    "motion_noise_ratio_min": 3.0, # 이동 범위 / 정지 잡음
    "trunk_valid_ratio_min": 0.80,
    "trunk_baseline_sd_mm_max": 10.0,
    "visibility_min": 0.50,
}

# 구(v10 §8.2) 임계값 — 감사 비교용. 초 단위.
QV10_ABSOLUTE = {"gap_max_s": 0.10, "interp_frac_max": 0.10}

# 점수·결과 기반 튜닝 금지를 강제할 때 찾는 필드 이름
FORBIDDEN_FIELDS = ("score", "mae", "arat", "vlm", "pred", "reference", "kappa", "accuracy")


# =====================================================================
# 1. 표본 통계
# =====================================================================
def sampling_stats(t):
    """장치 시간 → 표본 간격 통계.  반환 dict 또는 None."""
    t = np.asarray(t, float)
    t = np.sort(t[np.isfinite(t)])
    if t.size < 3:
        return None
    keep = np.concatenate(([True], np.diff(t) > 0))
    t = t[keep]
    if t.size < 3:
        return None
    dt = np.diff(t)
    med = float(np.median(dt))
    mad = float(np.median(np.abs(dt - med)))
    return {"n": int(t.size), "span_s": float(t[-1] - t[0]), "median_dt_s": med,
            "mad_dt_s": mad, "p95_dt_s": float(np.percentile(dt, 95)),
            "max_dt_s": float(np.max(dt)), "min_dt_s": float(np.min(dt)),
            "fps_effective": (1.0 / med) if med > 0 else None}


def gap_ratio_and_missing(t):
    """max_gap_ratio(무차원)과 missing_frac.  관측된 median dt 기준."""
    st = sampling_stats(t)
    if st is None:
        return None, None, None
    t = np.sort(np.asarray(t, float))
    t = t[np.isfinite(t)]
    span = st["span_s"]
    med = st["median_dt_s"]
    if span <= 0 or med <= 0:
        return None, None, st
    max_gap_ratio = st["max_dt_s"] / med
    expected_n = span / med + 1.0
    observed_n = float(st["n"])
    missing = max(0.0, 1.0 - (observed_n - 1.0) / (expected_n - 1.0)) if expected_n > 1 else 1.0
    return float(max_gap_ratio), float(missing), st


def interp_frac_v10(t):
    """v10 정의: median dt 초과분의 합 / span.  (비교 감사용)"""
    t = np.sort(np.asarray(t, float))
    t = t[np.isfinite(t)]
    if t.size < 3:
        return None
    dt = np.diff(t)
    med = float(np.median(dt))
    span = float(t[-1] - t[0])
    if span <= 0:
        return None
    return float(np.sum(np.maximum(0.0, dt - med)) / span)


# =====================================================================
# 2. 규칙 판정
# =====================================================================
def q_wrist_robust(t, wrist_valid_mask=None, pos=None, q=None, baseline_s=2.0):
    """손목(M4) 품질.  프레임레이트 무관.

    t            : 장치 시간(초) 배열
    wrist_valid  : 유효 표본 불리언(없으면 t 자체를 유효로 간주)
    pos          : (N,3) 손목 3D 좌표(있으면 정지 잡음/이동 범위 계산)
    """
    q = dict(QROBUST_DEFAULTS, **(q or {}))
    t = np.asarray(t, float)
    if wrist_valid_mask is None:
        tm = t[np.isfinite(t)]
    else:
        tm = t[np.asarray(wrist_valid_mask, bool) & np.isfinite(t)]
    gr, miss, st = gap_ratio_and_missing(tm)
    n_samples = 0 if st is None else st["n"]

    motion_ratio, base_noise, motion_range, base_mad_mm_s = None, None, None, None
    if pos is not None and n_samples >= 3:
        p = np.asarray(pos, float)
        keep = np.isfinite(p).all(axis=1)
        p = p[keep]
        tt = np.asarray(t, float)[keep] if np.asarray(t).shape[0] == keep.shape[0] else None
        if p.shape[0] >= 3:
            mdt = st["median_dt_s"]
            grid = np.arange(p.shape[0], dtype=float) * mdt
            speed = np.linalg.norm(np.gradient(p, grid, axis=0), axis=1)
            # 정지 기준선 = 시행 시작 baseline_s 구간 (프로토콜 §6.3 "정지 기준선 2초")
            if tt is not None:
                t0 = float(np.nanmin(tt))
                base_sel = (tt <= t0 + baseline_s)
            else:
                base_sel = np.zeros(p.shape[0], bool)
                base_sel[:max(3, int(round(baseline_s / max(mdt, 1e-9))))] = True
            base = speed[base_sel]
            if base.size == 0:
                base = speed[:max(3, int(round(baseline_s / max(mdt, 1e-9))))]
            base_med = float(np.median(base)) if base.size else 0.0
            base_mad = float(np.median(np.abs(base - base_med))) if base.size else 0.0
            # ★ 대칭 비교: 정지 구간 상위 95% 속력 vs 이동 구간 상위 99% 속력.
            #   MAD는 크기(magnitude) 분포에서 과소평가되므로 상위 분위수를 짝으로 쓴다.
            base_noise = float(np.percentile(base, 95)) if base.size else 0.0
            mov = speed[~base_sel] if (~base_sel).any() else speed
            motion_range = float(np.percentile(mov, 99)) if mov.size else 0.0
            if base_noise <= 1e-9:
                motion_ratio = float("inf") if motion_range > max(1e-6, base_med) else 0.0
            else:
                motion_ratio = motion_range / base_noise
            base_mad_mm_s = base_mad * 1000.0

    checks = {
        "n_samples": (n_samples, ">=", q["min_samples"]),
        "max_gap_ratio": (gr, "<=", q["max_gap_ratio_max"]),
        "missing_frac": (miss, "<=", q["missing_frac_max"]),
        "motion_noise_ratio": (motion_ratio, ">=", q["motion_noise_ratio_min"]),
    }
    reasons = []
    if n_samples < q["min_samples"]:
        reasons.append("insufficient_samples")
    if gr is None:
        reasons.append("no_timeline")
    elif gr > q["max_gap_ratio_max"]:
        reasons.append("gap_ratio_exceeded")
    if miss is not None and miss > q["missing_frac_max"]:
        reasons.append("missing_frames")
    if motion_ratio is not None and motion_ratio < q["motion_noise_ratio_min"]:
        reasons.append("motion_unresolved")
    flags = list(reasons)
    return {"pass": len(reasons) == 0, "reasons": reasons,
            "flags": flags, "motion_unresolved": ("motion_unresolved" in reasons),
            "checks": checks,
            "median_dt_s": None if st is None else st["median_dt_s"],
            "fps_effective": None if st is None else st["fps_effective"],
            "n_samples": n_samples, "max_gap_ratio": gr, "missing_frac": miss,
            "motion_noise_ratio": motion_ratio, "baseline_noise": base_noise,
            "baseline_mad": base_mad_mm_s, "motion_range": motion_range,
            "def_note": "baseline_noise = P95(speed, rest 2s); motion_range = P99(speed, movement)"}


def q_hand_robust(t, valid_mask, seg_len, q=None, baseline_s=2.0):
    """손(M1·M2) 품질."""
    q = dict(QROBUST_DEFAULTS, **(q or {}))
    t = np.asarray(t, float)
    valid_mask = np.asarray(valid_mask, bool)
    track_ratio = float(valid_mask.mean()) if valid_mask.size else 0.0
    n_valid = int(valid_mask.sum())

    gr, miss, st = gap_ratio_and_missing(t[valid_mask])
    seg = np.asarray(seg_len, float)
    seg_ok = np.isfinite(seg)
    base_mask = (t <= (t[0] + baseline_s)) & seg_ok if t.size else np.zeros(0, bool)
    if base_mask.sum() >= 3:
        base = float(np.median(seg[base_mask]))
        with np.errstate(invalid="ignore"):
            rel = np.abs(seg - base) / base if base > 0 else np.full_like(seg, np.inf)
        dev_frac = float(np.mean(rel[seg_ok] > q["seg_len_dev_tol"]))
        base_ok = True
    else:
        base, dev_frac, base_ok = None, 1.0, False

    reasons = []
    if track_ratio < q["track_ratio_min"]:
        reasons.append("low_tracking")
    if n_valid < q["min_samples"]:
        reasons.append("insufficient_frames")
    if gr is not None and gr > q["max_gap_ratio_max"]:
        reasons.append("gap_ratio_exceeded")
    if not base_ok:
        reasons.append("no_baseline")
    elif dev_frac > q["seg_len_dev_frac_max"]:
        reasons.append("segment_length_unstable")
    return {"pass": len(reasons) == 0, "reasons": reasons,
            "track_ratio": track_ratio, "n_valid_frames": n_valid,
            "max_gap_ratio": gr, "missing_frac": miss,
            "seg_len_baseline_mm": None if base is None else base * 1000.0,
            "seg_len_dev_frac": dev_frac, "baseline_available": base_ok,
            "median_dt_s": None if st is None else st["median_dt_s"]}


def q_trunk_robust(t, valid_mask, shoulder_mid, hip_mid, q=None, baseline_s=2.0):
    """체간(M5) 품질.  축이 필요 없다(lean 정의)."""
    q = dict(QROBUST_DEFAULTS, **(q or {}))
    t = np.asarray(t, float)
    valid_mask = np.asarray(valid_mask, bool)
    valid_ratio = float(valid_mask.mean()) if valid_mask.size else 0.0
    sm = np.asarray(shoulder_mid, float)
    hm = np.asarray(hip_mid, float)
    d = sm - hm
    # MediaPipe Pose world landmark: 수직축 = y  → 수평면 = (x, z)
    horiz = np.linalg.norm(d[:, [0, 2]], axis=1) if d.ndim == 2 else np.array([])
    finite = np.isfinite(horiz)
    base_mask = (t <= (t[0] + baseline_s)) & finite if t.size else np.zeros(0, bool)
    base_sd_mm = None
    if base_mask.sum() >= 3:
        base_sd_mm = float(np.std(horiz[base_mask])) * 1000.0
    reasons = []
    if valid_ratio < q["trunk_valid_ratio_min"]:
        reasons.append("low_trunk_visibility")
    if base_sd_mm is None:
        reasons.append("no_trunk_baseline")
    elif base_sd_mm > q["trunk_baseline_sd_mm_max"]:
        reasons.append("unstable_trunk_baseline")
    return {"pass": len(reasons) == 0, "reasons": reasons, "valid_ratio": valid_ratio,
            "baseline_sd_mm": base_sd_mm}


# =====================================================================
# 3. 감사: 구(v10 절대초) vs 신(dt 상대)
# =====================================================================
def audit_record(t, q=None):
    """한 시행의 구/신 판정을 함께 낸다."""
    t = np.asarray(t, float)
    t = t[np.isfinite(t)]
    gr, miss, st = gap_ratio_and_missing(t)
    if st is None:
        return None
    ifr = interp_frac_v10(t)
    n = st["n"]
    old_pass = (st["max_dt_s"] <= QV10_ABSOLUTE["gap_max_s"] + 1e-12
                and (ifr is not None and ifr <= QV10_ABSOLUTE["interp_frac_max"])
                and n >= 8)
    new = q_wrist_robust(t, q=q)
    return {
        "fps_effective": st["fps_effective"], "median_dt_s": st["median_dt_s"],
        "max_dt_s": st["max_dt_s"], "ifr_v10": ifr, "max_gap_ratio": gr,
        "missing_frac": miss, "old_pass": bool(old_pass), "new_pass": bool(new["pass"]),
        "new_reasons": new["reasons"],
    }


def audit(records, q=None):
    recs = [r for r in (audit_record(r["t"], q=q) for r in records) if r]
    if not recs:
        return {"n": 0}
    old = sum(1 for r in recs if r["old_pass"]) / len(recs)
    new = sum(1 for r in recs if r["new_pass"]) / len(recs)
    return {"n": len(recs), "old_reject_rate": 1.0 - old, "new_reject_rate": 1.0 - new,
            "old_pass_rate": old, "new_pass_rate": new,
            "fps_effective": sorted({round(r["fps_effective"], 2) for r in recs}),
            "records": recs}


# =====================================================================
# 4. 보정 (점수·결과 사용 금지 강제)
# =====================================================================
def _reject_forbidden(records):
    for r in records:
        for k in r.keys():
            for bad in FORBIDDEN_FIELDS:
                if bad in str(k).lower():
                    raise ValueError(
                        "보정 입력에 결과 필드 '%s'가 있다. Q 보정은 추적·운동학 통계만 사용해야 한다"
                        "(계획서 v10 §8.2)." % k)


def calibrate(records, target_low=0.05, target_high=0.30,
              gap_grid=(1.5, 2.0, 2.5, 3.0, 4.0, 6.0),
              miss_grid=(0.05, 0.10, 0.15, 0.25, 0.40)):
    """추적 통계만으로 (max_gap_ratio, missing_frac) 임계를 고른다.

    목표: 탈락률이 [target_low, target_high] 안에 들어오는 조합 중
          **가장 엄격한**(작은) 임계를 고른다. 없으면 가장 가까운 조합.
    """
    _reject_forbidden(records)
    ts = [np.asarray(r["t"], float) for r in records if r.get("t") is not None]
    ts = [t[np.isfinite(t)] for t in ts if np.isfinite(t).sum() >= 3]
    if not ts:
        return None
    stats = []
    for t in ts:
        gr, miss, st = gap_ratio_and_missing(t)
        if st is not None:
            stats.append((gr, miss, st["n"]))
    best = None
    for g in sorted(gap_grid):
        for m in sorted(miss_grid):
            rej = sum(1 for gr, miss, n in stats if (gr > g) or (miss > m) or n < 8) / len(stats)
            in_band = target_low <= rej <= target_high
            if in_band:
                dist = 0.0
            elif rej < target_low:
                dist = target_low - rej
            else:
                dist = rej - target_high
            # 1순위 대역 내, 2순위 대역까지 거리, 3순위 더 엄격한 임계
            cand = (0 if in_band else 1, round(dist, 6), g + m, g, m, rej)
            if best is None or cand < best:
                best = cand
    _, _, _, g, m, rej = best
    return {"max_gap_ratio_max": g, "missing_frac_max": m,
            "calibration_reject_rate": rej,
            "in_target_band": bool(target_low <= rej <= target_high),
            "target_band": [target_low, target_high], "n_records": len(stats),
            "note": "추적 통계만 사용. ARAT 점수·VLM 출력 미사용."}


# =====================================================================
# 5. 오라클
# =====================================================================
def _synth_times(fps, dur_s, drop_idx=(), jitter=0.15, seed=1):
    """fps로 균일 샘플링 + jitter. drop_idx 위치 프레임을 제거."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * fps)
    dt = 1.0 / fps
    t = np.arange(n) * dt
    t = t + rng.normal(0, jitter * dt, n)
    t = np.sort(t)
    mask = np.ones(n, bool)
    for i in drop_idx:
        if 0 <= i < n:
            mask[i] = False
    return t[mask]


def selftest():
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    # (1) 핵심 회귀: 같은 내용이 fps만 다를 때 판정이 같아야 한다
    t134 = _synth_times(13.4, 10.0, seed=11)
    t300 = _synth_times(30.0, 10.0, seed=11)
    st134 = sampling_stats(t134)
    chk("표본통계: 13.4fps median_dt≈0.075s", abs(st134["median_dt_s"] - 1 / 13.4) < 0.01,
        "%.4f s (fps_eff %.1f)" % (st134["median_dt_s"], st134["fps_effective"]))
    q134 = q_wrist_robust(t134)
    q300 = q_wrist_robust(t300)
    chk("★ 신규칙: 13.4fps 결측없음 → 통과", q134["pass"] is True, str(q134["reasons"]))
    chk("★ 신규칙: 30.0fps 결측없음 → 통과", q300["pass"] is True, str(q300["reasons"]))
    chk("★ fps 무관 일관성", q134["pass"] == q300["pass"])
    a134 = audit_record(t134)
    a300 = audit_record(t300)
    chk("★ 구규칙: 13.4fps 결측없음 → 탈락(문제 재현)", a134["old_pass"] is False,
        "max_dt=%.3f ifr=%.3f" % (a134["max_dt_s"], a134["ifr_v10"]))
    chk("★ 구규칙: 30.0fps 결측없음 → 통과", a300["old_pass"] is True,
        "max_dt=%.3f ifr=%.3f" % (a300["max_dt_s"], a300["ifr_v10"]))

    # (2) 실제 결측은 잡아야 한다
    t_drop = _synth_times(13.4, 10.0, drop_idx=range(40, 60), seed=3)  # 20프레임 낙하
    qd = q_wrist_robust(t_drop)
    chk("결측 20프레임 → 탈락", qd["pass"] is False, str(qd["reasons"]))
    chk("결측 사유에 gap/missing 포함",
        any(r in ("gap_ratio_exceeded", "missing_frames") for r in qd["reasons"]), str(qd["reasons"]))

    # (3) dt 상대성: 임계가 dt 배수임을 수치로 확인
    gr, miss, _ = gap_ratio_and_missing(t134)
    chk("max_gap_ratio 는 dt 배수(무차원)", gr is not None and gr < 2.5, "%.3f" % gr)
    chk("결측 없는 13.4fps → missing_frac ≈ 0", miss is not None and miss <= 0.05, "%.4f" % miss)

    # (4) 보정: 점수 필드가 있으면 예외
    raised = False
    try:
        calibrate([{"t": t134, "score": 3}])
    except ValueError:
        raised = True
    chk("★ 보정이 결과 필드를 거부", raised is True)

    # (5) 보정이 목표 대역에서 임계를 고른다
    recs = [{"t": _synth_times(13.4, 8.0, seed=i)} for i in range(22)]
    recs += [{"t": _synth_times(13.4, 8.0, drop_idx=range(30, 60), seed=100 + i)} for i in range(4)]
    cal = calibrate(recs, target_low=0.05, target_high=0.25)
    chk("보정: 탈락률이 목표 대역", cal is not None and cal["in_target_band"] is True,
        None if cal is None else "rej=%.2f g=%s m=%s" % (cal["calibration_reject_rate"], cal["max_gap_ratio_max"], cal["missing_frac_max"]))
    cal2 = calibrate(recs, None) if False else calibrate(recs)
    chk("보정: 결과 반환 키", set(["max_gap_ratio_max", "missing_frac_max", "calibration_reject_rate"]) <= set(cal2 or {}))

    # (6) 감사 요약
    au = audit([{"t": t134}, {"t": t300}, {"t": t_drop}])
    chk("감사: 구 탈락률 > 신 탈락률", au["old_reject_rate"] > au["new_reject_rate"],
        "old=%.2f new=%.2f" % (au["old_reject_rate"], au["new_reject_rate"]))

    # (7) 손목 정지 잡음 — 정지 2초 → 이동
    tt = _synth_times(13.4, 8.0, jitter=0.05, seed=5)
    rng = np.random.default_rng(9)
    def _rest_then_pos(t, move_amp_m):
        p = np.zeros((t.size, 3))
        for i, ti in enumerate(t):
            if ti > 2.0:                      # 정지 2초 이후 이동
                p[i, 0] = move_amp_m * np.sin(2 * np.pi * 1.0 * (ti - 2.0))
        p += rng.normal(0, 0.0005, p.shape)   # 0.5 mm 추적 잡음
        return p
    q_tiny = q_wrist_robust(tt, pos=_rest_then_pos(tt, 0.0002))   # 0.2 mm 이동(잡음 0.5mm 이하)
    q_small = q_wrist_robust(tt, pos=_rest_then_pos(tt, 0.005))   # 5 mm 이동
    q_big = q_wrist_robust(tt, pos=_rest_then_pos(tt, 0.20))      # 20 cm 이동
    chk("정지 대비 0.2mm 이동 → motion_unresolved",
        "motion_unresolved" in q_tiny["reasons"] and q_tiny["motion_unresolved"] is True,
        "ratio=%.2f %s" % (q_tiny["motion_noise_ratio"] or -1, q_tiny["reasons"]))
    chk("정지 대비 5mm 이동 → 통과(노이즈보다 구분됨)", q_small["pass"] is True,
        "ratio=%.1f" % (q_small["motion_noise_ratio"] or -1))
    chk("정지 대비 20cm 이동 → 통과", q_big["pass"] is True,
        "ratio=%.1f" % (q_big["motion_noise_ratio"] or -1))
    chk("★ 이동/잡음 비 단조 증가", (q_tiny["motion_noise_ratio"] < q_small["motion_noise_ratio"]
        < q_big["motion_noise_ratio"]),
        "%.2f < %.1f < %.1f" % (q_tiny["motion_noise_ratio"], q_small["motion_noise_ratio"], q_big["motion_noise_ratio"]))
    chk("motion_unresolved 는 reasons 와 flags 양쪽에 노출",
        q_tiny["motion_unresolved"] is True and "motion_unresolved" in q_tiny["flags"])

    print("=" * 72)
    print("qrobust 오라클 (v11)")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="v11 프레임레이트 견고 Q")
    ap.add_argument("--series", help="series.json: [{'t':[...]}, ...]")
    ap.add_argument("--calibrate", action="store_true", help="--series 로 임계 보정")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.series:
        ap.error("--series 또는 --selftest 필요")
    recs = json.load(io.open(a.series, encoding="utf-8"))
    res = calibrate(recs) if a.calibrate else audit(recs)
    txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(txt)
        print("wrote %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

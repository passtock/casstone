# -*- coding: utf-8 -*-
"""v13 §8.2 · §21 규칙 구현 + 오라클.

v13에서 바뀐 것만 새로 구현하고, 바뀌지 않은 시간축·손목·체간 규칙은 v12 구현을 import 해 재사용한다.
(v12 코드는 수정하지 않는다.)

v13 조항 → 코드 대응
  §8.2-1  `dt_ref`는 세션당 1회 → 전 지표 공통            → `session_dt_ref()`
  §8.2 손 분절  `tol_seg = max(0.20, 3×MAD)`             → `segment_tolerances()`
  §8.2 손 분절  불일치 프레임 = "2개 이상 동시 위반"          → `segment_frame_flags()`
  §8.2 손 분절  분모 = 검사 가능한 프레임 수                 → 위 함수의 `denom_frames`
  §8.2 손 분절  기준선 = 정지 2초, <8프레임이면 판단 불가      → `evaluate_segment_rule()`
  §8.2 손 분절  상한 = 개발군 90백분위(잠정 30%)            → `calibrate_cap()`
  §8.2 손 행    연속 미검출 ≤ 5×dt_ref                    → `hand_q_v13()`
  §8.2 손-일관성 손목–(8)·(12) 거리 [60,230]mm 밖 → 프레임 무효 → `hand_consistency()`
  §8.2 손 분절  위반 횟수·위반 분절 이름 기록                → `per_segment_counts`
  §8.2          보류율 >50% → 손 지표 조건부 강등           → `demotion_decision()`
  §21           분모·dt_ref·tol·손-일관성 구현 기준 준수      → 오라클에서 검사

실행:
  python experiments/v13/qv13.py --selftest
  python experiments/v13/qv13.py --pilot "<session>" --pose "<pose.csv>" --rest-mode fallback
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "v12"))
from qv12 import (  # noqa: E402  (v12 구현 재사용 — 수정하지 않음)
    SEGMENTS_15, SEGMENTS_TI, SETTINGS, MIN_OBS, GAP_ABS_MAX_S, FS_FLOOR_HZ,
    acquisition_missing, dt_ref_of, effective_rate, gaps_and_interp,
    q_trunk, q_wrist,
)

# ---------------- v13 상수 (문서 값) ----------------
TOL_FLOOR = 0.20          # §8.2 하한
K_TOL = 3.0               # §8.2 K_tol
MIN_SEG_AGREE = 2         # §8.2 "2개 이상 동시 위반"
CAP_DEFAULT = 0.30        # §8.2 개발군 측정 전 잠정 상한
CAP_PERCENTILE = 0.90     # §8.2 개발군 90백분위
MIN_REST_FRAMES = 8       # §8.2 정지 기준선 최소 유효 프레임
GAP_FACTOR_DTREF = 5.0    # §8.2 손 행 "연속 미검출 ≤ 5 × dt_ref"
TRACK_MIN = 0.80          # §8.2 손 행 추적률 하한
HC_MM = (60.0, 230.0)     # §8.2 손-일관성 범위
RS_IMPLAUSIBLE_SPAN_MM = 260.0   # 앱 사실값(별개 규칙, 병기용)

HAND_TI_SEGS = SEGMENTS_TI            # 엄지·검지 6분절 → D_TI_max
HAND_ALL_SEGS = SEGMENTS_15           # 15분절 → F_sum14

FORBIDDEN = ("score", "mae", "arat", "vlm", "pred", "kappa", "accuracy", "reference")


# =====================================================================
# §8.2-1  세션 공통 dt_ref
# =====================================================================
def session_dt_ref(frame_ids, times):
    """세션 원시 프레임의 양의 시간차 중앙값. 프레임 ID로 중복 제거 후 계산.

    §8.2-1: 세션당 1회 계산해 그 세션의 모든 과제·모든 지표에 공통 적용한다.
    """
    fid = np.asarray(frame_ids, dtype=float)
    t = np.asarray(times, dtype=float)
    ok = np.isfinite(fid) & np.isfinite(t)
    fid, t = fid[ok], t[ok]
    if t.size < 3:
        return None, 0
    order = np.argsort(fid, kind="stable")
    fid, t = fid[order], t[order]
    keep = np.concatenate(([True], np.diff(fid) > 0))
    fid, t = fid[keep], t[keep]
    med, _ = dt_ref_of(t)
    return med, int(t.size)


# =====================================================================
# §8.2  분절별 허용오차
# =====================================================================
def _seg_len(P, seg):
    i, j = seg
    return np.linalg.norm(P[:, i] - P[:, j], axis=-1)


def segment_tolerances(dev_trials, segments=HAND_ALL_SEGS, k_tol=K_TOL, floor=TOL_FLOOR):
    """개발군에서 분절별 허용오차를 정한다.

    s_seg = 1.4826 × MAD(분절 길이 ÷ 그 분절의 기준 길이), tol_seg = max(floor, k_tol × s_seg)
    §8.2: 개발군의 **동작 구간을 포함한 전체 시행**에서 계산한다(정지 구간만으로 추정하지 않는다).
    결과 필드는 분절 쌍 → dict(tol, s_seg, n, base_len_mm).
    """
    _reject_forbidden(dev_trials)
    out = {}
    for seg in segments:
        rel_mads, base_lens, n = [], [], 0
        for P in dev_trials:
            P = np.asarray(P, float)
            if P.ndim != 3 or P.shape[1] < 21:
                continue
            d = _seg_len(P, seg)
            b = float(np.nanmedian(d))
            if not np.isfinite(b) or b <= 0:
                continue
            mad = float(np.nanmedian(np.abs(d - b)))
            rel_mads.append(mad / b)
            base_lens.append(b * 1000.0)
            n += int(np.isfinite(d).sum())
        if not rel_mads:
            out[seg] = {"tol": floor, "s_seg": None, "n": 0, "base_len_mm": None}
            continue
        s = 1.4826 * float(np.median(rel_mads))
        out[seg] = {"tol": max(floor, k_tol * s), "s_seg": s, "n": n,
                    "base_len_mm": float(np.median(base_lens))}
    return out


def _reject_forbidden(records):
    """§8.2: 임계값을 환자 ARAT 점수·VLM 정답률로 고르지 않는다 — 코드로 강제."""
    for r in records:
        keys = r.keys() if hasattr(r, "keys") else []
        for k in keys:
            for bad in FORBIDDEN:
                if bad in str(k).lower():
                    raise ValueError("보정 입력에 결과 필드 '%s'가 있다. 개발군 추적·운동학 통계만 써야 한다"
                                     "(v13 §8.2)." % k)


# =====================================================================
# §8.2  분절 불일치 프레임 (2개 이상 동시 위반)
# =====================================================================
def segment_frame_flags(P, t, tol_map, segments=HAND_ALL_SEGS, rest=None,
                        rest_window_s=2.0, min_rest_frames=MIN_REST_FRAMES,
                        min_agree=MIN_SEG_AGREE, rest_matrix=None):
    """프레임별 분절 불일치 판정.

    rest: 불리언 배열(정지 2초 구간). None 이면 `rest_window_s` 로 앞에서 잘라 쓴다(진단용).
    rest_matrix: 이미 계산된 정지 구간 유효 마스크(선택).

    반환 dict:
      flags           (F,) bool   최종 불일치 프레임
      denom_frames    int         **검사 가능한 프레임 수**(프레임 × 분절 쌍이 아니다)
      per_segment     {seg: 위반 프레임 수}
      violating_names 위반이 1회 이상 있었던 분절 이름
      rest_ok         bool / reason
      viol_counts     (F,) int    프레임별 동시 위반 분절 수
      pair_denom      int         (참고·비교용) 프레임 × 분절 쌍 수
    """
    P = np.asarray(P, float)
    t = np.asarray(t, float)
    F = P.shape[0]
    base_sel = rest if rest is not None else (t <= (t[0] + rest_window_s))
    base_sel = np.asarray(base_sel, bool)
    viol = np.zeros((len(segments), F), bool)
    checkable = np.zeros(F, bool)
    per_seg = {}
    n_rest_ok = 0
    for k, seg in enumerate(segments):
        d = _seg_len(P, seg)
        bsel = base_sel & np.isfinite(d)
        base_n = int(bsel.sum())
        if base_n < min_rest_frames:
            per_seg[seg] = None
            continue
        b = float(np.median(d[bsel]))
        if not np.isfinite(b) or b <= 0:
            per_seg[seg] = None
            continue
        n_rest_ok += 1
        rel = np.abs(d - b) / b
        ok = np.isfinite(rel)
        tol = tol_map.get(seg, {}).get("tol", TOL_FLOOR) if isinstance(tol_map.get(seg), dict) \
            else tol_map.get(seg, TOL_FLOOR)
        viol[k] = ok & (rel > tol)
        checkable |= ok
        per_seg[seg] = int(viol[k].sum())
    viol_counts = viol.sum(axis=0)
    flags = checkable & (viol_counts >= min_agree)
    if n_rest_ok == 0:
        rest_ok, reason = False, "segment_baseline_unavailable"
    else:
        rest_ok, reason = True, "ok"
    names = [nm(segments[k]) for k in range(len(segments))
             if per_seg.get(segments[k]) not in (None, 0)]
    return {"flags": flags, "denom_frames": int(checkable.sum()),
            "per_segment": {nm(s): per_seg[s] for s in segments},
            "violating_names": names, "rest_ok": rest_ok, "reason": reason,
            "viol_counts": viol_counts.astype(int),
            "pair_denom": int(checkable.sum() * len(segments)),
            "n_segments_with_baseline": n_rest_ok}


_NAMES = {(1, 2): "Th(1-2)", (2, 3): "Th(2-3)", (3, 4): "Th(3-4)",
          (5, 6): "In(5-6)", (6, 7): "In(6-7)", (7, 8): "In(7-8)",
          (9, 10): "Md(9-10)", (10, 11): "Md(10-11)", (11, 12): "Md(11-12)",
          (13, 14): "Rg(13-14)", (14, 15): "Rg(14-15)", (15, 16): "Rg(15-16)",
          (17, 18): "Pk(17-18)", (18, 19): "Pk(18-19)", (19, 20): "Pk(19-20)"}


def nm(seg):
    return _NAMES.get(seg, str(seg))


# =====================================================================
# 랜드마크 커버리지 진단 (v13 규칙의 알려진 맹점을 기계적으로 드러낸다)
#   v13 검토(2026-10-02 2차): "2개 이상" 조건은 **분절 2개 이상에 속한 랜드마크**만 잡는다.
#   손끝(4,8,12,16,20)과 기저(1,5,9,13,17)는 분절 1개뿐이므로 이 조건으로는 잡히지 않는다.
# =====================================================================
def landmark_coverage(consistency_tips=(8, 12), min_agree=MIN_SEG_AGREE,
                      app_span_tips=(4, 8, 12, 16, 20)):
    """랜드마크별로 **v13 게이트**가 잡는지, 그리고 비게이트 보완이 있는지 계산한다.

    v13 §8.2의 손 게이트는 두 가지다.
      (1) 분절 규칙: 분절 2개 이상에 속한 랜드마크만 "2개 이상 동시 위반"으로 잡힌다.
      (2) 손-일관성: 손목(0)→검지끝(8)·중지끝(12) 거리 [60,230] mm.
    `implausible_span`(앱, 최대 span 260 mm)은 v13 손 게이트가 **아니다**(병기·진단용).
    """
    import collections
    cnt = collections.Counter()
    for (i, j) in SEGMENTS_15:
        cnt[i] += 1
        cnt[j] += 1
    rows = {}
    for k in range(21):
        gate = bool(cnt[k] >= min_agree) or (k in consistency_tips)
        rows[k] = {
            "n_segments": cnt[k],
            "by_segment_rule": bool(cnt[k] >= min_agree),
            "by_hand_consistency": k in consistency_tips,
            "by_app_implausible_span_NOT_A_GATE": k in app_span_tips,
            "covered_by_gate": gate,
        }
    uncovered_gate = sorted(k for k, v in rows.items() if not v["covered_by_gate"])
    uncovered_no_aux = sorted(k for k, v in rows.items()
                              if not v["covered_by_gate"] and not v["by_app_implausible_span_NOT_A_GATE"])
    return {"per_landmark": rows,
            "uncovered_by_gate": uncovered_gate,
            "uncovered_without_aux": uncovered_no_aux,
            "uncovered_gate_tips": [k for k in uncovered_gate if k in (4, 8, 12, 16, 20)],
            "note": ("v13 게이트가 잡지 못하는 랜드마크: %s. 그중 손끝: %s. "
                     "엄지끝 4는 D_TI_max의 정의 랜드마크이며 게이트 밖이다. "
                     "앱 `implausible_span`(260mm)은 비게이트 보완(큰 이탈만 잡음)."
                     % (uncovered_gate, [k for k in uncovered_gate if k in (4, 8, 12, 16, 20)]))}


# =====================================================================
# §8.2  손-일관성 (프레임 무효 조건)
# =====================================================================
def hand_consistency(P, lo=HC_MM[0], hi=HC_MM[1]):
    """손목(0)–검지끝(8)·중지끝(12) world 3D 거리 ∈ [lo, hi] mm 를 벗어나면 그 프레임 무효.

    앱의 `implausible_span`(최대 span 260mm)과 **별개 규칙**이다. 두 판정을 모두 기록한다.
    """
    P = np.asarray(P, float)
    F = P.shape[0]
    out = {"valid": np.zeros(F, bool), "d_index_mm": np.full(F, np.nan),
           "d_middle_mm": np.full(F, np.nan), "status": np.full(F, "", dtype=object),
           "n_invalid": 0, "n_invalid_range": 0, "n_invalid_nan": 0}
    if F == 0:
        return out
    w = P[:, 0]
    for tip, key in ((8, "d_index_mm"), (12, "d_middle_mm")):
        d = np.linalg.norm(P[:, tip] - w, axis=-1) * 1000.0
        out[key] = d
    di, dm = out["d_index_mm"], out["d_middle_mm"]
    finite = np.isfinite(di) & np.isfinite(dm)
    inrange = finite & (di >= lo) & (di <= hi) & (dm >= lo) & (dm <= hi)
    out["valid"] = inrange
    out["status"][~finite] = "landmark_missing"
    out["status"][finite & ~inrange] = "hand_consistency_range"
    out["status"][inrange] = "ok"
    out["n_invalid"] = int((~inrange).sum())
    out["n_invalid_range"] = int((finite & ~inrange).sum())
    out["n_invalid_nan"] = int((~finite).sum())
    # 앱 규칙 병기(별개): 손목–손끝 최대 span > 260mm
    spans = np.nanmax(np.stack([np.linalg.norm(P[:, k] - w, axis=-1) * 1000.0
                                for k in (4, 8, 12, 16, 20)], axis=1), axis=1)
    out["implausible_span"] = np.isfinite(spans) & (spans > RS_IMPLAUSIBLE_SPAN_MM)
    out["n_implausible_span"] = int(out["implausible_span"].sum())
    return out


# =====================================================================
# §8.2 손 Q (v13)
# =====================================================================
def hand_q_v13(P, t, dt_ref_session, tol_map, rest=None, segments=HAND_ALL_SEGS,
               cap=None, setting="base", rest_window_s=2.0, cap_source=None):
    """cap=None 이면 §8.2 세 설정표의 `seg_dev_max`(40/30/20%)를 쓴다.
    개발군에서 확정한 상한이 있으면 그 값을 넘겨 덮어쓴다(§8.2 "상한은 개발군에서 확정")."""
    S = SETTINGS[setting]
    if cap is None:
        cap = S["seg_dev_max"]
        cap_source = cap_source or ("setting:%s.seg_dev_max" % setting)
    else:
        cap_source = cap_source or "explicit"
    P = np.asarray(P, float)
    t = np.asarray(t, float)
    cons = hand_consistency(P)
    finite_tip = np.isfinite(P[:, 4, 0]) & np.isfinite(P[:, 8, 0])
    valid = finite_tip & cons["valid"]
    track_ratio = float(valid.mean()) if valid.size else 0.0
    n_valid = int(valid.sum())

    # 연속 미검출 (≤ 5 × dt_ref, 세션 기준)
    limit = GAP_FACTOR_DTREF * (dt_ref_session or 0.0)
    longest = 0.0
    run = None
    for i in range(valid.size):
        if not valid[i]:
            if run is None:
                run = i
        else:
            if run is not None:
                longest = max(longest, float(t[i] - t[run]))
                run = None
    if run is not None:
        longest = max(longest, float(t[-1] - t[run]) if t.size else 0.0)

    seg = evaluate_segment_rule(P, t, tol_map, segments=segments, rest=rest,
                                min_agree=MIN_SEG_AGREE, rest_window_s=rest_window_s)
    reasons, gaps = [], []
    if track_ratio < TRACK_MIN:
        reasons.append("low_tracking")
    if limit > 0 and longest > limit:
        reasons.append("hand_gap_over_5x_dt_ref")
    if n_valid < MIN_OBS:
        reasons.append("insufficient_frames")
    # §8.2: 손-일관성 밖 프레임은 '무효'(valid 에서 제외)이며 그 자체로 보류 사유가 아니다.
    #       무효 프레임 수·비율은 기록·보고만 한다.
    if not seg["rest_ok"]:
        reasons.append("segment_baseline_unavailable")
    else:
        denom = max(seg["denom_frames"], 1)
        rate = seg["flags"].sum() / denom
        if rate > cap:
            reasons.append("segment_deviation_over_cap")
    hard = []
    if not seg["rest_ok"]:
        hard.append("segment_baseline_unavailable")
    return {
        "pass": len(reasons) == 0, "reasons": reasons, "hard_missing": hard,
        "setting": setting, "track_ratio": track_ratio, "n_valid": n_valid,
        "longest_gap_s": longest, "gap_limit_s": limit, "dt_ref_session_s": dt_ref_session,
        "segment": seg, "consistency": {k: v for k, v in cons.items() if not isinstance(v, np.ndarray)},
        "seg_rate": (seg["flags"].sum() / max(seg["denom_frames"], 1)) if seg["rest_ok"] else None,
        "cap": cap, "cap_source": cap_source,
        "settings_keys_used": {"seg_dev_max": S["seg_dev_max"], "valid_min": S["valid_min"]},
    }


def evaluate_segment_rule(P, t, tol_map, segments=HAND_ALL_SEGS, rest=None,
                          min_agree=MIN_SEG_AGREE, rest_window_s=2.0):
    return segment_frame_flags(P, t, tol_map, segments=segments, rest=rest,
                               rest_window_s=rest_window_s, min_agree=min_agree)


# =====================================================================
# §8.2  상한 보정(개발군) · 강등 판정
# =====================================================================
def calibrate_cap(dev_rates, percentile=CAP_PERCENTILE, floor_cap=None):
    """개발군의 프레임 불일치율 분포에서 상한을 정한다(기본 90백분위)."""
    rates = [float(r) for r in dev_rates if r is not None and np.isfinite(r)]
    if not rates:
        return {"cap": CAP_DEFAULT, "n": 0, "provisional": True,
                "note": "개발군 측정 없음 → 잠정 30%"}
    c = float(np.percentile(rates, percentile * 100.0))
    if floor_cap is not None:
        c = max(c, floor_cap)
    return {"cap": c, "n": len(rates), "percentile": percentile, "provisional": False,
            "dev_rates": sorted(rates),
            "note": "개발군 %d건의 %.0f백분위. 환자 ARAT 점수·VLM 출력 미사용." % (len(rates), percentile * 100)}


def demotion_decision(hold_rate_by_task, threshold=0.50, source=None,
                      include_not_evaluable=None):
    """§8.2: **개발군**에서 **T1·T2별** 손 지표 보류율이 50%를 넘으면 조건부 입력으로 강등.

    source 가 "dev_group" 이 아니면 `diagnostic_only=True` 로 표시한다.
    (파일럿·진단용 기준선에서 얻은 보류율을 §8.2 강등 판정으로 오인하지 않게 하기 위함)
    """
    over = {k: v for k, v in hold_rate_by_task.items() if v is not None and v > threshold}
    dev = (source == "dev_group")
    return {"demote": bool(over) if dev else None,
            "diagnostic_only": (not dev),
            "source": source, "threshold": threshold, "over": over,
            "include_not_evaluable": include_not_evaluable,
            "note": ("§8.2 강등 판정은 개발군·T1·T2별 보류율로만 한다. 그 밖은 관찰값이다."
                     if not dev else "개발군 판정"),
            "action": (("D_TI_max·F_sum14를 A3의 조건부 입력으로 강등" if over else "주 입력 유지")
                       if dev else "판정 보류(진단용 관측)")}


# =====================================================================
# 오라클
# =====================================================================
def _synth_hand(F=150, fps=13.4, seed=1, noise_mm=(0.4, 0.4), seg="In(5-6)") -> tuple:
    """합성 손: 손가락 체인이 일직선이고 분절 길이가 일정. noise_mm=(기준, 특정분절 추가)"""
    rng = np.random.default_rng(seed)
    t = np.arange(F) / fps
    P = np.zeros((F, 21, 3))
    xs = {0: 0.000, 1: 0.010, 2: 0.020, 3: 0.030, 4: 0.080,
          5: 0.020, 6: 0.040, 7: 0.060, 8: 0.080,
          9: 0.020, 10: 0.040, 11: 0.060, 12: 0.080,
          13: 0.020, 14: 0.040, 15: 0.060, 16: 0.080,
          17: 0.020, 18: 0.040, 19: 0.060, 20: 0.080}
    scale = noise_mm[0] / 1000.0
    for j, x in xs.items():
        P[:, j, 0] = x + rng.normal(0, scale, F)
        P[:, j, 1] = rng.normal(0, scale, F)
        P[:, j, 2] = 0.30 + rng.normal(0, scale, F)
    # 특정 분절에 추가 잡음(추정 실패 모사)
    if seg == "In(5-6)":
        extra = noise_mm[1] / 1000.0
        P[:, 6, 0] = xs[6] + rng.normal(0, extra, F)
        P[:, 6, 1] = rng.normal(0, extra, F)
    return P, t


def _flat_tols(segments=HAND_ALL_SEGS, tol=TOL_FLOOR):
    return {s: {"tol": tol, "s_seg": None, "n": 0, "base_len_mm": None} for s in segments}


def selftest():
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    # ---- §8.2-1 dt_ref 세션 공통 ----
    fid = np.repeat(np.arange(100), 2)
    tt = np.repeat(np.arange(100) * 0.0553, 2)
    d, n = session_dt_ref(fid, tt)
    chk("§8.2-1 세션 dt_ref = 중복 제거 후 중앙 간격", abs(d - 0.0553) < 1e-6 and n == 100,
        "dt_ref=%.4f n=%d" % (d, n))

    # ---- §8.2 분절별 허용오차 ----
    devs = []
    for s in range(4):
        P, _ = _synth_hand(F=120, seed=10 + s, noise_mm=(0.4, 2.5))
        devs.append(P)
    tol = segment_tolerances(devs)
    chk("§8.2 tol_seg 하한 0.20 적용", tol[(9, 10)]["tol"] >= 0.20 - 1e-12,
        "tol(Md9-10)=%.3f" % tol[(9, 10)]["tol"])
    chk("§8.2 시끄러운 분절의 tol 이 하한보다 큼",
        tol[(5, 6)]["tol"] > 0.20 and tol[(5, 6)]["s_seg"] > tol[(9, 10)]["s_seg"],
        "tol(In5-6)=%.3f s=%.3f / tol(Md9-10)=%.3f s=%.3f" % (
            tol[(5, 6)]["tol"], tol[(5, 6)]["s_seg"], tol[(9, 10)]["tol"], tol[(9, 10)]["s_seg"]))

    # ---- ★ 2개 이상 동시 위반 ----
    P1, t1 = _synth_hand(F=150, seed=5, noise_mm=(0.3, 3.0))
    r1 = segment_frame_flags(P1, t1, _flat_tols(), min_agree=1)
    r2 = segment_frame_flags(P1, t1, _flat_tols(), min_agree=2)
    chk("★ 1개 기준은 프레임을 잡고, 2개 기준은 줄어든다",
        r1["flags"].sum() >= r2["flags"].sum(),
        "k1=%d k2=%d / 150" % (r1["flags"].sum(), r2["flags"].sum()))

    # (A) 체인 끝 랜드마크만 교란 → 정확히 1개 분절만 위반
    #     랜드마크 4(엄지끝)는 분절 (3,4)에만 속한다. → 2개 기준에서 검출되지 않아야 한다.
    P2, t2 = _synth_hand(F=150, seed=6, noise_mm=(0.15, 0.15))
    rest2 = np.zeros(150, bool); rest2[:27] = True
    win = slice(60, 120)
    P2[win, 4, 0] += 0.020
    r1b = segment_frame_flags(P2, t2, _flat_tols(), rest=rest2, min_agree=1)
    r2b = segment_frame_flags(P2, t2, _flat_tols(), rest=rest2, min_agree=2)
    chk("★ 체인 끝 1개 분절 교란 → 1개 기준은 검출", r1b["flags"].sum() >= 50,
        "k1=%d" % r1b["flags"].sum())
    chk("★ 체인 끝 1개 분절 교란 → 2개 기준은 검출 안 함", r2b["flags"].sum() == 0,
        "k2=%d" % r2b["flags"].sum())

    # (B) ★ 공유 랜드마크를 움직이면 인접 2분절이 동시에 변한다
    #     → k2 조건은 '랜드마크 이탈'을 여전히 잡는다(의도된 성질).
    P4 = P2.copy()
    P4[win, 6, 0] += 0.012          # 랜드마크 6 = (5,6) 과 (6,7) 에 동시 소속
    r4 = segment_frame_flags(P4, t2, _flat_tols(), rest=rest2, min_agree=2)
    chk("★ 공유 랜드마크 이탈 → k2 에서도 검출(의도된 성질)", r4["flags"].sum() >= 50,
        "k2=%d" % r4["flags"].sum())

    # (C) 서로 다른 두 체인에서 1개씩(비공유) 교란 → k2 검출
    P5 = P2.copy()
    P5[win, 20, 0] += 0.012         # 소지 끝 = (19,20) 만
    r5 = segment_frame_flags(P5, t2, _flat_tols(), rest=rest2, min_agree=2)
    chk("★ 비공유 두 분절 동시 교란 → k2 검출", r5["flags"].sum() >= 50,
        "k2=%d" % r5["flags"].sum())
    chk("★ 위반 분절 이름이 기록된다", len(r5["violating_names"]) >= 2,
        str(r5["violating_names"]))
    chk("★ 분절별 위반 횟수가 기록된다",
        all(isinstance(v, int) for v in r5["per_segment"].values()), "ok")

    # ---- ★ 분모 = 프레임 ----
    chk("★ 분모 = 검사 가능한 프레임 수(프레임×분절 아님)",
        r5["denom_frames"] <= 150 and r5["pair_denom"] == r5["denom_frames"] * 15,
        "denom=%d pair=%d" % (r5["denom_frames"], r5["pair_denom"]))
    fr = r5["flags"].sum() / max(r5["denom_frames"], 1)
    pr = r5["flags"].sum() / max(r5["pair_denom"], 1)
    chk("★ 분모 해석 차이(프레임 vs 프레임×분절)가 15배 검출력 차이를 만든다",
        fr > 10 * pr,
        "frame=%.3f pair=%.4f (%.1f배)" % (fr, pr, fr / max(pr, 1e-9)))

    # ---- §8.2 정지 기준선 ----
    rest_short = np.zeros(150, bool)
    rest_short[:3] = True
    rs = segment_frame_flags(P1, t1, _flat_tols(), rest=rest_short)
    chk("§8.2 정지 기준선 <8프레임 → 판단 불가", rs["rest_ok"] is False
        and rs["reason"] == "segment_baseline_unavailable", rs["reason"])
    rest_ok = np.zeros(150, bool)
    rest_ok[:20] = True
    ro = segment_frame_flags(P1, t1, _flat_tols(), rest=rest_ok)
    chk("§8.2 정지 기준선 충분 → 판정 수행", ro["rest_ok"] is True)

    # ---- §8.2 손-일관성 ----
    Pc, _ = _synth_hand(F=50, seed=7, noise_mm=(0.3, 0.0))
    hc = hand_consistency(Pc)
    chk("§8.2 손-일관성 [60,230]mm 안이면 유효", hc["valid"].all(),
        "d_index 중앙 %.1fmm d_middle 중앙 %.1fmm" % (np.nanmedian(hc["d_index_mm"]),
                                                      np.nanmedian(hc["d_middle_mm"])))
    Pbad = Pc.copy()
    Pbad[:, 8, 0] = Pbad[:, 0, 0] + 0.30      # 검지끝을 300mm 로
    hb = hand_consistency(Pbad)
    chk("§8.2 손-일관성 밖 → 프레임 무효", hb["valid"].sum() == 0
        and hb["n_invalid_range"] == 50, "n_invalid=%d" % hb["n_invalid"])
    chk("§8.2 손-일관성은 앱 규칙과 별개로 기록", "n_implausible_span" in hb
        and hb["n_implausible_span"] >= 0, "span260=%d" % hb["n_implausible_span"])

    # ---- §8.2 상한 보정 ----
    cal = calibrate_cap([0.05, 0.10, 0.20, 0.30, 0.40, 0.45, 0.50, 0.52, 0.60, 0.70])
    exp_cap = float(np.percentile([0.05, 0.10, 0.20, 0.30, 0.40, 0.45, 0.50, 0.52, 0.60, 0.70], 90))
    chk("§8.2 상한 = 개발군 90백분위(선형 보간)", abs(cal["cap"] - exp_cap) < 1e-9
        and cal["provisional"] is False, "cap=%.4f (기대 %.4f)" % (cal["cap"], exp_cap))
    chk("§8.2 개발군 없으면 잠정 30%", calibrate_cap([])["cap"] == CAP_DEFAULT)

    # ---- §8.2 강등 판정 ----
    dd = demotion_decision({"T1": 0.62, "T2": 0.20}, source="dev_group")
    chk("§8.2 보류율 >50% → 조건부 강등", dd["demote"] is True and "강등" in dd["action"])
    chk("§8.2 보류율 ≤50% → 유지", demotion_decision({"T1": 0.30, "T2": 0.20}, source="dev_group")["demote"] is False)

    # ---- §8.2 결과 기반 튜닝 금지 ----
    raised = False
    try:
        segment_tolerances([{"score": 3}])
    except ValueError:
        raised = True
    chk("§8.2 결과 필드가 들어오면 보정 거부", raised is True)

    # ---- §8.2 손 Q 통합 ----
    Pq, tq = _synth_hand(F=150, seed=11, noise_mm=(0.30, 0.30))
    rest = np.zeros(150, bool)
    rest[:27] = True
    q = hand_q_v13(Pq, tq, 0.0746, _flat_tols(), rest=rest, cap=CAP_DEFAULT)
    chk("손 Q(v13): 안정 자료 + 충분한 정지구간 → 통과", q["pass"] is True,
        "%s rate=%s" % (q["reasons"], q["seg_rate"]))
    chk("손 Q: 연속 미검출 한계 = 5×dt_ref", abs(q["gap_limit_s"] - 5 * 0.0746) < 1e-9,
        "%.4f s" % q["gap_limit_s"])
    q2 = hand_q_v13(Pq, tq, 0.0746, _flat_tols(), rest=rest[:3].tolist() + [False] * 147,
                    cap=CAP_DEFAULT)
    chk("손 Q: 정지구간 부족 → hard_missing", q2["hard_missing"] == ["segment_baseline_unavailable"]
        and q2["pass"] is False, str(q2["reasons"]))


    # ---- 랜드마크 커버리지 (v13 게이트의 사각지대) ----
    cov = landmark_coverage()
    chk("★ 커버리지: 손끝 4·16·20 이 게이트 밖", cov["uncovered_gate_tips"] == [4, 16, 20],
        str(cov["uncovered_gate_tips"]))
    chk("★ 커버리지: 게이트 밖 랜드마크 목록", cov["uncovered_by_gate"] == [0, 1, 4, 5, 9, 13, 16, 17, 20],
        str(cov["uncovered_by_gate"]))
    chk("★ 커버리지: 8·12 는 손-일관성이 잡는다",
        cov["per_landmark"][8]["by_hand_consistency"] and cov["per_landmark"][12]["by_hand_consistency"])
    chk("★ 커버리지: 엄지끝 4 는 D_TI_max 정의 랜드마크인데 게이트 밖",
        cov["per_landmark"][4]["covered_by_gate"] is False
        and cov["per_landmark"][4]["by_app_implausible_span_NOT_A_GATE"] is True)

    # ---- 세 설정 배선 ----
    tq2 = np.arange(150) / 13.4
    rest_ok = np.zeros(150, bool); rest_ok[:27] = True
    ql = hand_q_v13(Pq, tq2, 0.0746, _flat_tols(), rest=rest_ok, cap=None, setting="loose")
    qs = hand_q_v13(Pq, tq2, 0.0746, _flat_tols(), rest=rest_ok, cap=None, setting="strict")
    chk("★ 세 설정이 상한으로 배선됨(느슨 0.40 / 엄격 0.20)",
        abs(ql["cap"] - 0.40) < 1e-12 and abs(qs["cap"] - 0.20) < 1e-12,
        "loose=%.2f strict=%.2f source=%s" % (ql["cap"], qs["cap"], ql["cap_source"]))
    qx = hand_q_v13(Pq, tq2, 0.0746, _flat_tols(), rest=rest_ok, cap=0.55, setting="base")
    chk("★ 개발군 확정 상한이 설정값을 덮어쓴다", abs(qx["cap"] - 0.55) < 1e-12,
        qx["cap_source"])

    # ---- 강등 판정은 개발군·과제별에서만 ----
    dp = demotion_decision({"T1": 1.0}, source="pilot_fallback_diagnostic")
    dd_ = demotion_decision({"T1": 0.6}, source="dev_group")
    chk("★ 강등: 진단용 자료는 판정 보류(diagnostic_only)",
        dp["diagnostic_only"] is True and dp["demote"] is None, str(dp["action"]))
    chk("★ 강등: 개발군 입력이면 판정", dd_["diagnostic_only"] is False and dd_["demote"] is True)

    print("=" * 74)
    print("qv13 오라클 (v13 §8.2 · §21)")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 74)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


# =====================================================================
# 파일럿 실행
# =====================================================================
def _load_hand(f, hand):
    by = {}
    with io.open(f, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("Hand") or "").strip() != hand:
                continue
            try:
                fid = int(float(r["Frame_ID"])); lid = int(float(r["Landmark_ID"]))
                by.setdefault(fid, {})[lid] = (
                    float(r.get("MP_X_m") or "nan"), float(r.get("MP_Y_m") or "nan"),
                    float(r.get("MP_Z_m") or "nan"),
                    float(r.get("time_s") or "nan"))
            except (KeyError, TypeError, ValueError):
                continue
    if not by:
        return None
    fids = sorted(by)
    P = np.full((len(fids), 21, 3), np.nan)
    t = np.full(len(fids), np.nan)
    for i, fid in enumerate(fids):
        for lid, (x, y, z, ts) in by[fid].items():
            if 0 <= lid <= 20:
                P[i, lid] = (x, y, z)
            if lid == 0:
                t[i] = ts
    if not np.isfinite(t).any():
        t = np.arange(len(fids), dtype=float)
    return fids, t, P


def run_pilot(session_dir, pose_path=None, hand="Left", rest_mode="fallback",
              tol_map=None, cap=CAP_DEFAULT, setting="base"):
    files = sorted(glob.glob(os.path.join(session_dir, "split", "*", "Trial_*", "*_landmarks.csv")))
    loaded = []
    for f in files:
        r = _load_hand(f, hand)
        if r:
            loaded.append((os.path.basename(os.path.dirname(f)), r))

    # §8.2-1 세션 공통 dt_ref (모든 시행 프레임을 프레임 ID로 합침)
    all_fid = np.concatenate([r[0] for _, r in loaded]) if loaded else np.array([])
    all_t = np.concatenate([r[1] for _, r in loaded]) if loaded else np.array([])
    dt_session, n_sess = session_dt_ref(all_fid, all_t)

    # 개발군이 없으므로 tol 은 하한(0.20) — v13 §8.2 "개발군 측정 전에는 하한 적용"
    if tol_map is None:
        tol_map = _flat_tols()

    rows = []
    for trial, (fid, t, P) in loaded:
        dt_local, _ = dt_ref_of(t)
        if rest_mode == "strict":
            rest = np.zeros(len(t), bool)          # §6.3.1 정지구간 없음 → 판단 불가
        else:
            rest = t <= (t[0] + 2.0)               # 진단용 대체(정지구간 아님, 라벨 필수)
        q = hand_q_v13(P, t, dt_session, tol_map, rest=rest, cap=cap, setting=setting)
        seg = q["segment"]
        rows.append({
            "trial": trial, "n_frames": int(len(fid)),
            "dt_ref_session_s": dt_session, "dt_ref_local_s": dt_local,
            "rest_mode": rest_mode,
            "track_ratio": q["track_ratio"], "n_valid": q["n_valid"],
            "hand_consistency_invalid": q["consistency"]["n_invalid"],
            "hand_consistency_invalid_frac": (q["consistency"]["n_invalid"] / len(fid)) if len(fid) else None,
            "implausible_span": q["consistency"]["n_implausible_span"],
            "seg_denom_frames": seg["denom_frames"], "seg_pair_denom": seg["pair_denom"],
            "seg_flags": int(seg["flags"].sum()),
            "seg_rate": q["seg_rate"], "seg_rest_ok": seg["rest_ok"],
            "seg_violating": seg["violating_names"],
            "seg_per_segment": seg["per_segment"],
            "reasons": q["reasons"], "hard_missing": q["hard_missing"], "pass": q["pass"],
        })
    hold = sum(1 for r in rows if not r["pass"]) / len(rows) if rows else None
    return {
        "session": os.path.basename(session_dir), "hand": hand, "rest_mode": rest_mode,
        "session_dt_ref_s": dt_session, "n_session_frames": n_sess,
        "tol_source": "하한 0.20 (개발군 미측정)", "cap": cap,
        "n_trials": len(rows), "hold_rate": hold,
        "demotion": demotion_decision({"T1": hold, "T2": hold},
                                      source=("pilot_%s_diagnostic" % rest_mode)),
        "landmark_coverage": landmark_coverage(),
        "records": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="v13 §8.2 규칙 구현·검증")
    ap.add_argument("--pilot")
    ap.add_argument("--pose", default=None)
    ap.add_argument("--hand", default="Left")
    ap.add_argument("--rest-mode", default="fallback", choices=["strict", "fallback"])
    ap.add_argument("--cap", type=float, default=CAP_DEFAULT)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.pilot:
        ap.error("--pilot 또는 --selftest")
    res = run_pilot(a.pilot, pose_path=a.pose, hand=a.hand, rest_mode=a.rest_mode, cap=a.cap)
    txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(txt)
        print("wrote %s" % a.out)
    print(json.dumps({k: v for k, v in res.items() if k != "records"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

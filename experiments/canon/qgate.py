# -*- coding: utf-8 -*-
"""품질 게이트 Q — 손 M1·M2 (분절 규칙 제외판). 신규 파일(기존 코드 미수정).

2026-10-02 사용자 지시 반영:
  "손가락 분절 규칙은 데이터를 버리는 게이트가 아닌 '참고용 진단값'으로 격하"

구조로 강제한다(주석 약속이 아니라 시그니처로):
  · `decide_hand_gate()` 는 **분절 규칙 값을 인자로 받지 않는다.** 넘길 방법이 없다.
  · 분절 규칙은 `segment_diagnostic()` 으로 **계산·기록만** 한다.
  · `assert_segment_not_in_gate()` 가 판정 함수 소스에 'segment' 문자열이 없는지 정적으로 검사한다.

정의는 `defs.py` 에서만 가져온다(엄지 (1,2,3)·(2,3,4) 포함).
파일럿 자료 재분석은 하지 않는다. 입력은 호출자가 준 프레임 배열뿐이다.

출처: capstone/실험계획서_v13.2_최종본.md §8.2
"""
from __future__ import annotations
import inspect
import math
import numpy as np

from defs import (FLEX14, FLEX_NAMES, SEGMENTS_15, SEGMENT_RULE_IS_GATE, SETTINGS,
                  DEFAULT_SETTING, HAND_CONSISTENCY_ANCHOR, HAND_CONSISTENCY_TIPS,
                  HAND_CONSISTENCY_MM, D_TI_MAX_PAIR, SEG_TOL_FLOOR, SEG_K_TOL,
                  SEG_MIN_AGREE, SEG_BASELINE_FRAMES_MIN, SEG_BASELINE_WINDOW_S,
                  GAP_RATIO_MAX, GAP_S_MAX, MAX_MISSED_RUN_DT, MIN_VALID_FRAMES,
                  HAND_GATE_CONDITIONS, HAND_DIAGNOSTIC_ONLY)


def interior_angle(a, b, c) -> float:
    """b 를 꼭짓점으로 하는 내각(deg). 굴곡각 = 180 − 내각."""
    v1, v2 = np.asarray(a, float) - np.asarray(b, float), np.asarray(c, float) - np.asarray(b, float)
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return float("nan")
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(v1, v2) / (n1 * n2))))))


# ── 지표 (계획서 §7.1) ──────────────────────────────────────────────────────
def flexion_angles(P: np.ndarray) -> np.ndarray:
    """(F,21,3) → (F,14). 열 순서는 FLEX_NAMES. 엄지는 (1,2,3)·(2,3,4)."""
    F = P.shape[0]
    A = np.full((F, len(FLEX_NAMES)), np.nan)
    for j, name in enumerate(FLEX_NAMES):
        i1, i2, i3 = FLEX14[name]
        for fr in range(F):
            A[fr, j] = 180.0 - interior_angle(P[fr, i1], P[fr, i2], P[fr, i3])
    return A


def f_sum14_p95(P: np.ndarray) -> float | None:
    """14개 굴곡각 합의 시행 P95. 14개가 모두 유한한 프레임만 쓴다."""
    A = flexion_angles(P)
    ok = np.isfinite(A).all(axis=1)
    if ok.sum() < 8:
        return None
    return float(np.percentile(A[ok].sum(axis=1), 95))


def d_ti_max_mm(P: np.ndarray) -> float | None:
    """MP world 4–8 거리의 시행 최댓값(mm). 상한 캡 없음(§8.2 주석)."""
    d = np.linalg.norm(P[:, D_TI_MAX_PAIR[0]] - P[:, D_TI_MAX_PAIR[1]], axis=-1) * 1000.0
    d = d[np.isfinite(d)]
    return float(d.max()) if d.size else None


# ── 손-일관성 (프레임 무효 조건, §8.2) ─────────────────────────────────────
def span_mm(P: np.ndarray) -> np.ndarray:
    """(F,21,3) → (F,3): 손목에서 엄지끝(4)·검지끝(8)·중지끝(12) 까지 3D 거리(mm)."""
    w = P[:, HAND_CONSISTENCY_ANCHOR]
    return np.stack([np.linalg.norm(P[:, tip] - w, axis=-1) * 1000.0
                     for tip in HAND_CONSISTENCY_TIPS], axis=1)


def hand_consistency_invalid(P: np.ndarray) -> np.ndarray:
    """[60,230] mm 를 벗어난 프레임을 True 로 표시(무효 프레임)."""
    s = span_mm(P)
    lo, hi = HAND_CONSISTENCY_MM
    return ~np.isfinite(s).all(axis=1) | ((s < lo) | (s > hi)).any(axis=1)


# ── ★ 진단값 (판정에 쓰지 않는다) ───────────────────────────────────────────
def segment_diagnostic(P: np.ndarray, t: np.ndarray, *, cap: float | None = None,
                       cap_source: str = "setting:default") -> dict:
    """분절 불일치 **진단값**. 반환값은 판정에 사용되지 않는다.

    계획서 §8.2 규칙을 그대로 계산한다.
      기준 길이 = 시행 전 2초 유효 프레임의 분절별 중앙값 (최소 8개)
      tol_seg   = max(0.20, 3 × 1.4826×MAD(분절길이 ÷ 기준길이))
      불일치    = 2개 이상 분절이 동시에 tol_seg 를 벗어난 프레임
      분모      = 검사 가능한(기준 길이가 있는) 프레임 수
    """
    F = P.shape[0]
    L = np.stack([np.linalg.norm(P[:, a] - P[:, b], axis=-1) for (a, b) in SEGMENTS_15], axis=1)
    rest = np.isfinite(t) & (t <= (t[0] + SEG_BASELINE_WINDOW_S))
    base = np.full(L.shape[1], np.nan)
    for k in range(L.shape[1]):
        m = rest & np.isfinite(L[:, k])
        if m.sum() >= SEG_BASELINE_FRAMES_MIN:
            v = float(np.median(L[:, k][m]))
            if v > 0:
                base[k] = v
    testable = np.isfinite(base)
    if not testable.any():
        return {"rate": None, "n_testable_frames": 0, "cap": cap,
                "cap_source": cap_source, "would_exceed_cap": None,
                "violating_segments": [], "baseline_available": False,
                "status": "segment_baseline_unavailable", "is_gate": SEGMENT_RULE_IS_GATE}
    rel = np.abs(L[:, testable] - base[testable]) / base[testable]
    norm = np.where(np.isfinite(rel), rel, np.nan)
    mad = np.nanmedian(np.abs(norm - np.nanmedian(norm, axis=0)), axis=0) * 1.4826
    tol = np.maximum(SEG_TOL_FLOOR, SEG_K_TOL * mad)
    viol = np.nansum((norm > tol).astype(int), axis=1)
    usable = np.isfinite(L[:, testable]).any(axis=1)
    n = int(usable.sum())
    rate = float((viol >= SEG_MIN_AGREE)[usable].sum()) / n if n else None
    names = [SEGMENTS_15[k] for k in np.flatnonzero(testable)]
    vcount = np.nansum((norm > tol).astype(int), axis=0)
    return {"rate": rate, "n_testable_frames": n, "cap": cap, "cap_source": cap_source,
            "would_exceed_cap": (rate > cap) if (rate is not None and cap is not None) else None,
            "violating_segments": [names[i] for i in np.argsort(-vcount)[:5] if vcount[i] > 0],
            "baseline_available": True, "status": "ok", "is_gate": SEGMENT_RULE_IS_GATE}


# ── ★ 판정 (분절 규칙을 받지 않는다) ────────────────────────────────────────
def decide_hand_gate(*, track_rate, max_missed_run_dt, n_valid_frames,
                     consistency_invalid_frac, setting=DEFAULT_SETTING) -> dict:
    """손 M1·M2 게이트 판정. **분절 규칙은 인자에 없다.**

    인자
      track_rate                : 대상 손 추적률(0–1)
      max_missed_run_dt         : 연속 미검출 프레임 수 ÷ dt_ref  (dt_ref 단위 배수)
      n_valid_frames            : 손-일관성까지 통과한 실제 유효 프레임 수
      consistency_invalid_frac  : 손-일관성 위반 프레임 비율(0–1)
    """
    s = SETTINGS[setting]
    checks = {
        "hand_track_rate": track_rate >= s["hand_valid_min"],
        "max_missed_run": max_missed_run_dt <= MAX_MISSED_RUN_DT,
        "min_valid_frames": n_valid_frames >= MIN_VALID_FRAMES,
        "hand_consistency": consistency_invalid_frac <= (1.0 - s["hand_valid_min"]),
    }
    failed = [k for k, ok in checks.items() if not ok]
    return {"setting": setting, "checks": checks, "failed": failed,
            "decision": "pass" if not failed else "hold"}


# 격하 상태를 게이트 바깥에 선언한다(판정 함수 안에는 분절 관련 문자열이 없어야 한다)
SEGMENT_RULE_USED_IN_GATE = False


def gate_definition() -> dict:
    """게이트 구성의 선언. 판정 함수와 분리해 둔다."""
    return {"conditions_that_can_reject": list(HAND_GATE_CONDITIONS),
            "diagnostic_only_never_reject": list(HAND_DIAGNOSTIC_ONLY),
            "segment_rule_used_in_gate": SEGMENT_RULE_USED_IN_GATE,
            "settings": list(SETTINGS)}


def assert_segment_not_in_gate() -> None:
    """판정 함수가 분절 규칙을 읽지 않는지 정적으로 검사(문자열 수준)."""
    src = inspect.getsource(decide_hand_gate)
    for bad in ("segment", "SEG_", "tol_seg"):
        assert bad not in src, "게이트 판정 함수에 분절 규칙이 섞였다: %r" % bad
    assert SEGMENT_RULE_IS_GATE is False, "SEGMENT_RULE_IS_GATE 가 True 다"
    assert SEGMENT_RULE_USED_IN_GATE is False, "SEGMENT_RULE_USED_IN_GATE 가 True 다"

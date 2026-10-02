# -*- coding: utf-8 -*-
"""정본 정의·게이트 오라클 — **합성 자료만** 사용한다(파일럿 재분석 없음).

목적
  ① 엄지 관절 정의가 계획서 §7.1 대로 (1,2,3)·(2,3,4) 인가
  ② 분절 규칙이 **게이트가 아니라 진단값**으로만 쓰이는가(구조 + 정적 검사 + 동작 검사)
  ③ 게이트의 나머지 조건은 여전히 보류를 낼 수 있는가(격하가 무력화가 아님)

실행: python experiments/canon/oracle.py
"""
from __future__ import annotations
import math
import sys
import numpy as np

import defs as D
import qgate as Q

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s  %s" % (name, detail))


def make_hand(seed=0, jitter_m=0.0, tip_jump_m=0.0):
    """합성 21점 손. jitter_m>0 이면 프레임마다 무작위 흔들림(비강체)."""
    rng = np.random.default_rng(seed)
    P = np.zeros((21, 3))
    P[0] = (0.00, 0.00, 0.0)
    P[1], P[2], P[3], P[4] = (0.03, 0.012, 0), (0.062, 0.022, 0), (0.094, 0.030, 0), (0.126, 0.036, 0)
    for base, x in ((5, 0.020), (9, 0.038), (13, 0.056), (17, 0.074)):
        P[base] = (x, 0.020, 0)
        prev = P[base].copy()
        for k in range(3):
            prev = prev + np.array([0.004 * (k + 1), 0.040, 0.0])
            P[base + 1 + k] = prev
    P[4] = P[4] + np.array([0.0, 0.0, 0.0])
    if tip_jump_m:
        P[8] = P[8] + np.array([0.0, tip_jump_m, 0.0])   # +y 로 벌린다
    if jitter_m:
        P = P + rng.normal(scale=jitter_m, size=P.shape)
    P[4] = P[4]
    return P


def seq(n=40, jitter_m=0.0, dt=0.077, seed=1):
    t = np.arange(n) * dt
    base = make_hand(seed=seed)
    P = np.stack([make_hand(seed=seed + i, jitter_m=jitter_m) for i in range(n)])
    return P, t


print("=" * 92)
print("① 정의 오라클 — 계획서 §7.1 · §8.2")
print("=" * 92)
check("엄지 CMC–MCP–IP == (1,2,3)", D.FLEX14["Thumb_CMC_MCP_IP"] == (1, 2, 3), D.FLEX14["Thumb_CMC_MCP_IP"])
check("엄지 MCP–IP–TIP == (2,3,4)", D.FLEX14["Thumb_MCP_IP_TIP"] == (2, 3, 4), D.FLEX14["Thumb_MCP_IP_TIP"])
check("엄지가 (0,1,2) 를 쓰지 않는다", (0, 1, 2) not in D.FLEX14.values())
check("굴곡각 총 14개", len(D.FLEX14) == 14, len(D.FLEX14))
check("손가락 5개, 엄지만 2각",
      sum(1 for v in D.FINGER_OF_FLEX.values() if v == "Thumb") == 2 and
      all(sum(1 for v in D.FINGER_OF_FLEX.values() if v == f) == 3 for f in ("Index", "Middle", "Ring", "Pinky")))
want15 = [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), (9, 10), (10, 11), (11, 12),
          (13, 14), (14, 15), (15, 16), (17, 18), (18, 19), (19, 20)]
check("분절 15개가 계획서와 일치", D.SEGMENTS_15 == want15)
check("D_TI_max 는 엄지·검지 6분절", len(D.SEGMENTS_TI6) == 6 and D.SEGMENTS_TI6 == want15[:6])
check("손-일관성 끝점 = 4·8·12, 범위 [60,230]",
      D.HAND_CONSISTENCY_TIPS == (4, 8, 12) and D.HAND_CONSISTENCY_MM == (60.0, 230.0))
check("세 설정표가 3개이고 기본 상한 30%",
      set(D.SETTINGS) == {"loose", "default", "strict"} and D.SETTINGS["default"]["seg_dev_max"] == 0.30)

print()
print("=" * 92)
print("② 분절 규칙 격하 — 구조·정적·동작")
print("=" * 92)
check("SEGMENT_RULE_IS_GATE == False", D.SEGMENT_RULE_IS_GATE is False)
try:
    Q.assert_segment_not_in_gate()
    check("판정 함수 소스에 분절 규칙 없음(정적 검사)", True)
except AssertionError as e:
    check("판정 함수 소스에 분절 규칙 없음(정적 검사)", False, str(e))
sig = Q.decide_hand_gate.__code__.co_varnames[:Q.decide_hand_gate.__code__.co_argcount]
check("판정 함수 시그니처에 분절 인자 없음",
      not any("seg" in s.lower() for s in sig), sig)
check("격하 후 게이트 조건 목록 = 4개(분절 제외)",
      set(D.HAND_GATE_CONDITIONS) == {"hand_track_rate", "max_missed_run",
                                      "min_valid_frames", "hand_consistency"})
check("진단값 목록에 분절 규칙 포함", "segment_deviation" in D.HAND_DIAGNOSTIC_ONLY)

# 동작 검사: 분절 진단값이 상한을 넘어도 판정은 통과
P, t = seq(n=40, jitter_m=0.012, seed=7)
diag = Q.segment_diagnostic(P, t, cap=D.SETTINGS["default"]["seg_dev_max"])
dec = Q.decide_hand_gate(track_rate=0.95, max_missed_run_dt=1.0, n_valid_frames=38,
                         consistency_invalid_frac=0.01)
print("      (합성) 분절 진단: 비율=%s 상한초과=%s | 게이트 판정=%s" %
      (None if diag["rate"] is None else round(diag["rate"], 3), diag["would_exceed_cap"], dec["decision"]))
check("판정 함수가 분절 규칙을 쓰지 않는다고 선언", Q.SEGMENT_RULE_USED_IN_GATE is False)
check("선언 함수에 진단값 목록이 있다",
      "segment_deviation" in Q.gate_definition()["diagnostic_only_never_reject"])
check("판정 반환에 분절 키가 없다", not any("seg" in k.lower() for k in dec["checks"]))
check("★ 진단값이 상한 초과인데도 게이트는 통과(격하 동작)",
      (diag["rate"] is not None and diag["would_exceed_cap"] is True and dec["decision"] == "pass"),
      "rate=%s cap_exceed=%s decision=%s" % (diag["rate"], diag["would_exceed_cap"], dec["decision"]))

print()
print("=" * 92)
print("③ 격하가 무력화가 아님 — 나머지 조건은 여전히 보류를 낸다")
print("=" * 92)
d1 = Q.decide_hand_gate(track_rate=0.50, max_missed_run_dt=1.0, n_valid_frames=38,
                        consistency_invalid_frac=0.01)
check("추적률 0.50 → 보류", d1["decision"] == "hold" and "hand_track_rate" in d1["failed"], d1)
d2 = Q.decide_hand_gate(track_rate=0.95, max_missed_run_dt=10.0, n_valid_frames=38,
                        consistency_invalid_frac=0.01)
check("연속 미검출 10×dt_ref → 보류", d2["decision"] == "hold" and "max_missed_run" in d2["failed"], d2)
d3 = Q.decide_hand_gate(track_rate=0.95, max_missed_run_dt=1.0, n_valid_frames=5,
                        consistency_invalid_frac=0.01)
check("유효 프레임 5개 → 보류", d3["decision"] == "hold" and "min_valid_frames" in d3["failed"], d3)
d4 = Q.decide_hand_gate(track_rate=0.95, max_missed_run_dt=1.0, n_valid_frames=38,
                        consistency_invalid_frac=0.30)
check("손-일관성 위반 30% → 보류", d4["decision"] == "hold" and "hand_consistency" in d4["failed"], d4)
d5 = Q.decide_hand_gate(track_rate=0.90, max_missed_run_dt=3.0, n_valid_frames=20,
                        consistency_invalid_frac=0.05)
check("모두 통과 → 통과", d5["decision"] == "pass", d5)
check("설정별 임계가 다르다(기본 0.80 vs 엄격 0.90)",
      Q.decide_hand_gate(track_rate=0.85, max_missed_run_dt=3.0, n_valid_frames=20,
                         consistency_invalid_frac=0.05, setting="default")["decision"] == "pass" and
      Q.decide_hand_gate(track_rate=0.85, max_missed_run_dt=3.0, n_valid_frames=20,
                         consistency_invalid_frac=0.05, setting="strict")["decision"] == "hold")

print()
print("=" * 92)
print("④ 지표·일관성 함수 오라클 (합성)")
print("=" * 92)
P1, _ = seq(n=30, jitter_m=0.0)
A = Q.flexion_angles(P1)
check("굴곡각 행렬 모양 (30,14)", A.shape == (30, 14), A.shape)
check("합성 강체손에서 14각 모두 유한", np.isfinite(A).all())
fs = Q.f_sum14_p95(P1)
check("F_sum14 P95 산출", fs is not None and math.isfinite(fs), fs)
dt_ = Q.d_ti_max_mm(P1)
check("D_TI_max 산출", dt_ is not None and dt_ > 0, dt_)
P2 = np.stack([make_hand(seed=1, tip_jump_m=0.100) for _ in range(30)])
check("검지끝 +100mm 시 D_TI_max 증가", Q.d_ti_max_mm(P2) > Q.d_ti_max_mm(P1))
s = Q.span_mm(P1)
check("손목–4/8/12 거리 3개", s.shape == (30, 3), s.shape)
ok = Q.hand_consistency_invalid(P1)
check("합성 정상손은 일관성 통과", not ok.all())
big = make_hand().copy()
big[8] = big[0] + np.array([0.300, 0, 0])          # 0→8 = 300 mm
Pb = np.stack([big] * 10)
check("0→8 = 300mm 프레임은 무효", Q.hand_consistency_invalid(Pb).all())
small = make_hand().copy()
small[8] = small[0] + np.array([0.010, 0, 0])      # 0→8 = 10 mm
Ps = np.stack([small] * 10)
check("0→8 = 10mm 프레임은 무효", Q.hand_consistency_invalid(Ps).all())

diag_ok = Q.segment_diagnostic(*seq(n=40, jitter_m=0.0), cap=0.30)
check("진단값에 is_gate=False 기록", diag_ok["is_gate"] is False)
check("진단값에 분모(검사 가능 프레임) 기록", diag_ok["n_testable_frames"] > 0, diag_ok["n_testable_frames"])

print()
print("=" * 92)
print("결과: PASS %d / FAIL %d" % (PASS, FAIL))
print("=" * 92)
sys.exit(1 if FAIL else 0)

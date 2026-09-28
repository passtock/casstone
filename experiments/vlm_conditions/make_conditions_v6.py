#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""조건 생성기 v6 — **연구계획서 v6.2 §6·§7에 맞춘 정본 생성기**

배경 (결함 D-15)
----------------
구 `make_conditions.py`는 **파일럿 파이프라인**(`trials_summary.csv` + `qiu_kinematics_summary.csv`)에
맞춰 만들어졌고, 계획서와 다음이 달랐다:

| 계획서 v6.2 | 구 코드 |
|---|---|
| K1 = 엄지–검지 거리 P95 | `MGA_mm_3D_cal` (최대 파지 간격) |
| K2 = 손목속도 **P95** | **`PV_mm_s` = peak velocity** ← V-1이 깨졌다고 규명한 지표 |
| 지표 2개 | 지표 4개 (MGA·PV·SPARC·TAM) |
| ARAT 3번(5 cm 블록 55 g)·12번(구슬 1.6 cm) | `free`(맨손 쥐기펴기)·`cylinder`(원통형) |
| 조건 A0·A0-time 포함 | 없음 |

이 파일은 **그 불일치를 없앤 정본**이다. 구 파일은 파일럿 재현용으로 남겨 둔다.

입력
----
`<session>/L2_metric/<trial_id>.json` — `k1k2_from_files.py`가 쓴 것.
필요 키:
  - `k1_raw_mm`, `k2_raw_mm`            : Q 판정 **이전** 계산값  → **A2**가 쓴다
  - `k1_thumb_index_surface_p95_mm` …   : Q-gated 값(None 가능)   → **A3**가 쓴다
  - `q_held_k1`, `q_held_k2`            : 값은 있었지만 Q가 보류했는지
  - `observation_window_s`              : 프롬프트의 T

출력
----
`conditions.csv` — 한 행 = VLM 1회 호출
  `condition, injection, r_seed, participant, task, trial_index, trial_id,
   video, k1, k2, n_numbers, video_provided, prompt`

사용
----
    python experiments/vlm_conditions/make_conditions_v6.py --selftest
    python experiments/vlm_conditions/make_conditions_v6.py --session <세션폴더> --out conditions.csv
    python experiments/vlm_conditions/make_conditions_v6.py --sessions A B C --out all.csv \\
        --u-mode ratio --u-ratios 0.10 0.30

설계 근거 (계획서 조항)
----------------------
  §6  조건 A1~A4 + R  ·  §6.1 주입  ·  §7 입력 프레임  ·  §7.1 프롬프트
  §5.1 dt 하한은 **L1(`k1k2_from_files.py`)** 에서 처리한다(이 파일은 소비자).
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import random
import sys

# ===========================================================================
# 계획서 §6 / §7 — 동결된 상수
# ===========================================================================
CONDITIONS = ["A1", "A2", "A3", "A4", "R"]           # §6 표의 VLM 조건
# A0 / A0-time 은 로지스틱 회귀 대조군이라 VLM 출력이 아니다 → experiments/analysis/baseline_models.py
INJECTIONS = ["none", "bias_1u", "bias_3u", "burst_3u"]   # §6.1 (4수준; none = 원래)
KPI = {
    "k1": "thumb_index_surface_p95_mm",              # §5 정의 (프롬프트 키 이름)
    "k2": "wrist_surface_speed_p95_mm_s",
}
R_SEEDS = [20260922, 20260923, 20260924]             # §6 R 배정 알고리즘
PROMPT_NULL_NOTE = ("[지침]  null은 신뢰 가능한 추정이 없다는 뜻이며, "
                    "기능 저하나 0값을 뜻하지 않습니다.")


# ===========================================================================
# 프롬프트 — 계획서 §7.1 과 **문자 단위로 동일**해야 한다
# ===========================================================================
PROMPT_HEAD = """당신은 뇌졸중 장애인의 상지 기능을 영상으로 평가하는 임상 평가자입니다.

[과제]  {task_label}
[지시문]  {instruction}
[채점 기준]
  3 = 5초 이내 정상 수행 (올바른 손·팔 움직임, 자세 유지)
  2 = 완료했으나 5–60초 또는 큰 어려움
  1 = 60초 내 부분 수행
  0 = 60초 내 어떤 부분도 못함
[관찰 구간]  T = {T} 초
"""
PROMPT_NUMBERS_HEAD = "\n[운동학 수치]\n"
PROMPT_NULL = PROMPT_NULL_NOTE + "\n"
PROMPT_TAIL = "\n[출력]  먼저 점수(0/1/2/3) 한 줄, 그 다음 최대 2문장의 근거.\n"

# ARAT 물성 (§4.2, Yozbatiran 2008 정본)
TASKS = {
    "T1": {"arat": "3", "object": "5 cm 목재 블록 55 g",
           "shelf": "선반 37 cm",
           "instruction": "grasp the block that I have placed here, lift it up, "
                          "and place then release it on top of that shelf."},
    "T2": {"arat": "12", "object": "구슬 지름 1.6 cm 5.4 g",
           "shelf": "선반 위 상부 뚜껑",
           "instruction": "grasp the marble using these fingers, lift it up, "
                          "and place it in the tin on top of that shelf."},
}


def task_label(task: str) -> str:
    t = TASKS[task]
    return "ARAT %s번 — %s" % (t["arat"], t["object"])


def build_prompt(task: str, T, numbers, video_provided: bool) -> str:
    """계획서 §7.1. numbers = [('k1',값|None), ('k2',값|None)] 또는 []."""
    lines = [PROMPT_HEAD.format(task_label=task_label(task),
                                instruction=TASKS[task]["instruction"],
                                T=("%.2f" % T) if T is not None else "미상")]
    if numbers:
        lines.append(PROMPT_NUMBERS_HEAD)
        for key, val in numbers:
            lines.append("  %s = %s\n" % (KPI[key], "null" if val is None else "%.4g" % val))
        lines.append(PROMPT_NULL)
    lines.append("\n[영상]  %s\n" % ("제공됨" if video_provided
                                     else "제공되지 않음 (수치만으로 판단)"))
    lines.append(PROMPT_TAIL)
    return "".join(lines)


# ===========================================================================
# 값 선택 — A1/A2/A3/A4 (§6)
# ===========================================================================
def values_for(condition: str, rec: dict, has_video: bool, numbers_provided: bool):
    """조건별로 프롬프트에 들어갈 수치 목록을 만든다.

    - A1 : 수치 없음
    - A2 : **Q 판정 이전 원값**(k1_raw/k2_raw) — 하드 결측만 null
    - A3 : **Q-gated 값** — Q가 보류하면 null
    - A4 : A3와 같은 수치, 영상 없음
    """
    if condition == "A1" or not numbers_provided:
        return []
    if condition == "A2":
        return [("k1", rec.get("k1_raw_mm")), ("k2", rec.get("k2_raw_mm"))]
    return [("k1", rec.get("k1_thumb_index_surface_p95_mm")),
            ("k2", rec.get("k2_wrist_surface_speed_p95_mm_s"))]


# ===========================================================================
# 오류 주입 (§6.1) — A2·A3 에만
# ===========================================================================
# ⚠️ 해석 명시: bias = 그 시행의 **전 값**에 +k·u (체계적 편향)
#              burst = **지정 시행 하나만** +3u (고립 급등). 나머지 시행은 원래값.
#    → 이 구분은 집계 수준에서만 드러난다(전체가 밀리느냐, 하나만 튀느냐).
def inject(values, injection: str, u: float, is_burst_target: bool):
    if not values or injection == "none" or u is None:
        return values
    if injection == "bias_1u":
        return [(k, None if v is None else v + 1.0 * u) for k, v in values]
    if injection == "bias_3u":
        return [(k, None if v is None else v + 3.0 * u) for k, v in values]
    if injection == "burst_3u":
        if not is_burst_target:
            return values                       # 지정 시행만 급등
        return [(k, None if v is None else v + 3.0 * u) for k, v in values]
    raise ValueError("unknown injection: %s" % injection)


def estimate_u(recs, mode: str, ratios=(0.10, 0.30), abs_u=None):
    """u 추정 (§6.1 A안/B안).

    A안(absolute): 치구·3D 기준 실측 P95 절대오차를 `abs_u` 로 받는다.
    B안(ratio)   : 기저값 대비 비율. 양의 u 로 표현하기 위해 **기저값 평균 × 비율**을 쓴다.
    """
    if abs_u is not None:
        return float(abs_u)
    base = [r.get("k1_raw_mm") for r in recs if r.get("k1_raw_mm") is not None]
    base += [r.get("k2_raw_mm") for r in recs if r.get("k2_raw_mm") is not None]
    if not base:
        return None
    mean_base = sum(base) / float(len(base))
    return mean_base * max(ratios)


# ===========================================================================
# 파일 입력
# ===========================================================================
def load_session(session_dir: str):
    """L2_metric/*.json 을 읽어 시행 레코드 목록을 돌려준다."""
    out = []
    for p in sorted(glob.glob(os.path.join(session_dir, "L2_metric", "*.json"))):
        with io.open(p, "r", encoding="utf-8") as f:
            rec = json.load(f)
        rec.setdefault("trial_id", os.path.basename(p)[:-5])
        rec["_session"] = os.path.basename(os.path.abspath(session_dir.rstrip("/\\")))
        rec["_path"] = p
        out.append(rec)
    return out


def participant_of(rec: dict) -> str:
    """참여자 식별자 = 세션 폴더명.

    폴더 1개 = 참여자 1명 (예: `20260915_비장애인_test_26세_남`).
    ⚠️ `split('_')[1]` 로 집단명('비장애인')을 돌려주면 **모든 참여자가 한 사람으로 취급**된다.
    """
    return rec.get("_session", "")


def task_of(rec: dict) -> str:
    tid = rec.get("trial_id", "")
    m = [s for s in tid.split("_") if s in TASKS]
    return m[0] if m else "T1"


def trial_index_of(rec: dict) -> int:
    tid = rec.get("trial_id", "")
    for s in tid.split("_"):
        if s.lower().startswith("t") and s[1:].isdigit():
            return int(s[1:])
    return 1


# ===========================================================================
# R 조건 배정 (§6 알고리즘)
# ===========================================================================
def r_withheld_map(session_recs, seeds=R_SEEDS):
    """A3가 보류한 개수와 **같은 개수**를, A2에서 무작위로 제거하는 R 배정.

    반환 {seed: set(trial_id)} — 각 seed에서 '제거할' 시행.
    """
    a3_held = set()
    a2_avail = []
    for r in session_recs:
        k1g = r.get("k1_thumb_index_surface_p95_mm") is not None
        k2g = r.get("k2_wrist_surface_speed_p95_mm_s") is not None
        if not (k1g and k2g):
            a3_held.add((r["trial_id"], task_of(r)))
        else:
            a2_avail.append((r["trial_id"], task_of(r)))
    out = {}
    for sd in seeds:
        rnd = random.Random(sd)
        n = len(a3_held)
        pool = list(a2_avail)
        rnd.shuffle(pool)
        out[sd] = set(pool[:n])
    return out, a3_held


# ===========================================================================
# 생성
# ===========================================================================
def make_rows(session_recs, u, burst_trial_index=2, u_mode="ratio"):
    rows = []
    rmap, a3_held = r_withheld_map(session_recs)

    for rec in session_recs:
        pid, task, ti = participant_of(rec), task_of(rec), trial_index_of(rec)
        T = rec.get("observation_window_s")
        video = _video_name(rec)
        is_burst = (ti == burst_trial_index)

        for cond in CONDITIONS:
            prov = (cond != "A1")
            if cond == "R":
                for sd, removed in rmap.items():
                    suppressed = (rec["trial_id"], task) in removed
                    vals = [] if suppressed else values_for("A2", rec, True, True)
                    rows.append(_row(cond, "none", sd, pid, task, ti, rec, vals, T,
                                     video_provided=(cond != "A4"), u=u,
                                     u_mode=u_mode, video=video))
                continue

            inj_list = INJECTIONS if cond in ("A2", "A3") else ["none"]
            for inj in inj_list:
                base = values_for(cond, rec, True, prov)
                vals = inject(base, inj, u, is_burst)
                rows.append(_row(cond, inj, "", pid, task, ti, rec, vals, T,
                                 video_provided=(cond != "A4"), u=u,
                                 u_mode=u_mode, video=video))
    return rows


def _video_name(rec):
    stem = os.path.splitext(os.path.basename(rec.get("_path", "")))[0]
    return stem + ".mp4"


def _row(cond, inj, seed, pid, task, ti, rec, vals, T, video_provided, u, u_mode, video):
    prompt = build_prompt(task, T, vals, video_provided)
    return {
        "condition": cond, "injection": inj, "r_seed": seed,
        "participant": pid, "task": task, "trial_index": ti,
        "trial_id": rec["trial_id"], "video": video,
        "k1": "" if not vals else ("" if vals[0][1] is None else vals[0][1]),
        "k2": "" if len(vals) < 2 or vals[1][1] is None else vals[1][1],
        "n_numbers": len(vals),
        "video_provided": int(video_provided),
        "u_used": "" if u is None else round(u, 6), "u_mode": u_mode,
        "prompt": prompt,
    }


FIELDS = ["condition", "injection", "r_seed", "participant", "task", "trial_index",
          "trial_id", "video", "k1", "k2", "n_numbers", "video_provided",
          "u_used", "u_mode", "prompt"]


def write_csv(rows, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ===========================================================================
# 오라클 — **계획서 준수 검증** (D-15 해소 증거)
# ===========================================================================
_UNSET = object()


def _synth_rec(trial_id, session, k1, k2, k1_gated=_UNSET, k2_gated=_UNSET,
               q_held_k1=False, q_held_k2=False, T=3.5):
    """⚠️ _UNSET 센티넬: k1_gated=None 은 "Q가 보류해서 null" 을 뜻하므로
    기본값 None 을 쓰면 충돌한다(초기 오라클이 이걸로 오탐했다)."""
    return {"trial_id": trial_id, "_session": session, "_path": "/x/" + trial_id + ".json",
            "k1_raw_mm": k1, "k2_raw_mm": k2,
            "k1_thumb_index_surface_p95_mm": (k1 if k1_gated is _UNSET else k1_gated),
            "k2_wrist_surface_speed_p95_mm_s": (k2 if k2_gated is _UNSET else k2_gated),
            "q_held_k1": q_held_k1, "q_held_k2": q_held_k2,
            "observation_window_s": T}


def selftest():
    ok_all = True
    log = []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-58s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    print("[C1] 계획서 준수: 상수·지표·과제")
    chk("조건 == A1,A2,A3,A4,R (A0/A0-time 없음 — 로지스틱은 별도)",
        CONDITIONS == ["A1", "A2", "A3", "A4", "R"], str(CONDITIONS))
    chk("주입 4수준 == none,bias_1u,bias_3u,burst_3u",
        INJECTIONS == ["none", "bias_1u", "bias_3u", "burst_3u"], str(INJECTIONS))
    chk("K1 프롬프트 키 == thumb_index_surface_p95_mm (§5)",
        KPI["k1"] == "thumb_index_surface_p95_mm", KPI["k1"])
    chk("K2 프롬프트 키 == wrist_surface_speed_p95_mm_s (§5)",
        KPI["k2"] == "wrist_surface_speed_p95_mm_s", KPI["k2"])
    chk("과제 == T1(ARAT 3, 5cm 블록)·T2(ARAT 12, 구슬)",
        TASKS["T1"]["arat"] == "3" and TASKS["T2"]["arat"] == "12")
    chk("R seed 3개 (§6)", len(R_SEEDS) == 3, str(R_SEEDS))
    chk("지표는 2개(K1·K2) — MGA/PV/SPARC/TAM 아님",
        len(KPI) == 2 and "MGA" not in json.dumps(KPI), str(KPI))

    print("[C2] 프롬프트가 §7.1과 일치")
    n = [("k1", 41.0), ("k2", 312.0)]
    p_full = build_prompt("T2", 3.5, n, True)
    p_a4 = build_prompt("T2", 3.5, n, False)
    p_a1 = build_prompt("T1", 3.5, [], True)
    chk("역할 문장 포함(뇌졸중 장애인)", "당신은 뇌졸중 장애인의 상지 기능을" in p_full)
    chk("K1 키 문자열 포함", "thumb_index_surface_p95_mm = 41" in p_full)
    chk("K2 키 문자열 포함", "wrist_surface_speed_p95_mm_s = 312" in p_full)
    chk("null 지침('기능 저하') 포함", "기능 저하나 0값을 뜻하지 않습니다" in p_full)
    chk("'장애나 0값' 옛 문구 없음", "장애나 0값" not in p_full)
    chk("[영상] 제공됨/제공되지 않음 라벨", "[영상]  제공됨" in p_full
        and "[영상]  제공되지 않음" in p_a4)
    chk("A1엔 수치 블록 없음", "[운동학 수치]" not in p_a1)
    chk("출력 지시 포함", "먼저 점수(0/1/2/3) 한 줄" in p_full)

    print("[C3] 조건별 수치 선택 (A2=원값, A3=Q-gated)")
    held = _synth_rec("S01_T2_t01", "S01_세션", 41.0, 312.0,
                      k1_gated=None, k2_gated=None, q_held_k1=True, q_held_k2=False)
    ok = _synth_rec("S01_T2_t02", "S01_세션", 38.0, 280.0)
    chk("A2는 Q-보류 시행에도 원값 제공",
        values_for("A2", held, True, True) == [("k1", 41.0), ("k2", 312.0)],
        str(values_for("A2", held, True, True)))
    chk("A3는 Q-보류 시행을 null 처리",
        values_for("A3", held, True, True) == [("k1", None), ("k2", None)],
        str(values_for("A3", held, True, True)))
    half = _synth_rec("S01_T2_t03", "S01_세션", 35.0, 260.0,
                      k1_gated=None, q_held_k1=True)   # k1만 보류
    chk("일부만 보류되면 그 지표만 null (k2는 값 유지)",
        values_for("A3", half, True, True) == [("k1", None), ("k2", 260.0)],
        str(values_for("A3", half, True, True)))
    chk("A1은 수치 없음", values_for("A1", ok, True, False) == [])
    chk("A4는 A3와 같은 수치", values_for("A4", ok, True, True) == values_for("A3", ok, True, True))

    print("[C4] 오류 주입 (§6.1)")
    v = [("k1", 10.0), ("k2", 100.0)]
    chk("bias_1u = +u", inject(v, "bias_1u", 5.0, False) == [("k1", 15.0), ("k2", 105.0)])
    chk("bias_3u = +3u", inject(v, "bias_3u", 5.0, False) == [("k1", 25.0), ("k2", 115.0)])
    chk("burst_3u 대상 아님 → 원래값",
        inject(v, "burst_3u", 5.0, False) == v)
    chk("burst_3u 대상 → +3u",
        inject(v, "burst_3u", 5.0, True) == [("k1", 25.0), ("k2", 115.0)])
    chk("null 은 주입해도 null",
        inject([("k1", None)], "bias_3u", 5.0, False) == [("k1", None)])

    print("[C5] R 조건: A3 보류 수와 같은 수를 무작위 제거")
    recs = [_synth_rec("S_T1_t1", "S01_x", 10.0, 100.0),
            _synth_rec("S_T1_t2", "S01_x", 11.0, 110.0),
            _synth_rec("S_T1_t3", "S01_x", 12.0, 120.0),
            _synth_rec("S_T2_t1", "S01_x", 13.0, 130.0, k1_gated=None, q_held_k1=True),
            _synth_rec("S_T2_t2", "S01_x", 14.0, 140.0, k1_gated=None, k2_gated=None,
                       q_held_k1=True, q_held_k2=True)]
    rmap, a3_held = r_withheld_map(recs)
    chk("A3 보류 시행 2건 식별", len(a3_held) == 2, str(sorted(a3_held)))
    chk("각 seed가 정확히 2건 제거", all(len(v) == 2 for v in rmap.values()),
        str({k: len(v) for k, v in rmap.items()}))
    chk("seed 3개", len(rmap) == 3)

    print("[C6] 행 생성 수·구조")
    rows = make_rows(recs, u=5.0, burst_trial_index=1)
    n_none = sum(1 for r in rows if r["injection"] == "none")
    n_bias = sum(1 for r in rows if r["injection"] in ("bias_1u", "bias_3u"))
    n_burst = sum(1 for r in rows if r["injection"] == "burst_3u")
    n_r = sum(1 for r in rows if r["condition"] == "R")
    chk("A1·A4는 주입 없음(none)만", all(
        r["injection"] == "none" for r in rows if r["condition"] in ("A1", "A4")))
    chk("R 행 = 시행수 × seed3", n_r == 5 * 3, "R=%d" % n_r)
    chk("bias 행 = A2·A3 × 2수준 × 시행수", n_bias == 2 * 2 * 5, "bias=%d" % n_bias)
    chk("burst 행 = A2·A3 × 시행수", n_burst == 2 * 5, "burst=%d" % n_burst)
    chk("모든 행에 prompt 존재", all(r["prompt"] for r in rows))
    chk("CSV 필드 고정", set(rows[0].keys()) == set(FIELDS), str(sorted(rows[0].keys())))

    print("[C7] 컴퓨트 산식 (§6.1) 재현 — v6.2(72영상) + v6.3(120영상·2모델)")
    def n_vlm(n_videos, n_repeat_videos=0):
        base = n_videos * 4 + n_videos * 3
        inj = n_videos * 2 * 3
        rep = n_repeat_videos * 2
        return base, inj, base + inj, base + inj + rep

    # --- v6.2 회계 (12명 → 72영상) — 이력 검증 ---
    b, i, t, tt = n_vlm(72, 24)
    chk("v6.2: 비주입 504 · 주입 432 · 합 936 · 반복포함 984",
        (b, i, t, tt) == (504, 432, 936, 984), str((b, i, t, tt)))
    chk("구 회계 1,008 은 '원래' 144를 중복 계상한 값",
        1008 - 936 == 72, "1,008-936=72")

    # --- v6.3 회계 (20명 → 120영상, 모델 2개) ---
    chk("v6.3: 영상 120 (=20명×2과제×3시행)", 20 * 2 * 3 == 120, "20*2*3=120")
    b3, i3, t3, tt3 = n_vlm(120, 24)
    chk("v6.3: 비주입 840 · 주입 720 · 합 1,560 · 반복포함 1,608",
        (b3, i3, t3, tt3) == (840, 720, 1560, 1608), str((b3, i3, t3, tt3)))
    chk("v6.3: 2모델 3,216 (=1,608×2)", tt3 * 2 == 3216, "2모델=%d" % (tt3 * 2))

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    print("※ 합성 레코드다. 실제 촬영·VLM 성능이 아니다.")
    try:
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "results", "conditions_v6_oracle.txt")
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with io.open(outp, "w", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
        print("[saved] %s" % os.path.abspath(outp))
    except Exception as e:
        print("[warn] 오라클 로그 저장 실패: %s" % e)
    return ok_all


# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--session", help="세션 폴더 (하나)")
    ap.add_argument("--sessions", nargs="*", default=[], help="세션 폴더들")
    ap.add_argument("--out", default="conditions.csv")
    ap.add_argument("--u-mode", choices=["ratio", "absolute"], default="ratio")
    ap.add_argument("--u-ratios", nargs="*", type=float, default=[0.10, 0.30])
    ap.add_argument("--u-abs", type=float, default=None, help="A안: 실측 P95 절대오차 (mma)")
    ap.add_argument("--burst-trial-index", type=int, default=2)
    a = ap.parse_args()

    if a.selftest:
        return 0 if selftest() else 1

    dirs = ([a.session] if a.session else []) + list(a.sessions)
    if not dirs:
        print(__doc__)
        return 0

    recs = []
    for d in dirs:
        got = load_session(d)
        if not got:
            print("[warn] L2_metric/*.json 없음: %s" % d)
        recs += got
    if not recs:
        print("입력 레코드 0건 — L2_metric 가 생성됐는지 확인하세요.")
        return 1

    ratios = tuple(a.u_ratios) if len(a.u_ratios) >= 1 else (0.10,)
    u = estimate_u(recs, a.u_mode, ratios, a.u_abs)
    rows = make_rows(recs, u=u, burst_trial_index=a.burst_trial_index, u_mode=a.u_mode)
    write_csv(rows, a.out)

    prov = {"generator": "make_conditions_v6.py",
            "plan": "outputs/research-plan-v6.md §6·§7 (v6.2)",
            "sessions": [os.path.basename(os.path.abspath(d.rstrip('/\\'))) for d in dirs],
            "n_trials": len(recs), "n_rows": len(rows),
            "u": u, "u_mode": a.u_mode, "u_ratios": list(ratios),
            "burst_trial_index": a.burst_trial_index,
            "conditions": CONDITIONS, "injections": INJECTIONS, "r_seeds": R_SEEDS}
    with io.open(os.path.splitext(a.out)[0] + ".provenance.json", "w", encoding="utf-8") as f:
        json.dump(prov, f, ensure_ascii=False, indent=1)

    by = {}
    for r in rows:
        by[(r["condition"], r["injection"])] = by.get((r["condition"], r["injection"]), 0) + 1
    print("행 %d개 → %s" % (len(rows), a.out))
    print("  u = %s (%s)" % (("%.4f" % u) if u is not None else "None", a.u_mode))
    for k in sorted(by):
        print("    %-9s %-10s %d" % (k[0], k[1], by[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

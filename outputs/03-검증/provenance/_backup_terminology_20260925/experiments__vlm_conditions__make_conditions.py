# -*- coding: utf-8 -*-
"""
VLM 조건·주입 생성기 — 선생님 파이프라인 데이터 직결판
=========================================================

목적
----
`capstone/.../데이터_저장/<session>/` 의 **실제 산출물**을 읽어서
A0~R 조건 + 오염 주입본의 **VLM 입력과 프롬프트**를 만든다.

이것이 없으면 PR-1(오염 전파)의 입력이 존재하지 않아 주 결과를 계산할 수 없다.

입력 (선생님 파이프라인 산출물)
--------------------------------
  Session_*_trials_summary.csv   : MGA_mm_3D_cal, SPARC, TAM_total_deg, RS_Valid_Rate ...
  qiu_kinematics_summary.csv     : PV_m_s, PAp_mm, TAPV_s, RTS_SPARC ...
  Session_*_metadata.json        : subject, protocol, conventions
  split/index.csv                : task/trial → 폴더·프레임 구간 (영상 위치)

출력
----
  conditions.csv     : (trial × condition × injection × run) 1행 = VLM 입력 1건
  prompts/<key>.txt  : 실제 프롬프트 텍스트
  provenance.json    : u 출처·크기, Q 게이트 결정, seed, 동결 파라미터

조건 (프로토콜 §9)
------------------
  A1 = 영상 + 지침 + T (수치 없음)
  A2 = A1 + 수치 전부
  A3 = A1 + Q 통과 수치만 (미통과는 null)
  A4 = A3와 같은 수치, 영상 없음
  R  = A2에서 **A3와 같은 개수**를 무작위 제거 (seed 3개)
  주입 = A2·A3에만: none / bias_1u / bias_3u / burst_implausible

설계 결정 (동결 필요)
---------------------
1. **수치 세트** = 기본 4개: MGA(파지 벌림), PV(최대 속도), SPARC(부드러움), TAM(총 운동).
   → 계획서는 K1·K2 2개였으나, 실제 파이프라인이 더 풍부하다. **R 조건이 의미를 가지려면
     수치가 3개 이상 필요**(같은 개수 제거 비교)하므로 4개로 둔다. `--metrics`로 변경 가능.
2. **u**: A안(실측, `--u-mode measured`) / B안(기저값 비율, `--u-mode ratio`).
   B안의 기저값 = **세션 내 그 지표의 중앙값**(SPARC는 절대값).
3. **burst 재정의**: 시행 1개만 보는 설계에서 burst≡bias 이므로,
   burst = **물리적으로 불가능한 값**(예: 파지 벌림 260 mm). `--burst-mode implausible`.

실행
----
  python experiments/vlm_conditions/make_conditions.py --selftest
  python experiments/vlm_conditions/make_conditions.py \
      --session-dir "capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남" \
      --u-mode ratio
"""

import argparse
import csv
import glob
import io
import json
import math
import os
import random
import re
import statistics
import sys
import zlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ===========================================================================
# 지표 정의 — 선생님 파이프라인 컬럼명에 맞춘다
# ===========================================================================
METRIC_SPECS = {
    "MGA_mm_3D_cal": {
        "label": "maximum grip aperture",
        "unit": "mm",
        "source": "trials_summary",
        "fallbacks": ["MGA_mm_3D", "MP_MGA_raw_mm", "PAp_mm"],
        "scale": 1.0,
        "plausible": (10.0, 150.0),
        "implausible": 260.0,
        "note": "엄지-검지 최대 벌림(보정). ARAT 구슬은 16 mm, 블록은 50 mm 규모",
    },
    "PV_mm_s": {
        "label": "peak hand velocity",
        "unit": "mm/s",
        "source": "qiu",
        "fallbacks": ["PV_m_s"],
        "scale": 1000.0,                     # m/s → mm/s
        "plausible": (50.0, 2500.0),
        "implausible": 6000.0,
        "note": "도달 최대 속도. 정상 300–800 mm/s",
    },
    "SPARC": {
        "label": "movement smoothness (SPARC)",
        "unit": "a.u.",
        "source": "trials_summary",
        "fallbacks": ["RTS_SPARC"],
        "scale": 1.0,
        "plausible": (-30.0, -0.5),
        "implausible": 2.0,
        "note": "SPARC는 항상 음수. 0에 가까울수록 매끄러움",
    },
    "TAM_total_deg": {
        "label": "total active motion (5 fingers)",
        "unit": "deg",
        "source": "trials_summary",
        "fallbacks": [],
        "scale": 1.0,
        "plausible": (0.0, 1500.0),
        "implausible": 3000.0,
        "note": "5손가락 합. 클수록 좋음",
    },
}
DEFAULT_METRICS = ["MGA_mm_3D_cal", "PV_mm_s", "SPARC", "TAM_total_deg"]

CONDITIONS = ["A1", "A2", "A3", "A4", "R"]
INJECTIONS = ["none", "bias_1u", "bias_3u", "burst_implausible"]
R_SEEDS = [20260922, 20260923, 20260924]

TASKS_ARAT = {           # 과제 이름 → ARAT 항목·물체 (프롬프트용)
    "cylinder": ("12", "원통형 파지 (참고: ARAT 12번 계열)"),
    "free": ("3", "맨손 쥐기/펴기 (참고: ARAT 3번 계열)"),
    "default": ("-", "상지 과제"),
}


# ===========================================================================
# 입력 읽기
# ===========================================================================
def read_csv_rows(path):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def find_one(session_dir, pattern):
    hits = sorted(glob.glob(os.path.join(session_dir, pattern)))
    return hits[0] if hits else None


def load_session(session_dir):
    ts = find_one(session_dir, "Session_*_trials_summary.csv")
    qiu = find_one(session_dir, "qiu_kinematics_summary.csv")
    meta = find_one(session_dir, "Session_*_metadata.json")
    idx = find_one(session_dir, os.path.join("split", "index.csv"))
    out = {"dir": session_dir,
           "trials": read_csv_rows(ts) if ts else [],
           "qiu": read_csv_rows(qiu) if qiu else [],
           "index": read_csv_rows(idx) if idx else [],
           "paths": {"trials": ts, "qiu": qiu, "metadata": meta, "index": idx}}
    if meta:
        with io.open(meta, encoding="utf-8") as f:
            out["metadata"] = json.load(f)
    else:
        out["metadata"] = {}
    return out


def metric_value(session, metric, trial_row, qiu_row):
    """지표 1개의 값 + 출처 컬럼명. 없으면 (None, None)."""
    spec = METRIC_SPECS[metric]
    src_rows = {"trials_summary": trial_row, "qiu": qiu_row}
    row = src_rows.get(spec["source"], {})
    for col in [metric] + spec["fallbacks"]:
        if row and col in row:
            v = (row.get(col) or "").strip()
            if v not in ("", "None", "nan"):
                try:
                    return float(v) * spec["scale"], col
                except ValueError:
                    pass
    return None, None


def norm_trial(name):
    """'Trial #1' <-> 'Trial_1' 표기 차이를 흡수한다."""
    t = (name or "").strip()
    return t.replace("#", "").replace(" ", "_").replace("__", "_")


def task_key(name):
    """'Task 1' 과 'Task 1: 맨손 쥐기/펴기 (Free Motion)' 를 같은 키로 만든다.

    실측: trials_summary 는 'Task 1', split/index.csv 는 긴 이름을 쓴다.
    """
    m = re.match(r"\s*Task\s*(\d+)", name or "", re.I)
    if m:
        return "T" + m.group(1)
    return (name or "").strip().lower()


def resolve_task_full(session, short_name):
    """짧은 과제명 → index.csv 의 긴 과제명(프롬프트 라벨용)."""
    k = task_key(short_name)
    for r in session.get("index", []):
        if task_key(r.get("task")) == k:
            return (r.get("task") or short_name).strip()
    return (short_name or "").strip()


def resolve_video(session, task_name, trial_name):
    """split/index.csv 의 folder 열로 영상 경로를 찾는다.

    ⚠️ `_mediapipe.avi`(랜드마크 오버레이)가 아니라 **`_original.avi`** 를 골라야 한다.
       오버레이 영상을 VLM에 주면 랜드마크가 영상에 그려져 있어
       모델이 수치 없이도 벌림을 읽을 수 있고, A1과 A2/A3의 비교가 무효가 된다.
    """
    want = norm_trial(trial_name)
    for r in session.get("index", []):
        if task_key(r.get("task")) == task_key(task_name) and norm_trial(r.get("trial")) == want:
            folder = r.get("folder", "")
            cands = []
            for ext in ("*.avi", "*.mp4", "*.mkv", "*.mov"):
                cands += glob.glob(os.path.join(session["dir"], folder, ext))
            if not cands:
                return None
            orig = [c for c in cands if "original" in os.path.basename(c).lower()]
            return (orig or cands)[0]
    return None


# ===========================================================================
# Q 게이트
# ===========================================================================
def q_gate(trial_row, q1_min=0.7, min_paired=50, diff_max_mm=None,
           q_mode="mp", min_samples=50):
    """프로토콜 §8의 Q 규칙 (선생님 컬럼명 기준). 반환 (bool, reasons).

    q_mode='mp' (기본): **MediaPipe 기반 지표의 가용성**으로 게이트.
        - RS_Valid_Rate가 낮은 세션(실측: 0.16~0.63)에서는 rs 모드를 쓰면 전부 보류된다.
        - 게이트: MP 샘플 수 >= min_samples  (지표 존재 여부는 별도로 확인)
    q_mode='rs': RealSense 깊이 유효성으로 게이트.
        - RS_Valid_Rate >= q1_min, Paired_Samples >= min_paired
        - ⚠️ `Interrupted`는 **게이트에서 제외**한다(수동 종료 모드에서 1이 정상).
    """
    reasons = []
    def num(k):
        v = (trial_row.get(k) or "").strip()
        try:
            return float(v)
        except ValueError:
            return None
    if q_mode == "rs":
        rate = num("RS_Valid_Rate")
        paired = num("Paired_Samples")
        if rate is None:
            reasons.append("Q1(RS_Valid_Rate 없음)")
        elif rate < q1_min:
            reasons.append("Q1(%.2f<%.2f)" % (rate, q1_min))
        if paired is None or paired < min_paired:
            reasons.append("Q3(Paired_Samples=%s<%d)" % (paired, min_paired))
        diff = num("RS_MP_mean_abs_difference_mm")
        if diff_max_mm is not None and diff is not None and diff > diff_max_mm:
            reasons.append("Q4(MP-RS 불일치 %.1fmm>%.1fmm)" % (diff, diff_max_mm))
    else:
        samples = num("Samples")
        if samples is None or samples < min_samples:
            reasons.append("Q1(MP Samples=%s<%d)" % (samples, min_samples))
    return (len(reasons) == 0), reasons


# ===========================================================================
# u 결정
# ===========================================================================
def compute_u(session, metrics, u_mode="ratio", ratios=(0.10, 0.30),
              measured=None):
    """지표별 u(1단위)와 사용 출처. B안 기저값 = 세션 중앙값(SPARC는 |·|)."""
    values = {m: [] for m in metrics}
    for tr in session["trials"]:
        qr = match_qiu(session, tr)
        for m in metrics:
            v, _ = metric_value(session, m, tr, qr)
            if v is not None:
                values[m].append(v)
    u1, baseline, src = {}, {}, {}
    for m in metrics:
        vs = values[m]
        if not vs:
            baseline[m] = None
            u1[m] = None
            src[m] = "없음"
            continue
        med = statistics.median(vs)
        baseline[m] = med
        if u_mode == "measured" and measured and m in measured:
            u1[m] = float(measured[m])
            src[m] = "A안(실측)"
        else:
            base = abs(med) if abs(med) > 1e-9 else 1.0
            u1[m] = ratios[0] * base
            src[m] = "B안(기저값 %.0f%%" % (ratios[0] * 100) + ")"
    return u1, baseline, src


def match_qiu(session, trial_row):
    """Trial + Hand 로 qiu 행을 찾는다."""
    t = (trial_row.get("Trial") or "").strip()
    h = (trial_row.get("Hand") or "").strip()
    for r in session["qiu"]:
        if (r.get("Trial") or "").strip() == t and (r.get("Hand") or "").strip() == h:
            return r
    for r in session["qiu"]:
        if (r.get("Trial") or "").strip() == t:
            return r
    return {}


# ===========================================================================
# 주입
# ===========================================================================
def inject(metric, value, injection, u1):
    """(새 값, 설명). value=None이면 그대로 None."""
    if value is None:
        return None, "held"
    spec = METRIC_SPECS[metric]
    if injection == "none":
        return value, "none"
    if injection == "bias_1u":
        return value + 1.0 * u1[metric], "+1u(%.3g)" % u1[metric]
    if injection == "bias_3u":
        return value + 3.0 * u1[metric], "+3u(%.3g)" % (3 * u1[metric])
    if injection == "burst_implausible":
        return spec["implausible"], "implausible(%.3g %s)" % (spec["implausible"], spec["unit"])
    raise ValueError(injection)


def r_hold_set(metrics, held_in_a3, seed):
    """R 조건: A3가 보류한 개수와 **같은 개수**를 무작위로 제거.

    - A3가 0개 보류 → R도 0개 제거 (그 시행은 R 비교가 무의미 → '정보 없음')
    - A3가 전부 보류 → **R도 전부 제거** (R ≡ A3, 역시 정보 없음)
    - 그 외 → A3가 보유한 지표 중에서 무작위 (A3와 겹치지 않게)
    """
    n = len(held_in_a3)
    if n == 0:
        return set(), 0
    if n >= len(metrics):
        return set(metrics), n
    candidates = [m for m in metrics if m not in held_in_a3]
    rng = random.Random(seed)
    if len(candidates) >= n:
        return set(rng.sample(candidates, n)), n
    return set(rng.sample(metrics, n)), n


# ===========================================================================
# 프롬프트
# ===========================================================================
PROMPT_HEAD = """당신은 뇌졸중 환자의 상지 기능을 영상으로 평가하는 임상 평가자입니다.

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
PROMPT_NUMBERS_NOTE = "[지침]  null은 신뢰 가능한 추정이 없다는 뜻이며, 장애나 0값이 아닙니다.\n"
PROMPT_TAIL = "\n[출력]  먼저 점수(0/1/2/3) 한 줄, 그 다음 최대 2문장의 근거.\n"""

INSTRUCTIONS = {
    "cylinder": "원통형 물체를 잡아 들어 올려 지정된 위치에 놓으세요.",
    "free": "손을 쥐었다 펴세요.",
    "default": "화면에 보이는 과제를 수행하세요.",
}


def task_kind(task_name):
    t = (task_name or "").lower()
    if "cylinder" in t or "원통" in t:
        return "cylinder"
    if "free" in t or "맨손" in t or "쥐기" in t:
        return "free"
    return "default"


def build_prompt(task_name, T, numbers, video_provided):
    kind = task_kind(task_name)
    label = "%s — %s" % (task_name, TASKS_ARAT[kind][1])
    lines = [PROMPT_HEAD.format(task_label=label,
                               instruction=INSTRUCTIONS.get(kind, INSTRUCTIONS["default"]),
                               T=("%.2f" % T) if T is not None else "미상")]
    if numbers and any(v is not None for _, v, _ in numbers):
        lines.append(PROMPT_NUMBERS_HEAD)
        for name, val, unit in numbers:
            lines.append("  %s = %s %s\n" % (name, ("null" if val is None else "%.4g" % val), unit))
        lines.append(PROMPT_NUMBERS_NOTE)
    lines.append("\n[영상]  %s\n" % ("제공됨" if video_provided else "제공되지 않음 (수치만으로 판단)"))
    lines.append(PROMPT_TAIL)
    return "".join(lines)


# ===========================================================================
# 메인 생성
# ===========================================================================
def make_conditions(session, metrics=None, u_mode="ratio", ratios=(0.10, 0.30),
                    measured_u=None, q1_min=0.7, min_paired=50, diff_max_mm=None,
                    out_dir=".", pid=None, write=True, q_mode="mp", min_samples=50):
    metrics = metrics or DEFAULT_METRICS
    u1, baseline, u_src = compute_u(session, metrics, u_mode, ratios, measured_u)
    pid = pid or os.path.basename(session["dir"].rstrip("/\\")).split("_")[0]
    rows, prompts, prov = [], {}, {}

    for tr in session["trials"]:
        trial_name = (tr.get("Trial") or "").strip()
        task_name = (tr.get("Task") or "").strip()
        hand = (tr.get("Hand") or "").strip()
        if not trial_name:
            continue
        qr = match_qiu(session, tr)
        passed, q_reasons = q_gate(tr, q1_min, min_paired, diff_max_mm,
                                   q_mode=q_mode, min_samples=min_samples)

        def num(k):
            v = (tr.get(k) or "").strip()
            try:
                return float(v)
            except ValueError:
                return None
        T = num("Valid_Duration_s")
        if T is None:
            T = num("Duration_s")
        video = resolve_video(session, task_name, trial_name)
        task_full = resolve_task_full(session, task_name)

        base_vals, base_cols = {}, {}
        for m in metrics:
            v, col = metric_value(session, m, tr, qr)
            base_vals[m] = v
            base_cols[m] = col

        a3_vals = {m: (base_vals[m] if passed else None) for m in metrics}
        held_in_a3 = set(m for m in metrics if a3_vals[m] is None)

        for cond in CONDITIONS:
            seeds = R_SEEDS if cond == "R" else [R_SEEDS[0]]
            for seed in seeds:
                r_held, r_n = r_hold_set(metrics, held_in_a3, seed)
                if cond == "A1":
                    vals, inj = {m: None for m in metrics}, "none"
                elif cond == "A2":
                    vals, inj = dict(base_vals), "none"
                elif cond == "A3":
                    vals, inj = dict(a3_vals), "none"
                elif cond == "A4":
                    vals, inj = dict(a3_vals), "none"
                else:  # R
                    vals = {m: (None if m in r_held else base_vals[m]) for m in metrics}
                    inj = "none"

                # A2·A3 에만 주입
                if cond in ("A2", "A3"):
                    inj_list = INJECTIONS
                else:
                    inj_list = ["none"]
                for injection in inj_list:
                    vv, notes = {}, {}
                    for m in metrics:
                        vv[m], notes[m] = inject(m, vals[m], injection, u1)
                    numbers = [(m, vv[m], METRIC_SPECS[m]["unit"]) for m in metrics]
                    video_provided = (cond != "A4")
                    key = "%s_%s_%s_%s_%s_s%d" % (
                        pid, task_kind(task_name), hand, trial_name.replace(" ", ""),
                        cond, seed)
                    key = key + ("_" + injection if injection != "none" else "")
                    prompt = build_prompt(task_full, T, numbers, video_provided)
                    rows.append({
                        "key": key, "pid": pid, "session": os.path.basename(session["dir"]),
                        "trial": trial_name, "hand": hand, "task": task_full,
                        "condition": cond, "injection": injection, "r_seed": seed,
                        "video": video or "", "n_numbers": sum(1 for m in metrics if vv[m] is not None),
                        "held": ";".join(m for m in metrics if vv[m] is None),
                        "q_pass": int(passed), "q_reasons": ";".join(q_reasons),
                        "T_s": T,
                        **{("v_" + m): ("" if vv[m] is None else "%.6g" % vv[m]) for m in metrics},
                        "inject_notes": ";".join("%s:%s" % (m, notes[m]) for m in metrics),
                        "prompt_path": os.path.join("prompts", key + ".txt"),
                    })
                    prompts[key] = prompt

    prov = {
        "session_dir": session["dir"],
        "pid": pid,
        "metrics": metrics,
        "u_mode": u_mode,
        "u1": u1, "baseline": baseline, "u_source": u_src,
        "q_gate": {"mode": q_mode, "q1_min": q1_min, "min_paired": min_paired,
                   "diff_max_mm": diff_max_mm, "min_samples": min_samples},
        "r_seeds": R_SEEDS,
        "n_rows": len(rows),
        "design_notes": [
            "burst는 물리적으로 불가능한 값으로 정의(시행 1개만 보는 설계에서 bias와 중복되므로)",
            "R은 A3가 보류한 개수와 같은 개수를 비보류 지표 중에서 무작위 제거",
            "A4는 A3와 같은 수치, 영상만 제외",
            "조건명은 프롬프트에 쓰지 않는다",
        ],
    }

    if write:
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, "prompts"), exist_ok=True)
        cols = ["key", "pid", "session", "trial", "hand", "task", "condition",
                "injection", "r_seed", "video", "n_numbers", "held", "q_pass",
                "q_reasons", "T_s"] + ["v_" + m for m in metrics] + \
               ["inject_notes", "prompt_path"]
        with io.open(os.path.join(out_dir, "conditions.csv"), "w",
                     encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        for k, p in prompts.items():
            with io.open(os.path.join(out_dir, "prompts", k + ".txt"), "w",
                         encoding="utf-8") as f:
                f.write(p)
        with io.open(os.path.join(out_dir, "provenance.json"), "w",
                     encoding="utf-8") as f:
            json.dump(prov, f, ensure_ascii=False, indent=2)
    return rows, prompts, prov


# ===========================================================================
# 오라클
# ===========================================================================
def selftest():
    ok_all, log = True, []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-52s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    # 합성 세션: 4시행, 그중 1개는 Q 미통과
    trials = []
    for i in range(1, 5):
        trials.append({
            "Trial": "Trial #%d" % i, "Hand": "Right",
            "Task": "Task 1: 맨손 쥐기/펴기 (Free Motion)",
            "Duration_s": "8.0", "Valid_Duration_s": "7.5",
            "MGA_mm_3D_cal": "%.1f" % (60 + i),      # 61,62,63,64
            "SPARC": "-2.0", "TAM_total_deg": "900",
            "RS_Valid_Rate": "0.9", "Paired_Samples": "120", "Interrupted": "0",
            "RS_MP_mean_abs_difference_mm": "8.0",
            "Samples": "120" if i != 3 else "20",        # 3번은 MP 샘플 부족 → 미통과
        })
    qiu = [{"Trial": "Trial #%d" % i, "Hand": "Right", "PV_m_s": "0.45"} for i in range(1, 5)]
    sess = {"dir": "/tmp/synth", "trials": trials, "qiu": qiu, "index": [],
            "metadata": {}, "paths": {}}
    metrics = ["MGA_mm_3D_cal", "PV_mm_s", "SPARC", "TAM_total_deg"]

    rows, prompts, prov = make_conditions(sess, metrics=metrics, u_mode="ratio",
                                          out_dir=None, write=False, q_mode="mp")
    by = {}
    for r in rows:
        by.setdefault((r["trial"], r["condition"], r["injection"], r["r_seed"]), []).append(r)

    print("[C1] A1은 수치 없음 / A2는 전부 / A3는 Q 통과만")
    a1 = [r for r in rows if r["condition"] == "A1"]
    a2 = [r for r in rows if r["condition"] == "A2" and r["injection"] == "none"]
    a3 = [r for r in rows if r["condition"] == "A3" and r["injection"] == "none"]
    chk("A1 전부 n_numbers=0", all(r["n_numbers"] == 0 for r in a1))
    chk("A2 전부 n_numbers=4", all(r["n_numbers"] == 4 for r in a2))
    t3 = [r for r in a3 if r["trial"] == "Trial #3"][0]
    t1 = [r for r in a3 if r["trial"] == "Trial #1"][0]
    chk("Q 미통과 시행은 A3에서 n_numbers=0", t3["n_numbers"] == 0, str(t3["q_reasons"]))
    chk("Q 통과 시행은 A3에서 n_numbers=4", t1["n_numbers"] == 4)

    print("[C2] bias 주입 = 정확히 +1u / +3u")
    base = float(t1["v_MGA_mm_3D_cal"])
    u_mga = prov["u1"]["MGA_mm_3D_cal"]
    b1 = [r for r in rows if r["trial"] == "Trial #1" and r["condition"] == "A3"
          and r["injection"] == "bias_1u"][0]
    b3 = [r for r in rows if r["trial"] == "Trial #1" and r["condition"] == "A3"
          and r["injection"] == "bias_3u"][0]
    chk("bias_1u == base+1u", abs(float(b1["v_MGA_mm_3D_cal"]) - (base + u_mga)) < 1e-6,
        "%.4f vs %.4f" % (float(b1["v_MGA_mm_3D_cal"]), base + u_mga))
    chk("bias_3u == base+3u", abs(float(b3["v_MGA_mm_3D_cal"]) - (base + 3 * u_mga)) < 1e-6)
    chk("B안 u = 중앙값의 10%", abs(u_mga - 0.10 * statistics.median([61, 62, 63, 64])) < 1e-6,
        "u=%.4f" % u_mga)

    print("[C3] burst = 물리적으로 불가능한 값")
    bs = [r for r in rows if r["trial"] == "Trial #1" and r["condition"] == "A3"
          and r["injection"] == "burst_implausible"][0]
    chk("MGA == 260 mm", abs(float(bs["v_MGA_mm_3D_cal"]) - 260.0) < 1e-9)
    chk("SPARC == +2.0 (부호 불가능)", abs(float(bs["v_SPARC"]) - 2.0) < 1e-9)
    chk("burst는 bias와 값이 다름", abs(float(bs["v_MGA_mm_3D_cal"]) - float(b3["v_MGA_mm_3D_cal"])) > 1.0)

    print("[C4] R = A3와 같은 개수 제거, seed 3개 재현")
    t1_held = int(t1["n_numbers"])
    r_rows = [r for r in rows if r["trial"] == "Trial #1" and r["condition"] == "R"]
    chk("R 시행 수 = 3 seed", len(r_rows) == 3, str(len(r_rows)))
    a3_held_n = 4 - t1_held
    chk("R의 제공 개수 = A2 − A3보류개수", all(r["n_numbers"] == 4 - a3_held_n for r in r_rows),
        str([r["n_numbers"] for r in r_rows]))
    rows2, _, _ = make_conditions(sess, metrics=metrics, u_mode="ratio", write=False,
                                       q_mode="mp")
    r2 = [r for r in rows2 if r["trial"] == "Trial #1" and r["condition"] == "R"]
    chk("동일 seed → 동일 결과(재현성)",
        [r["held"] for r in r_rows] == [r["held"] for r in r2])
    # Q 미통과 시행: A3가 4개 전부 보류 → R도 4개 보류
    t3r = [r for r in rows if r["trial"] == "Trial #3" and r["condition"] == "R"]
    chk("A3가 전부 보류면 R도 전부 보류", all(r["n_numbers"] == 0 for r in t3r))

    print("[C5] 프롬프트 규칙")
    p_a1 = [p for k, p in prompts.items() if "_A1_" in k][0]
    p_a3 = [p for k, p in prompts.items() if "_A3_" in k and "bias" not in k
            and "burst" not in k][0]
    chk("A1 프롬프트에 [운동학 수치] 없음", "[운동학 수치]" not in p_a1)
    chk("A3 프롬프트에 수치 있음", "[운동학 수치]" in p_a3)
    chk("null 지침 문구 포함", "장애나 0값이 아닙니다" in p_a3)
    chk("조건명이 프롬프트에 없음", ("A3" not in p_a3 and "A1" not in p_a1))
    p_a4 = [p for k, p in prompts.items() if "_A4_" in k][0]
    chk("A4는 '영상 제공되지 않음'", "제공되지 않음" in p_a4)

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "conditions_oracle.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("[saved] %s" % out)
    return ok_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--session-dir")
    ap.add_argument("--out", default="vlm_conditions_out")
    ap.add_argument("--metrics", default=",".join(DEFAULT_METRICS))
    ap.add_argument("--u-mode", default="ratio", choices=["ratio", "measured"])
    ap.add_argument("--ratios", type=float, nargs=2, default=[0.10, 0.30])
    ap.add_argument("--q1-min", type=float, default=0.7)
    ap.add_argument("--min-paired", type=int, default=50)
    ap.add_argument("--diff-max-mm", type=float, default=None)
    ap.add_argument("--q-mode", default="mp", choices=["mp", "rs"])
    ap.add_argument("--min-samples", type=int, default=50)
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.session_dir:
        print(__doc__); return

    sess = load_session(a.session_dir)
    print("세션: %s" % a.session_dir)
    print("  trials_summary: %d행 / qiu: %d행 / index: %d행"
          % (len(sess["trials"]), len(sess["qiu"]), len(sess["index"])))
    metrics = [m.strip() for m in a.metrics.split(",") if m.strip()]
    rows, prompts, prov = make_conditions(
        sess, metrics=metrics, u_mode=a.u_mode, ratios=tuple(a.ratios),
        q1_min=a.q1_min, min_paired=a.min_paired, diff_max_mm=a.diff_max_mm,
        out_dir=a.out, q_mode=a.q_mode, min_samples=a.min_samples)
    print("  생성: 조건 %d건 / 프롬프트 %d개" % (len(rows), len(prompts)))
    print("  u 모드: %s" % a.u_mode)
    for m in metrics:
        print("    %-18s u1=%.4g  (%s)" % (m, prov["u1"][m] or float("nan"),
                                           prov["u_source"][m]))
    print("  출력: %s/{conditions.csv, prompts/, provenance.json}" % a.out)


if __name__ == "__main__":
    main()

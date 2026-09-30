# -*- coding: utf-8 -*-
"""VLM 조건·프롬프트 생성기 v7 — 지표 세트 M1·M2·M4 (2026-09-30 전면 재작성).

지표(계획서 §7.6):
  M1 = K1_mp       엄지끝·검지끝 MediaPipe world landmark 거리 P95 (mm)
  M2 = TAM_total   5지 총굴곡 (deg, 앱 산출)
  M4 = SPARC       clock_v3 정의 (무차원)
  (M3 = MGA 는 보조·기록용 → **프롬프트에 넣지 않는다**)

입력: L2_metric/*.json (experiments/metrics/l2_from_app.py 산출)
출력: conditions.csv (+ provenance)

규칙:
  · A1=영상만 / A2=M1·M2·M4 전부 / A3=A2에서 Q 미통과 지표만 null / A4=A3에서 영상 제거 / R=A2에서 A3와 같은 수를 무작위 제거
  · 주입(bias_1u/bias_3u/burst_3u)은 **A2·A3만**, **지표별 u**
  · 조건명은 프롬프트에 쓰지 않는다. 과제·지시문·채점기준·파지조건·낙하규칙은 모든 조건 동일

사용:
  python experiments/vlm_conditions/make_conditions_v6.py --selftest
  python experiments/vlm_conditions/make_conditions_v6.py --sessions <S1> <S2> --out conditions.csv
"""
import argparse
import csv
import glob
import io
import json
import os
import random
import sys

CONDITIONS = ["A1", "A2", "A3", "A4", "R"]
INJECTIONS = ["none", "bias_1u", "bias_3u", "burst_3u"]

# 지표 슬롯 → (L2 필드, 프롬프트 키, 단위, 가용 플래그)
METRICS = {
    "m1": ("m1_mga_mm", "mga_mm", "mm"),
    "m2": ("m2_tam_total_deg", "tam_total_deg", "deg"),
    "m4": ("m4_sparc", "sparc", "1"),
}
METRIC_ORDER = ("m1", "m2", "m4")
R_SEEDS = [20260922, 20260923, 20260924]

# 주입 부호: "나빠지는 방향". M4(SPARC)는 ≤0이고 더 음수일수록 거칠다 → -1.
SIGN = {"m1": +1.0, "m2": +1.0, "m4": -1.0}

# ---- 프롬프트 (계획서 §9.1 과 문자 단위 동일) ----
PROMPT_HEAD = """당신은 뇌졸중 장애인의 상지 기능을 영상으로 평가하는 임상 평가자입니다.

[과제]  {task_label}
[지시문]  {instruction}
[파지 조건]  {grasp_condition}
[채점 기준]
  3 = 5초 이내 정상 수행 + 정상 손·팔 움직임 + 자세 유지 (+T2: 손가락 패드로 맞섬)
  2 = 완료했으나 5–60초 또는 큰 어려움 (잘못된 손·팔 움직임, 해제 실패, +T2: 패드 미사용)
  1 = 60초 내 부분 수행 (들어올렸으나 목표 높이/놓기 미완)
  0 = 60초 내 어떤 부분도 못함 (+T2: 잘못된 손가락 맞섬)
[낙하 규칙]  물체를 떨어뜨렸더라도 다시 집어 수행하면 최선 수행으로 평가합니다(낙하 자체는 감점이 아님).
             다만 60초 안에 완료되지 못하면 부분 수행입니다. 과제를 성공적으로 끝낸 뒤 물체가 떨어지면 감점하지 않습니다.
[관찰 구간]  T = {T} 초
"""

GRASP_COND = {
    "T1": "손가락 사용 제한 없음. 단 엄지와 다른 손가락의 맞섬(opposition)이 포함된 파지여야 함.",
    "T2": "반드시 엄지와 검지의 맞섬이어야 함. 잘못된 맞섬이면 점수는 0. "
          "3점은 손가락 패드로 맞섬한 경우에만 가능.",
}

TASKS = {
    "T1": {"arat": "3", "object": "5 cm 목재 블록 55 g",
           "instruction": "grasp the block that I have placed here, lift it up, "
                          "and place then release it on top of that shelf."},
    "T2": {"arat": "12", "object": "구슬 지름 1.6 cm 5.4 g",   # Yozbatiran Table A2 (D-19)
           "instruction": "grasp the marble using these fingers, lift it up, "
                          "and place it in the tin on top of that shelf."},
}

NULL_NOTE = ("[지침]  null은 신뢰 가능한 추정이 없다는 뜻이며, "
             "기능 저하나 0값을 뜻하지 않습니다.")


def task_label(task):
    t = TASKS[task]
    return "ARAT %s번 — %s" % (t["arat"], t["object"])


def build_prompt(task, T, numbers, video_provided):
    """numbers = [('m1', 값|None), ...] (A1은 [])."""
    lines = [PROMPT_HEAD.format(task_label=task_label(task),
                                instruction=TASKS[task]["instruction"],
                                grasp_condition=GRASP_COND[task],
                                T=("%.2f" % T) if T is not None else "미상")]
    if numbers:
        lines.append("\n[운동학 수치]\n")
        for key, val in numbers:
            lines.append("  %s = %s\n" % (METRICS[key][1],
                                          "null" if val is None else "%.4g" % val))
        lines.append(NULL_NOTE + "\n")
    lines.append("\n[영상]  %s\n" % ("제공됨" if video_provided
                                     else "제공되지 않음 (수치만으로 판단)"))
    lines.append("\n[출력]  먼저 점수(0/1/2/3) 한 줄, 그 다음 최대 2문장의 근거.\n")
    return "".join(lines)


# ---------------------------------------------------------------- 값 선택
def raw_values(rec):
    return [(k, rec.get(METRICS[k][0])) for k in METRIC_ORDER]


def gated_values(rec):
    avail = rec.get("available") or {}
    return [(k, rec.get(METRICS[k][0]) if avail.get(k) else None) for k in METRIC_ORDER]


def values_for(condition, rec):
    if condition == "A1":
        return []
    if condition == "A2":
        return raw_values(rec)
    return gated_values(rec)          # A3·A4는 Q-gated


# ---------------------------------------------------------------- 주입
def _u_for(u_map, key):
    return u_map.get(key) if isinstance(u_map, dict) else u_map


def inject(values, injection, u_map, is_burst_target):
    """지표별 u. 주입 불가(u 없음)면 **원값 유지**(결측으로 바꾸지 않음)."""
    if not values or injection == "none":
        return values
    factor = {"bias_1u": 1.0, "bias_3u": 3.0, "burst_3u": 3.0}.get(injection)
    if factor is None:
        raise ValueError("unknown injection: %s" % injection)
    if injection == "burst_3u" and not is_burst_target:
        return values
    out = []
    for k, v in values:
        u = _u_for(u_map, k)
        out.append((k, v if (v is None or u is None)
                    else v + factor * u * SIGN.get(k, 1.0)))
    return out


def _p95(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    pos = 0.95 * (len(v) - 1)
    lo, hi = int(pos), min(int(pos) + 1, len(v) - 1)
    return v[lo] * (1 - (pos - lo)) + v[hi] * (pos - lo)


def estimate_u(recs, mode, ratios=(0.10, 0.30), abs_u=None):
    """지표별 dict. A안=실측 절대오차(abs_u), B안=기저 P95 × 비율."""
    if abs_u is not None:
        return {k: float(abs_u[k]) for k in METRIC_ORDER}
    ratio = min(ratios)   # B안: u = 기저 P95의 10% → bias_1u=+10% · bias_3u=+30%(계획서 §5-17)
    out = {}
    for k in METRIC_ORDER:
        field = METRICS[k][0]
        base = _p95([r.get(field) for r in recs])
        out[k] = None if base is None else abs(base) * ratio   # u 는 크기(비음수)
    return out


# ---------------------------------------------------------------- 입력
def load_session(session_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(session_dir, "L2_metric", "*.json"))):
        with io.open(p, encoding="utf-8") as f:
            rec = json.load(f)
        rec.setdefault("trial_id", os.path.basename(p)[:-5])
        rec["_session"] = os.path.basename(os.path.abspath(session_dir.rstrip("/\\")))
        rec["_path"] = p
        out.append(rec)
    return out


def participant_of(rec):
    return rec.get("_session", "")


def task_of(rec):
    tid = rec.get("trial_id", "")
    m = [s for s in tid.split("_") if s in TASKS]
    return m[0] if m else "T1"


def trial_index_of(rec):
    tid = rec.get("trial_id", "")
    for s in tid.split("_"):
        if s.lower().startswith("t") and s[1:].isdigit():
            return int(s[1:])
    return 1


def _video_name(rec):
    return os.path.splitext(os.path.basename(rec.get("_path", "")))[0] + ".mp4"


# ---------------------------------------------------------------- R 배정
def r_withheld_map(recs, seeds=R_SEEDS):
    """M1·M2·M4 각각: **원값이 있는 전체 후보 P**에서, A3가 버린 수와 같은 수를 무작위 제거."""
    P = {k: [] for k in METRIC_ORDER}
    n_held = {k: 0 for k in METRIC_ORDER}
    for r in recs:
        key = (r["trial_id"], task_of(r))
        avail = r.get("available") or {}
        for k in METRIC_ORDER:
            if r.get(METRICS[k][0]) is None:
                continue                       # 하드 결측은 P에서 제외
            P[k].append(key)
            if not avail.get(k):
                n_held[k] += 1                 # Q가 보류
    out = {}
    for sd in seeds:
        rnd = random.Random(sd)
        out[sd] = {}
        for k in METRIC_ORDER:
            pool = list(P[k])
            rnd.shuffle(pool)
            out[sd][k] = set(pool[:n_held[k]])
    return out, n_held


def make_rows(recs, u, burst_trial_index=2, u_mode="ratio"):
    rows = []
    rmap, n_held = r_withheld_map(recs)
    for rec in recs:
        pid, task, ti = participant_of(rec), task_of(rec), trial_index_of(rec)
        T = rec.get("observation_window_s")
        video = _video_name(rec)
        is_burst = (ti == burst_trial_index)
        for cond in CONDITIONS:
            if cond == "R":
                key = (rec["trial_id"], task)
                for sd, rm in rmap.items():
                    vals = [(k, None if key in rm[k] else rec.get(METRICS[k][0]))
                            for k in METRIC_ORDER]
                    rows.append(_row(cond, "none", sd, pid, task, ti, rec, vals, T,
                                     cond != "A4", u, u_mode, video))
                continue
            injs = INJECTIONS if cond in ("A2", "A3") else ["none"]
            for inj in injs:
                base = values_for(cond, rec)
                rows.append(_row(cond, inj, "", pid, task, ti, rec,
                                 inject(base, inj, u, is_burst), T,
                                 cond != "A4", u, u_mode, video))
    return rows


def _row(cond, inj, seed, pid, task, ti, rec, vals, T, video_provided, u, u_mode, video):
    got = dict(vals)
    row = {
        "condition": cond, "injection": inj, "r_seed": seed,
        "participant": pid, "task": task, "trial_index": ti, "trial_id": rec["trial_id"],
        "video": video, "n_numbers": len(vals),
        "video_provided": int(video_provided),
        "prompt": build_prompt(task, T, vals, video_provided),
    }
    for k in METRIC_ORDER:
        v = got.get(k) if vals else None
        row[k] = "" if v is None else v
        row[k + "_provided"] = int(k in got and got[k] is not None)
        uk = _u_for(u, k)
        row["u_%s_used" % k] = "" if uk is None else round(uk, 6)
    row["u_mode"] = u_mode
    return row


FIELDS = (["condition", "injection", "r_seed", "participant", "task", "trial_index",
           "trial_id", "video", "n_numbers", "video_provided"]
          + sum([[k, k + "_provided", "u_%s_used" % k] for k in METRIC_ORDER], [])
          + ["u_mode", "prompt"])


def write_csv(rows, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- 오라클
def _rec(tid, sess, m1, m2, m4, a1=True, a2=True, a4=True, T=3.5):
    return {"trial_id": tid, "_session": sess, "_path": "/x/%s.json" % tid,
            "m1_mga_mm": m1, "m2_tam_total_deg": m2, "m4_sparc": m4,
            "observation_window_s": T,
            "available": {"m1": a1, "m2": a2, "m4": a4}}


def selftest():
    ok_all, log = True, []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-56s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    print("[C1] 상수·지표·과제")
    chk("조건 A1·A2·A3·A4·R", CONDITIONS == ["A1", "A2", "A3", "A4", "R"])
    chk("주입 3수준+none", INJECTIONS == ["none", "bias_1u", "bias_3u", "burst_3u"])
    chk("지표 = M1·M2·M4 (M3 제외)", METRIC_ORDER == ("m1", "m2", "m4"), str(METRIC_ORDER))
    chk("프롬프트 키 = mga_mm·tam_total_deg·sparc",
        [METRICS[k][1] for k in METRIC_ORDER] == ["mga_mm", "tam_total_deg", "sparc"])
    chk("M1 단위 mm · M2 deg · M4 무차원",
        (METRICS["m1"][2], METRICS["m2"][2], METRICS["m4"][2]) == ("mm", "deg", "1"))
    chk("T2 물성 = 구슬 1.6 cm", "1.6 cm" in TASKS["T2"]["object"] and "1.5" not in TASKS["T2"]["object"])
    chk("T1 물성 = 5 cm·55 g", "5 cm" in TASKS["T1"]["object"] and "55 g" in TASKS["T1"]["object"])

    print("[C2] 프롬프트")
    n3 = [("m1", 95.2), ("m2", 742.0), ("m4", -3.51)]
    p = build_prompt("T2", 3.5, n3, True)
    chk("M1 키·값 포함", "mga_mm = 95.2" in p)
    chk("M2 키·값 포함", "tam_total_deg = 742" in p)
    chk("M4 키·값 포함", "sparc = -3.51" in p)
    chk("null 지침 포함", "기능 저하나 0값을 뜻하지 않습니다" in p)
    chk("낙하 규칙 포함", "[낙하 규칙]" in p and "최선 수행" in p)
    chk("T2 맞섬·패드 조건", "엄지와 검지의 맞섬" in p and "패드로 맞섬" in p)
    chk("A1엔 수치 블록 없음", "[운동학 수치]" not in build_prompt("T1", 3.5, [], True))
    chk("A4 라벨 = 제공되지 않음", "제공되지 않음" in build_prompt("T2", 3.5, n3, False))

    print("[C3] 조건별 값 선택")
    ok = _rec("S_T1_t1", "S", 95.0, 740.0, -3.4)
    held_m1 = _rec("S_T1_t2", "S", 95.0, 740.0, -3.6, a1=False)
    chk("A1 = 수치 없음", values_for("A1", ok) == [])
    chk("A2 = 원값(M1·M2·M4)", values_for("A2", held_m1) == [("m1", 95.0), ("m2", 740.0), ("m4", -3.6)])
    chk("A3 = Q-gated(M1만 null)", values_for("A3", held_m1) == [("m1", None), ("m2", 740.0), ("m4", -3.6)],
        str(values_for("A3", held_m1)))
    chk("A4 = A3와 동일", values_for("A4", ok) == values_for("A3", ok))

    print("[C4] 주입 — 지표별 u(단위 다름)")
    v = [("m1", 100.0), ("m2", 800.0), ("m4", -4.0)]
    u2 = {"m1": 5.0, "m2": 40.0, "m4": 0.4}
    chk("bias_1u = 나빠지는 방향(M4는 감소)",
        inject(v, "bias_1u", u2, False) == [("m1", 105.0), ("m2", 840.0), ("m4", -4.4)])
    chk("bias_3u = 3u",
        inject(v, "bias_3u", u2, False) == [("m1", 115.0), ("m2", 920.0), ("m4", -5.2)])
    chk("burst 대상 아님 → 원값", inject(v, "burst_3u", u2, False) == v)
    chk("burst 대상 → 3u",
        inject(v, "burst_3u", u2, True) == [("m1", 115.0), ("m2", 920.0), ("m4", -5.2)])
    chk("u 없는 지표는 원값 유지",
        inject(v, "bias_3u", {"m1": 5.0}, False) == [("m1", 115.0), ("m2", 800.0), ("m4", -4.0)])
    chk("u 는 비음수(M4도 크기)",
        estimate_u([_rec("z", "S", 10.0, 100.0, -2.0)], "ratio", (0.10,))["m4"] > 0)
    chk("null은 주입해도 null", inject([("m1", None)], "bias_3u", u2, False) == [("m1", None)])

    print("[C5] R 배정 — 전체 P에서, 지표별")
    recs = [_rec("S_T1_t1", "S", 100.0, 700.0, -3.0),
            _rec("S_T1_t2", "S", 101.0, 710.0, -3.1),
            _rec("S_T1_t3", "S", 102.0, 720.0, -3.2),
            _rec("S_T2_t1", "S", 103.0, 730.0, -3.3, a1=False),
            _rec("S_T2_t2", "S", 104.0, 740.0, -3.4, a1=False, a4=False),
            _rec("S_T2_t3", "S", None, None, None)]
    rmap, n_held = r_withheld_map(recs, seeds=list(range(1, 21)))
    chk("M1 보류 2 · M2 보류 0 · M4 보류 1", (n_held["m1"], n_held["m2"], n_held["m4"]) == (2, 0, 1), str(n_held))
    chk("지표별 정확히 n건 제거",
        all(len(v["m1"]) == 2 and len(v["m2"]) == 0 and len(v["m4"]) == 1 for v in rmap.values()))
    Pk = {("S_T1_t1", "T1"), ("S_T1_t2", "T1"), ("S_T1_t3", "T1"), ("S_T2_t1", "T2"), ("S_T2_t2", "T2")}
    Qk = {("S_T2_t1", "T2"), ("S_T2_t2", "T2")}
    uni = set().union(*[v["m1"] for v in rmap.values()])
    chk("R 제거집합 ⊆ P", uni <= Pk)
    chk("R이 Q-보류도 제거 대상에 포함(품질 독립)", bool(uni & Qk), str(sorted(uni)))
    chk("하드 결측은 제외", ("S_T2_t3", "T2") not in uni)

    print("[C6] 행 생성")
    N = len(recs)
    rows = make_rows(recs, u={"m1": 5.0, "m2": 40.0, "m4": 0.4}, burst_trial_index=1)
    n_r = sum(1 for r in rows if r["condition"] == "R")
    n_bias = sum(1 for r in rows if r["injection"] in ("bias_1u", "bias_3u"))
    n_burst = sum(1 for r in rows if r["injection"] == "burst_3u")
    chk("R 행 = 시행수×seed3", n_r == N * 3, "R=%d (N=%d)" % (n_r, N))
    chk("bias 행 = A2·A3 × 2수준 × 시행수", n_bias == 2 * 2 * N, "bias=%d" % n_bias)
    chk("burst 행 = A2·A3 × 시행수", n_burst == 2 * N, "burst=%d" % n_burst)
    chk("모든 행에 prompt", all(r["prompt"] for r in rows))
    chk("CSV 필드 고정", set(rows[0].keys()) == set(FIELDS))
    chk("M3는 필드에 없다(mga_ 미포함)", not any("mga" in k for k in rows[0].keys()))
    chk("m1/m2/m4 provided 플래그 3개",
        all(("%s_provided" % k) in rows[0] for k in METRIC_ORDER))
    chk("u 가 지표별로 따로 기록됨",
        any(r["u_m1_used"] != r["u_m2_used"] for r in rows))

    print("[C7] u 추정(지표별)")
    ue = estimate_u([_rec("a", "S", 10.0, 100.0, -2.0), _rec("b", "S", 20.0, 200.0, -4.0)],
                    "ratio", (0.10,))
    chk("세 지표 모두 산출", set(ue) == set(METRIC_ORDER) and all(ue[k] is not None for k in METRIC_ORDER), str(ue))
    chk("B안 = 기저 P95×0.10", abs(ue["m2"] / ue["m1"] - 10.0) < 1e-9, str(ue))
    chk("B안 = 기저 P95×0.10 (최소 비율)",
        abs(estimate_u([_rec("z2", "S", 100.0, 1000.0, -4.0)], "ratio", (0.10, 0.30))["m1"] - 10.0) < 1e-6,
        str(estimate_u([_rec("z2", "S", 100.0, 1000.0, -4.0)], "ratio", (0.10, 0.30))))
    chk("A안 = 절대값 지정", estimate_u([], "absolute", (), {"m1": 5.0, "m2": 40.0, "m4": 0.4})
        == {"m1": 5.0, "m2": 40.0, "m4": 0.4})

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    print("※ 합성 레코드다. 실제 촬영·VLM 성능이 아니다.")
    try:
        outp = os.path.join(HERE, "..", "results", "conditions_v7_oracle.txt")
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with io.open(outp, "w", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
        print("[saved] %s" % os.path.abspath(outp))
    except OSError as e:
        print("[warn] 로그 저장 실패: %s" % e)
    return ok_all


HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--session")
    ap.add_argument("--sessions", nargs="*", default=[])
    ap.add_argument("--out", default="conditions.csv")
    ap.add_argument("--u-mode", choices=["ratio", "absolute"], default="ratio")
    ap.add_argument("--u-ratios", nargs="*", type=float, default=[0.10, 0.30])
    ap.add_argument("--u-abs-m1", type=float, default=None, help="A안: M1 실측 P95 절대오차(mm)")
    ap.add_argument("--u-abs-m2", type=float, default=None, help="A안: M2 절대오차(deg)")
    ap.add_argument("--u-abs-m4", type=float, default=None, help="A안: M4 절대오차(무차원)")
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
        print("입력 0건 — l2_from_app.py --write 로 L2_metric 를 만드세요.")
        return 1

    abs_u = None
    if a.u_mode == "absolute":
        if None in (a.u_abs_m1, a.u_abs_m2, a.u_abs_m4):
            print("[error] A안은 --u-abs-m1(mm)·--u-abs-m2(deg)·--u-abs-m4 둘 다 필요")
            return 2
        abs_u = {"m1": a.u_abs_m1, "m2": a.u_abs_m2, "m4": a.u_abs_m4}
    u = estimate_u(recs, a.u_mode, tuple(a.u_ratios), abs_u)
    rows = make_rows(recs, u=u, burst_trial_index=a.burst_trial_index, u_mode=a.u_mode)
    write_csv(rows, a.out)
    prov = {"generator": "make_conditions_v6.py (v7)", "metrics": list(METRIC_ORDER),
            "sessions": [os.path.basename(os.path.abspath(d.rstrip("/\\"))) for d in dirs],
            "n_trials": len(recs), "n_rows": len(rows), "u": u, "u_mode": a.u_mode,
            "conditions": CONDITIONS, "injections": INJECTIONS, "r_seeds": R_SEEDS}
    with io.open(os.path.splitext(a.out)[0] + ".provenance.json", "w", encoding="utf-8") as f:
        json.dump(prov, f, ensure_ascii=False, indent=1)
    print("행 %d개 → %s" % (len(rows), a.out))
    print("  u = %s (%s)" % (json.dumps(u), a.u_mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())

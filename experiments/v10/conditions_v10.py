# -*- coding: utf-8 -*-
"""v10 §9·§10 조건·프롬프트 생성기.

계획서: capstone/실험계획서_v10_최종본.md  §9(비환자 참고 분포), §10(입력 조건), §11.3(생성 지침)

생성하는 조건:
  A1        영상만 (수치·참고표 없음)
  A2        영상 + 적용 지표의 유한값 전체 + 참고표
  A3        영상 + Q 통과값만 + A2와 동일 참고표
  R         영상 + A3와 같은 개수를 무작위로 보류 + 동일 참고표 (seed 3)
  A4        영상 없음 + A3와 동일 수치·참고표
  A1n       영상 + 모든 적용 지표 키 null + 같은 구조의 null 참고표
  A2-noRef  영상 + A2 수치, 참고표 없음
  A3-hand   T1·T2만: Q 통과 MGA·추정 TAM_total만 + 손 지표 참고표

핵심 규칙(v10 명시):
  · 하드 결측은 모든 조건에서 null로 유지된다(§8.1, §10).
  · R은 "A3가 보류하지 않은 시행"으로 후보를 제한하지 않는다. 원래 유한값이 있는 모든 시행 P에서
    지표별로 A3 추가 보류 개수 n만큼 비복원 무작위 선택한다(§10 R 대조군).
  · 적용 안 함(T3의 M1·M2)은 키를 만들지 않고 분모에 넣지 않는다(§7 표, §8.1).
  · 조건명은 프롬프트에 쓰지 않는다.

실행:
  python experiments/v10/conditions_v10.py --selftest
  python experiments/v10/conditions_v10.py --trials trials.json --ref ref.json --out conditions.jsonl
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys

# ---- 과제 정의 (v10 §5) ----
TASKS = {
    "T1": {
        "arat_item": 3, "name": "5 cm 나무 블록을 집어 선반 위에 놓기",
        "instruction": "grasp the block that I have placed here, lift it up, and place then release it on top of that shelf.",
        "grasp_condition": "손가락 사용 제한 없음. 단 엄지와 다른 손가락의 맞섬(opposition)이 포함된 파지여야 함.",
        "object": "한 변 5 cm 나무 블록(문헌 제시 55 g)",
        "uses_hand_metrics": True, "t3_extra": None,
    },
    "T2": {
        "arat_item": 12, "name": "엄지–검지로 구슬을 집어 선반 위 용기에 넣기",
        "instruction": "grasp the marble using these fingers, lift it up, and place it in the tin on top of the shelf.",
        "grasp_condition": ("반드시 엄지와 검지의 맞섬이어야 함. 잘못된 맞섬이면 점수는 0. "
                            "3점은 손가락 **패드**로 맞섬한 경우에만 가능."),
        "object": "구슬(문헌 제시 지름 1.6 cm·5.4 g)",
        "uses_hand_metrics": True, "t3_extra": None,
    },
    "T3": {
        "arat_item": 18, "name": "무릎에 둔 손을 들어 손바닥을 머리 위에 대기",
        "instruction": "put the palm of your hand on top of your head.",
        "grasp_condition": "물체 없음. 손바닥으로 머리 위에 닿아야 함. 손가락 완전 신전을 별도 조건으로 붙이지 않음.",
        "object": "없음(도달 과제)",
        "uses_hand_metrics": False,
        "t3_extra": "T3에는 손 벌림·손가락 굴곡 지표를 적용하지 않는다. 손가락 수치가 낮다는 이유로 낮은 점수를 유도하지 않는다.",
    },
}

HAND_METRICS = ["mga_mm", "tam_total_deg"]
ARM_TRUNK_METRICS = ["sparc", "td_mm"]

METRIC_LABELS = {
    "mga_mm": ("MGA", "mm", "엄지끝–검지끝 3D 거리의 구간 최댓값"),
    "tam_total_deg": ("추정 TAM_total", "deg", "14개 기하학적 굴곡각 합의 구간 P95"),
    "sparc": ("SPARC", "1(무차원)", "손목 3D 이동 속력의 평활도(≤0, 0에 가까울수록 부드러움)"),
    "td_mm": ("TD", "mm", "어깨 중점의 탁자 전방 변위 최대"),
}


def metrics_for_task(task):
    return (HAND_METRICS + ARM_TRUNK_METRICS) if TASKS[task]["uses_hand_metrics"] else list(ARM_TRUNK_METRICS)


# =====================================================================
# 참고 분포 (§9.1)
# =====================================================================
def build_reference(rows, min_n=15):
    """rows: [{'person':pid,'task':T,'metric':m,'value':v,'usable':bool}] → 참고표.

    개인별 중앙값 → 집단 중앙값·Q25·Q75·유효 인원. 유효 인원 < min_n 이면 unavailable.
    """
    buckets = {}
    for r in rows:
        if not r.get("usable"):
            continue
        v = r.get("value")
        if v is None:
            continue
        buckets.setdefault((r["task"], r["metric"]), {}).setdefault(r["person"], []).append(float(v))
    table = {}
    for (task, metric), persons in buckets.items():
        meds = sorted(float(_median(v)) for v in persons.values() if v)
        n = len(meds)
        entry = {"metric": metric, "task": task, "n_persons": n,
                 "available": n >= min_n, "min_n": min_n}
        if n >= min_n:
            entry.update({"median": _quantile(meds, 0.50), "q25": _quantile(meds, 0.25),
                          "q75": _quantile(meds, 0.75)})
        else:
            entry.update({"median": None, "q25": None, "q75": None})
        table["%s|%s" % (task, metric)] = entry
    return table


def _median(xs):
    return _quantile(sorted(xs), 0.50)


def _quantile(sorted_xs, q):
    n = len(sorted_xs)
    if n == 0:
        return None
    if n == 1:
        return float(sorted_xs[0])
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac)


# =====================================================================
# 조건 생성 (§10)
# =====================================================================
def _finite(v):
    return v is not None and isinstance(v, (int, float)) and v == v


def build_conditions(trials, ref_table, seeds=(20261001, 20261002, 20261003)):
    """trials: [{pid,task,trial,t_obs_s,metrics:{m:{value,hard_missing,q_pass,ref_usable}}}]"""
    out = []
    by_task_metric = {}
    for tr in trials:
        for m in metrics_for_task(tr["task"]):
            md = tr["metrics"].get(m, {})
            by_task_metric.setdefault((tr["task"], m), []).append((tr, md))

    # --- A2 / A3 / A1n ---
    for tr in trials:
        keys = metrics_for_task(tr["task"])
        a2, a3, a1n = {}, {}, {}
        for m in keys:
            md = tr["metrics"].get(m, {})
            v = md.get("value") if _finite(md.get("value")) else None
            hard = bool(md.get("hard_missing", v is None))
            if hard:
                a2[m] = a3[m] = a1n[m] = None
            else:
                a2[m] = v
                a3[m] = v if md.get("q_pass", True) else None
                a1n[m] = None
        out.append(_row(tr, "A2", a2, ref_table, keys, video=True))
        out.append(_row(tr, "A3", a3, ref_table, keys, video=True))
        out.append(_row(tr, "A1n", a1n, _null_reference(tr["task"], keys), keys, video=True))
        out.append(_row(tr, "A2-noRef", a2, None, keys, video=True))
        if TASKS[tr["task"]]["uses_hand_metrics"]:
            hand_vals = {m: a3[m] for m in HAND_METRICS}
            out.append(_row(tr, "A3-hand", hand_vals, _subset_reference(ref_table, tr["task"], HAND_METRICS),
                            HAND_METRICS, video=True))
        out.append(_row(tr, "A1", {}, None, [], video=True))
        out.append(_row(tr, "A4", a3, ref_table, keys, video=False))

    # --- R (지표별 무작위 보류, §10) ---
    for si, seed in enumerate(seeds):
        rng = random.Random(seed)
        plans = {}
        for (task, m), pairs in by_task_metric.items():
            n_extra = sum(1 for tr, md in pairs if _finite(md.get("value")) and not md.get("q_pass", True))
            pool = [tr["trial"] for tr, md in pairs if _finite(md.get("value"))]
            pick = set(rng.sample(pool, min(n_extra, len(pool)))) if (n_extra and pool) else set()
            plans[(task, m)] = pick
        for tr in trials:
            keys = metrics_for_task(tr["task"])
            vals = {}
            for m in keys:
                md = tr["metrics"].get(m, {})
                v = md.get("value") if _finite(md.get("value")) else None
                if md.get("hard_missing", v is None):
                    vals[m] = None
                    continue
                pick = plans.get((tr["task"], m), set())
                vals[m] = None if tr["trial"] in pick else v
            out.append(_row(tr, "R", vals, ref_table, keys, video=True,
                            seed=seed, seed_index=si))
    return out


def _null_reference(task, keys):
    return {"%s|%s" % (task, m): {"metric": m, "task": task, "n_persons": 0,
                                  "available": False, "median": None, "q25": None, "q75": None}
            for m in keys}


def _subset_reference(ref_table, task, metrics):
    if not ref_table:
        return None
    sub = {}
    for m in metrics:
        k = "%s|%s" % (task, m)
        if k in ref_table:
            sub[k] = ref_table[k]
    return sub


def _row(tr, condition, values, ref_table, keys, video=True, seed=None, seed_index=None):
    prompt = build_prompt(tr, values, ref_table, keys, video=video)
    return {
        "pid": tr["pid"], "task": tr["task"], "trial": tr["trial"], "condition": condition,
        "seed": seed, "seed_index": seed_index, "video": bool(video),
        "metric_keys": list(keys), "metric_values": values, "t_obs_s": tr.get("t_obs_s"),
        "prompt": prompt, "prompt_hash": _hash(prompt),
    }


def _hash(s):
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# =====================================================================
# 프롬프트 (§9.2 + §11.3 공통 지침)
# =====================================================================
COMMON_GUIDANCE = (
    "· 제공된 운동학 수치는 카메라 영상에서 추정한 값이며 **절대 정확도는 검증되지 않았습니다**.\n"
    "· null은 '신뢰할 수 있는 추정이 없다'는 뜻이며, 기능 저하나 0값을 뜻하지 않습니다.\n"
    "· T_obs는 영상 관찰 구간 길이이며 성공 시간이 아닙니다.\n"
    "· 보이지 않는 접촉·힘·저항을 추측하지 마십시오. 확인되지 않은 것을 확인됐다고 쓰지 마십시오.\n"
    "· 최종 점수는 해당 항목의 완수·시간·파지·자세 기준으로 판단하십시오."
)

SCORING = (
    "3 = 5.000초 이내 정상 수행 + 정상 손 움직임 + 정상 팔 움직임 + 정상 자세\n"
    "2 = 완료했으나 5–60초 소요 또는 큰 어려움(손 움직임·팔 움직임·자세 중 하나가 비정상, 해제 실패 포함)\n"
    "1 = 60초 내 부분 수행(들어올렸으나 목표 높이·놓기 미완 등)\n"
    "0 = 60초 내 어떤 부분도 수행하지 못함"
)


def build_prompt(tr, values, ref_table, keys, video=True):
    t = TASKS[tr["task"]]
    lines = []
    lines.append("당신은 뇌졸중 환자의 상지 기능을 영상으로 평가하는 임상 평가자입니다.")
    lines.append("")
    lines.append("[과제] %s (ARAT %d번) — %s" % (t["name"], t["arat_item"], t["object"]))
    lines.append("[지시문] %s" % t["instruction"])
    lines.append("[파지·수행 조건] %s" % t["grasp_condition"])
    if t["t3_extra"]:
        lines.append("[적용 제외] %s" % t["t3_extra"])
    lines.append("[채점 기준]")
    lines.append(SCORING)
    lines.append("[채점 자세 기준] 몸통은 의자 등받이에 접촉을 유지해야 합니다. "
                 "몸통이 등받이에서 완전히 떨어지면 자세 비정상입니다.")
    lines.append("[낙하 규칙] 물체를 떨어뜨렸더라도 다시 집어 수행하면 최선 수행으로 평가합니다"
                 "(낙하 자체는 감점이 아님). 60초 안에 완료하지 못하면 부분 수행입니다. "
                 "과제를 성공적으로 마친 뒤 물체가 떨어지면 감점하지 않습니다.")
    lines.append("[관찰 구간] T_obs = %s 초" % (tr.get("t_obs_s")))

    if keys:
        lines.append("")
        lines.append("[운동학 수치]")
        for m in keys:
            label, unit, _desc = METRIC_LABELS[m]
            v = values.get(m)
            shown = "null" if not _finite(v) else ("%.4g" % float(v))
            lines.append("  %s (%s) = %s %s" % (label, m, shown, unit if shown != "null" else ""))
    if ref_table:
        avail = [v for v in ref_table.values() if v.get("available")]
        if avail:
            lines.append("")
            lines.append("[비환자 참고 분포]")
            for e in avail:
                label = METRIC_LABELS[e["metric"]][0]
                lines.append("  %s: 중앙값 %.4g · Q25 %.4g · Q75 %.4g (유효 인원 %d)"
                             % (label, e["median"], e["q25"], e["q75"], e["n_persons"]))
        else:
            lines.append("")
            lines.append("[비환자 참고 분포] 제공 가능한 참고값이 없습니다(unavailable).")
        lines.append("해석 원칙: 이 참고표는 본 연구 비환자 표본 중 성공 수행·품질 기준을 충족한 자료의 요약입니다. "
                     "임상 정상 범위나 ARAT 점수 경계값이 아닙니다. 참고 범위와 다르다는 이유만으로 감점하지 마십시오.")
    lines.append("")
    lines.append("[지침]")
    lines.append(COMMON_GUIDANCE)
    lines.append("[영상] %s" % ("제공됨" if video else "제공되지 않음 (수치만으로 판단)"))
    lines.append("[출력] 먼저 점수(0/1/2/3) 한 줄, 그 다음 최대 2문장의 근거. JSON으로 출력.")
    return "\n".join(lines)


MODELS = [
    ("Qwen2.5-VL-32B-Instruct", "https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct", "main"),
    ("Qwen3.8-27B", "https://huggingface.co/Qwen/Qwen3.8-27B", "comparison"),
    ("InternVL3.5-8B", "https://huggingface.co/OpenGVLab/InternVL3_5-8B", "comparison"),
    ("LLaVA-NeXT-Video-7B", "https://huggingface.co/lmms-lab/LLaVA-NeXT-Video-7B", "comparison"),
    ("LLaVA-OneVision-7B", "https://huggingface.co/lmms-lab/llava-onevision-qwen2-7b-ov", "comparison"),
]


# =====================================================================
# 오라클
# =====================================================================
def _demo_trials():
    trials = []
    for pid, task in [("P01", "T1"), ("P01", "T2"), ("P01", "T3"), ("P02", "T1")]:
        keys = metrics_for_task(task)
        metrics = {}
        for i, m in enumerate(keys):
            metrics[m] = {"value": 10.0 + i, "hard_missing": False,
                          "q_pass": not (m == keys[0] and pid == "P01"), "ref_usable": True}
        trials.append({"pid": pid, "task": task, "trial": 1, "t_obs_s": 4.2, "metrics": metrics})
    # 하드 결측 1건
    trials.append({"pid": "P03", "task": "T1", "trial": 1, "t_obs_s": 60.0,
                   "metrics": {m: {"value": None, "hard_missing": True, "q_pass": False, "ref_usable": False}
                               for m in metrics_for_task("T1")}})
    return trials


def selftest():
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    trials = _demo_trials()
    ref_rows = [{"person": "N%02d" % i, "task": t, "metric": m, "value": 5.0 + i,
                 "usable": True} for i in range(16) for t in ("T1", "T2", "T3")
                for m in metrics_for_task(t)]
    ref = build_reference(ref_rows)
    conds = build_conditions(trials, ref)

    def find(pid, task, condition, seed_index=None):
        for c in conds:
            if c["pid"] == pid and c["task"] == task and c["condition"] == condition \
               and (seed_index is None or c["seed_index"] == seed_index):
                return c
        return None

    a1 = find("P01", "T1", "A1")
    chk("A1: 수치 블록 없음", "[운동학 수치]" not in a1["prompt"] and a1["metric_values"] == {})
    chk("A1: 참고표 없음", "[비환자 참고 분포]" not in a1["prompt"])
    chk("A1: 영상 제공됨", "[영상] 제공됨" in a1["prompt"])

    a2 = find("P01", "T1", "A2")
    chk("A2: 4개 키(M1·M2·SPARC·TD)", len(a2["metric_keys"]) == 4, str(a2["metric_keys"]))
    chk("A2: 참고표 포함", "[비환자 참고 분포]" in a2["prompt"])
    chk("A2: Q 실패해도 원값 유지", all(v is not None for v in a2["metric_values"].values()), str(a2["metric_values"]))

    a3 = find("P01", "T1", "A3")
    chk("A3: Q 실패 지표만 null", a3["metric_values"]["mga_mm"] is None
        and a3["metric_values"]["sparc"] is not None, str(a3["metric_values"]))
    chk("A3: A2와 같은 참고표", _refsig(a3) == _refsig(a2))

    t3 = find("P01", "T3", "A2")
    chk("T3: 손 지표 키 없음", "mga_mm" not in t3["metric_keys"] and "tam_total_deg" not in t3["metric_keys"],
        str(t3["metric_keys"]))
    t3h = find("P01", "T3", "A3-hand")
    chk("T3: A3-hand 생성 안 함", t3h is None)

    h = find("P01", "T1", "A3-hand")
    chk("A3-hand: 손 지표 2개만", h["metric_keys"] == HAND_METRICS, str(h["metric_keys"]))
    chk("A3-hand: 참고표도 손만", all(k.split("|")[1] in HAND_METRICS for k in _refkeys(h)), str(_refkeys(h)))

    hard = find("P03", "T1", "A2")
    chk("하드 결측: A2에서 null", all(v is None for v in hard["metric_values"].values()))
    hard_r = find("P03", "T1", "R", 0)
    chk("하드 결측: R에서도 null 유지", all(v is None for v in hard_r["metric_values"].values()))

    r0 = find("P01", "T1", "R", 0)
    n_a3_null = sum(1 for v in a3["metric_values"].values() if v is None)
    n_r0_null = sum(1 for v in r0["metric_values"].values() if v is None)
    chk("R: A3와 같은 보류 개수", n_a3_null == n_r0_null, "A3=%d R=%d" % (n_a3_null, n_r0_null))
    chk("R: seed 3개 생성", len({c["seed_index"] for c in conds if c["condition"] == "R"}) == 3)

    # R의 seed 변동성: 10시행 중 지표별 3개 추가보류 → 3 seed가 전부 같을 확률은 작다
    big = []
    for i in range(10):
        big.append({"pid": "P01", "task": "T1", "trial": i + 1, "t_obs_s": 3.0,
                    "metrics": {m: {"value": 20.0 + i, "hard_missing": False,
                                     "q_pass": (i >= 3), "ref_usable": True}
                                for m in metrics_for_task("T1")}})
    cbig = build_conditions(big, ref)
    rs = [[c["metric_values"]["mga_mm"] for c in cbig
           if c["condition"] == "R" and c["seed_index"] == s] for s in range(3)]
    n_null = [sum(1 for v in x if v is None) for x in rs]
    chk("R: seed별 보류 개수 = A3 추가보류 수(3)", all(n == 3 for n in n_null), str(n_null))
    chk("R: seed 간 보류 위치가 실제로 달라짐", any(rs[a] != rs[b] for a in range(3) for b in range(a + 1, 3)))

    noref = find("P01", "T1", "A2-noRef")
    chk("A2-noRef: 참고표 없음·수치는 A2와 동일",
        "[비환자 참고 분포]" not in noref["prompt"] and noref["metric_values"] == a2["metric_values"])

    a1n = find("P01", "T1", "A1n")
    chk("A1n: 모든 키 null + null 참고표",
        all(v is None for v in a1n["metric_values"].values()) and "unavailable" in a1n["prompt"])

    a4 = find("P01", "T1", "A4")
    chk("A4: 영상 없음 표기", "[영상] 제공되지 않음" in a4["prompt"])

    small = build_reference([{"person": "N%02d" % i, "task": "T1", "metric": "mga_mm",
                              "value": 1.0 + i, "usable": True} for i in range(10)])
    chk("참고표: 유효인원 <15 → unavailable",
        small["T1|mga_mm"]["available"] is False and small["T1|mga_mm"]["median"] is None)

    import re as _re
    lab = _re.compile(r"\b(A1n|A2-noRef|A3-hand|A1|A2|A3|A4|R)\b")
    bad = [c["condition"] for c in conds if lab.search(c["prompt"])]
    chk("프롬프트에 조건명 없음", bad == [], str(set(bad)))
    chk("등받이 자세 기준 명시", "등받이" in a2["prompt"])

    print("=" * 72)
    print("conditions_v10 오라클")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def _refkeys(c):
    return [k for k in _ref_of(c)]


def _ref_of(c):
    keys = []
    p = c["prompt"]
    if "[비환자 참고 분포]" in p:
        for e in METRIC_LABELS:
            if METRIC_LABELS[e][0] + ": 중앙값" in p:
                keys.append("%s|%s" % (c["task"], e))
    return keys


def _refsig(c):
    return tuple(sorted(_ref_of(c)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="v10 §9·§10 조건·프롬프트 생성")
    ap.add_argument("--trials", help="trials.json: [{pid,task,trial,t_obs_s,metrics:{...}}]")
    ap.add_argument("--ref-rows", help="ref_rows.json: [{person,task,metric,value,usable}]")
    ap.add_argument("--ref", help="미리 계산된 참고표 json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.trials:
        ap.error("--trials 또는 --selftest 필요")
    trials = json.load(io.open(a.trials, encoding="utf-8"))
    if a.ref:
        ref = json.load(io.open(a.ref, encoding="utf-8"))
    elif a.ref_rows:
        ref = build_reference(json.load(io.open(a.ref_rows, encoding="utf-8")))
    else:
        ref = None
    conds = build_conditions(trials, ref)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            for c in conds:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
        print("wrote %d conditions → %s" % (len(conds), a.out))
    else:
        print(json.dumps({"n_conditions": len(conds),
                          "by_condition": _count(conds)}, ensure_ascii=False, indent=2))
    return 0


def _count(conds):
    out = {}
    for c in conds:
        out[c["condition"]] = out.get(c["condition"], 0) + 1
    return out


if __name__ == "__main__":
    sys.exit(main())

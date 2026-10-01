# -*- coding: utf-8 -*-
"""v10 §12 분석 하네스: 환자 통합 MAE · 고정순서 검정 · 환자단위 부트스트랩 · Holm 민감도.

계획서: capstone/실험계획서_v10_최종본.md  §12(분석 계획)

구현한 규칙(v10 명시):
  · 분석 단위 = **환자**. 225시행은 225명이 아니다(§12.1-3).
  · 과제별 MAE를 구하고 `환자 통합 MAE = (T1+T2+T3)/3` 로 평균한다(§12.1-1,2).
  · 효과량 부호(§3.2): PR-1 = MAE(A1)−MAE(A2) · PR-2 = MAE(A2)−MAE(A3) · PR-3 = MAE(R)−MAE(A3).
    양수 = 개선.
  · 주 검정: **PR-2 → PR-3 → PR-1 고정 순서**, 단계별 α=.05. 앞 단계가 비유의이면 후속 확증 주장 중단(§12.1-5).
    모든 효과량은 계속 보고한다. Holm k=3은 **민감도**로 병기(§12.1-6).
  · 부트스트랩: 환자 단위 2,000회. **한 사람의 모든 과제·시행·조건을 함께 재표본화**한다(§12.1-7).
  · R은 seed별 MAE를 먼저 계산한 뒤 평균한다(§10). 점수를 먼저 평균하지 않는다.
  · 출력 실패는 0점으로 바꾸지 않는다(§11.4). 유효 MAE와 보수적 손실(최대오차 3)을 함께 낸다.
  · 통합 분석 가능 환자가 20명 미만이면 탐색적으로만 표시한다(§12.2).

실행:
  python experiments/v10/analysis_v10.py --selftest
  python experiments/v10/analysis_v10.py --preds preds.csv --refs refs.csv --out report.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import random
import sys
from itertools import combinations

MAX_ERROR = 3.0          # 0–3 척도 최대 오차 (실행 실패 보수적 손실)
BOOT_N = 2000
BOOT_SEED = 20261001
EXPLORATORY_N = 20       # 이 미만이면 탐색적 표시 (§12.2)

FIXED_SEQUENCE = ["PR-2", "PR-3", "PR-1"]
EFFECT_DEFS = {
    "PR-1": ("A1", "A2"),   # MAE(A1) − MAE(A2)
    "PR-2": ("A2", "A3"),   # MAE(A2) − MAE(A3)
    "PR-3": ("R", "A3"),    # MAE(R)  − MAE(A3)
}


# =====================================================================
# 1. 로딩
# =====================================================================
def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def load_preds(path):
    rows = []
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "pid": (r.get("pid") or r.get("participant_id") or "").strip(),
                "task": (r.get("task") or "").strip(),
                "trial": int(float(r.get("trial", r.get("trial_index", 0)) or 0)),
                "condition": (r.get("condition") or "").strip(),
                "seed": (r.get("seed") or "").strip(),
                "score": _f(r.get("score", r.get("pred"))),
                "status": (r.get("status") or "ok").strip(),
            })
    return rows


def load_refs(path):
    out = {}
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            pid = (r.get("pid") or r.get("participant_id") or "").strip()
            task = (r.get("task") or "").strip()
            trial = int(float(r.get("trial", r.get("trial_index", 0)) or 0))
            s = _f(r.get("score"))
            if s is not None:
                out[(pid, task, trial)] = s
    return out


# =====================================================================
# 2. MAE
# =====================================================================
def mae_rows(preds, refs, condition, tasks=None, loss="valid"):
    """조건 하나의 (pid, task)별 MAE.  loss='valid' | 'conservative'(실패=오차 3)."""
    acc = {}
    for p in preds:
        if p["condition"] != condition:
            continue
        if tasks is not None and p["task"] not in tasks:
            continue
        key = (p["pid"], p["task"])
        ref = refs.get((p["pid"], p["task"], p["trial"]))
        if ref is None:
            continue
        acc.setdefault(key, []).append((p["score"], ref))
    out = {}
    for key, pairs in acc.items():
        errs = []
        for pred, ref in pairs:
            if pred is None:
                if loss == "conservative":
                    errs.append(MAX_ERROR)
                continue
            errs.append(abs(pred - ref))
        out[key] = (sum(errs) / len(errs)) if errs else None
    return out


def integrated_mae(per_key, tasks=("T1", "T2", "T3")):
    """(pid,task)->mae 를 환자별 (T1+T2+T3)/3 로 통합. 과제 결측은 제외하고 평균."""
    by_pid = {}
    for (pid, task), v in per_key.items():
        if v is None or task not in tasks:
            continue
        by_pid.setdefault(pid, {})[task] = v
    out = {}
    for pid, d in by_pid.items():
        if d:
            out[pid] = sum(d.values()) / len(d)
    return out


def r_seed_averaged(preds, refs, tasks=None, loss="valid"):
    """R: seed별 환자 MAE → seed 평균 (§10)."""
    seeds = sorted({p["seed"] for p in preds if p["condition"] == "R"})
    per_seed = []
    for s in seeds:
        sub = [dict(p, condition="R") for p in preds if p["condition"] == "R" and p["seed"] == s]
        per_seed.append(integrated_mae(mae_rows(sub, refs, "R", tasks=tasks, loss=loss), tasks=tasks or ("T1", "T2", "T3")))
    pids = set()
    for d in per_seed:
        pids |= set(d)
    out = {}
    for pid in sorted(pids):
        vals = [d[pid] for d in per_seed if pid in d]
        if vals:
            out[pid] = sum(vals) / len(vals)
    return out, seeds


# =====================================================================
# 3. 검정
# =====================================================================
def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def wilcoxon_signed_rank(diffs, exact_max_n=20):
    """양측 Wilcoxon signed-rank. 0차이는 제거. 반환 (stat, p, n, method)."""
    d = [x for x in diffs if x is not None and abs(x) > 1e-12]
    n = len(d)
    if n < 1:
        return None, 1.0, 0, "no_data"
    absd = [abs(x) for x in d]
    r = _ranks(absd)
    w_plus = sum(rr for rr, x in zip(r, d) if x > 0)
    w_minus = sum(rr for rr, x in zip(r, d) if x < 0)
    w = min(w_plus, w_minus)
    if n <= exact_max_n and len(set(absd)) == n:
        cnt = 0
        total = 0
        for k in range(n + 1):
            for combo in combinations(range(n), k):
                s = sum(absd[i] for i in combo)
                total += 1
                if s <= w + 1e-12 or (sum(absd) - s) <= w + 1e-12:
                    cnt += 1
        return w, min(1.0, cnt / total), n, "exact"
    # 정규근사 + 동률 보정 + 연속성 보정
    mu = n * (n + 1) / 4.0
    tie_term = 0.0
    for v in set(absd):
        c = absd.count(v)
        if c > 1:
            tie_term += c ** 3 - c
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0 - tie_term / 48.0)
    if sigma <= 0:
        return w, 1.0, n, "normal_degenerate"
    z = (w - mu + 0.5) / sigma
    p = 2.0 * _norm_cdf(z)
    return w, min(1.0, max(0.0, p)), n, "normal"


def _norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def holm(pvals, alpha=0.05):
    """Holm 보정. pvals: {name: p}. 반환 {name: (p_adj, reject)}"""
    items = sorted([(n, p) for n, p in pvals.items() if p is not None], key=lambda t: t[1])
    m = len(items)
    out = {}
    prev = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        adj = max(adj, prev)
        prev = adj
        out[name] = (adj, adj < alpha)
    for name, p in pvals.items():
        if name not in out:
            out[name] = (None, False)
    return out


def bootstrap_ci(diffs_by_pid, n_boot=BOOT_N, seed=BOOT_SEED, alpha=0.05):
    """환자 단위 부트스트랩 평균차 CI. diffs_by_pid: {pid: diff}"""
    pids = sorted(diffs_by_pid)
    if not pids:
        return None, None, None
    vals = [diffs_by_pid[p] for p in pids]
    rng = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(n_boot):
        s = 0.0
        for _i in range(n):
            s += vals[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(math.floor(alpha / 2 * n_boot))]
    hi = means[int(math.ceil((1 - alpha / 2) * n_boot)) - 1]
    return sum(vals) / n, lo, hi


# =====================================================================
# 4. 전체 분석
# =====================================================================
def analyze(preds, refs, n_boot=BOOT_N, boot_seed=BOOT_SEED, alpha=0.05):
    res = {"n_patients": 0, "exploratory": False, "effects": {}, "fixed_sequence": [],
           "holm": {}, "r_seeds": [], "loss": {}}

    per_cond = {}
    for c in ("A1", "A2", "A3"):
        per_cond[c] = integrated_mae(mae_rows(preds, refs, c))
    r_avg, r_seeds = r_seed_averaged(preds, refs)
    per_cond["R"] = r_avg
    res["r_seeds"] = r_seeds

    pids = sorted(set(per_cond["A2"]) & set(per_cond["A3"]) & set(per_cond["A1"]) & set(per_cond["R"]))
    res["n_patients"] = len(pids)
    res["exploratory"] = len(pids) < EXPLORATORY_N

    # 효과량 + 부트스트랩
    for name, (ca, cb) in EFFECT_DEFS.items():
        diffs = {p: (per_cond[ca][p] - per_cond[cb][p]) for p in pids
                 if per_cond[ca].get(p) is not None and per_cond[cb].get(p) is not None}
        if not diffs:
            res["effects"][name] = {"n": 0, "mean": None, "ci": [None, None], "p": None,
                                    "def": "MAE(%s)-MAE(%s)" % (ca, cb)}
            continue
        mean, lo, hi = bootstrap_ci(diffs, n_boot=n_boot, seed=boot_seed, alpha=alpha)
        _w, p, n, method = wilcoxon_signed_rank(list(diffs.values()))
        res["effects"][name] = {
            "def": "MAE(%s)-MAE(%s)" % (ca, cb), "positive_means": "improvement",
            "n": n, "mean": mean, "median": _median(list(diffs.values())),
            "ci": [lo, hi], "p": p, "test": "wilcoxon_signed_rank:%s" % method,
            "n_positive": sum(1 for v in diffs.values() if v > 0),
            "n_negative": sum(1 for v in diffs.values() if v < 0),
        }

    # 고정 순서 (PR-2 → PR-3 → PR-1)
    stopped = False
    for name in FIXED_SEQUENCE:
        p = res["effects"][name]["p"]
        sig = (p is not None and p < alpha) and not stopped
        res["fixed_sequence"].append({
            "step": name, "p": p, "alpha": alpha, "significant": bool(sig),
            "stopped_before": bool(stopped),
            "note": ("앞 단계 비유의 → 후속 확증 주장 중단" if stopped else
                     ("유의" if sig else "비유의")),
        })
        if not sig:
            stopped = True

    # Holm k=3 민감도
    ps = {n: res["effects"][n]["p"] for n in ("PR-1", "PR-2", "PR-3")}
    adj = holm({n: p for n, p in ps.items() if p is not None}, alpha=alpha)
    res["holm"] = {n: {"p": ps.get(n), "p_adj": adj.get(n, (None, False))[0],
                       "reject": adj.get(n, (None, False))[1]} for n in ("PR-1", "PR-2", "PR-3")}

    # 보수적 손실 병기 (§11.4)
    for loss in ("valid", "conservative"):
        eff = {}
        for name, (ca, cb) in EFFECT_DEFS.items():
            a = integrated_mae(mae_rows(preds, refs, ca, loss=loss))
            b = integrated_mae(mae_rows(preds, refs, cb, loss=loss)) if cb != "R" else r_seed_averaged(preds, refs, loss=loss)[0]
            common = sorted(set(a) & set(b))
            eff[name] = (sum(a[p] - b[p] for p in common) / len(common)) if common else None
        res["loss"][loss] = eff

    # 과제별 병기 (§12.1-4)
    res["per_task"] = {}
    for task in ("T1", "T2", "T3"):
        row = {}
        for name, (ca, cb) in EFFECT_DEFS.items():
            a = integrated_mae(mae_rows(preds, refs, ca, tasks=(task,)), tasks=(task,))
            if cb == "R":
                b, _s = r_seed_averaged(preds, refs, tasks=(task,))
            else:
                b = integrated_mae(mae_rows(preds, refs, cb, tasks=(task,)), tasks=(task,))
            common = sorted(set(a) & set(b))
            row[name] = (sum(a[p] - b[p] for p in common) / len(common)) if common else None
        res["per_task"][task] = row
    return res


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


# =====================================================================
# 5. 오라클
# =====================================================================
def _demo(n_pat=25, seed=7, a3_better=True, fail_frac=0.0):
    rng = random.Random(seed)
    preds, refs = [], {}
    for i in range(n_pat):
        pid = "P%02d" % i
        for task in ("T1", "T2", "T3"):
            for trial in (1, 2):
                ref = rng.choice([0, 1, 2, 3])
                refs[(pid, task, trial)] = float(ref)
                for cond, noise in (("A1", 1.0), ("A2", 1.3), ("A3", 0.30 if a3_better else 1.3)):
                    s = max(0, min(3, round(ref + rng.gauss(0, noise))))
                    if fail_frac and rng.random() < fail_frac:
                        s = None
                    preds.append({"pid": pid, "task": task, "trial": trial,
                                  "condition": cond, "seed": "", "score": s,
                                  "status": "ok" if s is not None else "no_output"})
                for si, sd in enumerate((20261001, 20261002, 20261003)):
                    s = max(0, min(3, round(ref + rng.gauss(0, 0.95))))
                    preds.append({"pid": pid, "task": task, "trial": trial,
                                  "condition": "R", "seed": str(sd), "score": s, "status": "ok"})
    return preds, refs


def selftest():
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    # 손계산 검증
    per = {("P1", "T1"): 1.0, ("P1", "T2"): 2.0, ("P1", "T3"): 3.0,
           ("P2", "T1"): 0.0, ("P2", "T2"): 0.0, ("P2", "T3"): 3.0}
    integ = integrated_mae(per)
    chk("통합 MAE = 과제 평균", abs(integ["P1"] - 2.0) < 1e-12 and abs(integ["P2"] - 1.0) < 1e-12,
        str(integ))
    per2 = {("P3", "T1"): 1.0, ("P3", "T3"): 2.0}
    chk("과제 결측 시 남은 과제로 평균", abs(integrated_mae(per2)["P3"] - 1.5) < 1e-12)

    # Wilcoxon 손계산: 모두 양수 6쌍 → exact p = 2/64 = 0.03125
    _w, p, n, method = wilcoxon_signed_rank([1, 2, 3, 4, 5, 6])
    chk("Wilcoxon exact(전부 양수, n=6)", abs(p - 2 / 64.0) < 1e-12 and method == "exact",
        "p=%.6f %s" % (p, method))
    _w, p0, n, _m = wilcoxon_signed_rank([0, 0, 0])
    chk("Wilcoxon 0차이 전부 → n=0, p=1", n == 0 and p0 == 1.0)

    # Holm
    h = holm({"a": 0.01, "b": 0.04, "c": 0.2})
    chk("Holm: a 통과(b=0.04<0.05)", h["a"][1] is True and h["a"][0] == 0.03, str(h["a"]))
    chk("Holm: b 비통과(p_adj=0.08)", h["b"][1] is False and abs(h["b"][0] - 0.08) < 1e-12, str(h["b"]))
    chk("Holm: c 비통과", h["c"][1] is False)

    # 부트스트랩
    mean, lo, hi = bootstrap_ci({("P%d" % i): 1.0 for i in range(10)}, n_boot=500)
    chk("부트스트랩: 상수 → CI=[1,1]", abs(mean - 1.0) < 1e-12 and abs(lo - 1.0) < 1e-12 and abs(hi - 1.0) < 1e-12,
        "%s %s %s" % (mean, lo, hi))

    # 전체 분석: A3 우세 → PR-2 유의해야
    preds, refs = _demo(n_pat=25, a3_better=True)
    res = analyze(preds, refs, n_boot=300)
    chk("환자 수 25", res["n_patients"] == 25, str(res["n_patients"]))
    chk("PR-2 양수(개선)", res["effects"]["PR-2"]["mean"] > 0, "%.3f" % res["effects"]["PR-2"]["mean"])
    chk("PR-2 고정순서 1단계 유의", res["fixed_sequence"][0]["step"] == "PR-2"
        and res["fixed_sequence"][0]["significant"] is True,
        "p=%.4g" % (res["effects"]["PR-2"]["p"] or -1))
    chk("고정순서 = PR-2→PR-3→PR-1",
        [s["step"] for s in res["fixed_sequence"]] == ["PR-2", "PR-3", "PR-1"])
    chk("R seed 3개 사용", len(res["r_seeds"]) == 3, str(res["r_seeds"]))
    chk("과제별 결과 병기", set(res["per_task"]) == {"T1", "T2", "T3"})
    chk("Holm 민감도 병기", all(k in res["holm"] for k in ("PR-1", "PR-2", "PR-3")))

    # 고정 순서 중단: A1이 가장 좋으면 PR-2 비유의 → 2단계에서 중단
    preds2, refs2 = _demo(n_pat=25, a3_better=False)
    res2 = analyze(preds2, refs2, n_boot=300)
    fs = res2["fixed_sequence"]
    chk("고정순서: 1단계 비유의면 이후 중단 표시",
        (fs[0]["significant"] is False and fs[1]["stopped_before"] is True)
        or fs[0]["significant"] is True, "step0_sig=%s" % fs[0]["significant"])

    # 실패 처리
    preds3, refs3 = _demo(n_pat=25, fail_frac=0.3)
    res3 = analyze(preds3, refs3, n_boot=200)
    chk("실패: valid/conservative 병기", set(res3["loss"]) == {"valid", "conservative"})
    chk("실패: 보수적 손실이 유효 MAE보다 나쁨(효과량이 작아짐)",
        res3["loss"]["conservative"]["PR-2"] <= res3["loss"]["valid"]["PR-2"] + 1e-9,
        "valid=%.3f cons=%.3f" % (res3["loss"]["valid"]["PR-2"], res3["loss"]["conservative"]["PR-2"]))

    # 20명 미만 → 탐색적
    preds4, refs4 = _demo(n_pat=12)
    res4 = analyze(preds4, refs4, n_boot=100)
    chk("환자<20 → exploratory=True", res4["exploratory"] is True)

    print("=" * 72)
    print("analysis_v10 오라클")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="v10 §12 분석")
    ap.add_argument("--preds")
    ap.add_argument("--refs")
    ap.add_argument("--out", default=None)
    ap.add_argument("--n-boot", type=int, default=BOOT_N)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.preds and a.refs):
        ap.error("--preds --refs 또는 --selftest 필요")
    res = analyze(load_preds(a.preds), load_refs(a.refs), n_boot=a.n_boot)
    txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            fh.write(txt)
        print("wrote %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

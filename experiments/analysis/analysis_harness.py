# -*- coding: utf-8 -*-
"""
분석 하네스 (v6.1 연구계획서 §9) — PR-1 · PR-2 · bootstrap · Holm · κ · 보류율
==============================================================================

목적
----
계획서 §9의 분석을 **데이터를 보기 전에** 실행 가능한 코드로 고정한다.
없으면 "주 결과를 어떻게 계산할지"를 데이터 이후에 정하게 되고, 그건
사후 선택(post-hoc)이 된다.

v6.1 배선 (2026-09-24, 결함 D-12 해소)
--------------------------------------
| 주 결과 | 정의 | 부호 해석 |
|---|---|---|
| **PR-1 (수치 주입 효과)** | `I_i = MAE_i(A2) − MAE_i(A1)` | **양수 = 주입이 해로움** (v6.3 신규) |
| **PR-2 (게이팅 효과)** | `G_i = MAE_i(A2) − MAE_i(A3)` | **양수 = A3가 더 정확 = 게이팅이 도움** |
| **PR-3 (게이팅의 고유 가치)** | `E_i = MAE_i(R) − MAE_i(A3)` | **양수 = A3가 R보다 나음 = 품질 규칙의 고유 기여** |

**1급 기술 결과(검정 아님, 반드시 보고):** 보류율 · 큰 오차(≥2점) 비율 · Pareto 곡선
**탐색적:** `A2−A1`(숫자 추가), `A3−A4`(영상의 가치), A0/A0time, 주입 수준별(A3), 설명 평가
**기전(H5, 탐색적):** `A3(bias_3u) − A3(none)` — 구 PR-1이었으나 **격하**됨
  근거: Li 2026(PMID 42406872)·ST-VLM이 "VLM은 재활 수치를 못 읽는다"를 이미 보임.

입력 (CSV)
----------
1) predictions.csv
   participant_id,trial_id,task,condition,injection,run,predicted_score,rationale,output_status
   - condition ∈ A0 | A0time | A1 | A2 | A3 | A4 | R
   - injection ∈ none | bias_1u | bias_3u | burst_3u
   - run = 1(주결과) 또는 2(반복 안정성)
   - predicted_score = 0..3 (실패 시 빈칸)
   - output_status ∈ ok | parse_failed | api_failed | timeout
   **선택 열 (보류율 계산용 — 없으면 보류율은 "자료 없음"으로 표시)**
   - k1_provided, k2_provided ∈ 1 | 0   (프롬프트에 그 수치가 실제로 들어갔는가)

2) reference.csv
   participant_id,trial_id,task,therapist_score,independent_score

3) sweep.csv (선택, `--sweep` — Pareto 곡선용)
   participant_id,trial_id,task,q1_threshold,condition,predicted_score,output_status,k1_provided,k2_provided

출력
----
- 콘솔/파일 보고서: 조건별 MAE · PR-1 · PR-2 · bootstrap CI · Holm · κ · 보류율 · 큰 오차
- per_patient_mae.csv: 장애인×조건 MAE (재분석 가능)

실행
----
  python experiments/analysis/analysis_harness.py --selftest
  python experiments/analysis/analysis_harness.py --demo
  python experiments/analysis/analysis_harness.py --predictions P.csv --reference R.csv
  python experiments/analysis/analysis_harness.py --predictions P.csv --reference R.csv --sweep S.csv
"""

import argparse
import csv
import io
import math
import os
import random
import statistics
import sys
import zlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CONDITIONS = ["A0", "A0time", "A1", "A2", "A3", "A4", "R"]
# 수치를 담는 조건 (보류율이 의미를 갖는 조건)
NUMERIC_CONDITIONS = ["A2", "A3", "A4", "R"]
INJECTIONS = ["none", "bias_1u", "bias_3u", "burst_3u"]
FAIL_STATUSES = {"parse_failed", "api_failed", "timeout"}
MAX_LOSS = 3.0          # 0–3 척도의 최대 절대오차
BIG_ERROR = 2           # "큰 오차" 기준 (척도 0–3에서 2점 이상)
BOOT_N = 10000
BOOT_SEED = 20260922
SCORE_MIN, SCORE_MAX = 0, 3


# ===========================================================================
# 통계 함수 (외부 의존 없음)
# ===========================================================================
def mean(xs):
    return statistics.fmean(xs) if xs else float("nan")


def stdev(xs):
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def bootstrap_ci_mean(xs, n_boot=BOOT_N, seed=BOOT_SEED, alpha=0.05):
    """장애인 단위 bootstrap 백분위 CI. 반환 (lo, hi, p_two_sided).

    ⚠️ 분산이 0이면 부트스트랩 분포가 퇴화한다 → **p는 NaN**(정의 불가)을 돌려준다.
       (이전 판은 이 경우 p=0.0001을 돌려주어 잘못된 '유의'를 만들었다.)
    """
    if len(xs) < 2:
        return (float("nan"), float("nan"), float("nan"))
    obs = mean(xs)
    if stdev(xs) == 0:
        return (obs, obs, float("nan"))
    rng = random.Random(seed)
    n = len(xs)
    boots = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += xs[rng.randrange(n)]
        boots.append(s / n)
    boots.sort()
    lo = boots[int(alpha / 2 * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    centered = [x - obs for x in xs]
    cnt = 0
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += centered[rng.randrange(n)]
        if abs(s / n) >= abs(obs):
            cnt += 1
    p = (cnt + 1) / (n_boot + 1)
    return (lo, hi, p)


def _norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def wilcoxon_signed_rank(diffs):
    """양측 Wilcoxon signed-rank (정규근사 + 연속성보정 + tie 보정). 반환 (W, p).

    scipy 불필요. |d|=0 쌍은 제외(Wilcoxon 규약). n<6이면 (None, None) — 검정 불가.
    주 검정법: 계획서 §11.1 (양측 Wilcoxon, 장애인 단위 대응, Holm k=3).
    """
    d = [x for x in diffs if x is not None
         and not (isinstance(x, float) and math.isnan(x)) and x != 0.0]
    n = len(d)
    if n < 6:
        return (None, None)
    order = sorted(range(n), key=lambda i: abs(d[i]))
    avg = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            avg[order[k]] = r
        i = j + 1
    Wp = sum(avg[k] for k in range(n) if d[k] > 0)
    Wm = sum(avg[k] for k in range(n) if d[k] < 0)
    W = min(Wp, Wm)
    mu = n * (n + 1) / 4.0
    cnt = {}
    for x in d:
        a = abs(x)
        cnt[a] = cnt.get(a, 0) + 1
    tie = sum(t ** 3 - t for t in cnt.values())
    var = n * (n + 1) * (2 * n + 1) / 24.0 - tie / 48.0
    if var <= 0:
        return (W, None)
    z = (W - mu + 0.5) / math.sqrt(var)
    p = 2.0 * _norm_cdf(z)
    return (W, min(1.0, p))


def holm(pvals):
    """Holm 보정. 원래 순서대로 adjusted p를 반환."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for k, i in enumerate(order):
        val = (m - k) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj


def weighted_kappa_linear(pred, ref, k_min=SCORE_MIN, k_max=SCORE_MAX):
    """선형 가중 Cohen's κ (순서형 0–3). 둘이 모두 한 칸이면 None(정의 불가)."""
    if not pred:
        return None
    K = k_max - k_min + 1
    n = len(pred)
    po = 0.0
    for p, r in zip(pred, ref):
        w = 1.0 - abs(p - r) / float(K - 1)
        po += w
    po /= n
    rowp = [0] * K
    colp = [0] * K
    for p in pred:
        rowp[p - k_min] += 1
    for r in ref:
        colp[r - k_min] += 1
    pe = 0.0
    for i in range(K):
        for j in range(K):
            w = 1.0 - abs(i - j) / float(K - 1)
            pe += w * (rowp[i] / n) * (colp[j] / n)
    if abs(1.0 - pe) < 1e-12:
        return None
    return (po - pe) / (1.0 - pe)


def confusion(pred, ref):
    """ref(행) x pred(열) 혼동행렬."""
    K = SCORE_MAX - SCORE_MIN + 1
    m = [[0] * K for _ in range(K)]
    for p, r in zip(pred, ref):
        m[r - SCORE_MIN][p - SCORE_MIN] += 1
    return m


# ===========================================================================
# 입출력
# ===========================================================================
def _flag(v):
    """'1'/'0'/'' → 1/0/None"""
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return 1 if float(v) >= 0.5 else 0
    except ValueError:
        return None


def load_predictions(path):
    out = []
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ps = (row.get("predicted_score") or "").strip()
            st = (row.get("output_status") or "ok").strip() or "ok"
            try:
                score = int(float(ps))
            except ValueError:
                score = None
            rec = {
                "pid": row["participant_id"].strip(),
                "trial": row["trial_id"].strip(),
                "task": row.get("task", "").strip(),
                "condition": row["condition"].strip(),
                "injection": (row.get("injection") or "none").strip(),
                "run": int(float(row.get("run") or 1)),
                "score": score if (score is not None and SCORE_MIN <= score <= SCORE_MAX) else None,
                "status": st,
                "rationale": (row.get("rationale") or "").strip(),
            }
            # `*_provided` 열을 **동적으로** 전부 보존 (m1/m2/m4 또는 구 k1/k2)
            for k, v in row.items():
                if k and k.endswith("_provided"):
                    rec[k] = _flag(v)
            out.append(rec)
    return out


def load_references(path):
    refs = {}
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            t = row["trial_id"].strip()
            def val(k):
                v = (row.get(k) or "").strip()
                try:
                    return int(float(v))
                except ValueError:
                    return None
            refs[t] = {"pid": row["participant_id"].strip(),
                       "task": row.get("task", "").strip(),
                       "therapist": val("therapist_score"),
                       "independent": val("independent_score")}
    return refs


# ===========================================================================
# 핵심 집계
# ===========================================================================
def _iter_trials(preds, condition, injection="none", run=1, refs=None,
                 reference="therapist", task=None):
    """조건에 맞는 (pred_row, ref_score) 를 순회. refs=None이면 ref_score=None.

    `task`(예 "T2")가 주어지면 그 과제만 통과시킨다 — **주 분석은 T2 단독**(§11.1)."""
    for pr in preds:
        if pr["condition"] != condition or pr["injection"] != injection or pr["run"] != run:
            continue
        if task is not None and pr.get("task") != task:
            continue
        if refs is None:
            yield pr, None
            continue
        ref = refs.get(pr["trial"])
        if ref is None or ref[reference] is None:
            continue
        yield pr, ref[reference]


def per_patient_mae(preds, refs, condition, injection="none", run=1,
                    reference="therapist", only_ok=True, task=None):
    """{pid: {'mae':.., 'n':.., 'n_fail':.., 'loss_with_fail':..}}"""
    bucket = {}
    for pr, ref_score in _iter_trials(preds, condition, injection, run, refs, reference, task):
        b = bucket.setdefault(pr["pid"], {"errs": [], "n_fail": 0, "n_total": 0})
        b["n_total"] += 1
        if pr["status"] in FAIL_STATUSES or pr["score"] is None:
            b["n_fail"] += 1
            continue
        b["errs"].append(abs(pr["score"] - ref_score))
    out = {}
    for pid, b in bucket.items():
        mae = mean(b["errs"]) if (b["errs"] or not only_ok) else float("nan")
        err_sum = sum(b["errs"])
        loss = (err_sum + MAX_LOSS * b["n_fail"]) / b["n_total"] if b["n_total"] else float("nan")
        out[pid] = {"mae": mae, "n": len(b["errs"]), "n_fail": b["n_fail"],
                    "loss_with_fail": loss}
    return out


def per_patient_big_error(preds, refs, condition, injection="none", run=1,
                          reference="therapist", threshold=BIG_ERROR, task=None):
    """{pid: {'rate': 큰오차비율, 'n_big':.., 'n':..}}

    ⚠️ 평균 MAE는 위험을 숨긴다. 이 지표는 **평균이 아니라 위험**을 본다 (RQ-B3).
       실패 출력(parse/api/timeout)은 분모에서 제외하고 별도로 센다.
    """
    bucket = {}
    for pr, ref_score in _iter_trials(preds, condition, injection, run, refs, reference, task):
        b = bucket.setdefault(pr["pid"], {"n": 0, "n_big": 0, "n_fail": 0})
        if pr["status"] in FAIL_STATUSES or pr["score"] is None:
            b["n_fail"] += 1
            continue
        b["n"] += 1
        if abs(pr["score"] - ref_score) >= threshold:
            b["n_big"] += 1
    return {pid: {"rate": (b["n_big"] / b["n"]) if b["n"] else float("nan"),
                  "n_big": b["n_big"], "n": b["n"], "n_fail": b["n_fail"]}
            for pid, b in bucket.items()}


def abstention_stats(preds, condition, injection="none", run=1):
    """조건의 **수치 제공/보류** 통계. `<m*|k*>_provided` 열을 **자동 인식**한다.

    반환 {'n','rates':{key:rate},'keys':[...],'k1_rate','k2_rate','any_withheld','available'}
    (k1_rate/k2_rate는 구 스키마·구 보고서 호환용: m1→k1_rate, m2→k2_rate 로 매핑한다.)
    """
    keys = None
    n = 0
    sums = {}
    any_withheld = 0
    for pr, _ in _iter_trials(preds, condition, injection, run, None, None):
        if keys is None:
            keys = sorted({k[:-len("_provided")] for k in pr if k.endswith("_provided")})
            if not keys:
                keys = ["k1", "k2"]
        n += 1
        vals = {}
        for k in keys:
            v = pr.get(k + "_provided")
            if v is None or v == "":
                continue
            v = int(v)
            vals[k] = v
            d = sums.setdefault(k, [0, 0])
            d[0] += v
            d[1] += 1
        if any(v == 0 for v in vals.values()):
            any_withheld += 1
    rates = {k: (sums[k][0] / sums[k][1]) if sums.get(k, [0, 0])[1] else float("nan")
             for k in (keys or [])}
    return {
        "n": n,
        "rates": rates,
        "keys": list(keys or []),
        "k1_rate": rates.get("m1", rates.get("k1", float("nan"))),
        "k2_rate": rates.get("m2", rates.get("k2", float("nan"))),
        "any_withheld": (any_withheld / n) if n else float("nan"),
        "available": bool(sums),
    }


def paired_diff(a, b, key="mae", pids=None):
    """a - b 의 장애인별 차이. 양쪽에 값이 있는 장애인만."""
    ids = sorted(set(a) & set(b)) if pids is None else [p for p in pids if p in a and p in b]
    diffs = []
    for pid in ids:
        va, vb = a[pid][key], b[pid][key]
        if va is None or vb is None:
            continue
        if isinstance(va, float) and math.isnan(va):
            continue
        if isinstance(vb, float) and math.isnan(vb):
            continue
        diffs.append(va - vb)
    return diffs


def collect_scores(preds, refs, condition, injection="none", run=1, reference="therapist"):
    pred, ref = [], []
    for pr, ref_score in _iter_trials(preds, condition, injection, run, refs, reference):
        if pr["status"] in FAIL_STATUSES or pr["score"] is None:
            continue
        pred.append(pr["score"])
        ref.append(ref_score)
    return pred, ref


# ===========================================================================
# Pareto 곡선 (Q1 임계값 sweep) — RQ-B2의 핵심 그림
# ===========================================================================
def pareto_sweep(sweep_rows, refs, reference="therapist"):
    """Q1 임계값별 (보류율, MAE) 을 계산한다.

    입력 행 형식: {'pid','trial','q1_threshold','condition','score','status',
                   'k1_provided','k2_provided'}
    반환: 임계값 오름차순 list of dict
          {'threshold','n','abstention_rate','mae','big_error_rate','n_fail'}

    ⚠️ **합성·실측 무관하게 이 함수는 데이터가 있어야 돈다.** 임계값 sweep은
       VLM 재실행이 필요하므로 **컴퓨트 의존**이다 (계획서 §13).
    """
    by_thr = {}
    for r in sweep_rows:
        by_thr.setdefault(r["q1_threshold"], []).append(r)
    out = []
    for thr in sorted(by_thr):
        rows = by_thr[thr]
        errs = []
        n_fail = 0
        n_big = 0
        n_withheld = 0
        for r in rows:
            if (r.get("k1_provided") == 0) or (r.get("k2_provided") == 0):
                n_withheld += 1
            ref = refs.get(r["trial"])
            if ref is None or ref[reference] is None:
                continue
            if r["status"] in FAIL_STATUSES or r["score"] is None:
                n_fail += 1
                continue
            e = abs(r["score"] - ref[reference])
            errs.append(e)
            if e >= BIG_ERROR:
                n_big += 1
        out.append({
            "threshold": thr,
            "n": len(rows),
            "abstention_rate": (n_withheld / len(rows)) if rows else float("nan"),
            "mae": mean(errs),
            "big_error_rate": (n_big / len(errs)) if errs else float("nan"),
            "n_fail": n_fail,
        })
    return out


def load_sweep(path):
    rows = []
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ps = (row.get("predicted_score") or "").strip()
            try:
                score = int(float(ps))
            except ValueError:
                score = None
            try:
                thr = float((row.get("q1_threshold") or "").strip())
            except ValueError:
                continue
            rows.append({
                "pid": row["participant_id"].strip(),
                "trial": row["trial_id"].strip(),
                "task": row.get("task", "").strip(),
                "q1_threshold": thr,
                "condition": row["condition"].strip(),
                "score": score if (score is not None and SCORE_MIN <= score <= SCORE_MAX) else None,
                "status": (row.get("output_status") or "ok").strip() or "ok",
                "k1_provided": _flag(row.get("k1_provided")),
                "k2_provided": _flag(row.get("k2_provided")),
            })
    return rows


# ===========================================================================
# 보고서
# ===========================================================================
def analyze(preds, refs, reference="therapist", run=1, out_csv=None, sweep_rows=None,
            task="T2"):
    L = []
    pids = sorted({p["pid"] for p in preds})
    L.append("# 분석 결과 (v6.1 계획서 §9)")
    L.append("")
    L.append("- 장애인 수: %d" % len(pids))
    L.append("- 참조 평가자: **%s**" % reference)
    L.append("- run: %d (1=주결과)" % run)
    L.append("- bootstrap: %d회, seed=%d, 백분위 95%% CI" % (BOOT_N, BOOT_SEED))
    L.append("- **PR-1 = 수치 주입 효과** `MAE(A2) − MAE(A1)` (양수 = 주입이 해로움)")
    L.append("- **PR-2 = 게이팅 효과** `MAE(A2) − MAE(A3)` (양수 = A3가 더 정확)")
    L.append("- **PR-3 = 게이팅의 고유 가치** `MAE(R) − MAE(A3)` (양수 = 품질 규칙이 기여)")
    L.append("- **주 분석 대상: %s 단독** — 두 과제를 풀링하지 않는다(§11.1). "
             "T1은 2차(참고)로만 보고." % (task if task else "전체"))
    L.append("- **주 검정: 양측 Wilcoxon signed-rank**(장애인 단위 대응, Holm k=3). "
             "n<6이면 bootstrap p로 대체. paired t는 민감도.")
    L.append("- **주 기준 평가자: therapist**(현장 치료사). independent 는 라벨 민감도 분석.")
    L.append("- 오염 전파(bias_3u)는 **H5 기전, 탐색적**으로 보고")
    L.append("")

    # 장애인×조건 MAE 표
    per_cond = {}
    for c in CONDITIONS:
        per_cond[c] = per_patient_mae(preds, refs, c, "none", run, reference, task=task)
    L.append("## 조건별 장애인평균 MAE (주입 없음)")
    L.append("")
    L.append("> ⚠️ 이 표의 MAE는 **장애인별 MAE의 평균(장애인 동등 가중)** 이다. "
             "전체 시행을 풀링한 평균이 아니다. 분석 단위가 장애인이므로 이쪽이 맞다.")
    L.append("")
    L.append("| 조건 | 장애인수 | 평균 MAE | SD | 최소 | 최대 | 실패수 | 실패포함 손실 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for c in CONDITIONS:
        vals = [v["mae"] for v in per_cond[c].values()
                if v["mae"] is not None and not math.isnan(v["mae"])]
        if not vals:
            L.append("| %s | 0 | — | — | — | — | — | — |" % c)
            continue
        nf = sum(v["n_fail"] for v in per_cond[c].values())
        loss = mean([v["loss_with_fail"] for v in per_cond[c].values()][:len(vals)])
        L.append("| %s | %d | **%.3f** | %.3f | %.3f | %.3f | %d | %.3f |"
                 % (c, len(vals), mean(vals), stdev(vals), min(vals), max(vals), nf, loss))
    L.append("")

    # ---- 1급 기술 결과: 보류율 ----
    L.append("## 1급 기술 결과 ① — 보류율 (게이팅의 대가, 검정 아님)")
    L.append("")
    abst = {c: abstention_stats(preds, c, "none", run) for c in CONDITIONS}
    if not any(abst[c]["available"] for c in CONDITIONS):
        L.append("⚠️ **`k1_provided`/`k2_provided` 열이 없어 보류율을 계산할 수 없다.** "
                 "VLM 하네스가 이 두 열을 채워야 한다.")
    else:
        L.append("| 조건 | 시행수 | " + " | ".join(
            ("M%d 제공률" % (i + 1)) for i in range(max(1, len(abst["A2"]["keys"]))))
            + " | ≥1개 보류율 |")
        L.append("|---|---:|" + "---:|" * (max(1, len(abst["A2"]["keys"])) + 1))
        for c in NUMERIC_CONDITIONS:
            a = abst[c]
            if not a["available"]:
                L.append("| %s | %d | " % (c, a["n"])
                         + "— | " * (max(1, len(abst["A2"]["keys"])) + 1))
                continue
            cells = " | ".join("%.3f" % a["rates"].get(k, float("nan")) for k in a["keys"])
            L.append("| %s | %d | %s | **%.3f** |" % (c, a["n"], cells, a["any_withheld"]))
        L.append("")
        L.append("> ⚠️ **수치를 담지 않는 조건(A0·A0time·A1)은 표에서 제외했다.** "
                 "그 조건에서 '보류'는 의미가 없다(애초에 수치가 없다).")
        a2r, a3r = abst["A2"]["any_withheld"], abst["A3"]["any_withheld"]
        if not (isinstance(a2r, float) and math.isnan(a2r)):
            L.append("")
            L.append("- A2(전체 제공) 보류율 **%.3f** vs A3(게이팅) 보류율 **%.3f**" % (a2r, a3r))
            L.append("- **게이팅이 버린 정보량 = A3 보류율 − A2 보류율 = %.3f**" % (a3r - a2r))
    L.append("")

    # ---- 1급 기술 결과: 큰 오차 비율 ----
    L.append("## 1급 기술 결과 ② — 큰 오차(≥%d점) 비율 (위험 지표, 검정 아님)" % BIG_ERROR)
    L.append("")
    L.append("> 평균 MAE는 위험을 숨긴다. 척도가 0–3이므로 **2점 이상 오차**는 임상적으로 다른 사건이다.")
    L.append("")
    L.append("| 조건 | 장애인수 | 평균 큰오차 비율 | SD | 전체 큰오차/유효시행 |")
    L.append("|---|---:|---:|---:|---:|")
    for c in CONDITIONS:
        be = per_patient_big_error(preds, refs, c, "none", run, reference, task=task)
        vals = [v["rate"] for v in be.values()
                if v["rate"] is not None and not math.isnan(v["rate"])]
        if not vals:
            L.append("| %s | 0 | — | — | — |" % c)
            continue
        nb = sum(v["n_big"] for v in be.values())
        nn = sum(v["n"] for v in be.values())
        L.append("| %s | %d | **%.3f** | %.3f | %d/%d |"
                 % (c, len(vals), mean(vals), stdev(vals), nb, nn))
    L.append("")
    d_big = paired_diff(per_patient_big_error(preds, refs, "A2", "none", run, reference, task=task),
                        per_patient_big_error(preds, refs, "A3", "none", run, reference, task=task),
                        key="rate")
    if len(d_big) >= 2:
        ci = bootstrap_ci_mean(d_big)
        L.append("- **A2 − A3 큰오차 비율 차이: %+.3f** [%+.3f, %+.3f] (탐색적)"
                 % (mean(d_big), ci[0], ci[1]))
        L.append("  → 양수 = 게이팅이 큰 오차를 줄임 (RQ-B3)")
        L.append("")

    # ---- 확증적: PR-1, PR-2, PR-3 (v6.3, Holm k=3) ----
    a1 = per_cond["A1"]
    a2 = per_cond["A2"]
    a3 = per_cond["A3"]
    r_cond = per_cond["R"]
    a3_b3 = per_patient_mae(preds, refs, "A3", "bias_3u", run, reference, task=task)

    pr1 = paired_diff(a2, a1)          # MAE(A2) − MAE(A1)  수치 주입 효과
    pr2 = paired_diff(a2, a3)          # MAE(A2) − MAE(A3)  게이팅 효과
    pr3 = paired_diff(r_cond, a3)      # MAE(R)  − MAE(A3)  고유 가치

    ci1 = bootstrap_ci_mean(pr1)
    ci2 = bootstrap_ci_mean(pr2)
    ci3 = bootstrap_ci_mean(pr3)
    w1, w2, w3 = (wilcoxon_signed_rank(x) for x in (pr1, pr2, pr3))
    # 주 검정 = 양측 Wilcoxon(§11.1). n<6 등 p 불가면 bootstrap p로 대체.
    raw_p = [(w[1] if w[1] is not None else ci[2])
             for w, ci in ((w1, ci1), (w2, ci2), (w3, ci3))]
    adj_p = holm(raw_p)

    L.append("## 확증적 결과 (Holm 보정 **k=3**, α=0.05)")
    L.append("")
    L.append("| # | 정의 | 방향 | n | 평균 차이 | 95% CI | p(원) | p(Holm) | 판정 |")
    L.append("|---|---|---|---:|---:|---|---:|---:|---|")
    def verdict(ci):
        if math.isnan(ci[0]):
            return "계산 불가"
        if ci[0] > 0 or ci[1] < 0:
            return "✅ 0 미포함"
        return "❌ 0 포함"
    L.append("| **PR-1** | MAE(A2) − MAE(A1) | 양수 = 주입이 해로움 | %d | %+.3f | [%+.3f, %+.3f] | %.4f | %.4f | %s |"
             % (len(pr1), mean(pr1), ci1[0], ci1[1], raw_p[0], adj_p[0], verdict(ci1)))
    L.append("| **PR-2** | MAE(A2) − MAE(A3) | 양수 = 게이팅이 도움 | %d | %+.3f | [%+.3f, %+.3f] | %.4f | %.4f | %s |"
             % (len(pr2), mean(pr2), ci2[0], ci2[1], raw_p[1], adj_p[1], verdict(ci2)))
    L.append("| **PR-3** | MAE(R) − MAE(A3) | 양수 = 품질 규칙 기여 | %d | %+.3f | [%+.3f, %+.3f] | %.4f | %.4f | %s |"
             % (len(pr3), mean(pr3), ci3[0], ci3[1], raw_p[2], adj_p[2], verdict(ci3)))
    L.append("")
    L.append("**부호 해석:** PR-1 양수 = A2(수치 제공)가 A1(영상만)보다 나쁨. "
             "PR-2 양수 = A3(게이팅)가 A2(전체)보다 정확. "
             "PR-3 양수 = A3가 R(같은 양 무작위 제거)보다 정확.")
    L.append("")

    if task == "T2":
        pc1 = {c: per_patient_mae(preds, refs, c, "none", run, reference, task="T1")
               for c in CONDITIONS}
        d1 = paired_diff(pc1["A2"], pc1["A1"])
        d2 = paired_diff(pc1["A2"], pc1["A3"])
        d3 = paired_diff(pc1["R"], pc1["A3"])
        if any(len(x) >= 2 for x in (d1, d2, d3)):
            L.append("### 2차(참고) — T1(ARAT 3번, 블록). **주 분석 아님, 풀링하지 않음**")
            L.append("")
            L.append("| 비교 | n | 평균 차이 | 95% CI |")
            L.append("|---|---:|---:|---|")
            for lbl, d in (("PR-1 (A2-A1)", d1), ("PR-2 (A2-A3)", d2), ("PR-3 (R-A3)", d3)):
                if len(d) < 2:
                    L.append("| %s | %d | - | - |" % (lbl, len(d)))
                    continue
                ci = bootstrap_ci_mean(d)
                L.append("| %s | %d | %+.3f | [%+.3f, %+.3f] |"
                         % (lbl, len(d), mean(d), ci[0], ci[1]))
            L.append("")
    L.append("**판정표 연결(계획서 §10):**")
    L.append("")
    L.append("| 관측 | 허용되는 결론 |")
    L.append("|---|---|")
    L.append("| PR-1 유의, A2>A1 | 수치 주입이 채점을 악화시킴 |")
    L.append("| PR-1 유의, A2<A1 | 수치 주입이 채점을 개선함 |")
    L.append("| PR-1 비유의 | 이 표본에서 주입 효과를 확인하지 못함 → PR-2 해석이 약해짐 |")
    L.append("| PR-2 유의 | 품질 게이팅이 채점 오차를 줄임 |")
    L.append("| PR-2 비유의 | 이 표본에서 게이팅의 채점 개선을 확인하지 못함 |")
    L.append("| PR-3 유의 | 게이팅의 고유 가치 확인 (정보량 감소로 설명되지 않음) |")
    L.append("| PR-3 비유의 | 이득이 정보량 감소 효과로 설명될 수 있음 |")
    L.append("")

    # ---- 탐색적 ----
    L.append("## 탐색적 결과 (보정 없음 — 표/그림에 \"탐색적\" 표기 필수)")
    L.append("")
    L.append("> ⚠️ 부호 규약: 표의 값은 **X − Y** 이므로 **양수 = X의 MAE가 더 큼(더 부정확)** 이다.")
    L.append("")
    L.append("| 비교 | 의미 | n | 평균 차이 | 95% CI | p(원) |")
    L.append("|---|---|---:|---:|---|---:|")
    expl = [("A2 − A1", "숫자 추가 효과", "A2", "A1"),
            ("A3 − A4", "영상의 가치", "A3", "A4"),
            ("A0 − A3", "경량 통계모형 대비", "A0", "A3"),
            ("A0time − A3", "시간 단서만 대비", "A0time", "A3")]
    for label, meaning, x, y in expl:
        d = paired_diff(per_cond[x], per_cond[y])
        if len(d) < 2:
            L.append("| %s | %s | %d | — | — | — |" % (label, meaning, len(d)))
            continue
        ci = bootstrap_ci_mean(d)
        L.append("| %s | %s | %d | %+.3f | [%+.3f, %+.3f] | %.4f |"
                 % (label, meaning, len(d), mean(d), ci[0], ci[1], ci[2]))
    L.append("")
    L.append("### H5 기전 (탐색적) — 수치 오염이 채점으로 전파되는가")
    L.append("")
    L.append("| 비교 | n | 평균 차이 | 95% CI | p(원) |")
    L.append("|---|---:|---:|---|---:|")
    for inj in ("bias_1u", "bias_3u", "burst_3u"):
        d = paired_diff(per_patient_mae(preds, refs, "A3", inj, run, reference, task=task), a3)
        if len(d) < 2:
            continue
        ci = bootstrap_ci_mean(d)
        L.append("| A3(%s) − A3(none) | %d | %+.3f | [%+.3f, %+.3f] | %.4f |"
                 % (inj, len(d), mean(d), ci[0], ci[1], ci[2]))
    L.append("")

    # ---- Pareto 곡선 ----
    if sweep_rows:
        L.append("## Pareto 곡선 (Q1 임계값 sweep) — RQ-B2")
        L.append("")
        curve = pareto_sweep(sweep_rows, refs, reference)
        L.append("| Q1 임계값 | n | 보류율 | MAE | 큰오차율 | 실패수 |")
        L.append("|---:|---:|---:|---:|---:|---:|")
        for p in curve:
            L.append("| %.3f | %d | %.3f | %.3f | %.3f | %d |"
                     % (p["threshold"], p["n"], p["abstention_rate"],
                        p["mae"], p["big_error_rate"], p["n_fail"]))
        L.append("")
        L.append("> 이 표를 **(보류율, MAE)** 평면에 그리면 게이팅의 트레이드오프 곡선이 된다.")
        L.append("> \"보류율을 올리면 MAE가 얼마나 내려가는가\"가 게이팅의 실제 가치다.")
        L.append("")

    # ---- 부가 지표 ----
    pred3, ref3 = collect_scores(preds, refs, "A3", "none", run, reference)
    L.append("## 부가 지표 (A3, 주입 없음)")
    L.append("")
    if pred3:
        exact = sum(1 for p, r in zip(pred3, ref3) if p == r) / len(pred3)
        k = weighted_kappa_linear(pred3, ref3)
        over = sum(1 for p, r in zip(pred3, ref3) if r <= 1 and p == 3)
        n_low = sum(1 for r in ref3 if r <= 1)
        cm = confusion(pred3, ref3)
        L.append("- 정확일치율: **%.3f**" % exact)
        L.append("- 선형 가중 κ: **%s**" % ("계산 불가(한 칸에 몰림)" if k is None else "%.3f" % k))
        L.append("- 0–1 → 3 과대평가: **%d건 / %d건**" % (over, n_low))
        L.append("- 혼동행렬 (행=사람, 열=모델):")
        L.append("")
        L.append("| ref\\pred | 0 | 1 | 2 | 3 |")
        L.append("|---|---:|---:|---:|---:|")
        for i, row in enumerate(cm):
            L.append("| **%d** | %s |" % (i, " | ".join(str(v) for v in row)))
    L.append("")

    # ---- 라벨 불확실 ----
    nu = [t for t, r in refs.items() if r.get("independent") is not None
          and r.get("therapist") is not None and r["independent"] != r["therapist"]]
    n_with_both = [t for t, r in refs.items() if r.get("independent") is not None]
    L.append("## 라벨 불확실성")
    L.append("")
    L.append("- 두 평가자 모두 있는 시행: %d" % len(n_with_both))
    L.append("- 서로 다른 점수(라벨 불확실): **%d건 (%.1f%%)**"
             % (len(nu), 100.0 * len(nu) / len(n_with_both) if n_with_both else 0.0))
    L.append("")

    report = "\n".join(L)

    if out_csv:
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        fields = ["participant_id", "condition"] + \
                 ["mae_%s" % reference, "n", "n_fail", "loss_with_fail"]
        with io.open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(fields)
            for c in CONDITIONS:
                for pid in pids:
                    v = per_cond[c].get(pid)
                    if not v:
                        continue
                    w.writerow([pid, c, v["mae"], v["n"], v["n_fail"], v["loss_with_fail"]])
    return report


# ===========================================================================
# 오라클
# ===========================================================================
def selftest():
    ok_all = True
    log = []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-52s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    print("[A1] MAE 계산")
    preds = [{"pid": "P1", "trial": "t1", "condition": "A1", "injection": "none",
              "run": 1, "score": 3, "status": "ok", "task": "T1",
              "k1_provided": 0, "k2_provided": 0},
             {"pid": "P1", "trial": "t2", "condition": "A1", "injection": "none",
              "run": 1, "score": 2, "status": "ok", "task": "T1",
              "k1_provided": 0, "k2_provided": 0},
             {"pid": "P1", "trial": "t3", "condition": "A1", "injection": "none",
              "run": 1, "score": 1, "status": "ok", "task": "T1",
              "k1_provided": 0, "k2_provided": 0},
             {"pid": "P1", "trial": "t4", "condition": "A1", "injection": "none",
              "run": 1, "score": 0, "status": "ok", "task": "T1",
              "k1_provided": 0, "k2_provided": 0}]
    refs = {"t1": {"pid": "P1", "therapist": 3, "independent": 3, "task": "T1"},
            "t2": {"pid": "P1", "therapist": 1, "independent": 1, "task": "T1"},
            "t3": {"pid": "P1", "therapist": 2, "independent": 2, "task": "T1"},
            "t4": {"pid": "P1", "therapist": 3, "independent": 3, "task": "T1"}}
    m = per_patient_mae(preds, refs, "A1", "none", 1, "therapist")
    # |3-3| + |2-1| + |1-2| + |0-3| = 0+1+1+3 = 5 / 4 = 1.25
    chk("MAE == 1.250", abs(m["P1"]["mae"] - 1.25) < 1e-9, "got %s" % m["P1"]["mae"])

    print("[A2] 실패 처리 (loss=3)")
    preds2 = [dict(p) for p in preds]
    preds2[0]["status"] = "api_failed"
    preds2[0]["score"] = None
    m2 = per_patient_mae(preds2, refs, "A1", "none", 1, "therapist")
    # 유효 오차 = 1+1+3 = 5 / 3 = 1.667 ; 실패포함 = (5 + 3*1)/4 = 2.0
    chk("MAE(유효만) == 1.667", abs(m2["P1"]["mae"] - 5.0 / 3) < 1e-9, "got %.4f" % m2["P1"]["mae"])
    chk("실패포함 손실 == 2.000", abs(m2["P1"]["loss_with_fail"] - 2.0) < 1e-9,
        "got %.4f" % m2["P1"]["loss_with_fail"])
    chk("실패 1건 집계", m2["P1"]["n_fail"] == 1)

    print("[A3] Holm 보정")
    p = [0.01, 0.03, 0.04]
    adj = holm(p)
    chk("Holm([.01,.03,.04]) == [.03,.06,.06]",
        all(abs(a - b) < 1e-12 for a, b in zip(adj, [0.03, 0.06, 0.06])), str(adj))
    chk("Holm 단조성", all(adj[i] >= p[i] - 1e-12 for i in range(3)))

    print("[A4] 선형 가중 κ (손계산 값으로 검증)")
    chk("완전일치 → 1.0", abs(weighted_kappa_linear([0, 1, 2, 3], [0, 1, 2, 3]) - 1.0) < 1e-12)
    # 손계산: pred=[0,1,2,3], ref=[1,0,3,2]
    #   po = (1-1/3)*4/4 = 0.6667
    #   pe = Σ w_ij (1/4)(1/4) = 9.3333/16 = 0.5833
    #   κ = (0.6667-0.5833)/(1-0.5833) = **0.2**
    k_hat = weighted_kappa_linear([0, 1, 2, 3], [1, 0, 3, 2])
    chk("역방향 배치 κ == 0.200 (선형가중은 관대)", abs(k_hat - 0.2) < 1e-9, "got %.6f" % k_hat)
    # 진짜 음수 κ: po=0, pe=0.5 → κ = -1.0
    k_neg = weighted_kappa_linear([0, 0, 3, 3], [3, 3, 0, 0])
    chk("극단 불일치 κ == -1.000", abs(k_neg + 1.0) < 1e-9, "got %.6f" % k_neg)
    chk("한 칸 몰림 → None", weighted_kappa_linear([3, 3, 3], [3, 3, 3]) is None)

    print("[A5] bootstrap CI (알려진 값)")
    xs = [1.0] * 12
    lo, hi, pv = bootstrap_ci_mean(xs)
    chk("모두 1.0 → CI=[1,1]", abs(lo - 1.0) < 1e-12 and abs(hi - 1.0) < 1e-12, "[%s,%s]" % (lo, hi))
    chk("분산 0 → p는 NaN(퇴화 보호)", math.isnan(pv), "p=%s" % pv)
    xs2 = [2.0] * 6 + [0.0] * 6
    lo2, hi2, pv2 = bootstrap_ci_mean(xs2)
    chk("평균 1.0, CI가 0 미포함", lo2 > 0 and hi2 > 0, "[%.2f,%.2f] p=%.4f" % (lo2, hi2, pv2))

    print("[A6] paired_diff 부호")
    a = {"P1": {"mae": 2.0}, "P2": {"mae": 3.0}}
    b = {"P1": {"mae": 1.0}, "P2": {"mae": 1.0}}
    d = paired_diff(a, b)
    chk("a-b == [1.0, 2.0]", d == [1.0, 2.0], str(d))

    print("[A7] PR-1/PR-2 배선 (D-12 회귀 방지)")
    # A2가 A3보다 나쁜 상황을 만들면 MAE(A2)-MAE(A3) > 0 이어야 한다.
    mk = lambda cond, s: [{"pid": "P1", "trial": "t%d" % i, "condition": cond,
                           "injection": "none", "run": 1, "score": s,
                           "status": "ok", "task": "T1",
                           "k1_provided": 1, "k2_provided": 1} for i in range(4)]
    pr_a1 = mk("A1", 1)     # 오차 1
    pr_a2 = mk("A2", 3)     # 오차 3
    pr_a3 = mk("A3", 1)     # 오차 1
    refs0 = {"t%d" % i: {"pid": "P1", "therapist": 0, "independent": 0, "task": "T1"}
             for i in range(4)}
    m_a1 = per_patient_mae(pr_a1, refs0, "A1", "none", 1, "therapist")
    m_a2 = per_patient_mae(pr_a2, refs0, "A2", "none", 1, "therapist")
    m_a3 = per_patient_mae(pr_a3, refs0, "A3", "none", 1, "therapist")
    dpr1 = paired_diff(m_a2, m_a1)      # 주입 효과 = 3-1 = +2
    dpr2 = paired_diff(m_a2, m_a3)      # 게이팅 효과 = 3-1 = +2
    chk("PR-1 = MAE(A2)-MAE(A1) == +2.0", abs(dpr1[0] - 2.0) < 1e-9, str(dpr1))
    chk("PR-2 = MAE(A2)-MAE(A3) == +2.0", abs(dpr2[0] - 2.0) < 1e-9, str(dpr2))
    # 동일 조건끼리는 0 (배선이 조건을 섞으면 여기가 깨진다)
    d_same = paired_diff(m_a3, m_a1)
    chk("A3(1) - A1(1) == 0.0 (조건 미분리 감지)", abs(d_same[0]) < 1e-9, str(d_same))

    print("[A8] 보류율 계산")
    pr_ab = [{"pid": "P1", "trial": "a", "condition": "A3", "injection": "none",
              "run": 1, "score": 2, "status": "ok", "task": "T1",
              "k1_provided": 1, "k2_provided": 1},
             {"pid": "P1", "trial": "b", "condition": "A3", "injection": "none",
              "run": 1, "score": 2, "status": "ok", "task": "T1",
              "k1_provided": 0, "k2_provided": 1},
             {"pid": "P1", "trial": "c", "condition": "A3", "injection": "none",
              "run": 1, "score": 2, "status": "ok", "task": "T1",
              "k1_provided": 1, "k2_provided": 0},
             {"pid": "P1", "trial": "d", "condition": "A3", "injection": "none",
              "run": 1, "score": 2, "status": "ok", "task": "T1",
              "k1_provided": 0, "k2_provided": 0}]
    ab = abstention_stats(pr_ab, "A3", "none", 1)
    chk("K1 제공률 == 0.50", abs(ab["k1_rate"] - 0.50) < 1e-9, "got %.3f" % ab["k1_rate"])
    chk("K2 제공률 == 0.50", abs(ab["k2_rate"] - 0.50) < 1e-9, "got %.3f" % ab["k2_rate"])
    chk("≥1개 보류율 == 0.75", abs(ab["any_withheld"] - 0.75) < 1e-9, "got %.3f" % ab["any_withheld"])
    chk("available == True", ab["available"] is True)
    pr_no = [dict(p, k1_provided=None, k2_provided=None) for p in pr_ab]
    chk("열 없으면 available == False", abstention_stats(pr_no, "A3")["available"] is False)

    print("[A9] 큰 오차(≥2점) 비율")
    pr_be = [{"pid": "P1", "trial": "t1", "condition": "A2", "injection": "none",
              "run": 1, "score": 3, "status": "ok", "task": "T1",
              "k1_provided": 1, "k2_provided": 1},
             {"pid": "P1", "trial": "t2", "condition": "A2", "injection": "none",
              "run": 1, "score": 3, "status": "ok", "task": "T1",
              "k1_provided": 1, "k2_provided": 1},
             {"pid": "P1", "trial": "t3", "condition": "A2", "injection": "none",
              "run": 1, "score": 2, "status": "ok", "task": "T1",
              "k1_provided": 1, "k2_provided": 1},
             {"pid": "P1", "trial": "t4", "condition": "A2", "injection": "none",
              "run": 1, "score": None, "status": "timeout", "task": "T1",
              "k1_provided": 1, "k2_provided": 1}]
    refs_be = {"t1": {"pid": "P1", "therapist": 0, "independent": 0, "task": "T1"},
               "t2": {"pid": "P1", "therapist": 0, "independent": 0, "task": "T1"},
               "t3": {"pid": "P1", "therapist": 2, "independent": 2, "task": "T1"},
               "t4": {"pid": "P1", "therapist": 1, "independent": 1, "task": "T1"}}
    be = per_patient_big_error(pr_be, refs_be, "A2", "none", 1, "therapist")
    # 유효 3건 중 오차 3,3,0 → 큰오차(≥2) 2건 → 0.667 ; 실패 1건은 분모 제외
    chk("큰오차 비율 == 0.667", abs(be["P1"]["rate"] - 2.0 / 3) < 1e-9, "got %.4f" % be["P1"]["rate"])
    chk("실패는 분모 제외 (n==3)", be["P1"]["n"] == 3, "n=%d" % be["P1"]["n"])
    chk("실패 1건 별도 집계", be["P1"]["n_fail"] == 1)

    print("[A10] Pareto sweep")
    sw = []
    for thr, k1, sc in ((0.10, 1, 3), (0.20, 0, 2), (0.30, 0, 1)):
        sw.append({"pid": "P1", "trial": "t1", "task": "T1", "q1_threshold": thr,
                   "condition": "A3", "score": sc, "status": "ok",
                   "k1_provided": k1, "k2_provided": 1})
    refs_sw = {"t1": {"pid": "P1", "therapist": 0, "independent": 0, "task": "T1"}}
    curve = pareto_sweep(sw, refs_sw, "therapist")
    chk("임계값 3개, 오름차순",
        [c["threshold"] for c in curve] == [0.10, 0.20, 0.30], str([c["threshold"] for c in curve]))
    chk("보류율 0.00 → 0.67 → 1.00",
        abs(curve[0]["abstention_rate"] - 0.0) < 1e-9
        and abs(curve[1]["abstention_rate"] - 1.0) < 1e-9
        and abs(curve[2]["abstention_rate"] - 1.0) < 1e-9,
        str([round(c["abstention_rate"], 3) for c in curve]))
    chk("MAE 3 → 2 → 1 (보류↑ = MAE↓)",
        abs(curve[0]["mae"] - 3) < 1e-9 and abs(curve[1]["mae"] - 2) < 1e-9
        and abs(curve[2]["mae"] - 1) < 1e-9,
        str([c["mae"] for c in curve]))

    print("[A11] Wilcoxon signed-rank (주 검정, §11.1)")
    w, p = wilcoxon_signed_rank([1.0, 1.2, 0.8, 1.5, 0.9, 1.1, 1.3, 0.7])
    chk("8쌍 모두 양수 → p < 0.05", w is not None and p is not None and p < 0.05,
        "W=%s p=%s" % (w, ("%.5f" % p) if p is not None else p))
    wb, pb = wilcoxon_signed_rank([1, -1, 1, -1, 1, -1, 1, -1])
    chk("부호 섮이면 p 큼(>0.5)", pb is not None and pb > 0.5, "p=%s" % pb)
    chk("n<6 → (None, None) 검정 불가", wilcoxon_signed_rank([1.0, 2.0, 3.0]) == (None, None))
    chk("0 차이는 제외", wilcoxon_signed_rank([0.0, 0.0, 0.0]) == (None, None))

    print("[A12] 주 분석 T2 단독(과제 필터, §11.1)")
    preds_t = [{"condition": "A1", "injection": "none", "run": 1, "pid": "P1",
                "trial": "t1", "task": "T2", "score": 1, "status": "ok"},
               {"condition": "A1", "injection": "none", "run": 1, "pid": "P1",
                "trial": "t2", "task": "T1", "score": 3, "status": "ok"}]
    n_all = len(list(_iter_trials(preds_t, "A1", "none", 1, None, None, None)))
    n_t2 = len(list(_iter_trials(preds_t, "A1", "none", 1, None, None, "T2")))
    chk("과제 필터: 전체 2건 vs T2 1건", n_all == 2 and n_t2 == 1, "%d/%d" % (n_all, n_t2))

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "analysis_oracle.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("[saved] %s" % out)
    return ok_all


# ===========================================================================
# 합성 데모 (엔드투엔드: predictions.csv + reference.csv → 보고서)
# ===========================================================================
def make_demo(root, n_pat=12, n_trials=3, seed=20260922):
    """알려진 효과를 심은 합성 데이터셋을 만든다.

    ⚠️ **합성이다. 실제 결과 아님. 논문 인용 금지.**
    심어둔 효과 (v6.3 배선에 맞춤):
      - **A2(수치 제공)가 A1(영상만)보다 나쁨** → PR-1 = MAE(A2)−MAE(A1) > 0 검출 기대
      - **A3(게이팅)가 A2(전체)보다 정확** → PR-2 = MAE(A2)−MAE(A3) > 0 검출 기대
      - **R(무작위 제거)이 A3보다 나쁨** → PR-3 = MAE(R)−MAE(A3) > 0 검출 기대
      - **A3는 수치를 일부 보류** → 보류율 > 0
    ⚠️ 효과 크기는 **파이프라인 검출 능력을 보이려고 크게** 잡았다. 실제 효과크기가 아니다.
    """
    rng = random.Random(seed)
    os.makedirs(root, exist_ok=True)
    # 조건별 "기본으로 틀릴 확률". A3 < R < A2 순서가 핵심 (PR-1·PR-2 검출용)
    BASE_ERR = {"A0": 0.62, "A0time": 0.66, "A1": 0.55, "A2": 0.62,
                "A3": 0.22, "A4": 0.45, "R": 0.48}
    GATE_WITHHOLD_P = 0.18     # A3에서 지표별 보류 확률
    pred_rows, ref_rows = [], []
    for pi in range(1, n_pat + 1):
        pid = "P%02d" % pi
        for ti in range(1, n_trials + 1):
            for task in ("T1", "T2"):
                tid = "%s_%s_t%02d" % (pid, task, ti)
                truth = rng.choice([0, 1, 2, 2, 3, 3])       # 1·2 구간 강조
                indep = truth if rng.random() < 0.75 else min(3, max(0, truth + rng.choice([-1, 1])))
                ref_rows.append([pid, tid, task, truth, indep])
                for cond in CONDITIONS:
                    for inj in INJECTIONS:
                        if inj != "none" and cond not in ("A2", "A3"):
                            continue
                        # 조건·시행별 독립 난수 (조건 간 상관 제거)
                        rr = random.Random(zlib.crc32(
                            ("%s|%s|%s|%s|%d" % (pid, tid, cond, inj, seed)).encode("utf-8")))
                        base_p = BASE_ERR[cond]
                        err = 1 if rr.random() < base_p else 0
                        # 오차 크기: 1점(80%) / 2점(20%) → 큰 오차(≥2) 비율이 0이 되지 않도록
                        mag = 2 if rr.random() < 0.20 else 1
                        pred = max(0, min(3, truth + (rr.choice([-1, 1]) * mag if err else 0)))
                        # --- 심어둔 효과: A2에 bias_3u → 오차 증가 (H5 기전 검출용)
                        if cond == "A2" and inj == "bias_3u" and rr.random() < 0.4:
                            pred = max(0, min(3, pred + (1 if pred < 3 else -1)))
                        # --- 수치 제공 여부 (보류율 계산용)
                        if cond == "A2":
                            k1p, k2p = 1, 1
                        elif cond in ("A3", "A4"):
                            k1p = 0 if rr.random() < GATE_WITHHOLD_P else 1
                            k2p = 0 if rr.random() < GATE_WITHHOLD_P else 1
                        elif cond == "R":
                            # A3와 같은 양을 무작위로 제거 → 보류율은 비슷
                            k1p = 0 if rr.random() < GATE_WITHHOLD_P else 1
                            k2p = 0 if rr.random() < GATE_WITHHOLD_P else 1
                        else:
                            k1p, k2p = 0, 0
                        status = "ok"
                        if rr.random() < 0.01:
                            status, pred = "parse_failed", None
                        pred_rows.append([pid, tid, task, cond, inj, 1,
                                          "" if pred is None else pred, "", status,
                                          k1p, k2p])
    pp = os.path.join(root, "predictions.csv")
    rp = os.path.join(root, "reference.csv")
    with io.open(pp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["participant_id", "trial_id", "task", "condition", "injection",
                    "run", "predicted_score", "rationale", "output_status",
                    "k1_provided", "k2_provided"])
        w.writerows(pred_rows)
    with io.open(rp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["participant_id", "trial_id", "task",
                    "therapist_score", "independent_score"])
        w.writerows(ref_rows)
    return pp, rp, len(pred_rows), len(ref_rows)


def make_demo_sweep(root, refs_path, seed=20260922):
    """Pareto 곡선용 합성 sweep 데이터. 임계값이 커지면 보류율↑ · MAE↓.

    ⚠️ 합성이다. 실제 결과 아님.
    ⚠️ **정답은 `reference.csv`에서 읽는다.** 자체 `truth`를 새로 뽑으면 기준과
       어긋나 MAE가 부풀려진다 (2026-09-24 발견·수정).
    """
    rng = random.Random(seed + 7)
    thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]
    # reference.csv 에서 (trial -> truth) 를 읽어 sweep 이 같은 기준을 쓰게 한다
    truth_of = {}
    with io.open(refs_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            v = (row.get("therapist_score") or "").strip()
            try:
                truth_of[row["trial_id"].strip()] = int(float(v))
            except ValueError:
                pass
    rows = []
    for tid, truth in truth_of.items():
        parts = tid.split("_")
        pid = parts[0] if parts else "P??"
        task = parts[1] if len(parts) > 1 else "T?"
        for thr in thresholds:
            rr = random.Random(zlib.crc32(("%s|%s|%.2f" % (tid, task, thr)).encode("utf-8")))
            # 임계값이 커지면 보류가 늘고 오차가 줄도록 설계
            withhold = rr.random() < thr
            err_p = 0.30 * (1.0 - thr) + 0.03
            mag = 2 if rr.random() < 0.20 else 1
            pred = max(0, min(3, truth + (rr.choice([-1, 1]) * mag if rr.random() < err_p else 0)))
            rows.append([pid, tid, task, thr, "A3",
                         pred, "ok", 0 if withhold else 1, 0 if withhold else 1])
    sp = os.path.join(root, "sweep.csv")
    with io.open(sp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["participant_id", "trial_id", "task", "q1_threshold", "condition",
                    "predicted_score", "output_status", "k1_provided", "k2_provided"])
        w.writerows(rows)
    return sp, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--predictions")
    ap.add_argument("--reference")
    ap.add_argument("--sweep", help="Pareto 곡선용 sweep.csv")
    ap.add_argument("--task", default="T2",
                    help="주 분석 과제 (기본 T2; 전체는 all)")
    ap.add_argument("--reference-rater", default="therapist",
                    choices=["therapist", "independent"])
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest() else 1)

    sweep_rows = None
    if a.demo:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")
        pp, rp, np_, nr = make_demo(base)
        sp, ns = make_demo_sweep(base, rp)
        print("[demo] 합성 데이터 생성: %s" % base)
        print("       predictions %d행 / reference %d행 / sweep %d행 (⚠️ 합성)" % (np_, nr, ns))
        preds = load_predictions(pp)
        refs = load_references(rp)
        sweep_rows = load_sweep(sp)
    else:
        if not (a.predictions and a.reference):
            print(__doc__); return
        preds = load_predictions(a.predictions)
        refs = load_references(a.reference)
        if a.sweep:
            sweep_rows = load_sweep(a.sweep)

    out_csv = a.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results", "per_patient_mae.csv")
    rep = analyze(preds, refs, a.reference_rater, 1, out_csv, sweep_rows,
                  task=(None if a.task == "all" else a.task))
    print(rep)
    rp_out = os.path.join(os.path.dirname(out_csv),
                          "analysis_report_demo.txt" if a.demo else "analysis_report.txt")
    with io.open(rp_out, "w", encoding="utf-8") as f:
        f.write(rep + "\n")
    print("[saved] %s" % rp_out)
    if a.demo:
        print("[saved] %s" % out_csv)
        print("")
        print("⚠️ 위 수치는 **합성 데이터**에 심어둔 효과의 검출 여부를 본 것이다.")
        print("   실제 실험 결과가 아니다. 논문 인용 금지.")


if __name__ == "__main__":
    main()

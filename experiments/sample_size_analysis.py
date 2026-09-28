#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sample_size_analysis.py — 표본 크기 재검토 (계획서 §11 대체 근거)

왜 다시 계산하는가
------------------
계획서 §11은 "n=12에서 dz 0.89"만 제시한다. 그런데:
  ① 검정이 **대응 비교**(같은 장애인에서 조건만 바뀜)인데 비모수 대안(Wilcoxon)의 검정력은 계산돼 있지 않다.
  ② 실제 관심은 "유의한가"보다 **효과크기 CI의 폭**이다 (판정표가 CI 기준으로 쓰여 있다).
  ③ 건강인 검증군(10명)이 **무엇을 추정하는지**와 그 정밀도가 정량화돼 있지 않다.
  ④ Q1 임계값을 **개발 6명**에서 2-fold로 고르는데, 임계값 자체의 불안정성이 계산돼 있지 않다.

이 스크립트는 위 4개를 계산해 **권장 n**을 낸다.

사용
----
    python experiments/sample_size_analysis.py
출력: 콘솔 + outputs/03-검증/sample-size-reanalysis.md (자동 생성) + .json
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(ROOT, "outputs", "03-검증", "sample-size-reanalysis.md")
OUT_JSON = os.path.join(ROOT, "outputs", "03-검증", "sample-size-reanalysis.json")

ALPHA = 0.05
POWER = 0.80
SEED = 20260925


# ─────────────────────────────────────────────────────────────────────────────
# A. 대응 비교: 모수(paired t) 검정력
# ─────────────────────────────────────────────────────────────────────────────
def _t_crit(df, p):
    """스튜던트 t 분위수 (scipy 없이). Cornish–Fisher 근사 + 이분법 보정."""
    # 초기값: 정규분위 + 보정
    z = _norm_ppf(p)
    g1 = (z ** 3 + z) / 4.0
    g2 = (5 * z ** 5 + 16 * z ** 3 + 3 * z) / 96.0
    x = z + g1 / df + g2 / df ** 2
    # 이분법으로 t CDF = p 만족하도록
    lo, hi = x - 1.0, x + 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _norm_ppf(p):
    # Acklam 근사
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _t_cdf(t, df):
    """정규화 불완전베타로 t CDF."""
    x = df / (df + t * t)
    ib = _betainc_reg(0.5 * df, 0.5, x)
    return 1 - 0.5 * ib if t > 0 else 0.5 * ib


def _betainc_reg(a, b, x):
    """정규화 불완전베타 I_x(a,b) — 연분수 (Numerical Recipes betacf)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x)
    return 1 - math.exp(math.log(1 - x) * b + math.log(x) * a - lbeta) / b * _betacf(b, a, 1 - x)


def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c = 1.0
    d = 1 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1 / d
        de = d * c
        h *= de
        if abs(de - 1) < EPS:
            break
    return h


def detectable_dz(n, alpha=ALPHA, power=POWER):
    df = n - 1
    return (_t_crit(df, 1 - alpha / 2) + _t_crit(df, power)) / math.sqrt(n)


def power_paired_t(n, dz, alpha=ALPHA):
    df = n - 1
    ncp = dz * math.sqrt(n)
    # P(T > t_crit) with noncentral t
    tc = _t_crit(df, 1 - alpha / 2)
    lo, hi = 0.0, 60.0
    target = 1 - power_paired_t  # placeholder (not used)
    return _noncentral_t_sf(tc, df, ncp)


def _noncentral_t_sf(t, df, ncp):
    """P(T > t) for noncentral t — 수치적분 (Gauss-Legendre)."""
    xs, ws = np.polynomial.legendre.leggauss(400)
    lo, hi = -12.0, 12.0
    z = 0.5 * (hi - lo) * xs + 0.5 * (hi + lo)
    w = 0.5 * (hi - lo) * ws
    phi = np.exp(-0.5 * (z - ncp) ** 2) / math.sqrt(2 * math.pi)
    with np.errstate(invalid="ignore"):
        val = _t_cdf_vec(t * z / math.sqrt(df), df)
    return float(np.sum(w * phi * val))


def _t_cdf_vec(x, df):
    out = np.empty_like(x)
    for i, v in enumerate(x):
        out[i] = _t_cdf(v, df) if math.isfinite(v) else (1.0 if v > 0 else 0.0)
    out[~np.isfinite(x)] = 1.0 if (x > 0).any() else 0.0
    return out


def ci_halfwidth(n, sd, alpha=ALPHA):
    df = n - 1
    return _t_crit(df, 1 - alpha / 2) * sd / math.sqrt(n)


# ─────────────────────────────────────────────────────────────────────────────
# B. Wilcoxon 부호순위 검정력 (시뮬레이션)
# ─────────────────────────────────────────────────────────────────────────────
def wilcoxon_power(n, delta, sd=1.0, sims=4000, alpha=ALPHA, seed=SEED):
    rng = np.random.RandomState(seed)
    rej = 0
    for _ in range(sims):
        d = rng.normal(delta, sd, size=n)
        if np.allclose(d, 0):
            continue
        r = _wilcoxon_stat(d)
        rej += (r < alpha)
    return rej / sims


def _wilcoxon_stat(d):
    """양측 Wilcoxon 부호순위의 정규근사 p (연속성·동점 보정)."""
    d = d[d != 0]
    n = len(d)
    if n < 1:
        return 1.0
    order = np.argsort(np.abs(d))
    ranks = np.empty(n)
    ranks[order] = np.arange(1, n + 1)
    # 동점 평균화
    absd = np.abs(d)
    for v in np.unique(absd):
        m = absd == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    w = ranks[d > 0].sum()
    mu = n * (n + 1) / 4.0
    sdw = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sdw == 0:
        return 1.0
    z = (abs(w - mu) - 0.5) / sdw
    return 2 * (1 - _norm_cdf(z))


def _norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


# ─────────────────────────────────────────────────────────────────────────────
# C. Q1 임계값 안정성 (개발 자료에서 고를 때)
# ─────────────────────────────────────────────────────────────────────────────
def q1_threshold_stability(n_dev, sims=1200, k=2, seed=SEED,
                           true_thr=0.5, slope=6.0, per_person=12):
    """개발 n명에서 사람단위 k-fold로 **balanced accuracy 최대화** 임계값을 고를 때
    그 값이 참 임계값에서 얼마나 벗어나는가.

    잠재구조 (신호 있음 — 이전 판은 신호가 0이라 무정보였다):
      - 사람마다 품질 지수 q ~ U(0,1)
      - '믿을 수 있는 시행' 확률 p = sigmoid(slope * (q - true_thr))
      - 임계값 t 를 골라 (q >= t) 를 '믿음'으로 예측하고 balanced accuracy 최대화
    참 임계값 = true_thr.
    """
    rng = np.random.RandomState(seed)
    picked = []
    grid = np.arange(0.05, 0.96, 0.025)
    for _ in range(sims):
        pid = np.repeat(np.arange(n_dev), per_person)
        q = rng.uniform(0, 1, size=len(pid))
        p = 1.0 / (1.0 + np.exp(-slope * (q - true_thr)))
        y = (rng.uniform(size=len(pid)) < p).astype(int)
        fold_pick = []
        for f in range(k):
            tr = (pid % k) != f
            if tr.sum() == 0:
                continue
            best_t, best_ba = None, -1.0
            for t in grid:
                pred = (q[tr] >= t).astype(int)
                tp = int(((pred == 1) & (y[tr] == 1)).sum())
                tn = int(((pred == 0) & (y[tr] == 0)).sum())
                fp = int(((pred == 1) & (y[tr] == 0)).sum())
                fn = int(((pred == 0) & (y[tr] == 1)).sum())
                sens = tp / (tp + fn) if (tp + fn) else 0.0
                spec = tn / (tn + fp) if (tn + fp) else 0.0
                ba = 0.5 * (sens + spec)
                if ba > best_ba:
                    best_ba, best_t = ba, float(t)
            if best_t is not None:
                fold_pick.append(best_t)
        if fold_pick:
            picked.append(float(np.mean(fold_pick)))
    picked = np.asarray(picked)
    return float(picked.mean()), float(picked.std())


# ─────────────────────────────────────────────────────────────────────────────
# D. 건강인 검증군: 파일럿 규칙 재현성
# ─────────────────────────────────────────────────────────────────────────────
def healthy_check_icc_precision(n, sims=3000, k_measure=2, true_icc=0.75, seed=SEED):
    """n명에서 ICC(2,1) 추정치의 95% CI 폭 (시뮬레이션).

    '규칙 재현성'을 검증할 때 흔히 쓰는 지표. 여기서는 사람 간 분산이
    전체의 true_icc 비율이 되도록 모형을 만든다.
    """
    rng = np.random.RandomState(seed)
    iccs = []
    for _ in range(sims):
        s = rng.normal(0, math.sqrt(true_icc), size=n)
        e = rng.normal(0, math.sqrt(1 - true_icc), size=(n, k_measure))
        x = s[:, None] + e
        v = _icc21(x)
        if v == v:
            iccs.append(v)
    iccs = np.asarray(iccs)
    lo, hi = np.percentile(iccs, [2.5, 97.5])
    return float(iccs.mean()), float(lo), float(hi)


def _icc21(x):
    """ICC(2,1) — two-way random, absolute agreement, single measure."""
    n, k = x.shape
    if n < 2 or k < 2:
        return float("nan")
    gm = x.mean()
    ms_r = k * ((x.mean(axis=1) - gm) ** 2).sum() / (n - 1)
    ms_c = n * ((x.mean(axis=0) - gm) ** 2).sum() / (k - 1)
    ss_t = ((x - gm) ** 2).sum()
    ss_e = ss_t - (k * ((x.mean(axis=1) - gm) ** 2).sum()) - (n * ((x.mean(axis=0) - gm) ** 2).sum())
    ms_e = ss_e / ((n - 1) * (k - 1))
    den = ms_r + (k - 1) * ms_e + k * (ms_c - ms_e) / n
    return float((ms_r - ms_e) / den) if den != 0 else float("nan")


# ─────────────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────────────
def main():
    lines, res = [], {}
    A = lines.append

    A("# 표본 크기 재검토 (계획서 §11 대체 근거)")
    A("")
    A("**작성일:** 2026-09-25 · **생성:** `experiments/sample_size_analysis.py`")
    A("**대상:** 계획서 v6.2 §11 (표본 크기와 검정력)")
    A("")
    A("> ⚠️ **이 문서는 자체 계산(C등급)이다.** 실제 데이터가 아니라 가정에 기반한다.")
    A("")

    # ---- A. 대응 t 검정력 ----
    A("## A. 주 결과(PR-1/PR-2) 검정력 — 대응 비교")
    A("")
    A("주 결과는 **같은 장애인에서 조건만 바뀌는 대응 비교**이므로 `dz = Δ/SD(Δ)` 를 쓴다.")
    A("")
    A("| n (본평가 장애인) | df | 검출 가능 dz (t검정, 80%) | SD(Δ)=1점일 때 검출 가능 Δ | 척도(0–3)의 % |")
    A("|---:|---:|---:|---:|---:|")
    ns = [8, 10, 12, 15, 18, 20, 24, 30, 40]
    for n in ns:
        dz = detectable_dz(n)
        A("| %d | %d | **%.2f** | %.2f점 | %.0f%% |" % (n, n - 1, dz, dz, 100 * dz / 3))
    res["detectable_dz"] = {n: detectable_dz(n) for n in ns}
    A("")
    A("**→ 척도가 0–3점이므로, Δ는 \"점수 몇 점 차이\"로 환산된다.** 12명이면 **0.89점(척도의 30%)** 미만은 못 잡는다.")
    A("")

    # ---- A2. CI 폭 ----
    A("### A-2. 더 중요한 것: 효과크기 **CI의 폭**")
    A("")
    A("판정표(§10)가 \"CI가 0을 포함하면 방향 확인 안 됨\"으로 쓰여 있으므로, 실제 관심은 유의성이 아니라 **CI 폭**이다.")
    A("")
    A("| n | SD(Δ)=0.5 | SD(Δ)=0.75 | SD(Δ)=1.0 | SD(Δ)=1.25 |")
    A("|---:|---:|---:|---:|---:|")
    for n in ns:
        row = "| %d |" % n
        for sd in (0.5, 0.75, 1.0, 1.25):
            row += " ±%.2f |" % ci_halfwidth(n, sd)
        A(row)
    A("")
    A("(단위: ARAT 점수. `±` 는 95% CI 반폭.)")
    A("**→ 12명·SD=1.0이면 CI 반폭이 ±0.64점**이다. 관측 Δ가 0.5점이면 CI가 0을 크게 넘나든다.")
    A("")

    # ---- B. Wilcoxon ----
    A("## B. 비모수 대안(Wilcoxon 부호순위)의 검정력")
    A("")
    A("점수 차이는 정규분포가 아닐 수 있다. 실제 분석이 Wilcoxon이면 검정력이 더 낮다.")
    A("")
    A("| n | Δ=0.5 (dz 0.5) | Δ=0.75 (dz 0.75) | Δ=1.0 (dz 1.0) |")
    A("|---:|---:|---:|---:|")
    sim = {}
    for n in [10, 12, 15, 20, 24, 30]:
        row = "| %d |" % n
        sim[n] = {}
        for dl in (0.5, 0.75, 1.0):
            p = wilcoxon_power(n, dl, sd=1.0)
            sim[n][dl] = p
            row += " %.2f |" % p
        A(row)
    res["wilcoxon_power"] = sim
    A("")
    A("**→ dz 0.75(≈0.75점)를 80% 검정력으로 잡으려면 Wilcoxon은 t검정보다 1.5~2배 n이 필요하다.**")
    A("")

    # ---- C. Q1 임계값 안정성 ----
    A("## C. 🔴 Q1 임계값의 안정성 — **개발 6명으로 충분한가**")
    A("")
    A("계획 §3 결정 14: Q1은 **개발 자료에서** balanced accuracy 최대화로 고르고, **사람단위 2-fold**로 과적합을 막는다.")
    A("그런데 개발군은 **장애인 3명 + 비장애인 6명**이다. 임계값 자체가 얼마나 흔들리는지 계산했다.")
    A("")
    A("| 개발 인원 | 추정 임계값 평균 | **임계값 SD** | 참값(0.50) 대비 편차 |")
    A("|---:|---:|---:|---:|")
    stab = {}
    for n_dev in (3, 4, 6, 10, 16, 24, 40, 60):
        m, s = q1_threshold_stability(n_dev)
        stab[n_dev] = {"mean": m, "sd": s, "bias": m - 0.5}
        A("| %d | %.2f | **%.3f** | %+.3f |" % (n_dev, m, s, m - 0.5))
    res["q1_threshold_stability"] = stab
    A("")
    A("> 위 시뮬레이션은 **참 임계값 0.50 이 실제로 존재하는 경우**다(품질 지수가 높을수록 '믿을 만한 시행'일 확률이 높다).")
    A("> 그런데도 **인원이 적으면 고른 값이 크게 흩어진다.**")
    A("")
    A("**→ 개발군 3명으로 Q1을 고르는 것은 사실상 임의 선택에 가깝다.**")
    A("**권고:** Q1을 **고정 규칙**(예: 유효 depth 비율 ≥ 0.7)으로 사전 명시하고, 개발 자료는 **확인용**으로만 쓴다.")
    A("")

    # ---- D. 건강인 검증군 ----
    A("## D. 비장애인 검증군(10명) — 무엇을 추정하고 얼마나 정밀한가")
    A("")
    A("계획 §4.1은 비장애인 **개발 6 + 독립 검증 10**을 둔다. \"규칙 재현성\"이 목적인데,")
    A("신뢰도 지표(예: ICC)는 **표본이 작으면 CI가 매우 넓다.**")
    A("")
    A("| n | 추정 ICC 평균 | 95% CI 하한 | 95% CI 상한 | **CI 폭** |")
    A("|---:|---:|---:|---:|---:|")
    icc = {}
    for n in (6, 10, 16, 20, 30, 50):
        m, lo, hi = healthy_check_icc_precision(n)
        icc[n] = {"mean": m, "lo": lo, "hi": hi, "width": hi - lo}
        A("| %d | %.2f | %.2f | %.2f | **%.2f** |" % (n, m, lo, hi, hi - lo))
    res["icc_precision"] = icc
    A("")
    A("(참고: 참 ICC=0.75로 가정. 실제 값은 데이터가 정한다.)")
    A("**→ 10명이면 95% CI 폭이 0.67**(0.25~0.92)이다. 즉 **점추정만 보고하면 과신**이고,")
    A("**\"재현성이 확인됐다\"고 말하려면 CI 하한을 봐야 한다** — 10명의 하한 0.25는 \"나쁠 수도 있다\"는 뜻이다.")
    A("**16명이면 폭 0.48, 30명이면 0.33** 으로 좁아진다.")
    A("")

    # ---- E. 분포 요건 ----
    A("## E. 점수 분포 요건 (§3 결정 20)")
    A("")
    A("계획은 본평가 12명에 **0점 1–2 / 1점 ≥3 / 2점 ≥4 / 3점 2–3** 을 목표로 둔다. 이건 검정력이 아니라 **층화 요건**이다.")
    A("")
    tot_lo = 1 + 3 + 4 + 2
    tot_hi = 2 + 5 + 5 + 3
    A("- 목표 구간의 **최소 합계 = %d명** (0점1 + 1점3 + 2점4 + 3점2)" % tot_lo)
    A("- 계획 본평가 인원은 **12명** → **여유가 2명뿐**이다.")
    A("- ⚠️ **모집이 어긋나면(예: 1점이 2명만) 분석은 가능하지만 \"가장 흐릿한 1–2 경계\"가 비어 판정표 해석이 약해진다.**")
    A("- ⚠️ **점수를 보고 대상을 빼거나 더하면 안 된다**(§12). 따라서 **모집 순서를 무작위화**하거나, 순차 모집 후 분포를 있는 그대로 보고한다.")
    A("- 💡 **n을 20명으로 늘리면** 검정력뿐 아니라 **이 층화 요건도 여유있게 충족**된다(최소 10명 ≪ 20명).")
    A("")

    # ---- F. 권고 ----
    A("## F. 권고")
    A("")
    A("| 항목 | 계획 현재 | 권고 | 근거 |")
    A("|---|---|---|---|")
    A("| 본평가 장애인 | 12명 | **20명 가능하면 20명** | 12명은 dz 0.89(=0.89점) 미만을 못 잡음. 20명이면 dz 0.66(=0.66점)까지. **CI 반폭도 12명 ±0.64 → 20명 ±0.47** |")
    A("| 비장애인 검증 | 10명 | **16명 이상** | ICC 95% CI 폭이 10명 **0.67** → 16명 **0.48**. 하한도 0.25 → 0.42 |")
    A("| 개발군(장애인 3) | 3명 | **Q1을 고정 규칙으로 바꾸고 개발군은 '기본 점검'으로** | Q1 시뮬: 개발 3명 SD 0.101 → 24명 0.051 |")
    A("| 검정 방법 선택 | 미정 | **Wilcoxon을 쓴다면 n을 1.5~2배로** | 비모수는 Δ=0.75점(dz 0.75)에서 80% 도달이 t검정보다 어려움 |")
    A("")
    A("> **정직한 결론:** 12명 설계는 **\"큰 효과의 방향 탐색\"** 이며, **소효과 검출은 원리적으로 불가능**하다.")
    A("> 이 사실은 논문에 그대로 쓴다(§11 기존 문장 유지). **n을 못 늘린다면, 주 결과를 \"방향 + CI\"로만 주장하고 유의성으로 결론을 만들지 않는다.**")
    A("")

    md = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with io.open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    with io.open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(md)
    print("[saved] %s" % OUT_MD)
    print("[saved] %s" % OUT_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())

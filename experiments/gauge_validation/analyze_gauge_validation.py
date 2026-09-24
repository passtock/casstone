# -*- coding: utf-8 -*-
"""
정적 치구 검증 분석기 (v6 계획 §7-1)
====================================

측정 시트(CSV)를 읽어 v5 §6.1이 요구한 지표를 계산한다:
  bias, MAE, RMSE, 절대오차 P95, 무효율, Bland-Altman LoA

추가로 v6 §0-3 D3의 "10% 오염 기준"을 자동 판정한다:
  각 치구 거리에서 P95 절대오차가 그 거리의 10% 이내인가?

사용법:
  python experiments/gauge_validation/analyze_gauge_validation.py                 # DEMO 합성 분석
  python experiments/gauge_validation/analyze_gauge_validation.py <sheet.csv>     # 실제 시트 분석
  python experiments/gauge_validation/analyze_gauge_validation.py --selftest      # 오라클 검증

⚠️ DEMO 합성 파일의 결과는 우리 장비 성능이 아니다. 실측 시트를 넣어야 실제 값이 나온다.
"""

import csv
import io
import math
import os
import statistics
import sys

# Windows 콘솔(cp949)에서 이모지·한글 출력 시 죽지 않도록 UTF-8로 재설정
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")

ACCEPT_FRAC = 0.10   # D3 규칙: P95 절대오차가 참값의 10%를 넘으면 "오염" 라벨


# ---------------------------------------------------------------------------
# 통계 유틸
# ---------------------------------------------------------------------------
def p95(xs):
    if not xs:
        return float("nan")
    s = sorted(xs)
    k = 0.95 * (len(s) - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def stats(diffs):
    """diffs = measured - true (mm)"""
    n = len(diffs)
    if n == 0:
        return None
    bias = statistics.fmean(diffs)
    sd = statistics.stdev(diffs) if n > 1 else 0.0
    mae = statistics.fmean(abs(d) for d in diffs)
    rmse = math.sqrt(statistics.fmean(d * d for d in diffs))
    p95abs = p95([abs(d) for d in diffs])
    return {
        "n": n,
        "bias": bias,
        "sd": sd,
        "mae": mae,
        "rmse": rmse,
        "p95abs": p95abs,
        "loa_lo": bias - 1.96 * sd,
        "loa_hi": bias + 1.96 * sd,
    }


def fmt_row(label, s, true_mm=None):
    if s is None:
        return "| %s | 0 | — | — | — | — | — | — | — |" % label
    verdict = "—"
    if true_mm:
        verdict = "✅ 통과" if s["p95abs"] <= ACCEPT_FRAC * true_mm else "❌ 초과"
    return ("| %s | %d | %+.2f | %.2f | %.2f | %.2f | %.2f | [%.2f, %.2f] | %s |"
            % (label, s["n"], s["bias"], s["sd"], s["mae"], s["rmse"],
               s["p95abs"], s["loa_lo"], s["loa_hi"], verdict))


# ---------------------------------------------------------------------------
# 시트 로딩
# ---------------------------------------------------------------------------
def load(path):
    recs = []
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("measured_mm", "").strip() == "":
                row["_valid"] = False
                row["_measured"] = None
            else:
                try:
                    row["_measured"] = float(row["measured_mm"])
                    row["_valid"] = str(row.get("valid_flag", "1")).strip() not in ("0", "false", "False", "")
                except ValueError:
                    row["_measured"] = None
                    row["_valid"] = False
            row["_true"] = float(row["true_distance_mm"])
            recs.append(row)
    return recs


def analyze(recs):
    total = len(recs)
    valid = [r for r in recs if r["_valid"] and r["_measured"] is not None]
    invalid = total - len(valid)
    diffs = [r["_measured"] - r["_true"] for r in valid]

    out = []
    out.append("# 정적 치구 검증 결과")
    out.append("")
    out.append("- 총 기록 %d, 유효 %d, 무효 %d, **무효율 %.1f%%**"
               % (total, len(valid), invalid, 100.0 * invalid / total if total else 0.0))
    out.append("- 판정 규칙: **P95 절대오차 ≤ 참값의 %.0f%%** (v6 §0-3 D3의 오염 기준)"
               % (100 * ACCEPT_FRAC))
    out.append("")
    out.append("## 전체")
    out.append("")
    out.append("| 구분 | n | bias(mm) | SD(mm) | MAE(mm) | RMSE(mm) | \\|err\\| P95(mm) | 95% LoA(mm) | 판정 |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    overall = stats(diffs)
    out.append(fmt_row("전체", overall))
    out.append("")

    def group(key):
        buckets = {}
        for r in valid:
            buckets.setdefault(r[key], []).append(r["_measured"] - r["_true"])
        return buckets

    out.append("## 치구 크기별 (핵심 판정)")
    out.append("")
    out.append("| 치구(mm) | n | bias(mm) | SD(mm) | MAE(mm) | RMSE(mm) | \\|err\\| P95(mm) | 95% LoA(mm) | 판정 |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    per_dist = group("true_distance_mm")
    for d in sorted(per_dist, key=lambda x: float(x)):
        out.append(fmt_row("%s mm" % d, stats(per_dist[d]), float(d)))
    out.append("")

    out.append("## 작업영역 거리별 (깊이 오차의 거리 의존성)")
    out.append("")
    out.append("| zone | n | bias(mm) | SD(mm) | MAE(mm) | RMSE(mm) | \\|err\\| P95(mm) | 95% LoA(mm) | 판정 |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    for z in sorted(group("zone")):
        out.append(fmt_row(z, stats(group("zone")[z])))
    out.append("")

    out.append("## 방향별 (Scano 2020의 구역별 신뢰도 차이 검사)")
    out.append("")
    out.append("| direction | n | bias(mm) | SD(mm) | MAE(mm) | RMSE(mm) | \\|err\\| P95(mm) | 95% LoA(mm) | 판정 |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    per_dir = group("direction")
    for dd in sorted(per_dir):
        out.append(fmt_row(dd, stats(per_dir[dd])))
    out.append("")

    # 방향 비대칭
    dir_p95 = {k: stats(v)["p95abs"] for k, v in per_dir.items() if v}
    if len(dir_p95) >= 2:
        worst = max(dir_p95, key=dir_p95.get)
        best = min(dir_p95, key=dir_p95.get)
        ratio = dir_p95[worst] / dir_p95[best] if dir_p95[best] > 0 else float("inf")
        out.append("**방향 비대칭:** 최악 `%s` %.2f mm vs 최선 `%s` %.2f mm → 비 %.2f×"
                   % (worst, dir_p95[worst], best, dir_p95[best], ratio))
        if ratio >= 2.0:
            out.append("→ ⚠️ **2배 이상 차이.** Scano 2020처럼 방향을 나눠 보고하고, "
                       "나쁜 방향을 고정 프리셋에서 회피하거나 별도 품질 규칙을 둔다.")
        out.append("")

    # 10% 초과 치구 목록
    over = [d for d in per_dist if stats(per_dist[d])["p95abs"] > ACCEPT_FRAC * float(d)]
    out.append("## 결론 요약")
    out.append("")
    if over:
        out.append("- ⚠️ **10%% 기준 초과 치구: %s mm** → 해당 규모에서 K1은 이미 오염 라벨. "
                   "구슬 과제(직경 15 mm)와 겹치는 규모인지 반드시 확인." % ", ".join(sorted(over, key=float)))
    else:
        out.append("- ✅ 모든 치구 크기에서 P95 절대오차가 참값의 10% 이내.")
    out.append("- 이 결과로 **u_K1 = 위 P95 절대오차(치구별)** 를 정의한다(§0-3 D3). "
               "20 mm 치구의 값이 구슬 과제 K1에 가장 가까운 대리값이다.")
    out.append("- ⚠️ 정적 치구만 통과했다고 **가린 손끝의 3D 정확도가 검증됐다고 쓰지 않는다**(v5 §6.1).")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 오라클 자체 검증
# ---------------------------------------------------------------------------
def selftest():
    print("=== 오라클 검증 (알려진 값으로 계산기 검증) ===")
    ok = True

    # T1: 상수 편향 +3.0
    s = stats([3.0, 3.0, 3.0, 3.0])
    checks = [("bias=3.0", s["bias"] == 3.0), ("MAE=3.0", s["mae"] == 3.0),
              ("RMSE=3.0", s["rmse"] == 3.0), ("P95=3.0", abs(s["p95abs"] - 3.0) < 1e-9)]
    for name, cond in checks:
        print("  T1 %-12s %s" % (name, "PASS" if cond else "FAIL"))
        ok &= cond

    # T2: 부호 섞임 -> bias 0, MAE 1
    s = stats([1.0, -1.0, 1.0, -1.0])
    checks = [("bias=0", abs(s["bias"]) < 1e-12), ("MAE=1", abs(s["mae"] - 1.0) < 1e-12),
              ("RMSE=1", abs(s["rmse"] - 1.0) < 1e-12)]
    for name, cond in checks:
        print("  T2 %-12s %s" % (name, "PASS" if cond else "FAIL"))
        ok &= cond

    # T3: P95 보간 (1..10 -> 9.55)
    v = p95([float(i) for i in range(1, 11)])
    cond = abs(v - 9.55) < 1e-9
    print("  T3 P95(1..10)=9.55  %s (got %.4f)" % ("PASS" if cond else "FAIL", v))
    ok &= cond

    # T4: 무효 처리 (10행 중 2행 무효 -> 무효율 20%)
    recs = []
    for i in range(10):
        recs.append({"_valid": i >= 2, "_measured": (40.0 + 1.0) if i >= 2 else None,
                     "_true": 40.0, "true_distance_mm": "40", "zone": "mid", "direction": "frontal"})
    rep = analyze(recs)
    cond = "무효율 20.0%" in rep
    print("  T4 무효율 20.0%%       %s" % ("PASS" if cond else "FAIL"))
    ok &= cond

    # T5: 판정 임계 (P95 4.0mm vs 40mm 참값 -> 10% 이하 = 통과)
    s = stats([4.0, 4.0, 4.0, 4.0])
    cond = (s["p95abs"] <= 0.10 * 40.0)
    print("  T5 40mm에서 P95 4.0 -> 통과  %s" % ("PASS" if cond else "FAIL"))
    ok &= cond
    s2 = stats([4.5, 4.5, 4.5, 4.5])
    cond = (s2["p95abs"] > 0.10 * 40.0)
    print("  T6 40mm에서 P95 4.5 -> 초과  %s" % ("PASS" if cond else "FAIL"))
    ok &= cond

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok else "FAIL 있음"))
    return ok


# ---------------------------------------------------------------------------
def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    path = None
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            path = a
    if path is None:
        path = os.path.join(HERE, "gauge_sheet_DEMO_synthetic.csv")
        print("[info] 인자 없음 → DEMO 합성 파일 분석: %s" % os.path.basename(path))
        print("[info] ⚠️ 합성 결과다. 우리 장비 성능이 아니다.")
        print("")

    recs = load(path)
    report = analyze(recs)
    print(report)

    os.makedirs(RESULTS, exist_ok=True)
    tag = "DEMO_synthetic" if "DEMO" in os.path.basename(path) else os.path.basename(path).replace(".csv", "")
    out_path = os.path.join(RESULTS, "gauge_validation_report_%s.txt" % tag)
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("")
    print("[saved] %s" % out_path)


if __name__ == "__main__":
    main()

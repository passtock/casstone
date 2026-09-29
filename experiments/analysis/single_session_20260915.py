# -*- coding: utf-8 -*-
"""단일 세션 정밀 검증 — 20260915_비장애인_test_26세_남 (Task1 맨손 쥐기/펴기, 8시행 × 양손).

계획서 §4.6이 "장비 없이 쓸 수 있는 일관성 점검"으로 든 것을 이 데이터로 직접 수행한다:
  ② 좌우 대칭 점검        — 양손 값이 크게 달라선 안 된다
  ③ 시행 간 변동 점검     — Frykberg 2021 수준인가
  + 시행 순서 추세        — §9 분석 계획이 요구
  + 누적 안정화 시행 수   — §9 "지표별 누적 ICC ≥0.75 도달 시행 수를 직접 계산"
  + Q 규칙 실측 진단      — Samples / Paired_Samples / depth 유효율

출력: experiments/results/single_session_20260915.txt
"""
import csv, glob, io, math, os, sys, statistics as st
from collections import defaultdict

SRC = "capstone/호진파일/outputs/데이터_저장/20260915_비장애인_test_26세_남"
OUT = "experiments/results/single_session_20260915.txt"

KEY = ["SPARC", "TAM_total_deg", "Index_ROM_deg", "Index_ROM_3D_deg",
       "ROM_Index_MCP_deg", "ROM_Index_PIP_deg", "ROM_Middle_MCP_deg",
       "MP_MGA_raw_mm", "MGA_cm", "MGA_mm_3D", "MGA_mm_3D_cal",
       "Flex_Speed_deg_s", "Ext_Speed_deg_s", "Thumb_CMC_ROM_deg",
       "Samples", "RS_Valid_Samples", "Paired_Samples", "Duration_s"]

fd = glob.glob(os.path.join(SRC, "*_trials_summary.csv"))[0]
rows = [r for r in csv.DictReader(open(fd, encoding="utf-8-sig")) if r["Task"] == "Task 1"]


def f(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except Exception:
        return None


def by(col, hand):
    return [f(r.get(col)) for r in rows if r["Hand"] == hand]


def stats(v):
    v = [x for x in v if x is not None]
    if len(v) < 2: return None
    m = st.mean(v); sd = st.stdev(v)
    return dict(n=len(v), mean=m, sd=sd, sem=sd,
                mdc=1.96 * math.sqrt(2) * sd,
                mdcpct=(1.96 * math.sqrt(2) * sd / abs(m) * 100) if abs(m) > 1e-12 else None)


def icc21(pairs):
    """ICC(2,1): 행=시행, 열=손(2). pairs=[(L,R),...]"""
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    n = len(pairs)
    if n < 3: return None
    k = 2
    grand = st.mean([x for p in pairs for x in p])
    rowm = [st.mean(p) for p in pairs]
    colm = [st.mean([p[j] for p in pairs]) for j in range(k)]
    ssr = k * sum((r - grand) ** 2 for r in rowm)
    ssc = n * sum((c - grand) ** 2 for c in colm)
    sst = sum((x - grand) ** 2 for p in pairs for x in p)
    sse = sst - ssr - ssc
    msr = ssr / (n - 1); msc = ssc / (k - 1); mse = sse / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    if den <= 0: return None
    return (msr - mse) / den


def spearman(x, y):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v)
        for pos, i in enumerate(s): r[i] = pos + 1
        return r
    rx, ry = rank(x), rank(y)
    n = len(x); mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


lines = []
def out(s=""): lines.append(s)

out("=" * 96)
out("단일 세션 정밀 검증 — 20260915_비장애인 26세 남 · Task1 맨손 쥐기/펴기 · 8시행 × 양손")
out("=" * 96)
out(f"원자료: {fd}")
out(f"행 수: {len(rows)} (Right {sum(1 for r in rows if r['Hand']=='Right')} · Left {sum(1 for r in rows if r['Hand']=='Left')})")
out("Trial_Mode: " + ",".join(sorted({r.get("Trial_Mode", "") for r in rows})) +
    "  ·  Interrupted: " + ",".join(sorted({str(r.get('Interrupted', '')) for r in rows})))
out()

# ── A. 지표별 기술통계 + MDC
out("### A. 지표별 기술통계 · MDC95 (양손 통합) ###")
out(f"{'지표':<22}{'n':>3}{'결측':>5}{'mean':>13}{'SD':>12}{'MDC95':>12}{'MDC/mean%':>11}{'물리위반%':>10}")
LIM = {"SPARC": ("sparc",), "speed": ("Flex_Speed_deg_s", "Ext_Speed_deg_s")}
for col in KEY:
    L = by(col, "Left"); R = by(col, "Right"); allv = L + R
    nv = [x for x in allv if x is not None]
    miss = len(allv) - len(nv)
    s = stats(allv)
    viol = 0
    if col == "SPARC": viol = sum(1 for x in nv if x > 0)
    elif col in ("Flex_Speed_deg_s", "Ext_Speed_deg_s"): viol = sum(1 for x in nv if not (0 <= x <= 2000))
    elif col == "MGA_mm_3D_cal": pass
    vp = (viol / len(nv) * 100) if nv else 0
    if s:
        mp = s["mdcpct"]; mp_s = ("%.1f" % mp) if mp is not None else "-"
        out("%-22s%3d%5d%13.4g%12.4g%12.4g%11s%10.0f"
            % (col, s["n"], miss, s["mean"], s["sd"], s["mdc"], mp_s, vp))
    else:
        out(f"{col:<22}{0:>3}{miss:>5}{'-':>13}{'-':>12}{'-':>12}{'-':>11}{'-':>10}")
out()

# ── B. 좌우 대칭 점검 (계획 §4.6 ②)
out("### B. 좌우 대칭 점검 (계획 §4.6-②) — 양손 ICC(2,1) + 대응차 ###")
out(f"{'지표':<22}{'Right mean':>12}{'Left mean':>12}{'차이%':>8}{'ICC(2,1)':>10}  판정")
for col in KEY:
    L, R = by(col, "Left"), by(col, "Right")
    pairs = list(zip(R, L))  # 같은 시행 index로 짝
    ic = icc21(pairs)
    Rs = stats(R); Ls = stats(L)
    if not (Rs and Ls): continue
    diffp = abs(Rs["mean"] - Ls["mean"]) / ((abs(Rs["mean"]) + abs(Ls["mean"])) / 2) * 100
    tag = ""
    if ic is not None:
        tag = "양호" if ic >= 0.75 else ("보통" if ic >= 0.5 else "낮음")
    ic_s = ("%.3f" % ic) if ic is not None else "-"
    out("%-22s%12.4g%12.4g%8.1f%10s  %s" % (col, Rs["mean"], Ls["mean"], diffp, ic_s, tag))
out()

# ── C. 시행 순서 추세 (계획 §9)
out("### C. 시행 순서 추세 (Spearman rho vs 시행번호) ###")
out(f"{'지표':<22}{'Right rho':>11}{'Left rho':>11}  해석(|rho|>0.7 = 추세 있음)")
for col in KEY:
    res = []
    for h in ("Right", "Left"):
        v = by(col, h)
        ok = [(i, x) for i, x in enumerate(v) if x is not None]
        res.append(spearman([i for i, _ in ok], [x for _, x in ok]) if len(ok) >= 4 else None)
    tag = ""
    if all(r is not None for r in res):
        m = max(abs(res[0]), abs(res[1]))
        tag = "추세 주의" if m > 0.7 else "추세 없음"
    r0 = ("%+.3f" % res[0]) if res[0] is not None else "-"
    r1 = ("%+.3f" % res[1]) if res[1] is not None else "-"
    out("%-22s%11s%11s  %s" % (col, r0, r1, tag))
out()

# ── D. 누적 안정화 — 몇 시행이면 안정하는가 (계획 §9)
out("### D. 누적 안정화: 첫 k시행 누적평균이 전체평균 ±5% 이내가 되는 최소 k ###")
out(f"{'지표':<22}{'Right k':>9}{'Left k':>9}  비고")
for col in KEY:
    ks = []
    for h in ("Right", "Left"):
        v = [x for x in by(col, h) if x is not None]
        if len(v) < 4: ks.append(None); continue
        gm = st.mean(v); k = None
        for j in range(2, len(v) + 1):
            if abs(st.mean(v[:j]) - gm) <= 0.05 * abs(gm):
                k = j; break
        ks.append(k)
    k0 = str(ks[0]) if ks[0] else ">%d" % len([x for x in by(col,'Right') if x is not None])
    k1 = str(ks[1]) if ks[1] else ">%d" % len([x for x in by(col,'Left') if x is not None])
    out("%-22s%9s%9s" % (col, k0, k1))
out()

# ── E. Q 규칙 실측 진단
out("### E. Q 규칙 실측 진단 (Samples / Paired_Samples / depth 유효율) ###")
out(f"{'시행':<10}{'Hand':<7}{'Samples':>9}{'RS_Valid':>10}{'Paired':>8}{'depth유효율%':>13}{'Q3(<50)':>9}")
q3_block = 0; tot = 0
for r in rows:
    S = f(r.get("Samples")); RV = f(r.get("RS_Valid_Samples")); PR = f(r.get("Paired_Samples"))
    rate = (RV / S * 100) if (S and RV is not None) else None
    blocked = (PR is not None and PR < 50)
    if blocked: q3_block += 1
    tot += 1
    out("%-10s%-7s%9s%10s%8s%13s%9s" % (r["Trial"], r["Hand"],
        ("%.0f" % S) if S else "-", ("%.0f" % RV) if RV is not None else "-",
        ("%.0f" % PR) if PR is not None else "-", ("%.0f" % rate) if rate is not None else "-",
        "보류" if blocked else "통과"))
out()
out(f"→ Q3(<50 유효쌍)로 보류되는 시행: {q3_block}/{tot}  ({q3_block/tot*100:.0f}%)")
out()

# ── 요약
out("### 요약 ###")
out("· 이 세션은 1인 · 1과제(맨손 쥐기/펴기) · 8시행 × 양손이다. 병변 대조가 아니므로 '좌우 대칭'은 파이프라인 편향 점검이다.")
out("· Trial_Mode=manual / Interrupted=1 → 시행 경계를 사람이 잘랐다. 계획서 §4.3은 '성공·접촉 순간을 사람이 골라 입력'을 금지한다.")
out("· MGA_mm_3D_cal 은 이 세션에서 전부 결측이다(코드가 쓰는 K1 대리값).")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
print("\n".join(lines)); print("\n[saved]", OUT)

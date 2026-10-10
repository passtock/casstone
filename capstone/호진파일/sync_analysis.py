"""양손 싱크로율 분석 (미러테라피: 건측 동작을 환측이 얼마나 같이 따라가는가).

입력: outputs/데이터_재분할/<세션>/*_continuous_raw_재분할.csv (Trial_reseg 구간)
신호: 손별 검지~소지 12관절 *_filt 평균을 구간 안에서 0%(쥔 상태)~100%(편 상태)로 정규화

trial별 지표
  Open_Delay_s  : 펴기 지연 = 환측이 50% 펴진 시각 - 건측이 50% 펴진 시각 (+ = 환측이 늦음)
  Close_Delay_s : 쥐기 지연 = 환측이 50% 아래로 내려간 시각 - 건측의 같은 시각
  Mismatch_s    : 평균 어긋남 시간 = (|펴기 지연| + |쥐기 지연|) / 2  (+/- 가 상쇄되지 않음)
  Sync_pct      : 동작 구간 싱크로율 = 펴는 중/쥐는 중 구간만으로 계산한 두 곡선의 상관 x 100
                  (다 편 채 유지·쉬는 구간을 빼서 값이 부풀려지지 않게 함)
  Amp_pct       : 환측 움직임 크기 = 환측 진폭 / 건측 진폭 x 100

구간: 재분할 구간을 이웃 trial과 겹치지 않는 범위에서 넓히고, 손마다 '50% 이상 펴진 구간'을 찾는다.
      건측은 환측 펴짐 구간과 가장 많이 겹치는 펴짐 구간을 짝으로 쓴다 (녹화 안 된 동작이 섞이지 않게).
"""
import glob
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import medfilt

matplotlib.use("Agg")
matplotlib.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 8,
                            "axes.spines.top": False, "axes.spines.right": False,
                            "axes.edgecolor": "#c3c2b7", "xtick.color": "#52514e", "ytick.color": "#52514e"})

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "outputs", "데이터_저장")
RES = os.path.join(BASE, "outputs", "데이터_재분할")
OUT = os.path.join(BASE, "outputs", "논문_figures")
FINGER_JOINTS = [f"{f}_{j}_filt" for f in ("Index", "Middle", "Ring", "Pinky") for j in ("MCP", "PIP", "DIP")]
EXT_S = 1.5        # 재분할 구간 확장 (건측 동작이 잘리지 않게)
PHASE_PAD_S = 0.2  # 동작 구간 앞뒤 여유
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e1e0d9"
PRE, POST = "#9ec5f4", "#2a78d6"
AFF_C, UNA_C = "#2a78d6", "#eb6834"
PATIENT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]


def open_runs(x):
    """x >= 0.5 인 연속 구간들 [(i0, i1)] (i1 포함)."""
    m = np.r_[False, x >= 0.5, False]
    d = np.diff(m.astype(int))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def cross_time(g, x, i, rising):
    """i 근처 50% 교차 시각 (선형 보간). rising: i-1 -> i 상승, 아니면 i -> i+1 하강."""
    j0, j1 = (i - 1, i) if rising else (i, i + 1)
    if j0 < 0 or j1 >= len(x):
        return np.nan
    return g[j0] + (0.5 - x[j0]) / (x[j1] - x[j0]) * (g[j1] - g[j0]) if x[j1] != x[j0] else g[j1]


def sync_metrics(t, a, u):
    """t: 시각, a: 환측 곡선, u: 건측 곡선 (같은 프레임, 원 단위 각도)."""
    ok = np.isfinite(a) & np.isfinite(u)
    t, a, u = t[ok], medfilt(a[ok], 5), medfilt(u[ok], 5)
    dt = float(np.median(np.diff(t)))
    g = np.arange(t[0], t[-1], dt)
    a, u = np.interp(g, t, a), np.interp(g, t, u)
    an, un = (a - a.min()) / (np.ptp(a) or 1), (u - u.min()) / (np.ptp(u) or 1)

    ra, ru = open_runs(an), open_runs(un)
    if not ra or not ru:
        return None, "펴짐 구간 없음"
    a0, a1 = max(ra, key=lambda r: r[1] - r[0])                       # 환측 주 동작
    ov = [max(0, min(a1, r[1]) - max(a0, r[0])) for r in ru]
    if max(ov) == 0:
        return None, "양손 펴짐 구간이 겹치지 않음"
    u0, u1 = ru[int(np.argmax(ov))]                                   # 짝이 되는 건측 동작
    if a0 == 0 or u0 == 0 or a1 == len(g) - 1 or u1 == len(g) - 1:
        return None, "구간 끝에서 잘림"

    ta_o, ta_c = cross_time(g, an, a0, True), cross_time(g, an, a1, False)
    tu_o, tu_c = cross_time(g, un, u0, True), cross_time(g, un, u1, False)
    r = dict(Open_Delay_s=ta_o - tu_o, Close_Delay_s=ta_c - tu_c)
    r["Mismatch_s"] = (abs(r["Open_Delay_s"]) + abs(r["Close_Delay_s"])) / 2

    # 동작 구간: 펴는 중(두 손 중 먼저 시작~나중 끝) + 쥐는 중
    def phase(x, i_cross, rising):
        lo = np.flatnonzero(x <= 0.1)
        hi = np.flatnonzero(x >= 0.9)
        if rising:
            s = lo[lo < i_cross][-1] if np.any(lo < i_cross) else 0
            e = hi[hi > i_cross][0] if np.any(hi > i_cross) else i_cross
        else:
            s = hi[hi < i_cross][-1] if np.any(hi < i_cross) else 0
            e = lo[lo > i_cross][0] if np.any(lo > i_cross) else i_cross
        return g[s], g[e]

    mask = np.zeros(len(g), bool)
    for rising, ia, iu in ((True, a0, u0), (False, a1, u1)):
        (s1, e1), (s2, e2) = phase(an, ia, rising), phase(un, iu, rising)
        mask |= (g >= min(s1, s2) - PHASE_PAD_S) & (g <= max(e1, e2) + PHASE_PAD_S)
    r["Sync_pct"] = float(np.corrcoef(an[mask], un[mask])[0, 1] * 100)
    r["Amp_pct"] = float(np.ptp(a) / np.ptp(u) * 100) if np.ptp(u) else np.nan
    return r, (g - g[0], an, un)


def load():
    rows, curves = [], {}
    for d in sorted(glob.glob(os.path.join(RES, "*"))):
        if not os.path.isdir(d):
            continue
        src = [s for s in glob.glob(os.path.join(SRC, "*")) if os.path.basename(s).startswith(os.path.basename(d))][0]
        meta = json.load(open(glob.glob(os.path.join(src, "*metadata.json"))[0], encoding="utf-8"))
        name = meta["subject"]["name"]
        patient = name.replace("(애프터)", "").replace("애프터", "")
        phase = "post" if "애프터" in name else "pre"
        aff = "Left" if "좌" in meta["subject"]["affected_side"] else "Right"
        una = "Right" if aff == "Left" else "Left"
        df = pd.read_csv(glob.glob(os.path.join(d, "*_continuous_raw_재분할.csv"))[0], encoding="utf-8-sig")
        df["f"] = df[FINGER_JOINTS].mean(axis=1)
        sp = df[df.Trial_reseg != "Rest"].groupby("Trial_reseg").time_s.agg(["min", "max"]).sort_values("min")
        b = sp.values.tolist()
        for k, (tr, (t0, t1)) in enumerate(zip(sp.index, b)):
            lo = max(t0 - EXT_S, (b[k - 1][1] + t0) / 2 if k > 0 else -np.inf)
            hi = min(t1 + EXT_S, (t1 + b[k + 1][0]) / 2 if k + 1 < len(b) else np.inf)
            w = df[(df.time_s >= lo) & (df.time_s <= hi)].pivot_table(index="time_s", columns="hand", values="f").dropna()
            m, cv = sync_metrics(w.index.values, w[aff].values, w[una].values)
            row = dict(환자=patient, phase=phase, FMA=meta["subject"]["fma_score"], Trial=tr, 사용=m is not None,
                       제외사유="" if m is not None else cv)
            if m is not None:
                row.update(m)
                curves.setdefault((patient, phase), []).append((tr, m, cv))
            rows.append(row)
    return pd.DataFrame(rows), curves


EASY = [  # (열, 이름, 단위, 해석, 좋아지는 판정)
    ("Sync_pct", "동작 구간 싱크로율", "%", "높을수록 양손이 같이 움직임", lambda a, b: b > a),
    ("Mismatch_s", "평균 어긋남 시간", "초", "낮을수록 양손 타이밍이 맞음 (0초 = 동시)", lambda a, b: b < a),
    ("Open_Delay_s", "펴기 지연", "초", "+ = 환측이 늦게 펴짐", lambda a, b: abs(b) < abs(a)),
    ("Close_Delay_s", "쥐기 지연", "초", "+ = 환측이 늦게 쥠", lambda a, b: abs(b) < abs(a)),
    ("Amp_pct", "환측 움직임 크기", "건측 대비 %", "100%에 가까울수록 양손 크기 같음", lambda a, b: abs(b - 100) < abs(a - 100)),
]


def p_mark(p):
    return "**" if p < 0.01 else "*" if p < 0.05 else ""


def main():
    T, curves = load()
    T.to_csv(os.path.join(RES, "싱크로율_trial별.csv"), index=False, encoding="utf-8-sig")
    ex = T[~T.사용]
    if len(ex):
        print("== 제외된 trial\n" + ex[["환자", "phase", "Trial", "제외사유"]].to_string(index=False))
    U = T[T.사용]
    patients = list(dict.fromkeys(T.환자))
    fma = {p: int(T[T.환자 == p].FMA.iloc[0]) for p in patients}

    stat, comp = {}, []
    for col, name, unit, hint, better in EASY:
        for i, p in enumerate(patients):
            a = U[(U.환자 == p) & (U.phase == "pre")][col]
            b = U[(U.환자 == p) & (U.phase == "post")][col]
            pv = stats.ttest_ind(b, a, equal_var=False).pvalue
            good = better(a.mean(), b.mean())
            stat[(col, p)] = dict(pre=a.mean(), post=b.mean(), pre_sd=a.std(), post_sd=b.std(),
                                  n_pre=len(a), n_post=len(b), p=pv, good=good)
            comp.append(dict(환자=f"P{i + 1}", 이름=p, FMA=fma[p], 지표=name, 단위=unit, n_pre=len(a), n_post=len(b),
                             pre_mean=a.mean(), pre_sd=a.std(), post_mean=b.mean(), post_sd=b.std(), p=pv,
                             판정=("좋아짐" if good else "나빠짐") + p_mark(pv)))
    C = pd.DataFrame(comp)
    C.round(4).to_csv(os.path.join(RES, "싱크로율_전후비교.csv"), index=False, encoding="utf-8-sig")
    show = C.assign(값=C.apply(lambda r: f"{r.pre_mean:6.2f} → {r.post_mean:6.2f} {r.판정:5s} p={r.p:.3f}", axis=1))
    print(show.pivot_table(index="지표", columns="환자", values="값", aggfunc="first")
          .reindex([e[1] for e in EASY]).to_string())

    table(stat, patients, fma, U)
    fig_summary(stat, patients, fma)
    fig_example(curves, patients, U)
    fig_all(curves, patients, U)


def table(stat, patients, fma, U):
    from make_paper_figures import draw_table
    keys = ["Sync_pct", "Mismatch_s", "Open_Delay_s", "Close_Delay_s"]
    head = ["환자"] + [f"{e[1]} ({e[2]})" for e in EASY if e[0] in keys]
    rows = [head]
    for i, p in enumerate(patients):
        row = [f"P{i + 1} (FMA {fma[p]})"]
        for k in keys:
            r = stat[(k, p)]
            fmt = "{:.0f}" if k == "Sync_pct" else "{:+.2f}" if "Delay" in k else "{:.2f}"
            same = fmt.format(r["pre"]) == fmt.format(r["post"])
            mark = "–" if same else ("↑" if r["good"] else "↓") + p_mark(r["p"])
            row.append(f"{fmt.format(r['pre'])} → {fmt.format(r['post'])}  {mark}")
        rows.append(row)
    n = "/".join(f"{stat[('Sync_pct', p)]['n_pre']}·{stat[('Sync_pct', p)]['n_post']}" for p in patients)
    draw_table(rows, "표 5. 재활 전후 양손 싱크로율",
               os.path.join(OUT, "표5_양손싱크로율.png"), col_w=[1.15, 1.55, 1.55, 1.4, 1.4],
               note=f"재활 전 → 후 (trial 평균, n 전·후 = {n}). ↑ 좋아짐, ↓ 나빠짐, – 변화 없음, *p<0.05, **p<0.01. "
                    "지연: 양손이 50% 펴짐/쥠에 도달한 시각 차 (+ = 환측이 늦음). 어긋남 = (|펴기 지연|+|쥐기 지연|)/2.")


def fig_summary(stat, patients, fma):
    keys = ["Sync_pct", "Mismatch_s", "Amp_pct"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7))
    w = 0.36
    for ax, k in zip(axes, keys):
        col, name, unit, hint, _ = [e for e in EASY if e[0] == k][0]
        fmt = "{:.2f}" if k == "Mismatch_s" else "{:.0f}"
        top = 0
        for i, p in enumerate(patients):
            r = stat[(k, p)]
            for dx, key, c in ((-w / 2 - 0.01, "pre", PRE), (w / 2 + 0.01, "post", POST)):
                ax.bar(i + dx, r[key], w, color=c, zorder=2)
                ax.text(i + dx, r[key], fmt.format(r[key]), ha="center", va="bottom", fontsize=6.8, color=INK)
                top = max(top, r[key])
            if r["p"] < 0.05:
                ax.text(i, max(r["pre"], r["post"]) + top * 0.1, p_mark(r["p"]), ha="center", fontsize=9, color=INK)
        if k in ("Sync_pct", "Amp_pct"):
            ax.axhline(100, color="#898781", lw=0.8, zorder=1)
        ax.set_ylim(0, top * 1.28)
        ax.set_xticks(range(len(patients)), [f"P{i + 1}\nFMA {fma[p]}" for i, p in enumerate(patients)], fontsize=7)
        ax.set_title(f"{name} ({unit})", fontsize=8.5, color=INK)
        ax.text(0.5, -0.3, hint, transform=ax.transAxes, ha="center", fontsize=6.3, color=INK2)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", labelsize=7)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=PRE, label="재활 전"),
                        plt.Rectangle((0, 0), 1, 1, color=POST, label="재활 후")],
               frameon=False, fontsize=7.5, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"그림11_양손싱크로율_요약.{ext}"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def representative(curves, p, ph, U):
    """예시 trial: 대비가 가장 뚜렷하게 - 재활 전은 어긋남 최대, 재활 후는 어긋남 최소."""
    pick = max if ph == "pre" else min
    return pick(curves[(p, ph)], key=lambda c: c[1]["Mismatch_s"])


def draw_curve(ax, tr, m, cv, title):
    t, an, un = cv
    ax.fill_between(t, an * 100, un * 100, color="#d03b3b", alpha=0.13, lw=0, label="양손 차이")
    ax.plot(t, un * 100, color=UNA_C, lw=1.8, label="건측")
    ax.plot(t, an * 100, color=AFF_C, lw=1.8, label="환측")
    ax.axhline(50, color="#c3c2b7", lw=0.6, zorder=0)
    ax.set_title(f"{title}\n펴기 {m['Open_Delay_s']:+.2f}초 · 쥐기 {m['Close_Delay_s']:+.2f}초 · 어긋남 {m['Mismatch_s']:.2f}초",
                 fontsize=7.8, color=INK)
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=7)


def fig_example(curves, patients, U):
    j = len(patients) - 1
    p = patients[j]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), sharey=True)
    for ax, ph, title in zip(axes, ("pre", "post"), ("재활 전", "재활 후")):
        tr, m, cv = representative(curves, p, ph, U)
        draw_curve(ax, tr, m, cv, f"P{j + 1} {title} ({tr.replace('Trial_', 'T')})")
        ax.set_xlabel("시간 (초)", fontsize=8)
    axes[0].set_ylabel("손 펴짐 정도 (%)", fontsize=8)
    axes[0].legend(frameon=False, fontsize=7, loc="lower center")
    fig.text(0.5, -0.03, "0% = 쥔 상태, 100% = 다 편 상태. 지연은 50% 선을 지나는 시각 차 (+ = 환측이 늦음). "
             "예시 trial: 재활 전은 어긋남이 가장 큰 trial, 재활 후는 가장 작은 trial.", ha="center", fontsize=6.6, color=INK2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"그림12_양손곡선_P3전후.{ext}"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_all(curves, patients, U):
    fig, axes = plt.subplots(2, len(patients), figsize=(7.6, 4.4), sharey=True)
    for j, p in enumerate(patients):
        for i, (ph, title) in enumerate((("pre", "재활 전"), ("post", "재활 후"))):
            tr, m, cv = representative(curves, p, ph, U)
            draw_curve(axes[i, j], tr, m, cv, f"P{j + 1} {title}")
    for ax in axes[1]:
        ax.set_xlabel("시간 (초)", fontsize=7.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("손 펴짐 정도 (%)", fontsize=7.5)
    axes[0, 0].legend(frameon=False, fontsize=6.5, loc="lower center")
    fig.text(0.5, -0.01, "예시 trial: 재활 전은 어긋남이 가장 큰 trial, 재활 후는 가장 작은 trial.",
             ha="center", fontsize=6.6, color=INK2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"부록_양손곡선_전체환자.{ext}"), dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()

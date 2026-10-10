"""논문(kat259D) 결과표/그림 생성.

입력: outputs/데이터_저장/<세션 폴더>/*metadata.json
      outputs/데이터_재분할/<세션 폴더>/*_continuous_raw_재분할.csv (resegment_trials.py 결과, Trial_reseg 사용)
출력: outputs/논문_figures/
최대 신전 각도 = 환측 손, Grasping 구간(Trial != Rest)에서 trial별 각 관절 *_filt 최대값의 평균.
(full_3patients_analysis.json 과 동일한 정의, 값 일치 확인됨)
"""
import glob
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "font.size": 9,
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": "#0b0b0b",
    "xtick.color": "#52514e",
    "ytick.color": "#52514e",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
})

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "outputs", "데이터_저장")
RESEG = os.path.join(BASE, "outputs", "데이터_재분할")
OUT = os.path.join(BASE, "outputs", "논문_figures")
os.makedirs(OUT, exist_ok=True)

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
PRE, POST = "#9ec5f4", "#2a78d6"            # 재활 전(연한 파랑) / 재활 후(파랑)
PATIENT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]  # 카테고리 1~3 슬롯 (all-pairs 검증 통과)

FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
FINGER_KO = {"Thumb": "엄지", "Index": "검지", "Middle": "중지", "Ring": "약지", "Pinky": "소지"}
JOINTS = ["Thumb_CMC", "Thumb_MCP", "Thumb_IP"] + [
    f"{f}_{j}" for f in FINGERS[1:] for j in ("MCP", "PIP", "DIP")]



def load_sessions():
    rows = []
    for d in sorted(glob.glob(os.path.join(DATA, "*"))):
        if not os.path.isdir(d):
            continue
        meta = json.load(open(glob.glob(os.path.join(d, "*metadata.json"))[0], encoding="utf-8"))
        name = meta["subject"]["name"]
        after = "애프터" in name
        patient = name.replace("(애프터)", "").replace("애프터", "")
        aff = "Left" if "좌" in meta["subject"]["affected_side"] else "Right"
        rd = os.path.join(RESEG, os.path.basename(d).replace(" - 복사본", ""))
        raw = pd.read_csv(glob.glob(os.path.join(rd, "*_continuous_raw_재분할.csv"))[0], encoding="utf-8-sig")
        s = raw[(raw.hand == aff) & (raw.Trial_reseg != "Rest")]
        per_trial = s.groupby("Trial_reseg")[[j + "_filt" for j in JOINTS]].max()
        per_trial.columns = JOINTS
        rows.append(dict(patient=patient, phase="post" if after else "pre", meta=meta,
                         affected=aff, trials=per_trial))
    return rows


def welch(a, b):
    t, p = stats.ttest_ind(b, a, equal_var=False)
    return p


def p_mark(p):
    return "**" if p < 0.01 else "*" if p < 0.05 else ""


def main():
    sessions = load_sessions()
    patients = list(dict.fromkeys(r["patient"] for r in sessions))
    by = {(r["patient"], r["phase"]): r for r in sessions}

    # ---------- 환자별 요약 ----------
    summ = []
    for i, p in enumerate(patients):
        pre, post = by[(p, "pre")], by[(p, "post")]
        m = pre["meta"]["subject"]
        a = pre["trials"].mean(axis=1)    # trial별 15관절 평균 최대 신전각
        b = post["trials"].mean(axis=1)
        summ.append(dict(
            환자=f"P{i + 1}", 이름=p, 성별=m["gender"][:1], 나이=m["age"], FMA=m["fma_score"],
            환측="좌" if pre["affected"] == "Left" else "우",
            n_pre=len(a), n_post=len(b),
            pre_mean=a.mean(), pre_sd=a.std(ddof=1), post_mean=b.mean(), post_sd=b.std(ddof=1),
            delta=b.mean() - a.mean(), p=welch(a, b),
            **{f"pre_{f}": pre["trials"][[j for j in JOINTS if j.startswith(f)]].mean(axis=1).mean() for f in FINGERS},
            **{f"post_{f}": post["trials"][[j for j in JOINTS if j.startswith(f)]].mean(axis=1).mean() for f in FINGERS},
        ))
    S = pd.DataFrame(summ)
    S.to_csv(os.path.join(OUT, "환자별_최대신전각도_요약.csv"), index=False, encoding="utf-8-sig")

    # 관절별 변화량
    D = pd.DataFrame({f"P{i + 1}": by[(p, "post")]["trials"].mean() - by[(p, "pre")]["trials"].mean()
                      for i, p in enumerate(patients)}).T
    P = pd.DataFrame({f"P{i + 1}": {j: welch(by[(p, "pre")]["trials"][j], by[(p, "post")]["trials"][j]) for j in JOINTS}
                      for i, p in enumerate(patients)}).T
    D.round(2).to_csv(os.path.join(OUT, "관절별_변화량.csv"), encoding="utf-8-sig")

    # ---------- 표 2 (평균) ----------
    pre_g, post_g = S.pre_mean.mean(), S.post_mean.mean()
    tab2 = [["항목", "재활 전", "재활 후", "변화량"],
            ["신전 각도(°) M-S",
             f"{pre_g:.1f} ± {S.pre_mean.std(ddof=1):.1f}",
             f"{post_g:.1f} ± {S.post_mean.std(ddof=1):.1f}",
             f"{post_g - pre_g:+.1f} ± {S.delta.std(ddof=1):.1f}"],
            ["신전 각도(°) Auto", "-", "-", "-"],
            ["블록 시간(s) M-S", "-", "-", "-"],
            ["블록 시간(s) Auto", "-", "-", "-"]]
    draw_table(tab2, "표 2. 모드별 재활 전후 측정 결과 (평균 ± SD, n = 3)",
               os.path.join(OUT, "표2_모드별_재활전후_결과.png"), col_w=[1.6, 1.2, 1.2, 1.2],
               note="값: 환자별 평균(15개 관절의 trial별 최대 신전 각도)의 평균 ± SD. "
                    "Auto mode·블록 옮기기 시간은 데이터 미수집.")

    # ---------- 표 3 (환자별) ----------
    tab3 = [["환자", "성별/나이", "FMA", "환측", "재활 전 (°)", "재활 후 (°)", "변화량 (°)", "p"]]
    for r in S.itertuples():
        tab3.append([r.환자, f"{r.성별}/{r.나이}", str(r.FMA), r.환측,
                     f"{r.pre_mean:.1f} ± {r.pre_sd:.1f}", f"{r.post_mean:.1f} ± {r.post_sd:.1f}",
                     f"{r.delta:+.1f}", f"{r.p:.3f}{p_mark(r.p)}"])
    draw_table(tab3, "표 3. 환자별 Master-Slave 재활 전후 최대 신전 각도",
               os.path.join(OUT, "표3_환자별_최대신전각도.png"),
               col_w=[0.6, 0.9, 0.55, 0.55, 1.25, 1.25, 1.0, 0.8],
               note="평균 ± SD (trial 단위, 전 n = "
                    + "/".join(str(x) for x in S.n_pre) + ", 후 n = " + "/".join(str(x) for x in S.n_post)
                    + "). 구간: 연속 기록에서 실제 동작에 맞춰 재분할. p: Welch t-test, *p<0.05, **p<0.01. 180° = 완전 신전.")

    # ---------- 그림 A: 환자별 전후 (dumbbell, 평균 ± SD) ----------
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    y = np.arange(len(S))[::-1]
    for yi, r in zip(y, S.itertuples()):
        ax.plot([r.pre_mean, r.post_mean], [yi, yi], color="#c3c2b7", lw=2, zorder=1)
        ax.errorbar(r.pre_mean, yi + 0.12, xerr=r.pre_sd, fmt="o", ms=6, color=PRE, mec="white", mew=1,
                    ecolor=PRE, elinewidth=1, capsize=2, zorder=3)
        ax.errorbar(r.post_mean, yi - 0.12, xerr=r.post_sd, fmt="o", ms=6, color=POST, mec="white", mew=1,
                    ecolor=POST, elinewidth=1, capsize=2, zorder=3)
        ax.text(max(r.pre_mean + r.pre_sd, r.post_mean + r.post_sd) + 1.5, yi,
                f"{r.delta:+.1f}°{p_mark(r.p)}", va="center", fontsize=8, color=INK)
    ax.set_yticks(y, [f"{r.환자}\nFMA {r.FMA}" for r in S.itertuples()], fontsize=8)
    ax.set_xlabel("평균 최대 신전 각도 (°)  (180° = 완전 신전)")
    ax.set_xlim(115, 185)
    ax.set_ylim(-0.6, len(S) - 0.4)
    ax.xaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=PRE, label="재활 전"),
                       plt.Line2D([], [], marker="o", ls="", color=POST, label="재활 후")],
              frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.tight_layout()
    save(fig, "그림5_환자별_재활전후_최대신전각도")

    # ---------- 그림 B: 손가락별 전후 (small multiples, dumbbell) ----------
    fig, axes = plt.subplots(1, len(S), figsize=(7.0, 2.3), sharey=True)
    for ax, r in zip(axes, S.itertuples()):
        yi = np.arange(5)[::-1]
        pre_v = np.array([getattr(r, f"pre_{f}") for f in FINGERS])
        post_v = np.array([getattr(r, f"post_{f}") for f in FINGERS])
        for k in range(5):
            ax.plot([pre_v[k], post_v[k]], [yi[k], yi[k]], color="#c3c2b7", lw=2, zorder=1)
        ax.scatter(pre_v, yi, s=36, color=PRE, edgecolor="white", lw=1, zorder=3)
        ax.scatter(post_v, yi, s=36, color=POST, edgecolor="white", lw=1, zorder=3)
        lo = min(pre_v.min(), post_v.min())
        ax.set_xlim(np.floor((lo - 5) / 10) * 10, 182)
        ax.set_yticks(yi, [FINGER_KO[f] for f in FINGERS])
        ax.set_title(f"{r.환자} (FMA {r.FMA})", fontsize=9, color=INK)
        ax.xaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
    fig.supxlabel("최대 신전 각도 (°)  (180° = 완전 신전)", fontsize=9, y=0.02)
    fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=PRE, label="재활 전"),
                        plt.Line2D([], [], marker="o", ls="", color=POST, label="재활 후")],
               frameon=False, fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.06))
    fig.tight_layout()
    save(fig, "그림6_손가락별_재활전후_최대신전각도")

    # ---------- 그림 C: 관절별 변화량 히트맵 (diverging blue<->red) ----------
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    cmap = LinearSegmentedColormap.from_list("div", ["#d03b3b", "#f0efec", "#2a78d6"])
    lim = np.ceil(np.abs(D.values).max() / 5) * 5
    fig, ax = plt.subplots(figsize=(7.0, 1.9))
    im = ax.imshow(D.values, cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    ax.set_xticks(range(len(JOINTS)), [j.replace("_", "\n") for j in JOINTS], fontsize=7)
    ax.set_yticks(range(len(D)), [f"{r.환자} (FMA {r.FMA})" for r in S.itertuples()], fontsize=8)
    for i in range(D.shape[0]):
        for j in range(D.shape[1]):
            v, pv = D.values[i, j], P.values[i, j]
            ax.text(j, i, f"{v:+.1f}{p_mark(pv)}", ha="center", va="center", fontsize=6.5,
                    color="white" if abs(v) > lim * 0.6 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("Δ (°), + = 신전 증가", fontsize=7, labelpad=4)
    cb.ax.tick_params(labelsize=7)
    cb.outline.set_visible(False)
    fig.tight_layout()
    save(fig, "그림7_관절별_최대신전각도_변화량")

    improved_metrics(S)
    improved_summary(S)

    print(S[["환자", "이름", "FMA", "pre_mean", "post_mean", "delta", "p"]].round(3).to_string())
    print("표2 M-S:", tab2[1])
    print("저장:", OUT)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)


def draw_table(rows, title, path, col_w, note=None):
    """논문 스타일(삼선표) 표 이미지."""
    total = sum(col_w)
    h = 0.28 * len(rows) + 0.5 + (0.25 if note else 0)
    fig = plt.figure(figsize=(total + 0.2, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, total)
    ax.set_ylim(0, h)
    y = h - 0.22
    ax.text(total / 2, y, title, ha="center", va="center", fontsize=9.5, fontweight="bold", color=INK)
    y -= 0.22
    ax.plot([0, total], [y, y], color=INK, lw=1.2)
    for ri, row in enumerate(rows):
        y -= 0.28
        cx = 0
        for ci, (cell, cw) in enumerate(zip(row, col_w)):
            ax.text(cx + cw / 2, y + 0.14, cell, ha="center", va="center", fontsize=8.5,
                    fontweight="bold" if ri == 0 else "normal",
                    color=MUTED if cell == "-" else INK)
            cx += cw
        if ri == 0:
            ax.plot([0, total], [y, y], color=INK, lw=0.6)
    ax.plot([0, total], [y, y], color=INK, lw=1.2)
    if note:
        ax.text(0, y - 0.17, note, ha="left", va="center", fontsize=6.8, color=INK2)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(path.replace(".png", ".pdf"), bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


# 세 환자 모두 좋아진 지표 (scan_improved_metrics.py 결과 사용)
KEY_METRICS = [
    ("MGA_palm_pct", "MGA / 손바닥 길이 (%)"),
    ("ROM_Index_PIP", "검지 PIP ROM (°)"),
    ("Finger_ROM", "손가락 평균 ROM (°)"),
]


def improved_metrics(S):
    T = pd.read_csv(os.path.join(RESEG, "지표스캔_trial별.csv"), encoding="utf-8-sig")
    names = list(S.이름)
    rows = [["지표", "환자", "재활 전", "재활 후", "변화율", "p", "건측 변화율"]]
    for col, label in KEY_METRICS:
        for i, p in enumerate(names):
            a = T[(T.환자 == p) & (T.phase == "pre")]
            b = T[(T.환자 == p) & (T.phase == "post")]
            pv = stats.ttest_ind(b[col], a[col], equal_var=False).pvalue
            pct = (b[col].mean() - a[col].mean()) / a[col].mean() * 100
            upct = (b["UNA_" + col].mean() - a["UNA_" + col].mean()) / a["UNA_" + col].mean() * 100
            rows.append([label if i == 0 else "", f"P{i + 1}",
                         f"{a[col].mean():.1f} ± {a[col].std():.1f}", f"{b[col].mean():.1f} ± {b[col].std():.1f}",
                         f"{pct:+.1f}%", f"{pv:.3f}{p_mark(pv)}", f"{upct:+.1f}%"])
    draw_table(rows, "표 4. 세 환자 모두 향상된 지표 (환측 손)",
               os.path.join(OUT, "표4_향상지표.png"), col_w=[1.7, 0.5, 1.15, 1.15, 0.8, 0.75, 0.9],
               note="평균 ± SD (trial 단위). p: Welch t-test, *p<0.05, **p<0.01. "
                    "건측 변화율: 같은 구간 건측 손의 변화 (비교 기준).")

    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.5))
    rng = np.random.default_rng(0)
    for ax, (col, label) in zip(axes, KEY_METRICS):
        for i, p in enumerate(names):
            for ph, dx, c in (("pre", -0.17, PRE), ("post", 0.17, POST)):
                v = T[(T.환자 == p) & (T.phase == ph)][col].values
                ax.scatter(i + dx + rng.uniform(-0.05, 0.05, len(v)), v, s=9, color=c, alpha=0.75, lw=0, zorder=2)
                ax.plot([i + dx - 0.11, i + dx + 0.11], [v.mean()] * 2, color=INK, lw=1.4, zorder=3)
            a = T[(T.환자 == p) & (T.phase == "pre")][col]
            b = T[(T.환자 == p) & (T.phase == "post")][col]
            pv = stats.ttest_ind(b, a, equal_var=False).pvalue
            top = max(a.max(), b.max())
            ax.text(i, top, f"{(b.mean() - a.mean()) / a.mean() * 100:+.0f}%{p_mark(pv)}",
                    ha="center", va="bottom", fontsize=7, color=INK)
        ax.set_xticks(range(len(names)), [f"P{i + 1}\nFMA {f}" for i, f in enumerate(S.FMA)], fontsize=7)
        ax.set_title(label, fontsize=8.5, color=INK)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.margins(y=0.15)
        ax.tick_params(axis="y", labelsize=7)
    fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=PRE, label="재활 전"),
                        plt.Line2D([], [], marker="o", ls="", color=POST, label="재활 후"),
                        plt.Line2D([], [], color=INK, lw=1.4, label="평균")],
               frameon=False, fontsize=7.5, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout()
    save(fig, "그림8_향상지표_trial분포")



def improved_summary(S):
    """세 환자 모두 향상된 지표: 전후 연결선(그림 9) + 변화율 막대(그림 10)."""
    T = pd.read_csv(os.path.join(RESEG, "지표스캔_trial별.csv"), encoding="utf-8-sig")
    names = list(S.이름)
    labels = [f"P{i + 1} (FMA {f})" for i, f in enumerate(S.FMA)]
    res = {}
    for col, _ in KEY_METRICS:
        for i, p in enumerate(names):
            a = T[(T.환자 == p) & (T.phase == "pre")][col]
            b = T[(T.환자 == p) & (T.phase == "post")][col]
            res[(col, i)] = dict(pre=a.mean(), post=b.mean(),
                                 pre_se=a.std(ddof=1) / np.sqrt(len(a)), post_se=b.std(ddof=1) / np.sqrt(len(b)),
                                 pct=(b.mean() - a.mean()) / a.mean() * 100,
                                 p=stats.ttest_ind(b, a, equal_var=False).pvalue)

    # 그림 9: 전후 연결선
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.7))
    for ax, (col, label) in zip(axes, KEY_METRICS):
        for i in range(len(names)):
            r = res[(col, i)]
            c = PATIENT_COLORS[i]
            ax.errorbar([0, 1], [r["pre"], r["post"]], yerr=[r["pre_se"], r["post_se"]], color=c, lw=1.6,
                        marker="o", ms=5, mec="white", mew=1, capsize=2, elinewidth=0.9, zorder=3)
            ax.text(1.08, r["post"], f"P{i + 1} {r['pct']:+.0f}%{p_mark(r['p'])}", va="center",
                    fontsize=7, color=INK)
        ax.set_xticks([0, 1], ["재활 전", "재활 후"])
        ax.set_xlim(-0.25, 1.75)
        ax.set_title(label, fontsize=8.5, color=INK)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", labelsize=7)
        ax.margins(y=0.12)
    fig.legend(handles=[plt.Line2D([], [], color=PATIENT_COLORS[i], marker="o", lw=1.6, label=l)
                        for i, l in enumerate(labels)],
               frameon=False, fontsize=7.5, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.08))
    fig.text(0.5, -0.02, "평균 ± SE (trial 단위). *p<0.05, **p<0.01 (Welch t-test)", ha="center", fontsize=6.8, color=INK2)
    fig.tight_layout()
    save(fig, "그림9_향상지표_전후변화")

    # 그림 10: 변화율 막대
    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    w = 0.26
    for i in range(len(names)):
        xs = np.arange(len(KEY_METRICS)) + (i - 1) * (w + 0.02)
        vals = [res[(col, i)]["pct"] for col, _ in KEY_METRICS]
        ax.bar(xs, vals, w, color=PATIENT_COLORS[i], label=labels[i], zorder=2)
        for x, (col, _) in zip(xs, KEY_METRICS):
            r = res[(col, i)]
            ax.text(x, r["pct"] + 0.6, f"{r['pct']:.0f}{p_mark(r['p'])}", ha="center", va="bottom", fontsize=6.8, color=INK)
    ax.axhline(0, color="#c3c2b7", lw=0.8)
    ax.set_xticks(range(len(KEY_METRICS)), [l for _, l in KEY_METRICS], fontsize=7.5)
    ax.set_ylabel("재활 후 변화율 (%)")
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(r["pct"] for r in res.values()) * 1.2)
    ax.legend(frameon=False, fontsize=7, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 1.0))
    fig.text(0.5, -0.03, "변화율 = (재활 후 평균 - 재활 전 평균) / 재활 전 평균. *p<0.05, **p<0.01", ha="center", fontsize=6.5, color=INK2)
    fig.tight_layout()
    save(fig, "그림10_향상지표_변화율")


if __name__ == "__main__":
    main()

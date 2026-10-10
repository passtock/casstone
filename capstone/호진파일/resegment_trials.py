"""녹화 버튼 구간(Trial)을 실제 동작 구간으로 다시 맞추고 trial 지표를 다시 계산한다.

원본(outputs/데이터_저장)은 건드리지 않고 outputs/데이터_재분할/ 에 새로 저장한다.

재분할 방법 (환측 손, 검지~소지 12관절 *_filt 평균 = 손가락 신호 f):
  1. 원래 trial 구간 안에서 f가 최대인 지점(pk)을 앵커로 잡는다.
  2. 시작: pk에서 뒤로 가며 f <= b0 + 15%(f[pk]-b0) 가 되는 첫 지점.
     b0 = 이전 trial의 펴짐 이후 ~ pk 사이(최대 8초) f 최소값 (국소 쥔 상태 기준선).
  3. 끝: pk에서 앞으로 가며 f <= b1 + 15%(f[pk]-b1) 가 되는 첫 지점.
     b1 = pk ~ 다음 trial 앵커 사이(최대 8초) f 최소값.
  4. 앞뒤로 PAD_S 만큼 여유를 주되 이웃 구간과 겹치지 않게 자른다.
연속 녹화 데이터(Rest 포함)를 쓰므로, 녹화 버튼을 늦게 눌러 잘렸던 펴기 구간도 다시 들어온다.
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
matplotlib.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 8})

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "outputs", "데이터_저장")
OUT = os.path.join(BASE, "outputs", "데이터_재분할")
os.makedirs(OUT, exist_ok=True)

FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
JOINTS = ["Thumb_CMC", "Thumb_MCP", "Thumb_IP"] + [
    f"{f}_{j}" for f in FINGERS[1:] for j in ("MCP", "PIP", "DIP")]
FINGER_JOINTS = JOINTS[3:]
TAM_JOINTS = ["Thumb_MCP", "Thumb_IP"] + FINGER_JOINTS        # ASSH: 엄지 = MCP + IP
BASE_FRAC = 0.15        # 기준선 + 15% 진폭에서 시작/끝 판정
SEARCH_S = 8.0          # 기준선 탐색 최대 범위
LOCAL_S = 2.0           # 국소 기준선 = 펴기 직전/쥐기 직후 2초 최소값
MISS_FRAC = 0.3         # 버튼 구간 경계에서 진폭의 30% 이상 펴져 있으면 타이밍 어긋남으로 판정
PAD_S = 0.3             # 구간 앞뒤 여유
GAP_S = 0.5             # 이보다 큰 프레임 간격 = 손 인식 끊김 (기존 코드 VALID_GAP_MAX_S)
INK, PRE, POST = "#0b0b0b", "#9ec5f4", "#2a78d6"


# ---------------------------------------------------------------- 재분할
def realign(t, f, spans):
    """spans: [(trial, t0, t1)] 원래 구간. 반환: trial별 새 구간 dict 목록."""
    n = len(t)
    anchors = []
    for tr, t0, t1 in spans:
        idx = np.flatnonzero((t >= t0) & (t <= t1) & np.isfinite(f))
        anchors.append(int(idx[np.nanargmax(f[idx])]) if len(idx) else None)

    out = []
    for k, (tr, t0, t1) in enumerate(spans):
        pk = anchors[k]
        if pk is None:
            out.append(dict(trial=tr, ok=False, note="구간 안에 유효 프레임 없음"))
            continue
        prev_pk = next((anchors[j] for j in range(k - 1, -1, -1) if anchors[j] is not None), None)
        next_pk = next((anchors[j] for j in range(k + 1, len(anchors)) if anchors[j] is not None), None)

        # 시작 쪽
        lo_i = max(int(np.searchsorted(t, t[pk] - SEARCH_S)), (prev_pk + 1) if prev_pk is not None else 0)
        b0 = np.nanmin(f[lo_i:pk + 1])
        i50 = next((i for i in range(pk, lo_i - 1, -1) if f[i] <= b0 + 0.5 * (f[pk] - b0)), lo_i)
        b0 = np.nanmin(f[max(lo_i, int(np.searchsorted(t, t[i50] - LOCAL_S))):i50 + 1])   # 펴기 직전 국소 기준선
        thr0 = b0 + BASE_FRAC * (f[pk] - b0)
        on = None
        for i in range(pk, lo_i - 1, -1):
            if f[i] <= thr0:
                on = i
                break
        # 끝 쪽
        hi_i = min(int(np.searchsorted(t, t[pk] + SEARCH_S)), next_pk if next_pk is not None else n)
        b1 = np.nanmin(f[pk:hi_i])
        j50 = next((i for i in range(pk, hi_i) if f[i] <= b1 + 0.5 * (f[pk] - b1)), hi_i - 1)
        b1 = np.nanmin(f[j50:max(j50 + 1, min(hi_i, int(np.searchsorted(t, t[j50] + LOCAL_S))))])
        thr1 = b1 + BASE_FRAC * (f[pk] - b1)
        off = None
        for i in range(pk, hi_i):
            if f[i] <= thr1:
                off = i
                break

        notes = []
        if on is None:
            notes.append("시작 기준선 못 찾음")
            on = lo_i
        if off is None:
            notes.append("끝 기준선 못 찾음")
            off = hi_i - 1
        if np.any(np.diff(t[on:off + 1]) > GAP_S):
            notes.append("구간 내 인식 끊김")
        out.append(dict(trial=tr, ok=not notes or notes == ["구간 내 인식 끊김"],
                        orig_start=t0, orig_end=t1, onset=t[on], offset=t[off], peak_t=t[pk],
                        base_pre=b0, base_post=b1, peak=f[pk], note=", ".join(notes),
                        f_at_orig_start=_first_valid(t, f, t0, +1), f_at_orig_end=_first_valid(t, f, t1, -1)))

    # 여유 붙이고 이웃과 겹치지 않게
    for k, r in enumerate(out):
        if "onset" not in r:
            continue
        s, e = r["onset"] - PAD_S, r["offset"] + PAD_S
        if k > 0 and "offset" in out[k - 1]:
            s = max(s, (out[k - 1]["offset"] + r["onset"]) / 2)
        if k + 1 < len(out) and "onset" in out[k + 1]:
            e = min(e, (r["offset"] + out[k + 1]["onset"]) / 2)
        r["new_start"], r["new_end"] = s, e
        r["start_shift_s"] = s - r["orig_start"]     # 음수 = 원래보다 앞에서 시작(녹화가 늦었음)
        r["end_shift_s"] = e - r["orig_end"]         # 양수 = 원래보다 뒤에서 끝(녹화가 일찍 끝남)
        late = r["f_at_orig_start"] > r["base_pre"] + MISS_FRAC * (r["peak"] - r["base_pre"])
        early = r["f_at_orig_end"] > r["base_post"] + MISS_FRAC * (r["peak"] - r["base_post"])
        r["타이밍"] = ("녹화 늦게 시작" if late else "") + (" / " if late and early else "") + \
                     ("녹화 일찍 종료" if early else "") or "정상"
    return out


def _first_valid(t, f, t_edge, direction):
    """버튼 구간 경계에서 구간 안쪽 첫 유효 프레임 값."""
    idx = np.flatnonzero(np.isfinite(f) & ((t >= t_edge) if direction > 0 else (t <= t_edge)))
    return f[idx[0]] if direction > 0 else f[idx[-1]]


def extra_cycles(t, f, windows, t_lo, t_hi):
    """trial 어디에도 안 들어간 쥐기-펴기 동작(녹화 안 된 시도) 찾기."""
    m = (t >= t_lo) & (t <= t_hi) & np.isfinite(f)
    lo, hi = np.percentile(f[m], [5, 95])
    above = m & (f >= lo + 0.5 * (hi - lo))
    for s, e in windows:
        above &= ~((t >= s) & (t <= e))
    found, i = [], 0
    idx = np.flatnonzero(above)
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and idx[j + 1] == idx[j] + 1:
            j += 1
        a, b = idx[i], idx[j]
        pre = f[(t >= t[a] - LOCAL_S) & (t < t[a])]
        post = f[(t > t[b]) & (t <= t[b] + LOCAL_S)]
        closed = lo + 0.3 * (hi - lo)
        complete = len(pre) and len(post) and np.nanmin(pre) <= closed and np.nanmin(post) <= closed
        if t[b] - t[a] >= 0.3 and complete:
            found.append((round(t[idx[i]], 2), round(t[idx[j]], 2), round(np.nanmax(f[idx[i]:idx[j] + 1]), 1)))
        i = j + 1
    return found


# ---------------------------------------------------------------- 지표
def sparc(speed, dt, fc=10.0, thr=0.05):
    """Balasubramanian 2015 SPARC (기존 Mirror_therapy_clock_v3.sparc 와 동일 식)."""
    if len(speed) < 20 or np.max(speed) < 1e-4:
        return np.nan
    nfft = 2 ** (int(np.ceil(np.log2(len(speed)))) + 4)
    sp = np.abs(np.fft.rfft(speed, n=nfft))
    sp /= sp.max()
    fr = np.fft.rfftfreq(nfft, d=dt)
    el = np.flatnonzero((fr <= min(fc, 0.5 / dt)) & (sp >= thr))
    if len(el) < 2 or el[-1] < 2:
        return np.nan
    e = int(el[-1])
    fq, mg = fr[:e + 1], sp[:e + 1]
    return float(-np.sum(np.sqrt((np.diff(fq) / fq[-1]) ** 2 + np.diff(mg) ** 2)))


def trial_metrics(g):
    """g: 한 trial 구간의 환측 손 프레임(시간순)."""
    t = g.time_s.values
    J = g[[j + "_filt" for j in JOINTS]].values
    f = g[[j + "_filt" for j in FINGER_JOINTS]].mean(axis=1).values
    jmax, jmin = np.nanmax(J, axis=0), np.nanmin(J, axis=0)
    rom = dict(zip(JOINTS, jmax - jmin))
    r = dict(
        MaxExt_deg=float(np.mean(jmax)),                                   # 15관절 최대 신전각 평균
        MaxFlex_deg=float(np.mean(jmin)),                                  # 15관절 최소각 평균(얼마나 쥐었나)
        TAM_deg=float(sum(rom[j] for j in TAM_JOINTS)),
        Finger_ROM_deg=float(np.nanmax(f) - np.nanmin(f)),                 # 4손가락 평균 신호 진폭
        MGA_cm=float(np.nanmax(g.Grip_Aperture_cm_filt)),
        Thumb_PalmarAbd_max_deg=float(np.nanmax(g.Thumb_PalmarAbd_filt)),
        Thumb_RadialAbd_max_deg=float(np.nanmax(g.Thumb_RadialAbd_filt)),
        Duration_s=float(t[-1] - t[0]),
        Frames=len(t),
    )
    for fn in FINGERS:
        r[f"ROM_{fn}_deg"] = float(sum(rom[j] for j in JOINTS if j.startswith(fn) and j != "Thumb_CMC"))
    # 속도·시간 지표: 끊김 없는 가장 긴 연속 구간에서
    gaps = np.flatnonzero(np.diff(t) > GAP_S)
    edges = np.r_[0, gaps + 1, len(t)]
    a, b = max(zip(edges[:-1], edges[1:]), key=lambda ab: ab[1] - ab[0])
    tt, ff = t[a:b], f[a:b]
    if len(tt) >= 9:
        # 손 인식 지터(1~2프레임 튐) 제거 후 균일 격자에서 미분
        fm = medfilt(ff, 5)
        dt = float(np.median(np.diff(tt)))
        grid = np.arange(tt[0], tt[-1], dt)
        fg = np.interp(grid, tt, fm)
        v = np.gradient(fg, grid)
        r["Ext_PeakVel_deg_s"] = float(np.max(v))
        r["Flex_PeakVel_deg_s"] = float(np.max(-v))
        ipk = int(np.argmax(fg))
        pre, post = fg[:ipk + 1], fg[ipk:]
        # 펴는 시간은 펴기 전 기준선, 쥐는 시간은 쥔 뒤 기준선으로 따로 잡는다
        b_pre, b_post, top = pre.min(), post.min(), fg[ipk]
        i10 = np.flatnonzero(pre <= b_pre + 0.1 * (top - b_pre))
        i90 = np.flatnonzero(pre >= b_pre + 0.9 * (top - b_pre))
        if len(i10) and len(i90):
            r["Open_Time_s"] = float(grid[i90[0]] - grid[i10[-1]])           # 10->90% 펴는 시간
        k90 = np.flatnonzero(post <= b_post + 0.9 * (top - b_post))
        k10 = np.flatnonzero(post <= b_post + 0.1 * (top - b_post))
        if len(k90) and len(k10):
            r["Close_Time_s"] = float(grid[ipk + k10[0]] - grid[ipk + k90[0]])  # 90->10% 쥐는 시간
        r["Hold_Open_s"] = float(np.sum(fg >= b_pre + 0.9 * (top - b_pre)) * dt)
        # SPARC: 참고용 (펴고 버틴 시간에 크게 좌우됨)
        span = tt[-1] - tt[0]
        n = int(np.floor(span / np.max(np.diff(tt)))) + 1
        if n >= 20:
            g2 = np.linspace(0, span, n)
            ag = np.interp(g2, tt - tt[0], ff)
            r["SPARC_참고"] = sparc(np.abs(np.gradient(ag, g2)), g2[1] - g2[0])
    return r


METRICS = [  # (열, 표시 이름, 좋아지는 방향 +1/-1)
    ("MaxExt_deg", "최대 신전각 (°)", +1),
    ("MaxFlex_deg", "최대 굴곡 시 각도 (°)", -1),
    ("TAM_deg", "TAM (°)", +1),
    ("Finger_ROM_deg", "손가락 평균 ROM (°)", +1),
    ("MGA_cm", "MGA (cm)", +1),
    ("Ext_PeakVel_deg_s", "펴기 최고속도 (°/s)", +1),
    ("Flex_PeakVel_deg_s", "쥐기 최고속도 (°/s)", +1),
    ("Open_Time_s", "펴는 시간 10→90% (s)", -1),
    ("Close_Time_s", "쥐는 시간 90→10% (s)", -1),
    ("Thumb_PalmarAbd_max_deg", "엄지 장측외전 최대 (°)", +1),
    ("Thumb_RadialAbd_max_deg", "엄지 요측외전 최대 (°)", +1),
]


# ---------------------------------------------------------------- 실행
def process_session(d):
    meta = json.load(open(glob.glob(os.path.join(d, "*metadata.json"))[0], encoding="utf-8"))
    name = meta["subject"]["name"]
    aff = "Left" if "좌" in meta["subject"]["affected_side"] else "Right"
    raw_path = glob.glob(os.path.join(d, "*continuous_raw.csv"))[0]
    prefix = os.path.basename(raw_path).replace("_continuous_raw.csv", "")
    raw = pd.read_csv(raw_path, encoding="utf-8-sig")

    h = raw[raw.hand == aff].sort_values("time_s").reset_index(drop=True)
    t = h.time_s.values
    f = h[[j + "_filt" for j in FINGER_JOINTS]].mean(axis=1).values
    tr = raw[raw.Trial != "Rest"].groupby("Trial").time_s.agg(["min", "max"]).sort_values("min")
    spans = [(k, v["min"], v["max"]) for k, v in tr.iterrows()]
    segs = realign(t, f, spans)
    windows = [(r["new_start"], r["new_end"]) for r in segs if "new_start" in r]
    extras = extra_cycles(t, f, windows, spans[0][1] - 3, spans[-1][2] + 3)

    # 새 trial 라벨을 원본 연속 데이터(양손 모두)에 붙여 저장
    out_dir = os.path.join(OUT, os.path.basename(d).replace(" - 복사본", ""))
    os.makedirs(out_dir, exist_ok=True)
    raw = raw.rename(columns={"Trial": "Trial_orig"})
    raw.insert(raw.columns.get_loc("Trial_orig") + 1, "Trial_reseg", "Rest")
    for r in segs:
        if "new_start" in r:
            raw.loc[(raw.time_s >= r["new_start"]) & (raw.time_s <= r["new_end"]), "Trial_reseg"] = r["trial"]
    raw.to_csv(os.path.join(out_dir, prefix + "_continuous_raw_재분할.csv"), index=False, encoding="utf-8-sig")

    # trial 지표 (환측)
    rows = []
    for r in segs:
        row = dict(Trial=r["trial"], Hand=aff, 사용=r.get("ok", False), 타이밍=r.get("타이밍", ""), 비고=r.get("note", ""))
        if "new_start" in r:
            row.update(Orig_Start_s=round(r["orig_start"], 3), Orig_End_s=round(r["orig_end"], 3),
                       New_Start_s=round(r["new_start"], 3), New_End_s=round(r["new_end"], 3),
                       Start_Shift_s=round(r["start_shift_s"], 2), End_Shift_s=round(r["end_shift_s"], 2))
            g = h[(h.time_s >= r["new_start"]) & (h.time_s <= r["new_end"])]
            row.update(trial_metrics(g))
            go = h[(h.time_s >= r["orig_start"]) & (h.time_s <= r["orig_end"])]
            row["MaxExt_deg_원래구간"] = float(np.mean(np.nanmax(go[[j + "_filt" for j in JOINTS]].values, axis=0)))
        rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(out_dir, prefix + "_trials_summary_재분할.csv"), index=False, encoding="utf-8-sig")

    # 확인용 그림
    fig, ax = plt.subplots(figsize=(18, 3.2))
    ax.plot(t, f, ".-", ms=2, lw=0.8, color="#52514e")
    for r in segs:
        if "new_start" not in r:
            continue
        ax.axvspan(r["orig_start"], r["orig_end"], color="#e1e0d9", alpha=0.9, lw=0)
        ax.axvspan(r["new_start"], r["new_end"], facecolor="none", edgecolor="#2a78d6", lw=1.4)
        c = "#d03b3b" if r["타이밍"] != "정상" else INK
        ax.text((r["new_start"] + r["new_end"]) / 2, np.nanmax(f) + 2, r["trial"].replace("Trial_", "T"),
                ha="center", color=c, fontsize=8)
    for s, e, _ in extras:
        ax.axvspan(s, e, color="#eb6834", alpha=0.25, lw=0)
    ax.set_xlim(spans[0][1] - 5, spans[-1][2] + 5)
    ax.set_title(f"{name} 환측({aff}) — 회색: 원래 녹화 구간, 파란 테두리: 재분할 구간, 주황: 녹화 안 된 동작, 빨간 번호: 타이밍 보정됨")
    ax.set_ylabel("손가락 평균 각 (°)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, prefix + "_재분할_확인.png"), dpi=100)
    plt.close(fig)

    seg_df = pd.DataFrame([{**{"세션": name}, **{k: v for k, v in r.items()}} for r in segs])
    return dict(name=name, patient=name.replace("(애프터)", "").replace("애프터", ""),
                phase="post" if "애프터" in name else "pre", meta=meta, trials=T, segs=seg_df, extras=extras)


def hedges_g(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (b.mean() - a.mean()) / sp * (1 - 3 / (4 * (na + nb) - 9)) if sp > 0 else np.nan


def main():
    res = [process_session(d) for d in sorted(glob.glob(os.path.join(DATA, "*"))) if os.path.isdir(d)]

    # 구간 재정렬 요약
    seg_all = pd.concat([r["segs"] for r in res], ignore_index=True)
    cols = ["세션", "trial", "타이밍", "orig_start", "orig_end", "onset", "offset", "new_start", "new_end",
            "start_shift_s", "end_shift_s", "note"]
    seg_all[[c for c in cols if c in seg_all]].round(2).to_csv(
        os.path.join(OUT, "구간_재정렬_요약.csv"), index=False, encoding="utf-8-sig")
    ex = [dict(세션=r["name"], 시작_s=s, 끝_s=e, 최대각=m) for r in res for s, e, m in r["extras"]]
    pd.DataFrame(ex).to_csv(os.path.join(OUT, "녹화안된_동작.csv"), index=False, encoding="utf-8-sig")

    print("== 타이밍 보정된 trial")
    adj = seg_all[seg_all["타이밍"] != "정상"]
    print(adj[["세션", "trial", "타이밍", "start_shift_s", "end_shift_s", "note"]].round(2).to_string(index=False))
    print("== 녹화 안 된 동작:", ex)

    # 전후 비교
    by = {(r["patient"], r["phase"]): r for r in res}
    patients = list(dict.fromkeys(r["patient"] for r in res))
    comp = []
    for i, p in enumerate(patients):
        A = by[(p, "pre")]["trials"]
        B = by[(p, "post")]["trials"]
        A, B = A[A["사용"]], B[B["사용"]]
        for col, label, sign in METRICS:
            a, b = A[col].dropna(), B[col].dropna()
            tt, pv = stats.ttest_ind(b, a, equal_var=False)
            comp.append(dict(환자=f"P{i + 1}", 이름=p, FMA=by[(p, "pre")]["meta"]["subject"]["fma_score"],
                             지표=label, 열=col, 좋은방향=sign, n_pre=len(a), n_post=len(b),
                             pre_mean=a.mean(), pre_sd=a.std(ddof=1), post_mean=b.mean(), post_sd=b.std(ddof=1),
                             delta=b.mean() - a.mean(), pct=(b.mean() - a.mean()) / abs(a.mean()) * 100,
                             p=pv, hedges_g=hedges_g(a, b),
                             판정=("개선" if (b.mean() - a.mean()) * sign > 0 else "악화") if pv < 0.05 else "변화 없음"))
    C = pd.DataFrame(comp)
    C.round(4).to_csv(os.path.join(OUT, "지표_전후비교.csv"), index=False, encoding="utf-8-sig")
    piv = C.pivot_table(index="지표", columns="환자", values="판정", aggfunc="first").reindex([m[1] for m in METRICS])
    print("== 전후 비교 (p<0.05 기준)")
    print(piv.to_string())
    plot_metrics(C, patients)


def plot_metrics(C, patients):
    n = len(METRICS)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(10, 2.3 * rows))
    for ax, (col, label, sign) in zip(axes.flat, METRICS):
        sub = C[C.열 == col].reset_index(drop=True)
        x = np.arange(len(sub))
        for xi, r in sub.iterrows():
            ax.plot([xi - 0.12, xi + 0.12], [r.pre_mean, r.post_mean], color="#c3c2b7", lw=1.5, zorder=1)
            ax.errorbar(xi - 0.12, r.pre_mean, yerr=r.pre_sd, fmt="o", ms=5, color=PRE, ecolor=PRE, capsize=2, zorder=3)
            ax.errorbar(xi + 0.12, r.post_mean, yerr=r.post_sd, fmt="o", ms=5, color=POST, ecolor=POST, capsize=2, zorder=3)
            mark = "**" if r.p < 0.01 else "*" if r.p < 0.05 else ""
            if mark:
                ax.annotate(mark, (xi, max(r.pre_mean + r.pre_sd, r.post_mean + r.post_sd)),
                            ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_xticks(x, [f"{r.환자}\nFMA {r.FMA}" for _, r in sub.iterrows()], fontsize=7)
        arrow = "↑ 좋음" if sign > 0 else "↓ 좋음"
        ax.set_title(f"{label}  ({arrow})", fontsize=8)
        ax.set_xlim(-0.5, len(sub) - 0.5)
        ax.yaxis.grid(True, color="#e1e0d9", lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.margins(y=0.2)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=PRE, label="재활 전"),
                        plt.Line2D([], [], marker="o", ls="", color=POST, label="재활 후")],
               loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.01))
    fig.text(0.5, -0.005, "평균 ± SD (trial 단위, 재분할 구간). *p<0.05, **p<0.01 (Welch t-test)", ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.01, 1, 0.98))
    fig.savefig(os.path.join(OUT, "지표_전후비교.png"), dpi=200, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, "지표_전후비교.pdf"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()

"""재분할 trial 구간으로 후보 지표를 넓게 계산하고, 세 환자 모두 좋아진 지표를 찾는다.

입력: outputs/데이터_재분할/<세션>/*_continuous_raw_재분할.csv (Trial_reseg)
출력: outputs/데이터_재분할/지표스캔_trial별.csv, 지표스캔_전후비교.csv
"""
import glob
import json
import os

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import medfilt

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "outputs", "데이터_저장")
RES = os.path.join(BASE, "outputs", "데이터_재분할")

FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
JOINTS = ["Thumb_CMC", "Thumb_MCP", "Thumb_IP"] + [
    f"{f}_{j}" for f in FINGERS[1:] for j in ("MCP", "PIP", "DIP")]
FINGER_JOINTS = JOINTS[3:]
TAM_JOINTS = ["Thumb_MCP", "Thumb_IP"] + FINGER_JOINTS


def hand_metrics(g):
    t = g.time_s.values
    J = g[[j + "_filt" for j in JOINTS]]
    jmax, jmin = J.max(), J.min()
    r = {}
    for j in JOINTS:
        r[f"ROM_{j}"] = jmax[j + "_filt"] - jmin[j + "_filt"]
        r[f"Max_{j}"] = jmax[j + "_filt"]
    for fn in FINGERS:
        js = [j for j in TAM_JOINTS if j.startswith(fn)]
        r[f"ROM_{fn}"] = sum(r[f"ROM_{j}"] for j in js)
        r[f"Max_{fn}"] = np.mean([r[f"Max_{j}"] for j in JOINTS if j.startswith(fn)])
    for lvl in ("MCP", "PIP", "DIP"):
        r[f"ROM_all_{lvl}"] = np.mean([r[f"ROM_{f}_{lvl}"] for f in FINGERS[1:]])
        r[f"Max_all_{lvl}"] = np.mean([r[f"Max_{f}_{lvl}"] for f in FINGERS[1:]])
    r["MaxExt"] = np.mean([r[f"Max_{j}"] for j in JOINTS])
    r["TAM"] = sum(r[f"ROM_{j}"] for j in TAM_JOINTS)
    f = g[[j + "_filt" for j in FINGER_JOINTS]].mean(axis=1).values
    r["Finger_ROM"] = np.nanmax(f) - np.nanmin(f)
    r["MGA_cm"] = g.Grip_Aperture_cm_filt.max()
    r["MGA_3D_mm"] = g.Grip_Aperture_mm_3D.max()
    r["MGA_palm_pct"] = g.Grip_Aperture_pctPalm_3D.max()
    r["Aperture_ROM_cm"] = g.Grip_Aperture_cm_filt.max() - g.Grip_Aperture_cm_filt.min()
    r["Thumb_PalmarAbd_max"] = g.Thumb_PalmarAbd_filt.max()
    r["Thumb_RadialAbd_max"] = g.Thumb_RadialAbd_filt.max()
    # 속도 (지터 제거 후)
    ok = np.isfinite(f)
    tt, ff = t[ok], f[ok]
    if len(tt) >= 9:
        fm = medfilt(ff, 5)
        dt = float(np.median(np.diff(tt)))
        grid = np.arange(tt[0], tt[-1], dt)
        fg = np.interp(grid, tt, fm)
        v = np.gradient(fg, grid)
        r["Ext_PeakVel"] = v.max()
        r["Flex_PeakVel"] = (-v).max()
        amp = fg.max() - fg.min()
        r["Ext_PeakVel_norm"] = v.max() / amp if amp > 0 else np.nan     # 진폭 대비 속도 (1/s)
        r["Flex_PeakVel_norm"] = (-v).max() / amp if amp > 0 else np.nan
        ipk = int(np.argmax(fg))
        pre, post, top = fg[:ipk + 1], fg[ipk:], fg[ipk]
        bp, bq = pre.min(), post.min()
        i10 = np.flatnonzero(pre <= bp + 0.1 * (top - bp)); i90 = np.flatnonzero(pre >= bp + 0.9 * (top - bp))
        k90 = np.flatnonzero(post <= bq + 0.9 * (top - bq)); k10 = np.flatnonzero(post <= bq + 0.1 * (top - bq))
        r["Open_Time"] = grid[i90[0]] - grid[i10[-1]] if len(i10) and len(i90) else np.nan
        r["Close_Time"] = grid[ipk + k10[0]] - grid[ipk + k90[0]] if len(k90) and len(k10) else np.nan
    return r


# 지표: (이름, 설명, 좋은 방향)
def direction(col):
    if col.startswith(("Open_Time", "Close_Time")):
        return -1
    return +1


LABELS = {
    "MaxExt": "최대 신전각 (15관절 평균)", "TAM": "TAM", "Finger_ROM": "손가락 평균 ROM",
    "MGA_cm": "MGA (2D, cm)", "MGA_3D_mm": "MGA (3D, mm)", "MGA_palm_pct": "MGA / 손바닥 길이 (%)",
    "Aperture_ROM_cm": "손 벌림 변화폭 (cm)", "Ext_PeakVel": "펴기 최고속도", "Flex_PeakVel": "쥐기 최고속도",
    "Ext_PeakVel_norm": "펴기 속도/진폭", "Flex_PeakVel_norm": "쥐기 속도/진폭",
    "Open_Time": "펴는 시간", "Close_Time": "쥐는 시간",
    "Thumb_PalmarAbd_max": "엄지 장측외전", "Thumb_RadialAbd_max": "엄지 요측외전",
}


def hedges_g(a, b):
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (b.mean() - a.mean()) / sp * (1 - 3 / (4 * (na + nb) - 9)) if sp > 0 else np.nan


def main():
    rows = []
    for d in sorted(glob.glob(os.path.join(RES, "*"))):
        if not os.path.isdir(d):
            continue
        src = [s for s in glob.glob(os.path.join(SRC, "*")) if os.path.basename(s).startswith(os.path.basename(d))][0]
        meta = json.load(open(glob.glob(os.path.join(src, "*metadata.json"))[0], encoding="utf-8"))
        name = meta["subject"]["name"]
        aff = "Left" if "좌" in meta["subject"]["affected_side"] else "Right"
        una = "Right" if aff == "Left" else "Left"
        df = pd.read_csv(glob.glob(os.path.join(d, "*_continuous_raw_재분할.csv"))[0], encoding="utf-8-sig")
        for tr, g in df[df.Trial_reseg != "Rest"].groupby("Trial_reseg"):
            ga, gu = g[g.hand == aff].sort_values("time_s"), g[g.hand == una].sort_values("time_s")
            ma, mu = hand_metrics(ga), hand_metrics(gu)
            row = dict(세션=name, 환자=name.replace("(애프터)", "").replace("애프터", ""),
                       phase="post" if "애프터" in name else "pre", FMA=meta["subject"]["fma_score"], Trial=tr)
            row.update(ma)
            row.update({f"UNA_{k}": v for k, v in mu.items()})
            # 환측/건측 비율 (그날 컨디션·카메라 거리 보정)
            for k in ("MaxExt", "TAM", "Finger_ROM", "MGA_cm", "MGA_3D_mm", "MGA_palm_pct", "Ext_PeakVel", "Flex_PeakVel"):
                row[f"Ratio_{k}"] = ma[k] / mu[k] if mu.get(k) else np.nan
            rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(RES, "지표스캔_trial별.csv"), index=False, encoding="utf-8-sig")

    metric_cols = [c for c in T.columns if c not in ("세션", "환자", "phase", "FMA", "Trial") and not c.startswith("UNA_")]
    patients = list(dict.fromkeys(T.환자))
    out = []
    for c in metric_cols:
        sign = direction(c.replace("Ratio_", ""))
        rec = dict(지표=c)
        good, sig, gs = 0, 0, []
        for i, p in enumerate(patients):
            a = T[(T.환자 == p) & (T.phase == "pre")][c].dropna()
            b = T[(T.환자 == p) & (T.phase == "post")][c].dropna()
            if len(a) < 3 or len(b) < 3:
                continue
            _, pv = stats.ttest_ind(b, a, equal_var=False)
            g = hedges_g(a, b) * sign
            rec[f"P{i + 1}_pre"], rec[f"P{i + 1}_post"] = a.mean(), b.mean()
            rec[f"P{i + 1}_pct"] = (b.mean() - a.mean()) / abs(a.mean()) * 100
            rec[f"P{i + 1}_p"], rec[f"P{i + 1}_g"] = pv, g
            good += g > 0
            sig += (g > 0) and pv < 0.05
            gs.append(g)
        rec.update(모두개선=good == len(patients), 개선환자수=good, 유의개선수=sig, 최소g=min(gs), 평균g=np.mean(gs))
        out.append(rec)
    S = pd.DataFrame(out).sort_values(["모두개선", "유의개선수", "최소g"], ascending=False)
    S.to_csv(os.path.join(RES, "지표스캔_전후비교.csv"), index=False, encoding="utf-8-sig")
    print(f"후보 지표 {len(S)}개 중 세 환자 모두 개선 방향: {S.모두개선.sum()}개")
    cols = ["지표", "유의개선수", "최소g", "P1_pct", "P1_p", "P2_pct", "P2_p", "P3_pct", "P3_p"]
    print(S[S.모두개선][cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()

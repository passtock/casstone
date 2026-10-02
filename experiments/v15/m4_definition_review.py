# -*- coding: utf-8 -*-
"""M4(SPARC) 정의 재검토 — 신호 4종 × 지표 3종 안정성 시험 (신규 파일).

31차 결과: M4(Index_PIP 각도계열 SPARC)의 **반복시행 변동성 비율**이
    Healthy 58.9% / Patient_affected 117.5% / Patient_unaffected 92.4% 로 세 집단 모두 50% 초과.

두 가지를 분리해 시험한다.
 (가) **지표 자체가 불안정한가**, 아니면 **나눗셈(비율) 자체가 부적절한가**.
      SPARC/LDLJ 는 0 근처 음수(−7~−15)의 **정규화 무차원값**이라 평균으로 나누는 순간
      분모가 작아 비율이 부풀려진다. → **절대 SD** 와 **초과 변동비(SD_group/SD_Healthy)** 를 병기한다.
 (나) **어떤 신호·정의가 가장 안정적인가**. 신호 4종 × 지표 3종을 모두 계산해 표로 낸다.

신호 4종(위치형 → 속도 프로파일에 지표 적용)
    indexPIP   : 검지 PIP 굴곡각 (deg)
    sum14      : 14개 굴곡각 합 (deg)
    aperture   : 검지–엄지 끝 벌림 D_TI (mm)
    wrist_path : 손목 MP 위치의 시작점 대비 3D 거리 (mm)  ← v13.2 `SPARC_task`(Pose 손목 3D)의 대체
지표 3종
    SPARC (fc = min(10, Nyq)) · LDLJ(무차원 저크 로그) · n_peaks(운동단위 수)
시간축 = `capture_monotonic_s` (30차에 확정한 정본). 원자료 수정 없음.

출력: experiments/results/v15_m4_definition_review.json
"""
from __future__ import annotations
import csv, glob, io, json, math, os, statistics as st, sys
import numpy as np

sys.path.insert(0, os.path.abspath("experiments/metrics"))
from sparc_ref import sparc  # noqa: E402

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/v15_m4_definition_review.json"

FLEX14 = [(0, 1, 2), (1, 2, 3), (0, 5, 6), (5, 6, 7), (6, 7, 8),
          (0, 9, 10), (9, 10, 11), (10, 11, 12), (0, 13, 14), (13, 14, 15),
          (14, 15, 16), (0, 17, 18), (17, 18, 19), (18, 19, 20)]
INDEX_PIP = (5, 6, 7)
WRIST, THUMB_TIP, INDEX_TIP = 0, 4, 8


def rd(p):
    with io.open(p, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def interior(a, b, c):
    v1, v2 = a - b, c - b
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return np.nan
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(v1, v2) / (n1 * n2))))))


def ldlj(speed, t):
    """무차원 저크 로그(관례: 더 음수 = 더 매끄러움). 속도 프로파일에 적용."""
    v = np.asarray(speed, float)
    tt = np.asarray(t, float)
    if v.size < 8 or tt.size != v.size:
        return None
    T = float(tt[-1] - tt[0])
    if T <= 0:
        return None
    dt = T / (v.size - 1)
    D = float(np.max(np.abs(v)))
    if not np.isfinite(D) or D < 1e-9:
        return None
    a = np.gradient(v, dt)
    J = float(np.sum(a * a) * dt)
    if not np.isfinite(J) or J <= 0:
        return None
    val = (T ** 3) / (D ** 2) * J
    return float(-math.log(val)) if val > 0 else None


def n_peaks(speed, frac=0.10):
    """속도 최대값의 10% 이상인 국소 봉우리 수(운동단위 근사)."""
    v = np.asarray(speed, float)
    if v.size < 5:
        return None
    thr = frac * float(np.max(v))
    c = 0
    for i in range(1, v.size - 1):
        if v[i] >= thr and v[i] > v[i - 1] and v[i] >= v[i + 1]:
            c += 1
    return float(c)


def trial_signals(sd, hand):
    """시행×손별 신호 4종의 속도 프로파일과 시간축을 만든다."""
    out = []
    for lf in sorted(glob.glob(os.path.join(sd, "split", "*", "Trial_*", "*_landmarks.csv"))):
        if "pose_landmarks" in lf:
            continue
        df = lf.replace("_landmarks.csv", "_distance_comparison.csv")
        mono = {}
        if os.path.exists(df):
            for r in rd(df):
                if (r.get("Hand") or "") != hand:
                    continue
                fid, t = f(r.get("Frame_ID")), f(r.get("capture_monotonic_s"))
                if fid is not None and t is not None:
                    mono[int(fid)] = t
        by = {}
        with io.open(lf, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if (r.get("Hand") or "").strip() != hand:
                    continue
                try:
                    fid = int(float(r["Frame_ID"])); lid = int(float(r["Landmark_ID"]))
                except (KeyError, TypeError, ValueError):
                    continue
                xyz = (f(r.get("MP_X_m")), f(r.get("MP_Y_m")), f(r.get("MP_Z_m")))
                if all(v is not None for v in xyz):
                    by.setdefault(fid, {})[lid] = xyz
        if len(by) < 20:
            continue
        fids = [k for k in sorted(by) if all(0 <= l < 21 for l in by[k])]
        P = np.full((len(fids), 21, 3), np.nan)
        t = np.full(len(fids), np.nan)
        for i, fid in enumerate(fids):
            for lid, xyz in by[fid].items():
                if 0 <= lid <= 20:
                    P[i, lid] = xyz
            tv = mono.get(fid)
            if tv is not None:
                t[i] = tv
        ok = np.isfinite(t) & np.isfinite(P[:, WRIST]).all(axis=1)
        if ok.sum() < 20:
            continue
        tt, P = t[ok], P[ok]
        o = np.argsort(tt, kind="stable")
        tt, P = tt[o], P[o]
        keep = np.concatenate(([True], np.diff(tt) > 0))
        tt, P = tt[keep], P[keep]
        if tt.size < 20:
            continue
        span = float(tt[-1] - tt[0])
        if span <= 0:
            continue
        mdt = float(np.median(np.diff(tt)))
        if not np.isfinite(mdt) or mdt <= 0:
            continue
        grid = np.linspace(0.0, span, int(math.floor(span / mdt)) + 1)
        if grid.size < 20:
            continue
        fs = (grid.size - 1) / span

        def resample(series):
            v = np.asarray(series, float)
            m = np.isfinite(v)
            if m.sum() < 20:
                return None
            return np.interp(grid, tt[m] - tt[0], v[m])

        ang = np.full((P.shape[0], 14), np.nan)
        for j, (i1, i2, i3) in enumerate(FLEX14):
            for fr in range(P.shape[0]):
                ang[fr, j] = 180.0 - interior(P[fr, i1], P[fr, i2], P[fr, i3])
        ip = ang[:, FLEX14.index(INDEX_PIP)]
        comp = np.isfinite(ang).all(axis=1)
        s14 = np.full(P.shape[0], np.nan)
        s14[comp] = ang[comp].sum(axis=1)
        dti = np.linalg.norm(P[:, THUMB_TIP] - P[:, INDEX_TIP], axis=-1) * 1000.0
        wpath = np.linalg.norm(P[:, WRIST] - P[0, WRIST], axis=-1) * 1000.0

        sigs = {}
        for name, series in (("indexPIP", ip), ("sum14", s14), ("aperture", dti), ("wrist_path", wpath)):
            g = resample(series)
            if g is None:
                continue
            speed = np.abs(np.gradient(g, grid))
            sigs[name] = {
                "sparc": sparc(speed, grid, fc=min(10.0, fs / 2.0)),
                "ldlj": ldlj(speed, grid),
                "n_peaks": n_peaks(speed),
                "peaks_per_s": (n_peaks(speed) / span) if (n_peaks(speed) is not None and span > 0) else None,
                "speed_median": float(np.median(speed)),
            }
        out.append({"trial": os.path.basename(os.path.dirname(lf)), "fs": fs, "signals": sigs})
    return out


def ratios(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return {}
    m, s = st.mean(v), st.stdev(v)
    return {"n": len(v), "mean": m, "sd": s,
            "ratio_pct": (1.96 * math.sqrt(2) * s / abs(m) * 100.0) if abs(m) > 1e-9 else None}


def main():
    sessions = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))]
    data = {}
    for d in sessions:
        sd = os.path.join(ROOT, d)
        m = glob.glob(os.path.join(sd, "*_metadata.json"))
        j = json.load(io.open(m[0], encoding="utf-8-sig")) if m else {}
        grp = j.get("subject", {}).get("group")
        aff = j.get("subject", {}).get("affected_side")
        for hand in ("Left", "Right"):
            role = ("affected" if aff and hand in str(aff) else "unaffected" if aff else "control")
            grp2 = "Patient" if grp == "Patient" else "Healthy"
            rows = trial_signals(sd, hand)
            if rows:
                data.setdefault((grp2, role), []).append({"session": d, "hand": hand, "trials": rows})

    res = {"provenance": {
        "signals": ["indexPIP", "sum14", "aperture", "wrist_path"],
        "metrics": ["sparc", "ldlj", "n_peaks"],
        "time_axis": "capture_monotonic_s",
        "note": "SPARC/LDLJ는 0 근처 무차원값 → 비율(%)은 분모가 작아 과대. 절대 SD와 초과계수(SD_group/SD_Healthy)를 병기"},
        "table": []}
    table = []
    for signame in ("indexPIP", "sum14", "aperture", "wrist_path"):
        for met in ("sparc", "ldlj", "n_peaks", "peaks_per_s"):
            row = {"signal": signame, "metric": met}
            base_sd = None
            for key in (("Healthy", "control"), ("Patient", "affected"), ("Patient", "unaffected")):
                vals = [t["signals"][signame][met]
                        for g in data.get(key, []) for t in g["trials"]
                        if signame in t["signals"] and met in t["signals"][signame]]
                r = ratios(vals)
                tag = "H" if key[0] == "Healthy" else ("A" if key[1] == "affected" else "U")
                row[tag + "_n"] = r.get("n")
                row[tag + "_mean"] = r.get("mean")
                row[tag + "_sd"] = r.get("sd")
                row[tag + "_ratio"] = r.get("ratio_pct")
                if tag == "H":
                    base_sd = r.get("sd")
            for tag in ("A", "U"):
                sdv = row.get(tag + "_sd")
                row[tag + "_excess"] = (sdv / base_sd) if (base_sd and sdv and base_sd > 1e-12) else None
            table.append(row)
    res["provenance"]["table"] = table

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2, default=str))

    print("=" * 118)
    print("M4 정의 재검토 — 신호 4종 × 지표 3종 (n: H/A/U = Healthy/환측/비환측)")
    print("=" * 118)
    print("%-11s %-8s | %-22s | %-22s | %-22s" % ("신호", "지표", "Healthy (평균/SD/비율%)", "환측", "비환측"))
    for row in table:
        def fmt(tag):
            r, mm, ss = row.get(tag + "_ratio"), row.get(tag + "_mean"), row.get(tag + "_sd")
            if r is None:
                return "-"
            return "%7.3f/%6.3f/%6.1f%%" % (mm, ss, r)
        print("%-11s %-8s | %-22s | %-22s | %-22s" % (
            row["signal"], row["metric"], fmt("H"), fmt("A"), fmt("U")))
    print()
    print("초과 변동계수 = SD(집단)/SD(Healthy).  1.0 = 비장애와 같은 흩어짐:")
    print("%-11s %-8s | %8s %8s" % ("신호", "지표", "환측", "비환측"))
    for row in table:
        e = lambda t: ("%8.2f" % row[t + "_excess"]) if row.get(t + "_excess") else "       -"
        print("%-11s %-8s | %s %s" % (row["signal"], row["metric"], e("A"), e("U")))
    print()
    print("JSON →", OUT)


if __name__ == "__main__":
    main()

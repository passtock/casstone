# -*- coding: utf-8 -*-
"""§8.2 분절 규칙 — 실패 유형 4종 주입 검증 v2 (신규 파일).

v1(같은 파일의 이전 저장본)은 기준선을 "집단 중앙값"으로 잡아 29차 `rule_current`(시행 첫 2초)와
비교가 성립하지 않았다. v2는 **29차 정의에 정확히 맞춘다**.

  TOL = 0.20 · MIN_AGREE = 2 · REST_S = 2.0
  θ(손가락) = 그 손가락 14각 정의의 합 (엄지 2개, 나머지 3개)  ← v1은 검지 1개만 써서 달랐다
  현행 : 시행 첫 2초 중앙값 대비 ±20% 벗어난 분절이 2개 이상인 프레임 = 불일치
  B안  : L̂(θ)=a0+a1θ+a2θ² (2차), |L−L̂|/L̂ > 0.20 인 분절 2개 이상 = 불일치
  B 계수는 **LOSO**(나머지 2세션에서 적합 → 남긴 1세션에서 평가)로 순환 제거

주입 유형 (0.5초 ≈ 8프레임, 시행당 1회, 좌우 별도)
    I1 배경 도약 · I2 완전 소실 · I3 스케일 오류 · I4 물체 가림(손끝이 손목으로 붕괴)

측정: ① 시행 단위 검출률 ② **정상 구간 오검출(프레임·시행)** ③ 주입 시야 상실(판정 불가 프레임)
    검출률은 **오검출률과 함께** 읽어야 한다. 오검출이 높으면 "검출"은 규칙이 늘 켜져 있기 때문일 수 있다.

정직: ① B 계수를 환자 세션에서 적합하는 경우가 생긴다(LOSO 한계) → 사양과 다름, 명시.
      ② 환자 세션에 영상 정답이 없어 실제 오류와 정상 운동을 구분하지 못한다.

출력: experiments/results/v15_failure_injection_v2.json
"""
from __future__ import annotations
import csv, glob, io, json, math, os
import numpy as np

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/v15_failure_injection_v2.json"
TOL, MIN_AGREE, REST_S = 0.20, 2, 2.0

FLEX_DEFS = {"Thumb": [(0, 1, 2), (1, 2, 3)],
             "Index": [(0, 5, 6), (5, 6, 7), (6, 7, 8)],
             "Middle": [(0, 9, 10), (9, 10, 11), (10, 11, 12)],
             "Ring": [(0, 13, 14), (13, 14, 15), (14, 15, 16)],
             "Pinky": [(0, 17, 18), (17, 18, 19), (18, 19, 20)]}
SEGMENTS = [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8),
            (9, 10), (10, 11), (11, 12), (13, 14), (14, 15), (15, 16),
            (17, 18), (18, 19), (19, 20)]
FINGER_OF = {s: f for f, defs in () for s in []}
FINGER_OF = {}
for f in ("Thumb",):
    for s in [(1, 2), (2, 3), (3, 4)]:
        FINGER_OF[s] = f
for f, segs in (("Index", [(5, 6), (6, 7), (7, 8)]), ("Middle", [(9, 10), (10, 11), (11, 12)]),
                ("Ring", [(13, 14), (14, 15), (15, 16)]), ("Pinky", [(17, 18), (18, 19), (19, 20)])):
    for s in segs:
        FINGER_OF[s] = f
FNAMES = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def rd(p):
    with io.open(p, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def fl(x):
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


def load_windows(sd, hand):
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
                fid, t = fl(r.get("Frame_ID")), fl(r.get("capture_monotonic_s"))
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
                xyz = (fl(r.get("MP_X_m")), fl(r.get("MP_Y_m")), fl(r.get("MP_Z_m")))
                if all(v is not None for v in xyz):
                    by.setdefault(fid, {})[lid] = xyz
        if len(by) < 20:
            continue
        fids = [k for k in sorted(by) if all(0 <= l < 21 for l in by[k])]
        if len(fids) < 20:
            continue
        P = np.full((len(fids), 21, 3), np.nan)
        t = np.full(len(fids), np.nan)
        for i, fid in enumerate(fids):
            for lid, xyz in by[fid].items():
                if 0 <= lid <= 20:
                    P[i, lid] = xyz
            tv = mono.get(fid)
            if tv is not None:
                t[i] = tv
        if not np.isfinite(t).any():
            t = np.arange(len(fids), dtype=float)
        out.append({"trial": os.path.basename(os.path.dirname(lf)), "P": P, "t": t})
    return out


def per_frame(P, t):
    F = P.shape[0]
    L = np.full((F, 15), np.nan)
    for k, (a, b) in enumerate(SEGMENTS):
        L[:, k] = np.linalg.norm(P[:, a] - P[:, b], axis=-1)
    flex = {}
    for f in FNAMES:
        vals = np.full((F, len(FLEX_DEFS[f])), np.nan)
        for m, (i, j, k) in enumerate(FLEX_DEFS[f]):
            for fr in range(F):
                vals[fr, m] = 180.0 - interior(P[fr, i], P[fr, j], P[fr, k])
        flex[f] = np.nansum(vals, axis=1)
    return {"L": L, "flex": flex, "t": t, "F": F}


def rule_current(pf):
    L, t, F = pf["L"], pf["t"], pf["F"]
    viol = np.zeros((15, F), bool)
    for k in range(15):
        d = L[:, k]
        s = (t <= (t[0] + REST_S)) & np.isfinite(d)
        if s.sum() < 8:
            continue
        base = float(np.median(d[s]))
        if base <= 0:
            continue
        viol[k] = np.isfinite(d) & (np.abs(d - base) / base > TOL)
    cnt = viol.sum(axis=0)
    return np.isfinite(L).any(axis=1) & (cnt >= MIN_AGREE)


def rule_B(pf, kappa):
    L, F = pf["L"], pf["F"]
    viol = np.zeros((15, F), bool)
    for k, seg in enumerate(SEGMENTS):
        coef = kappa.get(k)
        if coef is None:
            continue
        th = pf["flex"][FINGER_OF[seg]]
        ok = np.isfinite(L[:, k]) & np.isfinite(th)
        if ok.sum() < 8:
            continue
        Lh = np.polyval(coef, th[ok])
        rel = np.full(ok.sum(), np.inf)
        g = Lh > 1e-6
        rel[g] = np.abs(L[ok, k][g] - Lh[g]) / Lh[g]
        viol[k, np.flatnonzero(ok)] = rel > TOL
    cnt = viol.sum(axis=0)
    return np.isfinite(L).any(axis=1) & (cnt >= MIN_AGREE)


def fit_kappa(pfs):
    kappa = {}
    for k, seg in enumerate(SEGMENTS):
        xs, ys = [], []
        for pf in pfs:
            th = pf["flex"][FINGER_OF[seg]]
            ok = np.isfinite(pf["L"][:, k]) & np.isfinite(th)
            xs.append(th[ok]); ys.append(pf["L"][ok, k])
        x = np.concatenate(xs) if xs else np.array([])
        y = np.concatenate(ys) if ys else np.array([])
        if x.size >= 50:
            kappa[k] = np.polyfit(x, y, 2)
    return kappa


def inject(P, kind, idx0, width, rng):
    Q = P.copy()
    sl = slice(idx0, min(idx0 + width, P.shape[0]))
    if kind == "I1_jump":
        d = rng.normal(size=3); d = d / np.linalg.norm(d) * 0.150
        Q[sl, 8] = Q[sl, 8] + d
    elif kind == "I2_loss":
        Q[sl, 8] = np.nan
    elif kind == "I3_scale":
        w = P[sl, 0:1, :]; Q[sl] = w + 1.5 * (P[sl] - w)
    elif kind == "I4_collapse":
        Q[sl, 8] = P[sl, 0]
    return Q, sl


def main():
    sessions = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))]
    groups = {}
    for d in sessions:
        m = glob.glob(os.path.join(ROOT, d, "*_metadata.json"))
        groups[d] = ("Patient" if m and
                     json.load(io.open(m[0], encoding="utf-8-sig")).get("subject", {}).get("group") == "Patient"
                     else "Healthy")
    rng = np.random.default_rng(20261002)

    # 세션×손 → per_frame 사전계산
    PF = {}
    for d in sessions:
        for hand in ("Left", "Right"):
            wins = load_windows(os.path.join(ROOT, d), hand)
            if wins:
                PF[(d, hand)] = [per_frame(w["P"], w["t"]) for w in wins]
                PF[(d, hand) + ("raw",)] = [w["P"] for w in wins]

    res = {"provenance": {"tol": TOL, "min_agree": MIN_AGREE, "rest_s": REST_S,
                          "theta": "손가락 14각 합(엄지2·나머지3)", "fit": "LOSO(나머지 2세션)",
                          "fit_caveat": "비장애 세션을 남길 때 환자 세션에서 B를 적합 → 사양과 다름",
                          "time_axis": "capture_monotonic_s (29차는 time_s 사용)"},
           "detection": {}, "false_alarm": {}}

    for d in sessions:
        for hand in ("Left", "Right"):
            if (d, hand) not in PF:
                continue
            others = [pf for key in PF if len(key) == 2 and key[0] != d and key != (d, hand)
                      for pf in PF[key]]
            kappa = fit_kappa(others)
            wins, raws = PF[(d, hand)], PF[(d, hand) + ("raw",)]
            gt = groups[d]
            # 정상 오검출
            fa_f = fa_t = fa_fB = fa_tB = 0
            nfr = 0
            for pf in wins:
                f = rule_current(pf); b = rule_B(pf, kappa)
                nfr += pf["F"]
                fa_f += int(f.sum()); fa_t += int(f.any())
                fa_fB += int(b.sum()); fa_tB += int(b.any())
            res["false_alarm"]["%s|%s" % (gt, hand)] = {
                "n_trials": len(wins), "n_frames": nfr,
                "cur_frame": fa_f / max(nfr, 1), "cur_trial": fa_t / len(wins),
                "B_frame": fa_fB / max(nfr, 1), "B_trial": fa_tB / len(wins)}
            # 주입
            for kind in ("I1_jump", "I2_loss", "I3_scale", "I4_collapse"):
                dc = db = 0
                for wi, pf in enumerate(wins):
                    P = raws[wi]
                    idx0 = max(1, int(0.35 * P.shape[0]))
                    Q, sl = inject(P, kind, idx0, 8, rng)
                    pf2 = per_frame(Q, pf["t"])
                    dc += int(rule_current(pf2)[sl].any())
                    db += int(rule_B(pf2, kappa)[sl].any())
                res["detection"]["%s|%s|%s" % (gt, hand, kind)] = {
                    "n_trials": len(wins), "cur": dc / len(wins), "B": db / len(wins)}

    print("=" * 116)
    print("분절 규칙 실패유형 주입 v2 — 29차 정의 정합 (첫 2초 기준선 / θ=손가락 굴곡합 / B는 LOSO)")
    print("=" * 116)
    print("■ 주입 검출률 (시행 단위)")
    print("%-32s %5s %9s %9s" % ("집단|손|주입", "시행", "현행", "B안"))
    for k in sorted(res["detection"]):
        v = res["detection"][k]
        print("%-32s %5d %9.2f %9.2f" % (k, v["n_trials"], v["cur"], v["B"]))
    print()
    print("■ 정상 구간 오검출 — 검출률은 이 값과 함께 읽어야 한다")
    print("%-20s %6s %6s %11s %11s %10s %10s" % ("집단|손", "시행", "프레임", "현행(프레임)", "현행(시행)", "B(프레임)", "B(시행)"))
    for k in sorted(res["false_alarm"]):
        v = res["false_alarm"][k]
        print("%-20s %6d %6d %11.3f %11.3f %10.3f %10.3f" % (
            k, v["n_trials"], v["n_frames"], v["cur_frame"], v["cur_trial"], v["B_frame"], v["B_trial"]))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    print()
    print("JSON →", OUT)


if __name__ == "__main__":
    main()

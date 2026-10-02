# -*- coding: utf-8 -*-
"""§8.2 손 분절 규칙 재정의 3안 비교 (2026-10-02 요청).

현행(v13.2): 15개 분절 길이가 **시행 전 2초 중앙값** 대비 ±20% 벗어난 것이 **2개 이상**인 프레임을 불일치로 표시.
문제(28차 감사): 프레임 불일치율이 **손가락 운동량**과 강하게 상관(r=0.714 시행별, 0.979 세션×손).
  → 게이트가 "추적 품질"이 아니라 "운동량"을 재고, A3가 **많이 움직인 시행을 보류**한다.

비교안
  A. **움직임 회귀보정**: 시행별 불일치율을 시행의 운동량(TAM 중앙)에 회귀 → **잔차**로 판정.
  B. **자세 조건화**: 분절의 **기대 길이**를 그 분절이 속한 손가락의 굴곡합에 대한 함수로 적합 →
     `|L - L̂(θ)|/L̂(θ)` 로 판정. (κ는 참조 세션에서 적합)
  C. **진단값 강등**: 분절 규칙을 게이트에서 제거. 게이트는 추적률·갭·손-일관성만.

순환 방지: A·B의 적합은 **leave-one-session-out**(다른 2세션에서 적합 → 나머지 1세션에서 평가).

측정
  ① 시행별 불일치율의 **운동량 상관 r** (낮을수록 좋다)
  ② **집단 편향** = Healthy 평균 − Patient 평균 (현행은 환자가 더 잘 통과 = 음의 큰 값)
  ③ **검출력 보존**: 불일치로 표시되는 시행/프레임이 남아 있는가(0이면 게이트가 사라진 것)
"""
from __future__ import annotations

import csv, glob, io, json, math, os, statistics as st, sys
import numpy as np

sys.path.insert(0, os.path.abspath("experiments/v13"))
from qv13 import SEGMENTS_15, HAND_ALL_SEGS, nm  # noqa: E402

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/v14_segment_rule_options.json"
TOL = 0.20
MIN_AGREE = 2
REST_S = 2.0
# 손가락별 분절 → 굴곡합 계산용 관절 정의 (이름 = qv13.nm)
FINGER_OF = {}
for k in ("Th",):
    for s in [(1, 2), (2, 3), (3, 4)]:
        FINGER_OF[s] = "Thumb"
for name, segs in (("Index", [(5, 6), (6, 7), (7, 8)]),
                   ("Middle", [(9, 10), (10, 11), (11, 12)]),
                   ("Ring", [(13, 14), (14, 15), (15, 16)]),
                   ("Pinky", [(17, 18), (18, 19), (19, 20)])):
    for s in segs:
        FINGER_OF[s] = name
# 굴곡각 14개 (v13 §7.1)
FLEX_DEFS = {"Thumb": [(0, 1, 2), (1, 2, 3)],
             "Index": [(0, 5, 6), (5, 6, 7), (6, 7, 8)],
             "Middle": [(0, 9, 10), (9, 10, 11), (10, 11, 12)],
             "Ring": [(0, 13, 14), (13, 14, 15), (14, 15, 16)],
             "Pinky": [(0, 17, 18), (17, 18, 19), (18, 19, 20)]}


def interior(a, b, c):
    v1, v2 = a - b, c - b
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return np.nan
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(v1, v2) / (n1 * n2))))))


def load_session(sess_dir, hand):
    """시행별 (t, P) 목록."""
    out = []
    for f in sorted(glob.glob(os.path.join(sess_dir, "split", "*", "Trial_*", "*_landmarks.csv"))):
        by = {}
        with io.open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if (r.get("Hand") or "").strip() != hand:
                    continue
                try:
                    fid = int(float(r["Frame_ID"])); lid = int(float(r["Landmark_ID"]))
                except (KeyError, TypeError, ValueError):
                    continue
                try:
                    by.setdefault(fid, {})[lid] = (float(r["MP_X_m"]), float(r["MP_Y_m"]),
                                                   float(r["MP_Z_m"]), float(r.get("time_s") or "nan"))
                except (TypeError, ValueError):
                    pass
        if len(by) < 20:
            continue
        fids = sorted(by)
        P = np.full((len(fids), 21, 3), np.nan)
        t = np.full(len(fids), np.nan)
        for i, fid in enumerate(fids):
            for lid, (x, y, z, ts) in by[fid].items():
                if 0 <= lid <= 20:
                    P[i, lid] = (x, y, z)
                if lid == 0:
                    t[i] = ts
        if not np.isfinite(t).any():
            t = np.arange(len(fids), dtype=float)
        out.append({"trial": os.path.basename(os.path.dirname(f)),
                    "n": int(len(fids)), "t": t, "P": P, "fids": np.array(fids)})
    return out


def per_frame(trial):
    """프레임별: 15분절 길이, 손가락별 굴곡합, 14각 합."""
    P, t = trial["P"], trial["t"]
    F = P.shape[0]
    L = np.full((F, len(HAND_ALL_SEGS)), np.nan)
    for k, (i, j) in enumerate(HAND_ALL_SEGS):
        L[:, k] = np.linalg.norm(P[:, i] - P[:, j], axis=-1)
    flex = {}
    for fname, defs in FLEX_DEFS.items():
        a = np.full(F, np.nan)
        vals = np.full((F, len(defs)), np.nan)
        for m, (i, j, k) in enumerate(defs):
            for fr in range(F):
                vals[fr, m] = 180.0 - interior(P[fr, i], P[fr, j], P[fr, k])
        a = np.nansum(vals, axis=1)
        flex[fname] = a
    total = np.nansum(np.stack([flex[f] for f in FLEX_DEFS], axis=1), axis=1)
    return {"L": L, "flex": flex, "total": total, "t": t, "P": P, "F": F,
            "_name": trial["trial"], "_fids": trial.get("fids")}


def rule_current(pf):
    """현행 v13.2: 시행 전 2초 중앙값 대비 ±20%, 2개 이상 동시 위반."""
    L, t, F = pf["L"], pf["t"], pf["F"]
    rest = t <= (t[0] + REST_S)
    viol = np.zeros((L.shape[1], F), bool)
    for k in range(L.shape[1]):
        d = L[:, k]
        s = rest & np.isfinite(d)
        if s.sum() < 8:
            continue
        base = float(np.median(d[s]))
        if base <= 0:
            continue
        rel = np.abs(d - base) / base
        viol[k] = np.isfinite(rel) & (rel > TOL)
    cnt = viol.sum(axis=0)
    flags = np.isfinite(L).any(axis=1) & (cnt >= MIN_AGREE)
    return flags


def rule_pose(pf, kappa):
    """B. 자세 조건화: 분절별 기대 길이 L̂(굴곡합) 적합으로 판정.

    kappa: {seg_index: np.poly1d 계수 (2차)} — 다른 세션에서 적합된 것.
    """
    L, t, F = pf["L"], pf["t"], pf["F"]
    viol = np.zeros((L.shape[1], F), bool)
    for k, seg in enumerate(HAND_ALL_SEGS):
        coef = kappa.get(k)
        if coef is None:
            continue
        fname = FINGER_OF[seg]
        theta = pf["flex"][fname]
        ok = np.isfinite(L[:, k]) & np.isfinite(theta)
        if ok.sum() < 8:
            continue
        Lk = L[ok, k]
        Lh = np.polyval(coef, theta[ok])
        good = Lh > 1e-6
        rel = np.full(ok.sum(), np.inf)
        rel[good] = np.abs(Lk[good] - Lh[good]) / Lh[good]
        idx = np.flatnonzero(ok)
        viol[k, idx] = rel > TOL
    cnt = viol.sum(axis=0)
    return np.isfinite(L).any(axis=1) & (cnt >= MIN_AGREE)


def fit_kappa(sessions_pf):
    """참조 세션들에서 분절별 L̂(굴곡합) 2차 적합."""
    kappa = {}
    for k, seg in enumerate(HAND_ALL_SEGS):
        fname = FINGER_OF[seg]
        xs, ys = [], []
        for pf in sessions_pf:
            th = pf["flex"][fname]
            ok = np.isfinite(pf["L"][:, k]) & np.isfinite(th)
            xs.append(th[ok]); ys.append(pf["L"][ok, k])
        if not xs:
            continue
        x = np.concatenate(xs); y = np.concatenate(ys)
        if x.size < 50:
            continue
        kappa[k] = np.polyfit(x, y, 2)
    return kappa


def pearson(xs, ys):
    if len(xs) < 3:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs)); dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return (num / (dx * dy)) if dx * dy > 0 else None


def rule_C_trial(pf, dt_ref=0.077):
    """C. 진단값 강등: 게이트 = 추적률 + 갭 + 손-일관성 만 (분절 규칙 제외)."""
    P, t = pf["P"], pf["t"]
    F = pf["F"]
    w = P[:, 0]
    def d(landmark):
        return np.linalg.norm(P[:, landmark] - w, axis=-1) * 1000.0
    ok4 = np.isfinite(d(4)) & (d(4) >= 60) & (d(4) <= 230)
    ok8 = np.isfinite(d(8)) & (d(8) >= 60) & (d(8) <= 230)
    ok12 = np.isfinite(d(12)) & (d(12) >= 60) & (d(12) <= 230)
    tips = np.isfinite(P[:, 4, 0]) & np.isfinite(P[:, 8, 0])
    valid = tips & ok4 & ok8 & ok12
    track = float(valid.mean()) if valid.size else 0.0
    n_valid = int(valid.sum())
    longest, run = 0.0, None
    for i in range(valid.size):
        if not valid[i]:
            if run is None:
                run = i
        elif run is not None:
            longest = max(longest, float(t[i] - t[run]))
            run = None
    if run is not None and t.size:
        longest = max(longest, float(t[-1] - t[run]))
    # 획득 누락률(프레임 ID 연속성) — §8.2 손목 행과 동일 규칙
    try:
        acq = None
        if pf.get("_fids") is not None:
            f = np.asarray(pf["_fids"], float)
            df = np.diff(f)
            med = float(np.median(df)) if df.size else 0.0
            if med > 0:
                est = np.maximum(np.round(df / med) - 1, 0).sum()
                acq = float(est / (len(f) + est))
    except Exception:
        acq = None
    reasons = []
    if track < 0.80:
        reasons.append("low_tracking")
    if longest > 5.0 * dt_ref:
        reasons.append("gap_over_5x_dt_ref")
    if n_valid < 8:
        reasons.append("insufficient_frames")
    if acq is not None and acq > 0.15:
        reasons.append("acquisition_missing")
    return {"pass": len(reasons) == 0, "reasons": reasons,
            "track_ratio": track, "n_valid": n_valid, "longest_gap_s": longest,
            "acq_missing_rate": acq}


def main():
    sessions = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))]
    meta = {}
    for s in sessions:
        m = glob.glob(os.path.join(ROOT, s, "*_metadata.json"))
        g = None
        if m:
            try:
                g = json.load(io.open(m[0], encoding="utf-8-sig")).get("subject", {}).get("group")
            except Exception:
                pass
        meta[s] = g

    # 세션×손 단위로 프레임 특징을 모은다
    unit = {}
    for s in sessions:
        for hand in ("Left", "Right"):
            trials = load_session(os.path.join(ROOT, s), hand)
            if not trials:
                continue
            pfs = [per_frame(tr) for tr in trials]
            unit[(s, hand)] = pfs

    # 현행 / B 는 프레임 단위로, A 는 시행 단위로 계산
    res = {"provenance": {"sessions": sessions, "groups": meta, "tol": TOL,
                          "min_agree": MIN_AGREE, "rest_s": REST_S,
                          "note": "A·B 적합은 leave-one-session-out. 전부 Task1 자유 개폐."},
           "units": {}, "loso": {}}

    for (s, hand), pfs in unit.items():
        # 현행
        cur = []
        amp = []
        for pf in pfs:
            f = rule_current(pf)
            base = np.isfinite(pf["L"]).any(axis=1)
            rate = float(f.sum() / max(int(base.sum()), 1))
            cur.append({"trial": pf["_name"], "flag_rate": rate,
                        "tam": float(np.nanmedian(pf["total"]))})
            amp.append(float(np.nanmedian(pf["total"])))
        res["units"]["%s|%s" % (s, hand)] = {
            "group": meta[s], "n_trials": len(pfs),
            "current": cur,
            "current_rate_median": st.median([c["flag_rate"] for c in cur]) if cur else None,
            "current_rate_mean": st.mean([c["flag_rate"] for c in cur]) if cur else None,
        }

    # LOSO: 세션 하나를 빼고 B(자세조건화)를 나머지에서 적합 → 뺀 세션 평가
    for held in sessions:
        ref = [pf for (s, hand), pfs in unit.items() if s != held for pf in pfs]
        if not ref:
            continue
        kappa = fit_kappa(ref)
        rows = []
        for (s, hand), pfs in unit.items():
            if s != held:
                continue
            for pf in pfs:
                g = np.isfinite(pf["L"]).any(axis=1)
                fb = rule_pose(pf, kappa)
                rate = float(fb.sum() / max(int(g.sum()), 1))
                rows.append({"session": s, "hand": hand, "trial": pf["_name"],
                             "flag_rate": rate, "tam": float(np.nanmedian(pf["total"]))})
        res["loso"][held] = {"group": meta.get(held), "n": len(rows),
                             "rate_median": st.median([r["flag_rate"] for r in rows]) if rows else None}
        res.setdefault("pose_rows", []).extend(rows)

    # A. 움직임 회귀보정 (LOSO, 시행 단위)
    a_rows = []
    for held in sessions:
        ref = [c for k2, d in res["units"].items() if k2.split("|")[0] != held for c in d["current"]]
        tgt = [c for k2, d in res["units"].items() if k2.split("|")[0] == held for c in d["current"]]
        if len(ref) < 5 or not tgt:
            continue
        xr = np.array([c["tam"] for c in ref]); yr = np.array([c["flag_rate"] for c in ref])
        coef = np.polyfit(xr, yr, 1)
        resid_all = yr - np.polyval(coef, xr)
        mad = float(np.median(np.abs(resid_all - np.median(resid_all)))) or 1e-9
        for c in tgt:
            pred = float(np.polyval(coef, c["tam"]))
            r = c["flag_rate"] - pred
            a_rows.append({"session": held, "hand": None, "trial": c["trial"],
                           "flag_rate": c["flag_rate"], "tam": c["tam"],
                           "expected": pred, "residual": r, "z": r / (1.4826 * mad),
                           "gate_flag": abs(r) > 3 * 1.4826 * mad})
    res["A_rows"] = a_rows

    # ── 요약 ──
    def group_mean(rows, key="flag_rate"):
        byg = {}
        for r in rows:
            g = meta.get(r.get("session") or r.get("_s"))
            byg.setdefault(g, []).append(r[key])
        return {g: (st.mean(v) if v else None) for g, v in byg.items()}

    cur_rows = [{"session": k2.split("|")[0], "_s": k2.split("|")[0],
                 "flag_rate": c["flag_rate"], "tam": c["tam"]}
                for k2, d in res["units"].items() for c in d["current"]]
    pose_rows = res.get("pose_rows", [])
    summ = {
        "현행": {"r_trial_amp": pearson([r["tam"] for r in cur_rows], [r["flag_rate"] for r in cur_rows]),
                 "group_mean": group_mean(cur_rows),
                 "rate_median": st.median([r["flag_rate"] for r in cur_rows]),
                 "n": len(cur_rows)},
        "A_회귀보정": {"r_trial_amp": pearson([r["tam"] for r in a_rows], [r["residual"] for r in a_rows]) if len(a_rows) > 3 else None,
                       "n_gate_flagged": sum(1 for r in a_rows if r["gate_flag"]), "n": len(a_rows),
                       "note": "잔차의 운동량 상관이 0에 가까워야 함. gate_flag = |z|>3"},
        "B_자세조건화": {"r_trial_amp": pearson([r["tam"] for r in pose_rows], [r["flag_rate"] for r in pose_rows]) if len(pose_rows) > 3 else None,
                         "group_mean": group_mean(pose_rows),
                         "rate_median": st.median([r["flag_rate"] for r in pose_rows]) if pose_rows else None,
                         "n": len(pose_rows),
                         "n_trials_flagged_any": sum(1 for r in pose_rows if r["flag_rate"] > 0)},
        "C_진단값강등": {"note": "분절 규칙을 게이트에서 제거 → flag_rate 정의 없음(0). 게이트는 추적률·갭·손-일관성만.",
                         "r_trial_amp": None,
                         "gate_only_amplitude_dependence": "게이트가 운동량에 의존하지 않아야 함(추적률·갭은 운동량과 무관)"},
    }
    # C: 분절 규칙 제거 게이트
    c_rows = []
    for (s_, hand), pfs in unit.items():
        for pf in pfs:
            q = rule_C_trial(pf)
            c_rows.append({"session": s_, "hand": hand, "trial": pf["_name"],
                           "pass": q["pass"], "reasons": q["reasons"],
                           "track_ratio": q["track_ratio"],
                           "tam": float(np.nanmedian(pf["total"]))})
    res["C_rows"] = c_rows
    byg = {}
    for r in c_rows:
        byg.setdefault(meta.get(r["session"]), []).append(1.0 if r["pass"] else 0.0)
    summ["C_진단값강등"]["group_pass_rate"] = {g: (st.mean(v) if v else None) for g, v in byg.items()}
    summ["C_진단값강등"]["pass_rate"] = st.mean([1.0 if r["pass"] else 0.0 for r in c_rows]) if c_rows else None
    summ["C_진단값강등"]["n"] = len(c_rows)
    summ["C_진단값강등"]["reason_counts"] = {
        k: sum(1 for r in c_rows if k in r["reasons"])
        for k in ("low_tracking", "gap_over_5x_dt_ref", "insufficient_frames")}

    # 옵션별 cap 30% 게이트 통과율 (집단별) — 실제 게이트 결과
    def cap_pass(rows, key="flag_rate", cap=0.30):
        out_ = {}
        for r in rows:
            g = meta.get(r.get("session") or r.get("_s"))
            out_.setdefault(g, []).append(1.0 if r[key] <= cap else 0.0)
        return {g: (st.mean(v) if v else None) for g, v in out_.items()}
    summ["현행"]["gate_pass_at_30pct"] = cap_pass(cur_rows)
    summ["B_자세조건화"]["gate_pass_at_30pct"] = cap_pass(pose_rows)
    res["summary"] = summ

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2, default=str))

    print("=" * 92)
    print("§8.2 분절 규칙 재정의 3안 비교 — 전부 Task1(자유 개폐), LOSO 적합")
    print("=" * 92)
    print("단위별 현행 불일치율 (세션×손):")
    for k, v in res["units"].items():
        s, h = k.split("|")
        print("  %-46s %-6s group=%-8s 시행 %d  불일치율 중앙 %.3f" % (
            s[:44], h, v["group"], v["n_trials"], v["current_rate_median"] or -1))
    print()
    print("안별 요약")
    print("  %-14s %18s %10s %s" % ("안", "운동량 상관 r", "지표", "집단별"))
    for name in ("현행", "A_회귀보정", "B_자세조건화", "C_진단값강등"):
        s = summ[name]
        gm = s.get("group_mean") or s.get("group_pass_rate") or {}
        hs = ["%s=%.3f" % (str(g)[:8], v) for g, v in gm.items() if v is not None]
        print("  %-14s %18s %10s %14s %s" % (
            name, ("%.3f" % s["r_trial_amp"]) if s.get("r_trial_amp") is not None else "-",
            ("%.3f" % s["rate_median"]) if s.get("rate_median") is not None else "-",
            " ".join(hs), s.get("note", "")))
    print()
    print("  A: 잔차 상관이 0에 가까우면 '운동량 교란 제거' 성공. 게이트 발동 %d/%d 시행" % (
        summ["A_회귀보정"]["n_gate_flagged"], summ["A_회귀보정"]["n"]))
    print("  B: 자세 조건화 후에도 상관이 남으면 자세만으로는 부족")
    print("  C: 분절 규칙 제거 → 통과율 %.3f, 사유 %s" % (
        summ["C_진단값강등"].get("pass_rate") or -1, summ["C_진단값강등"].get("reason_counts")))
    print()
    print("JSON →", OUT)


if __name__ == "__main__":
    main()

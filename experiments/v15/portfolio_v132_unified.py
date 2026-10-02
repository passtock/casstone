# -*- coding: utf-8 -*-
"""v13.2 지표 기준 · 통일 시간축 · 집단/손 분리 포트폴리오 (신규 파일).

기존 `experiments/analysis/metric_portfolio_check_v2.py` 를 **수정하지 않고** 대체한다.
그 스크립트의 문제(독립 검토보고서 + 30차 확인):
  · 집단 필터 없음 → 비장애/환자를 섞어 반복성을 계산
  · 앱 요약의 속도 계열을 그대로 사용 → 비장애 16/16 이 2,000도/초 초과(평균 2.5e9), 시간축 중복 7~21쌍
  · 41개 구 지표(예: `TAM_total` = 관절별 ROM 합)를 다룸 → **현 주 입력이 아님**
  · 반복시행 SD를 "임상 MDC"라 부름 → 실제 수행 변동 포함

이 스크립트가 하는 일
  · 시간축을 `capture_monotonic_s`(거리비교 CSV) 하나로 통일
  · 지표를 **현 v13.2 정의**로 원자료에서 직접 재계산
      M1 `D_TI_max`   : MP world landmark 4–8 거리 최댓값(mm)
      M2 `F_sum14`    : 14개 굴곡각 합의 P95(deg)
      M4 `SPARC_*`    : 각도 시계열 평활도(참조 구현)  ※ v13.2 의 SPARC_task(Pose 손목 3D 속력)는
                        환자 세션에 Pose 자체가 없어 산출 불가 → 각도계열 대체값을 병기
      `duration_s`    : 단조 시간 기준 관찰 길이
  · **집단(Healthy/Patient) × 손(환측/비환측) 분리**. 집단 검정·치료효과 추론 없음.
  · 이름을 **반복시행 변동성 비율**(1.96√2·SD/|mean| ×100)로 쓴다 — "MDC"라고 부르지 않는다.

출력: experiments/results/v15_portfolio_v132_unified.json
"""
from __future__ import annotations
import csv, glob, io, json, math, os, statistics as st, sys
import numpy as np

sys.path.insert(0, os.path.abspath("experiments/metrics"))
from sparc_ref import sparc  # noqa: E402

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/v15_portfolio_v132_unified.json"

FLEX14 = {"Thumb_CMC": (0, 1, 2), "Thumb_MCP": (1, 2, 3),
          "Index_MCP": (0, 5, 6), "Index_PIP": (5, 6, 7), "Index_DIP": (6, 7, 8),
          "Middle_MCP": (0, 9, 10), "Middle_PIP": (9, 10, 11), "Middle_DIP": (10, 11, 12),
          "Ring_MCP": (0, 13, 14), "Ring_PIP": (13, 14, 15), "Ring_DIP": (14, 15, 16),
          "Pinky_MCP": (0, 17, 18), "Pinky_PIP": (17, 18, 19), "Pinky_DIP": (18, 19, 20)}
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


def session_meta(sd):
    m = glob.glob(os.path.join(sd, "*_metadata.json"))
    if not m:
        return {}
    j = json.load(io.open(m[0], encoding="utf-8-sig"))
    s, v = j.get("subject", {}), j.get("video", {})
    return {"group": s.get("group"), "age": s.get("age"), "affected": s.get("affected_side"),
            "meta_fps": v.get("actual_fps"), "meta_frames": v.get("frames_written")}


def trial_metrics(sd, hand):
    """시행별 v13.2 지표를 원자료에서 계산. 시간축 = capture_monotonic_s."""
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
                try:
                    by.setdefault(fid, {})[lid] = (f(r.get("MP_X_m")), f(r.get("MP_Y_m")), f(r.get("MP_Z_m")))
                except TypeError:
                    pass
        if len(by) < 20:
            continue
        fids = sorted(by)
        n = len(fids)
        P = np.full((n, 21, 3), np.nan)
        t = np.full(n, np.nan)
        for i, fid in enumerate(fids):
            for lid, xyz in by[fid].items():
                if 0 <= lid <= 20 and all(v is not None for v in xyz):
                    P[i, lid] = xyz
            tv = mono.get(fid)
            if tv is not None:
                t[i] = tv
        # --- M1 D_TI_max (MP 4–8 거리 최댓값, mm) ---
        dTI = np.linalg.norm(P[:, THUMB_TIP] - P[:, INDEX_TIP], axis=-1) * 1000.0
        m1 = float(np.nanmax(dTI)) if np.isfinite(dTI).any() else None
        # --- M2 F_sum14 (14각 합의 P95) ---
        ang = np.full((n, 14), np.nan)
        for j, (_, (i1, i2, i3)) in enumerate(FLEX14.items()):
            for fr in range(n):
                ang[fr, j] = 180.0 - interior(P[fr, i1], P[fr, i2], P[fr, i3])
        comp = np.isfinite(ang).all(axis=1)
        tot = np.full(n, np.nan)
        tot[comp] = ang[comp].sum(axis=1)
        m2 = float(np.nanpercentile(tot, 95)) if comp.sum() >= 8 else None
        # --- 시간축 확인 ---
        tv = t[np.isfinite(t)]
        med_dt = float(np.median(np.diff(np.sort(tv)))) if tv.size > 2 else None
        n_nonpos = int((np.diff(tv) <= 0).sum()) if tv.size > 1 else 0
        # --- M4 대체: Index_PIP 각도계열 SPARC (단조 시간 균일격자) ---
        sp = None
        sp_status = "no_signal"
        ip = ang[:, list(FLEX14.keys()).index("Index_PIP")]
        ok = np.isfinite(t) & np.isfinite(ip)
        if ok.sum() >= 20 and med_dt:
            tt, aa = t[ok], ip[ok]
            o = np.argsort(tt, kind="stable")
            tt, aa = tt[o], aa[o]
            keep = np.concatenate(([True], np.diff(tt) > 0))
            tt, aa = tt[keep], aa[keep]
            span = float(tt[-1] - tt[0])
            if span > 0 and tt.size >= 20:
                grid = np.linspace(0.0, span, int(math.floor(span / med_dt)) + 1)
                if grid.size >= 20:
                    ag = np.interp(grid, tt - tt[0], aa)
                    speed = np.abs(np.gradient(ag, grid))
                    fs = (grid.size - 1) / span
                    sp = sparc(speed, grid, fc=min(10.0, fs / 2.0))
                    sp_status = "ok" if sp is not None else "undefined"
        dur = float(t[-1] - t[0]) if (np.isfinite(t).sum() > 1 and np.nanmax(t) > np.nanmin(t)) else None
        out.append({"trial": os.path.basename(os.path.dirname(lf)), "n_frames": n,
                    "D_TI_max_mm": m1, "F_sum14_p95_deg": m2,
                    "SPARC_indexPIP": sp, "sparc_status": sp_status,
                    "duration_s": dur, "median_dt_s": med_dt, "n_nonpos_dt": n_nonpos})
    return out


def ratio(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return None
    m = st.mean(v)
    if abs(m) < 1e-9:
        return None
    return 1.96 * math.sqrt(2) * st.stdev(v) / abs(m) * 100.0


def main():
    sessions = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))]
    res = {"provenance": {
        "time_axis": "capture_monotonic_s (distance_comparison.csv) — 단일 정본",
        "metrics": "v13.2 정의를 원자료에서 재계산. SPARC_task(Pose 손목 3D)는 환자 Pose 부재로 불가 "
                   "→ Index_PIP 각도계열 SPARC 로 대체 표기",
        "naming": "1.96√2·SD/|mean| 는 '반복시행 변동성 비율'. 임상 MDC 아님.",
        "stats": "집단 검정·치료효과 추론 없음. 시행 수준 기술통계만.",
        "replaces": "experiments/analysis/metric_portfolio_check_v2.py (수정 없이 대체)",
    }, "sessions": {}}

    keymap = {"D_TI_max_mm": "M1_D_TI_max", "F_sum14_p95_deg": "M2_F_sum14",
              "SPARC_indexPIP": "M4_SPARC(대체)", "duration_s": "duration"}
    pool = {}
    for d in sessions:
        sd = os.path.join(ROOT, d)
        meta = session_meta(sd)
        rec = {"meta": meta, "hands": {}}
        for hand in ("Left", "Right"):
            rows = trial_metrics(sd, hand)
            if not rows:
                continue
            side = ("affected" if meta.get("affected") and hand in str(meta["affected"])
                    else "unaffected" if meta.get("affected") else "control")
            rec["hands"][hand] = {"side_role": side, "n_trials": len(rows), "trials": rows,
                                  "ratios": {k: ratio([r[kk] for r in rows]) for kk, k in keymap.items()},
                                  "medians": {k: (st.median([r[kk] for r in rows if r[kk] is not None])
                                                  if any(r[kk] is not None for r in rows) else None)
                                              for kk, k in keymap.items()}}
            gk = ("Patient" if meta.get("group") == "Patient" else "Healthy")
            pool.setdefault((gk, side), []).extend(
                [{k: r[kk] for kk, k in keymap.items()} for r in rows])
        res["sessions"][d] = rec

    res["pooled_ratios"] = {("%s|%s" % k): {kk: ratio([x[kk] for x in v]) for kk in keymap.values()}
                            for k, v in sorted(pool.items(), key=str)}
    res["pooled_n"] = {("%s|%s" % k): len(v) for k, v in sorted(pool.items(), key=str)}

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2, default=str))

    print("=" * 100)
    print("v13.2 지표 · 통일 시간축 · 집단×손 분리 포트폴리오")
    print("=" * 100)
    print("%-40s %-6s %-11s %5s %9s %11s %10s %8s" % (
        "세션", "손", "역할", "시행", "fps(mono)", "M1 D_TI(mm)", "M2 F_sum14", "M4 SPARC"))
    for d, rec in res["sessions"].items():
        for hand, h in rec["hands"].items():
            fps = 1.0 / h["medians"]["duration"] if False else None
            mdt = st.median([r["median_dt_s"] for r in h["trials"] if r["median_dt_s"]])
            print("%-40s %-6s %-11s %5d %9.2f %11s %10s %8s" % (
                d[:38], hand, h["side_role"], h["n_trials"], 1.0 / mdt if mdt else -1,
                ("%.1f" % h["medians"]["M1_D_TI_max"]) if h["medians"]["M1_D_TI_max"] else "-",
                ("%.1f" % h["medians"]["M2_F_sum14"]) if h["medians"]["M2_F_sum14"] else "-",
                ("%.2f" % h["medians"]["M4_SPARC(대체)"]) if h["medians"]["M4_SPARC(대체)"] else "-"))
    print()
    print("반복시행 변동성 비율 % (집단|손역할, n=시행 수):")
    for k, v in res["pooled_ratios"].items():
        print("  %-18s n=%-3s M1 %8s / M2 %8s / M4 %8s" % (
            k, res["pooled_n"][k],
            ("%.1f" % v["M1_D_TI_max"]) if v["M1_D_TI_max"] else "-",
            ("%.1f" % v["M2_F_sum14"]) if v["M2_F_sum14"] else "-",
            ("%.1f" % v["M4_SPARC(대체)"]) if v["M4_SPARC(대체)"] else "-"))
    print()
    print("※ 50% 기준은 참고일 뿐 판정 기준이 아니다(임상 MDC 아님).")
    print("JSON →", OUT)


if __name__ == "__main__":
    main()

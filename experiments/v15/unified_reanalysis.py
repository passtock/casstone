# -*- coding: utf-8 -*-
"""통일 시간축 재분석 (독립 검토보고서 우선순위 #1·#2).

배경: 27~29차 감사에서 쓴 시간축이 세션마다 달랐고, 앱 요약의 속도 열에는 중복 시각 때문에
      비현실적 값(비장애 16/16 이 2,000도/초 초과, 평균 2.5e9)이 들어 있었다.
      독립 검토보고서가 이를 지적했고, 이 스크립트는 **capture_monotonic_s 를 정본 시간축**으로
      삼아 세션 전체를 같은 방법으로 다시 계산한다.

원칙
  · 원자료 수정 없음. 출력은 새 경로에만.
  · 앱 요약의 속도 계열(Flex_Speed_deg_s, Ext_Speed_deg_s)은 **사용하지 않는다**(시간축 결함).
  · 집단 간 검정·치료효과 추론을 하지 않는다. **시행 수준 기술통계만** 낸다.
  · 환측을 명시한다(환자 affected_side = 좌측).

출력: experiments/results/v15_unified_reanalysis.json
"""
from __future__ import annotations
import csv, glob, io, json, math, os, statistics as st, sys
import numpy as np

sys.path.insert(0, os.path.abspath("experiments/metrics"))
from sparc_ref import sparc  # noqa: E402

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/v15_unified_reanalysis.json"


def read_csv(p):
    with io.open(p, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def session_meta(sd):
    m = glob.glob(os.path.join(sd, "*_metadata.json"))
    if not m:
        return {}
    j = json.load(io.open(m[0], encoding="utf-8-sig"))
    s, v = j.get("subject", {}), j.get("video", {})
    return {"group": s.get("group"), "age": s.get("age"), "affected": s.get("affected_side"),
            "meta_fps": v.get("actual_fps"), "frames_written": v.get("frames_written")}


def trial_signal(sd, hand):
    """시행별 (Frame_ID, capture_monotonic_s, Index_PIP_filt) 을 **Frame_ID 로 결합**."""
    out = []
    for cf in sorted(glob.glob(os.path.join(sd, "split", "*", "Trial_*", "*_continuous_raw.csv"))):
        df = cf.replace("_continuous_raw.csv", "_distance_comparison.csv")
        if not os.path.exists(df):
            continue
        mono = {}
        for r in read_csv(df):
            if (r.get("Hand") or "") != hand:
                continue
            fid = f(r.get("Frame_ID"))
            t = f(r.get("capture_monotonic_s"))
            if fid is not None and t is not None:
                mono[int(fid)] = t
        rec = []
        for r in read_csv(cf):
            if (r.get("hand") or "") != hand:
                continue
            fid = f(r.get("Frame_ID"))
            a = f(r.get("Index_PIP_filt"))
            if fid is None or a is None:
                continue
            t = mono.get(int(fid))
            if t is None:
                continue
            rec.append((int(fid), t, a))
        if len(rec) < 20:
            continue
        rec.sort()
        out.append({"trial": os.path.basename(os.path.dirname(cf)),
                    "fid": np.array([x[0] for x in rec]),
                    "t": np.array([x[1] for x in rec]),
                    "ang": np.array([x[2] for x in rec])})
    return out


def summarize_signal(tr):
    """단조 시간 기준 dt·속도·SPARC. 균일 격자 변환은 중앙 dt 사용."""
    t, a = tr["t"], tr["ang"]
    dt = np.diff(t)
    n_nonpos = int((dt <= 0).sum())
    good = dt > 0
    dt_pos = dt[good]
    med_dt = float(np.median(dt_pos)) if dt_pos.size else None
    # 중복 시각 제거(최초 기록만)
    keep = np.concatenate(([True], np.diff(t) > 0))
    t2, a2 = t[keep], a[keep]
    res = {"trial": tr["trial"], "n_frames": int(len(t)), "n_nonpos_dt": n_nonpos,
           "median_dt_s": med_dt, "fps_from_mono": (1.0 / med_dt) if med_dt else None}
    if len(t2) < 20 or med_dt is None:
        res.update({"vmax_dps": None, "v_p95_dps": None, "sparc": None, "sparc_status": "too_short"})
        return res
    dt2 = np.diff(t2)
    if np.any(dt2 <= 0):
        res.update({"vmax_dps": None, "v_p95_dps": None, "sparc": None, "sparc_status": "nonmonotonic"})
        return res
    v = np.abs(np.diff(a2) / dt2)
    res["vmax_dps"] = float(np.max(v))
    res["v_p95_dps"] = float(np.percentile(v, 95))
    # SPARC: 중앙 dt 균일 격자
    span = float(t2[-1] - t2[0])
    n = int(math.floor(span / med_dt)) + 1
    if n < 20:
        res.update({"sparc": None, "sparc_status": "grid_too_short"})
        return res
    grid = np.linspace(0.0, span, n)
    ag = np.interp(grid, t2 - t2[0], a2)
    speed = np.abs(np.gradient(ag, grid))
    fs = (n - 1) / span
    sv = sparc(speed, grid, fc=min(10.0, fs / 2.0))
    res["sparc"] = sv
    res["sparc_status"] = "ok" if sv is not None else "undefined"
    res["sparc_fs"] = fs
    return res


def main():
    out = {"provenance": {
        "time_axis": "capture_monotonic_s (distance_comparison.csv), Frame_ID·Hand 로 결합",
        "excluded_columns": ["Flex_Speed_deg_s", "Ext_Speed_deg_s",
                             "Duration_s", "Valid_Duration_s", "Cycle_Period_s"],
        "note": "앱 요약 속도열은 중복 시각 때문에 사용 불가(비장애 16/16 이 2,000도/초 초과). "
                "집단 검정·치료효과 추론 없음. 시행 수준 기술통계만."},
        "sessions": {}}

    for d in sorted(os.listdir(ROOT)):
        sd = os.path.join(ROOT, d)
        if not os.path.isdir(sd):
            continue
        meta = session_meta(sd)
        rec = {"meta": meta, "hands": {}}
        for hand in ("Left", "Right"):
            trs = trial_signal(sd, hand)
            rows = [summarize_signal(tr) for tr in trs]
            if not rows:
                continue
            def med(key):
                v = [r[key] for r in rows if r.get(key) is not None]
                return st.median(v) if v else None
            rec["hands"][hand] = {
                "side_role": ("affected" if meta.get("affected") and hand in str(meta["affected"])
                              else "unaffected" if meta.get("affected") else "n/a"),
                "n_trials": len(rows), "trials": rows,
                "median_fps_from_mono": med("fps_from_mono"),
                "median_vmax_dps": med("vmax_dps"),
                "median_v_p95_dps": med("v_p95_dps"),
                "median_sparc": med("sparc"),
                "n_nonpos_dt_total": sum(r["n_nonpos_dt"] for r in rows),
            }
        out["sessions"][d] = rec

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    print("=" * 96)
    print("통일 시간축 재분석 — capture_monotonic_s 기준 (앱 요약 속도열 사용 안 함)")
    print("=" * 96)
    print("%-44s %-6s %-10s %6s %8s %10s %9s %9s" % (
        "세션", "손", "역할", "시행", "fps(mono)", "Vmax(°/s)", "P95(°/s)", "SPARC"))
    for d, rec in out["sessions"].items():
        for hand, h in rec["hands"].items():
            print("%-44s %-6s %-10s %6d %8s %10s %9s %9s" % (
                d[:42], hand, h["side_role"], h["n_trials"],
                ("%.2f" % h["median_fps_from_mono"]) if h["median_fps_from_mono"] else "-",
                ("%.1f" % h["median_vmax_dps"]) if h["median_vmax_dps"] else "-",
                ("%.1f" % h["median_v_p95_dps"]) if h["median_v_p95_dps"] else "-",
                ("%.2f" % h["median_sparc"]) if h["median_sparc"] else "-"))
    print()
    print("  중복/비양수 시간차 합계(시행 전체 합):")
    for d, rec in out["sessions"].items():
        print("    %-46s %s" % (d[:44], {h: rec["hands"][h]["n_nonpos_dt_total"]
                                         for h in rec["hands"]}))
    print()
    print("JSON →", OUT)


if __name__ == "__main__":
    main()

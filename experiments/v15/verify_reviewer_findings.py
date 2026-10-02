# -*- coding: utf-8 -*-
"""독립 검토보고서(2026-10-02)가 지적한 잔여 항목을 원자료로 검증한다.

검증 항목
  1. `L2_metric/*.json` 의 SPARC·m1 이 앱 요약과 다른가 (리뷰: Trial1 Left L2 −7.5986 vs 앱 −5.929)
  2. `MGA_mm_3D_cal` 결측률 (리뷰: 48행 전부 결측)
  3. `RS_Valid_Rate` 의 세션×손 차이 (리뷰: 비장애 0.445/0.215, 미사 0.492/0.207, 애프터 0.419/0.919)
  4. 환자 전체 기록 프레임 (리뷰: 미사 33,038 / 애프터 1,031)
  5. 요약 스키마 차이 (리뷰: 환자에만 Time_Base·Dt_Dropped·Segments·p95 속도)
  6. 분할 CSV 정합성 (리뷰: 96개 대조 불일치 0)
  7. 깊이 기반 랜드마크 `ok` 비율 (리뷰: 32.38 / 63.10 / 78.58 %)
  8. MP world mm vs RS mm vs 보정 mm 의 구분

원자료 수정 없음. 출력은 새 경로에만.
출력: experiments/results/v15_reviewer_findings.json
"""
from __future__ import annotations
import csv, glob, io, json, math, os, statistics as st

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUT = "experiments/results/v15_reviewer_findings.json"


def rd(p):
    with io.open(p, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def main():
    R = {"checks": {}, "sessions": {}}
    sessions = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))]

    for d in sessions:
        sd = os.path.join(ROOT, d)
        rec = {}
        m = glob.glob(os.path.join(sd, "*_metadata.json"))
        if m:
            j = json.load(io.open(m[0], encoding="utf-8-sig"))
            rec["meta_frames_written"] = j.get("video", {}).get("frames_written")
            rec["meta_fps"] = j.get("video", {}).get("actual_fps")
            rec["affected_side"] = j.get("subject", {}).get("affected_side")

        # 앱 손 랜드마크 파일(pose_landmarks.csv 배제)
        lm = [x for x in glob.glob(os.path.join(sd, "*_landmarks.csv"))
              if "pose_landmarks" not in os.path.basename(x)]
        if lm:
            rows = rd(lm[0]) if False else None
            n_rows, fids, status = 0, set(), {}
            with io.open(lm[0], encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    n_rows += 1
                    fids.add(int(float(r["Frame_ID"])))
                    s = (r.get("RS_Status") or "").strip()
                    status[s] = status.get(s, 0) + 1
            rec["app_landmarks_file"] = os.path.basename(lm[0])
            rec["app_landmarks_rows"] = n_rows
            rec["app_landmarks_frames"] = len(fids)
            tot = sum(status.values())
            rec["rs_status_ok_pct"] = round(100.0 * status.get("ok", 0) / tot, 2) if tot else None
            rec["rs_status_top"] = sorted(status.items(), key=lambda kv: -kv[1])[:5]

        # 요약 스키마·결측률
        ts = glob.glob(os.path.join(sd, "*_trials_summary.csv"))
        if ts:
            rows = rd(ts[0])
            rec["summary_n_rows"] = len(rows)
            rec["summary_n_cols"] = len(rows[0]) if rows else 0
            rec["summary_cols_extra_vs_58"] = sorted(set(rows[0]) - set()) if rows else []
            cal = [r.get("MGA_mm_3D_cal") for r in rows]
            rec["MGA_mm_3D_cal_missing"] = sum(1 for x in cal if f(x) is None)
            rec["MGA_mm_3D_cal_n"] = len(cal)
            for col in ("RS_Valid_Rate", "MP_MGA_raw_mm", "MGA_mm_3D", "SPARC", "TAM_total_deg",
                        "Flex_Speed_deg_s"):
                if col in (rows[0] if rows else {}):
                    by = {}
                    for r in rows:
                        by.setdefault(r.get("Hand"), []).append(f(r.get(col)))
                    rec["median_%s_by_hand" % col] = {
                        h: (round(st.median([x for x in v if x is not None]), 4)
                            if any(x is not None for x in v) else None)
                        for h, v in by.items()}
            rec["has_Time_Base"] = "Time_Base" in (rows[0] if rows else {})
            rec["has_Flex_Speed_p95"] = "Flex_Speed_p95_deg_s" in (rows[0] if rows else {})

        # 분할 CSV 정합성: 세션 요약 행수 vs 분할 시행 요약 행수 합
        sp = os.path.join(sd, "split")
        if os.path.isdir(sp):
            srows = 0
            for x in glob.glob(os.path.join(sp, "*", "Trial_*", "*_trials_summary.csv")):
                srows += len(rd(x))
            rec["split_summary_rows_sum"] = srows
            n_lm = len(glob.glob(os.path.join(sp, "*", "Trial_*", "*_landmarks.csv")))
            rec["split_landmark_files"] = n_lm

        # L2_metric
        l2d = os.path.join(sd, "L2_metric")
        if os.path.isdir(l2d):
            js = sorted(glob.glob(os.path.join(l2d, "*.json")))
            pairs = []
            tam = {}
            if ts:
                for r in rd(ts[0]):
                    try:
                        tam[(r["Hand"], int(str(r["Trial"]).replace("Trial #", "").strip()))] = r
                    except ValueError:
                        pass
            for p in js:
                j = json.load(io.open(p, encoding="utf-8-sig"))
                key = (j.get("hand"), int(str(j.get("trial")).replace("Trial_", "")))
                ar = tam.get(key)
                pairs.append({
                    "id": j.get("trial_id"),
                    "l2_sparc": j.get("m4_sparc"), "app_sparc": (j.get("q") or {}).get("app_sparc"),
                    "l2_m1_mga_mm": j.get("m1_mga_mm"),
                    "app_MP_MGA_raw_mm": f(ar.get("MP_MGA_raw_mm")) if ar else None,
                    "app_MGA_mm_3D": f(ar.get("MGA_mm_3D")) if ar else None,
                    "l2_m2_tam_deg": j.get("m2_tam_total_deg"),
                    "app_TAM_total_deg": f(ar.get("TAM_total_deg")) if ar else None,
                })
            diff_sp = [x for x in pairs if x["l2_sparc"] is not None and x["app_sparc"] is not None
                       and abs(x["l2_sparc"] - x["app_sparc"]) > 1e-6]
            rec["L2_n"] = len(pairs)
            rec["L2_sparc_differs_from_app"] = len(diff_sp)
            rec["L2_examples"] = pairs[:3]
        R["sessions"][d] = rec

    # 스키마 비교(집단)
    healthy = [d for d in sessions if (R["sessions"][d].get("affected_side") is None)]
    patient = [d for d in sessions if R["sessions"][d].get("affected_side")]
    R["checks"]["schema"] = {
        "healthy_cols": [R["sessions"][d]["summary_n_cols"] for d in healthy],
        "patient_cols": [R["sessions"][d]["summary_n_cols"] for d in patient],
        "patient_only_cols": sorted(
            set(rd(glob.glob(os.path.join(ROOT, patient[0], "*_trials_summary.csv"))[0])[0])
            - set(rd(glob.glob(os.path.join(ROOT, healthy[0], "*_trials_summary.csv"))[0])[0])) if (healthy and patient) else [],
    }

    res = {}
    for d in sessions:
        r = R["sessions"][d]
        res[d] = {
            "meta_frames_written": r.get("meta_frames_written"),
            "affected": r.get("affected_side"),
            "app_landmarks_frames": r.get("app_landmarks_frames"),
            "app_landmarks_rows": r.get("app_landmarks_rows"),
            "rs_status_ok_pct": r.get("rs_status_ok_pct"),
            "summary_n_rows": r.get("summary_n_rows"), "summary_n_cols": r.get("summary_n_cols"),
            "MGA_mm_3D_cal_missing": "%s/%s" % (r.get("MGA_mm_3D_cal_missing"), r.get("MGA_mm_3D_cal_n")),
            "median_RS_Valid_Rate_by_hand": r.get("median_RS_Valid_Rate_by_hand"),
            "median_Flex_Speed_by_hand": r.get("median_Flex_Speed_deg_s_by_hand"),
            "has_Time_Base": r.get("has_Time_Base"), "has_Flex_Speed_p95": r.get("has_Flex_Speed_p95"),
            "split_summary_rows_sum": r.get("split_summary_rows_sum"),
            "split_landmark_files": r.get("split_landmark_files"),
            "L2_n": r.get("L2_n"), "L2_sparc_differs_from_app": r.get("L2_sparc_differs_from_app"),
        }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps({"by_session": res, "detail": R}, ensure_ascii=False, indent=2, default=str))

    print("=" * 104)
    print("검토보고서 잔여 지적 항목 검증")
    print("=" * 104)
    print("%-40s %10s %9s %9s %10s %9s" % ("세션", "meta프레임", "앱손프레임", "RS_ok%", "요약행/열", "cal결측"))
    for d, v in res.items():
        print("%-40s %10s %9s %9s %10s %9s" % (
            d[:38], v["meta_frames_written"], v["app_landmarks_frames"], v["rs_status_ok_pct"],
            "%s/%s" % (v["summary_n_rows"], v["summary_n_cols"]), v["MGA_mm_3D_cal_missing"]))
    print()
    print("RS_Valid_Rate 중앙(손별):")
    for d, v in res.items():
        print("  %-42s %s" % (d[:40], v["median_RS_Valid_Rate_by_hand"]))
    print()
    print("Flex_Speed_deg_s 중앙(손별) — 비장애만 폭주:")
    for d, v in res.items():
        print("  %-42s %s" % (d[:40], v["median_Flex_Speed_by_hand"]))
    print()
    print("환자 전용 요약 열:", R["checks"]["schema"]["patient_only_cols"])
    print()
    print("L2_metric vs 앱 요약:")
    for d, v in res.items():
        if v["L2_n"]:
            print("  %-42s L2 %d개, SPARC 불일치 %s개" % (d[:40], v["L2_n"], v["L2_sparc_differs_from_app"]))
    print()
    print("L2 예시(애프터):", json.dumps(
        [x for d in sessions for x in (R["sessions"][d].get("L2_examples") or [])][:2],
        ensure_ascii=False))
    print()
    print("JSON →", OUT)


if __name__ == "__main__":
    main()

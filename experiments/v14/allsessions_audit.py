# -*- coding: utf-8 -*-
"""전체 세션 감사 (2026-10-02 사용자 요청: "데이터_저장 안 파일들 다 써서 해봐").

⚠️ 이 스크립트는 **기존 근거 파일을 덮어쓰지 않는다.** 출력은 새 경로에만 쓴다.
   (경위: `experiments/analysis/metric_portfolio_check_v2.py` 가 결과 파일에 직접 쓰는 바람에
    09-28 근거를 덮어썼고, git으로 복원한 사고가 있었다.)

수행:
  ① 세션 인벤토리(집단·과제·시행·fps)
  ② 지표 편입 조건 C1·C2·C3 — **집단별(Healthy / Stroke)로 분리 계산** (원 정의 그대로:
     그룹 = (세션,Task,Hand), MDC95 = 1.96·√2·SD, C2 = MDC/|mean| ≤50%, 판정 = 그룹별 MDC의 중앙값)
     + 참고로 전체 통합도 병기
  ③ 프레임 드롭 감사 (세션별)
  ④ v13 Q 규칙 실행 (세션×손, fallback = 진단용 기준선)

주의(전제): 이 데이터는 **전부 Task1 "맨손 쥐기 펴기"(자유 개폐)** 다.
  ARAT 3·12·18번 촬영이 아니고, §6.3.1 정지 2초 구간도 없다 → Q는 strict에서 평가 불가.
"""
from __future__ import annotations

import csv, glob, io, json, math, os, statistics as st, sys
from collections import defaultdict

ROOT = "capstone/호진파일/outputs/데이터_저장"
OUTJ = "experiments/results/v14_allsessions_audit.json"
sys.path.insert(0, os.path.abspath("experiments/v13"))
from qv13 import run_pilot, landmark_coverage  # noqa: E402

# ── 원 스크립트의 정의를 그대로 옮긴다 ────────────────────────────────
LIM = {"angle_max": 180.0, "finger_tam_max": 360.0, "tam5_max": 1500.0,
       "speed_max": 2000.0, "sparc_max": 0.0, "mga_min": 0.0, "mga_max": 250.0, "time_max": 120.0}
ANGLE = ["Index_ROM_deg", "Index_ROM_3D_deg", "RS_Index_ROM_deg",
         "Thumb_CMC_ROM_deg", "Thumb_PalmarAbd_max_deg", "Thumb_PalmarAbd_ROM_deg",
         "Thumb_RadialAbd_max_deg", "Thumb_RadialAbd_ROM_deg",
         "ROM_Thumb_CMC_deg", "ROM_Thumb_MCP_deg", "ROM_Thumb_IP_deg",
         "ROM_Index_MCP_deg", "ROM_Index_PIP_deg", "ROM_Index_DIP_deg",
         "ROM_Middle_MCP_deg", "ROM_Middle_PIP_deg", "ROM_Middle_DIP_deg",
         "ROM_Ring_MCP_deg", "ROM_Ring_PIP_deg", "ROM_Ring_DIP_deg",
         "ROM_Pinky_MCP_deg", "ROM_Pinky_PIP_deg", "ROM_Pinky_DIP_deg"]
FINGER_TAM = ["TAM_Thumb_deg", "TAM_Index_deg", "TAM_Middle_deg", "TAM_Ring_deg", "TAM_Pinky_deg"]
SPEED = ["Flex_Speed_deg_s", "Ext_Speed_deg_s"]
SPARC = ["SPARC"]
MGA = ["MGA_cm", "MGA_mm_3D", "MGA_mm_3D_cal", "MP_MGA_raw_mm", "RS_MGA_raw_mm", "RS_MGA_p95_mm"]
TIME = ["Duration_s", "Cycle_Period_s", "Valid_Duration_s"]
CANDIDATES = ANGLE + FINGER_TAM + ["TAM_total_deg"] + SPEED + SPARC + MGA + TIME


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def plausible(col, v):
    if v is None:
        return None
    if col == "TAM_total_deg":
        return 0.0 <= v <= LIM["tam5_max"]
    if col in FINGER_TAM:
        return 0.0 <= v <= LIM["finger_tam_max"]
    if col in ANGLE:
        return 0.0 <= v <= LIM["angle_max"]
    if col in SPEED:
        return 0.0 <= v <= LIM["speed_max"]
    if col in SPARC:
        return v <= LIM["sparc_max"]
    if col in MGA:
        return LIM["mga_min"] <= v <= LIM["mga_max"]
    if col in TIME:
        return 0.0 < v <= LIM["time_max"]
    return True


def mdc_ratio(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return None
    m = st.mean(v)
    if abs(m) < 1e-9:
        return None
    sd = st.stdev(v)
    return 1.96 * math.sqrt(2) * sd / abs(m) * 100.0


# ── ① 인벤토리 ────────────────────────────────────────────────────────
def inventory():
    inv = []
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        rec = {"session": d}
        m = glob.glob(os.path.join(p, "*_metadata.json"))
        if m:
            j = json.load(io.open(m[0], encoding="utf-8-sig"))
            s, pr, v = j.get("subject", {}), j.get("protocol", {}), j.get("video", {})
            rec.update({"group": s.get("group"), "name": s.get("name"), "age": s.get("age"),
                        "sex": s.get("gender"), "fma": s.get("fma_score"),
                        "brunnstrom": s.get("brunnstrom"), "affected": s.get("affected_side"),
                        "trial_mode": pr.get("trial_mode"), "total_trials": pr.get("total_trials"),
                        "session_dur_s": pr.get("session_duration_s"),
                        "actual_fps": v.get("actual_fps"), "frames_written": v.get("frames_written")})
        ts = glob.glob(os.path.join(p, "*_trials_summary.csv"))
        if ts:
            with io.open(ts[0], encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
            rec["n_trial_rows"] = len(rows)
            c = defaultdict(int)
            for r in rows:
                c[(r.get("Task"), r.get("Hand"))] += 1
            rec["trial_rows_by_task_hand"] = {"%s|%s" % k: v for k, v in sorted(c.items(), key=str)}
        lm = glob.glob(os.path.join(p, "*_landmarks.csv"))
        if lm:
            fids, hands = set(), set()
            with io.open(lm[0], encoding="utf-8-sig") as fh:
                rd = csv.DictReader(fh)
                cols = rd.fieldnames or []
                for r in rd:
                    fids.add(int(float(r["Frame_ID"])))
                    if "Hand" in r:
                        hands.add(r["Hand"])
            rec["landmark_cols_has_Hand"] = "Hand" in cols
            rec["n_unique_frames"] = len(fids)
            rec["hands"] = sorted(h for h in hands if h)
        sp = os.path.join(p, "split")
        if os.path.isdir(sp):
            rec["n_split_trials"] = len(glob.glob(os.path.join(sp, "*", "Trial_*")))
        inv.append(rec)
    return inv


# ── ② 지표 편입 조건 (집단별 / 통합) ───────────────────────────────────
def load_rows():
    rows = []
    for f in glob.glob(os.path.join(ROOT, "*", "*_trials_summary.csv")):
        if "/split/" in f.replace("\\", "/"):
            continue
        sess = os.path.basename(os.path.dirname(f))
        grp = None
        mm = glob.glob(os.path.join(os.path.dirname(f), "*_metadata.json"))
        if mm:
            try:
                grp = json.load(io.open(mm[0], encoding="utf-8-sig")).get("subject", {}).get("group")
            except Exception:
                pass
        with io.open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                r["_s"], r["_g"] = sess, grp
                rows.append(r)
    return rows


def portfolio(rows, label):
    """rows 를 (세션,Task,Hand) 그룹으로 묶어 지표별 C1·C2·C3 를 계산."""
    G = defaultdict(list)
    for r in rows:
        G[(r["_s"], r.get("Task", "?"), r.get("Hand", "?"))].append(r)
    n_tot = len(rows)
    res = []
    for col in CANDIDATES:
        allv, miss, viol = [], 0, 0
        for g in G.values():
            for r in g:
                v = fnum(r.get(col))
                if v is None:
                    miss += 1
                    continue
                if plausible(col, v) is False:
                    viol += 1
                allv.append(v)
        mdcs = [x for x in (mdc_ratio([fnum(r.get(col)) for r in g]) for g in G.values()) if x is not None]
        miss_rate = miss / n_tot * 100 if n_tot else None
        viol_rate = viol / len(allv) * 100 if allv else None
        mdc = st.median(mdcs) if mdcs else None
        ok1 = miss_rate is not None and miss_rate <= 20
        ok2 = mdc is not None and mdc <= 50
        ok3 = viol_rate is not None and viol_rate <= 5
        res.append({"metric": col, "n": len(allv), "n_groups": len(G),
                    "miss_pct": miss_rate, "mdc_pct": mdc, "viol_pct": viol_rate,
                    "verdict": "편입가능" if (ok1 and ok2 and ok3) else "조건미달",
                    "ok": [ok1, ok2, ok3]})
    return {"label": label, "n_rows": n_tot, "n_groups": len(G),
            "group_keys": ["|".join(map(str, k)) for k in sorted(G, key=str)], "metrics": res}


# ── ③ 프레임 드롭 ─────────────────────────────────────────────────────
def frame_drops(sess_dir, hand="Left"):
    out = []
    for f in sorted(glob.glob(os.path.join(sess_dir, "split", "*", "Trial_*", "*_landmarks.csv"))):
        seen = {}
        with io.open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if (r.get("Hand") or "").strip() != hand:
                    continue
                try:
                    fid = int(float(r["Frame_ID"]))
                except (KeyError, TypeError, ValueError):
                    continue
                if fid in seen:
                    continue
                try:
                    seen[fid] = float(r.get("time_s"))
                except (TypeError, ValueError):
                    seen[fid] = float("nan")
        if len(seen) < 20:
            continue
        fids = sorted(seen)
        ts = [seen[i] for i in fids]
        df = [fids[i + 1] - fids[i] for i in range(len(fids) - 1)]
        dt = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
        span = fids[-1] - fids[0] + 1
        miss = sum(max(d - 1, 0) for d in df)
        out.append({"trial": os.path.basename(os.path.dirname(f)), "n_frames": len(fids),
                    "missing_frames": miss, "missing_pct": 100.0 * miss / span,
                    "max_fid_jump": max(df) if df else 0,
                    "median_dt_s": st.median(dt) if dt else None,
                    "max_dt_s": max(dt) if dt else None,
                    "fps_median": (1.0 / st.median(dt)) if dt and st.median(dt) > 0 else None})
    return out


# ── ④ Q (v13 규칙) ────────────────────────────────────────────────────
def q_eval(sess_dir, hand, rest_mode="fallback"):
    try:
        r = run_pilot(sess_dir, hand=hand, rest_mode=rest_mode)
    except Exception as e:  # noqa: BLE001
        return {"error": "%s: %s" % (type(e).__name__, e)}
    recs = r["records"]
    return {"hand": hand, "rest_mode": rest_mode, "n_trials": len(recs),
            "q_hand_pass": sum(1 for x in recs if x["pass"]),
            "q_hand_reasons": dict((k, sum(1 for x in recs if k in x["reasons"]))
                                   for k in set(y for x in recs for y in x["reasons"])),
            "seg_rate_median": st.median([x["seg_rate"] for x in recs if x["seg_rate"] is not None])
            if any(x["seg_rate"] is not None for x in recs) else None,
            "session_dt_ref_s": r["session_dt_ref_s"],
            "hand_consistency_invalid_total": sum(x["hand_consistency_invalid"] for x in recs),
            "n_frames_total": sum(x["n_frames"] for x in recs)}


def main():
    out = {"generated": "2026-10-02", "root": ROOT}
    out["inventory"] = inventory()

    rows = load_rows()
    by_group = defaultdict(list)
    for r in rows:
        by_group[r["_g"] or "UNKNOWN"].append(r)
    out["portfolio_pooled"] = portfolio(rows, "전체 통합(참고)")
    out["portfolio_by_group"] = {g: portfolio(v, g) for g, v in sorted(by_group.items())}

    out["frame_drops"] = {}
    out["q_v13"] = {}
    for rec in out["inventory"]:
        d = os.path.join(ROOT, rec["session"])
        out["frame_drops"][rec["session"]] = frame_drops(d, hand="Left")
        out["q_v13"][rec["session"]] = {h: q_eval(d, h) for h in ("Left", "Right")}
    out["landmark_coverage"] = landmark_coverage()

    io.open(OUTJ, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    # 콘솔 요약
    print("=" * 96)
    print("① 세션 인벤토리")
    for r in out["inventory"]:
        print("  %-46s group=%-8s age=%-3s fps=%-6s 프레임=%-5s trials=%s split=%s" % (
            r["session"][:44], r.get("group"), r.get("age"), r.get("actual_fps"),
            r.get("n_unique_frames"), r.get("n_trial_rows"), r.get("n_split_trials")))
    print()
    print("② 지표 편입 조건 — 집단별 (C2 = MDC95/|mean| ≤50%)")
    for lbl, pf in list(out["portfolio_by_group"].items()) + [("POOLED", out["portfolio_pooled"])]:
        na = sum(1 for m in pf["metrics"] if m["verdict"] == "편입가능")
        print("  [%s] n=%d rows, %d groups → 편입가능 %d / %d 지표" % (
            lbl, pf["n_rows"], pf["n_groups"], na, len(pf["metrics"])))
    print()
    print("③ 프레임 드롭 (Left)")
    for s, dd in out["frame_drops"].items():
        if not dd:
            print("  %-46s (측정 불가)" % s[:44]); continue
        mp = [x["missing_pct"] for x in dd]
        print("  %-46s 시행 %d, 누락 %.1f%%(중앙), 최대 프레임점프 %d, fps %.1f" % (
            s[:44], len(dd), st.median(mp), max(x["max_fid_jump"] for x in dd),
            st.median([x["fps_median"] for x in dd if x["fps_median"]])))
    print()
    print("④ v13 Q 규칙 (fallback = 진단용 기준선)")
    for s, qq in out["q_v13"].items():
        for h, v in qq.items():
            if "error" in v:
                print("  %-30s %-6s ERROR %s" % (s[:30], h, v["error"])); continue
            print("  %-30s %-6s 시행 %2d  손Q %d  seg_rate %s  dt_ref %.4f" % (
                s[:30], h, v["n_trials"], v["q_hand_pass"],
                ("%.3f" % v["seg_rate_median"]) if v["seg_rate_median"] is not None else "-",
                v["session_dt_ref_s"] or -1))
    print()
    print("⑤ 랜드마크 커버리지 (v13.1 게이트 기준)")
    print("   게이트 밖:", out["landmark_coverage"]["uncovered_by_gate"],
          "/ 손끝:", out["landmark_coverage"]["uncovered_gate_tips"])
    print()
    print("JSON →", OUTJ)


if __name__ == "__main__":
    main()

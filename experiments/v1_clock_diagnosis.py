#!/usr/bin/env python3
"""v1_clock_diagnosis.py — V-1(peak velocity 이상치) 및 D-13(fps/시계) 진단

배경
----
`outputs/research-plan-v6.md` §15.2 V-1 이 남긴 미확정 항목:

    "PV_m_s 이상치(최대 7.947 m/s)의 원인 추정 — 미확정(파이프라인 코드 미열람)."

본 스크립트는 팀 파이프라인(`capstone/호진파일/compute_qiu_metrics.py`)을 **읽고**,
실제 데이터(`capstone/호진파일/outputs/데이터_저장/20260915_...`)로 그 계산을
**재현**한 뒤, 원인을 통제 실험(ablation)으로 분리한다.

가설
----
H-a  타임스탬프가 **벽시계**(`time.time() - session_start`)이고, 카메라 프레임보다
     미세하게 촘촘히 찍힌다 → 인접 행의 dt가 실제 프레임 간격보다 훨씬 작아진다.
H-b  속도식이 `|Δp| / max(dt, 1e-4)` 이고 중복 제거 임계가 **1e-4 s(0.1 ms)** 뿐이라,
     H-a의 작은 dt가 **속도를 수십 배로 증폭**한다.
H-c  집계가 `max()` 이고 5점 이동평균이 그 스파이크를 지우지 못한다.

사용
----
    python experiments/v1_clock_diagnosis.py            # 기본 세션 자동 탐색
    python experiments/v1_clock_diagnosis.py --session "<경로>"

출력: 콘솔 리포트 + `outputs/03-검증/provenance/v1_clock_diagnosis.json`
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "03-검증" / "provenance"

DEFAULT_SESSION = ("capstone/호진파일/outputs/데이터_저장/"
                   "20260915_비장애인_test_26세_남")


# ─────────────────────────────────────────────────────────────────────────────
# 팀 파이프라인과 동일한 함수 (compute_qiu_metrics.py 에서 그대로 옮김)
# ─────────────────────────────────────────────────────────────────────────────
def smooth_moving_average(arr: np.ndarray, window_size: int = 5) -> np.ndarray:
    """compute_qiu_metrics.py:100 smooth_moving_average 와 동일."""
    if len(arr) < window_size:
        return arr
    window = np.ones(window_size) / window_size
    smoothed = np.convolve(arr, window, mode="same")
    smoothed[: window_size // 2] = arr[: window_size // 2]
    smoothed[-window_size // 2:] = arr[-window_size // 2:]
    return smoothed


def load_wrist(lm_csv: pathlib.Path, hand: str, t0: float, t1: float,
               frame_clock: dict[int, float] | None = None) -> dict:
    """landmarks.csv 에서 손목(Landmark_ID=0) 시계열을 읽는다.

    frame_clock 이 주어지면 time_s 대신 **프레임 시계**(video_timestamps.csv 의
    capture_unix_s − 세션 시작)를 쓴다.
    """
    rows_t, xs, ys, zs, frames = [], [], [], [], []
    with open(lm_csv, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("Landmark_ID") != "0" or row.get("Hand") != hand:
                continue
            try:
                t = float(row["time_s"])
            except (KeyError, ValueError):
                continue
            if not (t0 <= t <= t1):
                continue
            if not (row.get("MP_X_m") and row.get("MP_Y_m") and row.get("MP_Z_m")):
                continue
            fid = int(float(row["Frame_ID"]))
            if frame_clock is not None:
                if fid not in frame_clock:
                    continue
                t = frame_clock[fid]
            rows_t.append(t)
            xs.append(float(row["MP_X_m"]))
            ys.append(float(row["MP_Y_m"]))
            zs.append(float(row["MP_Z_m"]))
            frames.append(fid)
    return {"t": np.array(rows_t), "x": np.array(xs),
            "y": np.array(ys), "z": np.array(zs), "frame": np.array(frames)}


def pipeline_velocity(t: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray,
                      dt_floor: float = 1e-4, dt_ceil: float | None = None,
                      dedup_eps: float = 1e-4, smooth: bool = True):
    """compute_qiu_metrics.py:183-201 의 속도 계산을 그대로 재현.

    dt_floor : `np.maximum(dt, dt_floor)` 의 바닥값 (원본 1e-4)
    dt_ceil  : 주어지면 dt > dt_ceil 인 쌍을 **버린다** (원본에는 이런 상한이 없다)
    dedup_eps: 중복 타임스탬프 제거 임계 (원본 1e-4)
    """
    keep = np.diff(t, prepend=-1) > dedup_eps
    t, x, y, z = t[keep], x[keep], y[keep], z[keep]
    if smooth:
        x = smooth_moving_average(x, 5)
        y = smooth_moving_average(y, 5)
        z = smooth_moving_average(z, 5)
    dt = np.diff(t)
    d = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)
    m = np.ones(len(dt), dtype=bool)
    if dt_ceil is not None:
        m &= dt <= dt_ceil
    dt_eff = np.maximum(dt[m], dt_floor)
    vel = d[m] / dt_eff
    if smooth:
        vel = smooth_moving_average(vel, 5)
    t_vel = (t[:-1][m] + t[1:][m]) / 2.0
    return {"t": t, "dt": dt, "d": d, "vel": vel, "t_vel": t_vel,
            "dt_used": dt[m], "n": len(t), "n_pairs": len(dt), "n_used": int(m.sum())}


# ─────────────────────────────────────────────────────────────────────────────
def load_frame_clock(session: pathlib.Path) -> dict[int, float]:
    """video_timestamps.csv → {frame_id: elapsed_s}. 실측 프레임 시계."""
    p = session / "video_timestamps.csv"
    if not p.exists():
        return {}
    recs = []
    with open(p, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                recs.append((int(r["frame_id"]), float(r["capture_unix_s"])))
            except (KeyError, ValueError):
                continue
    if not recs:
        return {}
    recs.sort()
    base = recs[0][1]
    return {fid: ts - base for fid, ts in recs}


def load_trials(trials_csv: pathlib.Path) -> list[dict]:
    out = []
    with open(trials_csv, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out.append({"trial": r.get("Trial", ""), "hand": r.get("Hand", ""),
                        "task": r.get("Task", ""),
                        "start_s": float(r.get("Start_s") or 0),
                        "end_s": float(r.get("End_s") or 0)})
    return out


def qiu_pv(v: dict) -> float:
    return float(np.max(v["vel"])) if len(v["vel"]) else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default=DEFAULT_SESSION)
    a = ap.parse_args()
    session = (ROOT / a.session) if not os.path.isabs(a.session) else pathlib.Path(a.session)
    if not session.exists():
        print(f"세션 폴더 없음: {session}", file=sys.stderr)
        sys.exit(2)

    lm = pathlib.Path(glob.glob(str(session / "*_landmarks.csv"))[0])
    tr = pathlib.Path(glob.glob(str(session / "*_trials_summary.csv"))[0])
    print(f"세션: {session.relative_to(ROOT)}")
    print(f"  landmarks : {lm.name}")
    print(f"  trials    : {tr.name}")

    clock = load_frame_clock(session)
    print(f"  프레임 시계: {len(clock)} 프레임 "
          f"({'video_timestamps.csv 있음' if clock else '없음'})")

    trials = load_trials(tr)
    reps: dict[str, dict] = {}

    # ── 재현 대상: PV 최대 시행 ──────────────────────────────────────────
    target = None
    for t in trials:
        if t["trial"] == "Trial #1" and t["hand"] == "Right":
            target = t
            break
    target = target or trials[0]
    print(f"\n재현 대상: {target['trial']} / {target['hand']} / {target['task']} "
          f"(t={target['start_s']:.3f}–{target['end_s']:.3f})")

    raw = load_wrist(lm, target["hand"], target["start_s"], target["end_s"])

    # ── (0) 원본 파이프라인 재현 ────────────────────────────────────────
    v0 = pipeline_velocity(raw["t"], raw["x"], raw["y"], raw["z"])
    pv0 = qiu_pv(v0)
    print(f"\n[0] 원본 재현 (벽시계, max, dt floor 1e-4)")
    print(f"    PV = {pv0:.3f} m/s   (문서 기록값 7.947)")
    print(f"    표본 {v0['n']}개 → 쌍 {v0['n_pairs']}개")

    # dt 분포
    dt = v0["dt"]
    print(f"    dt 분포(s): min={dt.min():.6f} p1={np.percentile(dt,1):.4f} "
          f"중앙={np.median(dt):.4f} p99={np.percentile(dt,99):.4f} max={dt.max():.4f}")
    for thr in (0.001, 0.005, 0.010, 0.020, 0.030):
        n = int((dt < thr).sum())
        print(f"      dt < {thr*1000:6.1f} ms : {n:5d} 쌍 "
              f"({100*n/max(len(dt),1):5.1f}%)")
    print(f"    실측 프레임 간격(16.93 fps) = {1/16.933905:.4f} s")

    # argmax 순간
    i = int(np.argmax(v0["vel"]))
    print(f"\n    ▶ PV 지점: t={v0['t_vel'][i]:.4f}s, vel={v0['vel'][i]:.3f} m/s")
    print(f"      그 쌍의 dt   = {v0['dt_used'][i]*1000:.3f} ms")
    print(f"      그 쌍의 |Δp| = {v0['d'][i]*1000:.3f} mm")
    print(f"      → dt 바닥값(0.1 ms)이 아니라면 물리적으로 "
          f"{v0['d'][i]/ (1/16.93) :.3f} m/s 수준")

    # ── (1) dt 하한을 프레임 간격 수준으로 ──────────────────────────────
    print(f"\n[1] dt 하한 ablation (상한 없음, max)")
    abl = {}
    for floor in (1e-4, 0.002, 0.005, 0.010, 0.020, 0.040):
        v = pipeline_velocity(raw["t"], raw["x"], raw["y"], raw["z"], dt_floor=floor)
        pv = qiu_pv(v)
        abl[f"floor_{floor}"] = pv
        print(f"    dt floor {floor*1000:6.2f} ms → PV = {pv:8.3f} m/s")

    # ── (2) dt 상한 추가 (물리적으로 불가능한 간격 제거) ────────────────
    print(f"\n[2] dt 상한 추가 (plan §5.1-7 의 'dt>0.1s 계산 안 함'은 상한만 있다)")
    for ceil in (0.1, 0.05):
        v = pipeline_velocity(raw["t"], raw["x"], raw["y"], raw["z"], dt_ceil=ceil)
        print(f"    dt ≤ {ceil*1000:5.0f} ms → PV = {qiu_pv(v):8.3f} m/s "
              f"(사용 쌍 {v['n_used']}/{v['n_pairs']})")

    # ── (3) P95 vs max (plan 의 K1·K2 는 P95) ──────────────────────────
    print(f"\n[3] 집계 규칙: max vs P95 vs P99  (plan 은 K1·K2 에 P95 를 쓴다)")
    for label, v in (("원본(dt floor 1e-4)", v0),
                     ("dt≤0.1s", pipeline_velocity(raw["t"], raw["x"], raw["y"], raw["z"], dt_ceil=0.1))):
        print(f"    {label:22s} max={np.max(v['vel']):8.3f} "
              f"P99={np.percentile(v['vel'],99):7.3f} "
              f"P95={np.percentile(v['vel'],95):7.3f} m/s")

    # ── (4) 시계 교체: 벽시계 → 프레임 시계 ─────────────────────────────
    print(f"\n[4] 시계 교체 (벽시계 time_s → 프레임 시계 video_timestamps)")
    res_clock = None
    if clock:
        raw2 = load_wrist(lm, target["hand"], target["start_s"], target["end_s"],
                          frame_clock=clock)
        if len(raw2["t"]) >= 15:
            v2 = pipeline_velocity(raw2["t"], raw2["x"], raw2["y"], raw2["z"])
            pv2 = qiu_pv(v2)
            dt2 = v2["dt"]
            print(f"    표본 {v2['n']}개 | dt 중앙={np.median(dt2):.4f}s "
                  f"min={dt2.min():.4f}s max={dt2.max():.4f}s")
            print(f"    PV(프레임 시계) = {pv2:.3f} m/s   "
                  f"(벽시계 {pv0:.3f} → 변화 {pv2-pv0:+.3f})")
            i2 = int(np.argmax(v2["vel"]))
            print(f"      PV 지점 dt = {v2['dt_used'][i2]*1000:.2f} ms, "
                  f"|Δp| = {v2['d'][i2]*1000:.2f} mm")
            res_clock = {"pv": pv2, "dt_median": float(np.median(dt2))}
        else:
            print("    프레임 시계로 매칭되는 표본 부족")
    else:
        print("    video_timestamps.csv 없음 → 생략")

    # ── (5) 시행 전체 PV 표 vs 재계산 ──────────────────────────────────
    print(f"\n[5] 세션 전체 시행의 PV (원본 산출물 vs dt 하한 보정)")
    rows = []
    for t in trials:
        if t["hand"] != "Right":
            continue
        r = load_wrist(lm, t["hand"], t["start_s"], t["end_s"])
        if len(r["t"]) < 15:
            continue
        va = pipeline_velocity(r["t"], r["x"], r["y"], r["z"])
        vb = pipeline_velocity(r["t"], r["x"], r["y"], r["z"], dt_ceil=0.1)
        rows.append({"trial": t["trial"], "pv_raw": qiu_pv(va),
                     "pv_p95_raw": float(np.percentile(va["vel"], 95)),
                     "pv_dt_capped": qiu_pv(vb),
                     "pv_p95_capped": float(np.percentile(vb["vel"], 95)) or 0.0,
                     "n_pairs": va["n_pairs"],
                     "n_tiny": int((va["dt"] < 0.005).sum())})
    print(f"    {'시행':9s} {'PV원본':>9s} {'PV(dt≤.1s)':>11s} {'P95원본':>9s} "
          f"{'P95(dt≤.1s)':>12s} {'쌍수':>6s} {'dt<5ms':>7s}")
    for r in rows:
        print(f"    {r['trial']:9s} {r['pv_raw']:9.3f} {r['pv_dt_capped']:11.3f} "
              f"{r['pv_p95_raw']:9.3f} {r['pv_p95_capped']:12.3f} "
              f"{r['n_pairs']:6d} {r['n_tiny']:7d}")

    # ── 저장 ──────────────────────────────────────────────────────────
    OUT.mkdir(parents=True, exist_ok=True)
    slug = session.name[:24].replace(" ", "_")
    dest = OUT / f"v1_clock_diagnosis__{slug}.json"
    payload = {
        "session": str(session.relative_to(ROOT)),
        "target": target,
        "pv_reproduced": pv0,
        "pv_documented": 7.947,
        "dt_stats": {"min": float(dt.min()), "median": float(np.median(dt)),
                     "p99": float(np.percentile(dt, 99)), "max": float(dt.max()),
                     "n_below_5ms": int((dt < 0.005).sum()), "n_pairs": len(dt)},
        "cap": {"pv_raw": pv0, "P95": float(np.percentile(v0["vel"], 95)),
                "P99": float(np.percentile(v0["vel"], 99))},
        "dt_floor_ablation": abl,
        "frame_clock": res_clock,
        "per_trial": rows,
        "real_fps": 16.933905,
    }
    dest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장: {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""v11 — 기존 영상에서 MediaPipe Pose를 **오프라인으로** 추출한다 (계획서 v10 P1 해결).

## 해결하는 문제
v10 §7.2/§7.3의 M4(SPARC)·M5(TD)는 MediaPipe Pose를 전제하는데,
촬영 앱(`Mirror_therapy_clock_v3.py`)에는 Pose가 **없다**(grep 0건).
그래서 v10 정의대로의 M4·M5는 산출 불가였고, 파일럿 16레코드에서 TD가 16/16 null이었다.

## 해결 방식
**기존 앱을 수정하지 않는다.** v10 §6.2가 이미 "촬영과 추적을 분리해 landmark는 원칙적으로
오프라인 계산한다"고 정했으므로, **저장된 영상(`original.avi`)을 사후 처리**해 Pose를 뽑는다.
출력 CSV는 v10의 `load_pose_csv`가 그대로 읽을 수 있는 롱포맷이다.

    Frame_ID, time_s, Landmark_ID, visibility,
    MP_X_m, MP_Y_m, MP_Z_m,          # world landmark (원점=골반 중심, 미터)
    RS_X_m, RS_Y_m, RS_Z_m, RS_Status # 카메라 좌표(원시 depth+내부파라미터가 있을 때만)

⚠️ **좌표계 경고(실측 확인):** MediaPipe Pose world landmark의 원점은 **양 골반 중점**이다.
   파일럿에서 hips mid = (-0.0001, -0.0011, 0.0004) m 로 확인됐다.
   → world landmark로는 **체간의 전역 이동(의자 기준 앞으로 나감)을 복원할 수 없다.**
     복원 가능한 것은 **골반 기준 상체의 기울기/전방굴곡**이며, 이는 ARAT의
     "몸통이 등받이에서 떨어짐" 기준과 정합적이다(`l2_metrics_v11.TD_lean`).
   → 전역 이동량이 필요하면 `--depth-dir` + `--intrinsics` 로 RS_* 를 만들어 쓴다.

실행:
  python experiments/v11/pose_offline.py --selftest
  python experiments/v11/pose_offline.py --video <session>/original.avi \
      --timestamps <session>/video_timestamps.csv --out <session>/pose_landmarks.csv
  # 원시 depth가 있으면 카메라 좌표까지:
  python experiments/v11/pose_offline.py --video v.avi --timestamps ts.csv \
      --depth-dir <session>/raw_rgbd --intrinsics 600,600,640,360 --out pose.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import sys
import time

import numpy as np

# ---- MediaPipe Pose 인덱스 (공식 33점) ----
POSE_L_SHOULDER, POSE_R_SHOULDER = 11, 12
POSE_L_WRIST, POSE_R_WRIST = 15, 16
POSE_L_HIP, POSE_R_HIP = 23, 24
POSE_NOSE = 0
N_POSE = 33

REQUIRED_LANDMARKS = {
    "nose": POSE_NOSE, "l_shoulder": POSE_L_SHOULDER, "r_shoulder": POSE_R_SHOULDER,
    "l_wrist": POSE_L_WRIST, "r_wrist": POSE_R_WRIST, "l_hip": POSE_L_HIP, "r_hip": POSE_R_HIP,
}

CSV_HEADER = ["Frame_ID", "time_s", "Landmark_ID", "visibility",
              "MP_X_m", "MP_Y_m", "MP_Z_m",
              "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Status"]


# =====================================================================
# 1. 시간축
# =====================================================================
def load_video_timestamps(path):
    """video_timestamps.csv → {video_frame_index: (elapsed_s, frame_id)}."""
    out = {}
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                idx = int(float(r.get("video_frame_index", r.get("Frame_ID", 0))))
            except (TypeError, ValueError):
                continue
            try:
                el = float(r.get("elapsed_s", r.get("time_s", "nan")))
            except (TypeError, ValueError):
                el = float("nan")
            try:
                fid = int(float(r.get("frame_id", idx)))
            except (TypeError, ValueError):
                fid = idx
            out[idx] = (el, fid)
    return out


def build_time_axis(n_frames, ts_map, fallback_fps):
    """프레임별 (frame_id, time_s) 배열을 만든다.

    우선순위: video_timestamps.csv > fps 메타.
    """
    fids = np.arange(n_frames, dtype=int)
    times = np.full(n_frames, np.nan)
    src = "fps_meta" if fallback_fps and fallback_fps > 0 else "index"
    if fallback_fps and fallback_fps > 0:
        times = np.arange(n_frames, dtype=float) / float(fallback_fps)
    if ts_map:
        n_hit = 0
        for i in range(n_frames):
            if i in ts_map:
                el, fid = ts_map[i]
                if math.isfinite(el):
                    times[i] = el
                    fids[i] = fid
                    n_hit += 1
        if n_hit >= max(3, int(0.5 * n_frames)):
            src = "video_timestamps.csv"
    return fids, times, src


# =====================================================================
# 2. depth 역투영 (카메라 좌표)
# =====================================================================
def backproject(u, v, depth_m, fx, fy, cx, cy):
    """픽셀 + depth(m) → 카메라 좌표(m).  OpenCV 관례: X=우, Y=하, Z=전방."""
    z = float(depth_m)
    if not (z == z) or z <= 0 or not math.isfinite(z):
        return None
    x = (float(u) - cx) / fx * z
    y = (float(v) - cy) / fy * z
    return (x, y, z)


def load_depth_packet(depth_dir, frame_id, depth_scale=0.001, key="depth_aligned_u16"):
    """raw_rgbd/<frame_id>.npz → (H,W) float 깊이(m) 또는 None."""
    if not depth_dir:
        return None
    for name in ("%d.npz" % frame_id, "%06d.npz" % frame_id, "%08d.npz" % frame_id):
        p = os.path.join(depth_dir, name)
        if os.path.exists(p):
            try:
                with np.load(p) as z:
                    if key not in z:
                        key = list(z.keys())[0]
                    return np.asarray(z[key], dtype=np.float32) * depth_scale
            except Exception:
                return None
    return None


def depth_median_at(depth_m, u, v, win=3, valid_range=(0.1, 2.0)):
    """픽셀 중심 win×win 창의 유효 깊이 중앙값(m) + 유효비율."""
    if depth_m is None:
        return None, 0.0
    H, W = depth_m.shape[:2]
    u0, v0 = int(round(u)), int(round(v))
    h = win // 2
    y0, y1 = max(0, v0 - h), min(H, v0 + h + 1)
    x0, x1 = max(0, u0 - h), min(W, u0 + h + 1)
    if y1 <= y0 or x1 <= x0:
        return None, 0.0
    patch = depth_m[y0:y1, x0:x1].ravel()
    good = patch[np.isfinite(patch) & (patch >= valid_range[0]) & (patch <= valid_range[1])]
    frac = float(good.size) / float(patch.size) if patch.size else 0.0
    if frac < 0.5 or good.size == 0:
        return None, frac
    return float(np.median(good)), frac


# =====================================================================
# 3. 추출
# =====================================================================
def extract(video, out_csv, ts_path=None, depth_dir=None, intrinsics=None,
            model_complexity=1, min_visibility=0.5, max_frames=None, start_frame=0,
            depth_scale=0.001, quiet=False, fps_override=None):
    import cv2
    import mediapipe as mp

    ts_map = load_video_timestamps(ts_path) if ts_path and os.path.exists(ts_path) else {}
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise IOError("영상을 열 수 없다: %s" % video)
    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_meta = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
    if fps_override:
        fps_meta = float(fps_override)
    n_frames = n_total if not max_frames else min(n_total, start_frame + max_frames)
    if start_frame:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    fids_all, times_all, ts_src = build_time_axis(n_total, ts_map, fps_meta)

    pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=model_complexity,
                                  smooth_landmarks=True, enable_segmentation=False)
    rows = []
    vis_acc = {k: [] for k in REQUIRED_LANDMARKS}
    n_detected = 0
    t0 = time.time()
    i = start_frame
    while i < n_frames:
        ok, frame = cap.read()
        if not ok:
            break
        res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        fid = int(fids_all[i]) if i < len(fids_all) else i
        ts = float(times_all[i]) if i < len(times_all) else float("nan")
        if res.pose_landmarks:
            n_detected += 1
            img = res.pose_landmarks.landmark
            wl = res.pose_world_landmarks.landmark if res.pose_world_landmarks else None
            dep = load_depth_packet(depth_dir, fid, depth_scale) if depth_dir else None
            for j in range(N_POSE):
                vis = float(img[j].visibility)
                mp_xyz = (float(wl[j].x), float(wl[j].y), float(wl[j].z)) if wl else (float("nan"),) * 3
                rs = (float("nan"),) * 3
                status = "no_depth"
                if dep is not None and intrinsics is not None:
                    u = img[j].x * (frame.shape[1] - 1)
                    v = img[j].y * (frame.shape[0] - 1)
                    z, frac = depth_median_at(dep, u, v)
                    if z is None:
                        status = "depth_hole"
                    else:
                        bp = backproject(u, v, z, intrinsics[0], intrinsics[1], intrinsics[2], intrinsics[3])
                        if bp is None:
                            status = "depth_invalid"
                        else:
                            rs = bp
                            status = "ok"
                rows.append([fid, ts, j, vis] + list(mp_xyz) + list(rs) + [status])
                if vis >= min_visibility:
                    for k, idx in REQUIRED_LANDMARKS.items():
                        if j == idx:
                            vis_acc[k].append(vis)
        else:
            for j in range(N_POSE):
                rows.append([fid, ts, j, 0.0] + [float("nan")] * 6 + ["not_detected"])
        i += 1
        if not quiet and (i - start_frame) % 300 == 0:
            print("  ... %d/%d frames (%.0fs)" % (i - start_frame, n_frames - start_frame, time.time() - t0),
                  file=sys.stderr)
    cap.release()
    pose.close()

    with io.open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for r in rows:
            w.writerow([r[0], "%.6f" % r[1] if math.isfinite(r[1]) else "",
                        r[2], "%.4f" % r[3]] +
                       ["%.6f" % v if isinstance(v, float) and math.isfinite(v) else "" for v in r[4:10]] +
                       [r[10]])

    vis_report = {}
    for k, vals in vis_acc.items():
        a = np.asarray(vals, float)
        vis_report[k] = {"n_visible_frames": int(a.size),
                         "frac_of_detected": (float(a.size) / n_detected) if n_detected else 0.0,
                         "median_visibility": float(np.median(a)) if a.size else None}
    meta = {
        "provenance": {"tool": "experiments/v11/pose_offline.py",
                       "mediapipe": getattr(mp, "__version__", None),
                       "model_complexity": model_complexity, "smooth_landmarks": True,
                       "video": os.path.basename(video), "n_frames_total": n_total,
                       "n_frames_processed": i - start_frame, "n_detected": n_detected,
                       "fps_meta": fps_meta, "time_source": ts_src,
                       "depth_dir": depth_dir, "intrinsics": intrinsics,
                       "depth_scale": depth_scale if depth_dir else None,
                       "elapsed_s": round(time.time() - t0, 1)},
        "coordinate_warning": ("world landmark 원점 = 골반 중점. 전역 이동 복원 불가, "
                               "골반 기준 기울기만 가능."),
        "fov_report": vis_report,
    }
    meta_path = os.path.splitext(out_csv)[0] + ".meta.json"
    io.open(meta_path, "w", encoding="utf-8").write(json.dumps(meta, ensure_ascii=False, indent=2))
    return {"out_csv": out_csv, "meta": meta_path, "n_rows": len(rows), "n_detected": n_detected}


# =====================================================================
# 4. 오라클
# =====================================================================
def _write_synth_ts(path, n=100, fps=13.4, jitter=0.1, seed=1):
    rng = np.random.default_rng(seed)
    dt = 1.0 / fps
    t = np.cumsum(np.full(n, dt) + rng.normal(0, jitter * dt, n))
    t = t - t[0]
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["video_frame_index", "frame_id", "capture_unix_s", "elapsed_s", "dt_s"])
        for i in range(n):
            w.writerow([i, 600 + i, 1.7e9 + t[i], "%.6f" % t[i], "%.6f" % (dt if i == 0 else t[i] - t[i - 1])])
    return t


def selftest():
    import tempfile
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    # (1) 역투영 수학 (핀홀 왕복)
    fx, fy, cx, cy = 600.0, 600.0, 640.0, 360.0
    for (X, Y, Z) in [(0.1, -0.05, 0.8), (0.0, 0.0, 0.5), (-0.2, 0.15, 1.2)]:
        u = X / Z * fx + cx
        v = Y / Z * fy + cy
        bp = backproject(u, v, Z, fx, fy, cx, cy)
        ok = bp is not None and max(abs(bp[0] - X), abs(bp[1] - Y), abs(bp[2] - Z)) < 1e-9
        chk("역투영 왕복 (%.2f,%.2f,%.2f)" % (X, Y, Z), ok, str(None if bp is None else np.round(bp, 4)))
    chk("역투영: depth 0 → None", backproject(100, 100, 0.0, fx, fy, cx, cy) is None)
    chk("역투영: depth NaN → None", backproject(100, 100, float("nan"), fx, fy, cx, cy) is None)

    # (2) depth 창 중앙값 + 유효비율
    d = np.full((20, 20), 0.8, np.float32)
    d[10, 10] = 0.0                       # 구멍
    z, frac = depth_median_at(d, 10, 10, win=3, valid_range=(0.1, 2.0))
    chk("depth 창: 구멍 1개 → 유효비율 8/9, 중앙값 0.8", z is not None and abs(z - 0.8) < 1e-6
        and abs(frac - 8 / 9) < 1e-9, "z=%s frac=%.3f" % (z, frac))
    d2 = np.zeros((20, 20), np.float32)
    z2, frac2 = depth_median_at(d2, 10, 10, win=3, valid_range=(0.1, 2.0))
    chk("depth 창: 전부 무효 → None", z2 is None and frac2 == 0.0)

    # (3) 시간축: video_timestamps.csv 우선
    tmp = tempfile.mkdtemp(prefix="v11_pose_")
    ts = os.path.join(tmp, "video_timestamps.csv")
    t_true = _write_synth_ts(ts, n=100, fps=13.4)
    ts_map = load_video_timestamps(ts)
    fids, times, src = build_time_axis(100, ts_map, 30.0)
    chk("시간축: 출처 = video_timestamps.csv", src == "video_timestamps.csv", src)
    chk("시간축: frame_id 재사용(600..699)", fids[0] == 600 and fids[-1] == 699, "%d..%d" % (fids[0], fids[-1]))
    chk("시간축: 값 일치", abs(times[50] - t_true[50]) < 1e-6, "%.6f vs %.6f" % (times[50], t_true[50]))
    fids2, times2, src2 = build_time_axis(100, {}, 30.0)
    chk("시간축: ts 없으면 fps 메타 사용", src2 == "fps_meta" and abs(times2[30] - 1.0) < 1e-9, src2)

    # (4) CSV 스키마가 v10 로더와 호환되는가 (통합 검증)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v10"))
    compatible = False
    detail = ""
    try:
        from l2_metrics_v10 import load_pose_csv
        p = os.path.join(tmp, "pose.csv")
        with io.open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(CSV_HEADER)
            for i in range(60):
                tt = i / 13.4
                for j in range(N_POSE):
                    x, y, z = 0.0, -0.3, 0.0
                    if j in (POSE_L_SHOULDER, POSE_R_SHOULDER):
                        x = 0.15 if j == POSE_L_SHOULDER else -0.15
                    w.writerow([i, "%.6f" % tt, j, 0.95, "%.6f" % x, "%.6f" % y, "%.6f" % z,
                                "", "", "", "no_depth"])
        pd_mp = load_pose_csv(p, coord="MP")
        pd_rs = load_pose_csv(p, coord="RS")   # depth 없음 → RS 전부 결측이어야 정상
        compatible = (pd_mp["pos"].shape[1] == 33
                      and np.isfinite(pd_mp["pos"][:, POSE_R_SHOULDER]).all()
                      and pd_mp["valid"][:, POSE_R_SHOULDER].all()
                      and not np.isfinite(pd_rs["pos"]).any())
        detail = ("MP pos%s valid=%d/%d | RS finite=%d(0 기대)"
                  % (pd_mp["pos"].shape, int(pd_mp["valid"][:, POSE_R_SHOULDER].sum()),
                     pd_mp["pos"].shape[0], int(np.isfinite(pd_rs["pos"]).sum())))
    except Exception as e:  # noqa: BLE001
        detail = "%s: %s" % (type(e).__name__, e)
    chk("★ CSV가 v10 load_pose_csv와 호환", compatible, detail)

    # (5) depth 패킷 로딩
    try:
        np.savez(os.path.join(tmp, "7.npz"), depth_aligned_u16=(np.ones((4, 4), np.uint16) * 800))
        loaded = load_depth_packet(tmp, 7, depth_scale=0.001)
        chk("depth npz 로딩 → 미터 변환", loaded is not None and abs(float(loaded[0, 0]) - 0.8) < 1e-6,
            None if loaded is None else "%.3f m" % float(loaded[0, 0]))
    except Exception as e:  # noqa: BLE001
        chk("depth npz 로딩 → 미터 변환", False, str(e))

    print("=" * 72)
    print("pose_offline 오라클 (v11)")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="v11 오프라인 MediaPipe Pose 추출")
    ap.add_argument("--video")
    ap.add_argument("--timestamps", default=None)
    ap.add_argument("--depth-dir", default=None)
    ap.add_argument("--intrinsics", default=None, help="fx,fy,cx,cy")
    ap.add_argument("--model-complexity", type=int, default=1, choices=[0, 1, 2])
    ap.add_argument("--min-visibility", type=float, default=0.5)
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--start-frame", type=int, default=0)
    ap.add_argument("--depth-scale", type=float, default=0.001)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.video and a.out):
        ap.error("--video --out 또는 --selftest 필요")
    intr = None
    if a.intrinsics:
        intr = tuple(float(x) for x in a.intrinsics.split(","))
        if len(intr) != 4:
            ap.error("--intrinsics 는 fx,fy,cx,cy 4개")
    res = extract(a.video, a.out, ts_path=a.timestamps, depth_dir=a.depth_dir, intrinsics=intr,
                  model_complexity=a.model_complexity, min_visibility=a.min_visibility,
                  max_frames=a.max_frames, start_frame=a.start_frame, depth_scale=a.depth_scale,
                  quiet=a.quiet, fps_override=a.fps)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

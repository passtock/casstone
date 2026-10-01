# -*- coding: utf-8 -*-
"""PoseRecorder — 촬영 앱에 MediaPipe Pose를 추가하기 위한 **신규 모듈**.

기존 앱(`Mirror_therapy_clock_v3.py`)은 수정하지 않는다. 이 모듈을 import 해서
캡처 루프에서 `submit()` 1회, 종료 시 `finalize()` 1회만 호출하면 된다.
(주입은 `tools/integrate_pose_into_app.py` 패처가 담당한다.)

## 왜 스레드인가
실측(2026-10-01): Pose(model_complexity=1) 1프레임 ≈ 29 ms, Hands ≈ 15 ms.
같은 루프에서 순차 실행하면 30 fps 카메라가 약 22 fps 로 떨어진다.
따라서 Pose를 **워커 스레드**로 돌리고 캡처 루프는 큐에 넣기만 한다.
큐가 가득 차면 **오래된 프레임을 버리고 버린 수를 기록**한다(조용히 늘리지 않는다).

## 저장 형식
`experiments/v11/pose_offline.py` 와 **동일한 롱포맷**을 쓴다.
    Frame_ID, time_s, Landmark_ID, visibility, MP_X_m, MP_Y_m, MP_Z_m,
    RS_X_m, RS_Y_m, RS_Z_m, RS_Status
→ 기존 오프라인 도구(`experiments/v11/l2_metrics_v11.py`, `run_session_v11.py`)가
   수정 없이 그대로 읽는다. (오라클에서 호환을 검증한다.)

- `MP_*` = MediaPipe Pose world landmark(미터, **원점 = 골반 중점**).
  ⚠️ 전역 이동은 복원되지 않는다. 골반 기준 상체 기울기만 남는다.
- `RS_*` = 카메라 좌표. **정렬 depth + 내부파라미터가 있을 때만** 채운다. 없으면 `no_depth`.

## 내구성
프레임마다 `raw_pose/<frame_id>.npz` 를 원자적으로 남기고(`save_depth_packet` 과 같은 방식),
종료 시 CSV 로 합친다. 크래시해도 원시 Pose 가 남는다.

실행:
  python pose_recorder.py --selftest
  python pose_recorder.py --video <session>/original.avi \
      --timestamps <session>/video_timestamps.csv --outdir <session>       # 하드웨어 없이
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import queue
import sys
import threading
import time

import numpy as np

CSV_HEADER = ["Frame_ID", "time_s", "Landmark_ID", "visibility",
              "MP_X_m", "MP_Y_m", "MP_Z_m",
              "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Status"]

N_POSE = 33
POSE_L_SHOULDER, POSE_R_SHOULDER = 11, 12
POSE_L_WRIST, POSE_R_WRIST = 15, 16
POSE_L_HIP, POSE_R_HIP = 23, 24

# 앱 `Mirror_therapy_clock_v3.py` 의 RS_Status 어휘와 맞춘다.
ST_OK, ST_NO_DEPTH = "ok", "no_depth"
ST_HOLE, ST_RANGE, ST_INSUFF = "depth_hole", "depth_out_of_range", "insufficient_depth"
ST_NO_INTR, ST_DEPROJ_FAIL = "no_intrinsics", "deprojection_failed"


# =====================================================================
# 1. 역투영 (앱 `deproject_pixel` 과 같은 규약)
# =====================================================================
def _intr_get(intr, name, default=None):
    """rs2 intrinsics 객체와 dict 를 모두 받는다."""
    if intr is None:
        return default
    if isinstance(intr, dict):
        return intr.get(name, intr.get({"ppx": "cx", "ppy": "cy"}.get(name, name), default))
    return getattr(intr, name, default)


def backproject_pixel(u, v, z_m, intr, cv2mod=None):
    """정렬 depth 내부파라미터로 픽셀+depth(미터) → 카메라 좌표 XYZ(미터).

    앱과 동일하게: modified Brown-Conrady 이면 cv2.undistortPoints 로 왜곡을 먼저 푼다.
    """
    if intr is None or z_m is None or not np.isfinite(z_m) or z_m <= 0:
        return None
    fx, fy = _intr_get(intr, "fx"), _intr_get(intr, "fy")
    ppx, ppy = _intr_get(intr, "ppx"), _intr_get(intr, "ppy")
    if not all(isinstance(x, (int, float)) and np.isfinite(x) and x > 0 for x in (fx, fy)):
        return None
    coeffs = _intr_get(intr, "coeffs") or []
    model = str(_intr_get(intr, "model", ""))
    if cv2mod is not None and coeffs and "modified_brown_conrady" in model.lower():
        K = np.array([[fx, 0, ppx], [0, fy, ppy], [0, 0, 1.0]])
        xy = cv2mod.undistortPoints(
            np.array([[[float(u), float(v)]]], dtype=float), K,
            np.asarray(coeffs, dtype=float))[0, 0]
        return (float(xy[0]) * float(z_m), float(xy[1]) * float(z_m), float(z_m))
    return ((float(u) - ppx) / fx * float(z_m),
            (float(v) - ppy) / fy * float(z_m), float(z_m))


def depth_median_at(depth_m, u, v, win=5, valid_range=(0.1, 2.0)):
    """픽셀 중심 win×win 창의 유효 깊이 중앙값(미터)과 유효비율. (앱과 같은 5×5 창)"""
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
# 2. 워커
# =====================================================================
class _Worker(threading.Thread):
    """프레임을 큐에서 꺼내 Pose를 돌리고 raw_pose 에 남긴다."""

    def __init__(self, rec, maxsize=4, overflow="drop_new"):
        super().__init__(daemon=True, name="PoseWorker")
        self.rec = rec
        self.overflow = overflow
        self.q = queue.Queue(maxsize=maxsize)
        self._stop_evt = threading.Event()
        self.dropped = 0
        self.done = 0
        self.failed = 0

    def submit(self, item):
        try:
            self.q.put_nowait(item)
        except queue.Full:
            if self.overflow == "drop_old":
                # 가장 오래된 것을 버리고 최신을 넣는다(실시간 지향)
                try:
                    self.q.get_nowait()
                    self.q.task_done()
                    self.q.put_nowait(item)
                except queue.Empty:
                    pass
            self.dropped += 1
        return self.q.qsize()

    @property
    def accounted(self):
        return self.done + self.failed + self.dropped

    def run(self):
        while not (self._stop_evt.is_set() and self.q.empty()):
            try:
                item = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.rec._process_one(*item)
                self.done += 1
            except Exception as exc:  # noqa: BLE001
                self.failed += 1
                self.rec.errors.append(str(exc))
            finally:
                self.q.task_done()

    def stop(self, timeout=None):
        self._stop_evt.set()
        self.join(timeout=timeout)
        # 남은 항목이 있으면 마지막으로 비운다(유실 방지)
        if self.is_alive():
            self.join(timeout=1.0)
        return self.done


# =====================================================================
# 3. 본체
# =====================================================================
class PoseRecorder:
    """앱 캡처 루프에 붙이는 Pose 기록기.

    사용:
        rec = PoseRecorder(session_folder)
        rec.start()
        ...
        rec.submit(frame_id, time_s, frame_bgr, aligned_depth_u16=..., depth_scale=..., intr=..., cap_mono=...)
        ...
        rec.finalize()      # <folder>/pose_landmarks.csv + meta.json
    """

    def __init__(self, folder, model_complexity=1, min_visibility=0.5, threaded=True,
                 queue_size=8, overflow="drop_new", valid_range=(0.1, 2.0), win=5, engine=None,
                 raw_dir_name="raw_pose", csv_name="pose_landmarks.csv"):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.raw_dir = os.path.join(folder, raw_dir_name)
        os.makedirs(self.raw_dir, exist_ok=True)
        self.csv_path = os.path.join(folder, csv_name)
        self.meta_path = os.path.splitext(self.csv_path)[0] + ".meta.json"
        self.model_complexity = model_complexity
        self.min_visibility = min_visibility
        self.valid_range = valid_range
        self.win = win
        self.threaded = threaded
        self.queue_size = queue_size
        self.overflow = overflow
        self.errors = []
        self.rows = []
        self.n_submitted = 0
        self.n_processed = 0
        self.n_detected = 0
        self._engine = engine          # 테스트용 주입. None 이면 MediaPipe Pose.
        self._mp_version = None
        self._cv2 = None
        self._worker = None
        self._lock = threading.Lock()
        self._t0 = time.time()
        self._seek_cv2()

    # ---- 설정 ----
    def _seek_cv2(self):
        try:
            import cv2  # noqa: F401
            self._cv2 = cv2
        except Exception:  # pragma: no cover
            self._cv2 = None

    def _build_engine(self):
        if self._engine is not None:
            return self._engine
        import mediapipe as mp
        self._mp_version = getattr(mp, "__version__", None)
        return mp.solutions.pose.Pose(
            static_image_mode=False, model_complexity=self.model_complexity,
            smooth_landmarks=True, enable_segmentation=False)

    # ---- 수명주기 ----
    def start(self):
        self._engine = self._engine or self._build_engine()
        if self.threaded:
            self._worker = _Worker(self, maxsize=int(self.queue_size), overflow=self.overflow)
            self._worker.start()
        return self

    def submit(self, frame_id, time_s, frame_bgr, aligned_depth_u16=None, depth_scale=0.001,
               intr=None, cap_mono=None, cap_unix=None, frame_bgr_copy=True, depth_m=None):
        """캡처 루프에서 호출. threaded=True 면 즉시 반환한다.

        depth_m: 이미 미터로 변환된 정렬 depth(HxW float). 주면 depth_scale 변환을 건너뛴다.
                 (앱 `Mirror_therapy_clock_v3.py` 는 `self.latest_depth` 를 미터로 들고 있다.)
        """
        if frame_bgr_copy:
            frame_bgr = np.ascontiguousarray(frame_bgr)
        item = (frame_id, float(time_s), frame_bgr, aligned_depth_u16, float(depth_scale),
                intr, cap_mono, cap_unix, depth_m)
        self.n_submitted += 1
        if self._worker is not None:
            qsize = self._worker.submit(item)
            if self._worker.dropped and self._worker.dropped % 50 == 1:
                print("[POSE] 큐 포화로 %d 프레임을 건너뜀 (Pose가 캡처보다 느림)"
                      % self._worker.dropped)
            return qsize
        self._process_one(*item)
        self.n_processed += 1
        return 0

    # ---- 프레임 1장 처리 ----
    def _process_one(self, frame_id, time_s, frame_bgr, depth_u16, depth_scale, intr,
                     cap_mono, cap_unix, depth_m=None):
        rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB) if self._cv2 else frame_bgr
        if self._cv2:
            rgb = np.ascontiguousarray(rgb)
        res = self._engine.process(rgb)
        if getattr(res, "pose_landmarks", None) is None:
            rows = [(frame_id, time_s, j, 0.0, np.nan, np.nan, np.nan,
                     np.nan, np.nan, np.nan, "not_detected") for j in range(N_POSE)]
            self._emit(frame_id, rows, cap_mono, cap_unix)
            return
        img = res.pose_landmarks.landmark
        wl = res.pose_world_landmarks.landmark if getattr(res, "pose_world_landmarks", None) else None
        H, W = frame_bgr.shape[:2]
        if depth_m is None and depth_u16 is not None:
            depth_m = np.asarray(depth_u16, dtype=np.float32) * float(depth_scale)
        self.n_detected += 1
        rows = []
        for j in range(N_POSE):
            vis = float(getattr(img[j], "visibility", 0.0))
            if wl is not None:
                mp_xyz = (float(wl[j].x), float(wl[j].y), float(wl[j].z))
            else:
                mp_xyz = (np.nan, np.nan, np.nan)
            rs = (np.nan, np.nan, np.nan)
            status = ST_NO_DEPTH
            if depth_m is not None:
                if intr is None:
                    status = ST_NO_INTR
                else:
                    u = float(img[j].x) * (W - 1)
                    v = float(img[j].y) * (H - 1)
                    z, frac = depth_median_at(depth_m, u, v, win=self.win,
                                              valid_range=self.valid_range)
                    if z is None:
                        status = ST_HOLE if frac > 0 else ST_INSUFF
                    else:
                        bp = backproject_pixel(u, v, z, intr, cv2mod=self._cv2)
                        if bp is None:
                            status = ST_DEPROJ_FAIL
                        else:
                            rs, status = bp, ST_OK
            rows.append((frame_id, time_s, j, vis) + mp_xyz + rs + (status,))
        self._emit(frame_id, rows, cap_mono, cap_unix)

    def _emit(self, frame_id, rows, cap_mono, cap_unix):
        with self._lock:
            self.rows.extend(rows)
        # 크래시 대비 원자적 원시 저장
        try:
            path = os.path.join(self.raw_dir, "%09d.npz" % int(frame_id))
            tmp = path + ".tmp"
            arr = np.array([[r[3]] + list(r[4:10]) for r in rows], dtype=float)
            with open(tmp, "wb") as fp:
                np.savez(fp, values=arr,
                         frame_id=int(frame_id), time_s=float(rows[0][1]),
                         capture_monotonic_s=(-1.0 if cap_mono is None else float(cap_mono)),
                         capture_unix_s=(-1.0 if cap_unix is None else float(cap_unix)),
                         status=np.asarray([r[10] for r in rows]))
            os.replace(tmp, path)
        except Exception as exc:  # noqa: BLE001
            self.errors.append("raw_pose write: %s" % exc)

    # ---- 종료 ----
    def finalize(self, drain_timeout=30.0):
        if self._worker is not None:
            self._worker.stop(timeout=drain_timeout)
            self.n_processed = self._worker.done
            if self._worker.q.qsize():
                self.errors.append("finalize: 큐에 %d건이 남았다" % self._worker.q.qsize())
        with self._lock:
            rows = list(self.rows)
        with io.open(self.csv_path, "w", encoding="utf-8", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(CSV_HEADER)
            for r in rows:
                w.writerow([r[0], "%.6f" % r[1], r[2], "%.4f" % r[3]]
                           + ["%.6f" % x if isinstance(x, float) and np.isfinite(x) else ""
                              for x in r[4:10]]
                           + [r[10]])
        meta = {
            "provenance": {
                "tool": "capstone/호진파일/pose_recorder.py",
                "mediapipe": self._mp_version,
                "model_complexity": self.model_complexity,
                "threaded": self.threaded,
                "n_submitted": self.n_submitted, "n_processed": self.n_processed,
                "n_detected": self.n_detected,
                "n_dropped_by_queue": (self._worker.dropped if self._worker else 0),
                "queue_size": self.queue_size, "overflow": self.overflow,
                "n_failed": (self._worker.failed if self._worker else 0),
                "n_rows": len(rows), "elapsed_s": round(time.time() - self._t0, 1),
                "raw_dir": os.path.basename(self.raw_dir),
            },
            "coordinate_warning": "world landmark 원점 = 골반 중점. 전역 이동 복원 불가.",
            "errors": self.errors[:20],
        }
        io.open(self.meta_path, "w", encoding="utf-8").write(
            json.dumps(meta, ensure_ascii=False, indent=2))
        return self.csv_path

    def stats(self):
        dropped = (self._worker.dropped if self._worker else 0)
        failed = (self._worker.failed if self._worker else 0)
        accounted = self.n_processed + failed + dropped
        return {"n_submitted": self.n_submitted, "n_processed": self.n_processed,
                "n_detected": self.n_detected, "n_dropped_by_queue": dropped,
                "n_failed": failed, "accounted": accounted,
                "lossless": accounted == self.n_submitted,
                "queue_size": self.queue_size, "overflow": self.overflow,
                "n_errors": len(self.errors), "csv": self.csv_path}


# =====================================================================
# 4. 하드웨어 없는 실행 경로 (오프라인 / 재처리)
# =====================================================================
def run_offline(video, outdir, ts_path=None, model_complexity=1, max_frames=None,
                every_n=1, quiet=False):
    """저장된 영상 → PoseRecorder 로 pose_landmarks.csv 생성 (RealSense 불필요)."""
    import cv2

    ts_map = {}
    if ts_path and os.path.exists(ts_path):
        with io.open(ts_path, "r", encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    idx = int(float(r.get("video_frame_index", r.get("Frame_ID", 0))))
                    el = float(r.get("elapsed_s", r.get("time_s", "nan")))
                    fid = int(float(r.get("frame_id", idx)))
                except (TypeError, ValueError):
                    continue
                ts_map[idx] = (el, fid)

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise IOError("영상을 열 수 없다: %s" % video)
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if max_frames:
        n = min(n, max_frames)

    rec = PoseRecorder(outdir, model_complexity=model_complexity, threaded=False)
    rec.start()
    i = 0
    while i < n:
        ok, frame = cap.read()
        if not ok:
            break
        if i % every_n == 0:
            el, fid = ts_map.get(i, (i / fps if fps > 0 else float(i), i))
            if not np.isfinite(el):
                el = i / fps if fps > 0 else float(i)
            rec.submit(fid, el, frame, aligned_depth_u16=None, depth_scale=0.001, intr=None)
            if not quiet and i and i % 300 == 0:
                print("  ... %d/%d" % (i, n), file=sys.stderr)
        i += 1
    cap.release()
    out = rec.finalize()
    return {"csv": out, **rec.stats()}


# =====================================================================
# 5. 오라클
# =====================================================================
class _StubLM:
    def __init__(self, x=0.0, y=0.0, z=0.0, visibility=1.0):
        self.x, self.y, self.z, self.visibility = x, y, z, visibility


class _StubRes:
    def __init__(self, lms):
        if lms is None:
            self.pose_landmarks = None
            self.pose_world_landmarks = None
            return
        self.pose_landmarks = type("X", (), {"landmark": lms})()
        self.pose_world_landmarks = type("X", (), {"landmark": lms})()


class _StubEngine:
    """MediaPipe 없이 배관(CSV·역투영·스레드·결측)을 검증하기 위한 스텁."""

    def __init__(self, detect=True, vis=1.0):
        self.detect = detect
        self.vis = vis
        self.calls = 0

    def process(self, rgb):
        self.calls += 1
        if not self.detect:
            return _StubRes(None)
        lms = []
        for j in range(N_POSE):
            if j == POSE_L_SHOULDER:
                lms.append(_StubLM(0.15, -0.30, 0.0, self.vis))
            elif j == POSE_R_SHOULDER:
                lms.append(_StubLM(-0.15, -0.30, 0.0, self.vis))
            else:
                lms.append(_StubLM(0.0, 0.0, 0.0, self.vis))
        return _StubRes(lms)


def selftest():
    import tempfile
    checks, ok_all = [], True

    def chk(name, cond, info=""):
        nonlocal ok_all
        checks.append((name, bool(cond), info))
        ok_all = ok_all and bool(cond)

    tmp = tempfile.mkdtemp(prefix="pose_rec_")
    frame = np.zeros((48, 64, 3), np.uint8)

    # (1) 동기 모드 기본 배관
    rec = PoseRecorder(tmp, engine=_StubEngine(), threaded=False)
    rec.start()
    for i in range(5):
        rec.submit(i + 100, i * 0.075, frame)
    out = rec.finalize()
    chk("CSV 생성", os.path.exists(out))
    with io.open(out, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    chk("헤더 = v11 규격", rows[0] == CSV_HEADER, str(rows[0]))
    chk("행 수 = 5프레임 × 33점", len(rows) - 1 == 5 * 33, str(len(rows) - 1))
    chk("Frame_ID 보존", rows[1][0] == "100" and rows[-1][0] == "104")
    chk("미탐지 없음", all(r[10] != "not_detected" for r in rows[1:]))

    # (2) raw_pose 원자적 저장
    raws = sorted(os.listdir(os.path.join(tmp, "raw_pose")))
    chk("raw_pose 프레임별 npz", len(raws) == 5 and not any(x.endswith(".tmp") for x in raws), str(raws[:3]))
    with np.load(os.path.join(tmp, "raw_pose", raws[0])) as z:
        chk("raw npz 형상 (33, 7)", z["values"].shape == (33, 7), str(z["values"].shape))

    # (3) 미탐지 프레임
    tmp2 = tempfile.mkdtemp(prefix="pose_rec2_")
    rec2 = PoseRecorder(tmp2, engine=_StubEngine(detect=False), threaded=False)
    rec2.start()
    rec2.submit(1, 0.0, frame)
    out2 = rec2.finalize()
    with io.open(out2, encoding="utf-8", newline="") as fh:
        rows2 = list(csv.reader(fh))
    chk("미탐지 → not_detected 33행", len(rows2) - 1 == 33
        and all(r[10] == "not_detected" for r in rows2[1:]))
    chk("미탐지 시 visibility 0", all(float(r[3]) == 0.0 for r in rows2[1:]))

    # (4) 역투영 (앱 규약: 정렬 depth 내부파라미터)
    intr = {"fx": 600.0, "fy": 600.0, "ppx": 320.0, "ppy": 240.0, "model": "brown_conrady", "coeffs": []}
    bp = backproject_pixel(320.0, 240.0, 0.8, intr, cv2mod=None)
    chk("역투영: 주점 → (0,0,z)", bp is not None and abs(bp[0]) < 1e-9 and abs(bp[2] - 0.8) < 1e-9, str(bp))
    bp2 = backproject_pixel(620.0, 240.0, 0.8, intr, cv2mod=None)
    chk("역투영: +300px → x=0.4m", bp2 is not None and abs(bp2[0] - 0.4) < 1e-9, str(bp2))
    chk("역투영: depth 0 → None", backproject_pixel(1, 1, 0.0, intr) is None)
    chk("역투영: intrinsics 없음 → None", backproject_pixel(1, 1, 0.8, None) is None)
    chk("intrinsics dict/객체 모두 허용",
        backproject_pixel(600.0, 240.0, 0.8, type("I", (), {"fx": 600.0, "fy": 600.0, "ppx": 320.0,
                                                           "ppy": 240.0, "model": "x", "coeffs": []})()) is not None)

    # (5) depth 창 (앱과 같은 5×5, 유효비율 50% 규칙)
    d = np.full((480, 640), 0.8, np.float32)
    z, frac = depth_median_at(d, 320, 240, win=5)
    chk("depth 창: 균일 0.8m", z is not None and abs(z - 0.8) < 1e-6 and frac == 1.0, "%s %.2f" % (z, frac))
    d[238:243, 318:323] = 0.0
    z2, frac2 = depth_median_at(d, 320, 240, win=5)
    chk("depth 창: 전부 구멍 → None", z2 is None, str(z2))

    # (6) depth 있음 → RS_Status=ok, 없음 → no_depth
    tmp3 = tempfile.mkdtemp(prefix="pose_rec3_")
    rec3 = PoseRecorder(tmp3, engine=_StubEngine(), threaded=False)
    rec3.start()
    dep = (np.full((48, 64), 0.8, np.float32) / 0.001).astype(np.uint16)
    rec3.submit(7, 0.0, frame, aligned_depth_u16=dep, depth_scale=0.001,
                intr={"fx": 60.0, "fy": 60.0, "ppx": 32.0, "ppy": 24.0, "model": "brown_conrady", "coeffs": []})
    out3 = rec3.finalize()
    with io.open(out3, encoding="utf-8", newline="") as fh:
        rows3 = list(csv.reader(fh))[1:]
    chk("depth+intr → RS_Status=ok", any(r[10] == "ok" for r in rows3), rows3[0][10])
    chk("RS 좌표 채워짐", all(r[7] != "" for r in rows3 if r[10] == "ok"))

    tmp4 = tempfile.mkdtemp(prefix="pose_rec4_")
    rec4 = PoseRecorder(tmp4, engine=_StubEngine(), threaded=False)
    rec4.start()
    rec4.submit(7, 0.0, frame, aligned_depth_u16=dep, depth_scale=0.001, intr=None)
    out4 = rec4.finalize()
    with io.open(out4, encoding="utf-8", newline="") as fh:
        rows4 = list(csv.reader(fh))[1:]
    chk("depth 있는데 intr 없음 → no_intrinsics", all(r[10] == "no_intrinsics" for r in rows4), rows4[0][10])

    # (7) 스레드 모드: 전량 처리 + 통계
    tmp5 = tempfile.mkdtemp(prefix="pose_rec5_")
    rec5 = PoseRecorder(tmp5, engine=_StubEngine(), threaded=True, queue_size=256)
    rec5.start()
    for i in range(40):
        rec5.submit(i, i * 0.05, frame)
    out5 = rec5.finalize()
    st = rec5.stats()
    chk("스레드: 큐 충분 → 40프레임 전량 처리", st["n_processed"] == 40, json.dumps(st, ensure_ascii=False))
    chk("스레드: 유실 없음(processed+failed+dropped == submitted)", st["lossless"] is True, str(st["accounted"]))
    with io.open(out5, encoding="utf-8", newline="") as fh:
        chk("스레드 CSV 행 수 = 40×33", len(list(csv.reader(fh))) - 1 == 40 * 33)

    # 작은 큐: 드롭이 나도 '조용히 사라지지 않는다'(합계 보존)
    tmp7 = tempfile.mkdtemp(prefix="pose_rec7_")
    rec7 = PoseRecorder(tmp7, engine=_StubEngine(), threaded=True, queue_size=2)
    rec7.start()
    for i in range(200):
        rec7.submit(i, i * 0.05, frame)
    rec7.finalize()
    st7 = rec7.stats()
    chk("작은 큐: 합계 보존(유실 은폐 없음)", st7["lossless"] is True,
        "proc=%d drop=%d fail=%d submitted=%d" % (st7["n_processed"], st7["n_dropped_by_queue"],
                                                  st7["n_failed"], st7["n_submitted"]))
    chk("작은 큐: 드롭이 0보다 크게 보고됨", st7["n_dropped_by_queue"] > 0, str(st7["n_dropped_by_queue"]))

    # (8) 큐 포화 시 드롭을 숨기지 않는다
    tmp6 = tempfile.mkdtemp(prefix="pose_rec6_")
    rec6 = PoseRecorder(tmp6, engine=_StubEngine(), threaded=True, queue_size=1)
    rec6._worker = _Worker(rec6, maxsize=1)
    rec6._worker.dropped = 3
    chk("큐 드롭 계수 노출", rec6.stats()["n_dropped_by_queue"] == 3)

    # (9) ★ v11 도구 호환 (기존 오프라인 파이프라인이 그대로 읽는가)
    compatible, detail = False, ""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "experiments", "v10"))
        from l2_metrics_v10 import load_pose_csv
        # depth 없이 만든 파일을 RS 로 읽으면 전부 결측이어야 한다
        pd_mp = load_pose_csv(out, coord="MP")
        pd_rs = load_pose_csv(out, coord="RS")
        compatible = (pd_mp["pos"].shape[1] == 33
                      and np.isfinite(pd_mp["pos"][:, POSE_R_SHOULDER]).all()
                      and not np.isfinite(pd_rs["pos"]).any())
        detail = "MP %s valid=%d/%d | RS finite=%d" % (
            pd_mp["pos"].shape, int(pd_mp["valid"][:, POSE_R_SHOULDER].sum()),
            pd_mp["pos"].shape[0], int(np.isfinite(pd_rs["pos"]).sum()))
    except Exception as e:  # noqa: BLE001
        detail = "%s: %s" % (type(e).__name__, e)
    chk("★ v11 load_pose_csv 와 호환", compatible, detail)

    # (10) meta.json 기록
    meta = json.load(io.open(rec.meta_path, encoding="utf-8"))
    chk("meta.json: 출처·계수 기록",
        meta["provenance"]["n_processed"] == 5 and "coordinate_warning" in meta,
        json.dumps(meta["provenance"], ensure_ascii=False)[:80])

    print("=" * 72)
    print("pose_recorder 오라클")
    for name, cond, info in checks:
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, ("| " + info) if info else ""))
    n_pass = sum(1 for _, c, _ in checks if c)
    print("-" * 72)
    print("%d PASS / %d FAIL (total %d)" % (n_pass, len(checks) - n_pass, len(checks)))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="PoseRecorder — 녹화 앱용 Pose 기록 모듈")
    ap.add_argument("--video", help="오프라인 모드: 저장된 영상")
    ap.add_argument("--timestamps", default=None)
    ap.add_argument("--outdir", help="출력 폴더(세션 폴더)")
    ap.add_argument("--model-complexity", type=int, default=1, choices=[0, 1, 2])
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--every-n", type=int, default=1)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.video and a.outdir):
        ap.error("--video --outdir 또는 --selftest 필요")
    res = run_offline(a.video, a.outdir, ts_path=a.timestamps,
                      model_complexity=a.model_complexity, max_frames=a.max_frames,
                      every_n=a.every_n, quiet=a.quiet)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

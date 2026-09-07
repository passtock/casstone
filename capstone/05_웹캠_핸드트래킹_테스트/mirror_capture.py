"""Camera-independent measurement and lossless frame recording helpers.

All pixels/XYZ refer to the unmirrored camera image. Missing measurements
stay NaN internally and are exported as empty CSV cells, never as zero.
"""
import csv
import json
import os
import queue
import threading
import io
import zipfile
from pathlib import Path

import numpy as np

DEPTH_MIN_M = 0.10
DEPTH_MAX_M = 2.00
DEPTH_EDGE_M = 0.03
MAX_FRAME_GAP_S = 0.25


def sample_depth(depth_m, pixel):
    """Use a valid center sample; reject holes, range errors and mixed edges.

    The 3x3 neighbourhood is a quality gate, not a hole-filling operation.
    Thresholds are engineering defaults to validate against actual recordings.
    """
    if depth_m is None:
        return None, 'no_depth'
    u, v = pixel
    h, w = depth_m.shape
    if not np.isfinite([u, v]).all() or not (0 <= u <= w - 1 and 0 <= v <= h - 1):
        return None, 'outside_image'
    x, y = int(round(u)), int(round(v))
    z = float(depth_m[y, x])
    if not np.isfinite(z) or z <= 0:
        return None, 'depth_hole'
    if not DEPTH_MIN_M <= z <= DEPTH_MAX_M:
        return None, 'depth_out_of_range'
    patch = depth_m[max(0, y-1):min(h, y+2), max(0, x-1):min(w, x+2)]
    valid = patch[np.isfinite(patch) & (patch > 0)]
    if valid.size < max(1, int(np.ceil(patch.size / 2))):
        return None, 'insufficient_depth'
    if np.ptp(np.percentile(valid, [10, 90])) > DEPTH_EDGE_M:
        return None, 'depth_edge'
    return z, 'ok'


def measure_hand(world_points, pixels, depth_m, deproject, palm_calib_mm=0):
    """Compute both methods on one frame without blending their estimates.

    deproject(pixel, depth_m) returns a point in metres in the aligned depth
    camera frame. MediaPipe world points are in metres about the hand centre.
    """
    pixels = np.asarray(pixels, dtype=float).reshape(21, 2)
    mp_points = np.full((21, 3), np.nan)
    if world_points is not None:
        mp_points[:] = np.asarray(world_points, dtype=float).reshape(21, 3)
    mp_ok = bool(np.isfinite(mp_points[[4, 8]]).all())
    mp_mm = float(np.linalg.norm(mp_points[4] - mp_points[8]) * 1000) if mp_ok else None
    palm_mm = float(np.linalg.norm(mp_points[9] - mp_points[0]) * 1000)
    mp_cal = (mp_mm * palm_calib_mm / palm_mm
              if mp_ok and palm_calib_mm > 0 and np.isfinite(palm_mm) and palm_mm > 1e-6
              else None)
    rs_points = np.full((21, 3), np.nan)
    statuses, depths = [], []
    for i, pixel in enumerate(pixels):
        z, status = sample_depth(depth_m, pixel)
        if status == 'ok':
            if deproject is None:
                status = 'no_intrinsics'
            else:
                try:
                    xyz = np.asarray(deproject(pixel.tolist(), z), dtype=float)
                    if xyz.shape != (3,) or not np.isfinite(xyz).all():
                        raise ValueError('invalid deprojection')
                    rs_points[i] = xyz
                except (RuntimeError, ValueError, TypeError):
                    status = 'deprojection_failed'
        depths.append(z)
        statuses.append(status)
    rs_ok = statuses[4] == statuses[8] == 'ok'
    rs_mm = float(np.linalg.norm(rs_points[4] - rs_points[8]) * 1000) if rs_ok else None
    return dict(mp_points=mp_points, rs_points=rs_points, pixels=pixels,
                mp_valid=mp_ok, rs_valid=rs_ok, mp_aperture_mm=mp_mm,
                mp_aperture_cal_mm=mp_cal, rs_aperture_mm=rs_mm,
                rs_minus_mp_mm=rs_mm-mp_mm if rs_ok and mp_ok else None,
                rs_depth_m=depths, rs_status=statuses)


def contiguous_segments(records, max_gap=MAX_FRAME_GAP_S):
    """Never derive motion across a tracking gap or invalid protocol frame."""
    result, segment = [], []
    for rec in records:
        if not rec.get('protocol_valid', True):
            if segment:
                result.append(segment)
                segment = []
            continue
        missed_frame = (segment and 'frame_id' in rec and 'frame_id' in segment[-1]
                        and rec['frame_id'] != segment[-1]['frame_id'] + 1)
        if segment and (missed_frame or not (0 < rec['time'] - segment[-1]['time'] <= max_gap)):
            result.append(segment)
            segment = []
        segment.append(rec)
    if segment:
        result.append(segment)
    return result


class PairedVideoWriter:
    """Two synchronized AVI files; hold the previous frame during capture gaps.

    Stored videos use an unmirrored, fixed 30 FPS playback timeline. Source
    timestamps and the exact mapped video frame index remain in frames.csv.
    """
    def __init__(self, folder, fps=30.0):
        import cv2
        self.cv = cv2
        self.folder, self.fps = Path(folder), float(fps)
        self.writers = []
        self.names = ('original', 'mediapipe')
        self.frames = 0
        self.first_time = self.last_time = None
        self.previous = None
        self.shape = None

    def write(self, captured, original, annotated):
        if original.shape != annotated.shape or original.ndim != 3 or original.shape[2] != 3:
            raise ValueError('두 영상의 크기와 채널이 일치하지 않습니다.')
        if original.dtype != np.uint8 or annotated.dtype != np.uint8:
            raise ValueError('영상 입력은 uint8 BGR이어야 합니다.')
        if self.last_time is not None and captured < self.last_time:
            raise ValueError('영상 프레임 시각이 역행했습니다.')
        if not self.writers:
            self.shape = original.shape
            h, w = self.shape[:2]
            if h % 2 or w % 2:
                raise ValueError('AVI 녹화에는 짝수 가로·세로 해상도가 필요합니다.')
            self.first_time = captured
            for name in self.names:
                writer = self.cv.VideoWriter(str(self.folder / f'{name}.partial.avi'),
                                             self.cv.VideoWriter_fourcc(*'MJPG'), self.fps, (w, h))
                self.writers.append(writer)
                if not writer.isOpened():
                    raise RuntimeError(f'{name} 영상 저장기를 열 수 없습니다.')
        if original.shape != self.shape:
            raise ValueError('녹화 도중 카메라 해상도가 변경되었습니다.')
        target = max(self.frames, int(round((captured - self.first_time) * self.fps)))
        # Duplicate prior images to retain real elapsed time, rather than playing
        # a slow capture stream several times faster at a nominal 30 FPS.
        while self.frames < target:
            for writer, image in zip(self.writers, self.previous):
                writer.write(image)
            self.frames += 1
        for writer, image in zip(self.writers, (original, annotated)):
            writer.write(image)
        self.frames += 1
        self.previous = (original, annotated)
        self.last_time = captured
        return target

    def close(self):
        for writer in self.writers:
            writer.release()
        summary = dict(codec='MJPG', fps=self.fps, frames=self.frames,
                       first_capture_monotonic_s=self.first_time,
                       duration_s=self.frames / self.fps,
                       timing='Previous frame repeated between captures; exact sample index in frames.csv',
                       files=[], verified=False)
        if not self.frames:
            return summary
        # OpenCV write() has no success return. Reopen both completed streams to
        # detect empty/truncated files before declaring the recording complete.
        for name in self.names:
            path = self.folder / f'{name}.partial.avi'
            reader = self.cv.VideoCapture(str(path))
            try:
                count = int(reader.get(self.cv.CAP_PROP_FRAME_COUNT))
                ok, first = reader.read()
                if not reader.isOpened() or not ok or count != self.frames or first.shape != self.shape:
                    raise RuntimeError(f'{name} 영상 프레임 검증 실패 ({count}/{self.frames})')
                reader.set(self.cv.CAP_PROP_POS_FRAMES, self.frames - 1)
                ok, last = reader.read()
                if not ok or last.shape != self.shape:
                    raise RuntimeError(f'{name} 영상 마지막 프레임을 읽을 수 없습니다.')
            finally:
                reader.release()
        for name in self.names:
            os.replace(self.folder / f'{name}.partial.avi', self.folder / f'{name}.avi')
            summary['files'].append(f'{name}.avi')
        summary['verified'] = True
        return summary


class RawFrameWriter:
    """Bounded background writer. Each acquired frame is a lossless NPZ.

    A full queue is an explicit recording failure, never a silent drop.
    Manifest rows are written only after the corresponding NPZ is complete.
    No Qt, camera or GUI objects cross into the writer thread.
    """
    def __init__(self, folder, max_pending=24, record_videos=False):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=False)
        self.queue = queue.Queue(maxsize=max_pending)
        self.error = None
        self.written = 0
        self.record_videos = record_videos
        self.video_summary = {}
        self._closing = threading.Event()
        self._thread = threading.Thread(target=self._run, name='RawFrameWriter', daemon=False)
        self._thread.start()

    def submit(self, info, arrays):
        if self.error:
            raise RuntimeError(self.error)
        if self._closing.is_set():
            raise RuntimeError('원본 저장기가 이미 종료되었습니다.')
        # Caller hands over owned, immutable arrays (never a camera-backed view).
        try:
            self.queue.put_nowait((dict(info), arrays))
        except queue.Full as exc:
            self.error = '원본 저장 속도가 촬영을 따라가지 못했습니다. 세션을 중단합니다.'
            raise RuntimeError(self.error) from exc

    def close(self):
        self._closing.set()
        self._thread.join()
        return dict(format='per_frame_lossless_npz', written_frames=self.written,
                    videos=self.video_summary, error=self.error, complete=self.error is None)

    @staticmethod
    def _write_archive(out, arrays, info):
        # Avoid expensive zlib compression of colour noise on the capture path.
        # Depth/metadata use fast lossless compression; colour remains lossless.
        with zipfile.ZipFile(out, 'w', allowZip64=True) as archive:
            for name, array in dict(arrays, metadata_json=np.array(json.dumps(info, ensure_ascii=False))).items():
                if name == 'overlay_bgr':
                    continue  # Already retained in the separate playable video.
                data = io.BytesIO()
                np.save(data, array, allow_pickle=False)
                archive.writestr(f'{name}.npy', data.getvalue(), compresslevel=1,
                                 compress_type=zipfile.ZIP_STORED if name == 'color_bgr' else zipfile.ZIP_DEFLATED)

    def _run(self):
        video = None
        try:
            if self.record_videos:
                video = PairedVideoWriter(self.folder.parent)
            with (self.folder / 'frames.csv').open('x', newline='', encoding='utf-8-sig') as fp:
                fields = ['frame_id', 'capture_monotonic_s', 'capture_unix_s',
                          'color_frame_number', 'color_timestamp_ms', 'color_timestamp_domain',
                          'depth_frame_number', 'depth_timestamp_ms', 'depth_timestamp_domain',
                          'video_frame_index', 'file']
                writer = csv.DictWriter(fp, fields, extrasaction='ignore')
                writer.writeheader()
                while not self._closing.is_set() or not self.queue.empty():
                    try:
                        info, arrays = self.queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if video:
                        info['video_frame_index'] = video.write(info['capture_monotonic_s'],
                                                                arrays['color_bgr'], arrays['overlay_bgr'])
                    name = f"frame_{info['frame_id']:08d}.npz"
                    path = self.folder / name
                    temporary = self.folder / (name + '.partial')
                    with temporary.open('xb') as out:
                        self._write_archive(out, arrays, info)
                    os.replace(temporary, path)
                    writer.writerow(dict(info, file=name))
                    fp.flush()
                    self.written += 1
        except Exception as exc:
            self.error = f'원본 저장 실패: {exc}'
        finally:
            if video:
                try:
                    self.video_summary = video.close()
                except Exception as exc:
                    self.video_summary = dict(verified=False, error=str(exc))
                    self.error = f'{self.error or ""} 영상 저장 실패: {exc}'.strip()

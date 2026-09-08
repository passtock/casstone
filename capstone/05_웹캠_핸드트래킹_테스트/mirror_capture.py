"""Camera-independent measurement and lossless frame recording helpers.

All pixels/XYZ refer to the unmirrored camera image. Missing measurements
stay NaN internally and are exported as empty CSV cells, never as zero.
"""
import csv
import json
import os
import queue
import threading
import time
import io
import zipfile
from pathlib import Path

import numpy as np
from mirror_mjpeg import MjpegAvi

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
    def __init__(self, folder, fps=30.0, part_bytes=1024**3, part_seconds=60.0):
        import cv2
        self.cv = cv2
        self.folder, self.fps = Path(folder), float(fps)
        if not np.isfinite(self.fps) or self.fps <= 0:
            raise ValueError('fps must be finite and positive')
        if not np.isfinite(part_seconds) or part_seconds <= 0 or part_bytes <= 0:
            raise ValueError('part limits must be positive')
        self.part_seconds = float(part_seconds)
        self.writers = []
        self.names = ('original', 'mediapipe')
        self.frames = 0
        self.first_time = self.last_time = None
        self.previous = None
        self.shape = None
        self.part_bytes = part_bytes
        self.parts = []
        self.part_start = 0
        self.jpeg_encodes = 0
        self.resampled_sources = 0
        self.source_in_video = False

    def _names(self):
        suffix = '' if not self.parts else f'_part{len(self.parts)+1:03d}'
        return [name + suffix for name in self.names]

    def _open_part(self):
        h, w = self.shape[:2]
        for name in self._names():
            self.writers.append(MjpegAvi(self.folder / f'{name}.partial.avi', w, h, self.fps))
        self.part_start = self.frames

    def _append(self, packets):
        if self.writers and self.frames > self.part_start and (
                (self.frames - self.part_start) / self.fps >= self.part_seconds or any(
                writer.projected_size(packet) > self.part_bytes
                for writer, packet in zip(self.writers, packets))):
            self._close_part()
        if not self.writers:
            self._open_part()
        for writer, packet in zip(self.writers, packets):
            writer.write(packet)
        self.frames += 1

    def write(self, captured, original, annotated):
        if not np.isfinite(captured):
            raise ValueError('영상 프레임 시각이 유효하지 않습니다.')
        if original.shape != annotated.shape or original.ndim != 3 or original.shape[2] != 3:
            raise ValueError('두 영상의 크기와 채널이 일치하지 않습니다.')
        if original.dtype != np.uint8 or annotated.dtype != np.uint8:
            raise ValueError('영상 입력은 uint8 BGR이어야 합니다.')
        if self.last_time is not None and captured < self.last_time:
            raise ValueError('영상 프레임 시각이 역행했습니다.')
        if self.shape is None:
            self.shape = original.shape
            h, w = self.shape[:2]
            if h % 2 or w % 2:
                raise ValueError('AVI 녹화에는 짝수 가로·세로 해상도가 필요합니다.')
            self.first_time = captured
        if original.shape != self.shape:
            raise ValueError('녹화 도중 카메라 해상도가 변경되었습니다.')
        target = max(0, int(round((captured - self.first_time) * self.fps)))
        self.source_in_video = target >= self.frames
        if not self.source_in_video:
            # More than one source can fall in a 30-Hz playback slot. Retain
            # every source in NPZ, but never lengthen playback to fit them all.
            self.resampled_sources += 1
            self.last_time = captured
            return self.frames - 1
        # Encode a source image ONCE. Gap frames reuse the compressed packet,
        # preserving elapsed time without repeatedly doing full JPEG encoding.
        packets = []
        for image in (original, annotated):
            ok, data = self.cv.imencode('.jpg', image, [self.cv.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                raise RuntimeError('MJPEG 영상 압축에 실패했습니다.')
            packets.append(data.tobytes())
            self.jpeg_encodes += 1
        while self.frames < target:
            self._append(self.previous)
        self._append(packets)
        self.previous = packets
        self.last_time = captured
        return target

    def _close_part(self):
        if not self.writers:
            return
        errors = []
        for writer in self.writers:
            try:
                writer.release()
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise RuntimeError(f'AVI 파일 마무리 실패: {errors[0]}')
        part_frames = self.frames - self.part_start
        names = self._names()
        for name in names:
            path = self.folder / f'{name}.partial.avi'
            reader = self.cv.VideoCapture(str(path))
            try:
                count = int(reader.get(self.cv.CAP_PROP_FRAME_COUNT))
                ok, first = reader.read()
                if not reader.isOpened() or not ok or count != part_frames or first.shape != self.shape:
                    raise RuntimeError(f'{name} 영상 프레임 검증 실패 ({count}/{part_frames})')
                reader.set(self.cv.CAP_PROP_POS_FRAMES, part_frames - 1)
                ok, last = reader.read()
                if not ok or last.shape != self.shape:
                    raise RuntimeError(f'{name} 영상 마지막 프레임을 읽을 수 없습니다.')
            finally:
                reader.release()
        for name in names:
            os.replace(self.folder / f'{name}.partial.avi', self.folder / f'{name}.avi')
        self.parts.append(dict(first_video_frame=self.part_start, frames=part_frames,
                               files=[f'{name}.avi' for name in names]))
        self.writers = []

    def close(self):
        self._close_part()
        summary = dict(codec='MJPG', fps=self.fps, frames=self.frames,
                       first_capture_monotonic_s=self.first_time,
                       duration_s=self.frames / self.fps,
                       timing='Previous frame repeated between captures; exact sample index in frames.csv',
                       files=[name for part in self.parts for name in part['files']],
                       parts=self.parts, jpeg_encodes=self.jpeg_encodes,
                       resampled_sources=self.resampled_sources,
                       part_seconds=self.part_seconds, part_bytes=self.part_bytes,
                       verified=bool(self.frames))
        if not self.frames:
            return summary
        return summary


class RawFrameWriter:
    """Bounded background writer. Each acquired frame is a lossless NPZ.

    A full queue is an explicit recording failure, never a silent drop.
    Manifest rows are written only after the corresponding NPZ is complete.
    No Qt, camera or GUI objects cross into the writer thread.
    """
    def __init__(self, folder, max_pending=8, record_videos=False, *, compression='stored',
                 video_part_seconds=60.0):
        if compression not in ('stored', 'deflated'):
            raise ValueError('compression must be stored or deflated')
        if max_pending <= 0:
            raise ValueError('max_pending must be positive')
        self.compression = compression
        self.video_part_seconds = video_part_seconds
        self.archive_bytes = 0
        self.write_seconds_total = self.write_seconds_max = 0.0
        self.queue_high_water = 0
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=False)
        self.queue = queue.Queue(maxsize=max_pending)
        self.error = None
        self.written = 0
        self.received = 0
        self.started = time.perf_counter()
        self.last_write = None
        self.record_videos = record_videos
        self.video_summary = {}
        self._closing = threading.Event()
        self._thread = threading.Thread(target=self._run, name='RawFrameWriter', daemon=False)
        self._thread.start()

    def status(self):
        return dict(received=self.received, written=self.written,
                    pending=max(0, self.received - self.written), capacity=self.queue.maxsize,
                    backpressure=self.queue.full(), error=self.error,
                    write_fps=self.written / max(time.perf_counter() - self.started, .001),
                    compression=self.compression, archive_bytes=self.archive_bytes,
                    write_seconds_total=self.write_seconds_total,
                    write_seconds_max=self.write_seconds_max,
                    queue_high_water=self.queue_high_water,
                    last_write_monotonic_s=self.last_write)

    def ready(self):
        """Single producer checks BEFORE acquiring a camera frame; never drops data."""
        if self.error:
            raise RuntimeError(self.error)
        return not self.queue.full() and not self._closing.is_set()

    def submit(self, info, arrays):
        if self.error:
            raise RuntimeError(self.error)
        if self._closing.is_set():
            raise RuntimeError('원본 저장기가 이미 종료되었습니다.')
        # Caller hands over owned, immutable arrays (never a camera-backed view).
        try:
            self.queue.put_nowait((dict(info), arrays))
            self.received += 1
            self.queue_high_water = max(self.queue_high_water, self.queue.qsize())
        except queue.Full as exc:
            self.error = '원본 저장 속도가 촬영을 따라가지 못했습니다. 세션을 중단합니다.'
            raise RuntimeError(self.error) from exc

    def close(self):
        self._closing.set()
        self._thread.join()
        if self.received != self.written and not self.error:
            self.error = f'원본 프레임 수 불일치: 저장 {self.written} / 수신 {self.received}'
        if not self.written and not self.error:
            self.error = '수신·저장된 원본 프레임이 없습니다. 카메라 연결을 확인해주세요.'
        if self.record_videos and not self.video_summary.get('verified') and not self.error:
            self.error = '재생용 영상 검증이 완료되지 않았습니다.'
        return dict(format='per_frame_lossless_npz', written_frames=self.written,
                    received_frames=self.received,
                    diagnostics=self.status(),
                    videos=self.video_summary, error=self.error, complete=self.error is None)

    @staticmethod
    def _write_archive(out, arrays, info, compression='stored'):
        # Stored NPY arrays remain bit-exact. No per-frame zlib CPU spikes.
        method = zipfile.ZIP_STORED if compression == 'stored' else zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(out, 'w', allowZip64=True, compression=method,
                             compresslevel=1 if compression == 'deflated' else None) as archive:
            for name, array in dict(arrays, metadata_json=np.array(json.dumps(info, ensure_ascii=False))).items():
                if name == 'overlay_bgr':
                    continue  # Already retained in the separate playable video.
                data = io.BytesIO()
                np.save(data, array, allow_pickle=False)
                archive.writestr(f'{name}.npy', data.getvalue())

    def _run(self):
        video = None
        try:
            if self.record_videos:
                video = PairedVideoWriter(self.folder.parent, part_seconds=self.video_part_seconds)
            with (self.folder / 'frames.csv').open('x', newline='', encoding='utf-8-sig') as fp:
                fields = ['frame_id', 'capture_monotonic_s', 'capture_unix_s',
                          'color_frame_number', 'color_timestamp_ms', 'color_timestamp_domain',
                          'depth_frame_number', 'depth_timestamp_ms', 'depth_timestamp_domain',
                          'video_frame_index', 'video_part', 'video_part_frame_index',
                          'video_source_present', 'file']
                writer = csv.DictWriter(fp, fields, extrasaction='ignore')
                writer.writeheader()
                while not self._closing.is_set() or not self.queue.empty():
                    try:
                        info, arrays = self.queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    write_started = time.perf_counter()
                    if video:
                        info['video_frame_index'] = video.write(info['capture_monotonic_s'],
                                                                arrays['color_bgr'], arrays['overlay_bgr'])
                        info['video_part'] = len(video.parts) + 1
                        info['video_part_frame_index'] = info['video_frame_index'] - video.part_start
                        info['video_source_present'] = int(video.source_in_video)
                    name = f"frame_{info['frame_id']:08d}.npz"
                    path = self.folder / name
                    temporary = self.folder / (name + '.partial')
                    with temporary.open('xb') as out:
                        self._write_archive(out, arrays, info, self.compression)
                    os.replace(temporary, path)
                    writer.writerow(dict(info, file=name))
                    self.written += 1
                    # Bounded flush interval instead of one filesystem flush per frame.
                    if self.written % 8 == 0 or self.queue.empty():
                        fp.flush()
                    self.last_write = time.perf_counter()
                    elapsed = self.last_write - write_started
                    self.write_seconds_total += elapsed
                    self.write_seconds_max = max(self.write_seconds_max, elapsed)
                    self.archive_bytes += path.stat().st_size
        except Exception as exc:
            self.error = f'원본 저장 실패: {exc}'
        finally:
            if video:
                try:
                    self.video_summary = video.close()
                except Exception as exc:
                    self.video_summary = dict(verified=False, error=str(exc))
                    self.error = f'{self.error or ""} 영상 저장 실패: {exc}'.strip()

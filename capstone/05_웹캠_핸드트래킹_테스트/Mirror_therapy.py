import os
os.environ.update({'TF_ENABLE_ONEDNN_OPTS': '0', 'TF_CPP_MIN_LOG_LEVEL': '2',
                   'QT_ENABLE_HIGHDPI_SCALING': '1', 'QT_AUTO_SCREEN_SCALE_FACTOR': '1'})

import sys, csv, json, time, math, queue, re, hashlib, uuid
from datetime import datetime
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mirror_capture import (RawFrameWriter, measure_hand, contiguous_segments,
                            MAX_FRAME_GAP_S, DEPTH_MIN_M, DEPTH_MAX_M, DEPTH_EDGE_M)

try:
    import pyrealsense2 as rs
except Exception:
    rs = None

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QRadioButton, QButtonGroup,
    QPushButton, QGroupBox, QFrame, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QSizePolicy,
    QTabWidget, QLayout)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# ================================ 설정 ================================
RS_W, RS_H, RS_FPS = 1280, 720, 30
RS_DW, RS_DH = 848, 480          # 원본 depth; 컬러에 정렬 후 손끝 3D 계산
DEPTH_VIS_MIN, DEPTH_VIS_MAX = 0.4, 1.5
VIEW_COLOR, VIEW_DEPTH, VIEW_BOTH = "color", "depth", "both"

PALM_IDS = [0, 1, 5, 9, 13, 17]   # 3D 뷰 손바닥 메시 표시용
# 정준 좌표계 기준 평면에서는 엄지 CMC(1)를 뺀다. 1번은 엄지 외전/대립 시
# 함께 움직여, 측정하려는 자유도가 기준면 자체를 흔들기 때문이다.
FRAME_IDS = [0, 5, 9, 13, 17]
LM_SMOOTH_DEFAULT = True
HOLD_MOTION_DEFAULT = False      # 팔 고정 과제에서는 OFF (오검출만 남음)
HOLD_MOTION_PX = 28.0
VIEW3D_INTERVAL, VIEW3D_R, VIEW3D_ALPHA = 0.20, 1.25, 0.15
APERTURE_MAX_CM, APERTURE_CUTOFF, APERTURE_BETA = 30.0, 0.8, 0.02
CYCLE_HYST, CYCLE_MIN_RANGE = 0.15, 15.0
AUTO_TRIAL_SEC = 5.0             # 비장애인 대조군: 버튼 1회 = 고정 시간 자동 측정
LM_XY = (0.4, 0.08, 1.2)         # (min_cutoff, beta, d_cutoff)
LM_Z = (0.15, 0.002, 0.8)        # z는 단안 깊이 노이즈가 커서 강하게 억제

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
HANDS = ('Right', 'Left')
HAND_KR = {'Right': '오른손 (Right)', 'Left': '왼손 (Left)'}

JOINT_DEFS = {
    'Thumb_CMC': (0, 1, 2), 'Thumb_MCP': (1, 2, 3), 'Thumb_IP': (2, 3, 4),
    'Index_MCP': (0, 5, 6), 'Index_PIP': (5, 6, 7), 'Index_DIP': (6, 7, 8),
    'Middle_MCP': (0, 9, 10), 'Middle_PIP': (9, 10, 11), 'Middle_DIP': (10, 11, 12),
    'Ring_MCP': (0, 13, 14), 'Ring_PIP': (13, 14, 15), 'Ring_DIP': (14, 15, 16),
    'Pinky_MCP': (0, 17, 18), 'Pinky_PIP': (17, 18, 19), 'Pinky_DIP': (18, 19, 20),
}
FLEX_OF = {'Thumb': 'Thumb_IP', 'Index': 'Index_PIP', 'Middle': 'Middle_PIP',
           'Ring': 'Ring_PIP', 'Pinky': 'Pinky_PIP'}

# 손가락별 (근위, 중간, 원위) 3단. 엄지는 (CMC, MCP, IP)로 대응시킨다.
JOINT_TRIPLE = {
    'Thumb':  ('Thumb_CMC',  'Thumb_MCP',  'Thumb_IP'),
    'Index':  ('Index_MCP',  'Index_PIP',  'Index_DIP'),
    'Middle': ('Middle_MCP', 'Middle_PIP', 'Middle_DIP'),
    'Ring':   ('Ring_MCP',   'Ring_PIP',   'Ring_DIP'),
    'Pinky':  ('Pinky_MCP',  'Pinky_PIP',  'Pinky_DIP'),
}

# TAM 합산은 ASSH 정의: 엄지는 MCP + IP만, CMC는 별도 지표로 분리 보고.
TAM_JOINTS = {f: tuple(j for j in js if j) for f, js in JOINT_TRIPLE.items()}
TAM_JOINTS['Thumb'] = ('Thumb_MCP', 'Thumb_IP')

# 0°가 결측이 아니라 정상값인 각도들 (AngleFilter의 홀딩 로직을 쓰면 안 됨)
ABD_KEYS = ('Thumb_PalmarAbd', 'Thumb_RadialAbd')

SEG_LABELS = ('MCP', 'PIP', 'DIP')          # 게이지 행 식별자 (엄지는 CMC/MCP/IP)
SEG_COLORS = {'MCP': '#38bdf8', 'PIP': '#22c55e', 'DIP': '#f59e0b'}

CYCLE_JOINTS = ('Index_PIP', 'Middle_PIP', 'Ring_PIP', 'Pinky_PIP')
FINGER_COLORS = {'Thumb': '#ef4444', 'Index': '#0ea5e9', 'Middle': '#22c55e',
                 'Ring': '#f59e0b', 'Pinky': '#a855f7'}
LM_NAMES = ["Wrist", "Thumb_CMC", "Thumb_MCP", "Thumb_IP", "Thumb_TIP",
            "Index_MCP", "Index_PIP", "Index_DIP", "Index_TIP",
            "Middle_MCP", "Middle_PIP", "Middle_DIP", "Middle_TIP",
            "Ring_MCP", "Ring_PIP", "Ring_DIP", "Ring_TIP",
            "Pinky_MCP", "Pinky_PIP", "Pinky_DIP", "Pinky_TIP"]


# ============================== 필터 ==============================
class OneEuro:
    def __init__(self, x0=0.0, min_cutoff=0.7, beta=0.015, d_cutoff=1.0, t0=None):
        self.mc, self.beta, self.dc = float(min_cutoff), float(beta), float(d_cutoff)
        self.x, self.dx, self.t = float(x0), 0.0, t0

    @staticmethod
    def _a(te, cutoff):
        r = 2 * math.pi * cutoff * te
        return r / (r + 1)

    def filter(self, t, x):
        if self.t is None:
            self.t, self.x = t, float(x)
            return self.x
        te = t - self.t
        if te <= 1e-5:
            return self.x
        dx = (x - self.x) / te
        self.dx = self._a(te, self.dc) * dx + (1 - self._a(te, self.dc)) * self.dx
        a = self._a(te, self.mc + self.beta * abs(self.dx))
        self.x = a * x + (1 - a) * self.x
        self.t = t
        return self.x


class LandmarkSmoother:
    """21x3 좌표를 각각 One-Euro로 평활화. 각도 계산 전에 걸어야
    arccos 비선형성에 의한 계단형 스텝이 생기지 않는다."""

    def __init__(self):
        self.f = [[OneEuro(min_cutoff=c[0], beta=c[1], d_cutoff=c[2])
                   for c in (LM_XY, LM_XY, LM_Z)] for _ in range(21)]

    def smooth(self, t, pts):
        out = np.empty_like(pts)
        for i in range(21):
            for j in range(3):
                out[i, j] = self.f[i][j].filter(t, float(pts[i, j]))
        return out


class AngleFilter:
    """각도용: 스파이크 클램프 + One-Euro + 가려짐 홀딩."""

    def __init__(self, init_val=180.0):
        self.last = float(init_val)
        self.missing = 0
        self.euro = OneEuro(x0=init_val, min_cutoff=0.7, beta=0.015, t0=0.0)

    def update(self, t, v, hold=False):
        if hold:
            self.euro.t = t
            return self.last
        if v is None or not np.isfinite(v) or v <= 0.0:
            self.missing += 1
            if self.missing > 12:
                self.last = 0.95 * self.last + 0.05 * 160.0
            return self.last
        self.missing = 0
        d = v - self.last
        if abs(d) > 30.0:
            v = self.last + math.copysign(30.0, d)
        self.last = min(180.0, max(0.0, self.euro.filter(t, v)))
        return self.last


class ApertureFilter:
    """0이 정상값인 양(파지폭·외전각) 전용. 각도 필터는 raw<=0을 결측으로
    보고 홀딩하는데, 이 값들은 0 근처가 오히려 핵심 구간이라 얼어붙는다."""

    def __init__(self, init_val=0.0, vmax=APERTURE_MAX_CM,
                 cutoff=APERTURE_CUTOFF, beta=APERTURE_BETA):
        self.vmax = float(vmax)
        self.euro = OneEuro(x0=init_val, min_cutoff=cutoff, beta=beta)
        self.last = float(init_val)

    def update(self, t, v):
        if v is None or not np.isfinite(v):
            return self.last
        v = min(self.vmax, max(0.0, float(v)))
        self.last = min(self.vmax, max(0.0, self.euro.filter(t, v)))
        return self.last


# =========================== 기하 / 지표 ===========================
def angle3(a, b, c):
    ba, bc = a - b, c - b
    n1, n2 = np.linalg.norm(ba), np.linalg.norm(bc)
    if n1 < 1e-7 or n2 < 1e-7:
        return 180.0
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / (n1 * n2), -1, 1))))


def joint_angles(pts):
    a = {n: angle3(pts[i], pts[j], pts[k]) for n, (i, j, k) in JOINT_DEFS.items()}
    a.update({f"{f}_Flexion": a[j] for f, j in FLEX_OF.items()})
    return a


def palm_frame(pts):
    """손바닥 5점(엄지 CMC 제외) SVD 평면으로 손 고유축 R을 만들고
    손목 원점·손 길이 1.0으로 정규화."""
    c = pts[FRAME_IDS].mean(axis=0)
    normal = np.linalg.svd(pts[FRAME_IDS] - c)[2][2]
    if np.dot(normal, np.cross(pts[5] - pts[0], pts[17] - pts[0])) < 0:
        normal = -normal
    vy = pts[9] - pts[0]
    ny = float(np.linalg.norm(vy))
    if ny < 1e-7:
        return pts, np.eye(3), ny
    uy = vy / ny
    uy = uy - np.dot(uy, normal) * normal
    uy /= (np.linalg.norm(uy) + 1e-7)
    ux = np.cross(uy, normal)
    ux /= (np.linalg.norm(ux) + 1e-7)
    R = np.vstack([ux, uy, normal])
    return (R @ (pts - pts[0]).T).T / ny, R, ny


def thumb_abduction(canon):
    """정준 손바닥 좌표계에서 제1중수골(1->2)을 2자유도로 분해한다.
      palmar : 손바닥 평면 밖으로 나가는 각 (장측 외전, palmar abduction)
      radial : 손바닥 평면 안에서 제2중수골(0->5)과 이루는 각
               (요측 외전 = 제1-2 중수골간 각, intermetacarpal angle)
    좌/우 손은 정준계 손잡이(handedness)가 뒤집히므로 부호 대신 크기로 낸다.
    -> 좌우 대응 오차(MAE/RMSE)에 그대로 쓸 수 있다."""
    v = canon[2] - canon[1]
    n = float(np.linalg.norm(v))
    if n < 1e-7:
        return None, None
    v = v / n
    palmar = float(np.degrees(np.arcsin(np.clip(abs(v[2]), -1.0, 1.0))))
    vp = np.array([v[0], v[1], 0.0])
    ref = canon[5] - canon[0]
    ref = np.array([ref[0], ref[1], 0.0])
    nv, nr = np.linalg.norm(vp), np.linalg.norm(ref)
    if nv < 1e-7 or nr < 1e-7:
        return palmar, None
    radial = float(np.degrees(np.arccos(np.clip(np.dot(vp, ref) / (nv * nr), -1.0, 1.0))))
    return palmar, radial


def _mono(t):
    t = np.asarray(t, float)
    return t if len(t) < 2 else np.maximum.accumulate(t + np.arange(len(t)) * 1e-9)


def ang_velocity(times, vals):
    if len(times) < 5 or len(times) != len(vals):
        return None
    t, v = _mono(times), np.asarray(vals, float)
    if np.any(np.diff(t) <= 0) or not np.all(np.isfinite(v)):
        return None
    return np.gradient(v, t)


def count_cycles(times, flex):
    """굴곡각(180=신전)에서 '펴짐->쥠->펴짐'을 히스테리시스로 센다."""
    a = np.asarray(flex, float)
    if len(a) < 15:
        return 0, None
    lo, hi = np.percentile(a, 5), np.percentile(a, 95)
    rng = hi - lo
    if rng < CYCLE_MIN_RANGE:
        return 0, None
    hi_th, lo_th = lo + rng * (0.5 + CYCLE_HYST), lo + rng * (0.5 - CYCLE_HYST)
    # 처음부터 쥔 손을 펴는 반동작은 한 사이클로 세지 않는다.
    state, marks = ('open' if a[0] > hi_th else 'waiting_open'), []
    for ti, v in zip(times, a):
        if state == 'waiting_open' and v > hi_th:
            state = 'open'
        elif state == 'open' and v < lo_th:
            state = 'closed'
        elif state == 'closed' and v > hi_th:
            state = 'open'
            marks.append(float(ti))
    return len(marks), (float(np.mean(np.diff(marks))) if len(marks) >= 2 else None)


def sparc(vel, times, fc=10.0):
    """Spectral arc length. 0에 가까울수록 부드럽다."""
    if vel is None or len(vel) < 20 or np.all(np.abs(vel) < 1e-4):
        return None
    dt = float(np.mean(np.diff(_mono(times))))
    if not np.isfinite(dt) or dt <= 0:
        return None
    mag = np.abs(np.fft.rfft(vel))
    fr = np.fft.rfftfreq(len(vel), d=dt)
    m = fr <= fc
    f_s, m_s = fr[m], mag[m]
    if len(f_s) < 3 or float(np.max(m_s)) < 1e-7:
        return None
    m_s = m_s / np.max(m_s)
    return float(-np.sum(np.sqrt((np.diff(f_s) / fc) ** 2 + np.diff(m_s) ** 2)))


# ============================ 비디오 스레드 ============================
class VideoWorker(QThread):
    frame_processed = pyqtSignal(np.ndarray, dict, float, int, dict, dict, dict)
    recording_finished = pyqtSignal(str, dict)
    failed = pyqtSignal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index, self.running = camera_index, True
        self.mirror_mode = self.hold_motion = False
        self.use_filter = self.enable_3d = True
        self.smooth_3d = LM_SMOOTH_DEFAULT
        self.view_mode, self.source_name = VIEW_COLOR, "webcam"
        self.filters, self.ap_filters, self.smoothers, self.prev_px = {}, {}, {}, {}
        self.depth_scale, self.latest_depth, self.depth_filters = 1.0, None, None
        self.palm_calib_mm = 0.0
        self.t0 = time.perf_counter()
        self.commands = queue.Queue()
        self.recorder, self.session_id = None, None
        self.frame_id = 0
        self.camera_info = {}

    def _reset_state(self):
        self.filters, self.ap_filters, self.smoothers, self.prev_px = {}, {}, {}, {}

    def set_mirror_mode(self, v):
        self.commands.put(('setting', 'mirror_mode', bool(v)))

    def set_filter_mode(self, v):
        self.commands.put(('setting', 'use_filter', bool(v)))

    def set_view_mode(self, v):
        self.commands.put(('setting', 'view_mode', v))

    def set_enable_3d(self, v):
        self.commands.put(('setting', 'enable_3d', bool(v)))

    def set_smooth_3d(self, v):
        self.commands.put(('setting', 'smooth_3d', bool(v)))

    def set_palm_calib(self, mm):
        self.commands.put(('setting', 'palm_calib_mm', float(mm or 0.0)))

    def set_hold_motion(self, v):
        self.commands.put(('setting', 'hold_motion', bool(v)))

    def begin_recording(self, session_id, folder):
        self.commands.put(('start', session_id, folder))

    def end_recording(self):
        self.commands.put(('stop',))

    def _end_recording(self):
        if self.session_id is None:
            return
        session_id, self.session_id = self.session_id, None
        summary = (self.recorder.close() if self.recorder else
                   dict(complete=False, written_frames=0, error='원본 저장 시작 실패'))
        self.recorder = None
        summary['camera_info'] = self.camera_info
        self.recording_finished.emit(session_id, summary)

    def _apply_commands(self):
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                return
            if command[0] == 'setting':
                _, key, value = command
                setattr(self, key, value)
                if key in ('smooth_3d', 'use_filter', 'hold_motion'):
                    self._reset_state()
            elif command[0] == 'start':
                self._end_recording()
                _, self.session_id, folder = command
                self.recorder = RawFrameWriter(os.path.join(folder, 'raw_frames'), record_videos=True)
                self._reset_state()
            elif command[0] == 'stop':
                self._end_recording()

    @staticmethod
    def _intrinsics_dict(intr):
        return dict(width=intr.width, height=intr.height, fx=intr.fx, fy=intr.fy,
                    ppx=intr.ppx, ppy=intr.ppy, model=str(intr.model), coeffs=list(intr.coeffs))

    @staticmethod
    def _deproject(intr, pixel, depth):
        # SDK deprojection does not support modified Brown-Conrady directly.
        if intr.model == rs.distortion.modified_brown_conrady:
            K = np.array([[intr.fx, 0, intr.ppx], [0, intr.fy, intr.ppy], [0, 0, 1.]])
            xy = cv2.undistortPoints(np.array([[pixel]], dtype=float), K,
                                     np.asarray(intr.coeffs, dtype=float))[0, 0]
            return [xy[0] * depth, xy[1] * depth, depth]
        return rs.rs2_deproject_pixel_to_point(intr, pixel, depth)

    # ---------------- RealSense ----------------
    def _open_realsense(self):
        if rs is None:
            print("[안내] pyrealsense2 미설치 → 웹캠으로 동작합니다.")
            return None
        pipe = None
        try:
            if len(rs.context().query_devices()) == 0:
                print("[안내] RealSense 장치 없음 → 웹캠으로 폴백합니다.")
                return None
            pipe, cfg = rs.pipeline(), rs.config()
            cfg.enable_stream(rs.stream.color, RS_W, RS_H, rs.format.bgr8, RS_FPS)
            cfg.enable_stream(rs.stream.depth, RS_DW, RS_DH, rs.format.z16, RS_FPS)
            prof = pipe.start(cfg)
            sensor = prof.get_device().first_depth_sensor()
            self.depth_scale = float(sensor.get_depth_scale())
            cp = prof.get_stream(rs.stream.color).as_video_stream_profile()
            dp = prof.get_stream(rs.stream.depth).as_video_stream_profile()
            extr = dp.get_extrinsics_to(cp)
            self.camera_info = dict(
                source='realsense', depth_scale_m=self.depth_scale,
                color_intrinsics=self._intrinsics_dict(cp.get_intrinsics()),
                depth_intrinsics=self._intrinsics_dict(dp.get_intrinsics()),
                depth_to_color=dict(rotation=list(extr.rotation), translation=list(extr.translation)),
                color_fps=cp.fps(), depth_fps=dp.fps())
            try:
                if sensor.supports(rs.option.visual_preset):
                    sensor.set_option(rs.option.visual_preset,
                                      float(rs.rs400_visual_preset.high_accuracy))
            except Exception:
                pass
            spat, temp = rs.spatial_filter(), rs.temporal_filter()
            spat.set_option(rs.option.holes_fill, 1)
            self.depth_filters = [spat, temp]
            for _ in range(15):
                pipe.wait_for_frames()
            self.source_name = "realsense"
            print(f"[RealSense] 연결됨 | color {RS_W}x{RS_H} / depth {RS_DW}x{RS_DH}")
            return pipe, rs.align(rs.stream.color)
        except Exception as e:
            if pipe is not None:
                try:
                    pipe.stop()
                except Exception:
                    pass
            print(f"[경고] RealSense 초기화 실패 ({e}) → 웹캠으로 폴백합니다.")
            return None

    def _colorize_depth(self, d):
        norm = np.clip((d - DEPTH_VIS_MIN) / (DEPTH_VIS_MAX - DEPTH_VIS_MIN), 0, 1)
        vis = cv2.applyColorMap(((1 - norm) * 255).astype(np.uint8), cv2.COLORMAP_JET)
        vis[d <= 0] = (0, 0, 0)
        return vis

    def depth_at(self, px, py, win=9):
        """화면 좌표 기준 거리(m). 유효값 없으면 None."""
        if self.latest_depth is None:
            return None
        h, w = self.latest_depth.shape[:2]
        if not np.isfinite([px, py]).all() or not (0 <= px < w and 0 <= py < h):
            return None
        x, y, r = int(round(px)), int(round(py)), win // 2
        p = self.latest_depth[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)]
        v = p[p > 0]
        return float(np.median(v)) if v.size else None

    # ---------------- 3D 재구성 ----------------
    def build_3d(self, hand, world_lm, t, wrist_depth):
        # 표시 체크박스와 무관하게 측정·저장은 계속한다.
        if world_lm is None:
            return None
        raw = np.array([[l.x, l.y, l.z] for l in world_lm], dtype=np.float64)
        if self.smooth_3d:
            self.smoothers.setdefault(hand, LandmarkSmoother())
            pts, mode = self.smoothers[hand].smooth(t, raw), '정규화 3D'
        else:
            pts, mode = raw, '원본 3D'

        canon, R, palm_len = palm_frame(pts)
        angles = joint_angles(canon)
        angles['Grip_Aperture_pctPalm'] = float(np.linalg.norm(canon[4] - canon[8]) * 100)
        pab, rab = thumb_abduction(canon)
        angles['Thumb_PalmarAbd'] = pab
        angles['Thumb_RadialAbd'] = rab
        # 표시용은 R.T로 카메라 정렬로 되돌린다 (R이 상쇄되어 (pts-손목)/손길이와 같음)
        disp = (R.T @ canon.T).T
        if not np.all(np.isfinite(disp)):
            return None

        palm_mm, ap_mm = palm_len * 1000.0, float(np.linalg.norm(pts[4] - pts[8]) * 1000)
        # 모델의 손 크기는 '평균적인 손'이라 절대 mm로 보기 어렵다 -> 실측 손 길이로 보정
        ap_cal = (ap_mm * self.palm_calib_mm / palm_mm
                  if self.palm_calib_mm > 0 and palm_mm > 1e-6 else None)

        return {'points': disp, 'canon': canon, 'angles': angles, 'mode': mode,
                'metrics': {'mode': mode, 'wrist_dist_m': wrist_depth,
                            'aperture_mm': ap_mm, 'aperture_mm_cal': ap_cal,
                            'aperture_pct_palm': angles['Grip_Aperture_pctPalm'],
                            'palm_len_mm': palm_mm,
                            'thumb_palmar_abd': pab, 'thumb_radial_abd': rab}}

    def _moved(self, hand, x, y):
        """화면상 손목 픽셀 이동량으로 팔 이동을 감지 (world landmark는 병진 불변이라 부적합)."""
        prev = self.prev_px.get(hand)
        self.prev_px[hand] = (x, y)
        if not self.hold_motion or prev is None:
            return False
        return math.hypot(x - prev[0], y - prev[1]) > HOLD_MOTION_PX

    # ---------------- 메인 루프 ----------------
    def run(self):
        pipe = align = cap = hands = None
        try:
            got = self._open_realsense()
            if got:
                pipe, align = got
            else:
                self.source_name = 'webcam'
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(self.camera_index)
                if not cap.isOpened():
                    raise RuntimeError(f"카메라 {self.camera_index}번을 열 수 없습니다.")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, RS_W)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RS_H)
                self.camera_info = dict(source='webcam', depth_scale_m=None)

            mp_hands, draw, styles = (mp.solutions.hands, mp.solutions.drawing_utils,
                                      mp.solutions.drawing_styles)
            hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.65,
                                   min_tracking_confidence=0.55)
            prev_t = last_received = time.perf_counter()
            while self.running:
                # Only this thread mutates camera/filter/recorder state.
                self._apply_commands()
                capture = dict(session_id=self.session_id)
                arrays, intr = {}, None
                if pipe is not None:
                    try:
                        original = pipe.wait_for_frames(timeout_ms=1000)
                    except RuntimeError:
                        if time.perf_counter() - last_received > 3:
                            raise RuntimeError('RealSense 프레임 수신이 3초 이상 중단되었습니다.')
                        continue
                    capture_time, unix_time = time.perf_counter(), time.time()
                    cf0, df0 = original.get_color_frame(), original.get_depth_frame()
                    if not cf0:
                        if time.perf_counter() - last_received > 3:
                            raise RuntimeError('RealSense 컬러 프레임이 없습니다.')
                        continue
                    frame = np.asanyarray(cf0.get_data()).copy()
                    capture.update(color_frame_number=cf0.get_frame_number(),
                                   color_timestamp_ms=cf0.get_timestamp(),
                                   color_timestamp_domain=str(cf0.get_frame_timestamp_domain()))
                    frames = align.process(original)
                    df = frames.get_depth_frame()
                    self.latest_depth = None
                    if df0:
                        capture.update(depth_frame_number=df0.get_frame_number(),
                                       depth_timestamp_ms=df0.get_timestamp(),
                                       depth_timestamp_domain=str(df0.get_frame_timestamp_domain()))
                        arrays['depth_native_z16'] = np.asanyarray(df0.get_data()).copy()
                    if df:
                        aligned = np.asanyarray(df.get_data()).copy()
                        arrays['depth_aligned_z16'] = aligned
                        self.latest_depth = aligned.astype(np.float32) * self.depth_scale
                        intr = df.profile.as_video_stream_profile().get_intrinsics()
                        capture['aligned_depth_intrinsics'] = self._intrinsics_dict(intr)
                    capture['depth_scale_m'] = self.depth_scale
                    # Measurement always uses unfiltered, unmirrored aligned depth.
                    # Display choices must never change measurement inputs.
                else:
                    ok, frame = cap.read()
                    if not ok:
                        if time.perf_counter() - last_received > 3:
                            raise RuntimeError('웹캠 프레임 수신이 3초 이상 중단되었습니다.')
                        time.sleep(0.01)
                        continue
                    capture_time, unix_time = time.perf_counter(), time.time()
                    self.latest_depth = None
                last_received = capture_time
                self.frame_id += 1
                capture.update(frame_id=self.frame_id, capture_monotonic_s=capture_time,
                               capture_unix_s=unix_time, source=self.source_name,
                               camera_info=self.camera_info)
                arrays['color_bgr'] = frame.copy()  # no overlays, no mirroring, lossless
                fps = 1.0 / max(capture_time - prev_t, 1e-6)
                prev_t, t = capture_time, capture_time - self.t0

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                res = hands.process(rgb)
                has_depth = self.latest_depth is not None
                mode = self.view_mode if has_depth else VIEW_COLOR
                dvis = self._colorize_depth(self.latest_depth) if has_depth and mode != VIEW_COLOR else None
                # Always annotate the colour frame for recording, even when
                # the user is currently viewing only the depth image.
                canvases = [frame] + \
                           ([dvis] if mode in (VIEW_DEPTH, VIEW_BOTH) else [])
                angles_out, depths_out, hands3d, measurements = {}, {}, {}, {}
                overlays = []
                n_hands = len(res.multi_hand_landmarks or [])
                if res.multi_hand_landmarks:
                    wl = res.multi_hand_world_landmarks
                    h_img, w_img = frame.shape[:2]
                    # Duplicate handedness is ambiguous. Never silently overwrite one hand.
                    labels = []
                    for i in range(n_hands):
                        label = (res.multi_handedness[i].classification[0].label
                                 if res.multi_handedness and i < len(res.multi_handedness) else None)
                        labels.append({'Left': 'Right', 'Right': 'Left'}.get(label))
                    capture['hand_labels'] = labels
                    capture['ambiguous_handedness'] = len(set(labels)) != len(labels) or None in labels
                    for i, lms in enumerate(res.multi_hand_landmarks):
                        hand = labels[i]
                        if hand is None or labels.count(hand) != 1:
                            continue
                        for canvas in canvases:
                            draw.draw_landmarks(canvas, lms, mp_hands.HAND_CONNECTIONS,
                                                styles.get_default_hand_landmarks_style(),
                                                styles.get_default_hand_connections_style())
                        pixels = np.array([[lm.x * w_img, lm.y * h_img] for lm in lms.landmark])
                        wx, wy = pixels[0]
                        dist = self.depth_at(wx, wy)
                        depths_out[hand] = dist
                        world = wl[i].landmark if wl and i < len(wl) else None
                        W = (np.array([[lm.x, lm.y, lm.z] for lm in world], dtype=float)
                             if world is not None else None)
                        deproject = (lambda pixel, z: self._deproject(intr, pixel, z)) if intr else None
                        measurement = measure_hand(W, pixels, self.latest_depth, deproject, self.palm_calib_mm)
                        measurement['handedness_score'] = res.multi_handedness[i].classification[0].score
                        measurements[hand] = measurement
                        # No normalized-image fallback: its coordinates are not metres.
                        if W is None or not np.isfinite(W).all():
                            continue
                        rec = self.build_3d(hand, world, t, dist)
                        if rec:
                            hands3d[hand] = rec
                        mp_ap, rs_ap = measurement['mp_aperture_mm'], measurement['rs_aperture_mm']
                        rs_text = f"{rs_ap:.1f}mm" if rs_ap is not None else '--'
                        overlays.append((f"{hand} MP {mp_ap:.1f}mm | RS {rs_text}", wx, wy))
                        raw = joint_angles(W)
                        raw['Grip_Aperture'] = mp_ap / 10.0
                        pab, rab = thumb_abduction(palm_frame(W)[0])
                        raw['Thumb_PalmarAbd'], raw['Thumb_RadialAbd'] = pab, rab
                        hold, filt = self._moved(hand, wx, wy), {}
                        for k, v in raw.items():
                            key = f"{hand}_{k}"
                            if k == 'Grip_Aperture' or k in ABD_KEYS:
                                if v is None:
                                    filt[k] = None
                                    continue
                                if key not in self.ap_filters:
                                    self.ap_filters[key] = ApertureFilter(
                                        v, vmax=APERTURE_MAX_CM if k == 'Grip_Aperture' else 180.0)
                                filt[k] = self.ap_filters[key].update(t, v) if self.use_filter else v
                            else:
                                if key not in self.filters:
                                    self.filters[key] = AngleFilter(v)
                                filt[k] = self.filters[key].update(t, v, hold) if self.use_filter else v
                        angles_out[hand] = {'raw': raw, 'filtered': filt}
                if self.recorder:
                    recorded_overlay = frame.copy()
                    for text, wx, wy in overlays:
                        self._put(recorded_overlay, text, max(0, int(wx)-80),
                                  max(24, int(wy)-16), (0, 255, 0), 0.6)
                    self._put(recorded_overlay, f"Frame {self.frame_id} | Hands {n_hands}",
                              14, 24, (255, 255, 255), 0.6)
                    arrays['overlay_bgr'] = recorded_overlay
                    self.recorder.submit(capture, arrays)
                capture['measurements'] = measurements
                if self.mirror_mode:
                    frame = cv2.flip(frame, 1)
                    if dvis is not None:
                        dvis = cv2.flip(dvis, 1)
                display_canvases = ([frame] if mode in (VIEW_COLOR, VIEW_BOTH) else []) + \
                                   ([dvis] if mode in (VIEW_DEPTH, VIEW_BOTH) else [])
                for text, wx, wy in overlays:
                    x = frame.shape[1] - 1 - wx if self.mirror_mode else wx
                    for canvas in display_canvases:
                        self._put(canvas, text, max(0, int(x)-80), max(24, int(wy)-16), (0, 255, 0), 0.6)
                output = self._compose(mode, frame, dvis)
                self.frame_processed.emit(output, angles_out, fps, n_hands, depths_out, hands3d, capture)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.running = False
            # Drain start/stop requests even if camera initialization failed.
            try:
                self._apply_commands()
            except Exception as exc:
                self.failed.emit(str(exc))
            self._end_recording()
            if pipe is not None:
                try:
                    pipe.stop()
                except Exception:
                    pass
            if cap is not None:
                cap.release()
            if hands is not None:
                hands.close()

    @staticmethod
    def _put(img, text, x, y, color, scale=0.7):
        for col, th in ((0, 0, 0), 4), (color, 2):
            cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, col, th, cv2.LINE_AA)

    def _compose(self, mode, color, dvis):
        if mode == VIEW_DEPTH and dvis is not None:
            self._put(dvis, "DEPTH", 14, 34, (255, 255, 255), 1.0)
            return dvis
        if mode == VIEW_BOTH and dvis is not None:
            l, r = color.copy(), dvis.copy()
            self._put(l, "COLOR", 14, 34, (255, 255, 255), 1.0)
            self._put(r, "DEPTH", 14, 34, (255, 255, 255), 1.0)
            both = cv2.hconcat([l, r])
            return cv2.resize(both, (both.shape[1] // 2, both.shape[0] // 2),
                              interpolation=cv2.INTER_AREA)
        return color

    def stop(self):
        self.running = False
        self.wait()  # Do not destroy a running QThread or an unfinished raw writer.


# ============================ 실시간 차트 ============================
class LiveAngleChart(FigureCanvas):
    """오른손/왼손 5손가락 대표 굴곡각(PIP·엄지 IP) 2단 시계열."""

    def __init__(self, parent=None, w=6, h=4.2, dpi=100):
        self.fig = Figure(figsize=(w, h), dpi=dpi, layout='constrained')
        self.fig.patch.set_facecolor('#131622')
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes, self.lines, self.tbuf, self.abuf, self.spans = {}, {}, {}, {}, {}

        top = self.fig.add_subplot(211)
        bot = self.fig.add_subplot(212, sharex=top)
        for hand, ax in zip(HANDS, (top, bot)):
            ax.set_facecolor('#191c2b')
            ax.set_ylim(0, 180)
            ax.set_yticks([0, 45, 90, 135, 180])
            ax.set_xlim(0, 10)
            label = '오른손' if hand == 'Right' else '왼손'
            ax.set_ylabel(f"{label}\n각도(°)", color="#cbd5e1", fontsize=8, fontweight='bold')
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for s in ax.spines.values():
                s.set_edgecolor('#334155')
            ax.grid(True, ls='--', color='#272b3f', lw=0.8)
            self.lines[hand] = {f: ax.plot([], [], label=f, color=c, lw=2)[0]
                                for f, c in FINGER_COLORS.items()}
            ax.legend(loc='upper right', fontsize=7, ncol=5, facecolor='#191c2b',
                      edgecolor='#334155', labelcolor='#f1f5f9')
            self.axes[hand] = ax
            self.tbuf[hand] = deque(maxlen=300)
            self.abuf[hand] = {f: deque(maxlen=300) for f in FINGER_COLORS}
            self.spans[hand] = []
        top.tick_params(labelbottom=False)
        bot.set_xlabel("경과 시간 (초)", color="#cbd5e1", fontsize=9, fontweight='bold')
        self.fig.get_layout_engine().set(hspace=.10, w_pad=.05, h_pad=.05)
        self._last = None

    def update_data(self, t, ad):
        hit = False
        for hand in HANDS:
            if hand not in ad:
                continue
            d = ad[hand].get('filtered', ad[hand])
            self.tbuf[hand].append(t)
            for f in FINGER_COLORS:
                self.abuf[hand][f].append(d.get(f"{f}_Flexion", 180.0))
            hit = True
        if not hit or (self._last is not None and t - self._last < 0.1):
            return
        self._last = t
        tn = max(self.tbuf[h][-1] for h in HANDS if self.tbuf[h])
        for hand in HANDS:
            if len(self.tbuf[hand]) > 1:
                ta = np.array(self.tbuf[hand])
                for f in FINGER_COLORS:
                    self.lines[hand][f].set_data(ta, np.array(self.abuf[hand][f]))
            self.axes[hand].set_xlim(max(0.0, tn - 10), max(10.0, tn))
        self.draw_idle()

    def add_trial_span(self, t0, t1):
        for hand in HANDS:
            self.spans[hand].append(self.axes[hand].axvspan(t0, t1, color='#0284c7', alpha=0.25))
        self.draw_idle()

    def reset_chart(self):
        for hand in HANDS:
            self.tbuf[hand].clear()
            for f in self.abuf[hand]:
                self.abuf[hand][f].clear()
            for s in self.spans[hand]:
                try:
                    s.remove()
                except Exception:
                    pass
            self.spans[hand].clear()
            self.axes[hand].set_xlim(0, 10)
            for f in self.lines[hand]:
                self.lines[hand][f].set_data([], [])
        self._last = None
        self.draw_idle()


class Hand3DView(FigureCanvas):
    """정준화 3D 골격. 반경은 고정(손 크기 정규화)하고 중심만 손을 따라간다."""

    BONES = {'Thumb': [0, 1, 2, 3, 4], 'Index': [0, 5, 6, 7, 8], 'Middle': [0, 9, 10, 11, 12],
             'Ring': [0, 13, 14, 15, 16], 'Pinky': [0, 17, 18, 19, 20]}
    PALM_EDGES = [(0, 1), (1, 5), (5, 9), (9, 13), (13, 17), (17, 0)]

    def __init__(self, parent=None, w=6, h=4.2, dpi=100):
        self.fig = Figure(figsize=(w, h), dpi=dpi)
        self.fig.patch.set_facecolor('#131622')
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes, self.bones, self.palm, self.mesh, self.pts, self.titles, self.c = \
            {}, {}, {}, {}, {}, {}, {}

        for i, hand in enumerate(HANDS):
            ax = self.fig.add_subplot(1, 2, i + 1, projection='3d')
            ax.set_facecolor('#141724')
            ax.set_box_aspect([1, 1, 1])
            ax.view_init(elev=10, azim=-90)
            for s in ('x', 'y', 'z'):
                getattr(ax, f"set_{s}ticklabels")([])
            ax.tick_params(colors='none', length=0)
            try:
                for pa in (ax.xaxis, ax.yaxis, ax.zaxis):
                    pa.pane.set_facecolor('#0f121d')
                    pa.pane.set_edgecolor('#1e2438')
            except Exception:
                pass
            ax.grid(True, ls=':', color='#242b40', alpha=0.5)

            self.mesh[hand] = Poly3DCollection([], alpha=0.35, facecolor='#0284c7',
                                               edgecolor='#38bdf8', linewidths=1.2)
            ax.add_collection3d(self.mesh[hand])
            self.bones[hand] = {f: (ax.plot([], [], [], color=FINGER_COLORS[f], lw=4.5,
                                            solid_capstyle='round')[0], idx)
                                for f, idx in self.BONES.items()}
            self.palm[hand] = [ax.plot([], [], [], color='#64748b', lw=2.6, alpha=0.75)[0]
                               for _ in self.PALM_EDGES]
            # scatter의 _offsets3d는 비공개 API라 marker Line3D + set_data_3d를 쓴다
            self.pts[hand], = ax.plot([], [], [], ls='none', marker='o', ms=5,
                                      color='#fff', mec='#38bdf8', mew=0.8)
            self.titles[hand] = ax.set_title(f"{HAND_KR[hand]}  ·  대기", color="#64748b",
                                             fontsize=9, fontweight='bold', pad=2)
            self.axes[hand] = ax
            self.c[hand] = np.array([0.0, 0.0, 0.75])
            self._lim(ax, self.c[hand])
        self._last = None
        self.fig.subplots_adjust(left=.02, right=.98, top=.78, bottom=.04, wspace=.12)

    @staticmethod
    def _lim(ax, c, r=VIEW3D_R):
        ax.set_xlim(c[0] - r, c[0] + r)
        ax.set_ylim(c[1] - r, c[1] + r)
        ax.set_zlim(c[2] - r, c[2] + r)

    def _clear(self, hand):
        self.mesh[hand].set_verts([])
        for ln, _ in self.bones[hand].values():
            ln.set_data_3d([], [], [])
        for ln in self.palm[hand]:
            ln.set_data_3d([], [], [])
        self.pts[hand].set_data_3d([], [], [])

    def update_hands(self, t, hands3d):
        if self._last is not None and t - self._last < VIEW3D_INTERVAL:
            return
        self._last = t
        for hand in HANDS:
            rec = hands3d.get(hand)
            if rec is None:
                self._clear(hand)
                self.titles[hand].set_text(f"{HAND_KR[hand]}  ·  3D 없음")
                self.titles[hand].set_color("#64748b")
                continue

            P = rec['points']
            x, y, z = P[:, 0], P[:, 2], -P[:, 1]     # 화면축 (X, Z, -Y)
            self.mesh[hand].set_verts([np.column_stack([x[PALM_IDS], y[PALM_IDS], z[PALM_IDS]])])
            for ln, idx in self.bones[hand].values():
                ln.set_data_3d(x[idx], y[idx], z[idx])
            for ln, (a, b) in zip(self.palm[hand], self.PALM_EDGES):
                ln.set_data_3d([x[a], x[b]], [y[a], y[b]], [z[a], z[b]])
            self.pts[hand].set_data_3d(x, y, z)

            cloud = np.stack([x, y, z], 1).mean(axis=0)
            self.c[hand] = (1 - VIEW3D_ALPHA) * self.c[hand] + VIEW3D_ALPHA * cloud
            self._lim(self.axes[hand], self.c[hand])

            m = rec['metrics']
            ap = m['aperture_mm_cal'] if m['aperture_mm_cal'] is not None else m['aperture_mm']
            txt = f"{HAND_KR[hand]}  ·  MP 파지폭 {ap:.0f}mm"
            if m['aperture_mm_cal'] is not None:
                txt += "*"
            detail = []
            if m.get('thumb_palmar_abd') is not None:
                detail.append(f"외전 {m['thumb_palmar_abd']:.0f}°")
            if m['wrist_dist_m']:
                detail.append(f"손목 거리 {m['wrist_dist_m']:.2f}m")
            if detail:
                txt += '\n' + '  ·  '.join(detail)
            self.titles[hand].set_text(txt)
            self.titles[hand].set_color('#10b981')
        self.draw_idle()

    def reset_view(self):
        for hand in HANDS:
            self._clear(hand)
            self.c[hand] = np.array([0.0, 0.0, 0.75])
            self._lim(self.axes[hand], self.c[hand])
            self.titles[hand].set_text(f"{HAND_KR[hand]}  ·  대기")
            self.titles[hand].set_color("#64748b")
        self._last = None
        self.draw_idle()


QSS = """
* { font-family:'Malgun Gothic','Segoe UI',sans-serif; font-size:13px; }
QMainWindow { background:#0b0d14; } QWidget { color:#f8fafc; }
QGroupBox { background:#141724; border:1px solid #282f48; border-radius:8px; margin-top:14px;
            font-weight:bold; color:#38bdf8; padding:14px 10px 10px 10px; }
QGroupBox::title { subcontrol-origin:margin; subcontrol-position:top left; padding:0 8px; left:12px; }
QLabel { color:#e2e8f0; }
QScrollArea { background:#0b0d14; border:none; }
QWidget#settingsContent, QWidget#rightContent { background:#0b0d14; }
QFrame#videoCard { background:#141724; border:1px solid #282f48; border-radius:8px; }
QFrame#handGauge { background:#12141f; border:1px solid #282f48; border-radius:6px; }
QTabWidget::pane { background:#131622; border:1px solid #282f48; border-radius:6px; }
QTabBar::tab { background:#191c2b; color:#94a3b8; padding:8px 16px; margin-right:3px; }
QTabBar::tab:selected { background:#25334c; color:#38bdf8; }
QLineEdit,QSpinBox,QComboBox { background:#1c2032; border:1px solid #3b4566; border-radius:6px;
            padding:6px 10px; color:#fff; font-weight:600; min-height:22px; }
QLineEdit:focus,QSpinBox:focus,QComboBox:hover { border:1px solid #38bdf8; }
QComboBox QAbstractItemView { background:#141724; color:#fff; border:1px solid #38bdf8;
            selection-background-color:#2563eb; outline:none; }
QTableWidget { background:#12141f; border:1px solid #282f48; border-radius:6px;
            gridline-color:#242a42; color:#f1f5f9; font-size:12px; }
QHeaderView::section { background:#1c2032; color:#38bdf8; font-weight:bold; border:none;
            border-bottom:1px solid #3b4566; padding:4px; font-size:11px; }
QPushButton { background:#2563eb; color:#fff; font-weight:bold; border:none;
            border-radius:6px; padding:8px 14px; }
QPushButton:hover { background:#1d4ed8; }
QPushButton:disabled { background:#2d3348; color:#64748b; }
#start { background:#059669; font-size:14px; min-height:38px; }
#stop  { background:#dc2626; font-size:14px; min-height:38px; }
#start:disabled, #stop:disabled { background:#2d3348; color:#64748b; }
#trial { background:#0284c7; font-size:15px; min-height:48px; border:2px solid #38bdf8; }
#trial:disabled { background:#2d3348; border:1px solid #3b4566; color:#64748b; }
QProgressBar { background:#191c2b; border:1px solid #334155; border-radius:4px;
            text-align:center; color:#fff; font-size:10px; height:14px; }
QProgressBar::chunk { background:#0ea5e9; border-radius:3px; }
QCheckBox { color:#e2e8f0; font-weight:bold; spacing:8px; }
QCheckBox::indicator { width:18px; height:18px; border-radius:4px;
            border:1px solid #475569; background:#1c2032; }
QCheckBox::indicator:checked { background:#38bdf8; border:1px solid #38bdf8; }
"""


# ================================ 메인 ================================
class ScrollContent(QWidget):
    def heightForWidth(self, width):
        # Wrapped QLabel hints otherwise make QScrollArea reserve the canvases'
        # preferred height, even when every child fits at its smaller minimum.
        return self.minimumSizeHint().height()


class ClinicalApp(QMainWindow):
    TABLE_COLS = ["회차", "손", "과제", "소요시간", "사이클", "주기(s)",
                  "TAM(°)", "CMC(°)", "외전(°)", "MGA(cm)", "굴곡속도", "SPARC"]
    TASKS = ["Task 1: 맨손 쥐기/펴기 (Free Motion)", "Task 2: 구형 파지 (Sphere)",
             "Task 3: 원통형 파지 (Cylinder)", "Task 4: 정육면체 파지 (Cube)"]
    # 양손이 모두 인식돼야 기록하는 과제 (양손 동시 파지 프로토콜)
    BOTH_HANDS_TASKS = ("Task 4",)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 미러테라피 · 손 기능 평가 (정준화 3D)")
        # Qt reports logical pixels here, already accounting for Windows scaling.
        available = self.screen().availableGeometry()
        self.setMinimumSize(min(920, available.width()), min(560, available.height()))
        self.resize(min(1660, available.width() - 32), min(1040, available.height() - 64))
        self.setStyleSheet(QSS)

        self.session_on = self.trial_on = self.paused = False
        self.t_session = self.t_trial = 0.0
        self.auto_left, self._last_tick = 0.0, time.perf_counter()
        self.records, self.trials, self.trial_idx = [], [], 1
        self.frame_log, self.task_history = [], []
        self.session_id, self.capture_summary = None, {}
        self.finishing = self.unsaved = self.close_pending = False
        self._last_capture = None
        self._trial_previous = None
        self.trial_task, self.trial_hands = '', ()
        self._session_error = None
        self._stop_time = None
        self.folder = ""
        self.t_app = time.perf_counter()
        self.gauges, self.glabels, self.gtitles = {}, {}, {}

        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     "outputs", "데이터_저장"))
        os.makedirs(self.base_dir, exist_ok=True)

        self._build_ui()
        for key, fn in (("Q", self.close), ("Esc", self._escape_fullscreen),
                        ("F11", self._toggle_fullscreen),
                        ("M", lambda: self.chk_mirror.toggle()),
                        ("D", self._cycle_view),
                        ("Space", self._space)):
            QShortcut(QKeySequence(key), self).activated.connect(
                lambda f=fn, k=key: None if k not in ('Esc', 'F11') and
                isinstance(self.focusWidget(), QLineEdit) else f())

        self.worker = VideoWorker(0)
        self.worker.frame_processed.connect(self.on_frame)
        self.worker.recording_finished.connect(self._recording_finished)
        self.worker.failed.connect(self._worker_failed)
        self.worker.finished.connect(self._worker_stopped)
        self.worker.set_palm_calib(self.spin_palm.value())
        self.worker.set_hold_motion(self.chk_hold.isChecked())
        self.worker.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(100)

    # ------------------------------ UI ------------------------------
    def _toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _escape_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()

    def _build_ui(self):
        cw = QWidget(self)
        self.setCentralWidget(cw)
        main = QHBoxLayout(cw)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)
        main.addWidget(self._left_panel())
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setWidget(self._right_panel())
        main.addWidget(self.content_scroll, stretch=1)

    def _left_panel(self):
        panel = QWidget()
        panel.setFixedWidth(360)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        settings = QWidget()
        settings.setObjectName('settingsContent')
        lay = QVBoxLayout(settings)
        lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.settings_scroll.setWidget(settings)
        outer.addWidget(self.settings_scroll, stretch=1)

        g1 = QGroupBox("1. 피험자 구분")
        r1 = QHBoxLayout(g1)
        self.rb_patient, self.rb_healthy = QRadioButton("편마비 환자군"), QRadioButton("비장애인 대조군")
        self.rb_patient.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.rb_patient)
        grp.addButton(self.rb_healthy)
        self.rb_healthy.toggled.connect(self._on_group)
        r1.addWidget(self.rb_patient)
        r1.addWidget(self.rb_healthy)
        lay.addWidget(g1)

        g2 = QGroupBox("2. 기본 인적 사항")
        f2 = QGridLayout(g2)
        f2.setSpacing(6)
        self.txt_name = QLineEdit("이재용")
        self.spin_age = QSpinBox()
        self.spin_age.setRange(5, 110)
        self.spin_age.setValue(62)
        self.spin_age.setSuffix(" 세")
        self.cb_gender = QComboBox()
        self.cb_gender.addItems(["남성 (Male)", "여성 (Female)"])
        self.spin_palm = QSpinBox()
        self.spin_palm.setRange(0, 250)
        self.spin_palm.setSuffix(" mm (0=미사용)")
        self.spin_palm.setToolTip("손목 주름 중앙 ~ 중지 MCP 실측 길이.\n"
                                  "입력하면 3D 파지폭(mm)이 피험자 손 크기로 보정됩니다.")
        self.spin_palm.valueChanged.connect(self._on_palm)
        for r, (label, w) in enumerate([("이름:", self.txt_name), ("나이:", self.spin_age),
                                        ("성별:", self.cb_gender), ("실측 손 길이:", self.spin_palm)]):
            f2.addWidget(QLabel(label), r, 0)
            f2.addWidget(w, r, 1)
        lay.addWidget(g2)

        self.g_clin = QGroupBox("3. 임상 재활 척도")
        f3 = QGridLayout(self.g_clin)
        f3.setSpacing(6)
        self.spin_fma = QSpinBox()
        self.spin_fma.setRange(0, 14)
        self.spin_fma.setValue(8)
        self.spin_fma.setSuffix(" / 14점")
        self.cb_brs = QComboBox()
        self.cb_brs.addItems([f"Stage {i}" + s for i, s in enumerate(
            [" (완전이완)", " (경직시작)", " (공동운동극대)", " (부분분리운동)",
             " (독립분리운동)", " (정상협응)"], 1)])
        self.cb_brs.setCurrentIndex(3)
        self.cb_affected = QComboBox()
        self.cb_affected.addItems(["우측 (Right Hand)", "좌측 (Left Hand)"])
        for r, (label, w) in enumerate([("FMA-UE 점수:", self.spin_fma),
                                        ("Brunnstrom 단계:", self.cb_brs),
                                        ("환측 (마비손):", self.cb_affected)]):
            f3.addWidget(QLabel(label), r, 0)
            f3.addWidget(w, r, 1)
        lay.addWidget(self.g_clin)

        g4 = QGroupBox("4. 실험 프로토콜 과제")
        f4 = QHBoxLayout(g4)
        self.cb_task = QComboBox()
        self.cb_task.addItems(self.TASKS)
        self.cb_task.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_task.setMinimumContentsLength(16)
        self.cb_task.currentTextChanged.connect(self._on_task)
        f4.addWidget(self.cb_task)
        lay.addWidget(g4)
        lay.addStretch()

        g5 = QGroupBox("5. 구간 측정 제어")
        f5 = QVBoxLayout(g5)
        f5.setSpacing(8)

        auto_row = QHBoxLayout()
        self.spin_auto = QSpinBox()
        self.spin_auto.setRange(1, 60)
        self.spin_auto.setValue(int(AUTO_TRIAL_SEC))
        self.spin_auto.setSuffix(" 초")
        self.spin_auto.setEnabled(False)          # 환자군이 기본값
        self.spin_auto.setToolTip("비장애인 대조군에서 버튼을 한 번 누를 때 자동으로 측정되는 길이.\n"
                                  "환자군은 시작/종료를 직접 눌러 구간을 잡습니다.")
        self.spin_auto.valueChanged.connect(lambda v: self._trial_btn(not self.trial_on))
        auto_row.addWidget(QLabel("자동 측정 (대조군):"))
        auto_row.addWidget(self.spin_auto)
        f5.addLayout(auto_row)

        row = QHBoxLayout()
        self.btn_start = QPushButton("▶  세션 시작")
        self.btn_start.setObjectName("start")
        self.btn_start.clicked.connect(self.start_session)
        self.btn_stop = QPushButton("■  종료 및 저장")
        self.btn_stop.setObjectName("stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_session)
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_stop)
        f5.addLayout(row)

        self.btn_trial = QPushButton()
        self.btn_trial.setObjectName("trial")
        self.btn_trial.setEnabled(False)
        self.btn_trial.clicked.connect(self.toggle_trial)
        self._trial_btn(True)
        f5.addWidget(self.btn_trial)

        # Controls remain visible while subject/protocol settings scroll above.
        g5.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        outer.addWidget(g5)
        return panel

    def _right_panel(self):
        panel = ScrollContent()
        panel.setObjectName('rightContent')
        panel.setMinimumWidth(640)
        lay = QVBoxLayout(panel)
        lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        card = QFrame()
        card.setObjectName('videoCard')
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(8)

        status = QHBoxLayout()
        self.lbl_session = QLabel('● READY (대기 중)')
        self.lbl_session.setStyleSheet('color:#10b981; font-weight:bold; font-size:14px;')
        self.lbl_session.setWordWrap(True)
        self.lbl_session.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_fps = QLabel('FPS: -- | Hands: 0')
        self.lbl_fps.setStyleSheet('color:#94a3b8; font-size:12px;')
        self.lbl_fps.setWordWrap(True)
        self.lbl_fps.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_fps.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status.addWidget(self.lbl_session, stretch=1)
        status.addWidget(self.lbl_fps, stretch=1)
        cl.addLayout(status)
        self.lbl_trial = QLabel('대기 상태')
        self.lbl_trial.setWordWrap(True)
        self.lbl_trial.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_trial.setMinimumHeight(32)
        self.lbl_trial.setStyleSheet('color:#94a3b8; font-weight:bold;')

        actions = QHBoxLayout()
        self.cb_view = QComboBox()
        self.cb_view.addItems(['컬러 영상', 'Depth 영상', '컬러 + Depth'])
        self.cb_view.setMinimumContentsLength(10)
        self.cb_view.currentIndexChanged.connect(self._on_view)
        btn_folder = QPushButton('저장 폴더')
        btn_folder.clicked.connect(self._open_folder)
        btn_exit = QPushButton('종료 (Q)')
        btn_exit.clicked.connect(self.close)
        actions.addWidget(QLabel('보기:'))
        actions.addWidget(self.cb_view)
        actions.addWidget(self.lbl_trial, stretch=1)
        actions.addWidget(btn_folder)
        actions.addWidget(btn_exit)
        cl.addLayout(actions)

        self.chk_mirror = QCheckBox('미러링 (M)')
        self.chk_mirror.toggled.connect(self._on_mirror)
        self.chk_filter = QCheckBox('생체역학 필터')
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda v: self.worker.set_filter_mode(v))
        self.chk_3d = QCheckBox('3D 재구성')
        self.chk_3d.setChecked(True)
        self.chk_3d.toggled.connect(self._on_3d)
        self.chk_smooth = QCheckBox('3D 좌표 스무딩')
        self.chk_smooth.setChecked(LM_SMOOTH_DEFAULT)
        self.chk_smooth.setToolTip('랜드마크 (x,y,z)에 One-Euro 필터를 적용합니다.')
        self.chk_smooth.toggled.connect(self._on_smooth)
        self.chk_hold = QCheckBox('팔 이동 보정')
        self.chk_hold.setChecked(HOLD_MOTION_DEFAULT)
        self.chk_hold.setToolTip('손목이 크게 움직인 프레임의 각도 갱신을 보류합니다.')
        self.chk_hold.toggled.connect(lambda v: self.worker.set_hold_motion(v))
        options = QGridLayout()
        options.setHorizontalSpacing(18)
        options.setVerticalSpacing(6)
        for i, widget in enumerate((self.chk_mirror, self.chk_filter, self.chk_3d,
                                    self.chk_smooth, self.chk_hold)):
            options.addWidget(widget, i // 3, i % 3)
            options.setColumnStretch(i % 3, 1)
        cl.addLayout(options)

        self.lbl_video = QLabel('카메라 연결 중...')
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Pixmap size must not become the label's minimum size after a large frame.
        self.lbl_video.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.lbl_video.setMinimumHeight(190)
        self.lbl_video.setStyleSheet('background:#08090e; border-radius:6px;')
        cl.addWidget(self.lbl_video, stretch=1)
        grow = QHBoxLayout()
        grow.setSpacing(8)
        for hand in HANDS:
            grow.addWidget(self._gauge_panel(hand), stretch=1)
        cl.addLayout(grow)
        lay.addWidget(card, stretch=3)

        # Full-width pages keep plots and all 12 result columns readable.
        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setMinimumHeight(290)
        self.chart = LiveAngleChart(self)
        self.view3d = Hand3DView(self)
        for widget in (self.chart, self.view3d):
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            widget.setMinimumSize(0, 250)
        self.analysis_tabs.addTab(self.chart, '굴곡각 그래프')
        self.analysis_tabs.addTab(self.view3d, '3D 손 보기')
        self.table = QTableWidget(0, len(self.TABLE_COLS))
        self.table.setHorizontalHeaderLabels(self.TABLE_COLS)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(65)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.analysis_tabs.addTab(self.table, '회차 결과')
        lay.addWidget(self.analysis_tabs, stretch=2)

        self.lbl_toast = QLabel('세션 시작 시 원본·손 추적 영상을 함께 저장합니다. Space: 구간 측정 · F11: 전체화면 전환 · Esc: 창 모드')
        self.lbl_toast.setWordWrap(True)
        self.lbl_toast.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_toast.setMinimumHeight(36)
        self.lbl_toast.setStyleSheet('color:#94a3b8; font-size:12px; padding:2px 6px;')
        lay.addWidget(self.lbl_toast)
        return panel

    # ------------------ 게이지 (근위/중간/원위 · 엄지는 CMC/MCP/IP) ------------------
    def _gauge_panel(self, hand):
        panel = QFrame()
        panel.setObjectName("handGauge")
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(4)
        title = QLabel(f"{HAND_KR[hand]}  ·  미인식")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title.setMinimumHeight(32)
        title.setStyleSheet("font-size:11px; font-weight:bold; color:#64748b; border:none;")
        v.addWidget(title)
        self.gtitles[hand] = title

        row = QHBoxLayout()
        row.setSpacing(6)
        self.gauges[hand], self.glabels[hand] = {}, {}
        for f in FINGERS:
            col = QVBoxLayout()
            col.setSpacing(2)
            head = QLabel(f)
            head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            head.setStyleSheet("font-size:11px; font-weight:bold; color:#e2e8f0; border:none;")
            col.addWidget(head)

            grid = QGridLayout()
            grid.setSpacing(2)
            grid.setContentsMargins(0, 0, 0, 0)
            self.gauges[hand][f], self.glabels[hand][f] = {}, {}
            for r, (seg, jname) in enumerate(zip(SEG_LABELS, JOINT_TRIPLE[f])):
                disp = jname.split('_', 1)[1] if jname else '—'
                col_hex = SEG_COLORS[seg] if jname else '#475569'
                lbl = QLabel(f"{disp} --°")
                lbl.setMinimumWidth(50)
                lbl.setStyleSheet(f"font-size:10px; font-weight:bold; color:{col_hex}; border:none;")
                bar = QProgressBar()
                bar.setRange(0, 180)
                bar.setValue(0)
                bar.setTextVisible(False)
                bar.setFixedHeight(9)
                bar.setMinimumWidth(16)
                bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                bar.setStyleSheet(
                    "QProgressBar{background:#191c2b;border:1px solid #334155;border-radius:3px;}"
                    f"QProgressBar::chunk{{background:{col_hex};border-radius:2px;}}")
                bar.setEnabled(jname is not None)
                grid.addWidget(lbl, r * 2, 0)
                grid.addWidget(bar, r * 2 + 1, 0)
                self.gauges[hand][f][seg], self.glabels[hand][f][seg] = bar, lbl
            grid.setColumnStretch(0, 1)
            col.addLayout(grid)
            row.addLayout(col, stretch=1)
        v.addLayout(row)
        return panel

    def _update_gauge(self, hand, data, dist):
        title = self.gtitles[hand]
        if not data:
            title.setText(f"{HAND_KR[hand]}  ·  미인식")
            title.setStyleSheet("font-size:11px; font-weight:bold; color:#64748b; border:none;")
            for f in FINGERS:
                for seg, jname in zip(SEG_LABELS, JOINT_TRIPLE[f]):
                    disp = jname.split('_', 1)[1] if jname else '—'
                    self.gauges[hand][f][seg].setValue(0)
                    self.glabels[hand][f][seg].setText(f"{disp} --°")
            return
        filt = data.get('filtered', data)
        abd = filt.get('Thumb_PalmarAbd')
        head = f"{HAND_KR[hand]}  ·  인식됨  ·  " + (f"{dist:.2f} m" if dist else "depth --")
        if abd is not None and np.isfinite(abd):
            head += f"  ·  엄지 외전 {abd:.0f}°"
        title.setText(head)
        title.setStyleSheet("font-size:11px; font-weight:bold; color:#10b981; border:none;")
        for f in FINGERS:
            for seg, jname in zip(SEG_LABELS, JOINT_TRIPLE[f]):
                bar, lbl = self.gauges[hand][f][seg], self.glabels[hand][f][seg]
                if jname is None:
                    lbl.setText("—  n/a")
                    bar.setValue(0)
                    continue
                val = filt.get(jname)
                disp = jname.split('_', 1)[1]
                if val is None or not np.isfinite(val):
                    lbl.setText(f"{disp} --°")
                    bar.setValue(0)
                else:
                    lbl.setText(f"{disp} {val:.0f}°")
                    bar.setValue(int(val))

    # ---------------------------- 핸들러 ----------------------------
    def toast(self, msg, ok=False):
        self.lbl_toast.setText(f"[{datetime.now():%H:%M:%S}] {msg}")
        self.lbl_toast.setStyleSheet(
            f"color:{'#10b981' if ok else '#38bdf8'}; font-size:12px; font-weight:bold; padding:2px 6px;")

    def _on_group(self, healthy):
        self.g_clin.setEnabled(not healthy)
        self.spin_auto.setEnabled(healthy)
        self._trial_btn(not self.trial_on)
        self.toast("피험자 군: " + (f"비장애인 대조군 ({self.spin_auto.value()}초 자동 측정)"
                                     if healthy else "편마비 환자군 (수동 구간 측정)"))

    def _on_palm(self, mm):
        self.worker.set_palm_calib(mm)
        self.toast(f"손 길이 보정: {mm} mm" if mm else "손 길이 보정 해제 (모델 추정값 사용)")

    def _on_view(self, idx):
        self.worker.set_view_mode([VIEW_COLOR, VIEW_DEPTH, VIEW_BOTH][idx])
        if self.worker.source_name != "realsense" and idx:
            self.toast("⚠️ RealSense 미연결 → Depth 화면을 표시할 수 없습니다.")
        else:
            self.toast(f"보기 모드: {self.cb_view.currentText()}")

    def _cycle_view(self):
        self.cb_view.setCurrentIndex((self.cb_view.currentIndex() + 1) % self.cb_view.count())

    def _on_mirror(self, v):
        self.worker.set_mirror_mode(v)
        self.toast(f"미러링: {'ON (좌우반전)' if v else 'OFF'}")

    def _on_3d(self, v):
        self.worker.set_enable_3d(v)
        if not v:
            self.view3d.reset_view()
        self.toast(f"3D 재구성: {'ON' if v else 'OFF'}")

    def _on_smooth(self, v):
        self.worker.set_smooth_3d(v)
        self.view3d.reset_view()
        self.toast(f"3D 좌표 스무딩: {'ON' if v else 'OFF (원본 사용)'}")

    def _space(self):
        self.toggle_trial() if self.session_on else self.start_session()

    def _auto_mode(self):
        """비장애인 대조군 = 고정 시간 자동 측정, 편마비 환자군 = 수동 시작/종료."""
        return self.rb_healthy.isChecked()

    def _trial_btn(self, starting):
        if starting:
            tail = (f"{self.spin_auto.value()}초 자동 측정" if self._auto_mode() else "동작 시작")
        else:
            tail = (f"측정 중... {self.auto_left:.1f}초" if self._auto_mode() else "동작 완료")
        self.btn_trial.setText(
            f"{'▶' if starting else '⏹'}  [Trial #{self.trial_idx}] {tail}"
            + ("" if (not starting and self._auto_mode()) else "\nSpace로 실행"))
        self.btn_trial.setStyleSheet("" if starting else
                                     "#trial{background:#ea580c;border:2px solid #fdba74;}")

    def _status(self, text, color):
        self.lbl_trial.setText(text)
        self.lbl_trial.setStyleSheet(f"color:{color}; font-weight:bold;")

    # ---------------------------- 세션 ----------------------------
    def _session_controls(self, enabled):
        for widget in (self.txt_name, self.spin_age, self.cb_gender, self.rb_healthy,
                       self.rb_patient, self.spin_fma, self.cb_brs, self.cb_affected,
                       self.spin_palm, self.chk_filter, self.chk_smooth, self.chk_hold):
            widget.setEnabled(enabled)
        self.spin_auto.setEnabled(enabled and self.rb_healthy.isChecked())

    def _on_task(self, text):
        if self.session_on:
            self.task_history.append((time.perf_counter() - self.t_session, text))

    def _task_at(self, t):
        return next((task for changed, task in reversed(self.task_history) if changed <= t),
                    self.task_history[0][1])

    def start_session(self):
        if self.session_on or self.finishing or self.unsaved:
            return self.toast('이전 세션 저장을 먼저 완료해주세요.')
        if not self.worker.isRunning():
            return self.toast('카메라가 실행 중이 아닙니다. 연결을 확인하고 프로그램을 다시 시작해주세요.')
        name = self.txt_name.text().strip()
        if not name:
            return self.toast('경고: 피험자 이름을 입력해주세요!')
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip('. ') or 'subject'
        session_id = f"Session_{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid.uuid4().hex[:8]}"
        group = '비장애인' if self.rb_healthy.isChecked() else '환자'
        folder = os.path.join(self.base_dir, f'{group}_{safe_name}', session_id)
        try:
            os.makedirs(folder, exist_ok=False)
        except OSError as exc:
            return self.toast(f'저장 폴더 생성 실패: {exc}')
        self.folder, self.session_id = folder, session_id
        self.session_on, self.trial_on, self.paused = True, False, True
        self.finishing, self.unsaved, self._session_error = False, False, None
        self.t_session, self.trial_idx = time.perf_counter(), 1
        self._last_capture = self._stop_time = None
        self.capture_summary = {}
        self.records.clear()
        self.trials.clear()
        self.frame_log.clear()
        self.task_history = [(0.0, self.cb_task.currentText())]
        self.table.setRowCount(0)
        self.chart.reset_chart()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_trial.setEnabled(False)
        self._trial_btn(True)
        self._session_controls(False)
        self.worker.begin_recording(session_id, folder)
        self.lbl_session.setText('● REC (원본 RGB·깊이 및 두 방법 기록)')
        self.lbl_session.setStyleSheet('color:#ef4444; font-weight:bold; font-size:14px;')
        self._status('손 인식 대기', '#38bdf8')
        self.toast(f'▶ [{self.cb_task.currentText()}] 세션 시작!', ok=True)

    def toggle_trial(self):
        if not self.session_on or self.finishing or not self.records:
            return
        if self.trial_on:
            if self._auto_mode():
                return self.toast(f"⏳ 자동 측정 중입니다 ({self.auto_left:.1f}초 남음).")
            return self._finish_trial()
        if self.paused:
            return self.toast("⏸ 손이 인식된 상태에서만 기록할 수 있습니다.")
        self._start_trial()

    def _start_trial(self):
        self.trial_on = True
        self.t_trial = time.perf_counter() - self.t_session
        self.trial_task = self.cb_task.currentText()
        self.trial_hands = (HANDS if any(k in self.trial_task for k in self.BOTH_HANDS_TASKS)
                            else tuple(self._last_found))
        self._trial_previous = None
        self.cb_task.setEnabled(False)
        if self._auto_mode():
            self.auto_left = float(self.spin_auto.value())
            self._last_tick = time.perf_counter()
            self.btn_trial.setEnabled(False)     # 자동 구간은 중간 개입 없이 끝까지 간다
            self._trial_btn(False)
            self._status(f"🔴 [Trial #{self.trial_idx}] 자동 측정 {self.auto_left:.1f}초 남음",
                         "#f59e0b")
            self.toast(f"▶ [Trial #{self.trial_idx}] {self.auto_left:.0f}초 자동 측정 시작!")
        else:
            self.auto_left = 0.0
            self._trial_btn(False)
            self._status(f"🔴 [Trial #{self.trial_idx}] 동작 진행 중...", "#f59e0b")
            self.toast(f"▶ [Trial #{self.trial_idx}] 시작! 끝나면 [Space]")

    def _finish_trial(self, end_time=None):
        auto = self._auto_mode()
        self.trial_on, self.auto_left = False, 0.0
        t = (time.perf_counter() - self.t_session) if end_time is None else end_time
        t0, dur = self.t_trial, max(0.0, t - self.t_trial)
        task = self.trial_task
        short = task.split(":")[0].strip()

        for hand in self.trial_hands:
            seg = [r for r in self.records if r['hand'] == hand and r['task'] == task
                   and r.get('protocol_valid', True) and t0 <= r['time'] <= t]
            tr = self._trial_metrics(seg)
            tr.update(trial=self.trial_idx, hand=hand, task=task, task_short=short,
                      start=t0, end=t, duration=dur, auto=auto,
                      requested_duration=float(self.spin_auto.value()) if auto else None,
                      interrupted=auto and end_time is None)
            self.trials.append(tr)

            row = self.table.rowCount()
            self.table.insertRow(row)
            cells = [f"Trial #{self.trial_idx}", HAND_KR[hand].split(' ')[0], short,
                     f"{dur:.2f}초", f"{tr['cycles']}회",
                     f"{tr['period']:.2f}" if tr['period'] else "-",
                     f"{tr['tarom']:.1f}°",
                     f"{tr['cmc_rom']:.1f}°" if tr['cmc_rom'] is not None else "-",
                     f"{tr['pab_max']:.0f}°" if tr['pab_max'] is not None else "-",
                     f"{tr['mga']:.1f}cm",
                     f"{tr['flex_speed']:.0f}°/s" if tr['flex_speed'] else "-",
                     f"{tr['sparc']:.2f}" if tr['sparc'] is not None else "-"]
            for c, txt in enumerate(cells):
                self.table.setItem(row, c, QTableWidgetItem(txt))
        self.table.scrollToBottom()
        self.chart.add_trial_span(t0, t)

        self.trial_idx += 1
        self.cb_task.setEnabled(not self.finishing)
        self.btn_trial.setEnabled(self.session_on and not self.paused and not self.finishing)
        self._trial_btn(True)
        self._status(f"완료됨 (총 {len({x['trial'] for x in self.trials})}회)", "#10b981")
        self.toast(f"✅ [Trial #{self.trial_idx-1} - {short}] 기록 완료 ({dur:.2f}초)", ok=True)

    @staticmethod
    def _trial_metrics(seg):
        """구간 지표: 개폐 사이클/주기, TAM, 엄지 CMC/외전, MGA, 각속도, SPARC, 3D 파지폭."""
        filt = [r['filtered'] for r in seg]
        mga = max((f.get('Grip_Aperture', 0.0) for f in filt), default=0.0)   # cm
        pips = [f.get('Index_PIP', 180.0) for f in filt]
        rom = max(pips) - min(pips) if pips else 0.0

        # 관절별 ROM은 CMC 포함 전 관절, TAM 합산은 ASSH 정의(엄지 = MCP + IP)만
        # (ROM은 180-θ 부호 변환과 무관하므로 그대로 사용)
        tam_j = {}
        for jn in JOINT_DEFS:
            vals = [d[jn] for d in filt if d.get(jn) is not None]
            if vals:
                tam_j[jn] = max(vals) - min(vals)
        tam_f = {f: sum(tam_j.get(jn, 0.0) for jn in joints)
                 for f, joints in TAM_JOINTS.items()}
        tarom = sum(tam_f.values())

        def _stat(key):
            vals = [d[key] for d in filt if d.get(key) is not None]
            return (max(vals), max(vals) - min(vals)) if vals else (None, None)

        pab_max, pab_rom = _stat('Thumb_PalmarAbd')
        rab_max, rab_rom = _stat('Thumb_RadialAbd')

        # 엄지는 개폐 패턴이 달라 제외하고 4손가락 평균 굴곡각으로 사이클 판정
        cycles, periods, velocities, spectra = 0, [], [], []
        segments = contiguous_segments(seg)
        valid_duration = sum(part[-1]['time'] - part[0]['time'] for part in segments)
        for part in segments:
            times = [r['time'] for r in part]
            flex = [float(np.mean([r['filtered'][j] for j in CYCLE_JOINTS])) for r in part]
            n, period = count_cycles(times, flex)
            cycles += n
            if period is not None:
                periods.extend([period] * (n - 1))
            vel = ang_velocity(times, flex)
            if vel is not None:
                velocities.extend(vel)
                # FFT requires uniform samples; never interpolate across a gap.
                uniform = np.linspace(times[0], times[-1], len(times))
                smoothness = sparc(np.interp(uniform, times, vel), uniform)
                if smoothness is not None:
                    spectra.append(smoothness)
        period = float(np.mean(periods)) if periods else None
        fs = max(0.0, float(np.max(-np.asarray(velocities)))) if velocities else None
        es = max(0.0, float(np.max(velocities))) if velocities else None
        sp = float(np.mean(spectra)) if spectra else None

        comparisons = [r.get('measurement', {}) for r in seg]
        def values(key):
            return [m[key] for m in comparisons if m.get(key) is not None and np.isfinite(m[key])]
        mp_vals, rs_vals = values('mp_aperture_mm'), values('rs_aperture_mm')
        differences = values('rs_minus_mp_mm')

        def m3(key):
            vals = [r['metrics3d'].get(key) for r in seg
                    if r.get('metrics3d', {}).get(key) is not None]
            return max(vals) if vals else None

        p3 = [r['angles3d'].get('Index_PIP') for r in seg
              if r.get('angles3d', {}).get('Index_PIP') is not None]
        return dict(mga=mga, rom=rom, tarom=tarom, tam_f=tam_f, tam_j=tam_j,
                    cmc_rom=tam_j.get('Thumb_CMC'),
                    pab_max=pab_max, pab_rom=pab_rom, rab_max=rab_max, rab_rom=rab_rom,
                    cycles=cycles, period=period,
                    flex_speed=fs, ext_speed=es, sparc=sp,
                    valid_duration=valid_duration, samples=len(seg), rs_valid_samples=len(rs_vals),
                    mp_mga_mm=max(mp_vals) if mp_vals else None,
                    rs_mga_mm=max(rs_vals) if rs_vals else None,
                    paired_samples=len(differences),
                    rs_mp_mean_diff_mm=float(np.mean(differences)) if differences else None,
                    rs_mp_mean_abs_diff_mm=float(np.mean(np.abs(differences))) if differences else None,
                    mga3d=m3('aperture_mm'), mga3d_cal=m3('aperture_mm_cal'),
                    rom3d=(max(p3) - min(p3)) if len(p3) >= 2 else None)

    def _worker_failed(self, message):
        self._session_error = message
        self.paused = True
        self.btn_trial.setEnabled(False)
        self.toast(f'오류: {message}')
        if self.session_on and not self.finishing:
            self.stop_session()
        elif not self.session_on:
            self.btn_start.setEnabled(False)

    def _worker_stopped(self):
        self.btn_start.setEnabled(False)
        if self.session_on:
            self._recording_finished(self.session_id,
                dict(complete=False, written_frames=0,
                     error=self._session_error or '카메라 작업이 종료되었습니다.'))

    def stop_session(self):
        if self.unsaved:
            return self._save_finished_session()
        if not self.session_on or self.finishing:
            return
        self.finishing = True
        self._stop_time = time.perf_counter() - self.t_session
        self.btn_trial.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.cb_task.setEnabled(False)
        self._status('원본 데이터 저장 마무리 중...', '#f59e0b')
        # Worker emits all in-flight frames before recording_finished.
        self.worker.end_recording()

    def _recording_finished(self, session_id, summary):
        if session_id != self.session_id:
            return
        self.capture_summary = summary
        if self._stop_time is None:
            self._stop_time = time.perf_counter() - self.t_session
        if self.trial_on:
            self._finish_trial(end_time=self._stop_time)
            for trial in self.trials:
                if trial['trial'] == self.trial_idx - 1:
                    trial['interrupted'] = True
        self.session_on = False
        self.finishing = False
        self.unsaved = True
        self._save_finished_session()

    def _save_finished_session(self):
        try:
            self.save_session(self._stop_time or 0.0)
        except Exception as exc:
            self.unsaved = True
            self.btn_stop.setText('저장 재시도')
            self.btn_stop.setEnabled(True)
            self.btn_start.setEnabled(False)
            self.close_pending = False
            self._status('저장 실패 — 메모리 데이터 유지 중', '#ef4444')
            self.toast(f'저장 실패: {exc}. 저장 공간·폴더를 확인한 후 재시도해주세요.')
            return
        self.unsaved = False
        self.btn_stop.setText('■  종료 및 저장')
        self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(self.worker.isRunning())
        self.cb_task.setEnabled(True)
        self._session_controls(True)
        self.lbl_session.setText('● READY (세션 완료)')
        n = len({x['trial'] for x in self.trials})
        error = self._session_error or self.capture_summary.get('error')
        if error:
            self._status('부분 저장 — 오류 확인 필요', '#ef4444')
            self.toast(f'일부 데이터 저장됨: {error}')
        else:
            self._status(f'총 {n}회차 저장됨', '#10b981')
            self.toast(f'✅ 저장 완료! {n}개 회차 / 원본 {self.capture_summary.get("written_frames", 0)}프레임', ok=True)
        if self.close_pending:
            self.close_pending = False
            QTimer.singleShot(0, self.close)

    # ---------------------------- 저장 ----------------------------
    @staticmethod
    def _f(v, fmt="{:.2f}"):
        """None/NaN은 빈 칸으로 (0으로 채우면 실제 0과 구분 불가)."""
        try:
            return fmt.format(v) if v is not None and np.isfinite(v) else ""
        except TypeError:
            return ""

    def save_session(self, duration):
        pre = self.session_id
        f = self._f
        # A manual stop may precede delivery of an already captured frame.
        # Recompute from the fully drained recording so raw CSV and summaries agree.
        for trial in self.trials:
            seg = [r for r in self.records if r['hand'] == trial['hand']
                   and r['task'] == trial['task'] and r['protocol_valid']
                   and trial['start'] <= r['time'] <= trial['end']]
            trial.update(self._trial_metrics(seg))
        self._export_comparison(pre)

        # ---- 연속 시계열 ----
        head = ["time_s", "Task", "Trial", "Phase", "hand"]
        for j in JOINT_DEFS:
            head += [f"{j}_raw", f"{j}_filt"]
        head += ["Grip_Aperture_cm_raw", "Grip_Aperture_cm_filt",
                 "Thumb_PalmarAbd_raw", "Thumb_PalmarAbd_filt",
                 "Thumb_RadialAbd_raw", "Thumb_RadialAbd_filt", "Wrist_Depth_m"]
        head += [f"{j}_3D" for j in JOINT_DEFS]
        head += ["Grip_Aperture_mm_3D", "Grip_Aperture_mm_3D_cal",
                 "Grip_Aperture_pctPalm_3D", "Palm_Len_mm_3D", "Recon_Mode"]
        for nm in LM_NAMES:                       # 정준계 좌표 (손 회전 제거)
            head += [f"{nm}_canon_{ax}" for ax in "XYZ"]
        head += ['Frame_ID', 'Protocol_Valid']

        path_raw = os.path.join(self.folder, f"{pre}_continuous_raw.csv")
        with open(path_raw, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(head)
            for rec in self.records:
                t, tag, phase = rec['time'], "Rest", "Rest"
                task = rec['task']
                for tr in self.trials:
                    if (tr['hand'] == rec['hand'] and tr['task'] == task
                            and tr['start'] <= t <= tr['end']):
                        tag, phase = f"Trial_{tr['trial']}", "Grasping"
                        break
                a3, m3 = rec.get('angles3d') or {}, rec.get('metrics3d') or {}
                row = [f"{t:.4f}", task, tag, phase, rec['hand']]
                for j in JOINT_DEFS:
                    row += [f(rec['raw'].get(j)), f(rec['filtered'].get(j))]
                row += [f(rec['raw'].get('Grip_Aperture')), f(rec['filtered'].get('Grip_Aperture'))]
                for k in ABD_KEYS:
                    row += [f(rec['raw'].get(k)), f(rec['filtered'].get(k))]
                row += [f(rec.get('wrist_depth'), "{:.4f}")]
                row += [f(a3.get(j)) for j in JOINT_DEFS]
                row += [f(m3.get('aperture_mm'), "{:.1f}"), f(m3.get('aperture_mm_cal'), "{:.1f}"),
                        f(m3.get('aperture_pct_palm')), f(m3.get('palm_len_mm'), "{:.1f}"),
                        m3.get('mode', '')]
                pts = rec.get('canon')
                row += ([f"{v:.4f}" for p in pts for v in p] if pts is not None else [""] * 63)
                row += [rec['frame_id'], int(rec['protocol_valid'])]
                w.writerow(row)

        # ---- 회차 요약 (손가락별 TAM + 관절별 ROM + 엄지 외전 포함) ----
        joint_cols = [j for j in JOINT_DEFS]
        path_sum = os.path.join(self.folder, f"{pre}_trials_summary.csv")
        with open(path_sum, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(["Trial", "Hand", "Task", "Trial_Mode",
                        "Start_s", "End_s", "Duration_s", "Cycles",
                        "Cycle_Period_s", "TAM_total_deg", "MGA_cm", "Index_ROM_deg",
                        "Flex_Speed_deg_s", "Ext_Speed_deg_s", "SPARC",
                        "MGA_mm_3D", "MGA_mm_3D_cal", "Index_ROM_3D_deg",
                        "Thumb_CMC_ROM_deg",
                        "Thumb_PalmarAbd_max_deg", "Thumb_PalmarAbd_ROM_deg",
                        "Thumb_RadialAbd_max_deg", "Thumb_RadialAbd_ROM_deg"]
                       + [f"TAM_{x}_deg" for x in FINGERS]
                       + [f"ROM_{j}_deg" for j in joint_cols]
                       + ['Valid_Duration_s', 'Samples', 'RS_Valid_Samples', 'Paired_Samples',
                          'MP_MGA_raw_mm', 'RS_MGA_raw_mm', 'RS_minus_MP_mean_mm',
                          'RS_MP_mean_abs_difference_mm', 'Requested_Duration_s', 'Interrupted'])
            for tr in self.trials:
                w.writerow([f"Trial #{tr['trial']}", tr['hand'], tr['task_short'],
                            "auto" if tr.get('auto') else "manual",
                            f"{tr['start']:.2f}", f"{tr['end']:.2f}", f"{tr['duration']:.2f}",
                            tr['cycles'], f(tr['period']), f(tr['tarom']), f(tr['mga']),
                            f(tr['rom']), f(tr['flex_speed'], "{:.1f}"),
                            f(tr['ext_speed'], "{:.1f}"), f(tr['sparc'], "{:.3f}"),
                            f(tr['mga3d'], "{:.1f}"), f(tr['mga3d_cal'], "{:.1f}"), f(tr['rom3d']),
                            f(tr['cmc_rom']),
                            f(tr['pab_max']), f(tr['pab_rom']),
                            f(tr['rab_max']), f(tr['rab_rom'])]
                           + [f(tr['tam_f'].get(x)) for x in FINGERS]
                           + [f(tr['tam_j'].get(j)) for j in joint_cols]
                           + [f(tr['valid_duration']), tr['samples'], tr['rs_valid_samples'],
                              tr['paired_samples'], f(tr['mp_mga_mm']), f(tr['rs_mga_mm']),
                              f(tr['rs_mp_mean_diff_mm']), f(tr['rs_mp_mean_abs_diff_mm']),
                              f(tr['requested_duration']), int(tr['interrupted'])])

        meta = {
            'schema_version': 2,
            'session_id': self.session_id,
            'raw_recording': self.capture_summary,
            'session_error': self._session_error,
            'processed_frames': len(self.frame_log),
            'clock': 'capture_monotonic_s = host perf_counter at frame receipt; time_s is relative to session start',
            'frame_pairing': 'Frame_ID joins all CSVs to raw_frames/frames.csv and frame_XXXXXXXX.npz',
            'raw_arrays': 'color_bgr uint8 (unmirrored, no overlays); depth_native_z16 and depth_aligned_z16 uint16 when available',
            'video_files': {'original.avi': 'Unmirrored original colour camera stream, MJPG playback copy; lossless source remains in NPZ',
                            'mediapipe.avi': 'Same frames with MediaPipe landmarks, MP/RS distances, frame ID and detected hand count'},
            'video_timeline': '30 FPS playback, previous frame held over capture gaps. frames.csv video_frame_index maps source samples to both videos. Images are not interpolated.',
            'raw_scope': 'Every frame acquired by this app during recording, including no-hand frames; not a guarantee of every sensor frame. In-flight raw frames may extend past session stop; filter by time.',
            'measurement_methods': {
                'MP': 'Unsmoothed MediaPipe world landmarks (metres, hand-centred); aperture is tip 4 to tip 8 distance in mm',
                'MP_cal': 'MP aperture scaled by measured wrist-to-middle-MCP length; separate optional estimate',
                'RS': 'MediaPipe unmirrored image pixels + unfiltered color-aligned depth + aligned intrinsics; XYZ in metres in aligned camera frame',
                'comparison': 'RS-minus-MP is inter-method difference, NOT accuracy against ground truth; origins differ, compare distances, not absolute XYZ'},
            'depth_quality_gate': dict(min_m=DEPTH_MIN_M, max_m=DEPTH_MAX_M,
                                       neighborhood='3x3, valid centre, >= half valid samples',
                                       max_p90_p10_m=DEPTH_EDGE_M, fill_holes=False),
            'measurement_filter_enabled': self.chk_filter.isChecked(),
            'landmark_smoothing_enabled': self.chk_smooth.isChecked(),
            'display_mirrored': self.chk_mirror.isChecked(),
            'gap_policy': f'No cycle/velocity across missing frames or gaps > {MAX_FRAME_GAP_S}s; auto timer uses consecutive valid frame intervals for the hands present at trial start',
            'smoothness_definition': 'Legacy fixed-10-Hz spectral arc index on angular velocity; uniform resampling within valid segments, averaged across segments; not a validated clinical SPARC implementation',
            'versions': dict(python=sys.version, numpy=np.__version__, opencv=cv2.__version__,
                             mediapipe=getattr(mp, '__version__', None), pyqt=QtCore.PYQT_VERSION_STR),
            'source_sha256': {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                              for name in ('Mirror_therapy.py', 'mirror_capture.py')},
            "name": self.txt_name.text().strip(), "age": self.spin_age.value(),
            "gender": self.cb_gender.currentText(),
            "group": "Healthy" if self.rb_healthy.isChecked() else "Patient",
            "fma_score": self.spin_fma.value() if self.rb_patient.isChecked() else None,
            "brunnstrom": self.cb_brs.currentText() if self.rb_patient.isChecked() else None,
            "affected_side": self.cb_affected.currentText() if self.rb_patient.isChecked() else None,
            "total_trials": len({x['trial'] for x in self.trials}),
            "trial_mode": ("healthy: fixed-duration auto trial"
                           if self.rb_healthy.isChecked() else
                           "patient: manual start/stop"),
            "auto_trial_sec": (self.spin_auto.value()
                               if self.rb_healthy.isChecked() else None),
            "angle_convention": "angle3() inter-segment angle; 180 deg = full extension. "
                                "Convert to flexion as (180 - theta) when reporting.",
            "tam_definition": "TAM_total = sum over 5 fingers. Thumb = MCP + IP (ASSH); "
                              "CMC is reported separately and NOT included in TAM. "
                              "ROM = max - min within trial.",
            "thumb_cmc": ("Thumb_CMC = angle(wrist, CMC, MCP). The wrist-CMC segment is a "
                          "virtual palm segment, so this is a palm-relative composite of CMC "
                          "flexion and abduction, not an isolated joint angle."),
            "thumb_abduction": ("Palmar abduction = |out-of-palm-plane angle| of the 1st "
                                "metacarpal; radial abduction = in-plane angle to the 2nd "
                                "metacarpal (intermetacarpal angle). Both are magnitudes "
                                "(sign-free), so left and right hands are directly comparable."),
            "joint_defs": {k: list(v) for k, v in JOINT_DEFS.items()},
            "angle_3d_source": ("MediaPipe world landmark + One-Euro smoothing + SVD palm "
                                "canonicalization. Rotation+uniform-scale transform, so joint "
                                "angles equal those from the corresponding smoothed world landmarks, not necessarily raw world landmarks."),
            "coord_3d_units": "canonical palm frame: wrist origin, palm length = 1.0, rotation removed",
            "palm_frame_landmarks": FRAME_IDS,
            "hand_length_calib_mm": self.spin_palm.value() or None,
            "aperture_units": {"Grip_Aperture_cm": "cm (world landmark)",
                               "Grip_Aperture_mm_3D": "mm (model hand scale)",
                               "Grip_Aperture_mm_3D_cal": "mm (subject-calibrated)",
                               "Grip_Aperture_pctPalm_3D": "% of palm length"},
            "hold_motion_correction": self.chk_hold.isChecked(),
            "session_duration_sec": duration,
            "camera": self.worker.source_name,
            "depth_usage": "parallel RS 3D landmarks/aperture measurement and wrist distance display",
            "known_limitation": ("DIP angles are least reliable under monocular occlusion "
                                 "(fist closure). Thumb CMC and palmar abduction depend on the "
                                 "thenar-base landmark and the palm-plane normal, so expect "
                                 "lower reliability than PIP; report their ICC separately. "
                                 "Inspect *_joint_angles.png before reporting."),
            "saved_at": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        }
        with open(os.path.join(self.folder, "subject_metadata.json"), 'w', encoding='utf-8') as fp:
            json.dump(meta, fp, ensure_ascii=False, indent=2)
        if self.records:
            self.export_plot(os.path.join(self.folder, f"{pre}_waveform.png"), pre)
            self.export_joint_plot(os.path.join(self.folder, f"{pre}_joint_angles.png"), pre)

    def _export_comparison(self, pre):
        """Per-frame distances and all 21 landmarks, including invalid depth reasons."""
        f = self._f
        with open(os.path.join(self.folder, f'{pre}_distance_comparison.csv'), 'w',
                  newline='', encoding='utf-8-sig') as fp:
            writer = csv.writer(fp)
            writer.writerow(['Frame_ID', 'time_s', 'capture_monotonic_s', 'capture_unix_s',
                             'Hand', 'Task', 'Protocol_Valid', 'MP_Valid', 'RS_Valid',
                             'MP_Aperture_raw_mm', 'MP_Aperture_cal_mm', 'RS_Aperture_raw_mm',
                             'RS_minus_MP_mm', 'RS_Thumb_Status', 'RS_Index_Status',
                             'Handedness_Score', 'Color_Frame_Number', 'Color_Timestamp_ms',
                             'Depth_Frame_Number', 'Depth_Timestamp_ms'])
            for rec in self.records:
                m = rec['measurement']
                writer.writerow([rec['frame_id'], f(rec['time'], '{:.6f}'),
                                 f(rec['capture_monotonic_s'], '{:.6f}'), f(rec['capture_unix_s'], '{:.6f}'),
                                 rec['hand'], rec['task'], int(rec['protocol_valid']),
                                 int(m['mp_valid']), int(m['rs_valid']),
                                 f(m['mp_aperture_mm'], '{:.4f}'), f(m['mp_aperture_cal_mm'], '{:.4f}'),
                                 f(m['rs_aperture_mm'], '{:.4f}'), f(m['rs_minus_mp_mm'], '{:.4f}'),
                                 m['rs_status'][4], m['rs_status'][8], f(m.get('handedness_score'), '{:.4f}'),
                                 rec.get('color_frame_number'), f(rec.get('color_timestamp_ms'), '{:.6f}'),
                                 rec.get('depth_frame_number'), f(rec.get('depth_timestamp_ms'), '{:.6f}')])
        with open(os.path.join(self.folder, f'{pre}_landmarks.csv'), 'w',
                  newline='', encoding='utf-8-sig') as fp:
            writer = csv.writer(fp)
            writer.writerow(['Frame_ID', 'time_s', 'Hand', 'Landmark_ID', 'Landmark',
                             'Pixel_U', 'Pixel_V', 'MP_X_m', 'MP_Y_m', 'MP_Z_m',
                             'RS_X_m', 'RS_Y_m', 'RS_Z_m', 'RS_Depth_m', 'RS_Status'])
            for rec in self.records:
                m = rec['measurement']
                for i, name in enumerate(LM_NAMES):
                    writer.writerow([rec['frame_id'], f(rec['time'], '{:.6f}'), rec['hand'], i, name]
                                    + [f(v, '{:.4f}') for v in m['pixels'][i]]
                                    + [f(v, '{:.8f}') for v in m['mp_points'][i]]
                                    + [f(v, '{:.8f}') for v in m['rs_points'][i]]
                                    + [f(m['rs_depth_m'][i], '{:.6f}'), m['rs_status'][i]])
        with open(os.path.join(self.folder, f'{pre}_frame_quality.csv'), 'w',
                  newline='', encoding='utf-8-sig') as fp:
            fields = ['time', 'frame_id', 'task', 'hands', 'protocol_valid',
                      'ambiguous_handedness', 'capture_monotonic_s', 'capture_unix_s']
            writer = csv.DictWriter(fp, fields)
            writer.writeheader()
            writer.writerows(self.frame_log)

    def export_plot(self, path, title):
        fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, dpi=150,
                                 gridspec_kw={'height_ratios': [3, 3, 2]})
        fig.patch.set_facecolor('#ffffff')
        keys = {FLEX_OF[f]: (FINGER_COLORS[f], f) for f in FINGERS}

        for ax, hand in zip(axes[:2], HANDS):
            seg = [r for r in self.records if r['hand'] == hand]
            if not seg:
                ax.text(.5, .5, f"{hand}: 데이터 없음", ha='center', transform=ax.transAxes)
                continue
            ts = [r['time'] for r in seg]
            for k, (col, lab) in keys.items():
                ax.plot(ts, [r['filtered'].get(k, np.nan) for r in seg], color=col, lw=1.6, label=lab)
            ax.set_ylim(0, 180)
            ax.set_ylabel(f"{HAND_KR[hand]}\nFlexion (deg)", fontweight='bold')
            ax.grid(True, ls=':', alpha=.6)
            ax.legend(loc='upper right', fontsize=7, ncol=5)

        for hand, style in (('Right', '-'), ('Left', '--')):
            seg = [r for r in self.records if r['hand'] == hand]
            if not seg:
                continue
            ts = [r['time'] for r in seg]
            axes[2].plot(ts, [r['filtered'].get('Grip_Aperture', np.nan) for r in seg],
                         style, color='#0ea5e9', lw=1.4, label=f"{hand} 파지폭 (cm)")
        axes[2].set_ylabel("파지폭 (cm)", fontweight='bold')
        axes[2].set_xlabel("Elapsed Time (s)", fontweight='bold')
        axes[2].grid(True, ls=':', alpha=.6)
        axes[2].legend(loc='upper right', fontsize=7)

        for trial in {t['trial']: t for t in self.trials}.values():
            for ax in axes:
                ax.axvspan(trial['start'], trial['end'], color='#fef08a', alpha=.35)
            axes[0].text((trial['start'] + trial['end']) / 2, 168,
                         f"T{trial['trial']} ({trial['task_short']})", color='#854d0e',
                         fontweight='bold', fontsize=8, ha='center')

        axes[0].set_title(f"[{title}] open-close session", fontsize=11, fontweight='bold')
        plt.tight_layout()
        plt.savefig(path)
        plt.close(fig)

    def export_joint_plot(self, path, title):
        """손가락 5행 × 양손 2열 + 엄지 외전 1행. 각 축에 3단 관절을 겹쳐 그린다."""
        nrow = len(FINGERS) + 1
        fig, axes = plt.subplots(nrow, 2, figsize=(13, 15), sharex=True, dpi=150)
        fig.patch.set_facecolor('#ffffff')
        spans = list({t['trial']: t for t in self.trials}.values())

        for c, hand in enumerate(HANDS):
            seg_rec = [r for r in self.records if r['hand'] == hand]
            ts = [r['time'] for r in seg_rec]
            for rw, f in enumerate(FINGERS):
                ax = axes[rw][c]
                if rw == 0:
                    ax.set_title(HAND_KR[hand], fontsize=11, fontweight='bold')
                if not seg_rec:
                    ax.text(.5, .5, "데이터 없음", ha='center', transform=ax.transAxes)
                    continue
                for seg, jname in zip(SEG_LABELS, JOINT_TRIPLE[f]):
                    if jname is None:
                        continue
                    ax.plot(ts, [r['filtered'].get(jname, np.nan) for r in seg_rec],
                            color=SEG_COLORS[seg], lw=1.3, label=jname.split('_', 1)[1])
                for tr in spans:
                    ax.axvspan(tr['start'], tr['end'], color='#fef08a', alpha=.35)
                ax.set_ylim(0, 180)
                ax.set_yticks([0, 45, 90, 135, 180])
                ax.grid(True, ls=':', alpha=.6)
                ax.legend(loc='lower right', fontsize=6, ncol=3)
                if c == 0:
                    ax.set_ylabel(f"{f}\n각도(°)", fontweight='bold', fontsize=9)

            # 엄지 외전 2성분
            ax = axes[-1][c]
            if seg_rec:
                for key, col, lab in (('Thumb_PalmarAbd', '#8b5cf6', '장측외전'),
                                      ('Thumb_RadialAbd', '#ec4899', '요측외전')):
                    ax.plot(ts, [r['filtered'].get(key, np.nan) for r in seg_rec],
                            color=col, lw=1.3, label=lab)
                for tr in spans:
                    ax.axvspan(tr['start'], tr['end'], color='#fef08a', alpha=.35)
                ax.legend(loc='lower right', fontsize=6, ncol=2)
            else:
                ax.text(.5, .5, "데이터 없음", ha='center', transform=ax.transAxes)
            ax.set_ylim(0, 120)
            ax.grid(True, ls=':', alpha=.6)
            if c == 0:
                ax.set_ylabel("Thumb Abd\n각도(°)", fontweight='bold', fontsize=9)
            ax.set_xlabel("Elapsed Time (s)", fontweight='bold')

        fig.suptitle(f"[{title}] 관절별 각도 변화 (엄지 CMC/MCP/IP · 180° = 신전)",
                     fontsize=12, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.98])
        plt.savefig(path)
        plt.close(fig)

    # ---------------------------- 프레임 ----------------------------
    def on_frame(self, frame, angles, fps, n_hands, depths, hands3d, capture):
        cam = 'RealSense' if capture['source'] == 'realsense' else 'Webcam (RS 결측)'
        self.lbl_fps.setText(f'{cam} | FPS: {fps:.1f} | Hands: {n_hands}')
        captured = capture['capture_monotonic_s']
        self._last_capture = captured
        self._last_found = [h for h in HANDS if h in angles]
        if self.session_on and capture.get('session_id') == self.session_id:
            t = captured - self.t_session
            if t >= 0 and (self._stop_time is None or t <= self._stop_time):
                task = self._task_at(t)
                both = any(k in task for k in self.BOTH_HANDS_TASKS)
                found = self._last_found
                required = (self.trial_hands if self.trial_on and t >= self.t_trial
                            else HANDS if both else ())
                ok = all(h in found for h in required) if required else bool(found)
                fresh = time.perf_counter() - captured <= MAX_FRAME_GAP_S
                self.paused = not (ok and fresh)
                self.frame_log.append(dict(time=t, frame_id=capture['frame_id'], task=task,
                                           hands=';'.join(found), protocol_valid=ok,
                                           ambiguous_handedness=capture.get('ambiguous_handedness', False),
                                           capture_monotonic_s=captured,
                                           capture_unix_s=capture['capture_unix_s']))
                for hand, measurement in capture['measurements'].items():
                    rec = hands3d.get(hand)
                    data = angles.get(hand, {'raw': {}, 'filtered': {}})
                    self.records.append({
                        'time': t, 'frame_id': capture['frame_id'], 'hand': hand, 'task': task,
                        'protocol_valid': ok and hand in angles,
                        'capture_monotonic_s': captured, 'capture_unix_s': capture['capture_unix_s'],
                        'color_frame_number': capture.get('color_frame_number'),
                        'color_timestamp_ms': capture.get('color_timestamp_ms'),
                        'depth_frame_number': capture.get('depth_frame_number'),
                        'depth_timestamp_ms': capture.get('depth_timestamp_ms'),
                        'raw': data['raw'], 'filtered': data['filtered'],
                        'angles3d': rec['angles'] if rec else {},
                        'metrics3d': rec['metrics'] if rec else {},
                        'canon': rec['canon'] if rec else None,
                        'measurement': measurement, 'wrist_depth': depths.get(hand)})
                self.chart.update_data(t, angles)
                if self.trial_on and self._auto_mode() and t >= self.t_trial and not self.finishing:
                    if ok:
                        if self._trial_previous is not None:
                            delta = t - self._trial_previous
                            if 0 < delta <= MAX_FRAME_GAP_S:
                                self.auto_left = max(0.0, self.auto_left - delta)
                        self._trial_previous = t
                        if self.auto_left <= 1e-9:
                            self._finish_trial(end_time=t)
                    else:
                        self._trial_previous = None
                self.btn_trial.setEnabled(not self.finishing and
                    ((self.trial_on and not self._auto_mode()) or
                     (not self.trial_on and not self.paused)))

        if self.chk_3d.isChecked():
            self.view3d.update_hands(captured - self.t_app, hands3d)
        for hand in HANDS:
            self._update_gauge(hand, angles.get(hand), depths.get(hand))
        h, w, ch = frame.shape
        img = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format.Format_BGR888)
        self.lbl_video.setPixmap(QtGui.QPixmap.fromImage(img).scaled(
            self.lbl_video.width(), self.lbl_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _tick(self):
        now = time.perf_counter()
        if not self.session_on or self.finishing:
            return
        self.lbl_session.setText(
            f'● REC ({now - self.t_session:.1f}초 | {len(self.frame_log)} 프레임)')
        if self._last_capture is None or now - self._last_capture > MAX_FRAME_GAP_S:
            self.paused = True
            self._trial_previous = None
            self.btn_trial.setEnabled(self.trial_on and not self._auto_mode())
        if self.paused:
            self._status('⏸ 손/영상 인식 대기 — 유효 측정 시간 정지', '#f97316')
        elif self.trial_on and self._auto_mode():
            self._trial_btn(False)
            self._status(f'🔴 [Trial #{self.trial_idx}] 유효 측정 {self.auto_left:.1f}초 남음', '#f59e0b')
        elif self.trial_on:
            self._status(f'🔴 [Trial #{self.trial_idx}] 동작 진행 중...', '#f59e0b')
        else:
            self._status('준비됨 (동작 시작 대기)', '#38bdf8')

    def _open_folder(self):
        d = self.folder if os.path.exists(self.folder) else self.base_dir
        os.startfile(d) if sys.platform == 'win32' else self.toast(f"폴더: {d}")

    def closeEvent(self, e):
        if self.session_on or self.finishing:
            self.close_pending = True
            self.stop_session()
            e.ignore()
            return
        if self.unsaved:
            self.close_pending = True
            self._save_finished_session()
            e.ignore()
            return
        self.worker.stop()
        e.accept()


def main():
    for attr in ('AA_EnableHighDpiScaling', 'AA_UseHighDpiPixmaps'):
        if hasattr(QtCore.Qt.ApplicationAttribute, attr):
            QtWidgets.QApplication.setAttribute(
                getattr(QtCore.Qt.ApplicationAttribute, attr), True)
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 10))
    win = ClinicalApp()
    win.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

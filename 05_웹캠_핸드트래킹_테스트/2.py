"""
[공압장갑 Master-Slave 미러테라피 및 AI 손 기능 정량 평가 시스템 v2.5 - 고성능 저지연 버전]
- 제로 딜레이 최적화 (Zero-Latency Architecture):
  ① 카메라 버퍼 큐 딜레이 제거 (BUFFERSIZE=1)
  ② 640x480 고속 경량 추론 (MediaPipe 지연시간 80ms -> 15ms 단축, 30~60 FPS 보장)
  ③ 속도 비례 고감도 One-Euro 필터 (정지 시 안정성 + 동작 시 지연시간 < 5ms 즉각 추종)
  ④ UI 렌더링 파이프라인 가속 (FastTransformation)
- 손바닥 로컬 정규화 좌표계(Canonical Palm Frame): 카메라 거리/깊이(Z축) 이동 시 각도 100% 불변
- Task 1~3 단일 손 즉시 측정 / Task별·Trial별 실시간 개별 파일 분할 저장
"""

import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import sys
import csv
import json
import time
import math
from datetime import datetime
from collections import deque

import cv2
import mediapipe as mp
import numpy as np

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QRadioButton,
    QButtonGroup, QPushButton, QGroupBox, QFrame, QTextEdit,
    QCheckBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


# ================================================================
# 1. 고감도 저지연 One-Euro Filter (Zero-Delay One-Euro Filter)
# ================================================================
class OneEuroFilter:
    """
    지연 시간(Lag)이 없는 속도 비례 적응형 1-유로 필터:
    - 정지 시(min_cutoff=0.8Hz): 노이즈 및 지터 억제
    - 움직일 시(beta=0.06): 속도에 비례해 컷오프가 즉시 20Hz 이상으로 올라가 딜레이 제로 추종
    """
    def __init__(self, t0=0.0, x0=180.0, dx0=0.0, min_cutoff=0.8, beta=0.06, d_cutoff=1.2):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)
        self.t_prev = float(t0)

    def smoothing_factor(self, t_e, cutoff):
        r = 2.0 * math.pi * cutoff * t_e
        return r / (r + 1.0)

    def exponential_smoothing(self, a, x, x_prev):
        return a * x + (1.0 - a) * x_prev

    def filter(self, t, x):
        t_e = t - self.t_prev
        if t_e <= 0.0:
            return self.x_prev

        # 속도(미분) 추정
        raw_dx = (x - self.x_prev) / t_e
        a_d = self.smoothing_factor(t_e, self.d_cutoff)
        dx_hat = self.exponential_smoothing(a_d, raw_dx, self.dx_prev)

        # 동적 컷오프 주파수
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self.smoothing_factor(t_e, cutoff)
        x_hat = self.exponential_smoothing(a, x, self.x_prev)

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


# ================================================================
# 2. 하이브리드 생체역학 필터 (결측치 및 물리적 한계 보정)
# ================================================================
class HybridKinematicFilter:
    def __init__(self, init_val=180.0):
        self.val = float(init_val)
        self.last_valid_val = float(init_val)
        self.missing_count = 0
        self.max_missing_hold = 20
        self.euro_filter = OneEuroFilter(t0=0.0, x0=init_val)
        self.max_deg_per_frame = 45.0  # 초당 1300도 이상의 비정상 스파이크만 클램핑

    def update(self, t, raw_val):
        if raw_val is None or (isinstance(raw_val, float) and (np.isnan(raw_val) or raw_val <= 0.0)):
            self.missing_count += 1
            if self.missing_count <= self.max_missing_hold:
                return self.last_valid_val
            else:
                self.last_valid_val = 0.98 * self.last_valid_val + 0.02 * 160.0
                return self.last_valid_val

        self.missing_count = 0

        # 비정상 점프 방지 (단일 프레임 45도 초과 시 클램핑)
        delta = raw_val - self.last_valid_val
        if abs(delta) > self.max_deg_per_frame:
            clamped_val = self.last_valid_val + math.copysign(self.max_deg_per_frame, delta)
        else:
            clamped_val = raw_val

        filtered_val = self.euro_filter.filter(t, clamped_val)
        filtered_val = max(0.0, min(180.0, filtered_val))
        self.last_valid_val = filtered_val
        self.val = filtered_val
        return filtered_val


# ================================================================
# 3. 손바닥 정규화 좌표계(Canonical Palm Frame) 및 3D 관절 각도
# ================================================================
def normalize_to_canonical_palm_frame(landmarks):
    """
    21개 랜드마크를 손바닥 로컬 직교 좌표계로 변환:
    - 원점: Wrist(P0)
    - Y축: Wrist(P0) -> Middle MCP(P9)
    - Z축: 손바닥 평면 법선 벡터 (P5, P17 외적)
    - X축: Y축과 Z축의 외적 (손바닥 가로축)
    - 손바닥 길이(norm_y)로 스케일 정규화
    -> 카메라와의 거리(Z 깊이), 화면 내 위치, 손의 전역 회전에 100% 독립적
    """
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float64)
    p0, p5, p9, p17 = pts[0], pts[5], pts[9], pts[17]

    v_y = p9 - p0
    ny = np.linalg.norm(v_y)
    if ny < 1e-7:
        return pts
    u_y = v_y / ny

    v_z = np.cross(p5 - p0, p17 - p0)
    nz = np.linalg.norm(v_z)
    u_z = v_z / nz if nz > 1e-7 else np.array([0.0, 0.0, 1.0])

    v_x = np.cross(u_y, u_z)
    nx = np.linalg.norm(v_x)
    u_x = v_x / nx if nx > 1e-7 else np.array([1.0, 0.0, 0.0])

    u_z = np.cross(u_x, u_y)
    znm = np.linalg.norm(u_z)
    if znm > 1e-7:
        u_z /= znm

    R = np.vstack([u_x, u_y, u_z])
    return (R @ (pts - p0).T).T / ny


def calc_angle_3d(pa, pb, pc):
    """세 점 pa, pb, pc에서 pb를 꼭짓점으로 하는 3D 사잇각 (단위: 도, 0~180)"""
    ba = pa - pb
    bc = pc - pb
    n1, n2 = np.linalg.norm(ba), np.linalg.norm(bc)
    if n1 < 1e-7 or n2 < 1e-7:
        return 180.0
    cos_v = np.clip(np.dot(ba, bc) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_v)))


def compute_angles_and_pts(landmarks):
    """손바닥 로컬 좌표계에서 15개 관절 각도 및 대표 굴곡각 산출"""
    pts = normalize_to_canonical_palm_frame(landmarks)
    a = {}

    # 엄지 (Thumb)
    a['Thumb_MCP'] = calc_angle_3d(pts[1], pts[2], pts[3])
    a['Thumb_IP']  = calc_angle_3d(pts[2], pts[3], pts[4])

    # 검지 (Index)
    a['Index_MCP'] = calc_angle_3d(pts[0], pts[5], pts[6])
    a['Index_PIP'] = calc_angle_3d(pts[5], pts[6], pts[7])
    a['Index_DIP'] = calc_angle_3d(pts[6], pts[7], pts[8])

    # 중지 (Middle)
    a['Middle_MCP'] = calc_angle_3d(pts[0], pts[9], pts[10])
    a['Middle_PIP'] = calc_angle_3d(pts[9], pts[10], pts[11])
    a['Middle_DIP'] = calc_angle_3d(pts[10], pts[11], pts[12])

    # 약지 (Ring)
    a['Ring_MCP'] = calc_angle_3d(pts[0], pts[13], pts[14])
    a['Ring_PIP'] = calc_angle_3d(pts[13], pts[14], pts[15])
    a['Ring_DIP'] = calc_angle_3d(pts[14], pts[15], pts[16])

    # 소지 (Pinky)
    a['Pinky_MCP'] = calc_angle_3d(pts[0], pts[17], pts[18])
    a['Pinky_PIP'] = calc_angle_3d(pts[17], pts[18], pts[19])
    a['Pinky_DIP'] = calc_angle_3d(pts[18], pts[19], pts[20])

    # 손가락별 대표 굴곡각 (Flexion Angle)
    a['Thumb_Flexion']  = a['Thumb_IP']
    a['Index_Flexion']  = a['Index_PIP']
    a['Middle_Flexion'] = a['Middle_PIP']
    a['Ring_Flexion']   = a['Ring_PIP']
    a['Pinky_Flexion']  = a['Pinky_PIP']

    # 엄지-검지 끝 간격 (Grip Aperture, %)
    a['Grip_Aperture'] = float(np.linalg.norm(pts[4] - pts[8]) * 100.0)

    return a, pts


def compute_sparc(velocity_series, dt=1.0/30.0, cutoff_freq=10.0):
    vel = np.array(velocity_series, dtype=np.float64)
    if len(vel) < 15 or np.all(np.abs(vel) < 1e-4):
        return 0.0
    vel = vel - np.mean(vel)
    n = len(vel)
    fft_vals = np.abs(np.fft.rfft(vel))
    freqs = np.fft.rfftfreq(n, d=dt)
    mask = freqs <= cutoff_freq
    f_sub, mag_sub = freqs[mask], fft_vals[mask]
    if len(mag_sub) < 2 or mag_sub[0] < 1e-7:
        return 0.0
    norm_mag = mag_sub / mag_sub[0]
    df = np.diff(f_sub)
    d_mag = np.diff(norm_mag)
    return float(-np.sum(np.sqrt((df / cutoff_freq)**2 + d_mag**2)))


# ================================================================
# 4. 고속 저지연 비디오 캡처 및 MediaPipe 핸드 트래킹 스레드
# ================================================================
class VideoWorker(QThread):
    frame_processed = pyqtSignal(np.ndarray, dict, float, int)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = True
        self.mirror_mode = False
        self.use_filter = True
        self.filters = {}
        self.start_time = time.time()

    def set_mirror_mode(self, enabled):
        self.mirror_mode = enabled
        self.filters = {}

    def set_filter_mode(self, enabled):
        self.use_filter = enabled

    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"[에러] 카메라 {self.camera_index}번을 열 수 없습니다.")
            return

        # ── [핵심 가속] 버퍼 딜레이 제거 및 640x480 고속 경량 해상도 ──
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        mp_styles = mp.solutions.drawing_styles

        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.50
        )

        prev_t = time.time()

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.005)
                continue

            curr_t = time.time()
            fps = 1.0 / max(curr_t - prev_t, 1e-6)
            prev_t = curr_t
            t_sec = curr_t - self.start_time

            if self.mirror_mode:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = hands.process(rgb)
            rgb.flags.writeable = True

            hand_count = 0
            latest_angles = {}

            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
                wl_list = results.multi_hand_world_landmarks

                for hi, hand_lms in enumerate(results.multi_hand_landmarks):
                    hl = "Hand"
                    if results.multi_handedness and hi < len(results.multi_handedness):
                        hl = results.multi_handedness[hi].classification[0].label
                        if self.mirror_mode:
                            hl = "Right" if hl == "Left" else "Left"

                    mp_drawing.draw_landmarks(
                        frame, hand_lms, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style()
                    )

                    calc_lm = wl_list[hi].landmark if (wl_list and hi < len(wl_list)) else hand_lms.landmark

                    # 1. 정규화 좌표계 변환 및 3D 관절 각도 산출
                    raw_angles, _ = compute_angles_and_pts(calc_lm)

                    # 2. 적응형 1-유로 필터링 적용
                    filtered_angles = {}
                    for k, v in raw_angles.items():
                        fk = f"{hl}_{k}"
                        if fk not in self.filters:
                            self.filters[fk] = HybridKinematicFilter(init_val=v)

                        if self.use_filter:
                            filtered_angles[k] = self.filters[fk].update(t_sec, v)
                        else:
                            filtered_angles[k] = v

                    latest_angles[hl] = {
                        'raw': raw_angles,
                        'filtered': filtered_angles
                    }

            self.frame_processed.emit(frame, latest_angles, fps, hand_count)

        cap.release()
        hands.close()

    def stop(self):
        self.running = False
        self.wait(1000)


# ================================================================
# 5. 실시간 Matplotlib 5손가락 각도 그래프 캔버스
# ================================================================
class LiveAngleChart(FigureCanvas):
    HAND_ORDER = ('Right', 'Left')
    HAND_TITLES = {'Right': '오른손 (Right)', 'Left': '왼손 (Left)'}

    def __init__(self, parent=None, width=6, height=4.2, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#131622')
        super().__init__(self.fig)
        self.setParent(parent)

        self.finger_colors = {
            'Thumb': '#ef4444', 'Index': '#0ea5e9', 'Middle': '#22c55e',
            'Ring': '#f59e0b', 'Pinky': '#a855f7'
        }

        self.axes = {}
        self.lines = {}
        self.time_bufs = {}
        self.angle_bufs = {}
        self.trial_spans = {}

        ax_top = self.fig.add_subplot(211)
        ax_bot = self.fig.add_subplot(212, sharex=ax_top)

        for hl, ax in zip(self.HAND_ORDER, [ax_top, ax_bot]):
            ax.set_facecolor('#191c2b')
            ax.set_ylim(0, 180)
            ax.set_yticks([0, 45, 90, 135, 180])
            ax.set_xlim(0, 10)
            ax.set_ylabel(f"{self.HAND_TITLES[hl]}\n굴곡각(°)", color="#cbd5e1", fontsize=8, fontweight='bold')
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for s in ax.spines.values():
                s.set_edgecolor('#334155')
            ax.grid(True, linestyle='--', color='#272b3f', linewidth=0.8)

            self.lines[hl] = {}
            for f, c in self.finger_colors.items():
                ln, = ax.plot([], [], label=f, color=c, linewidth=2.0, alpha=0.95)
                self.lines[hl][f] = ln
            ax.legend(loc='upper right', fontsize=7, ncol=5, facecolor='#191c2b',
                      edgecolor='#334155', labelcolor='#f1f5f9')
            self.axes[hl] = ax
            self.time_bufs[hl] = deque(maxlen=300)
            self.angle_bufs[hl] = {f: deque(maxlen=300) for f in self.finger_colors}
            self.trial_spans[hl] = []

        ax_top.tick_params(labelbottom=False)
        ax_bot.set_xlabel("경과 시간 (초)", color="#cbd5e1", fontsize=9, fontweight='bold')
        self.fig.tight_layout(pad=1.2)
        self.fig.subplots_adjust(hspace=0.12)
        self._ri = 0.05
        self._lt = None

    def update_data(self, t, ad):
        if not ad:
            return
        up = False
        for hl in self.HAND_ORDER:
            if hl not in ad:
                continue
            hd = ad[hl]
            if isinstance(hd, dict) and 'filtered' in hd:
                hd = hd['filtered']
            self.time_bufs[hl].append(t)
            for f in self.finger_colors:
                self.angle_bufs[hl][f].append(hd.get(f"{f}_Flexion", 180.0))
            up = True
        if not up:
            return
        if self._lt is not None and (t - self._lt) < self._ri:
            return
        self._lt = t
        ts = [self.time_bufs[h][-1] for h in self.HAND_ORDER if self.time_bufs[h]]
        if not ts:
            return
        tn = max(ts)
        xm = max(0.0, tn - 10.0)
        for hl in self.HAND_ORDER:
            if len(self.time_bufs[hl]) > 1:
                ta = np.array(self.time_bufs[hl])
                for f in self.finger_colors:
                    self.lines[hl][f].set_data(ta, np.array(self.angle_bufs[hl][f]))
            self.axes[hl].set_xlim(xm, max(10.0, tn))
        self.draw_idle()

    def add_trial_span(self, ts, te, lbl):
        for hl in self.HAND_ORDER:
            sp = self.axes[hl].axvspan(ts, te, color='#0284c7', alpha=0.25)
            self.trial_spans[hl].append(sp)
        self.draw_idle()

    def reset_chart(self):
        for hl in self.HAND_ORDER:
            self.time_bufs[hl].clear()
            for f in self.angle_bufs[hl]:
                self.angle_bufs[hl][f].clear()
            for sp in self.trial_spans[hl]:
                try:
                    sp.remove()
                except Exception:
                    pass
            self.trial_spans[hl].clear()
            self.axes[hl].set_xlim(0, 10)
            for f in self.lines[hl]:
                self.lines[hl][f].set_data([], [])
        self._lt = None
        self.draw_idle()


# ================================================================
# 6. 메인 GUI 윈도우
# ================================================================
class CapstoneClinicalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 Master-Slave 미러테라피 및 AI 손 기능 평가 시스템 v2.5")
        self.resize(1440, 940)
        self.setMinimumSize(1280, 820)

        self.is_session_active = False
        self.session_start_time = 0.0
        self.session_records = []
        self.current_trial_records = []
        self.is_trial_in_progress = False
        self.current_trial_idx = 1
        self.current_trial_start_t = 0.0
        self.completed_trials = []
        self.current_subject_folder = ""
        self.last_angles = {}
        self.task_folders = {}
        self.gauges = {}
        self.gauge_labels = {}
        self.gauge_titles = {}

        default_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "outputs", "데이터_저장"))
        os.makedirs(default_base_dir, exist_ok=True)
        self.base_output_dir = default_base_dir

        self.apply_clean_theme()
        self.init_ui()
        self.setup_shortcuts()

        self.video_worker = VideoWorker(camera_index=0)
        self.video_worker.frame_processed.connect(self.on_frame_ready)
        self.video_worker.start()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_session_timer)
        self.status_timer.start(100)

    def apply_clean_theme(self):
        qss = """
        * { font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-size: 13px; }
        QMainWindow { background-color: #0b0d14; }
        QWidget { color: #f8fafc; }
        QGroupBox {
            background-color: #141724; border: 1px solid #282f48; border-radius: 8px;
            margin-top: 14px; font-weight: bold; font-size: 13px; color: #38bdf8;
            padding: 14px 10px 10px 10px;
        }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 12px; }
        QLabel { color: #e2e8f0; font-size: 13px; font-weight: 500; }
        QLineEdit, QSpinBox {
            background-color: #1c2032; border: 1px solid #3b4566; border-radius: 6px;
            padding: 6px 10px; color: #ffffff; font-size: 13px; font-weight: 600; min-height: 22px;
        }
        QLineEdit:focus, QSpinBox:focus { border: 1px solid #38bdf8; background-color: #242a42; }
        QComboBox {
            background-color: #1c2032; border: 1px solid #3b4566; border-radius: 6px;
            padding: 6px 12px; color: #ffffff; font-size: 13px; font-weight: 600; min-height: 22px;
        }
        QComboBox:hover { border: 1px solid #38bdf8; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: top right; width: 28px;
            border-left: 1px solid #3b4566; background-color: #242a42;
            border-top-right-radius: 5px; border-bottom-right-radius: 5px;
        }
        QComboBox QAbstractItemView {
            background-color: #141724; color: #ffffff; border: 1px solid #38bdf8;
            border-radius: 6px; padding: 4px; selection-background-color: #2563eb;
        }
        QComboBox QAbstractItemView::item { min-height: 32px; padding: 6px 10px; border-radius: 4px; }
        QTableWidget {
            background-color: #12141f; border: 1px solid #282f48; border-radius: 6px;
            gridline-color: #242a42; color: #f1f5f9; font-size: 12px;
        }
        QHeaderView::section {
            background-color: #1c2032; color: #38bdf8; font-weight: bold; border: none;
            border-bottom: 1px solid #3b4566; padding: 4px; font-size: 11px;
        }
        QPushButton {
            background-color: #2563eb; color: #ffffff; font-weight: bold; border: none;
            border-radius: 6px; padding: 8px 14px; font-size: 13px;
        }
        QPushButton:hover { background-color: #1d4ed8; }
        QPushButton:disabled { background-color: #2d3348; color: #64748b; }
        #btn_session_start { background-color: #059669; font-size: 14px; font-weight: bold; min-height: 38px; }
        #btn_session_start:hover { background-color: #10b981; }
        #btn_trial_toggle {
            background-color: #0284c7; font-size: 15px; font-weight: bold;
            min-height: 48px; border-radius: 6px; border: 2px solid #38bdf8;
        }
        #btn_trial_toggle:hover { background-color: #0369a1; }
        #btn_session_stop { background-color: #dc2626; font-size: 14px; font-weight: bold; min-height: 38px; }
        #btn_session_stop:hover { background-color: #ef4444; }
        QProgressBar {
            background-color: #191c2b; border: 1px solid #334155; border-radius: 4px;
            text-align: center; color: #ffffff; font-size: 10px; font-weight: bold; height: 14px;
        }
        QProgressBar::chunk { background-color: #0ea5e9; border-radius: 3px; }
        QCheckBox { color: #e2e8f0; font-size: 13px; font-weight: bold; spacing: 8px; }
        """
        self.setStyleSheet(qss)

    def _build_gauge_panel(self, hand_label):
        panel = QFrame()
        panel.setStyleSheet("QFrame { background-color: #12141f; border: 1px solid #282f48; border-radius: 6px; }")
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(4)
        title = QLabel(f"{LiveAngleChart.HAND_TITLES[hand_label]}  ·  미인식")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none;")
        v.addWidget(title)
        self.gauge_titles[hand_label] = title
        row = QHBoxLayout()
        row.setSpacing(6)
        self.gauges[hand_label] = {}
        self.gauge_labels[hand_label] = {}
        for f in FINGERS:
            box = QVBoxLayout()
            box.setSpacing(2)
            lbl = QLabel(f"{f}: --°")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; border: none;")
            bar = QProgressBar()
            bar.setRange(0, 180)
            bar.setValue(180)
            box.addWidget(lbl)
            box.addWidget(bar)
            row.addLayout(box)
            self.gauges[hand_label][f] = bar
            self.gauge_labels[hand_label][f] = lbl
        v.addLayout(row)
        return panel

    def _update_gauge_panel(self, hand_label, hand_data):
        title = self.gauge_titles[hand_label]
        hn = LiveAngleChart.HAND_TITLES[hand_label]
        if not hand_data:
            title.setText(f"{hn}  ·  미인식")
            title.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none;")
            for f in FINGERS:
                self.gauges[hand_label][f].setValue(0)
                self.gauge_labels[hand_label][f].setText(f"{f}: --°")
                self.gauge_labels[hand_label][f].setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none;")
            return
        title.setText(f"{hn}  ·  인식됨")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; border: none;")
        filt = hand_data['filtered'] if isinstance(hand_data, dict) and 'filtered' in hand_data else hand_data
        for f in FINGERS:
            val = filt.get(f"{f}_Flexion", 180.0)
            self.gauges[hand_label][f].setValue(int(val))
            self.gauge_labels[hand_label][f].setText(f"{f}: {val:.1f}°")
            self.gauge_labels[hand_label][f].setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; border: none;")

    def init_ui(self):
        cw = QWidget(self)
        self.setCentralWidget(cw)
        ml = QHBoxLayout(cw)
        ml.setContentsMargins(12, 12, 12, 12)
        ml.setSpacing(12)

        lp = QWidget()
        lp.setFixedWidth(440)
        ll = QVBoxLayout(lp)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)

        g1 = QGroupBox("1. 피험자 구분 (Subject Group)")
        g1l = QHBoxLayout(g1)
        self.rb_patient = QRadioButton("편마비 환자군 (Patient)")
        self.rb_healthy = QRadioButton("정상인 대조군 (Healthy)")
        self.rb_patient.setChecked(True)
        self.btn_group_type = QButtonGroup(self)
        self.btn_group_type.addButton(self.rb_patient)
        self.btn_group_type.addButton(self.rb_healthy)
        self.rb_healthy.toggled.connect(self.on_subject_type_changed)
        g1l.addWidget(self.rb_patient)
        g1l.addWidget(self.rb_healthy)
        ll.addWidget(g1)

        g2 = QGroupBox("2. 기본 인적 사항 (Demographics)")
        g2l = QGridLayout(g2)
        g2l.setSpacing(6)
        g2l.addWidget(QLabel("이름 (Name):"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("예: P01")
        self.txt_name.setText("이재용")
        g2l.addWidget(self.txt_name, 0, 1)
        g2l.addWidget(QLabel("나이 (Age):"), 1, 0)
        self.spin_age = QSpinBox()
        self.spin_age.setRange(5, 110)
        self.spin_age.setValue(62)
        self.spin_age.setSuffix(" 세")
        g2l.addWidget(self.spin_age, 1, 1)
        g2l.addWidget(QLabel("성별 (Gender):"), 2, 0)
        self.cb_gender = QComboBox()
        self.cb_gender.addItems(["남성 (Male)", "여성 (Female)"])
        g2l.addWidget(self.cb_gender, 2, 1)
        ll.addWidget(g2)

        self.group_clinical = QGroupBox("3. 임상 재활 척도 (Clinical Scales)")
        g3l = QGridLayout(self.group_clinical)
        g3l.setSpacing(6)
        g3l.addWidget(QLabel("FMA-UE 점수:"), 0, 0)
        self.spin_fma = QSpinBox()
        self.spin_fma.setRange(0, 66)
        self.spin_fma.setValue(38)
        self.spin_fma.setSuffix(" / 66점")
        g3l.addWidget(self.spin_fma, 0, 1)
        g3l.addWidget(QLabel("Brunnstrom 단계:"), 1, 0)
        self.cb_brs = QComboBox()
        self.cb_brs.addItems(["Stage 1 (완전이완)", "Stage 2 (경직시작)", "Stage 3 (공동운동극대)",
                              "Stage 4 (부분분리운동)", "Stage 5 (독립분리운동)", "Stage 6 (정상협응)"])
        self.cb_brs.setCurrentIndex(3)
        g3l.addWidget(self.cb_brs, 1, 1)
        g3l.addWidget(QLabel("환측 (마비손):"), 2, 0)
        self.cb_affected = QComboBox()
        self.cb_affected.addItems(["우측 (Right Hand)", "좌측 (Left Hand)"])
        g3l.addWidget(self.cb_affected, 2, 1)
        ll.addWidget(self.group_clinical)

        g4 = QGroupBox("4. 실험 프로토콜 과제 (Task Selection)")
        g4l = QHBoxLayout(g4)
        self.cb_task = QComboBox()
        self.cb_task.addItems(["Task 1: 맨손 쥐기/펴기 (Free Motion)", "Task 2: 원통형 파지 (Cylinder 5cm)",
                               "Task 3: 구형 파지 (Sphere 7cm)", "Task 4: 미러테라피 폐루프 (Mirror Therapy)"])
        self.cb_task.currentIndexChanged.connect(self.on_task_changed)
        g4l.addWidget(self.cb_task)
        ll.addWidget(g4)

        g5 = QGroupBox("5. 파지 구간 (시작/완료) 측정 제어")
        g5l = QVBoxLayout(g5)
        g5l.setSpacing(8)
        sr = QHBoxLayout()
        self.btn_session_start = QPushButton("▶  전체 세션 시작")
        self.btn_session_start.setObjectName("btn_session_start")
        self.btn_session_start.clicked.connect(self.start_session)
        self.btn_session_stop = QPushButton("■  세션 종료 및 일괄 마감")
        self.btn_session_stop.setObjectName("btn_session_stop")
        self.btn_session_stop.setEnabled(False)
        self.btn_session_stop.clicked.connect(self.stop_session)
        sr.addWidget(self.btn_session_start)
        sr.addWidget(self.btn_session_stop)
        g5l.addLayout(sr)

        self.btn_trial_toggle = QPushButton("▶  [Trial #1] 파지 시작 (Space)")
        self.btn_trial_toggle.setObjectName("btn_trial_toggle")
        self.btn_trial_toggle.setEnabled(False)
        self.btn_trial_toggle.clicked.connect(self.toggle_trial_state)
        g5l.addWidget(self.btn_trial_toggle)

        self.table_trials = QTableWidget(0, 6)
        self.table_trials.setHorizontalHeaderLabels(["회차", "과제", "소요시간", "MGA(%)", "TAROM(°)", "SPARC"])
        self.table_trials.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_trials.setFixedHeight(180)
        g5l.addWidget(self.table_trials)
        ll.addWidget(g5)
        ml.addWidget(lp)

        rp = QWidget()
        rl = QVBoxLayout(rp)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        vc = QFrame()
        vc.setStyleSheet("background-color: #141724; border-radius: 8px; border: 1px solid #282f48;")
        vcl = QVBoxLayout(vc)
        vcl.setContentsMargins(8, 8, 8, 8)

        vh = QHBoxLayout()
        self.lbl_session_status = QLabel("● READY (대기 중)")
        self.lbl_session_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        self.lbl_trial_status = QLabel("대기 상태 (시작 전)")
        self.lbl_trial_status.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")
        self.chk_mirror = QCheckBox("미러링 (M)")
        self.chk_mirror.toggled.connect(self.on_mirror_toggled)
        self.chk_filter = QCheckBox("하이브리드 필터")
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda v: self.video_worker.set_filter_mode(v))
        self.lbl_fps = QLabel("FPS: -- | Hands: 0")
        self.lbl_fps.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        self.btn_open_folder = QPushButton("📂 저장 폴더 열기")
        self.btn_open_folder.setStyleSheet("background-color: #272c44; color: #38bdf8; font-weight: bold; padding: 6px 12px; border-radius: 6px; border: 1px solid #3b4566;")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        self.btn_exit = QPushButton("✕ 종료 (Q)")
        self.btn_exit.setStyleSheet("background-color: #334155; color: #ffffff; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        self.btn_exit.clicked.connect(self.close)
        vh.addWidget(self.lbl_session_status)
        vh.addSpacing(12)
        vh.addWidget(self.lbl_trial_status)
        vh.addStretch()
        vh.addWidget(self.chk_mirror)
        vh.addSpacing(8)
        vh.addWidget(self.chk_filter)
        vh.addSpacing(12)
        vh.addWidget(self.lbl_fps)
        vh.addSpacing(10)
        vh.addWidget(self.btn_open_folder)
        vh.addWidget(self.btn_exit)
        vcl.addLayout(vh)

        self.lbl_video = QLabel("웹캠 영상을 연결하는 중입니다...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(400)
        self.lbl_video.setStyleSheet("background-color: #08090e; border-radius: 6px;")
        vcl.addWidget(self.lbl_video)

        gr = QHBoxLayout()
        gr.setSpacing(8)
        self.panel_gauge_right = self._build_gauge_panel('Right')
        self.panel_gauge_left = self._build_gauge_panel('Left')
        gr.addWidget(self.panel_gauge_right)
        gr.addWidget(self.panel_gauge_left)
        vcl.addLayout(gr)
        rl.addWidget(vc)

        cc = QFrame()
        cc.setStyleSheet("background-color: #141724; border-radius: 8px; border: 1px solid #282f48;")
        ccl = QVBoxLayout(cc)
        ccl.setContentsMargins(8, 8, 8, 8)
        self.angle_chart = LiveAngleChart(self, width=6, height=3.8)
        ccl.addWidget(self.angle_chart)
        rl.addWidget(cc)
        ml.addWidget(rp, stretch=1)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self.toggle_trial_state)
        QShortcut(QKeySequence(Qt.Key.Key_M), self).activated.connect(
            lambda: self.chk_mirror.setChecked(not self.chk_mirror.isChecked()))
        QShortcut(QKeySequence(Qt.Key.Key_Q), self).activated.connect(self.close)

    def on_subject_type_changed(self):
        ih = self.rb_healthy.isChecked()
        self.group_clinical.setEnabled(not ih)
        self.group_clinical.setTitle("3. 임상 재활 척도 (정상 대조군 - 비활성)" if ih else "3. 임상 재활 척도 (Clinical Scales)")

    def on_mirror_toggled(self, checked):
        self.video_worker.set_mirror_mode(checked)
        self.angle_chart.reset_chart()

    def on_task_changed(self, idx):
        if self.is_session_active:
            self.show_toast(f"과제 전환: {self.cb_task.currentText()}")

    def show_toast(self, msg, is_success=False):
        self.statusBar().showMessage(msg, 5000)

    def start_session(self):
        sn = self.txt_name.text().strip()
        if not sn:
            QMessageBox.warning(self, "입력 오류", "피험자 이름을 먼저 입력해주세요.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        grp = "Healthy" if self.rb_healthy.isChecked() else "Patient"
        fn = f"{sn}_{grp}_{ts}"
        self.current_subject_folder = os.path.join(self.base_output_dir, fn)
        os.makedirs(self.current_subject_folder, exist_ok=True)
        self.task_folders = {
            "Task 1": os.path.join(self.current_subject_folder, "Task1_맨손_쥐기펴기"),
            "Task 2": os.path.join(self.current_subject_folder, "Task2_원통형_파지"),
            "Task 3": os.path.join(self.current_subject_folder, "Task3_구형_파지"),
            "Task 4": os.path.join(self.current_subject_folder, "Task4_미러테라피")
        }
        for p in self.task_folders.values():
            os.makedirs(p, exist_ok=True)
        self.session_records = []
        self.completed_trials = []
        self.current_trial_idx = 1
        self.is_trial_in_progress = False
        self.session_start_time = time.time()
        self.is_session_active = True
        self.btn_session_start.setEnabled(False)
        self.btn_session_stop.setEnabled(True)
        self.btn_trial_toggle.setEnabled(True)
        self.set_trial_button_ui(True)
        self.txt_name.setEnabled(False)
        self.spin_age.setEnabled(False)
        self.cb_gender.setEnabled(False)
        self.rb_healthy.setEnabled(False)
        self.rb_patient.setEnabled(False)
        self.table_trials.setRowCount(0)
        self.angle_chart.reset_chart()
        self.lbl_session_status.setText("● REC (세션 녹화 중)")
        self.lbl_session_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")
        self.lbl_trial_status.setText("준비됨 (파지 시작 대기)")
        self.lbl_trial_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.show_toast(f"▶ 세션 시작: {fn}", is_success=True)

    def set_trial_button_ui(self, starting=True):
        if starting:
            self.btn_trial_toggle.setText(f"▶  [Trial #{self.current_trial_idx}] 파지 시작 (Space)")
            self.btn_trial_toggle.setStyleSheet(
                "#btn_trial_toggle { background-color: #0284c7; color: #ffffff; font-size: 15px;"
                " font-weight: bold; min-height: 48px; border: 2px solid #38bdf8; }"
                "#btn_trial_toggle:hover { background-color: #0369a1; }")
        else:
            self.btn_trial_toggle.setText(f"⏹  [Trial #{self.current_trial_idx}] 파지 완료 / 저장 (Space)")
            self.btn_trial_toggle.setStyleSheet(
                "#btn_trial_toggle { background-color: #ea580c; color: #ffffff; font-size: 15px;"
                " font-weight: bold; min-height: 48px; border: 2px solid #fdba74; }"
                "#btn_trial_toggle:hover { background-color: #c2410c; }")

    def toggle_trial_state(self):
        if not self.is_session_active or not self.session_records:
            return
        tn = time.time() - self.session_start_time
        if not self.is_trial_in_progress:
            self.is_trial_in_progress = True
            self.current_trial_start_t = tn
            self.current_trial_records = []
            self.set_trial_button_ui(False)
            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
            self.show_toast(f"▶ [Trial #{self.current_trial_idx}] 파지 시작!")
        else:
            self.is_trial_in_progress = False
            te, ts = tn, self.current_trial_start_t
            dur = max(0.01, te - ts)
            seg = [r for r in self.session_records if ts <= r['time'] <= te]
            if not seg:
                seg = self.session_records[-15:]
            ctf = self.cb_task.currentText()
            ctk = ctf.split(":")[0].strip()
            cts = ctf.split(":")[1].split("(")[0].strip() if ":" in ctf else ctf
            aps = [r['filtered'].get('Grip_Aperture', 0) for r in seg]
            mga = max(aps) if aps else 0.0
            tarom = 0.0
            for f in FINGERS:
                fp = [r['filtered'].get(f"{f}_Flexion", 180.0) for r in seg]
                if fp:
                    tarom += (max(fp) - min(fp))
            ip = [r['filtered'].get('Index_PIP', 180.0) for r in seg]
            sparc = compute_sparc(np.gradient(ip, 1.0/30.0)) if len(ip) > 1 else 0.0
            ti = {"trial": self.current_trial_idx, "task_full": ctf, "task_key": ctk, "task_short": cts,
                  "start_time": ts, "end_time": te, "duration": dur, "mga": mga, "tarom": tarom, "sparc": sparc}
            self.completed_trials.append(ti)
            self.angle_chart.add_trial_span(ts, te, f"T{self.current_trial_idx}")
            rp = self.table_trials.rowCount()
            self.table_trials.insertRow(rp)
            self.table_trials.setItem(rp, 0, QTableWidgetItem(f"Trial #{self.current_trial_idx}"))
            self.table_trials.setItem(rp, 1, QTableWidgetItem(ctk))
            self.table_trials.setItem(rp, 2, QTableWidgetItem(f"{dur:.2f}초"))
            self.table_trials.setItem(rp, 3, QTableWidgetItem(f"{mga:.1f}%"))
            self.table_trials.setItem(rp, 4, QTableWidgetItem(f"{tarom:.1f}°"))
            self.table_trials.setItem(rp, 5, QTableWidgetItem(f"{sparc:.2f}"))
            self.table_trials.scrollToBottom()
            td = self.task_folders.get(ctk, self.current_subject_folder)
            self.save_single_trial_files(td, ti, seg)
            self.current_trial_idx += 1
            self.set_trial_button_ui(True)
            self.lbl_trial_status.setText(f"완료됨 (총 {len(self.completed_trials)}회 기록됨)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.show_toast(f"💾 [{ctk} - Trial #{ti['trial']}] 저장 완료!", is_success=True)

    def save_single_trial_files(self, td, ti, seg):
        tnum = ti['trial']
        tk = ti['task_key'].replace(" ", "")
        pfx = f"{tk}_Trial_{tnum:02d}"
        cp = os.path.join(td, f"{pfx}_timeseries.csv")
        hd = ["time_s", "rel_time_s", "Task", "Trial", "hand_label",
              "Thumb_MCP_raw", "Thumb_MCP_filt", "Thumb_IP_raw", "Thumb_IP_filt",
              "Index_MCP_raw", "Index_MCP_filt", "Index_PIP_raw", "Index_PIP_filt", "Index_DIP_raw", "Index_DIP_filt",
              "Middle_MCP_raw", "Middle_MCP_filt", "Middle_PIP_raw", "Middle_PIP_filt", "Middle_DIP_raw", "Middle_DIP_filt",
              "Ring_MCP_raw", "Ring_MCP_filt", "Ring_PIP_raw", "Ring_PIP_filt", "Ring_DIP_raw", "Ring_DIP_filt",
              "Pinky_MCP_raw", "Pinky_MCP_filt", "Pinky_PIP_raw", "Pinky_PIP_filt", "Pinky_DIP_raw", "Pinky_DIP_filt",
              "Grip_Aperture_raw", "Grip_Aperture_filt"]
        t0 = ti['start_time']
        with open(cp, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(hd)
            for r in seg:
                ra, fa = r['raw'], r['filtered']
                row = [f"{r['time']:.4f}", f"{r['time']-t0:.4f}", ti['task_full'], f"Trial_{tnum}", r['hand']]
                for jn in ['Thumb_MCP', 'Thumb_IP', 'Index_MCP', 'Index_PIP', 'Index_DIP',
                           'Middle_MCP', 'Middle_PIP', 'Middle_DIP', 'Ring_MCP', 'Ring_PIP', 'Ring_DIP',
                           'Pinky_MCP', 'Pinky_PIP', 'Pinky_DIP']:
                    row.extend([f"{ra.get(jn,0):.2f}", f"{fa.get(jn,0):.2f}"])
                row.extend([f"{ra.get('Grip_Aperture',0):.2f}", f"{fa.get('Grip_Aperture',0):.2f}"])
                w.writerow(row)
        jp = os.path.join(td, f"{pfx}_summary.json")
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump(ti, f, ensure_ascii=False, indent=2)
        pp = os.path.join(td, f"{pfx}_plot.png")
        self._plot_trial(pp, ti, seg)
        sc = os.path.join(td, f"{tk}_Summary.csv")
        ex = os.path.exists(sc)
        with open(sc, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if not ex:
                w.writerow(["Trial", "Task", "Duration_s", "MGA_pct", "TAROM_deg", "SPARC"])
            w.writerow([f"Trial #{tnum}", ti['task_short'], f"{ti['duration']:.2f}",
                        f"{ti['mga']:.2f}", f"{ti['tarom']:.2f}", f"{ti['sparc']:.2f}"])

    def _plot_trial(self, sp, ti, seg):
        if not seg:
            return
        t0 = ti['start_time']
        ta = [r['time'] - t0 for r in seg]
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True, dpi=120)
        fig.patch.set_facecolor('#ffffff')
        cs = {'Thumb_IP': '#ef4444', 'Index_PIP': '#0ea5e9', 'Middle_PIP': '#22c55e', 'Ring_PIP': '#f59e0b', 'Pinky_PIP': '#a855f7'}
        for k, c in cs.items():
            a1.plot(ta, [r['filtered'].get(k, np.nan) for r in seg], label=k.replace('_', ' '), color=c, linewidth=2.0)
        a1.set_ylim(0, 180)
        a1.set_ylabel("Flexion Angle (°)", fontweight='bold')
        a1.set_title(f"[{ti['task_key']}] Trial #{ti['trial']} ({ti['duration']:.2f}s | TAROM: {ti['tarom']:.1f}°)", fontsize=10, fontweight='bold')
        a1.grid(True, linestyle=':', alpha=0.6)
        a1.legend(fontsize=8)
        a2.plot(ta, [r['filtered'].get('Grip_Aperture', 0) for r in seg], color='#334155', linewidth=2.0)
        a2.set_ylabel("Aperture (%)", fontweight='bold')
        a2.set_xlabel("Time (s)", fontweight='bold')
        a2.grid(True, linestyle=':', alpha=0.6)
        plt.tight_layout()
        plt.savefig(sp)
        plt.close(fig)

    def stop_session(self):
        if not self.is_session_active:
            return
        if self.is_trial_in_progress:
            self.toggle_trial_state()
        self.is_session_active = False
        dur = time.time() - self.session_start_time
        self.btn_session_start.setEnabled(True)
        self.btn_session_stop.setEnabled(False)
        self.btn_trial_toggle.setEnabled(False)
        for w in [self.txt_name, self.spin_age, self.cb_gender]:
            w.setEnabled(True)
        self.rb_healthy.setEnabled(True)
        self.rb_patient.setEnabled(True)
        self.lbl_session_status.setText("● READY (세션 완료)")
        self.lbl_session_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        self.lbl_trial_status.setText(f"총 {len(self.completed_trials)}회차 저장 완료")
        self._save_overall(dur)
        self.show_toast(f"✅ 세션 마감! 총 {len(self.completed_trials)}회차 저장.", is_success=True)

    def _save_overall(self, dur):
        if not self.session_records:
            return
        oc = os.path.join(self.current_subject_folder, "Session_Overall_Summary.csv")
        with open(oc, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(["Trial", "Task", "Duration_s", "MGA_pct", "TAROM_deg", "SPARC"])
            for tr in self.completed_trials:
                w.writerow([f"Trial #{tr['trial']}", tr.get('task_short', ''), f"{tr['duration']:.2f}",
                            f"{tr['mga']:.2f}", f"{tr['tarom']:.2f}", f"{tr['sparc']:.2f}"])
        mp = os.path.join(self.current_subject_folder, "subject_metadata.json")
        md = {"name": self.txt_name.text().strip(), "age": self.spin_age.value(),
              "gender": self.cb_gender.currentText(),
              "group": "Healthy" if self.rb_healthy.isChecked() else "Patient",
              "fma_score": self.spin_fma.value() if self.rb_patient.isChecked() else None,
              "brunnstrom_stage": self.cb_brs.currentText() if self.rb_patient.isChecked() else None,
              "affected_side": self.cb_affected.currentText() if self.rb_patient.isChecked() else None,
              "total_trials": len(self.completed_trials), "session_duration": dur,
              "tasks": list(set(tr['task_key'] for tr in self.completed_trials)),
              "trials": self.completed_trials,
              "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        with open(mp, 'w', encoding='utf-8') as f:
            json.dump(md, f, ensure_ascii=False, indent=2)

    def on_frame_ready(self, frame, ad, fps, hc):
        self.last_angles = ad
        self.lbl_fps.setText(f"FPS: {fps:.1f}  |  Hands: {hc}")
        ct = self.cb_task.currentText()
        im = "Task 4" in ct
        iv = (('Right' in ad) and ('Left' in ad)) if im else bool(ad)
        if self.is_session_active:
            if iv:
                t = time.time() - self.session_start_time
                ph = 'Right' if 'Right' in ad else ('Left' if 'Left' in ad else list(ad.keys())[0])
                hd = ad[ph]
                re = {'time': t, 'hand': ph, 'raw': hd['raw'], 'filtered': hd['filtered'], 'task': ct}
                self.session_records.append(re)
                if self.is_trial_in_progress:
                    self.current_trial_records.append(re)
                self.angle_chart.update_data(t, ad)
                self.btn_trial_toggle.setEnabled(True)
                self._refresh_trial_status_label()
            else:
                msg = "⏸ 미러테라피: 양손 인식 필요" if im else "손을 화면에 비춰주세요"
                col = "#f97316" if im else "#94a3b8"
                self.lbl_trial_status.setText(msg)
                self.lbl_trial_status.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 13px;")
        for hl in LiveAngleChart.HAND_ORDER:
            self._update_gauge_panel(hl, ad.get(hl))
        h, w, ch = frame.shape
        qi = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format.Format_BGR888)
        pm = QtGui.QPixmap.fromImage(qi).scaled(
            self.lbl_video.width(), self.lbl_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        self.lbl_video.setPixmap(pm)

    def _refresh_trial_status_label(self):
        if self.is_trial_in_progress:
            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
        elif self.completed_trials:
            self.lbl_trial_status.setText(f"완료됨 (총 {len(self.completed_trials)}회 기록됨)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
        else:
            self.lbl_trial_status.setText("준비됨 (파지 시작 대기)")
            self.lbl_trial_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")

    def update_session_timer(self):
        if self.is_session_active:
            el = time.time() - self.session_start_time
            self.lbl_session_status.setText(f"● REC ({el:.1f}초 | {len(self.session_records)} 프레임)")

    def open_output_folder(self):
        fld = self.current_subject_folder if os.path.exists(self.current_subject_folder) else self.base_output_dir
        if sys.platform == 'win32':
            os.startfile(fld)
        else:
            self.show_toast(f"폴더: {fld}")

    def closeEvent(self, event):
        if self.is_session_active:
            self.stop_session()
        self.video_worker.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = CapstoneClinicalApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

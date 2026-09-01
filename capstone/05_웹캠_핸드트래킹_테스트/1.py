import os
# Windows 고해상도(High-DPI) 디스플레이 선명한 벡터 폰트 렌더링 설정
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
    QCheckBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView
)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 맑은 고딕 한글 폰트 글로벌 고정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 게이지/차트에서 공통으로 쓰는 손가락 순서
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


# ================================================================
# 1. 4단계 하이브리드 생체역학 필터 (One-Euro + Velocity Guard + Missing Hold + Global-Motion Hold)
# ================================================================
class OneEuroFilter:
    def __init__(self, t0=0.0, x0=180.0, dx0=0.0, min_cutoff=0.7, beta=0.015, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff) # 정지 상태 컷오프 (지터 완전 억제)
        self.beta = float(beta)             # 속도 가중치 (빠른 움직임 래그 0 추종)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)
        self.t_prev = float(t0)

    def smoothing_factor(self, t_e, cutoff):
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    def exponential_smoothing(self, a, x, x_prev):
        return a * x + (1 - a) * x_prev

    def filter(self, t, x):
        t_e = t - self.t_prev
        if t_e <= 0.0:
            return self.x_prev

        a_d = self.smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = self.exponential_smoothing(a_d, dx, self.dx_prev)

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self.smoothing_factor(t_e, cutoff)
        x_hat = self.exponential_smoothing(a, x, self.x_prev)

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


class HybridKinematicFilter:
    def __init__(self, init_val=180.0):
        self.val = float(init_val)
        self.last_valid_val = float(init_val)
        self.missing_count = 0
        self.max_missing_hold = 12 # 최대 0.4초간 가려짐 홀딩
        self.euro_filter = OneEuroFilter(t0=0.0, x0=init_val, min_cutoff=0.7, beta=0.015)
        self.max_deg_per_frame = 30.0 # 프레임당 최대 30도 회전 속도 제한

    def update(self, t, raw_val, hold_motion=False):
        # 팔 전체가 이동/회전하는 "글로벌 모션" 구간에서는 값 갱신을 보류하고 직전 값을 유지
        # (손가락은 그대로인데 팔만 움직여서 생기는 원근/추정 오차를 걸러냄)
        if hold_motion:
            self.euro_filter.t_prev = t  # 다음 정상 프레임의 dt가 왜곡되지 않도록 시간만 갱신
            return self.last_valid_val

        if raw_val is None or (isinstance(raw_val, float) and (np.isnan(raw_val) or raw_val <= 0.0)):
            self.missing_count += 1
            if self.missing_count <= self.max_missing_hold:
                return self.last_valid_val
            else:
                self.last_valid_val = 0.95 * self.last_valid_val + 0.05 * 160.0
                return self.last_valid_val

        self.missing_count = 0

        # 물리적 스파이크 노이즈 제거
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
# 2. 3D 관절 각도 및 운동학 계산 유틸
# ================================================================
def calculate_angle_3d(a, b, c):
    pa = np.array([a.x, a.y, a.z])
    pb = np.array([b.x, b.y, b.z])
    pc = np.array([c.x, c.y, c.z])

    ba = pa - pb
    bc = pc - pb

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-7 or norm_bc < 1e-7:
        return 180.0

    cos_val = np.dot(ba, bc) / (norm_ba * norm_bc)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_val)))

def calculate_aperture(lm):
    p_thumb = np.array([lm[4].x, lm[4].y, lm[4].z])
    p_index = np.array([lm[8].x, lm[8].y, lm[8].z])
    return float(np.linalg.norm(p_thumb - p_index) * 100.0)

def compute_all_finger_angles(landmarks):
    angles = {}
    # Thumb
    angles['Thumb_MCP'] = calculate_angle_3d(landmarks[1], landmarks[2], landmarks[3])
    angles['Thumb_IP']  = calculate_angle_3d(landmarks[2], landmarks[3], landmarks[4])
    # Index
    angles['Index_MCP'] = calculate_angle_3d(landmarks[0], landmarks[5], landmarks[6])
    angles['Index_PIP'] = calculate_angle_3d(landmarks[5], landmarks[6], landmarks[7])
    angles['Index_DIP'] = calculate_angle_3d(landmarks[6], landmarks[7], landmarks[8])
    # Middle
    angles['Middle_MCP'] = calculate_angle_3d(landmarks[0], landmarks[9], landmarks[10])
    angles['Middle_PIP'] = calculate_angle_3d(landmarks[9], landmarks[10], landmarks[11])
    angles['Middle_DIP'] = calculate_angle_3d(landmarks[10], landmarks[11], landmarks[12])
    # Ring
    angles['Ring_MCP'] = calculate_angle_3d(landmarks[0], landmarks[13], landmarks[14])
    angles['Ring_PIP'] = calculate_angle_3d(landmarks[13], landmarks[14], landmarks[15])
    angles['Ring_DIP'] = calculate_angle_3d(landmarks[14], landmarks[15], landmarks[16])
    # Pinky
    angles['Pinky_MCP'] = calculate_angle_3d(landmarks[0], landmarks[17], landmarks[18])
    angles['Pinky_PIP'] = calculate_angle_3d(landmarks[17], landmarks[18], landmarks[19])
    angles['Pinky_DIP'] = calculate_angle_3d(landmarks[18], landmarks[19], landmarks[20])

    # 주요 굴곡각
    angles['Thumb_Flexion']  = angles['Thumb_IP']
    angles['Index_Flexion']  = angles['Index_PIP']
    angles['Middle_Flexion'] = angles['Middle_PIP']
    angles['Ring_Flexion']   = angles['Ring_PIP']
    angles['Pinky_Flexion']  = angles['Pinky_PIP']
    angles['Grip_Aperture']  = calculate_aperture(landmarks)

    return angles


# ================================================================
# 3. 비디오 캡처 및 MediaPipe 백그라운드 추론 스레드
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

        # 팔 전체가 이동/회전하는 "글로벌 모션" 감지용 상태
        self.prev_palm_state = {}
        self.global_motion_translation_thresh = 0.020   # 프레임 간 손목 이동 거리 임계값(미터). 오탐 많으면 값을 올리세요.
        self.global_motion_rotation_thresh_deg = 10.0    # 프레임 간 손바닥 방향 회전각 임계값(도). 오탐 많으면 값을 올리세요.

    def set_mirror_mode(self, enabled):
        # 미러링을 켜고 끄면 화면상 Right/Left 라벨이 서로 뒤바뀌는데, 기존 필터가 남아있으면
        # "다른 손"의 예전 값에 클램프(30도/프레임 제한)되어 잠깐 안 바뀌는 것처럼 보임 -> 초기화
        self.mirror_mode = enabled
        self.filters = {}
        self.prev_palm_state = {}

    def set_filter_mode(self, enabled):
        self.use_filter = enabled

    def _compute_palm_state(self, world_lm):
        """손목·검지MCP·새끼MCP로 손바닥의 위치/방향(법선벡터)을 계산.
        이 세 점은 손가락이 접히든 펴지든 항상 같은 강체(손바닥) 위에 있음."""
        wrist = np.array([world_lm[0].x, world_lm[0].y, world_lm[0].z])
        idx_mcp = np.array([world_lm[5].x, world_lm[5].y, world_lm[5].z])
        pinky_mcp = np.array([world_lm[17].x, world_lm[17].y, world_lm[17].z])
        v1 = idx_mcp - wrist
        v2 = pinky_mcp - wrist
        normal = np.cross(v1, v2)
        n_len = np.linalg.norm(normal)
        normal = normal / n_len if n_len > 1e-9 else np.array([0.0, 0.0, 1.0])
        return wrist, normal

    def _detect_global_motion(self, hand_label, world_lm):
        """손가락 관절과 무관하게 팔 전체가 이동/회전하는 구간을 감지.
        True를 반환하면 이번 프레임은 각도 갱신을 보류(직전 값 유지)해야 함."""
        wrist, normal = self._compute_palm_state(world_lm)
        hold = False
        if hand_label in self.prev_palm_state:
            prev_wrist, prev_normal = self.prev_palm_state[hand_label]
            translation = float(np.linalg.norm(wrist - prev_wrist))
            cos_a = float(np.clip(np.dot(normal, prev_normal), -1.0, 1.0))
            rotation_deg = math.degrees(math.acos(cos_a))
            if translation > self.global_motion_translation_thresh or rotation_deg > self.global_motion_rotation_thresh_deg:
                hold = True
        self.prev_palm_state[hand_label] = (wrist, normal)
        return hold

    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print(f"[에러] 카메라 {self.camera_index}번을 열 수 없습니다.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles

        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.55
        )

        prev_t = time.time()

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            curr_t = time.time()
            fps = 1.0 / (curr_t - prev_t) if (curr_t - prev_t) > 0 else 30.0
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
                world_landmarks_list = results.multi_hand_world_landmarks  # 카메라 거리/위치와 무관한 실측 3D(미터) 좌표

                for hand_idx, hand_lms in enumerate(results.multi_hand_landmarks):
                    hand_label = "Hand"
                    if results.multi_handedness and hand_idx < len(results.multi_handedness):
                        hand_label = results.multi_handedness[hand_idx].classification[0].label
                        if self.mirror_mode:
                            hand_label = "Right" if hand_label == "Left" else "Left"

                    mp_drawing.draw_landmarks(
                        frame,
                        hand_lms,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style()
                    )

                    # 각도/파지폭 계산에는 반드시 world_landmarks(실측 3D, 미터 단위, 카메라와의 거리·화면상
                    # 위치에 불변)를 사용. hand_lms(=multi_hand_landmarks)는 화면에 투영된 정규화 좌표라서
                    # 손이 카메라에 가까워지거나 멀어지거나 화면 상하로 움직이기만 해도 원근 왜곡으로 값이 흔들림.
                    if world_landmarks_list and hand_idx < len(world_landmarks_list):
                        calc_landmarks = world_landmarks_list[hand_idx].landmark
                    else:
                        calc_landmarks = hand_lms.landmark  # world landmark가 없을 때만 fallback

                    # 손가락은 그대로인 채 팔만 이동/회전하는 구간인지 판정 (True면 이번 프레임 값 갱신 보류)
                    hold_motion = self._detect_global_motion(hand_label, calc_landmarks)

                    raw_angles = compute_all_finger_angles(calc_landmarks)
                    filtered_angles = {}
                    for k, v in raw_angles.items():
                        fk_name = f"{hand_label}_{k}"
                        if fk_name not in self.filters:
                            self.filters[fk_name] = HybridKinematicFilter(init_val=v)

                        if self.use_filter:
                            filtered_angles[k] = self.filters[fk_name].update(t_sec, v, hold_motion=hold_motion)
                        else:
                            filtered_angles[k] = v

                    latest_angles[hand_label] = {
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
# 4. 실시간 Matplotlib 5손가락 각도 그래프 캔버스
# ================================================================
class LiveAngleChart(FigureCanvas):
    """오른손/왼손 5손가락 굴곡각을 위아래 2단 서브플롯으로 동시에 표시"""

    HAND_ORDER = ('Right', 'Left')
    HAND_TITLES = {'Right': '왼손 (Left)', 'Left': '오른손 (Right)'}

    def __init__(self, parent=None, width=6, height=4.2, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#131622')
        super().__init__(self.fig)
        self.setParent(parent)

        self.finger_colors = {
            'Thumb': '#ef4444',
            'Index': '#0ea5e9',
            'Middle': '#22c55e',
            'Ring': '#f59e0b',
            'Pinky': '#a855f7'
        }

        self.axes = {}
        self.lines = {}
        self.time_bufs = {}
        self.angle_bufs = {}
        self.trial_spans = {}

        ax_top = self.fig.add_subplot(211)
        ax_bottom = self.fig.add_subplot(212, sharex=ax_top)
        hand_axes = {'Right': ax_top, 'Left': ax_bottom}

        for hand_label in self.HAND_ORDER:
            ax = hand_axes[hand_label]
            ax.set_facecolor('#191c2b')
            ax.set_ylim(0, 180)
            ax.set_yticks([0, 45, 90, 135, 180])
            ax.set_xlim(0, 10)
            ax.set_ylabel(f"{self.HAND_TITLES[hand_label]}\n굴곡각(°)", color="#cbd5e1", fontsize=8, fontweight='bold')
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')
            ax.grid(True, linestyle='--', color='#272b3f', linewidth=0.8)

            self.lines[hand_label] = {}
            for f, col in self.finger_colors.items():
                line, = ax.plot([], [], label=f, color=col, linewidth=2.0, alpha=0.95)
                self.lines[hand_label][f] = line

            ax.legend(loc='upper right', fontsize=7, ncol=5, facecolor='#191c2b',
                      edgecolor='#334155', labelcolor='#f1f5f9')

            self.axes[hand_label] = ax
            self.time_bufs[hand_label] = deque(maxlen=300)
            self.angle_bufs[hand_label] = {f: deque(maxlen=300) for f in self.finger_colors}
            self.trial_spans[hand_label] = []

        ax_top.tick_params(labelbottom=False)
        ax_bottom.set_xlabel("경과 시간 (초)", color="#cbd5e1", fontsize=9, fontweight='bold')

        self.fig.tight_layout(pad=1.2)
        self.fig.subplots_adjust(hspace=0.12)

        # 화면 렌더링(draw_idle) 빈도 제한용. 데이터 자체는 매 프레임 버퍼에 쌓이지만,
        # 실제 matplotlib 재그리기는 이 간격(초)마다 한 번만 수행해서 GUI 스레드 부하를 줄임.
        self._render_interval = 0.1  # 약 10Hz. 그래도 느리면 0.15~0.2로 올리세요.
        self._last_render_t = None

    def update_data(self, t, angles_dict):
        if not angles_dict:
            return

        updated = False
        for hand_label in self.HAND_ORDER:
            if hand_label not in angles_dict:
                continue

            hand_data = angles_dict[hand_label]
            if isinstance(hand_data, dict) and 'filtered' in hand_data:
                hand_data = hand_data['filtered']

            self.time_bufs[hand_label].append(t)
            self.angle_bufs[hand_label]['Thumb'].append(hand_data.get('Thumb_Flexion', 180.0))
            self.angle_bufs[hand_label]['Index'].append(hand_data.get('Index_Flexion', 180.0))
            self.angle_bufs[hand_label]['Middle'].append(hand_data.get('Middle_Flexion', 180.0))
            self.angle_bufs[hand_label]['Ring'].append(hand_data.get('Ring_Flexion', 180.0))
            self.angle_bufs[hand_label]['Pinky'].append(hand_data.get('Pinky_Flexion', 180.0))
            updated = True

        if not updated:
            return

        # 실제 화면 재그리기는 일정 간격이 지났을 때만 수행 (성능 최적화)
        if self._last_render_t is not None and (t - self._last_render_t) < self._render_interval:
            return
        self._last_render_t = t

        # 두 서브플롯의 x축(시간) 범위는 더 최근에 갱신된 손 기준으로 통일
        latest_times = [self.time_bufs[h][-1] for h in self.HAND_ORDER if len(self.time_bufs[h]) > 0]
        if not latest_times:
            return
        t_now = max(latest_times)
        x_min = max(0.0, t_now - 10.0)

        for hand_label in self.HAND_ORDER:
            if len(self.time_bufs[hand_label]) > 1:
                t_arr = np.array(self.time_bufs[hand_label])
                for f in self.finger_colors:
                    self.lines[hand_label][f].set_data(t_arr, np.array(self.angle_bufs[hand_label][f]))
            self.axes[hand_label].set_xlim(x_min, max(10.0, t_now))

        self.draw_idle()

    def add_trial_span(self, t_start, t_end, trial_label):
        """파지 시작~완료 구간을 두 서브플롯 모두에 시각적 하이라이트(음영)로 표시"""
        for hand_label in self.HAND_ORDER:
            span = self.axes[hand_label].axvspan(t_start, t_end, color='#0284c7', alpha=0.25)
            self.trial_spans[hand_label].append(span)
        self.draw_idle()

    def reset_chart(self):
        for hand_label in self.HAND_ORDER:
            self.time_bufs[hand_label].clear()
            for f in self.angle_bufs[hand_label]:
                self.angle_bufs[hand_label][f].clear()
            for sp in self.trial_spans[hand_label]:
                try:
                    sp.remove()
                except Exception:
                    pass
            self.trial_spans[hand_label].clear()
            self.axes[hand_label].set_xlim(0, 10)
            for f in self.lines[hand_label]:
                self.lines[hand_label][f].set_data([], [])
        self._last_render_t = None
        self.draw_idle()


# ================================================================
# 5. 메인 GUI 윈도우 (2-State 파지 시작/완료 구간 트래킹)
# ================================================================
class CapstoneClinicalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 Master-Slave 미러테라피 및 손 기능 평가 시스템 (2-State 구간 기록)")
        self.resize(1420, 930)
        self.setMinimumSize(1260, 800)

        # 세션 및 Trial 구간 상태 변수
        self.is_session_active = False
        self.session_start_time = 0.0
        self.session_records = []          # 전체 연속 시계열 데이터

        # 2-State Trial 상태 관리
        self.is_trial_in_progress = False  # 파지 진행 중 여부 (True: 파지 중, False: 대기/휴식)
        self.current_trial_idx = 1         # 현재 회차 번호
        self.current_trial_start_t = 0.0   # 현재 회차 시작 시간
        self.completed_trials = []         # 완료된 Trial 목록

        self.current_subject_folder = ""
        self.last_angles = {}
        self.measurement_paused = False    # 세션 중 양손이 동시에 인식되지 않아 기록을 일시정지한 상태

        # 양손 게이지 위젯 저장소 (hand_label -> finger -> widget)
        self.gauges = {}
        self.gauge_labels = {}
        self.gauge_titles = {}

        default_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "outputs", "데이터_저장"))
        os.makedirs(default_base_dir, exist_ok=True)
        self.base_output_dir = default_base_dir

        self.apply_clean_theme()
        self.init_ui()
        self.setup_shortcuts()

        # 비디오 스레드 시작
        self.video_worker = VideoWorker(camera_index=0)
        self.video_worker.frame_processed.connect(self.on_frame_ready)
        self.video_worker.start()

        # 실시간 상태 갱신 타이머 (0.1초)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_session_timer)
        self.status_timer.start(100)

    def apply_clean_theme(self):
        """가독성을 극대화한 선명하고 현대적인 다크 QSS 스타일시트"""
        qss = """
        * {
            font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        QMainWindow {
            background-color: #0b0d14;
        }
        QWidget {
            color: #f8fafc;
        }
        QGroupBox {
            background-color: #141724;
            border: 1px solid #282f48;
            border-radius: 8px;
            margin-top: 14px;
            font-weight: bold;
            font-size: 13px;
            color: #38bdf8;
            padding: 14px 10px 10px 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 12px;
        }
        QLabel {
            color: #e2e8f0;
            font-size: 13px;
            font-weight: 500;
        }
        QLineEdit, QSpinBox {
            background-color: #1c2032;
            border: 1px solid #3b4566;
            border-radius: 6px;
            padding: 6px 10px;
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
            min-height: 22px;
        }
        QLineEdit:focus, QSpinBox:focus {
            border: 1px solid #38bdf8;
            background-color: #242a42;
        }

        QComboBox {
            background-color: #1c2032;
            border: 1px solid #3b4566;
            border-radius: 6px;
            padding: 6px 12px;
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
            min-height: 22px;
        }
        QComboBox:hover {
            border: 1px solid #38bdf8;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid #3b4566;
            background-color: #242a42;
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
        }
        QComboBox QAbstractItemView {
            background-color: #141724;
            color: #ffffff;
            border: 1px solid #38bdf8;
            border-radius: 6px;
            padding: 4px;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            min-height: 32px;
            padding: 6px 10px;
            color: #f8fafc;
            border-radius: 4px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #334155;
            color: #38bdf8;
        }

        /* Trial 테이블 */
        QTableWidget {
            background-color: #12141f;
            border: 1px solid #282f48;
            border-radius: 6px;
            gridline-color: #242a42;
            color: #f1f5f9;
            font-size: 12px;
        }
        QHeaderView::section {
            background-color: #1c2032;
            color: #38bdf8;
            font-weight: bold;
            border: none;
            border-bottom: 1px solid #3b4566;
            padding: 4px;
            font-size: 11px;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            background-color: #2563eb;
            color: white;
        }

        QPushButton {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #1d4ed8;
        }
        QPushButton:pressed {
            background-color: #1e40af;
        }
        QPushButton:disabled {
            background-color: #2d3348;
            color: #64748b;
        }

        /* 제어 버튼들 */
        #btn_session_start {
            background-color: #059669;
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            min-height: 38px;
        }
        #btn_session_start:hover {
            background-color: #10b981;
        }
        #btn_trial_toggle {
            background-color: #0284c7;
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
            min-height: 48px;
            border-radius: 6px;
            border: 2px solid #38bdf8;
        }
        #btn_trial_toggle:hover {
            background-color: #0369a1;
        }
        #btn_trial_toggle:disabled {
            background-color: #2d3348;
            border: 1px solid #3b4566;
            color: #64748b;
        }
        #btn_session_stop {
            background-color: #dc2626;
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            min-height: 38px;
        }
        #btn_session_stop:hover {
            background-color: #ef4444;
        }

        QProgressBar {
            background-color: #191c2b;
            border: 1px solid #334155;
            border-radius: 4px;
            text-align: center;
            color: #ffffff;
            font-size: 10px;
            font-weight: bold;
            height: 14px;
        }
        QProgressBar::chunk {
            background-color: #0ea5e9;
            border-radius: 3px;
        }
        QCheckBox {
            color: #e2e8f0;
            font-size: 13px;
            font-weight: bold;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #475569;
            background-color: #1c2032;
        }
        QCheckBox::indicator:checked {
            background-color: #38bdf8;
            border: 1px solid #38bdf8;
        }
        """
        self.setStyleSheet(qss)

    # ------------------------------------------------------------
    # 양손 게이지 패널 생성/갱신 (신규)
    # ------------------------------------------------------------
    def _build_gauge_panel(self, hand_label):
        """한쪽 손에 대한 5손가락 게이지 패널(제목 + 게이지 5개)을 생성"""
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
        """해당 손이 인식되면 각도를 반영, 인식되지 않으면 '--'로 초기화"""
        title = self.gauge_titles[hand_label]
        hand_name = LiveAngleChart.HAND_TITLES[hand_label]

        if not hand_data:
            title.setText(f"{hand_name}  ·  미인식")
            title.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none;")
            for f in FINGERS:
                self.gauges[hand_label][f].setValue(0)
                self.gauge_labels[hand_label][f].setText(f"{f}: --°")
                self.gauge_labels[hand_label][f].setStyleSheet(
                    "font-size: 11px; font-weight: bold; color: #64748b; border: none;")
            return

        title.setText(f"{hand_name}  ·  인식됨")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; border: none;")

        filt = hand_data['filtered'] if isinstance(hand_data, dict) and 'filtered' in hand_data else hand_data
        for f in FINGERS:
            val = filt.get(f"{f}_Flexion", 180.0)
            self.gauges[hand_label][f].setValue(int(val))
            self.gauge_labels[hand_label][f].setText(f"{f}: {val:.1f}°")
            self.gauge_labels[hand_label][f].setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #38bdf8; border: none;")

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 좌측 패널 (피험자 정보 & 2-State Trial 구간 제어 & 결과 테이블)
        # -------------------------------------------------------------
        left_panel = QWidget()
        left_panel.setFixedWidth(440)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1. 피험자 구분
        group_type = QGroupBox("1. 피험자 구분 (Subject Group)")
        gt_layout = QHBoxLayout(group_type)
        self.rb_patient = QRadioButton("편마비 환자군 (Patient)")
        self.rb_healthy = QRadioButton("정상인 대조군 (Healthy)")
        self.rb_patient.setChecked(True)
        self.btn_group_type = QButtonGroup(self)
        self.btn_group_type.addButton(self.rb_patient)
        self.btn_group_type.addButton(self.rb_healthy)
        self.rb_healthy.toggled.connect(self.on_subject_type_changed)
        gt_layout.addWidget(self.rb_patient)
        gt_layout.addWidget(self.rb_healthy)
        left_layout.addWidget(group_type)

        # 2. 기본 인적 사항
        group_info = QGroupBox("2. 기본 인적 사항 (Demographics)")
        gi_layout = QGridLayout(group_info)
        gi_layout.setSpacing(6)

        gi_layout.addWidget(QLabel("이름 (Name):"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("예: 이재용 / P01")
        self.txt_name.setText("이재용")
        gi_layout.addWidget(self.txt_name, 0, 1)

        gi_layout.addWidget(QLabel("나이 (Age):"), 1, 0)
        self.spin_age = QSpinBox()
        self.spin_age.setRange(5, 110)
        self.spin_age.setValue(62)
        self.spin_age.setSuffix(" 세")
        gi_layout.addWidget(self.spin_age, 1, 1)

        gi_layout.addWidget(QLabel("성별 (Gender):"), 2, 0)
        self.cb_gender = QComboBox()
        self.cb_gender.addItems(["남성 (Male)", "여성 (Female)"])
        gi_layout.addWidget(self.cb_gender, 2, 1)
        left_layout.addWidget(group_info)

        # 3. 임상 평가 척도
        self.group_clinical = QGroupBox("3. 임상 재활 척도 (Clinical Scales)")
        gc_layout = QGridLayout(self.group_clinical)
        gc_layout.setSpacing(6)

        gc_layout.addWidget(QLabel("FMA-UE 점수:"), 0, 0)
        self.spin_fma = QSpinBox()
        self.spin_fma.setRange(0, 66)
        self.spin_fma.setValue(38)
        self.spin_fma.setSuffix(" / 66점")
        gc_layout.addWidget(self.spin_fma, 0, 1)

        gc_layout.addWidget(QLabel("Brunnstrom 단계:"), 1, 0)
        self.cb_brs = QComboBox()
        self.cb_brs.addItems([
            "Stage 1 (완전이완 / Flaccidity)",
            "Stage 2 (경직시작 / Spasticity)",
            "Stage 3 (공동운동극대 / Synergies)",
            "Stage 4 (부분분리운동 / Out of Synergy)",
            "Stage 5 (독립분리운동 / Complex Movement)",
            "Stage 6 (정상협응 / Normal)"
        ])
        self.cb_brs.setCurrentIndex(3)
        gc_layout.addWidget(self.cb_brs, 1, 1)

        gc_layout.addWidget(QLabel("환측 (마비손):"), 2, 0)
        self.cb_affected = QComboBox()
        self.cb_affected.addItems(["우측 (Right Hand)", "좌측 (Left Hand)"])
        gc_layout.addWidget(self.cb_affected, 2, 1)
        left_layout.addWidget(self.group_clinical)

        # 4. 과제 선택
        group_task = QGroupBox("4. 실험 프로토콜 과제 (Task Selection)")
        gtask_layout = QHBoxLayout(group_task)
        self.cb_task = QComboBox()
        self.cb_task.addItems([
            "Task 1: 맨손 쥐기/펴기 (Free Motion)",
            "Task 2: 원통형 파지 (Cylinder 5cm)",
            "Task 3: 구형 파지 (Sphere 7cm)",
            "Task 4: 미러테라피 폐루프 (Mirror Therapy)"
        ])
        gtask_layout.addWidget(self.cb_task)
        left_layout.addWidget(group_task)

        # 5. ★★★ 2-State (파지 시작 -> 파지 완료) 제어 패널 ★★★
        group_ctrl = QGroupBox("5. 파지 구간 (시작/완료) 측정 제어")
        gctrl_layout = QVBoxLayout(group_ctrl)
        gctrl_layout.setSpacing(8)

        # 세션 시작/종료 버튼
        session_btn_row = QHBoxLayout()
        self.btn_session_start = QPushButton("▶  전체 세션 시작")
        self.btn_session_start.setObjectName("btn_session_start")
        self.btn_session_start.clicked.connect(self.start_session)

        self.btn_session_stop = QPushButton("■  세션 종료 및 일괄저장")
        self.btn_session_stop.setObjectName("btn_session_stop")
        self.btn_session_stop.setEnabled(False)
        self.btn_session_stop.clicked.connect(self.stop_session)

        session_btn_row.addWidget(self.btn_session_start)
        session_btn_row.addWidget(self.btn_session_stop)
        gctrl_layout.addLayout(session_btn_row)

        # 핵심 2-State 토글 버튼 (스페이스바로 시작 누르고, 끝날 때 다시 누름!)
        self.btn_trial_toggle = QPushButton("▶  [Trial #1] 파지 시작 (Space)")
        self.btn_trial_toggle.setObjectName("btn_trial_toggle")
        self.btn_trial_toggle.setEnabled(False)
        self.btn_trial_toggle.clicked.connect(self.toggle_trial_state)
        gctrl_layout.addWidget(self.btn_trial_toggle)

        # Trial 결과 테이블 (과제명 포함 6열, 넉넉한 높이)
        self.table_trials = QTableWidget(0, 6)
        self.table_trials.setHorizontalHeaderLabels(["회차", "수행 과제", "시작~종료", "소요시간", "MGA(%)", "ROM(°)"])
        self.table_trials.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_trials.setFixedHeight(180)
        gctrl_layout.addWidget(self.table_trials)

        left_layout.addWidget(group_ctrl)
        main_layout.addWidget(left_panel)

        # -------------------------------------------------------------
        # 우측 패널 (웹캠 비디오 피드 & 실시간 각도 차트 & 상단 툴바)
        # -------------------------------------------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # 상단 비디오 카드
        video_card = QFrame()
        video_card.setStyleSheet("background-color: #141724; border-radius: 8px; border: 1px solid #282f48;")
        vc_layout = QVBoxLayout(video_card)
        vc_layout.setContentsMargins(8, 8, 8, 8)

        # 비디오 헤더 상태 바 (상태 + 미러링/필터 체크박스 + FPS + 저장폴더열기/종료 버튼)
        v_header = QHBoxLayout()
        self.lbl_session_status = QLabel("● READY (대기 중)")
        self.lbl_session_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")

        self.lbl_trial_status = QLabel("대기 상태 (시작 전)")
        self.lbl_trial_status.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")

        # 오른쪽 상단으로 이동된 미러링 & 필터 옵션
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

        v_header.addWidget(self.lbl_session_status)
        v_header.addSpacing(12)
        v_header.addWidget(self.lbl_trial_status)
        v_header.addStretch()
        v_header.addWidget(self.chk_mirror)
        v_header.addSpacing(8)
        v_header.addWidget(self.chk_filter)
        v_header.addSpacing(12)
        v_header.addWidget(self.lbl_fps)
        v_header.addSpacing(10)
        v_header.addWidget(self.btn_open_folder)
        v_header.addWidget(self.btn_exit)
        vc_layout.addLayout(v_header)

        # 웹캠 뷰 레이블
        self.lbl_video = QLabel("웹캠 영상을 연결하는 중입니다...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(400)
        self.lbl_video.setStyleSheet("background-color: #08090e; border-radius: 6px;")
        vc_layout.addWidget(self.lbl_video)

        # ★★★ 5손가락 실시간 각도 게이지 바 : 오른손/왼손 두 패널 동시 표시 ★★★
        gauge_row = QHBoxLayout()
        gauge_row.setSpacing(10)
        for hand_label in LiveAngleChart.HAND_ORDER:   # ('Right', 'Left')
            gauge_row.addWidget(self._build_gauge_panel(hand_label), stretch=1)
        vc_layout.addLayout(gauge_row)

        right_layout.addWidget(video_card, stretch=5)

        # 하단 실시간 차트 카드 (오른손/왼손 2단 그래프)
        chart_card = QFrame()
        chart_card.setStyleSheet("background-color: #141724; border-radius: 8px; border: 1px solid #282f48;")
        cc_layout = QVBoxLayout(chart_card)
        cc_layout.setContentsMargins(8, 6, 8, 6)

        lbl_chart_title = QLabel("실시간 5손가락 관절 굴곡각 궤적 (오른손/왼손 동시 표시, 청색 음영: 파지 동작 구간)")
        lbl_chart_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e2e8f0;")
        cc_layout.addWidget(lbl_chart_title)

        self.angle_chart = LiveAngleChart(self, width=6, height=4.2)
        cc_layout.addWidget(self.angle_chart)

        # 하단 알림 토스트 배너
        self.lbl_toast = QLabel("안내: [세션 시작] 후 파지 시작할 때 [Space], 파지 끝나고 손 뗄 때 [Space]를 누르세요.")
        self.lbl_toast.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 2px 6px; font-weight: 500;")
        cc_layout.addWidget(self.lbl_toast)

        right_layout.addWidget(chart_card, stretch=5)
        main_layout.addWidget(right_panel, stretch=1)

    def setup_shortcuts(self):
        """전역 단축키 등록 ([Q] 종료, [M] 미러링, [Space] 파지 시작/완료 토글, [Esc] 종료)"""
        QShortcut(QKeySequence("Q"), self).activated.connect(self.handle_q_quit)
        QShortcut(QKeySequence("q"), self).activated.connect(self.handle_q_quit)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.close)
        QShortcut(QKeySequence("M"), self).activated.connect(self.toggle_mirror)
        QShortcut(QKeySequence("m"), self).activated.connect(self.toggle_mirror)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.handle_space_action)

    def handle_q_quit(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            self.close()

    def toggle_mirror(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            self.chk_mirror.toggle()  # 실제 처리(플립/필터초기화/토스트)는 on_mirror_toggled에서 일괄 수행

    def on_mirror_toggled(self, enabled):
        """미러링 체크박스(또는 [M] 단축키) 변경 시 호출.
        VideoWorker의 좌우 플립을 갱신하고, Right/Left 라벨이 뒤바뀌며 생기는
        필터 잔상 및 그래프 불연속을 함께 정리한다."""
        self.video_worker.set_mirror_mode(enabled)
        self.angle_chart.reset_chart()
        # 라벨이 뒤바뀌는 순간 이전 손의 값이 남아있지 않도록 게이지도 초기화
        for hand_label in LiveAngleChart.HAND_ORDER:
            self._update_gauge_panel(hand_label, None)
        mode_str = "ON (좌우반전)" if enabled else "OFF"
        self.show_toast(f"미러링 모드 변경: {mode_str}")

    def handle_space_action(self):
        """스페이스바 입력 시: 세션이 켜져 있으면 파지 시작/완료 토글, 안 켜져 있으면 세션 시작"""
        if isinstance(self.focusWidget(), QLineEdit):
            return
        if self.is_session_active:
            self.toggle_trial_state()
        else:
            self.start_session()

    def show_toast(self, message, is_success=False):
        color = "#10b981" if is_success else "#38bdf8"
        self.lbl_toast.setText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.lbl_toast.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; padding: 2px 6px;")

    def on_subject_type_changed(self, is_healthy):
        if is_healthy:
            self.group_clinical.setEnabled(False)
            self.group_clinical.setTitle("3. 임상 재활 척도 (정상인: 해당 없음)")
            self.show_toast("피험자 군 설정: [정상인 대조군]")
        else:
            self.group_clinical.setEnabled(True)
            self.group_clinical.setTitle("3. 임상 재활 척도 (Clinical Scales)")
            self.show_toast("피험자 군 설정: [편마비 환자군]")

    def make_subject_folder(self):
        date_str = datetime.now().strftime("%Y%m%d")
        name = self.txt_name.text().strip() or "Anonymous"
        age = self.spin_age.value()
        gender = "남" if "남성" in self.cb_gender.currentText() else "여"

        if self.rb_healthy.isChecked():
            folder_name = f"{date_str}_정상인_{name}_{age}세_{gender}"
        else:
            fma = self.spin_fma.value()
            brs_stage = self.cb_brs.currentIndex() + 1
            folder_name = f"{date_str}_환자_{name}_{age}세_{gender}_FMA{fma}_BRS{brs_stage}"

        full_path = os.path.join(self.base_output_dir, folder_name)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    def start_session(self):
        """연속 세션 시작"""
        name = self.txt_name.text().strip()
        if not name:
            self.show_toast("경고: 피험자 이름을 입력해주세요!")
            return

        self.current_subject_folder = self.make_subject_folder()
        self.is_session_active = True
        self.session_start_time = time.time()
        self.session_records.clear()

        # Trial 상태 초기화
        self.is_trial_in_progress = False
        self.current_trial_idx = 1
        self.completed_trials.clear()
        self.table_trials.setRowCount(0)
        self.angle_chart.reset_chart()
        self.measurement_paused = False

        # UI 상태 업데이트
        self.btn_session_start.setEnabled(False)
        self.btn_session_stop.setEnabled(True)
        self.btn_trial_toggle.setEnabled(True)

        # 버튼을 [Trial #1 파지 시작] 상태로 설정
        self.set_trial_button_ui(starting=True)

        self.txt_name.setEnabled(False)
        self.spin_age.setEnabled(False)
        self.cb_gender.setEnabled(False)
        self.rb_healthy.setEnabled(False)
        self.rb_patient.setEnabled(False)

        task_name = self.cb_task.currentText()
        self.lbl_session_status.setText("● REC (세션 연속 기록 중...)")
        self.lbl_session_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")
        self.lbl_trial_status.setText("준비됨 (파지 시작 대기)")
        self.lbl_trial_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")

        self.show_toast(f"▶ [{task_name}] 세션 시작! 파지 시작 시 [Space]를 누르세요.", is_success=True)

    def set_trial_button_ui(self, starting=True):
        """Trial 버튼 텍스트 및 스타일 동적 전환"""
        if starting:
            # 시작 대기 상태 (파란색 버튼)
            self.btn_trial_toggle.setText(f"▶  [Trial #{self.current_trial_idx}] 파지 시작 (Space)")
            self.btn_trial_toggle.setStyleSheet("""
                #btn_trial_toggle {
                    background-color: #0284c7;
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: bold;
                    min-height: 48px;
                    border: 2px solid #38bdf8;
                }
                #btn_trial_toggle:hover { background-color: #0369a1; }
            """)
        else:
            # 파지 진행 중 상태 (주황/빨간색 강조 버튼)
            self.btn_trial_toggle.setText(f"⏹  [Trial #{self.current_trial_idx}] 파지 완료 / 종료 (Space)")
            self.btn_trial_toggle.setStyleSheet("""
                #btn_trial_toggle {
                    background-color: #ea580c;
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: bold;
                    min-height: 48px;
                    border: 2px solid #fdba74;
                }
                #btn_trial_toggle:hover { background-color: #c2410c; }
            """)

    def toggle_trial_state(self):
        """
        ★★★ 핵심 2-State 로직 ★★★
        1번째 클릭: 파지 시작 (Start Marker)
        2번째 클릭: 파지 완료 (End Marker & 구간 데이터 자동 산출)
        """
        if not self.is_session_active or not self.session_records:
            return

        if self.measurement_paused:
            # 양손이 모두 인식되지 않는 동안은 스페이스바로도 Trial을 시작/종료할 수 없게 막음
            self.show_toast("⏸ 양손이 모두 인식되어야 파지 시작/완료를 기록할 수 있습니다.")
            return

        t_now = time.time() - self.session_start_time

        if not self.is_trial_in_progress:
            # [1] 파지 동작 시작!
            self.is_trial_in_progress = True
            self.current_trial_start_t = t_now
            self.set_trial_button_ui(starting=False) # 버튼을 [파지 완료] 상태로 변경

            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
            self.show_toast(f"▶ [Trial #{self.current_trial_idx}] 파지 시작 마킹! 파지 끝나고 손 뗄 때 [Space]를 누르세요.")

        else:
            # [2] 파지 동작 완료!
            self.is_trial_in_progress = False
            t_end = t_now
            t_start = self.current_trial_start_t
            duration = max(0.01, t_end - t_start)

            # 시작~종료 사이의 데이터 구간 슬라이싱
            segment = [r for r in self.session_records if t_start <= r['time'] <= t_end]
            if not segment:
                segment = self.session_records[-15:]

            # 정확한 파지 구간 지표 연산
            apertures = [r['filtered'].get('Grip_Aperture', 0) for r in segment]
            mga_val = max(apertures) if apertures else 0.0

            index_pips = [r['filtered'].get('Index_PIP', 180.0) for r in segment]
            rom_val = (max(index_pips) - min(index_pips)) if index_pips else 0.0

            cur_task_full = self.cb_task.currentText()
            cur_task_short = cur_task_full.split(":")[0].strip()

            trial_info = {
                "trial": self.current_trial_idx,
                "task": cur_task_full,
                "task_short": cur_task_short,
                "start_time": t_start,
                "end_time": t_end,
                "duration": duration,
                "mga": mga_val,
                "rom": rom_val
            }
            self.completed_trials.append(trial_info)

            # 실시간 차트에 파지 구간 음영 표시
            self.angle_chart.add_trial_span(t_start, t_end, f"T{self.current_trial_idx}")

            # 테이블에 완벽한 구간 결과 행 추가 (과제명 포함 6열)
            row_pos = self.table_trials.rowCount()
            self.table_trials.insertRow(row_pos)
            self.table_trials.setItem(row_pos, 0, QTableWidgetItem(f"Trial #{self.current_trial_idx}"))
            self.table_trials.setItem(row_pos, 1, QTableWidgetItem(cur_task_short))
            self.table_trials.setItem(row_pos, 2, QTableWidgetItem(f"{t_start:.1f}s ~ {t_end:.1f}s"))
            self.table_trials.setItem(row_pos, 3, QTableWidgetItem(f"{duration:.2f}초"))
            self.table_trials.setItem(row_pos, 4, QTableWidgetItem(f"{mga_val:.1f}%"))
            self.table_trials.setItem(row_pos, 5, QTableWidgetItem(f"{rom_val:.1f}°"))
            self.table_trials.scrollToBottom()

            # 다음 회차 준비
            self.current_trial_idx += 1
            self.set_trial_button_ui(starting=True)

            self.lbl_trial_status.setText(f"완료됨 (총 {len(self.completed_trials)}회 기록 완료)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.show_toast(f"✅ [Trial #{self.current_trial_idx - 1} - {cur_task_short}] 기록 완료! (소요시간: {duration:.2f}초, MGA: {mga_val:.1f}%, ROM: {rom_val:.1f}°)", is_success=True)

    def stop_session(self):
        """세션 종료 및 일괄 자동 저장"""
        if not self.is_session_active:
            return

        # 만약 파지 도중에 세션 종료를 눌렀다면 현재 Trial 자동 마감
        if self.is_trial_in_progress:
            self.toggle_trial_state()

        self.is_session_active = False
        duration = time.time() - self.session_start_time

        # UI 복구
        self.btn_session_start.setEnabled(True)
        self.btn_session_stop.setEnabled(False)
        self.btn_trial_toggle.setEnabled(False)
        self.txt_name.setEnabled(True)
        self.spin_age.setEnabled(True)
        self.cb_gender.setEnabled(True)
        self.rb_healthy.setEnabled(True)
        self.rb_patient.setEnabled(True)

        self.lbl_session_status.setText("● READY (세션 완료)")
        self.lbl_session_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        self.lbl_trial_status.setText(f"총 {len(self.completed_trials)}회차 데이터 저장됨")

        # 일괄 파일 저장
        saved_files = self.save_session_batch(duration)

        total_trials = len(self.completed_trials)
        self.show_toast(f"✅ 세션 저장 완료! 총 {total_trials}개 회차 일괄 저장됨 (소요시간: {duration:.1f}초)", is_success=True)

    def save_session_batch(self, duration):
        """전체 연속 시계열 + Trial별 분할 요약표 + 통합 플롯 일괄 저장"""
        if not self.session_records:
            self.show_toast("⚠️ 수집된 데이터가 없어 저장을 건너뜁니다.")
            return []

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"Session_{ts_str}"

        saved_paths = []

        # 1. 전체 연속 시계열 CSV (순수 Raw 데이터와 Filtered 데이터를 나란히 전수 기록!)
        raw_csv_path = os.path.join(self.current_subject_folder, f"{prefix}_continuous_raw.csv")
        headers = [
            "time_s", "Task", "Trial", "Movement_Phase", "hand_label",
            "Thumb_MCP_raw", "Thumb_MCP_filt", "Thumb_IP_raw", "Thumb_IP_filt",
            "Index_MCP_raw", "Index_MCP_filt", "Index_PIP_raw", "Index_PIP_filt", "Index_DIP_raw", "Index_DIP_filt",
            "Middle_MCP_raw", "Middle_MCP_filt", "Middle_PIP_raw", "Middle_PIP_filt", "Middle_DIP_raw", "Middle_DIP_filt",
            "Ring_MCP_raw", "Ring_MCP_filt", "Ring_PIP_raw", "Ring_PIP_filt", "Ring_DIP_raw", "Ring_DIP_filt",
            "Pinky_MCP_raw", "Pinky_MCP_filt", "Pinky_PIP_raw", "Pinky_PIP_filt", "Pinky_DIP_raw", "Pinky_DIP_filt",
            "Grip_Aperture_raw", "Grip_Aperture_filt"
        ]

        with open(raw_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for rec in self.session_records:
                t = rec['time']
                task_name = rec.get('task', self.cb_task.currentText())
                trial_tag = "Rest"
                phase_tag = "Rest"

                for tr in self.completed_trials:
                    if tr['start_time'] <= t <= tr['end_time']:
                        task_name = tr.get('task', task_name)
                        trial_tag = f"Trial_{tr['trial']}"
                        phase_tag = "Grasping"
                        break

                hand = rec['hand']
                raw_a = rec['raw']
                filt_a = rec['filtered']
                row = [
                    f"{t:.4f}", task_name, trial_tag, phase_tag, hand,
                    f"{raw_a.get('Thumb_MCP', 0):.2f}", f"{filt_a.get('Thumb_MCP', 0):.2f}",
                    f"{raw_a.get('Thumb_IP', 0):.2f}", f"{filt_a.get('Thumb_IP', 0):.2f}",
                    f"{raw_a.get('Index_MCP', 0):.2f}", f"{filt_a.get('Index_MCP', 0):.2f}",
                    f"{raw_a.get('Index_PIP', 0):.2f}", f"{filt_a.get('Index_PIP', 0):.2f}",
                    f"{raw_a.get('Index_DIP', 0):.2f}", f"{filt_a.get('Index_DIP', 0):.2f}",
                    f"{raw_a.get('Middle_MCP', 0):.2f}", f"{filt_a.get('Middle_MCP', 0):.2f}",
                    f"{raw_a.get('Middle_PIP', 0):.2f}", f"{filt_a.get('Middle_PIP', 0):.2f}",
                    f"{raw_a.get('Middle_DIP', 0):.2f}", f"{filt_a.get('Middle_DIP', 0):.2f}",
                    f"{raw_a.get('Ring_MCP', 0):.2f}", f"{filt_a.get('Ring_MCP', 0):.2f}",
                    f"{raw_a.get('Ring_PIP', 0):.2f}", f"{filt_a.get('Ring_PIP', 0):.2f}",
                    f"{raw_a.get('Ring_DIP', 0):.2f}", f"{filt_a.get('Ring_DIP', 0):.2f}",
                    f"{raw_a.get('Pinky_MCP', 0):.2f}", f"{filt_a.get('Pinky_MCP', 0):.2f}",
                    f"{raw_a.get('Pinky_PIP', 0):.2f}", f"{filt_a.get('Pinky_PIP', 0):.2f}",
                    f"{raw_a.get('Pinky_DIP', 0):.2f}", f"{filt_a.get('Pinky_DIP', 0):.2f}",
                    f"{raw_a.get('Grip_Aperture', 0):.2f}", f"{filt_a.get('Grip_Aperture', 0):.2f}"
                ]
                writer.writerow(row)
        saved_paths.append(raw_csv_path)

        # 2. Trial별 정확한 구간 요약 비교표 CSV (과제명 포함)
        summary_csv_path = os.path.join(self.current_subject_folder, f"{prefix}_trials_summary.csv")
        with open(summary_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Trial", "Task", "Start_Time_s", "End_Time_s", "Duration_s", "MGA_pct", "Index_ROM_deg", "Thumb_PIP_Mean", "Index_PIP_Mean", "Middle_PIP_Mean"])

            for tr in self.completed_trials:
                seg = [r for r in self.session_records if tr['start_time'] <= r['time'] <= tr['end_time']]
                if not seg:
                    continue
                t_pips = [r['filtered'].get('Thumb_IP', 0) for r in seg]
                i_pips = [r['filtered'].get('Index_PIP', 0) for r in seg]
                m_pips = [r['filtered'].get('Middle_PIP', 0) for r in seg]

                writer.writerow([
                    f"Trial #{tr['trial']}",
                    tr.get('task_short', 'Task'),
                    f"{tr['start_time']:.2f}",
                    f"{tr['end_time']:.2f}",
                    f"{tr['duration']:.2f}",
                    f"{tr['mga']:.2f}",
                    f"{tr['rom']:.2f}",
                    f"{np.mean(t_pips):.2f}",
                    f"{np.mean(i_pips):.2f}",
                    f"{np.mean(m_pips):.2f}"
                ])
        saved_paths.append(summary_csv_path)

        # 3. 파지 구간 음영이 들어간 고해상도 전체 세션 그래프 PNG
        plot_path = os.path.join(self.current_subject_folder, f"{prefix}_waveform_plot.png")
        self.export_session_plot(plot_path, prefix)
        saved_paths.append(plot_path)

        # 4. 메타데이터 JSON
        meta_path = os.path.join(self.current_subject_folder, "subject_metadata.json")
        meta_data = {
            "name": self.txt_name.text().strip(),
            "age": self.spin_age.value(),
            "gender": self.cb_gender.currentText(),
            "group": "Healthy" if self.rb_healthy.isChecked() else "Patient",
            "fma_score": self.spin_fma.value() if self.rb_patient.isChecked() else None,
            "brunnstrom_stage": self.cb_brs.currentText() if self.rb_patient.isChecked() else None,
            "affected_side": self.cb_affected.currentText() if self.rb_patient.isChecked() else None,
            "total_completed_trials": len(self.completed_trials),
            "session_duration_sec": duration,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        return saved_paths

    def export_session_plot(self, save_path, title_prefix):
        """파지 시작~완료 구간이 노란색/청색 밴드로 하이라이트된 고해상도 그래프 저장"""
        if not self.session_records:
            return

        t_arr = [r['time'] for r in self.session_records]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, dpi=150)
        fig.patch.set_facecolor('#ffffff')

        colors = {'Thumb_IP': '#ef4444', 'Index_PIP': '#0ea5e9', 'Middle_PIP': '#22c55e', 'Ring_PIP': '#f59e0b', 'Pinky_PIP': '#a855f7'}
        labels = {'Thumb_IP': 'Thumb IP', 'Index_PIP': 'Index PIP', 'Middle_PIP': 'Middle PIP', 'Ring_PIP': 'Ring PIP', 'Pinky_PIP': 'Pinky PIP'}

        for k, col in colors.items():
            vals = [r['filtered'].get(k, np.nan) for r in self.session_records]
            ax1.plot(t_arr, vals, label=labels[k], color=col, linewidth=1.8)

        # 파지 동작 구간 음영 하이라이트 (Start -> End)
        for tr in self.completed_trials:
            t_s = tr['start_time']
            t_e = tr['end_time']
            task_tag = tr.get('task_short', f"T{tr['trial']}")
            ax1.axvspan(t_s, t_e, color='#fef08a', alpha=0.35, label='_nolegend_')
            ax1.text((t_s + t_e)/2, 168, f"T{tr['trial']} ({task_tag})", color='#854d0e', fontweight='bold', fontsize=8, ha='center')
            ax2.axvspan(t_s, t_e, color='#fef08a', alpha=0.35, label='_nolegend_')

        ax1.set_ylim(0, 180)
        ax1.set_ylabel("Flexion Angle (deg)", fontweight='bold')
        ax1.set_title(f"[{title_prefix}] 5-Finger Continuous Session with Grasping Intervals", fontsize=11, fontweight='bold')
        ax1.grid(True, linestyle=':', alpha=0.6)
        ax1.legend(loc='upper right', fontsize=8)

        aperture_vals = [r['filtered'].get('Grip_Aperture', 0) for r in self.session_records]
        ax2.plot(t_arr, aperture_vals, color='#334155', linewidth=2.0, label='Grip Aperture (%)')
        ax2.set_ylabel("Aperture (rel %)", fontweight='bold')
        ax2.set_xlabel("Elapsed Time (seconds)", fontweight='bold')
        ax2.grid(True, linestyle=':', alpha=0.6)
        ax2.legend(loc='upper right', fontsize=8)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close(fig)

    def _refresh_trial_status_label(self):
        """일시정지 배너를 걷어낼 때, 현재 Trial 진행 상태에 맞는 표시로 복원"""
        if self.is_trial_in_progress:
            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
        elif self.completed_trials:
            self.lbl_trial_status.setText(f"완료됨 (총 {len(self.completed_trials)}회 기록 완료)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
        else:
            self.lbl_trial_status.setText("준비됨 (파지 시작 대기)")
            self.lbl_trial_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")

    def on_frame_ready(self, frame, angles_dict, fps, hand_count):
        self.last_angles = angles_dict
        self.lbl_fps.setText(f"FPS: {fps:.1f}  |  Hands: {hand_count}")

        both_hands_detected = ('Right' in angles_dict) and ('Left' in angles_dict)

        if self.is_session_active:
            if both_hands_detected:
                if self.measurement_paused:
                    # 양손이 다시 인식되어 측정 재개
                    self.measurement_paused = False
                    self.btn_trial_toggle.setEnabled(True)
                    self._refresh_trial_status_label()
                    self.show_toast("▶ 양손 인식 완료! 측정을 재개합니다.", is_success=True)

                t = time.time() - self.session_start_time
                primary_hand = 'Right' if 'Right' in angles_dict else ('Left' if 'Left' in angles_dict else list(angles_dict.keys())[0])
                h_data = angles_dict[primary_hand]
                self.session_records.append({
                    'time': t,
                    'hand': primary_hand,
                    'raw': h_data['raw'],
                    'filtered': h_data['filtered'],
                    'task': self.cb_task.currentText()
                })
                self.angle_chart.update_data(t, angles_dict)
            else:
                if not self.measurement_paused:
                    # 두 손 중 하나라도 인식이 끊겨 측정 일시정지
                    self.measurement_paused = True
                    self.btn_trial_toggle.setEnabled(False)
                    self.show_toast("⏸ 양손이 모두 인식되지 않아 측정을 일시정지합니다. 두 손을 화면에 비춰주세요.")
                self.lbl_trial_status.setText("⏸ 측정 일시정지 (양손 인식 필요)")
                self.lbl_trial_status.setStyleSheet("color: #f97316; font-weight: bold; font-size: 13px;")
                # 기록(session_records)과 실시간 그래프 갱신은 건너뛰고 직전 상태를 그대로 유지

        # ★★★ 오른손/왼손 게이지를 각각 독립적으로 갱신 (인식 안 된 손은 '--'로 표시) ★★★
        for hand_label in LiveAngleChart.HAND_ORDER:
            self._update_gauge_panel(hand_label, angles_dict.get(hand_label))

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_BGR888)

        lbl_w = self.lbl_video.width()
        lbl_h = self.lbl_video.height()
        pixmap = QtGui.QPixmap.fromImage(q_img).scaled(
            lbl_w, lbl_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_video.setPixmap(pixmap)

    def update_session_timer(self):
        if self.is_session_active:
            elapsed = time.time() - self.session_start_time
            frames = len(self.session_records)
            self.lbl_session_status.setText(f"● REC ({elapsed:.1f}초 | {frames} 프레임)")

    def open_output_folder(self):
        folder = self.current_subject_folder if os.path.exists(self.current_subject_folder) else self.base_output_dir
        if sys.platform == 'win32':
            os.startfile(folder)
        else:
            self.show_toast(f"폴더 위치: {folder}")

    def closeEvent(self, event):
        if self.is_session_active:
            self.stop_session()
        self.video_worker.stop()
        event.accept()


# ================================================================
# 6. 실행 진입점 (선명한 폰트 렌더링 활성화)
# ================================================================
def main():
    if hasattr(QtCore.Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    font = QFont("Malgun Gothic", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    window = CapstoneClinicalApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
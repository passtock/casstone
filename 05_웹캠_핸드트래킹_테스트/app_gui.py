"""
[공압장갑 Master-Slave 미러테라피 및 AI 손 기능 정량 평가 시스템 v3.5 - 최적화 통합본]
- Intel RealSense RGB-D 실제 Depth 3D 역투영(Deprojection) & 일반 웹캠 하이브리드 연동
- QThreadPool 기반 비동기 백그라운드 저장 (Matplotlib savefig 및 CSV I/O 지연 제로화)
- SVD 다점 평면 피팅 기반 내인성 3D 관절각 추출 (시점/거리 불변성)
- SPARC(Spectral Arc Length) 미분 노이즈 사전 평활화 및 적응형 컷오프
- 엑셀 한글 호환(UTF-8-SIG), 21개 3D 관절 좌표(63열) 및 임상 메타데이터 자동 관리
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

# Intel RealSense SDK 연동 시도
try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRunnable, QThreadPool, QObject
from PyQt6.QtGui import QKeySequence, QShortcut, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QRadioButton,
    QButtonGroup, QPushButton, QGroupBox, QFrame, QTextEdit,
    QCheckBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QTabWidget
)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


# ================================================================
# 1. 고감도 저지연 One-Euro 필터
# ================================================================
class OneEuroFilter:
    def __init__(self, t0=None, x0=180.0, dx0=0.0, min_cutoff=0.7, beta=0.03, d_cutoff=1.5):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)
        self.t_prev = t0

    def smoothing_factor(self, t_e, cutoff):
        r = 2.0 * math.pi * cutoff * t_e
        return r / (r + 1.0)

    def exponential_smoothing(self, a, x, x_prev):
        return a * x + (1.0 - a) * x_prev

    def filter(self, t, x):
        if self.t_prev is None:
            self.t_prev = t
            self.x_prev = x
            return x

        t_e = t - self.t_prev
        if t_e <= 1e-5:
            return self.x_prev

        raw_dx = (x - self.x_prev) / t_e
        a_d = self.smoothing_factor(t_e, self.d_cutoff)
        dx_hat = self.exponential_smoothing(a_d, raw_dx, self.dx_prev)

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self.smoothing_factor(t_e, cutoff)
        x_hat = self.exponential_smoothing(a, x, self.x_prev)

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


# ================================================================
# 2. 연속 적응형 생체역학 필터
# ================================================================
class SmoothKinematicFilter:
    def __init__(self, init_val=180.0):
        self.val = float(init_val)
        self.last_valid_val = float(init_val)
        self.missing_count = 0
        self.max_missing_hold = 12
        self.euro_filter = OneEuroFilter(x0=init_val, min_cutoff=1.5, beta=0.05)
        self.max_deg_per_frame = 30.0

    def update(self, t, raw_val):
        if raw_val is None or (isinstance(raw_val, float) and (np.isnan(raw_val) or raw_val <= 0.0)):
            self.missing_count += 1
            if self.missing_count <= self.max_missing_hold:
                return self.last_valid_val
            else:
                self.last_valid_val = 0.98 * self.last_valid_val + 0.02 * 160.0
                return self.last_valid_val

        self.missing_count = 0
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
# 2-1. 랜드마크 좌표 레벨 사전 스무딩
# ================================================================
class LandmarkSmoother:
    def __init__(self):
        self.filters = [
            [
                OneEuroFilter(min_cutoff=0.4, beta=0.08, d_cutoff=1.2),   # x
                OneEuroFilter(min_cutoff=0.4, beta=0.08, d_cutoff=1.2),   # y
                OneEuroFilter(min_cutoff=0.15, beta=0.002, d_cutoff=0.8), # z
            ]
            for _ in range(21)
        ]

    def smooth(self, t, pts):
        smoothed = np.empty_like(pts)
        for i in range(21):
            for j in range(3):
                smoothed[i, j] = self.filters[i][j].filter(t, float(pts[i, j]))
        return smoothed


# ================================================================
# 3. SVD 다점 평면 피팅 & 3D 내인성 관절각 연산
# ================================================================
def compute_robust_palm_frame(pts):
    palm_idx = [0, 1, 5, 9, 13, 17]
    palm_pts = pts[palm_idx]
    centroid = np.mean(palm_pts, axis=0)
    shifted = palm_pts - centroid

    _, _, vt = np.linalg.svd(shifted)
    normal = vt[2]

    ref_norm = np.cross(pts[5] - pts[0], pts[17] - pts[0])
    if np.dot(normal, ref_norm) < 0:
        normal = -normal

    v_y = pts[9] - pts[0]
    ny = np.linalg.norm(v_y)
    if ny < 1e-7:
        return pts, centroid, np.eye(3)
    u_y = v_y / ny

    u_y = u_y - np.dot(u_y, normal) * normal
    u_y = u_y / (np.linalg.norm(u_y) + 1e-7)

    u_x = np.cross(u_y, normal)
    u_x = u_x / (np.linalg.norm(u_x) + 1e-7)

    R = np.vstack([u_x, u_y, normal])
    canonical_pts = (R @ (pts - pts[0]).T).T / ny
    return canonical_pts, centroid, R


def calc_angle_3d(pa, pb, pc):
    ba = pa - pb
    bc = pc - pb
    n1, n2 = np.linalg.norm(ba), np.linalg.norm(bc)
    if n1 < 1e-7 or n2 < 1e-7:
        return 180.0
    cos_v = np.clip(np.dot(ba, bc) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_v)))


def compute_angles_and_pts(landmarks):
    if isinstance(landmarks, np.ndarray):
        pts_raw = landmarks.astype(np.float64)
    else:
        pts_raw = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float64)
    pts, centroid, R = compute_robust_palm_frame(pts_raw)
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

    # 대표 굴곡각
    a['Thumb_Flexion']  = a['Thumb_IP']
    a['Index_Flexion']  = a['Index_PIP']
    a['Middle_Flexion'] = a['Middle_PIP']
    a['Ring_Flexion']   = a['Ring_PIP']
    a['Pinky_Flexion']  = a['Pinky_PIP']

    a['Grip_Aperture'] = float(np.linalg.norm(pts[4] - pts[8]) * 100.0)

    return a, pts, centroid, R


def smooth_series(data, window_len=5):
    """미분 전 고주파 노이즈를 억제하는 경량 이동평균 필터"""
    if len(data) < window_len:
        return np.array(data, dtype=np.float64)
    w = np.ones(window_len, 'd') / window_len
    smoothed = np.convolve(data, w, mode='same')
    smoothed[:window_len//2] = data[:window_len//2]
    smoothed[-window_len//2:] = data[-window_len//2:]
    return smoothed


def compute_sparc(movement_data, time_series=None, dt=1.0/30.0, amp_th=0.05, fc_max=10.0, padlevel=4):
    """
    Balasubramanian et al. (2015) 표준 Spectral Arc Length (SPARC) 원본 알고리즘
    """
    if movement_data is None or len(movement_data) < 10:
        return 0.0

    v = np.array(movement_data, dtype=np.float64)

    # 가변 타임스탬프 리샘플링 (60Hz 균등 샘플링)
    if time_series is not None and len(time_series) == len(v):
        t = np.array(time_series, dtype=np.float64)
        if len(t) > 1:
            total_time = t[-1] - t[0]
            if total_time > 1e-4:
                fs = 60.0
                dt = 1.0 / fs
                num_points = max(15, int(total_time * fs))
                t_uniform = np.linspace(t[0], t[-1], num_points)
                v = np.interp(t_uniform, t, v)

    n = len(v)
    nfft = int(2 ** (np.ceil(np.log2(n)) + padlevel))

    f = np.fft.rfftfreq(nfft, d=dt)
    v_fft = np.abs(np.fft.rfft(v, n=nfft))

    max_v = np.max(v_fft)
    if max_v < 1e-7:
        return 0.0

    v_norm = v_fft / max_v

    mask_fc_max = f <= fc_max
    f_sub = f[mask_fc_max]
    v_sub = v_norm[mask_fc_max]

    idx_above_th = np.where(v_sub >= amp_th)[0]
    if len(idx_above_th) == 0:
        fc = fc_max
    else:
        last_idx = idx_above_th[-1]
        fc = min(fc_max, f_sub[last_idx])

    if fc < 1e-5:
        return 0.0

    mask_band = f <= fc
    f_band = f[mask_band]
    v_band = v_norm[mask_band]

    if len(f_band) < 2:
        return 0.0

    df = np.diff(f_band)
    dv = np.diff(v_band)
    sparc = -np.sum(np.sqrt((df / fc)**2 + dv**2))

    return float(sparc)


# ================================================================
# 4. 하이브리드 비디오 워커 (RealSense RGB-D 3D Deprojection 지원)
# ================================================================
class VideoWorker(QThread):
    frame_processed = pyqtSignal(np.ndarray, dict, float, int, str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = True
        self.mirror_mode = True
        self.use_filter = True
        self.filters = {}
        self.landmark_smoothers = {}
        self.start_time = time.time()
        self.device_name = "Webcam"

    def set_mirror_mode(self, enabled):
        self.mirror_mode = enabled
        self.filters.clear()
        self.landmark_smoothers.clear()

    def set_filter_mode(self, enabled):
        self.use_filter = enabled

    def run(self):
        use_realsense = False
        pipeline = None
        align = None
        depth_intrin = None

        if REALSENSE_AVAILABLE:
            try:
                ctx = rs.context()
                devices = ctx.query_devices()
                if len(devices) > 0:
                    dev = devices[0]
                    dev_name = dev.get_info(rs.camera_info.name)
                    pipeline = rs.pipeline()
                    config = rs.config()

                    try:
                        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
                        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
                        profile = pipeline.start(config)
                    except Exception:
                        config = rs.config()
                        config.enable_stream(rs.stream.color, rs.format.bgr8, 30)
                        config.enable_stream(rs.stream.depth, rs.format.z16, 30)
                        profile = pipeline.start(config)

                    align = rs.align(rs.stream.color)
                    # 실제 카메라 고유 파라미터 (Intrinsics) 추출
                    color_stream = profile.get_stream(rs.stream.color).as_video_stream_profile()
                    depth_intrin = color_stream.get_intrinsics()

                    use_realsense = True
                    self.device_name = f"Intel RealSense ({dev_name})"
                    print(f"[성공] {self.device_name} (RGB-D 하드웨어 3D 연동 활성화)")
            except Exception as e:
                print(f"[경고] RealSense 초기화 실패 ({e}). 웹캠으로 대체합니다.")
                use_realsense = False
                pipeline = None

        cap = None
        if not use_realsense:
            self.device_name = f"Webcam (Cam #{self.camera_index})"
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"[에러] 카메라 {self.camera_index}번을 열 수 없습니다.")
                return

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
            frame = None
            depth_frame = None
            if use_realsense:
                try:
                    frames = pipeline.wait_for_frames(2000)
                    aligned_frames = align.process(frames)
                    color_frame = aligned_frames.get_color_frame()
                    depth_frame = aligned_frames.get_depth_frame()
                    if not color_frame or not depth_frame:
                        continue
                    frame = np.asanyarray(color_frame.get_data())
                except Exception:
                    time.sleep(0.005)
                    continue
            else:
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

            h_img, w_img = frame.shape[:2]
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
                        if not self.mirror_mode:
                            hl = "Right" if hl == "Left" else "Left"

                    mp_drawing.draw_landmarks(
                        frame, hand_lms, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style()
                    )

                    # 3D 랜드마크 추출 (RealSense Depth 우선 -> MediaPipe World Landmark Fallback)
                    pts_np = np.zeros((21, 3), dtype=np.float64)
                    used_realsense_depth = False

                    if use_realsense and depth_frame and depth_intrin:
                        valid_count = 0
                        for i, lm in enumerate(hand_lms.landmark):
                            px = int((1.0 - lm.x if self.mirror_mode else lm.x) * w_img)
                            py = int(lm.y * h_img)
                            px = np.clip(px, 0, w_img - 1)
                            py = np.clip(py, 0, h_img - 1)
                            dist = depth_frame.get_distance(px, py)
                            if 0.15 < dist < 2.5:
                                pt3 = rs.rs2_deproject_pixel_to_point(depth_intrin, [px, py], dist)
                                pts_np[i] = [pt3[0] * 1000.0, pt3[1] * 1000.0, pt3[2] * 1000.0] # mm 단위 변환
                                valid_count += 1
                        if valid_count >= 15: # 대부분의 랜드마크 깊이가 유효할 때
                            used_realsense_depth = True

                    if not used_realsense_depth:
                        calc_lm = wl_list[hi].landmark if (wl_list and hi < len(wl_list)) else hand_lms.landmark
                        pts_np = np.array([[lm.x, lm.y, lm.z] for lm in calc_lm], dtype=np.float64)

                    if self.use_filter:
                        if hl not in self.landmark_smoothers:
                            self.landmark_smoothers[hl] = LandmarkSmoother()
                        pts_np = self.landmark_smoothers[hl].smooth(t_sec, pts_np)

                    raw_angles, norm_pts, _, R = compute_angles_and_pts(pts_np)
                    pose_3d = (R.T @ norm_pts.T).T

                    filtered_angles = {}
                    for k, v in raw_angles.items():
                        fk = f"{hl}_{k}"
                        if fk not in self.filters:
                            self.filters[fk] = SmoothKinematicFilter(init_val=v)

                        if self.use_filter:
                            filtered_angles[k] = self.filters[fk].update(t_sec, v)
                        else:
                            filtered_angles[k] = v

                    latest_angles[hl] = {
                        'raw': raw_angles,
                        'filtered': filtered_angles,
                        'pts_3d': pose_3d
                    }

            self.frame_processed.emit(frame, latest_angles, fps, hand_count, self.device_name)

        if use_realsense and pipeline:
            pipeline.stop()
        if cap:
            cap.release()
        hands.close()

    def stop(self):
        self.running = False
        self.wait(1000)


# ================================================================
# 4-1. 백그라운드 비동기 저장 워커 (UI 프리징 완전 방지)
# ================================================================
class SaveTrialWorker(QRunnable):
    def __init__(self, target_dir, trial_info, seg_records):
        super().__init__()
        self.td = target_dir
        self.ti = trial_info
        self.seg = seg_records

    def run(self):
        try:
            tnum = self.ti['trial']
            tk = self.ti['task_key'].replace(" ", "")
            pfx = f"{tk}_Trial_{tnum:02d}"
            cp = os.path.join(self.td, f"{pfx}_timeseries.csv")

            lm_names = [
                "Wrist",
                "Thumb_CMC", "Thumb_MCP", "Thumb_IP", "Thumb_TIP",
                "Index_MCP", "Index_PIP", "Index_DIP", "Index_TIP",
                "Middle_MCP", "Middle_PIP", "Middle_DIP", "Middle_TIP",
                "Ring_MCP", "Ring_PIP", "Ring_DIP", "Ring_TIP",
                "Pinky_MCP", "Pinky_PIP", "Pinky_DIP", "Pinky_TIP"
            ]

            hd = ["time_s", "rel_time_s", "Task", "Trial", "hand_label",
                  "Thumb_MCP_raw", "Thumb_MCP_filt", "Thumb_IP_raw", "Thumb_IP_filt",
                  "Index_MCP_raw", "Index_MCP_filt", "Index_PIP_raw", "Index_PIP_filt", "Index_DIP_raw", "Index_DIP_filt",
                  "Middle_MCP_raw", "Middle_MCP_filt", "Middle_PIP_raw", "Middle_PIP_filt", "Middle_DIP_raw", "Middle_DIP_filt",
                  "Ring_MCP_raw", "Ring_MCP_filt", "Ring_PIP_raw", "Ring_PIP_filt", "Ring_DIP_raw", "Ring_DIP_filt",
                  "Pinky_MCP_raw", "Pinky_MCP_filt", "Pinky_PIP_raw", "Pinky_PIP_filt", "Pinky_DIP_raw", "Pinky_DIP_filt",
                  "Grip_Aperture_raw", "Grip_Aperture_filt"]
            
            for name in lm_names:
                hd.extend([f"{name}_3D_X", f"{name}_3D_Y", f"{name}_3D_Z"])

            t0 = self.ti['start_time']

            with open(cp, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(hd)
                for r in self.seg:
                    for hl, hd_data in r['hands'].items():
                        ra, fa = hd_data['raw'], hd_data['filtered']
                        row = [f"{r['time']:.4f}", f"{r['time']-t0:.4f}", self.ti['task_full'], f"Trial_{tnum}", hl]
                        for jn in ['Thumb_MCP', 'Thumb_IP', 'Index_MCP', 'Index_PIP', 'Index_DIP',
                                   'Middle_MCP', 'Middle_PIP', 'Middle_DIP', 'Ring_MCP', 'Ring_PIP', 'Ring_DIP',
                                   'Pinky_MCP', 'Pinky_PIP', 'Pinky_DIP']:
                            row.extend([f"{ra.get(jn, 0):.2f}", f"{fa.get(jn, 0):.2f}"])
                        row.extend([f"{ra.get('Grip_Aperture', 0):.2f}", f"{fa.get('Grip_Aperture', 0):.2f}"])
                        
                        pts_3d = hd_data.get('pts_3d')
                        if pts_3d is not None and len(pts_3d) == 21:
                            for pt in pts_3d:
                                row.extend([f"{pt[0]:.4f}", f"{pt[1]:.4f}", f"{pt[2]:.4f}"])
                        else:
                            row.extend(["0.0000"] * 63)
                        w.writerow(row)

            jp = os.path.join(self.td, f"{pfx}_summary.json")
            with open(jp, 'w', encoding='utf-8') as f:
                json.dump(self.ti, f, ensure_ascii=False, indent=2)

            # Matplotlib 그래프 백그라운드 렌더링 및 파일 저장
            pp = os.path.join(self.td, f"{pfx}_plot.png")
            self._save_plot(pp)

            sc = os.path.join(self.td, f"{tk}_Summary.csv")
            ex = os.path.exists(sc)
            with open(sc, 'a', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                if not ex:
                    w.writerow(["Trial", "Task", "Duration_s", "MGA_pct", "TAROM_deg", "SPARC"])
                w.writerow([f"Trial #{tnum}", self.ti['task_short'], f"{self.ti['duration']:.2f}",
                            f"{self.ti['mga']:.2f}", f"{self.ti['tarom']:.2f}", f"{self.ti['sparc']:.2f}"])
        except Exception as e:
            print(f"[저장 워커 에러] {e}")

    def _save_plot(self, plot_path):
        if not self.seg:
            return
        t0 = self.ti['start_time']

        fig = Figure(figsize=(8, 5.5), dpi=120)
        fig.patch.set_facecolor('#ffffff')
        a1 = fig.add_subplot(211)
        a2 = fig.add_subplot(212, sharex=a1)

        cs = {'Thumb_IP': '#ef4444', 'Index_PIP': '#0ea5e9', 'Middle_PIP': '#22c55e', 'Ring_PIP': '#f59e0b', 'Pinky_PIP': '#a855f7'}
        target_hand = self.ti.get('target_hand', 'Right' if any('Right' in r.get('hands', {}) for r in self.seg) else 'Left')
        ta = []
        angles_series = {k: [] for k in cs}
        aperture_series = []

        for r in self.seg:
            if target_hand in r['hands']:
                ta.append(r['time'] - t0)
                fa = r['hands'][target_hand]['filtered']
                for k in cs:
                    angles_series[k].append(fa.get(k, np.nan))
                aperture_series.append(fa.get('Grip_Aperture', 0))

        if not ta:
            return

        for k, c in cs.items():
            a1.plot(ta, angles_series[k], label=k.replace('_', ' '), color=c, linewidth=2.0)

        a1.set_ylim(0, 180)
        a1.set_ylabel("Flexion Angle (°)", fontweight='bold')
        a1.set_title(f"[{self.ti['task_key']} - {target_hand}] Trial #{self.ti['trial']} ({self.ti['duration']:.2f}s | TAROM: {self.ti['tarom']:.1f}°)", fontsize=10, fontweight='bold')
        a1.grid(True, linestyle=':', alpha=0.6)
        a1.legend(fontsize=8)

        a2.plot(ta, aperture_series, color='#334155', linewidth=2.0)
        a2.set_ylabel("Aperture (%)", fontweight='bold')
        a2.set_xlabel("Time (s)", fontweight='bold')
        a2.grid(True, linestyle=':', alpha=0.6)

        fig.tight_layout()
        fig.savefig(plot_path)


# ================================================================
# 5. 경량 2단 Matplotlib 실시간 차트
# ================================================================
class LiveAngleChart(FigureCanvas):
    HAND_ORDER = ('Right', 'Left')
    HAND_TITLES = {'Right': '오른손 (Right)', 'Left': '왼손 (Left)'}

    def __init__(self, parent=None, width=6, height=3.8, dpi=100):
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
        self.has_new_data = False

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
                ln, = ax.plot([], [], label=f, color=c, linewidth=1.8, alpha=0.95)
                self.lines[hl][f] = ln
            ax.legend(loc='upper right', fontsize=7, ncol=5, facecolor='#191c2b',
                      edgecolor='#334155', labelcolor='#f1f5f9')
            self.axes[hl] = ax
            self.time_bufs[hl] = deque(maxlen=200)
            self.angle_bufs[hl] = {f: deque(maxlen=200) for f in self.finger_colors}
            self.trial_spans[hl] = []

        ax_top.tick_params(labelbottom=False)
        ax_bot.set_xlabel("경과 시간 (초)", color="#cbd5e1", fontsize=8, fontweight='bold')
        self.fig.tight_layout(pad=0.4)
        self.fig.subplots_adjust(left=0.08, right=0.98, top=0.96, bottom=0.10, hspace=0.08)

    def append_data(self, t, ad):
        if not ad:
            return
        for hl in self.HAND_ORDER:
            if hl in ad:
                hd = ad[hl]['filtered'] if 'filtered' in ad[hl] else ad[hl]
                self.time_bufs[hl].append(t)
                for f in self.finger_colors:
                    self.angle_bufs[hl][f].append(hd.get(f"{f}_Flexion", 180.0))
                self.has_new_data = True

    def render_chart(self):
        if not self.has_new_data:
            return
        self.has_new_data = False

        ts = [self.time_bufs[h][-1] for h in self.HAND_ORDER if len(self.time_bufs[h]) > 0]
        if not ts:
            return
        tn = max(ts)
        xm = max(0.0, tn - 8.0)

        for hl in self.HAND_ORDER:
            if len(self.time_bufs[hl]) > 1:
                ta = np.array(self.time_bufs[hl])
                for f in self.finger_colors:
                    self.lines[hl][f].set_data(ta, np.array(self.angle_bufs[hl][f]))
            self.axes[hl].set_xlim(xm, max(8.0, tn))
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
        self.has_new_data = False
        self.draw_idle()


# ================================================================
# 5-1. 실시간 3D 손 스켈레톤 뷰어
# ================================================================
class Live3DHandChart(FigureCanvas):
    HAND_ORDER = ('Left', 'Right')
    HAND_TITLES = {'Left': '왼손 (Left)', 'Right': '오른손 (Right)'}

    FINGER_BONES = {
        'Thumb':  ([0, 1, 2, 3, 4],       '#ef4444'),
        'Index':  ([0, 5, 6, 7, 8],       '#0ea5e9'),
        'Middle': ([0, 9, 10, 11, 12],    '#22c55e'),
        'Ring':   ([0, 13, 14, 15, 16],   '#f59e0b'),
        'Pinky':  ([0, 17, 18, 19, 20],   '#a855f7'),
    }
    PALM_EDGES = [(0, 1), (1, 5), (5, 9), (9, 13), (13, 17), (17, 0)]
    PALM_POLY_IDX = [0, 1, 5, 9, 13, 17]

    def __init__(self, parent=None, width=6, height=3.8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#131622')
        super().__init__(self.fig)
        self.setParent(parent)

        self.axes = {}
        self.bone_lines = {}
        self.palm_lines = {}
        self.palm_meshes = {}
        self.joint_scatters = {}
        self.has_new_data = False
        self.latest_pts = {}

        for idx, hl in enumerate(self.HAND_ORDER):
            ax = self.fig.add_subplot(1, 2, idx + 1, projection='3d')
            ax.set_facecolor('#141724')
            ax.set_title(self.HAND_TITLES[hl], color='#38bdf8', fontsize=11, fontweight='bold', pad=-6)
            
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-0.8, 0.8)
            ax.set_zlim(-0.15, 1.85)
            ax.set_box_aspect([1.0, 0.7, 1.0])
            
            ax.dist = 5.8
            ax.view_init(elev=10, azim=-90)

            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])
            ax.tick_params(colors='none', length=0)

            ax.xaxis.pane.set_facecolor('#0f121d')
            ax.yaxis.pane.set_facecolor('#0f121d')
            ax.zaxis.pane.set_facecolor('#0f121d')
            ax.xaxis.pane.set_edgecolor('#1e2438')
            ax.yaxis.pane.set_edgecolor('#1e2438')
            ax.zaxis.pane.set_edgecolor('#1e2438')
            ax.grid(True, linestyle=':', color='#242b40', alpha=0.5)

            poly = Poly3DCollection([], alpha=0.35, facecolor='#0284c7', edgecolor='#38bdf8', linewidths=1.2)
            ax.add_collection3d(poly)
            self.palm_meshes[hl] = poly

            self.bone_lines[hl] = {}
            for fname, (indices, color) in self.FINGER_BONES.items():
                ln, = ax.plot([], [], [], color=color, linewidth=4.5, alpha=0.95, solid_capstyle='round')
                self.bone_lines[hl][fname] = (ln, indices)

            self.palm_lines[hl] = []
            for _ in self.PALM_EDGES:
                ln, = ax.plot([], [], [], color='#64748b', linewidth=2.8, alpha=0.75, solid_capstyle='round')
                self.palm_lines[hl].append(ln)

            sc = ax.scatter([], [], [], c='#ffffff', s=55, edgecolors='#38bdf8', linewidths=0.8, alpha=0.95, depthshade=True, zorder=5)
            self.joint_scatters[hl] = sc
            self.axes[hl] = ax

        self.fig.subplots_adjust(left=-0.05, right=1.05, top=0.96, bottom=-0.05, wspace=-0.05)

    def update_hand(self, hl, pts):
        self.latest_pts[hl] = pts
        self.has_new_data = True

    def clear_hand(self, hl):
        if hl in self.latest_pts:
            del self.latest_pts[hl]
            self.palm_meshes[hl].set_verts([])
            for fname, (ln, _) in self.bone_lines[hl].items():
                ln.set_data_3d([], [], [])
            for ln in self.palm_lines[hl]:
                ln.set_data_3d([], [], [])
            self.joint_scatters[hl]._offsets3d = ([], [], [])
            self.has_new_data = True

    def render_chart(self):
        if not self.has_new_data:
            return
        self.has_new_data = False

        for hl in self.HAND_ORDER:
            if hl not in self.latest_pts:
                continue
            pts = self.latest_pts[hl]

            x = pts[:, 0]
            y = pts[:, 2]
            z = -pts[:, 1]

            palm_v = np.column_stack([x[self.PALM_POLY_IDX], y[self.PALM_POLY_IDX], z[self.PALM_POLY_IDX]])
            self.palm_meshes[hl].set_verts([palm_v])

            for fname, (ln, indices) in self.bone_lines[hl].items():
                ix = indices
                ln.set_data_3d(x[ix], y[ix], z[ix])

            for ln, (i, j) in zip(self.palm_lines[hl], self.PALM_EDGES):
                ln.set_data_3d([x[i], x[j]], [y[i], y[j]], [z[i], z[j]])

            self.joint_scatters[hl]._offsets3d = (x, y, z)

        self.draw_idle()

    def reset_chart(self):
        self.latest_pts.clear()
        for hl in self.HAND_ORDER:
            self.palm_meshes[hl].set_verts([])
            for fname, (ln, _) in self.bone_lines[hl].items():
                ln.set_data_3d([], [], [])
            for ln in self.palm_lines[hl]:
                ln.set_data_3d([], [], [])
            self.joint_scatters[hl]._offsets3d = ([], [], [])
        self.has_new_data = False
        self.draw_idle()


# ================================================================
# 6. 메인 GUI 윈도우
# ================================================================
class CapstoneClinicalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 Master-Slave 미러테라피 및 AI 손 기능 평가 시스템 v3.5")
        self.resize(1440, 940)
        self.setMinimumSize(1280, 820)

        # 백그라운드 멀티스레드 풀 초기화
        self.threadpool = QThreadPool()

        self.is_session_active = False
        self.session_start_time = 0.0
        self.session_records = []
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

        # 비디오 워커 스레드
        self.video_worker = VideoWorker(camera_index=0)
        self.video_worker.frame_processed.connect(self.on_frame_ready)
        self.video_worker.start()

        # UI 상태 타이머 (100ms)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_session_timer)
        self.status_timer.start(100)

        # 차트 전용 비동기 렌더링 타이머 (80ms로 최적화)
        self.chart_timer = QTimer(self)
        self.chart_timer.timeout.connect(self._render_active_chart)
        self.chart_timer.start(80)

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
            background-color: #1c2032; border: 1px solid #38bdf8; border-radius: 6px;
            padding: 6px 12px; color: #ffffff; font-size: 13px; font-weight: bold; min-height: 24px;
        }
        QComboBox:hover { background-color: #242a42; border: 1px solid #0ea5e9; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: top right; width: 28px;
            border-left: 1px solid #38bdf8; background-color: #242a42;
            border-top-right-radius: 5px; border-bottom-right-radius: 5px;
        }
        QComboBox QAbstractItemView {
            background-color: #0f172a; color: #ffffff; border: 1px solid #38bdf8;
            border-radius: 6px; padding: 4px; selection-background-color: #0284c7;
            selection-color: #ffffff; outline: none;
        }
        QComboBox QAbstractItemView::item {
            min-height: 30px; padding: 6px 10px; color: #ffffff; font-weight: bold;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #1e293b; color: #38bdf8;
        }

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

        QTabWidget::pane {
            background-color: #141724; border: 1px solid #282f48; border-radius: 6px;
            border-top-left-radius: 0px; top: -1px;
        }
        QTabBar::tab {
            background-color: #1c2032; color: #94a3b8; border: 1px solid #282f48;
            border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px;
            padding: 8px 18px; font-weight: bold; font-size: 12px; min-width: 140px;
        }
        QTabBar::tab:selected {
            background-color: #141724; color: #38bdf8; border-bottom: 2px solid #0284c7;
        }
        QTabBar::tab:hover:!selected { background-color: #242a42; color: #e2e8f0; }
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
            for f in FINGERS:
                self.gauges[hand_label][f].setValue(0)
                self.gauge_labels[hand_label][f].setText(f"{f}: --°")
            return

        title.setText(f"{hn}  ·  인식됨")
        filt = hand_data['filtered'] if isinstance(hand_data, dict) and 'filtered' in hand_data else hand_data
        for f in FINGERS:
            val = filt.get(f"{f}_Flexion", 180.0)
            self.gauges[hand_label][f].setValue(int(val))
            self.gauge_labels[hand_label][f].setText(f"{f}: {val:.1f}°")

    def init_ui(self):
        cw = QWidget(self)
        self.setCentralWidget(cw)
        ml = QHBoxLayout(cw)
        ml.setContentsMargins(12, 12, 12, 12)
        ml.setSpacing(12)

        # 좌측 패널
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

        # 우측 뷰 패널
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
        self.chk_mirror.setChecked(True)
        self.chk_mirror.toggled.connect(self.on_mirror_toggled)
        self.chk_filter = QCheckBox("생체역학 필터")
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda v: self.video_worker.set_filter_mode(v))
        
        self.lbl_fps = QLabel("FPS: -- | Hands: 0 | Cam: --")
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

        self.lbl_video = QLabel("카메라 영상을 연결하는 중입니다...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(320)
        self.lbl_video.setStyleSheet("background-color: #08090e; border-radius: 6px;")
        vcl.addWidget(self.lbl_video)

        gr = QHBoxLayout()
        gr.setSpacing(8)
        self.panel_gauge_left = self._build_gauge_panel('Left')
        self.panel_gauge_right = self._build_gauge_panel('Right')
        gr.addWidget(self.panel_gauge_left)
        gr.addWidget(self.panel_gauge_right)
        vcl.addLayout(gr)
        rl.addWidget(vc, 0)

        # 탭 전환 차트 영역
        self.chart_tabs = QTabWidget()

        # 탭 1: 3D 손 스켈레톤 뷰어
        tab_3d = QWidget()
        tab_3d_layout = QVBoxLayout(tab_3d)
        tab_3d_layout.setContentsMargins(2, 2, 2, 2)
        self.skeleton_chart = Live3DHandChart(self, width=6, height=3.8)
        tab_3d_layout.addWidget(self.skeleton_chart)
        self.chart_tabs.addTab(tab_3d, "🌐  3D 손 스켈레톤 뷰어")

        # 탭 2: 2D 굴곡각 시계열 차트
        tab_2d = QWidget()
        tab_2d_layout = QVBoxLayout(tab_2d)
        tab_2d_layout.setContentsMargins(2, 2, 2, 2)
        self.angle_chart = LiveAngleChart(self, width=6, height=3.8)
        tab_2d_layout.addWidget(self.angle_chart)
        self.chart_tabs.addTab(tab_2d, "📈  굴곡각 시계열 차트 (2D)")

        self.chart_tabs.setCurrentIndex(0)
        rl.addWidget(self.chart_tabs)
        ml.addWidget(rp, stretch=1)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self.handle_space_action)
        QShortcut(QKeySequence(Qt.Key.Key_M), self).activated.connect(
            lambda: self.chk_mirror.setChecked(not self.chk_mirror.isChecked()))
        QShortcut(QKeySequence(Qt.Key.Key_Q), self).activated.connect(self.close)

    def handle_space_action(self):
        if isinstance(self.focusWidget(), QLineEdit):
            return
        if self.is_session_active:
            self.toggle_trial_state()
        else:
            self.start_session()

    def on_subject_type_changed(self):
        ih = self.rb_healthy.isChecked()
        self.group_clinical.setEnabled(not ih)
        self.group_clinical.setTitle("3. 임상 재활 척도 (정상 대조군 - 비활성)" if ih else "3. 임상 재활 척도 (Clinical Scales)")

    def on_mirror_toggled(self, checked):
        self.video_worker.set_mirror_mode(checked)
        self.angle_chart.reset_chart()
        self.skeleton_chart.reset_chart()

    def show_toast(self, msg, is_success=False):
        self.statusBar().showMessage(msg, 5000)

    def start_session(self):
        import re
        sn = re.sub(r'[\\/*?:"<>|]', '_', self.txt_name.text().strip())
        if not sn:
            QMessageBox.warning(self, "입력 오류", "피험자 이름을 먼저 입력해주세요.")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        age = self.spin_age.value()
        gender = "남성" if "남성" in self.cb_gender.currentText() else "여성"

        if self.rb_healthy.isChecked():
            folder_name = f"{ts}_정상인_{sn}_{age}세_{gender}"
        else:
            fma = self.spin_fma.value()
            brs_stage = self.cb_brs.currentIndex() + 1
            folder_name = f"{ts}_환자_{sn}_{age}세_{gender}_FMA{fma}_BRS{brs_stage}"

        self.current_subject_folder = os.path.join(self.base_output_dir, folder_name)
        os.makedirs(self.current_subject_folder, exist_ok=True)

        self.task_folders = {
            "Task 1": os.path.join(self.current_subject_folder, "Task1_맨손_쥐기펴기"),
            "Task 2": os.path.join(self.current_subject_folder, "Task2_원통형_파지"),
            "Task 3": os.path.join(self.current_subject_folder, "Task3_구형_파지"),
            "Task 4": os.path.join(self.current_subject_folder, "Task4_미러테라피")
        }
        for p in self.task_folders.values():
            os.makedirs(p, exist_ok=True)

        self.session_records.clear()
        self.completed_trials.clear()
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
        self.skeleton_chart.reset_chart()

        self.lbl_session_status.setText("● REC (세션 녹화 중)")
        self.lbl_session_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")
        self.lbl_trial_status.setText("준비됨 (파지 시작 대기)")
        self.lbl_trial_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.show_toast(f"▶ 세션 시작: {folder_name}", is_success=True)

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
        if not self.is_session_active:
            return
        tn = time.time() - self.session_start_time
        if not self.is_trial_in_progress:
            self.is_trial_in_progress = True
            self.current_trial_start_t = tn
            self.set_trial_button_ui(False)
            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
            self.show_toast(f"▶ [Trial #{self.current_trial_idx}] 파지 시작!")
        else:
            self.is_trial_in_progress = False
            te, ts = tn, self.current_trial_start_t
            dur = max(0.01, te - ts)
            seg = [r for r in self.session_records if ts <= r['time'] <= te]

            if dur < 0.4 or len(seg) < 10:
                self.set_trial_button_ui(True)
                self.lbl_trial_status.setText("⚠️ 측정 시간 부족 (0.4초 이상 녹화 필요)")
                self.lbl_trial_status.setStyleSheet("color: #f97316; font-weight: bold; font-size: 13px;")
                self.show_toast("⚠️ 측정 시간이 너무 짧아(0.4초 미만) 취소되었습니다.", is_success=False)
                return

            ctf = self.cb_task.currentText()
            ctk = ctf.split(":")[0].strip()
            cts = ctf.split(":")[1].split("(")[0].strip() if ":" in ctf else ctf

            is_patient = self.rb_patient.isChecked()
            affected_text = self.cb_affected.currentText()

            if is_patient and ("좌측" in affected_text or "Left" in affected_text):
                target_hand = 'Left'
            elif is_patient and ("우측" in affected_text or "Right" in affected_text):
                target_hand = 'Right'
            else:
                target_hand = 'Right' if any('Right' in r.get('hands', {}) for r in seg) else 'Left'

            aps = []
            finger_angles = {f: [] for f in FINGERS}
            index_pips = []
            seg_times = []

            for r in seg:
                h_data = r['hands'].get(target_hand)
                if h_data:
                    fa = h_data['filtered']
                    aps.append(fa.get('Grip_Aperture', 0))
                    for f in FINGERS:
                        finger_angles[f].append(fa.get(f"{f}_Flexion", 180.0))
                    index_pips.append(fa.get('Index_PIP', 180.0))
                    seg_times.append(r['time'])

            mga = max(aps) if aps else 0.0
            tarom = sum((max(vals) - min(vals)) for vals in finger_angles.values() if len(vals) > 0)

            # SPARC 연산 전 미분 노이즈 평활화 필터 적용
            if len(index_pips) > 10 and len(seg_times) == len(index_pips):
                t_arr = np.array(seg_times, dtype=np.float64)
                pip_smoothed = smooth_series(index_pips, window_len=5)
                vel = np.gradient(pip_smoothed, t_arr)
                sparc = compute_sparc(vel, time_series=seg_times)
            else:
                sparc = 0.0

            ti = {"trial": self.current_trial_idx, "task_full": ctf, "task_key": ctk, "task_short": cts,
                  "target_hand": target_hand,
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
            
            # 비동기 스레드풀로 저장 태스크 분기 (메인 UI 즉시 응답)
            save_worker = SaveTrialWorker(td, ti, seg)
            self.threadpool.start(save_worker)

            self.current_trial_idx += 1
            self.set_trial_button_ui(True)
            self.lbl_trial_status.setText(f"완료됨 (총 {len(self.completed_trials)}회 기록됨)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.show_toast(f"💾 [{ctk} - Trial #{ti['trial']}] 저장 작업 시작됨", is_success=True)

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
        self.show_toast(f"✅ 세션 마감! 총 {len(self.completed_trials)}회차 저장 완료.", is_success=True)

    def _save_overall(self, dur):
        if not self.session_records:
            return
        oc = os.path.join(self.current_subject_folder, "Session_Overall_Summary.csv")
        with open(oc, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(["Trial", "Task", "Duration_s", "MGA_pct", "TAROM_deg", "SPARC"])
            for tr in self.completed_trials:
                w.writerow([f"Trial #{tr['trial']}", tr.get('task_short', ''), f"{tr['duration']:.2f}",
                            f"{tr['mga']:.2f}", f"{tr['tarom']:.2f}", f"{tr['sparc']:.2f}"])

        mp_path = os.path.join(self.current_subject_folder, "subject_metadata.json")
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
        with open(mp_path, 'w', encoding='utf-8') as f:
            json.dump(md, f, ensure_ascii=False, indent=2)

    def _render_active_chart(self):
        idx = self.chart_tabs.currentIndex()
        if idx == 0:
            self.skeleton_chart.render_chart()
        elif idx == 1:
            self.angle_chart.render_chart()

    def on_frame_ready(self, frame, ad, fps, hc, dev_name):
        self.last_angles = ad
        self.lbl_fps.setText(f"FPS: {fps:.1f}  |  Hands: {hc}  |  {dev_name}")

        ct = self.cb_task.currentText()
        is_mirror_task = "Task 4" in ct
        is_valid_frame = (('Right' in ad) and ('Left' in ad)) if is_mirror_task else bool(ad)

        for hl in Live3DHandChart.HAND_ORDER:
            hd = ad.get(hl)
            if hd and 'pts_3d' in hd:
                self.skeleton_chart.update_hand(hl, hd['pts_3d'])
            else:
                self.skeleton_chart.clear_hand(hl)

        if self.is_session_active:
            if is_valid_frame:
                t = time.time() - self.session_start_time
                self.session_records.append({'time': t, 'task': ct, 'hands': ad})
                self.angle_chart.append_data(t, ad)
                self.btn_trial_toggle.setEnabled(True)
                self._refresh_trial_status_label()
            else:
                msg = "⏸ 미러테라피: 양손 인식 필요" if is_mirror_task else "손을 화면에 비춰주세요"
                col = "#f97316" if is_mirror_task else "#94a3b8"
                self.lbl_trial_status.setText(msg)
                self.lbl_trial_status.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 13px;")

        for hl in LiveAngleChart.HAND_ORDER:
            self._update_gauge_panel(hl, ad.get(hl))

        h, w, ch = frame.shape
        qi = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format.Format_BGR888).copy()
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
        self.chart_timer.stop()
        self.status_timer.stop()
        self.video_worker.stop()
        self.threadpool.waitForDone(1500) # 백그라운드 파일 쓰기 완료 대기
        event.accept()


# ================================================================
# 7. 실행 진입점
# ================================================================
def main():
    app = QApplication(sys.argv)
    window = CapstoneClinicalApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
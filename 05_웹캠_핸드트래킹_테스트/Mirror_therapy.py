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

# ---- Intel RealSense D400 시리즈 (D455 확인됨) ----
try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except Exception:
    rs = None
    REALSENSE_AVAILABLE = False

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
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (projection='3d' 등록용)
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt

# 맑은 고딕 한글 폰트 글로벌 고정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 게이지/차트에서 공통으로 쓰는 손가락 순서
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")

# ---- RealSense 스트림 설정 (진단 스크립트에서 확인된 조합) ----
RS_WIDTH, RS_HEIGHT, RS_FPS = 1280, 720, 30

# Depth 시각화 색상 범위(미터). 이 구간이 파랑~빨강으로 펼쳐짐.
# D455는 최소 측정거리가 약 0.5~0.6m이므로 손을 그보다 멀리 두어야 depth가 잡힙니다.
DEPTH_VIS_MIN_M = 0.4
DEPTH_VIS_MAX_M = 1.5

# 보기 모드
VIEW_COLOR = "color"
VIEW_DEPTH = "depth"
VIEW_BOTH = "both"

# ================================================================
# 0. 3D 좌표 재구성 파라미터 (SVD 손바닥 평면 정규화 방식)
#
#    [변경점] depth 역투영 + Umeyama 정합으로 3D를 만들던 방식을 걷어내고,
#    MediaPipe world landmark를 손바닥 평면(SVD)으로 정렬한 뒤
#    손 길이로 정규화하는 '내인성 3D' 방식으로 교체했습니다.
#      - depth 구멍/노이즈에 전혀 영향받지 않음 (웹캠에서도 3D 동작)
#      - 손 크기·카메라 거리와 무관하게 항상 동일한 스케일로 표시
#      - 앞뒤(Z) 이동 시에도 관절각이 변하지 않음
#    depth는 이제 '손목까지의 거리 표시'와 'depth 품질 로깅'에만 쓰입니다.
# ================================================================
PALM_IDS = (0, 1, 5, 9, 13, 17)     # 손바닥 강체. SVD 평면 피팅에 사용
DEPTH_SAMPLE_WIN = 9                # depth 품질 로깅용 샘플 창(3D 계산에는 미사용)
VIEW3D_RENDER_INTERVAL = 0.15       # 3D 뷰 재그리기 간격(초)
LM_SMOOTH_DEFAULT = True            # 랜드마크 좌표 사전 스무딩 기본값

# 랜드마크 좌표 레벨 One-Euro 설정
# x,y는 적당히, z는 강하게 눌러 단안 깊이 추정 노이즈를 제거한다.
LM_XY_CUTOFF, LM_XY_BETA, LM_XY_DCUT = 0.4, 0.08, 1.2
LM_Z_CUTOFF, LM_Z_BETA, LM_Z_DCUT = 0.15, 0.002, 0.8

# 관절각 정의 (이름 -> 각도를 이루는 세 랜드마크)
JOINT_DEFS = {
    'Thumb_MCP':  (1, 2, 3),
    'Thumb_IP':   (2, 3, 4),
    'Index_MCP':  (0, 5, 6),
    'Index_PIP':  (5, 6, 7),
    'Index_DIP':  (6, 7, 8),
    'Middle_MCP': (0, 9, 10),
    'Middle_PIP': (9, 10, 11),
    'Middle_DIP': (10, 11, 12),
    'Ring_MCP':   (0, 13, 14),
    'Ring_PIP':   (13, 14, 15),
    'Ring_DIP':   (14, 15, 16),
    'Pinky_MCP':  (0, 17, 18),
    'Pinky_PIP':  (17, 18, 19),
    'Pinky_DIP':  (18, 19, 20),
}

# 3D 각도 중 CSV/화면에 대표로 남길 굴곡각
FLEX_JOINT_OF = {
    'Thumb': 'Thumb_IP', 'Index': 'Index_PIP', 'Middle': 'Middle_PIP',
    'Ring': 'Ring_PIP', 'Pinky': 'Pinky_PIP',
}

# 3D 재구성 상태 표시용
MODE_LABEL = {
    'kinematic':  '정규화 3D',       # SVD 손바닥 정렬 + 손 길이 정규화 (기본)
    'raw':        '원본 3D',         # 좌표 스무딩 없이 world landmark 그대로
}
MODE_COLOR = {
    'kinematic': '#10b981', 'raw': '#f59e0b',
}


# ================================================================
# 1. One-Euro 필터 및 4단계 하이브리드 생체역학 필터
# ================================================================
class OneEuroFilter:
    def __init__(self, t0=None, x0=180.0, dx0=0.0, min_cutoff=0.7, beta=0.015, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)  # 정지 상태 컷오프 (지터 완전 억제)
        self.beta = float(beta)              # 속도 가중치 (빠른 움직임 래그 0 추종)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)
        self.t_prev = t0                     # None이면 첫 호출 시각으로 초기화

    def smoothing_factor(self, t_e, cutoff):
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    def exponential_smoothing(self, a, x, x_prev):
        return a * x + (1 - a) * x_prev

    def filter(self, t, x):
        if self.t_prev is None:
            self.t_prev = t
            self.x_prev = float(x)
            return float(x)

        t_e = t - self.t_prev
        if t_e <= 1e-5:
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


class LandmarkSmoother:
    """21개 랜드마크의 (x,y,z) 좌표 각각에 One-Euro 필터를 적용.

    좌표를 먼저 평활화한 뒤 각도를 계산하면 arccos의 비선형성에 의한
    양자화 증폭(계단형 스텝)이 방지된다.
    """

    def __init__(self):
        self.filters = [
            [
                OneEuroFilter(min_cutoff=LM_XY_CUTOFF, beta=LM_XY_BETA, d_cutoff=LM_XY_DCUT),  # x
                OneEuroFilter(min_cutoff=LM_XY_CUTOFF, beta=LM_XY_BETA, d_cutoff=LM_XY_DCUT),  # y
                OneEuroFilter(min_cutoff=LM_Z_CUTOFF, beta=LM_Z_BETA, d_cutoff=LM_Z_DCUT),     # z
            ]
            for _ in range(21)
        ]

    def smooth(self, t, pts):
        """pts: (21,3) numpy array -> smoothed (21,3) array"""
        smoothed = np.empty_like(pts)
        for i in range(21):
            for j in range(3):
                smoothed[i, j] = self.filters[i][j].filter(t, float(pts[i, j]))
        return smoothed


class HybridKinematicFilter:
    def __init__(self, init_val=180.0):
        self.val = float(init_val)
        self.last_valid_val = float(init_val)
        self.missing_count = 0
        self.max_missing_hold = 12  # 최대 0.4초간 가려짐 홀딩
        self.euro_filter = OneEuroFilter(t0=0.0, x0=init_val, min_cutoff=0.7, beta=0.015)
        self.max_deg_per_frame = 30.0  # 프레임당 최대 30도 회전 속도 제한

    def update(self, t, raw_val, hold_motion=False):
        # 팔 전체가 이동/회전하는 "글로벌 모션" 구간에서는 값 갱신을 보류하고 직전 값을 유지
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
# 2. SVD 다점 평면 피팅 & 3D 내인성 관절각 연산
#    (기존 depth 역투영 + Umeyama 정합을 대체하는 3D 좌표 방식)
# ================================================================
def compute_robust_palm_frame(pts):
    """손바닥 6점으로 SVD 평면을 피팅해 손 고유 좌표계(R)를 만들고,
    손목을 원점으로 손 길이(손목~중지MCP)로 나눠 스케일을 정규화한다.

    반환: (정규화 좌표 21x3, 손바닥 중심, 회전행렬 R)
    """
    palm_pts = pts[list(PALM_IDS)]
    centroid = np.mean(palm_pts, axis=0)
    shifted = palm_pts - centroid

    _, _, vt = np.linalg.svd(shifted)
    normal = vt[2]

    # 법선 방향을 손등/손바닥 기준으로 일관되게 고정
    ref_norm = np.cross(pts[5] - pts[0], pts[17] - pts[0])
    if np.dot(normal, ref_norm) < 0:
        normal = -normal

    v_y = pts[9] - pts[0]
    ny = float(np.linalg.norm(v_y))
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
    """numpy 3D 점 세 개가 이루는 각도(도). b가 꼭짓점."""
    ba = pa - pb
    bc = pc - pb
    n1, n2 = np.linalg.norm(ba), np.linalg.norm(bc)
    if n1 < 1e-7 or n2 < 1e-7:
        return 180.0
    cos_v = np.clip(np.dot(ba, bc) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_v)))


def compute_angles_and_pts(landmarks):
    """랜드마크(객체 리스트 또는 (21,3) 배열) -> (관절각 dict, 정규화 좌표, 중심, R)"""
    if isinstance(landmarks, np.ndarray):
        pts_raw = landmarks.astype(np.float64)
    else:
        pts_raw = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float64)

    pts, centroid, R = compute_robust_palm_frame(pts_raw)

    a = {}
    for name, (i, j, k) in JOINT_DEFS.items():
        a[name] = calc_angle_3d(pts[i], pts[j], pts[k])

    for finger, joint in FLEX_JOINT_OF.items():
        a[f"{finger}_Flexion"] = a[joint]

    # 손 길이로 정규화된 파지폭(%). 손 크기·거리와 무관한 지표
    a['Grip_Aperture'] = float(np.linalg.norm(pts[4] - pts[8]) * 100.0)

    return a, pts, centroid, R


# ================================================================
# 3. 2D(원본 world landmark) 관절 각도 계산 유틸 (게이지/시계열용)
# ================================================================
def calculate_angle_3d(a, b, c):
    pa = np.array([a.x, a.y, a.z])
    pb = np.array([b.x, b.y, b.z])
    pc = np.array([c.x, c.y, c.z])
    return calc_angle_3d(pa, pb, pc)


def calculate_aperture(lm):
    p_thumb = np.array([lm[4].x, lm[4].y, lm[4].z])
    p_index = np.array([lm[8].x, lm[8].y, lm[8].z])
    return float(np.linalg.norm(p_thumb - p_index) * 100.0)


def compute_all_finger_angles(landmarks):
    angles = {}
    for name, (i, j, k) in JOINT_DEFS.items():
        angles[name] = calculate_angle_3d(landmarks[i], landmarks[j], landmarks[k])

    # 주요 굴곡각
    for finger, joint in FLEX_JOINT_OF.items():
        angles[f"{finger}_Flexion"] = angles[joint]
    angles['Grip_Aperture'] = calculate_aperture(landmarks)

    return angles


# ================================================================
# 4. 비디오 캡처 및 MediaPipe 백그라운드 추론 스레드
#    RealSense color + depth 동시 스트리밍, depth 화면 시각화 지원
#    3D 좌표는 SVD 손바닥 정규화 방식으로 산출 (depth 비의존)
# ================================================================
class VideoWorker(QThread):
    # frame(표시용 BGR), angles, fps, hand_count, 손목거리 dict, 3D 재구성 dict
    frame_processed = pyqtSignal(np.ndarray, dict, float, int, dict, dict)

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
        self.global_motion_translation_thresh = 0.020
        self.global_motion_rotation_thresh_deg = 10.0

        # ---- RealSense / 표시 상태 ----
        self.source_name = "webcam"     # 'realsense' 또는 'webcam'
        self.view_mode = VIEW_COLOR     # 화면에 무엇을 보여줄지
        self.depth_scale = 1.0          # depth 원시값 -> 미터
        self.latest_depth = None        # 화면 표시용 (미러링 적용됨)
        self.latest_depth_raw = None    # 미러링 전 원본 (거리 로깅 전용)
        self.color_intrinsics = None    # 손목 위치 역투영(로깅용)에만 사용
        self.depth_filters = None       # RealSense 후처리 필터 체인

        # ---- 3D (SVD 정규화) 상태 ----
        self.landmark_smoothers = {}    # 손별 랜드마크 좌표 One-Euro
        self.smooth_3d = LM_SMOOTH_DEFAULT
        self.enable_3d = True           # 3D 재구성 on/off (성능 조절용)

    def set_mirror_mode(self, enabled):
        self.mirror_mode = enabled
        self.filters = {}
        self.prev_palm_state = {}
        self.landmark_smoothers = {}

    def set_filter_mode(self, enabled):
        self.use_filter = enabled

    def set_view_mode(self, mode):
        """'color' / 'depth' / 'both'"""
        self.view_mode = mode

    def set_enable_3d(self, enabled):
        self.enable_3d = enabled
        self.landmark_smoothers = {}

    def set_smooth_3d(self, enabled):
        """3D 좌표 스무딩(랜드마크 레벨 One-Euro) on/off"""
        self.smooth_3d = enabled
        self.landmark_smoothers = {}

    # ------------------------------------------------------------
    # RealSense 파이프라인
    # ------------------------------------------------------------
    def _open_realsense(self):
        if not REALSENSE_AVAILABLE:
            print("[안내] pyrealsense2 미설치 → 일반 웹캠으로 동작합니다.")
            return None
        try:
            if len(rs.context().query_devices()) == 0:
                print("[안내] 연결된 RealSense 장치가 없습니다 → 웹캠으로 폴백합니다.")
                return None

            pipeline = rs.pipeline()
            cfg = rs.config()
            cfg.enable_stream(rs.stream.color, RS_WIDTH, RS_HEIGHT, rs.format.bgr8, RS_FPS)
            cfg.enable_stream(rs.stream.depth, RS_WIDTH, RS_HEIGHT, rs.format.z16, RS_FPS)
            profile = pipeline.start(cfg)

            device = profile.get_device()
            depth_sensor = device.first_depth_sensor()
            self.depth_scale = float(depth_sensor.get_depth_scale())

            try:
                if depth_sensor.supports(rs.option.visual_preset):
                    depth_sensor.set_option(rs.option.visual_preset,
                                            float(rs.rs400_visual_preset.high_accuracy))
            except Exception:
                pass

            align = rs.align(rs.stream.color)   # depth를 컬러 좌표계에 정렬

            # depth 구멍(측정 실패 픽셀)을 줄이는 후처리 체인.
            # 3D 좌표 산출에는 더 이상 쓰이지 않지만, Depth 화면과 손목 거리 표시 품질을 위해 유지.
            spat = rs.spatial_filter()
            spat.set_option(rs.option.filter_magnitude, 2)
            spat.set_option(rs.option.filter_smooth_alpha, 0.5)
            spat.set_option(rs.option.filter_smooth_delta, 20)
            spat.set_option(rs.option.holes_fill, 1)   # 1 = 아주 작은 구멍만
            temp = rs.temporal_filter()
            temp.set_option(rs.option.filter_smooth_alpha, 0.4)
            temp.set_option(rs.option.filter_smooth_delta, 20)
            self.depth_filters = [spat, temp]

            print(f"[RealSense] {device.get_info(rs.camera_info.name)} 연결됨 | "
                  f"{RS_WIDTH}x{RS_HEIGHT}@{RS_FPS} | depth_scale={self.depth_scale}")

            for _ in range(15):     # 자동 노출 안정화
                pipeline.wait_for_frames()

            self.source_name = "realsense"
            return pipeline, align
        except Exception as e:
            print(f"[경고] RealSense 초기화 실패 ({e}) → 웹캠으로 폴백합니다.")
            return None

    # ------------------------------------------------------------
    # Depth 시각화 / 거리 조회
    # ------------------------------------------------------------
    def _colorize_depth(self, depth_m):
        """미터 단위 depth 맵을 컬러맵 이미지(BGR)로 변환.
        DEPTH_VIS_MIN_M~MAX_M 범위를 고정으로 쓰기 때문에 프레임마다 색이 요동치지 않음.
        측정 실패(0) 픽셀은 검정으로 표시 -> 어디가 사각지대인지 바로 보임."""
        valid = depth_m > 0.0
        norm = np.clip((depth_m - DEPTH_VIS_MIN_M) / (DEPTH_VIS_MAX_M - DEPTH_VIS_MIN_M), 0.0, 1.0)
        gray = ((1.0 - norm) * 255.0).astype(np.uint8)   # 가까울수록 밝게
        vis = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        vis[~valid] = (0, 0, 0)
        return vis

    @staticmethod
    def _sample_depth(depth_map, px, py, win):
        """depth_map(미터)에서 (px,py) 주변 win x win 중앙값. 유효값 없으면 None."""
        if depth_map is None:
            return None
        h, w = depth_map.shape[:2]
        x, y = int(round(px)), int(round(py))
        r = win // 2
        x0, x1 = max(0, x - r), min(w, x + r + 1)
        y0, y1 = max(0, y - r), min(h, y + r + 1)
        if x0 >= x1 or y0 >= y1:
            return None
        patch = depth_map[y0:y1, x0:x1]
        vals = patch[patch > 0.0]
        if vals.size == 0:
            return None
        return float(np.median(vals))

    def get_depth_meters(self, px, py, win=5):
        """화면에 보이는 영상 기준 픽셀의 거리(미터). 화면 오버레이 표기용."""
        return self._sample_depth(self.latest_depth, px, py, win)

    def _depth_hit_pct(self, hand_lms, img_w, img_h):
        """21개 랜드마크 위치에서 depth가 잡힌 비율(%). 품질 로깅 전용."""
        if self.latest_depth_raw is None:
            return None
        hit = 0
        for lm in hand_lms.landmark:
            x = lm.x * img_w
            y = lm.y * img_h
            if self.mirror_mode:
                x = (img_w - 1.0) - x
            if self._sample_depth(self.latest_depth_raw, x, y, DEPTH_SAMPLE_WIN):
                hit += 1
        return float(hit / 21.0 * 100.0)

    # ------------------------------------------------------------
    # 3D 관절 재구성 (SVD 손바닥 정규화)
    # ------------------------------------------------------------
    def reconstruct_hand_3d(self, hand_label, hand_lms, world_lm,
                            img_w, img_h, t_sec, wrist_depth=None):
        """MediaPipe world landmark -> 손바닥 좌표계 정렬 + 손 길이 정규화 3D.

        1) 랜드마크 (x,y,z)에 One-Euro를 걸어 z 노이즈/양자화 떨림 제거
        2) 손바닥 6점 SVD 평면으로 손 고유 좌표계(R) 산출
        3) 손목 원점 · 손 길이 1.0 로 정규화 -> 관절각 계산 (거리/손크기 불변)
        4) 표시용 좌표는 R.T 로 손바닥 자세를 되살려 실제 손 방향 그대로 렌더링

        depth는 3D 좌표에 관여하지 않으며, 손목 거리/품질 로깅에만 쓰인다.
        """
        if (not self.enable_3d) or world_lm is None:
            return None

        pts_raw = np.array([[lm.x, lm.y, lm.z] for lm in world_lm], dtype=np.float64)
        if self.smooth_3d:
            if hand_label not in self.landmark_smoothers:
                self.landmark_smoothers[hand_label] = LandmarkSmoother()
            pts = self.landmark_smoothers[hand_label].smooth(t_sec, pts_raw)
            mode = 'kinematic'
        else:
            pts = pts_raw
            mode = 'raw'

        angles3d, norm_pts, centroid, R = compute_angles_and_pts(pts)

        # 손바닥 자세를 복원한 표시용 좌표 (손목 원점, 손 길이 = 1.0)
        points = (R.T @ norm_pts.T).T
        if not np.all(np.isfinite(points)):
            return None

        # 실제 물리 크기 지표는 world landmark(미터)에서 직접 산출
        palm_len_mm = float(np.linalg.norm(pts[9] - pts[0]) * 1000.0)
        aperture_mm = float(np.linalg.norm(pts[4] - pts[8]) * 1000.0)

        # 손목의 카메라 좌표(미터). depth가 있을 때만 로깅용으로 채운다.
        wrist_point = None
        if self.color_intrinsics is not None and wrist_depth:
            wx = hand_lms.landmark[0].x * img_w
            wy = hand_lms.landmark[0].y * img_h
            if self.mirror_mode:
                wx = (img_w - 1.0) - wx
            X, Y, Z = rs.rs2_deproject_pixel_to_point(
                self.color_intrinsics, [float(wx), float(wy)], float(wrist_depth))
            wrist_point = (float(X), float(Y), float(Z))

        # 모든 관절이 모델 기반이므로 전부 유효점으로 취급
        valid = np.ones(21, dtype=bool)

        return {
            'points': points,
            'valid': valid,
            'angles': angles3d,
            'norm_points': norm_pts,
            'mode': mode,
            'metrics': {
                'mode': mode,
                'wrist_dist_m': wrist_depth,
                'wrist_point': wrist_point,
                'aperture_mm': aperture_mm,
                'aperture_norm': angles3d.get('Grip_Aperture'),
                'palm_len_mm': palm_len_mm,
                'valid_pct': 100.0,
                'raw_hit_pct': self._depth_hit_pct(hand_lms, img_w, img_h),
                'fit_rmse_mm': None,
            }
        }

    def run(self):
        pipeline = None
        align = None
        cap = None

        rs_result = self._open_realsense()
        if rs_result is not None:
            pipeline, align = rs_result
        else:
            self.source_name = "webcam"
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"[에러] 카메라 {self.camera_index}번을 열 수 없습니다.")
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, RS_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RS_HEIGHT)

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
            # ---------------- 프레임 획득 ----------------
            if pipeline is not None:
                try:
                    frames = pipeline.wait_for_frames(timeout_ms=2000)
                except Exception:
                    time.sleep(0.01)
                    continue

                aligned = align.process(frames)
                color_frame = aligned.get_color_frame()
                depth_frame = aligned.get_depth_frame()
                if not color_frame:
                    time.sleep(0.01)
                    continue

                if depth_frame and self.depth_filters:
                    try:
                        for filt in self.depth_filters:
                            depth_frame = filt.process(depth_frame)
                    except Exception:
                        pass

                frame = np.asanyarray(color_frame.get_data()).copy()   # bgr8이라 그대로 사용
                if depth_frame:
                    dm = (np.asanyarray(depth_frame.get_data()).astype(np.float32)
                          * self.depth_scale)
                    self.latest_depth_raw = dm      # 거리 로깅은 항상 원본 좌표계에서
                    self.latest_depth = dm
                    if self.color_intrinsics is None:
                        # depth를 컬러에 정렬했으므로 이 프로파일의 intrinsics = 컬러 카메라 것
                        self.color_intrinsics = (depth_frame.profile
                                                 .as_video_stream_profile().intrinsics)
                else:
                    self.latest_depth = None
                    self.latest_depth_raw = None
            else:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue
                self.latest_depth = None
                self.latest_depth_raw = None

            curr_t = time.time()
            fps = 1.0 / (curr_t - prev_t) if (curr_t - prev_t) > 0 else 30.0
            prev_t = curr_t
            t_sec = curr_t - self.start_time

            if self.mirror_mode:
                frame = cv2.flip(frame, 1)
                if self.latest_depth is not None:
                    # 컬러를 뒤집으면 depth도 같이 뒤집어야 픽셀 대응이 유지됨
                    self.latest_depth = cv2.flip(self.latest_depth, 1)

            # ---------------- MediaPipe 추론 (항상 컬러 영상 기준) ----------------
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = hands.process(rgb)
            rgb.flags.writeable = True

            # ---------------- 표시용 캔버스 준비 ----------------
            has_depth = self.latest_depth is not None
            mode = self.view_mode if has_depth else VIEW_COLOR

            depth_vis = self._colorize_depth(self.latest_depth) if has_depth else None
            canvases = []                       # 랜드마크를 그려 넣을 이미지들
            if mode in (VIEW_COLOR, VIEW_BOTH):
                canvases.append(frame)
            if mode in (VIEW_DEPTH, VIEW_BOTH):
                canvases.append(depth_vis)

            hand_count = 0
            latest_angles = {}
            wrist_depths = {}
            hands3d = {}

            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
                world_landmarks_list = results.multi_hand_world_landmarks

                for hand_idx, hand_lms in enumerate(results.multi_hand_landmarks):
                    hand_label = "Hand"
                    if results.multi_handedness and hand_idx < len(results.multi_handedness):
                        hand_label = results.multi_handedness[hand_idx].classification[0].label
                        # MediaPipe는 "입력 영상이 미러링(셀피)되어 있다"고 가정하고 handedness를 판정한다.
                        #  - 미러링 ON  : cv2.flip으로 이미 셀피 영상 -> 라벨이 맞음 -> 그대로 사용
                        #  - 미러링 OFF : RealSense 원본(비반전) -> 라벨이 뒤집힘 -> 스왑 필요
                        if not self.mirror_mode:
                            hand_label = "Right" if hand_label == "Left" else "Left"

                    # 컬러/Depth 화면 양쪽에 동일한 스켈레톤을 그림
                    for canvas in canvases:
                        mp_drawing.draw_landmarks(
                            canvas,
                            hand_lms,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )

                    # 손목 지점의 실측 거리(미터)를 조회해서 화면에 표기
                    h_img, w_img = frame.shape[:2]
                    wx = hand_lms.landmark[0].x * w_img
                    wy = hand_lms.landmark[0].y * h_img
                    dist_m = self.get_depth_meters(wx, wy, win=9)
                    wrist_depths[hand_label] = dist_m

                    if dist_m is not None:
                        txt = f"{hand_label}  {dist_m:.2f} m"
                        color_txt = (0, 255, 0)
                    else:
                        txt = f"{hand_label}  depth --"
                        color_txt = (0, 165, 255)
                    for canvas in canvases:
                        cv2.putText(canvas, txt, (int(wx) - 60, max(24, int(wy) - 16)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
                        cv2.putText(canvas, txt, (int(wx) - 60, max(24, int(wy) - 16)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_txt, 2, cv2.LINE_AA)

                    if world_landmarks_list and hand_idx < len(world_landmarks_list):
                        calc_landmarks = world_landmarks_list[hand_idx].landmark
                    else:
                        calc_landmarks = hand_lms.landmark

                    # ---- 3D 관절 재구성 (SVD 손바닥 정규화) ----
                    rec3d = self.reconstruct_hand_3d(
                        hand_label, hand_lms,
                        world_landmarks_list[hand_idx].landmark
                        if (world_landmarks_list and hand_idx < len(world_landmarks_list)) else None,
                        w_img, h_img, t_sec, dist_m)
                    if rec3d is not None:
                        hands3d[hand_label] = rec3d
                        m3 = rec3d['metrics']
                        sub = f"3D {MODE_LABEL.get(rec3d['mode'], '')}"
                        if m3['aperture_mm'] is not None:
                            sub += f"  A={m3['aperture_mm']:.0f}mm"
                        if m3['raw_hit_pct'] is not None:
                            sub += f"  D{m3['raw_hit_pct']:.0f}%"
                        sub_col = MODE_COLOR.get(rec3d['mode'], '#94a3b8')
                        bgr = (0, 255, 0) if rec3d['mode'] == 'kinematic' else (0, 165, 255)
                        for canvas in canvases:
                            cv2.putText(canvas, sub, (int(wx) - 60, max(44, int(wy) + 8)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
                            cv2.putText(canvas, sub, (int(wx) - 60, max(44, int(wy) + 8)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr, 2, cv2.LINE_AA)

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

            # ---------------- 최종 표시 이미지 합성 ----------------
            display = self._compose_display(mode, frame, depth_vis)
            self.frame_processed.emit(display, latest_angles, fps, hand_count, wrist_depths, hands3d)

        # ---------------- 정리 ----------------
        if pipeline is not None:
            try:
                pipeline.stop()
            except Exception:
                pass
        if cap is not None:
            cap.release()
        hands.close()

    def _compose_display(self, mode, color_img, depth_vis):
        """보기 모드에 따라 실제로 화면에 뿌릴 이미지를 만든다."""
        if mode == VIEW_DEPTH and depth_vis is not None:
            out = depth_vis
            self._label_panel(out, "DEPTH")
            return out

        if mode == VIEW_BOTH and depth_vis is not None:
            left = color_img.copy()
            right = depth_vis.copy()
            self._label_panel(left, "COLOR")
            self._label_panel(right, "DEPTH")
            both = cv2.hconcat([left, right])
            # 가로 2배가 되므로 절반으로 줄여서 전송량을 원래 수준으로 유지
            return cv2.resize(both, (both.shape[1] // 2, both.shape[0] // 2),
                              interpolation=cv2.INTER_AREA)

        return color_img

    @staticmethod
    def _label_panel(img, text):
        cv2.putText(img, text, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(img, text, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    def _compute_palm_state(self, world_lm):
        """손목·검지MCP·새끼MCP로 손바닥의 위치/방향(법선벡터)을 계산."""
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
        """팔 전체가 이동/회전하는 구간을 감지. True면 이번 프레임 각도 갱신 보류."""
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

    def stop(self):
        self.running = False
        self.wait(2000)


# ================================================================
# 5. 실시간 Matplotlib 5손가락 각도 그래프 캔버스
# ================================================================
class LiveAngleChart(FigureCanvas):
    """오른손/왼손 5손가락 굴곡각을 위아래 2단 서브플롯으로 동시에 표시"""

    HAND_ORDER = ('Right', 'Left')
    HAND_TITLES = {'Right': '오른손 (Right)', 'Left': '왼손 (Left)'}

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

        self._render_interval = 0.1  # 약 10Hz 재그리기
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

        if self._last_render_t is not None and (t - self._last_render_t) < self._render_interval:
            return
        self._last_render_t = t

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
# 5-B. 실시간 3D 손 골격 뷰 (SVD 손바닥 정규화 좌표)
# ================================================================
class Hand3DView(FigureCanvas):
    """오른손과 왼손을 각각 독립된 3D 공간(서브플롯 2개)에 그린다.

    좌표는 손목이 원점이고 손 길이(손목~중지MCP)가 1.0인 정규화 좌표이므로
    카메라 거리·손 크기와 무관하게 항상 같은 크기로 보인다.
    화면축은 (X, Z, -Y)로 매핑해 위쪽이 위로 오게 한다.
    """

    HAND_COLORS = {'Right': '#0ea5e9', 'Left': '#f59e0b'}
    PANEL_ORDER = ('Right', 'Left')

    # 손가락별 뼈대 연결 및 색상
    FINGER_BONES = {
        'Thumb':  ([0, 1, 2, 3, 4],      '#ef4444'),
        'Index':  ([0, 5, 6, 7, 8],      '#0ea5e9'),
        'Middle': ([0, 9, 10, 11, 12],   '#22c55e'),
        'Ring':   ([0, 13, 14, 15, 16],  '#f59e0b'),
        'Pinky':  ([0, 17, 18, 19, 20],  '#a855f7'),
    }
    PALM_EDGES = [(0, 1), (1, 5), (5, 9), (9, 13), (13, 17), (17, 0)]
    PALM_POLY_IDX = [0, 1, 5, 9, 13, 17]

    def __init__(self, parent=None, width=6, height=4.2, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#131622')
        super().__init__(self.fig)
        self.setParent(parent)

        self.axes = {}
        self.bone_lines = {}      # {hand: {finger: (Line3D, indices)}}
        self.palm_lines = {}      # {hand: [Line3D, ...]}
        self.palm_meshes = {}     # {hand: Poly3DCollection}
        self.joint_scatters = {}  # {hand: PathCollection3D}
        self.titles = {}

        for i, hand in enumerate(self.PANEL_ORDER):
            ax = self.fig.add_subplot(1, 2, i + 1, projection='3d')
            ax.set_facecolor('#141724')

            # 정규화 좌표이므로 축 범위를 고정한다 (손이 항상 같은 크기로 보임)
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-0.8, 0.8)
            ax.set_zlim(-0.15, 1.85)
            ax.set_box_aspect([1.0, 0.7, 1.0])
            try:
                ax.dist = 5.8   # matplotlib 3.8+ 에서는 무시됨
            except Exception:
                pass
            ax.view_init(elev=10, azim=-90)

            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])
            ax.tick_params(colors='none', length=0)

            for pane_axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                pane_axis.pane.set_facecolor('#0f121d')
                pane_axis.pane.set_edgecolor('#1e2438')
            ax.grid(True, linestyle=':', color='#242b40', alpha=0.5)

            # 손바닥 반투명 면 (앞/뒤 착시 제거)
            poly = Poly3DCollection([], alpha=0.35, facecolor='#0284c7',
                                    edgecolor='#38bdf8', linewidths=1.2)
            ax.add_collection3d(poly)
            self.palm_meshes[hand] = poly

            self.bone_lines[hand] = {}
            for fname, (indices, color) in self.FINGER_BONES.items():
                ln, = ax.plot([], [], [], color=color, linewidth=4.5,
                              alpha=0.95, solid_capstyle='round')
                self.bone_lines[hand][fname] = (ln, indices)

            self.palm_lines[hand] = []
            for _ in self.PALM_EDGES:
                ln, = ax.plot([], [], [], color='#64748b', linewidth=2.6,
                              alpha=0.75, solid_capstyle='round')
                self.palm_lines[hand].append(ln)

            self.joint_scatters[hand] = ax.scatter(
                [], [], [], c='#ffffff', s=48, edgecolors='#38bdf8',
                linewidths=0.8, alpha=0.95, depthshade=True)

            self.titles[hand] = ax.set_title(
                f"{LiveAngleChart.HAND_TITLES[hand]}  ·  대기",
                color="#64748b", fontsize=9, fontweight='bold', pad=2)

            self.axes[hand] = ax

        self._last_render_t = None
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.02, wspace=0.02)

    @staticmethod
    def _to_plot_axes(P):
        """정규화 좌표(X,Y,Z) -> 화면 좌표(X, Z, -Y)"""
        return P[:, 0], P[:, 2], -P[:, 1]

    def _clear_hand(self, hand):
        self.palm_meshes[hand].set_verts([])
        for fname, (ln, _) in self.bone_lines[hand].items():
            ln.set_data_3d([], [], [])
        for ln in self.palm_lines[hand]:
            ln.set_data_3d([], [], [])
        self.joint_scatters[hand]._offsets3d = ([], [], [])

    def update_hands(self, t, hands3d):
        if self._last_render_t is not None and (t - self._last_render_t) < VIEW3D_RENDER_INTERVAL:
            return
        self._last_render_t = t

        for hand in self.PANEL_ORDER:
            name = LiveAngleChart.HAND_TITLES[hand]
            rec = hands3d.get(hand)

            if rec is None:
                self._clear_hand(hand)
                self.titles[hand].set_text(f"{name}  ·  3D 없음")
                self.titles[hand].set_color("#64748b")
                continue

            x, y, z = self._to_plot_axes(rec['points'])

            palm_v = np.column_stack([x[self.PALM_POLY_IDX],
                                      y[self.PALM_POLY_IDX],
                                      z[self.PALM_POLY_IDX]])
            self.palm_meshes[hand].set_verts([palm_v])

            for fname, (ln, idx) in self.bone_lines[hand].items():
                ln.set_data_3d(x[idx], y[idx], z[idx])

            for ln, (a, b) in zip(self.palm_lines[hand], self.PALM_EDGES):
                ln.set_data_3d([x[a], x[b]], [y[a], y[b]], [z[a], z[b]])

            self.joint_scatters[hand]._offsets3d = (x, y, z)

            m3 = rec['metrics']
            mode = rec.get('mode', 'kinematic')
            txt = f"{name}  ·  {MODE_LABEL.get(mode, mode)}"
            if m3.get('aperture_mm') is not None:
                txt += f"  ·  파지폭 {m3['aperture_mm']:.0f}mm"
            if m3.get('wrist_dist_m'):
                txt += f"  ·  {m3['wrist_dist_m']:.2f}m"
            self.titles[hand].set_text(txt)
            self.titles[hand].set_color(MODE_COLOR.get(mode, "#94a3b8"))

        self.draw_idle()

    def reset_view(self):
        for hand in self.PANEL_ORDER:
            self._clear_hand(hand)
            self.titles[hand].set_text(f"{LiveAngleChart.HAND_TITLES[hand]}  ·  대기")
            self.titles[hand].set_color("#64748b")
        self._last_render_t = None
        self.draw_idle()


# ================================================================
# 6. 메인 GUI 윈도우 (2-State 파지 시작/완료 구간 트래킹)
# ================================================================
class CapstoneClinicalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 Master-Slave 미러테라피 및 손 기능 평가 시스템 (SVD 정규화 3D)")
        self.resize(1660, 980)
        self.setMinimumSize(1400, 860)

        self.is_session_active = False
        self.session_start_time = 0.0
        self.session_records = []

        self.is_trial_in_progress = False
        self.current_trial_idx = 1
        self.current_trial_start_t = 0.0
        self.completed_trials = []

        self.current_subject_folder = ""
        self.last_angles = {}
        self.last_hands3d = {}
        self.app_start_time = time.time()
        self.measurement_paused = False

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
        """가독성을 극대화한 선명하고 현대적인 다크 QSS 스타일시트"""
        qss = """
        * {
            font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        QMainWindow { background-color: #0b0d14; }
        QWidget { color: #f8fafc; }
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
        QLabel { color: #e2e8f0; font-size: 13px; font-weight: 500; }
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
        QComboBox:hover { border: 1px solid #38bdf8; }
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
        QTableWidget::item { padding: 4px; }
        QTableWidget::item:selected { background-color: #2563eb; color: white; }
        QPushButton {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 13px;
        }
        QPushButton:hover { background-color: #1d4ed8; }
        QPushButton:pressed { background-color: #1e40af; }
        QPushButton:disabled { background-color: #2d3348; color: #64748b; }
        #btn_session_start {
            background-color: #059669; color: #ffffff;
            font-size: 14px; font-weight: bold; min-height: 38px;
        }
        #btn_session_start:hover { background-color: #10b981; }
        #btn_trial_toggle {
            background-color: #0284c7; color: #ffffff;
            font-size: 15px; font-weight: bold; min-height: 48px;
            border-radius: 6px; border: 2px solid #38bdf8;
        }
        #btn_trial_toggle:hover { background-color: #0369a1; }
        #btn_trial_toggle:disabled {
            background-color: #2d3348; border: 1px solid #3b4566; color: #64748b;
        }
        #btn_session_stop {
            background-color: #dc2626; color: #ffffff;
            font-size: 14px; font-weight: bold; min-height: 38px;
        }
        #btn_session_stop:hover { background-color: #ef4444; }
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
        QProgressBar::chunk { background-color: #0ea5e9; border-radius: 3px; }
        QCheckBox {
            color: #e2e8f0; font-size: 13px; font-weight: bold; spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px; height: 18px; border-radius: 4px;
            border: 1px solid #475569; background-color: #1c2032;
        }
        QCheckBox::indicator:checked {
            background-color: #38bdf8; border: 1px solid #38bdf8;
        }
        """
        self.setStyleSheet(qss)

    # ------------------------------------------------------------
    # 양손 게이지 패널 생성/갱신
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

    def _update_gauge_panel(self, hand_label, hand_data, dist_m=None):
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

        dist_txt = f"{dist_m:.2f} m" if dist_m else "depth --"
        title.setText(f"{hand_name}  ·  인식됨  ·  {dist_txt}")
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

        # ---------------- 좌측 패널 ----------------
        left_panel = QWidget()
        left_panel.setFixedWidth(440)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

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

        group_ctrl = QGroupBox("5. 파지 구간 (시작/완료) 측정 제어")
        gctrl_layout = QVBoxLayout(group_ctrl)
        gctrl_layout.setSpacing(8)

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

        self.btn_trial_toggle = QPushButton("▶  [Trial #1] 파지 시작 (Space)")
        self.btn_trial_toggle.setObjectName("btn_trial_toggle")
        self.btn_trial_toggle.setEnabled(False)
        self.btn_trial_toggle.clicked.connect(self.toggle_trial_state)
        gctrl_layout.addWidget(self.btn_trial_toggle)

        self.table_trials = QTableWidget(0, 8)
        self.table_trials.setHorizontalHeaderLabels(
            ["회차", "손", "과제", "소요시간", "MGA(%)", "ROM(°)", "MGA-3D", "ROM-3D"])
        self.table_trials.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_trials.setFixedHeight(180)
        gctrl_layout.addWidget(self.table_trials)

        left_layout.addWidget(group_ctrl)
        main_layout.addWidget(left_panel)

        # ---------------- 우측 패널 ----------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        video_card = QFrame()
        video_card.setStyleSheet("background-color: #141724; border-radius: 8px; border: 1px solid #282f48;")
        vc_layout = QVBoxLayout(video_card)
        vc_layout.setContentsMargins(8, 8, 8, 8)

        v_header = QHBoxLayout()
        self.lbl_session_status = QLabel("● READY (대기 중)")
        self.lbl_session_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")

        self.lbl_trial_status = QLabel("대기 상태 (시작 전)")
        self.lbl_trial_status.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")

        # 보기 모드 선택: 컬러 / Depth / 나란히
        self.cb_view = QComboBox()
        self.cb_view.addItems(["컬러 영상", "Depth 영상", "컬러 + Depth"])
        self.cb_view.setFixedWidth(130)
        self.cb_view.currentIndexChanged.connect(self.on_view_mode_changed)

        self.chk_mirror = QCheckBox("미러링 (M)")
        self.chk_mirror.toggled.connect(self.on_mirror_toggled)
        self.chk_filter = QCheckBox("하이브리드 필터")
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda v: self.video_worker.set_filter_mode(v))
        self.chk_3d = QCheckBox("3D 재구성")
        self.chk_3d.setChecked(True)
        self.chk_3d.setToolTip("MediaPipe world landmark를 SVD 손바닥 좌표계로 정규화해 3D로 표시합니다.\n"
                               "끄면 CPU 부하가 줄어듭니다.")
        self.chk_3d.toggled.connect(self.on_3d_toggled)
        self.chk_stable3d = QCheckBox("3D 좌표 스무딩")
        self.chk_stable3d.setChecked(LM_SMOOTH_DEFAULT)
        self.chk_stable3d.setToolTip(
            "켜짐: 랜드마크 (x,y,z)에 One-Euro를 걸어 z 노이즈·양자화 떨림을 제거합니다\n"
            "꺼짐: MediaPipe world landmark 원본 좌표를 그대로 사용합니다")
        self.chk_stable3d.toggled.connect(self.on_stable3d_toggled)

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
        v_header.addWidget(QLabel("보기:"))
        v_header.addWidget(self.cb_view)
        v_header.addSpacing(10)
        v_header.addWidget(self.chk_mirror)
        v_header.addSpacing(8)
        v_header.addWidget(self.chk_filter)
        v_header.addSpacing(8)
        v_header.addWidget(self.chk_3d)
        v_header.addSpacing(8)
        v_header.addWidget(self.chk_stable3d)
        v_header.addSpacing(12)
        v_header.addWidget(self.lbl_fps)
        v_header.addSpacing(10)
        v_header.addWidget(self.btn_open_folder)
        v_header.addWidget(self.btn_exit)
        vc_layout.addLayout(v_header)

        self.lbl_video = QLabel("카메라 영상을 연결하는 중입니다...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(400)
        self.lbl_video.setStyleSheet("background-color: #08090e; border-radius: 6px;")
        vc_layout.addWidget(self.lbl_video)

        # 5손가락 실시간 각도 게이지 바 : 오른손/왼손 두 패널 동시 표시
        gauge_row = QHBoxLayout()
        gauge_row.setSpacing(10)
        for hand_label in LiveAngleChart.HAND_ORDER:
            gauge_row.addWidget(self._build_gauge_panel(hand_label), stretch=1)
        vc_layout.addLayout(gauge_row)

        right_layout.addWidget(video_card, stretch=5)

        chart_card = QFrame()
        chart_card.setStyleSheet("background-color: #141724; border-radius: 8px; border: 1px solid #282f48;")
        cc_layout = QVBoxLayout(chart_card)
        cc_layout.setContentsMargins(8, 6, 8, 6)

        # 각도 그래프와 3D 공간을 좌우로 나란히 -> 별도 조작 없이 처음부터 함께 보임
        panes = QHBoxLayout()
        panes.setSpacing(10)

        left_pane = QVBoxLayout()
        left_pane.setSpacing(4)
        lbl_chart_title = QLabel("5손가락 굴곡각 궤적 (위: 오른손 / 아래: 왼손, 청색 음영: 파지 구간)")
        lbl_chart_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #e2e8f0;")
        left_pane.addWidget(lbl_chart_title)
        self.angle_chart = LiveAngleChart(self, width=6, height=4.2)
        left_pane.addWidget(self.angle_chart)

        right_pane = QVBoxLayout()
        right_pane.setSpacing(4)
        lbl_3d_title = QLabel("3D 관절 공간 (좌: 오른손 / 우: 왼손, SVD 손바닥 정규화 좌표 · 손 크기/거리 불변)")
        lbl_3d_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #e2e8f0;")
        right_pane.addWidget(lbl_3d_title)
        self.view3d = Hand3DView(self, width=6, height=4.2)
        right_pane.addWidget(self.view3d)

        panes.addLayout(left_pane, stretch=1)
        panes.addLayout(right_pane, stretch=1)
        cc_layout.addLayout(panes)

        self.lbl_toast = QLabel("안내: [세션 시작] 후 파지 시작할 때 [Space], 파지 끝나고 손 뗄 때 [Space]를 누르세요.")
        self.lbl_toast.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 2px 6px; font-weight: 500;")
        cc_layout.addWidget(self.lbl_toast)

        right_layout.addWidget(chart_card, stretch=5)
        main_layout.addWidget(right_panel, stretch=1)

    def setup_shortcuts(self):
        """전역 단축키 ([Q] 종료, [M] 미러링, [D] 보기전환, [Space] 파지 토글, [Esc] 종료)"""
        QShortcut(QKeySequence("Q"), self).activated.connect(self.handle_q_quit)
        QShortcut(QKeySequence("q"), self).activated.connect(self.handle_q_quit)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.close)
        QShortcut(QKeySequence("M"), self).activated.connect(self.toggle_mirror)
        QShortcut(QKeySequence("m"), self).activated.connect(self.toggle_mirror)
        QShortcut(QKeySequence("D"), self).activated.connect(self.cycle_view_mode)
        QShortcut(QKeySequence("d"), self).activated.connect(self.cycle_view_mode)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.handle_space_action)

    def handle_q_quit(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            self.close()

    def toggle_mirror(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            self.chk_mirror.toggle()

    def cycle_view_mode(self):
        """[D] 키로 컬러 → Depth → 컬러+Depth 순환"""
        if isinstance(self.focusWidget(), QLineEdit):
            return
        self.cb_view.setCurrentIndex((self.cb_view.currentIndex() + 1) % self.cb_view.count())

    def on_view_mode_changed(self, idx):
        modes = [VIEW_COLOR, VIEW_DEPTH, VIEW_BOTH]
        self.video_worker.set_view_mode(modes[idx])
        if self.video_worker.source_name != "realsense" and modes[idx] != VIEW_COLOR:
            self.show_toast("⚠️ RealSense가 연결되지 않아 Depth 화면을 표시할 수 없습니다. 컬러로 유지됩니다.")
        else:
            self.show_toast(f"보기 모드: {self.cb_view.currentText()}")

    def on_stable3d_toggled(self, enabled):
        self.video_worker.set_smooth_3d(enabled)
        self.view3d.reset_view()
        self.show_toast("3D 좌표 스무딩: " + ("ON (랜드마크 One-Euro 적용)" if enabled
                                          else "OFF (world landmark 원본 사용)"))

    def on_3d_toggled(self, enabled):
        self.video_worker.set_enable_3d(enabled)
        if not enabled:
            self.view3d.reset_view()
        self.show_toast(f"3D 재구성: {'ON' if enabled else 'OFF'}")

    def on_mirror_toggled(self, enabled):
        """미러링 체크박스(또는 [M] 단축키) 변경 시 호출."""
        self.video_worker.set_mirror_mode(enabled)
        self.angle_chart.reset_chart()
        self.view3d.reset_view()
        for hand_label in LiveAngleChart.HAND_ORDER:
            self._update_gauge_panel(hand_label, None)
        mode_str = "ON (좌우반전)" if enabled else "OFF"
        self.show_toast(f"미러링 모드 변경: {mode_str}")

    def handle_space_action(self):
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
        name = self.txt_name.text().strip()
        if not name:
            self.show_toast("경고: 피험자 이름을 입력해주세요!")
            return

        self.current_subject_folder = self.make_subject_folder()
        self.is_session_active = True
        self.session_start_time = time.time()
        self.session_records.clear()

        self.is_trial_in_progress = False
        self.current_trial_idx = 1
        self.completed_trials.clear()
        self.table_trials.setRowCount(0)
        self.angle_chart.reset_chart()
        self.measurement_paused = False

        self.btn_session_start.setEnabled(False)
        self.btn_session_stop.setEnabled(True)
        self.btn_trial_toggle.setEnabled(True)
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
        if starting:
            self.btn_trial_toggle.setText(f"▶  [Trial #{self.current_trial_idx}] 파지 시작 (Space)")
            self.btn_trial_toggle.setStyleSheet("""
                #btn_trial_toggle {
                    background-color: #0284c7; color: #ffffff;
                    font-size: 15px; font-weight: bold; min-height: 48px;
                    border: 2px solid #38bdf8;
                }
                #btn_trial_toggle:hover { background-color: #0369a1; }
            """)
        else:
            self.btn_trial_toggle.setText(f"⏹  [Trial #{self.current_trial_idx}] 파지 완료 / 종료 (Space)")
            self.btn_trial_toggle.setStyleSheet("""
                #btn_trial_toggle {
                    background-color: #ea580c; color: #ffffff;
                    font-size: 15px; font-weight: bold; min-height: 48px;
                    border: 2px solid #fdba74;
                }
                #btn_trial_toggle:hover { background-color: #c2410c; }
            """)

    def toggle_trial_state(self):
        """1번째: 파지 시작 마킹 / 2번째: 파지 완료 및 구간 지표 산출"""
        if not self.is_session_active or not self.session_records:
            return

        if self.measurement_paused:
            self.show_toast("⏸ 양손이 모두 인식되어야 파지 시작/완료를 기록할 수 있습니다.")
            return

        t_now = time.time() - self.session_start_time

        if not self.is_trial_in_progress:
            self.is_trial_in_progress = True
            self.current_trial_start_t = t_now
            self.set_trial_button_ui(starting=False)
            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
            self.show_toast(f"▶ [Trial #{self.current_trial_idx}] 파지 시작 마킹! 파지 끝나고 손 뗄 때 [Space]를 누르세요.")
        else:
            self.is_trial_in_progress = False
            t_end = t_now
            t_start = self.current_trial_start_t
            duration = max(0.01, t_end - t_start)

            segment = [r for r in self.session_records if t_start <= r['time'] <= t_end]
            if not segment:
                segment = self.session_records[-15:]

            cur_task_full = self.cb_task.currentText()
            cur_task_short = cur_task_full.split(":")[0].strip()

            # 오른손/왼손 각각 구간 지표를 산출해 한 회차에 두 행을 남긴다
            for hand_label in LiveAngleChart.HAND_ORDER:
                seg = [r for r in self.session_records
                       if r['hand'] == hand_label and t_start <= r['time'] <= t_end]
                if not seg:
                    continue

                apertures = [r['filtered'].get('Grip_Aperture', 0) for r in seg]
                mga_val = max(apertures) if apertures else 0.0
                index_pips = [r['filtered'].get('Index_PIP', 180.0) for r in seg]
                rom_val = (max(index_pips) - min(index_pips)) if index_pips else 0.0

                # 3D(정규화) 기반 지표
                ap3d = [r['metrics3d'].get('aperture_mm') for r in seg
                        if r.get('metrics3d', {}).get('aperture_mm')]
                mga3d = max(ap3d) if ap3d else None
                pip3d = [r['angles3d'].get('Index_PIP') for r in seg
                         if r.get('angles3d', {}).get('Index_PIP') is not None]
                rom3d = (max(pip3d) - min(pip3d)) if len(pip3d) >= 2 else None

                self.completed_trials.append({
                    "trial": self.current_trial_idx,
                    "hand": hand_label,
                    "task": cur_task_full,
                    "task_short": cur_task_short,
                    "start_time": t_start,
                    "end_time": t_end,
                    "duration": duration,
                    "mga": mga_val,
                    "rom": rom_val,
                    "mga3d_mm": mga3d,
                    "rom3d": rom3d,
                })

                row_pos = self.table_trials.rowCount()
                self.table_trials.insertRow(row_pos)
                cells = [
                    f"Trial #{self.current_trial_idx}",
                    LiveAngleChart.HAND_TITLES[hand_label].split(' ')[0],
                    cur_task_short,
                    f"{duration:.2f}초",
                    f"{mga_val:.1f}%",
                    f"{rom_val:.1f}°",
                    f"{mga3d:.0f}mm" if mga3d else "-",
                    f"{rom3d:.1f}°" if rom3d else "-",
                ]
                for c, txt in enumerate(cells):
                    self.table_trials.setItem(row_pos, c, QTableWidgetItem(txt))
            self.table_trials.scrollToBottom()

            self.angle_chart.add_trial_span(t_start, t_end, f"T{self.current_trial_idx}")

            done_n = len({tr['trial'] for tr in self.completed_trials})
            self.current_trial_idx += 1
            self.set_trial_button_ui(starting=True)

            self.lbl_trial_status.setText(f"완료됨 (총 {done_n}회 기록 완료)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.show_toast(f"✅ [Trial #{self.current_trial_idx - 1} - {cur_task_short}] "
                            f"양손 기록 완료! (소요시간: {duration:.2f}초)", is_success=True)

    def stop_session(self):
        if not self.is_session_active:
            return
        if self.is_trial_in_progress:
            self.toggle_trial_state()

        self.is_session_active = False
        duration = time.time() - self.session_start_time

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
        n_tr = len({tr["trial"] for tr in self.completed_trials})
        self.lbl_trial_status.setText(f"총 {n_tr}회차 데이터 저장됨")

        self.save_session_batch(duration)
        self.show_toast(f"✅ 세션 저장 완료! 총 {n_tr}개 회차(양손) 일괄 저장됨 "
                        f"(소요시간: {duration:.1f}초)", is_success=True)

    def save_session_batch(self, duration):
        """전체 연속 시계열 + Trial별 요약표 + 통합 플롯 일괄 저장"""
        if not self.session_records:
            self.show_toast("⚠️ 수집된 데이터가 없어 저장을 건너뜁니다.")
            return []

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"Session_{ts_str}"
        saved_paths = []

        raw_csv_path = os.path.join(self.current_subject_folder, f"{prefix}_continuous_raw.csv")
        headers = [
            "time_s", "Task", "Trial", "Movement_Phase", "hand_label",
            "Thumb_MCP_raw", "Thumb_MCP_filt", "Thumb_IP_raw", "Thumb_IP_filt",
            "Index_MCP_raw", "Index_MCP_filt", "Index_PIP_raw", "Index_PIP_filt", "Index_DIP_raw", "Index_DIP_filt",
            "Middle_MCP_raw", "Middle_MCP_filt", "Middle_PIP_raw", "Middle_PIP_filt", "Middle_DIP_raw", "Middle_DIP_filt",
            "Ring_MCP_raw", "Ring_MCP_filt", "Ring_PIP_raw", "Ring_PIP_filt", "Ring_DIP_raw", "Ring_DIP_filt",
            "Pinky_MCP_raw", "Pinky_MCP_filt", "Pinky_PIP_raw", "Pinky_PIP_filt", "Pinky_DIP_raw", "Pinky_DIP_filt",
            "Grip_Aperture_raw", "Grip_Aperture_filt",
            "Wrist_Depth_m",
            # ---- SVD 정규화 3D 지표 (depth 비의존) ----
            "Wrist_X_m", "Wrist_Y_m", "Wrist_Z_m",
            "Thumb_IP_3D", "Index_PIP_3D", "Middle_PIP_3D", "Ring_PIP_3D", "Pinky_PIP_3D",
            "Index_MCP_3D", "Middle_MCP_3D",
            "Grip_Aperture_mm_3D", "Grip_Aperture_norm_3D", "Palm_Len_mm_3D",
            "Recon_Mode", "Depth_Raw_Hit_pct"
        ]
        # 21개 정규화 3D 랜드마크 좌표 열 (손목 원점 · 손 길이 1.0)
        lm_names = [
            "Wrist",
            "Thumb_CMC", "Thumb_MCP", "Thumb_IP", "Thumb_TIP",
            "Index_MCP", "Index_PIP", "Index_DIP", "Index_TIP",
            "Middle_MCP", "Middle_PIP", "Middle_DIP", "Middle_TIP",
            "Ring_MCP", "Ring_PIP", "Ring_DIP", "Ring_TIP",
            "Pinky_MCP", "Pinky_PIP", "Pinky_DIP", "Pinky_TIP"
        ]
        for nm in lm_names:
            headers.extend([f"{nm}_3D_X", f"{nm}_3D_Y", f"{nm}_3D_Z"])

        def _f(v, fmt="{:.2f}"):
            """None/NaN이면 빈 칸으로 남긴다 (0으로 채우면 분석에서 실제 0과 구분이 안 됨)"""
            if v is None:
                return ""
            try:
                if not np.isfinite(v):
                    return ""
            except TypeError:
                return ""
            return fmt.format(v)

        with open(raw_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for rec in self.session_records:
                t = rec['time']
                task_name = rec.get('task', self.cb_task.currentText())
                trial_tag = "Rest"
                phase_tag = "Rest"

                for tr in self.completed_trials:
                    if tr['hand'] == rec['hand'] and tr['start_time'] <= t <= tr['end_time']:
                        task_name = tr.get('task', task_name)
                        trial_tag = f"Trial_{tr['trial']}"
                        phase_tag = "Grasping"
                        break

                raw_a = rec['raw']
                filt_a = rec['filtered']
                a3 = rec.get('angles3d', {}) or {}
                m3 = rec.get('metrics3d', {}) or {}
                depth_m = rec.get('wrist_depth')
                wp = m3.get('wrist_point')
                row = [
                    f"{t:.4f}", task_name, trial_tag, phase_tag, rec['hand'],
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
                    f"{raw_a.get('Grip_Aperture', 0):.2f}", f"{filt_a.get('Grip_Aperture', 0):.2f}",
                    _f(depth_m, "{:.4f}"),
                    _f(wp[0] if wp else None, "{:.4f}"),
                    _f(wp[1] if wp else None, "{:.4f}"),
                    _f(wp[2] if wp else None, "{:.4f}"),
                    _f(a3.get('Thumb_IP')), _f(a3.get('Index_PIP')), _f(a3.get('Middle_PIP')),
                    _f(a3.get('Ring_PIP')), _f(a3.get('Pinky_PIP')),
                    _f(a3.get('Index_MCP')), _f(a3.get('Middle_MCP')),
                    _f(m3.get('aperture_mm'), "{:.1f}"), _f(m3.get('aperture_norm'), "{:.2f}"),
                    _f(m3.get('palm_len_mm'), "{:.1f}"),
                    m3.get('mode', ''), _f(m3.get('raw_hit_pct'), "{:.1f}"),
                ]

                pts3d = rec.get('points3d')
                if pts3d is not None and len(pts3d) == 21:
                    for p in pts3d:
                        row.extend([f"{p[0]:.4f}", f"{p[1]:.4f}", f"{p[2]:.4f}"])
                else:
                    row.extend([""] * 63)

                writer.writerow(row)
        saved_paths.append(raw_csv_path)

        summary_csv_path = os.path.join(self.current_subject_folder, f"{prefix}_trials_summary.csv")
        with open(summary_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["Trial", "Hand", "Task", "Start_Time_s", "End_Time_s", "Duration_s",
                             "MGA_pct", "Index_ROM_deg", "Thumb_PIP_Mean", "Index_PIP_Mean",
                             "Middle_PIP_Mean", "Wrist_Depth_Mean_m",
                             "MGA_mm_3D", "Index_ROM_3D_deg", "Index_PIP_3D_Mean",
                             "Palm_Len_mm_Mean"])
            for tr in self.completed_trials:
                seg = [r for r in self.session_records
                       if r['hand'] == tr['hand'] and tr['start_time'] <= r['time'] <= tr['end_time']]
                if not seg:
                    continue
                t_pips = [r['filtered'].get('Thumb_IP', 0) for r in seg]
                i_pips = [r['filtered'].get('Index_PIP', 0) for r in seg]
                m_pips = [r['filtered'].get('Middle_PIP', 0) for r in seg]
                depths = [r['wrist_depth'] for r in seg if r.get('wrist_depth')]
                i3 = [r['angles3d'].get('Index_PIP') for r in seg
                      if r.get('angles3d', {}).get('Index_PIP') is not None]
                pl = [r['metrics3d'].get('palm_len_mm') for r in seg
                      if r.get('metrics3d', {}).get('palm_len_mm') is not None]

                writer.writerow([
                    f"Trial #{tr['trial']}", tr['hand'], tr.get('task_short', 'Task'),
                    f"{tr['start_time']:.2f}", f"{tr['end_time']:.2f}", f"{tr['duration']:.2f}",
                    f"{tr['mga']:.2f}", f"{tr['rom']:.2f}",
                    f"{np.mean(t_pips):.2f}", f"{np.mean(i_pips):.2f}", f"{np.mean(m_pips):.2f}",
                    f"{np.mean(depths):.3f}" if depths else "",
                    f"{tr['mga3d_mm']:.1f}" if tr.get('mga3d_mm') else "",
                    f"{tr['rom3d']:.2f}" if tr.get('rom3d') else "",
                    f"{np.mean(i3):.2f}" if i3 else "",
                    f"{np.mean(pl):.1f}" if pl else "",
                ])
        saved_paths.append(summary_csv_path)

        plot_path = os.path.join(self.current_subject_folder, f"{prefix}_waveform_plot.png")
        self.export_session_plot(plot_path, prefix)
        saved_paths.append(plot_path)

        meta_path = os.path.join(self.current_subject_folder, "subject_metadata.json")
        meta_data = {
            "name": self.txt_name.text().strip(),
            "age": self.spin_age.value(),
            "gender": self.cb_gender.currentText(),
            "group": "Healthy" if self.rb_healthy.isChecked() else "Patient",
            "fma_score": self.spin_fma.value() if self.rb_patient.isChecked() else None,
            "brunnstrom_stage": self.cb_brs.currentText() if self.rb_patient.isChecked() else None,
            "affected_side": self.cb_affected.currentText() if self.rb_patient.isChecked() else None,
            "total_completed_trials": len({tr["trial"] for tr in self.completed_trials}),
            "records_per_frame": "hand-wise long format (Right/Left each one row)",
            "angle_3d_source": ("MediaPipe world landmark + One-Euro landmark smoothing "
                                "+ SVD palm-plane normalization (depth independent)"),
            "coord_3d_units": "wrist-origin, normalized by palm length (wrist-middleMCP = 1.0)",
            "session_duration_sec": duration,
            "camera_source": getattr(self.video_worker, "source_name", "webcam"),
            "camera_resolution": f"{RS_WIDTH}x{RS_HEIGHT}@{RS_FPS}",
            "depth_scale": getattr(self.video_worker, "depth_scale", None),
            "depth_usage": "wrist distance display / quality logging only",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        return saved_paths

    def export_session_plot(self, save_path, title_prefix):
        """오른손/왼손 굴곡각 + 정규화 3D 지표를 3단으로 저장"""
        if not self.session_records:
            return

        colors = {'Thumb_IP': '#ef4444', 'Index_PIP': '#0ea5e9', 'Middle_PIP': '#22c55e',
                  'Ring_PIP': '#f59e0b', 'Pinky_PIP': '#a855f7'}
        labels = {'Thumb_IP': 'Thumb IP', 'Index_PIP': 'Index PIP', 'Middle_PIP': 'Middle PIP',
                  'Ring_PIP': 'Ring PIP', 'Pinky_PIP': 'Pinky PIP'}

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True, dpi=150,
                                            gridspec_kw={'height_ratios': [3, 3, 2]})
        fig.patch.set_facecolor('#ffffff')

        hand_axes = {'Right': ax1, 'Left': ax2}
        for hand_label, ax in hand_axes.items():
            seg = [r for r in self.session_records if r['hand'] == hand_label]
            if not seg:
                ax.text(0.5, 0.5, f"{hand_label}: 데이터 없음", ha='center', transform=ax.transAxes)
                continue
            ts = [r['time'] for r in seg]
            for k, col in colors.items():
                ax.plot(ts, [r['filtered'].get(k, np.nan) for r in seg],
                        label=labels[k], color=col, linewidth=1.6)
            ax.set_ylim(0, 180)
            ax.set_ylabel(f"{LiveAngleChart.HAND_TITLES[hand_label]}\nFlexion (deg)", fontweight='bold')
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.legend(loc='upper right', fontsize=7, ncol=5)

        # 3단: 정규화 3D 검지 PIP 각도와 파지폭(mm)
        for hand_label, style in (('Right', '-'), ('Left', '--')):
            seg = [r for r in self.session_records if r['hand'] == hand_label]
            if not seg:
                continue
            ts = [r['time'] for r in seg]
            ax3.plot(ts, [r.get('angles3d', {}).get('Index_PIP', np.nan) or np.nan for r in seg],
                     style, color='#0ea5e9', linewidth=1.4,
                     label=f"{hand_label} Index PIP (3D)")
            ax3.plot(ts, [r.get('metrics3d', {}).get('aperture_mm', np.nan) for r in seg],
                     style, color='#94a3b8', linewidth=1.0, alpha=0.8,
                     label=f"{hand_label} 파지폭 (mm)")
        ax3.set_ylabel("3D 각도(°) / 파지폭(mm)", fontweight='bold')
        ax3.set_xlabel("Elapsed Time (seconds)", fontweight='bold')
        ax3.grid(True, linestyle=':', alpha=0.6)
        ax3.legend(loc='upper right', fontsize=7, ncol=2)

        # 파지 구간 음영 (회차당 한 번만)
        seen = set()
        for tr in self.completed_trials:
            if tr['trial'] in seen:
                continue
            seen.add(tr['trial'])
            for ax in (ax1, ax2, ax3):
                ax.axvspan(tr['start_time'], tr['end_time'], color='#fef08a',
                           alpha=0.35, label='_nolegend_')
            ax1.text((tr['start_time'] + tr['end_time']) / 2, 168,
                     f"T{tr['trial']} ({tr.get('task_short', '')})",
                     color='#854d0e', fontweight='bold', fontsize=8, ha='center')

        ax1.set_title(f"[{title_prefix}] Both-hand session with SVD-normalized 3D",
                      fontsize=11, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close(fig)

    def _refresh_trial_status_label(self):
        if self.is_trial_in_progress:
            self.lbl_trial_status.setText(f"🔴 [Trial #{self.current_trial_idx}] 파지 동작 진행 중...")
            self.lbl_trial_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
        elif self.completed_trials:
            self.lbl_trial_status.setText(
                f"완료됨 (총 {len({tr['trial'] for tr in self.completed_trials})}회 기록 완료)")
            self.lbl_trial_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
        else:
            self.lbl_trial_status.setText("준비됨 (파지 시작 대기)")
            self.lbl_trial_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")

    def on_frame_ready(self, frame, angles_dict, fps, hand_count, wrist_depths, hands3d):
        self.last_angles = angles_dict
        self.last_hands3d = hands3d
        src = getattr(self.video_worker, "source_name", "webcam")
        src_tag = "RealSense D455" if src == "realsense" else "Webcam"
        n3d = len(hands3d)
        self.lbl_fps.setText(f"{src_tag} | FPS: {fps:.1f} | Hands: {hand_count} | 3D: {n3d}")

        both_hands_detected = ('Right' in angles_dict) and ('Left' in angles_dict)

        if self.is_session_active:
            if both_hands_detected:
                if self.measurement_paused:
                    self.measurement_paused = False
                    self.btn_trial_toggle.setEnabled(True)
                    self._refresh_trial_status_label()
                    self.show_toast("▶ 양손 인식 완료! 측정을 재개합니다.", is_success=True)

                t = time.time() - self.session_start_time
                # 오른손/왼손을 각각 한 행씩 기록
                for hand_label in LiveAngleChart.HAND_ORDER:
                    h_data = angles_dict[hand_label]
                    rec3d = hands3d.get(hand_label)
                    self.session_records.append({
                        'time': t,
                        'hand': hand_label,
                        'raw': h_data['raw'],
                        'filtered': h_data['filtered'],
                        'angles3d': rec3d['angles'] if rec3d else {},
                        'metrics3d': rec3d['metrics'] if rec3d else {},
                        'points3d': rec3d['points'] if rec3d else None,
                        'wrist_depth': wrist_depths.get(hand_label),
                        'task': self.cb_task.currentText()
                    })
                self.angle_chart.update_data(t, angles_dict)
            else:
                if not self.measurement_paused:
                    self.measurement_paused = True
                    self.btn_trial_toggle.setEnabled(False)
                    self.show_toast("⏸ 양손이 모두 인식되지 않아 측정을 일시정지합니다. 두 손을 화면에 비춰주세요.")
                self.lbl_trial_status.setText("⏸ 측정 일시정지 (양손 인식 필요)")
                self.lbl_trial_status.setStyleSheet("color: #f97316; font-weight: bold; font-size: 13px;")
        # 3D 공간은 세션 여부/한손 인식 여부와 무관하게 항상 갱신 (카메라 배치 확인용)
        self.view3d.update_hands(time.time() - self.app_start_time, hands3d)

        # 오른손/왼손 게이지를 각각 독립적으로 갱신 (제목에 실측 거리 표시)
        for hand_label in LiveAngleChart.HAND_ORDER:
            self._update_gauge_panel(hand_label, angles_dict.get(hand_label),
                                     wrist_depths.get(hand_label))

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_BGR888)

        pixmap = QtGui.QPixmap.fromImage(q_img).scaled(
            self.lbl_video.width(), self.lbl_video.height(),
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
# 7. 실행 진입점
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
import os
os.environ.update({'TF_ENABLE_ONEDNN_OPTS': '0', 'TF_CPP_MIN_LOG_LEVEL': '2',
                   'QT_ENABLE_HIGHDPI_SCALING': '1', 'QT_AUTO_SCREEN_SCALE_FACTOR': '1'})

import sys, csv, json, time, math, uuid
from datetime import datetime
from collections import deque

import cv2
import numpy as np
import mediapipe as mp

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
    QTableWidget, QTableWidgetItem, QHeaderView)

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
RS_DW, RS_DH = 848, 480          # 원본 depth 해상도. 컬러에 정렬 후 역투영에 사용
DEPTH_VIS_MIN, DEPTH_VIS_MAX = 0.4, 1.5
VIEW_COLOR, VIEW_DEPTH, VIEW_BOTH = "color", "depth", "both"

# high_accuracy는 신뢰도 임계를 높여 홀을 늘린다. 근거리 손 촬영에서는
# 홀이 결측의 지배적 원인이므로 기본값을 medium_density로 둔다.
RS_VISUAL_PRESET = 'medium_density'      # 'default' | 'high_accuracy' | 'high_density' | 'medium_density' | None

# ---- 영상 기록 ----
# 원본(original.avi)과 랜드마크 오버레이(mediapipe.avi)를 따로 남긴다.
# 둘 다 미러링 이전의 원본 좌표계 프레임이라 픽셀이 CSV와 그대로 대응된다.
VIDEO_FOURCC = 'MJPG'
VIDEO_RAW_NAME, VIDEO_MP_NAME = 'original.avi', 'mediapipe.avi'
# 파일에 적는 fps가 실제 처리 속도와 다르면 재생 배속이 어긋난다. MediaPipe 추론
# 때문에 루프는 카메라 fps보다 느리게 돌므로, RS_FPS를 그대로 쓰면 프레임이 모자라
# 영상이 빨라진다. 기록 직전 실측한 프레임 간격으로 fps를 정한다.
VIDEO_FPS_WINDOW = 120           # 실측에 쓰는 최근 프레임 간격 개수
VIDEO_FPS_MIN_SAMPLES = 20       # 이보다 표본이 적으면 RS_FPS로 폴백
VIDEO_FPS_RANGE = (1.0, 120.0)   # 순간적인 끊김이 이상값을 만들지 않도록 하는 상한/하한

# ---- depth 샘플링 품질 게이트 ----
# 홀 필링을 하지 않는다. 값을 만들어내는 대신 결측으로 남기고 상태 코드를 기록한다.
DEPTH_MIN_M, DEPTH_MAX_M = 0.10, 2.00
DEPTH_EDGE_M = 0.03              # 이웃의 10~90 백분위 폭이 이보다 크면 경계로 보고 버림
DEPTH_NEIGHBOR = 5               # 게이트 창 (평활용 아님). 3은 손끝에서 배경을 못 걸러냈다.
DEPTH_HAND_DEV_M = 0.12          # 손 대표거리에서 이만큼 벗어난 샘플은 배경으로 간주
DEPTH_HAND_MIN_SAMPLES = 5       # 대표거리를 세우기 위한 최소 유효 샘플 수
LM_MAX_SPAN_MM = 260.0           # 손목에서 어떤 랜드마크까지의 최대 해부학적 거리
APERTURE_MAX_MM = 150.0          # 엄지끝-검지끝 벌림의 상한 (이보다 크면 오검출)

# 권장 작업 거리. 벗어나면 화면에 경고를 띄운다 (D400 계열 근거리 하한 고려)
WORK_MIN_M, WORK_MAX_M = 0.35, 0.80
QC_WINDOW = 60                   # 실시간 QC 집계 프레임 수
RS_MIN_VALID_FRAMES = 10         # 이보다 적은 유효 프레임의 RS 요약값은 보고하지 않음

# 구간 내 표본 간격이 이보다 벌어지면 '기록이 끊긴 구간'으로 보고 유효시간에서 뺀다
VALID_GAP_MAX_S = 0.5

PALM_IDS = [0, 1, 5, 9, 13, 17]   # 3D 뷰 손바닥 메시 표시용
# 정준 좌표계 기준 평면에서는 엄지 CMC(1)를 뺀다. 1번은 엄지 외전/대립 시
# 함께 움직여, 측정하려는 자유도가 기준면 자체를 흔들기 때문이다.
FRAME_IDS = [0, 5, 9, 13, 17]
LM_SMOOTH_DEFAULT = True
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

# 결측 원인 코드. 각각이 다른 대응을 요구하므로 하나로 뭉뚱그리지 않는다.
#   depth_hole          : 센서가 값을 못 냄        -> 거리·조명·프리셋
#   depth_edge          : 이웃에 배경이 섞임        -> 배경 분리, 창 크기
#   depth_off_hand      : 손 대표거리에서 이탈      -> 배경 오검출 (조용한 오차의 주범)
#   implausible_span    : 손목에서 해부학적으로 멀다 -> 위와 동일
#   depth_out_of_range  : 작업 거리 밖
DEPTH_STATUSES = ('ok', 'no_depth', 'outside_image', 'depth_hole', 'depth_out_of_range',
                  'insufficient_depth', 'depth_edge', 'depth_off_hand',
                  'implausible_span', 'no_intrinsics', 'deprojection_failed')


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
    """각도용: 스파이크 클램프 + One-Euro + 결측 시 완만한 복귀."""

    def __init__(self, init_val=180.0):
        self.last = float(init_val)
        self.missing = 0
        self.euro = OneEuro(x0=init_val, min_cutoff=0.7, beta=0.015, t0=0.0)

    def update(self, t, v):
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
    좌/우 손은 정준계 손잡이(handedness)가 뒤집히므로 부호 대신 크기로 낸다."""
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
    state, marks = ('open' if a[0] > hi_th else 'closed'), []
    for ti, v in zip(times, a):
        if state == 'open' and v < lo_th:
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


# ======================= depth 기반 측정 (RS) =======================
def sample_depth(depth_m, pixel):
    """중심 화소의 유효 거리를 반환. 홀·범위초과·경계 혼입은 버린다.

    이웃 창은 '품질 게이트'이지 홀 필링이 아니다. 평균/보간으로 값을 만들면
    손끝에서 배경 거리가 섞여 들어와 조용히 틀린 좌표가 된다."""
    if depth_m is None:
        return None, 'no_depth'
    u, v = float(pixel[0]), float(pixel[1])
    h, w = depth_m.shape[:2]
    if not np.isfinite([u, v]).all() or not (0 <= u <= w - 1 and 0 <= v <= h - 1):
        return None, 'outside_image'
    x, y = int(round(u)), int(round(v))
    z = float(depth_m[y, x])
    if not np.isfinite(z) or z <= 0:
        return None, 'depth_hole'
    if not DEPTH_MIN_M <= z <= DEPTH_MAX_M:
        return None, 'depth_out_of_range'
    r = DEPTH_NEIGHBOR // 2
    patch = depth_m[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)]
    valid = patch[np.isfinite(patch) & (patch > 0)]
    if valid.size < max(1, int(np.ceil(patch.size / 2))):
        return None, 'insufficient_depth'
    if float(np.ptp(np.percentile(valid, [10, 90]))) > DEPTH_EDGE_M:
        return None, 'depth_edge'
    return z, 'ok'


def deproject_pixel(intr, pixel, depth):
    """정렬된 depth intrinsics로 픽셀+거리를 카메라 좌표계 XYZ(m)로 역투영.

    SDK의 rs2_deproject_pixel_to_point는 modified Brown-Conrady를 처리하지
    못하므로, 그 모델일 때만 OpenCV로 왜곡을 푼 뒤 z를 곱한다."""
    if intr is None:
        return None
    if rs is not None and intr.model == rs.distortion.modified_brown_conrady:
        K = np.array([[intr.fx, 0, intr.ppx], [0, intr.fy, intr.ppy], [0, 0, 1.0]])
        xy = cv2.undistortPoints(np.array([[[float(pixel[0]), float(pixel[1])]]], dtype=float),
                                 K, np.asarray(intr.coeffs, dtype=float))[0, 0]
        return [float(xy[0]) * depth, float(xy[1]) * depth, float(depth)]
    return rs.rs2_deproject_pixel_to_point(intr, [float(pixel[0]), float(pixel[1])],
                                           float(depth))


def measure_depth_hand(pixels, depth_m, intr):
    """21개 랜드마크 픽셀을 실제 depth로 역투영하고 관절각까지 낸다.

    3단 방어: (1) 화소 단위 품질 게이트, (2) 손 대표거리 이탈 제거,
    (3) 역투영 후 해부학적 거리 초과 제거. 국소 게이트만으로는 손끝에서
    배경이 통과해 '그럴듯하지만 틀린' 좌표가 남는다.

    MediaPipe world landmark와 섞지 않는다. 두 방법을 독립적으로 계산해야
    차이(RS - MP)를 그대로 신뢰도 비교 지표로 쓸 수 있다."""
    pixels = np.asarray(pixels, dtype=float).reshape(21, 2)
    pts = np.full((21, 3), np.nan)
    depths, statuses = [], []

    # --- 1단: 화소 단위 게이트 ---
    for px in pixels:
        z, st = sample_depth(depth_m, px)
        depths.append(z)
        statuses.append(st)

    # --- 2단: 손 대표거리에서 벗어난 샘플 제거 ---
    accepted = [z for z, st in zip(depths, statuses) if st == 'ok']
    hand_z = None
    if len(accepted) >= DEPTH_HAND_MIN_SAMPLES:
        hand_z = float(np.median(accepted))
        for i, (z, st) in enumerate(zip(depths, statuses)):
            if st == 'ok' and abs(z - hand_z) > DEPTH_HAND_DEV_M:
                statuses[i] = 'depth_off_hand'

    # --- 역투영 ---
    for i, px in enumerate(pixels):
        if statuses[i] != 'ok':
            continue
        if intr is None:
            statuses[i] = 'no_intrinsics'
            continue
        try:
            xyz = np.asarray(deproject_pixel(intr, px, depths[i]), dtype=float)
            if xyz.shape != (3,) or not np.isfinite(xyz).all():
                raise ValueError('invalid deprojection')
            pts[i] = xyz
        except (RuntimeError, ValueError, TypeError):
            statuses[i] = 'deprojection_failed'

    # --- 3단: 해부학적 거리 검사 ---
    finite = np.isfinite(pts).all(axis=1)
    if finite.any():
        origin = pts[0] if finite[0] else pts[finite].mean(axis=0)
        for i in range(21):
            if finite[i] and float(np.linalg.norm(pts[i] - origin)) * 1000 > LM_MAX_SPAN_MM:
                pts[i] = np.nan
                statuses[i] = 'implausible_span'
        finite = np.isfinite(pts).all(axis=1)

    # --- 지표 ---
    tip_ok = bool(finite[4] and finite[8])
    aperture = float(np.linalg.norm(pts[4] - pts[8]) * 1000) if tip_ok else None
    aperture_rejected = False
    if aperture is not None and aperture > APERTURE_MAX_MM:
        aperture, tip_ok, aperture_rejected = None, False, True

    angles = {}
    for name, (a, b, c) in JOINT_DEFS.items():
        angles[name] = (angle3(pts[a], pts[b], pts[c])
                        if finite[a] and finite[b] and finite[c] else None)
    for f, j in FLEX_OF.items():
        angles[f"{f}_Flexion"] = angles[j]

    palm_len = (float(np.linalg.norm(pts[9] - pts[0]) * 1000)
                if finite[0] and finite[9] else None)
    pab = rab = None
    if finite[FRAME_IDS].all() and finite[1] and finite[2]:
        canon = palm_frame(pts)[0]
        pab, rab = thumb_abduction(canon)
    wrist_z = float(pts[0, 2]) if finite[0] else None

    return dict(points=pts, depths=depths, status=statuses,
                valid=tip_ok, n_valid=int(finite.sum()),
                aperture_mm=aperture, aperture_rejected=aperture_rejected,
                angles=angles, palm_len_mm=palm_len, hand_z_m=hand_z,
                thumb_palmar_abd=pab, thumb_radial_abd=rab, wrist_z_m=wrist_z)


# ============================ 비디오 스레드 ============================
class VideoWorker(QThread):
    # frame, angles, fps, n_hands, hands3d, rs_measurements, frame_meta
    frame_processed = pyqtSignal(np.ndarray, dict, float, int, dict, dict, dict)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index, self.running = camera_index, True
        self.mirror_mode = False
        self.use_filter = self.enable_3d = True
        self.enable_depth3d = True
        self.smooth_3d = LM_SMOOTH_DEFAULT
        self.view_mode, self.source_name = VIEW_COLOR, "webcam"
        self.filters, self.ap_filters, self.smoothers = {}, {}, {}
        self.depth_scale, self.latest_depth, self.depth_filters = 1.0, None, None
        self.depth_intr = None          # 컬러에 정렬된 depth 스트림의 intrinsics
        self.camera_info = {}
        self.palm_calib_mm = 0.0
        self.t0 = time.time()
        # 프레임 식별자. 앱 기동부터 단조 증가시켜 CSV와 영상 프레임을 잇는다.
        self.frame_id = 0
        # 영상 기록 상태 (요청은 GUI 스레드, 실제 열고 닫기는 캡처 스레드에서)
        self._rec_folder = None
        self._rec_request = self._rec_release = False
        self.rec_raw = self.rec_mp = None
        self.rec_frames = 0
        self.rec_fps = float(RS_FPS)
        self._dt_hist = deque(maxlen=VIDEO_FPS_WINDOW)

    def set_mirror_mode(self, v):
        # 미러링은 표시 전용이다. 측정 입력(픽셀·depth·intrinsics)은 항상 원본.
        self.mirror_mode = v

    def set_filter_mode(self, v):
        self.use_filter = v

    def set_view_mode(self, v):
        self.view_mode = v

    def set_enable_3d(self, v):
        self.enable_3d = v
        self.smoothers = {}

    def set_enable_depth3d(self, v):
        self.enable_depth3d = bool(v)

    def set_smooth_3d(self, v):
        self.smooth_3d = v
        self.smoothers = {}

    def set_palm_calib(self, mm):
        self.palm_calib_mm = float(mm or 0.0)

    # ---------------- 영상 기록 ----------------
    def start_recording(self, folder):
        """세션 시작 시 호출. 실제 파일 생성은 다음 캡처 프레임에서 일어난다."""
        self._rec_folder = folder
        self._rec_request = True

    def stop_recording(self):
        self._rec_release = True

    def _measured_fps(self):
        """최근 프레임 간격의 중앙값으로 실제 처리 속도를 낸다.
        중앙값을 쓰는 이유는 한두 번의 끊김(디스크 I/O, GC)이 평균을 끌어내려
        영상이 도리어 느려지는 것을 막기 위해서다."""
        if len(self._dt_hist) < VIDEO_FPS_MIN_SAMPLES:
            return float(RS_FPS)
        med = float(np.median(self._dt_hist))
        if not np.isfinite(med) or med <= 0:
            return float(RS_FPS)
        return float(np.clip(1.0 / med, *VIDEO_FPS_RANGE))

    def _open_writers(self, frame):
        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_FOURCC)
        fps = self._measured_fps()
        try:
            raw = cv2.VideoWriter(os.path.join(self._rec_folder, VIDEO_RAW_NAME),
                                  fourcc, fps, (w, h))
            mpv = cv2.VideoWriter(os.path.join(self._rec_folder, VIDEO_MP_NAME),
                                  fourcc, fps, (w, h))
            if not (raw.isOpened() and mpv.isOpened()):
                raise RuntimeError('VideoWriter open failed')
            self.rec_raw, self.rec_mp, self.rec_frames = raw, mpv, 0
            self.rec_fps = fps
            print(f"[녹화] {VIDEO_RAW_NAME} / {VIDEO_MP_NAME} "
                  f"({w}x{h} @ {fps:.2f}fps 실측 · 카메라 {RS_FPS}fps)")
        except Exception as e:
            self.rec_raw = self.rec_mp = None
            print(f"[경고] 영상 기록을 시작하지 못했습니다: {e}")

    def _close_writers(self):
        for wtr in (self.rec_raw, self.rec_mp):
            if wtr is not None:
                try:
                    wtr.release()
                except Exception:
                    pass
        self.rec_raw = self.rec_mp = None

    # ---------------- RealSense ----------------
    @staticmethod
    def _intrinsics_dict(intr):
        return dict(width=intr.width, height=intr.height, fx=intr.fx, fy=intr.fy,
                    ppx=intr.ppx, ppy=intr.ppy, model=str(intr.model),
                    coeffs=list(intr.coeffs))

    def _apply_preset(self, sensor):
        if not RS_VISUAL_PRESET:
            return None
        try:
            if not sensor.supports(rs.option.visual_preset):
                return None
            preset = getattr(rs.rs400_visual_preset, RS_VISUAL_PRESET)
            sensor.set_option(rs.option.visual_preset, float(preset))
            return RS_VISUAL_PRESET
        except Exception as e:
            print(f"[경고] visual_preset '{RS_VISUAL_PRESET}' 적용 실패: {e}")
            return None

    def _open_realsense(self):
        if rs is None:
            print("[안내] pyrealsense2 미설치 → 웹캠으로 동작합니다 (depth 측정 불가).")
            return None
        try:
            if len(rs.context().query_devices()) == 0:
                print("[안내] RealSense 장치 없음 → 웹캠으로 폴백합니다 (depth 측정 불가).")
                return None
            pipe, cfg = rs.pipeline(), rs.config()
            cfg.enable_stream(rs.stream.color, RS_W, RS_H, rs.format.bgr8, RS_FPS)
            cfg.enable_stream(rs.stream.depth, RS_DW, RS_DH, rs.format.z16, RS_FPS)
            prof = pipe.start(cfg)
            sensor = prof.get_device().first_depth_sensor()
            self.depth_scale = float(sensor.get_depth_scale())
            preset = self._apply_preset(sensor)

            dev = prof.get_device()
            cp = prof.get_stream(rs.stream.color).as_video_stream_profile()
            dp = prof.get_stream(rs.stream.depth).as_video_stream_profile()
            extr = dp.get_extrinsics_to(cp)
            self.camera_info = dict(
                source='realsense',
                device=str(dev.get_info(rs.camera_info.name)),
                serial=str(dev.get_info(rs.camera_info.serial_number)),
                firmware=str(dev.get_info(rs.camera_info.firmware_version)),
                visual_preset=preset, depth_scale_m=self.depth_scale,
                color_intrinsics=self._intrinsics_dict(cp.get_intrinsics()),
                depth_intrinsics=self._intrinsics_dict(dp.get_intrinsics()),
                depth_to_color=dict(rotation=list(extr.rotation),
                                    translation=list(extr.translation)),
                color_fps=cp.fps(), depth_fps=dp.fps())

            # 후처리 필터는 '표시용'으로만 쓴다. 측정에는 절대 통과시키지 않는다.
            spat, temp = rs.spatial_filter(), rs.temporal_filter()
            spat.set_option(rs.option.holes_fill, 1)
            self.depth_filters = [spat, temp]
            for _ in range(15):
                pipe.wait_for_frames()
            self.source_name = "realsense"
            print(f"[RealSense] {self.camera_info['device']} | preset={preset} | "
                  f"color {RS_W}x{RS_H} / depth {RS_DW}x{RS_DH} | scale={self.depth_scale}")
            return pipe, rs.align(rs.stream.color)
        except Exception as e:
            print(f"[경고] RealSense 초기화 실패 ({e}) → 웹캠으로 폴백합니다.")
            return None

    def _colorize_depth(self, d):
        norm = np.clip((d - DEPTH_VIS_MIN) / (DEPTH_VIS_MAX - DEPTH_VIS_MIN), 0, 1)
        vis = cv2.applyColorMap(((1 - norm) * 255).astype(np.uint8), cv2.COLORMAP_JET)
        vis[d <= 0] = (0, 0, 0)
        return vis

    # ---------------- 3D 재구성 (MediaPipe world landmark) ----------------
    def build_3d(self, hand, world_lm, t, wrist_depth):
        if not self.enable_3d or world_lm is None:
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

    # ---------------- 메인 루프 ----------------
    def run(self):
        pipe = align = cap = None
        got = self._open_realsense()
        if got:
            pipe, align = got
        else:
            self.camera_info = dict(source='webcam', depth_scale_m=None)
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"[에러] 카메라 {self.camera_index}번을 열 수 없습니다.")
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, RS_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RS_H)

        mp_hands, draw, styles = (mp.solutions.hands, mp.solutions.drawing_utils,
                                  mp.solutions.drawing_styles)
        hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.65,
                               min_tracking_confidence=0.55)
        prev_t = time.time()

        while self.running:
            vis_depth = None
            color_num = color_ts = depth_num = depth_ts = None
            if pipe is not None:
                try:
                    frames = align.process(pipe.wait_for_frames(timeout_ms=2000))
                except Exception:
                    time.sleep(0.01)
                    continue
                cf, df = frames.get_color_frame(), frames.get_depth_frame()
                if not cf:
                    time.sleep(0.01)
                    continue
                frame = np.asanyarray(cf.get_data()).copy()      # 항상 비미러 원본
                # 하드웨어 프레임 번호/타임스탬프. 컬러-depth 정렬 여부를 사후에 검증할 수 있다.
                try:
                    color_num, color_ts = int(cf.get_frame_number()), float(cf.get_timestamp())
                except Exception:
                    pass
                if df:
                    try:
                        depth_num, depth_ts = int(df.get_frame_number()), float(df.get_timestamp())
                    except Exception:
                        pass
                    # 측정용: 정렬된 raw depth. 후처리·미러링을 거치지 않는다.
                    self.latest_depth = (np.asanyarray(df.get_data()).astype(np.float32)
                                         * self.depth_scale)
                    self.depth_intr = df.profile.as_video_stream_profile().get_intrinsics()
                    vis_depth = self.latest_depth
                    if self.depth_filters and self.view_mode != VIEW_COLOR:
                        try:
                            dfv = df
                            for f in self.depth_filters:
                                dfv = f.process(dfv)
                            vis_depth = (np.asanyarray(dfv.get_data()).astype(np.float32)
                                         * self.depth_scale)
                        except Exception:
                            vis_depth = self.latest_depth
                else:
                    self.latest_depth = self.depth_intr = None
            else:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                self.latest_depth = self.depth_intr = None

            now = time.time()
            dt_frame = now - prev_t
            fps = 1.0 / max(dt_frame, 1e-6)
            if 0.0 < dt_frame < 1.0:      # 창 최소화 등으로 멈춘 구간은 표본에서 뺀다
                self._dt_hist.append(dt_frame)
            prev_t, t = now, now - self.t0
            self.frame_id += 1
            # perf_counter는 시스템 시계 변경에 영향받지 않아 구간 길이 계산에 쓰고,
            # unix 시각은 외부 장비(EMG 등)와의 동기화용으로 함께 남긴다.
            cap_mono, cap_unix = time.perf_counter(), now

            # ---- 영상 기록: 랜드마크를 그리기 전의 원본을 먼저 저장 ----
            if self._rec_release:
                self._rec_release = self._rec_request = False
                self._close_writers()
            if self._rec_request and self.rec_raw is None and self._rec_folder:
                self._rec_request = False
                self._open_writers(frame)
            if self.rec_raw is not None:
                self.rec_raw.write(frame)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            res = hands.process(rgb)

            has_depth = self.latest_depth is not None
            mode = self.view_mode if has_depth else VIEW_COLOR
            dvis = self._colorize_depth(vis_depth) if (has_depth and mode != VIEW_COLOR) else None
            canvases = [frame] + ([dvis] if dvis is not None else [])

            angles_out, hands3d, measures = {}, {}, {}
            overlays = []
            n_hands = 0
            lm_meta, ambiguous = {}, False

            if res.multi_hand_landmarks:
                n_hands = len(res.multi_hand_landmarks)
                wl = res.multi_hand_world_landmarks
                h_img, w_img = frame.shape[:2]

                # MediaPipe는 셀피(미러) 영상을 가정한다. 항상 원본을 넣으므로 라벨을 뒤집는다.
                labels, scores = [], []
                for i in range(n_hands):
                    cls = (res.multi_handedness[i].classification[0]
                           if res.multi_handedness and i < len(res.multi_handedness) else None)
                    labels.append({'Left': 'Right', 'Right': 'Left'}.get(
                        cls.label if cls else None))
                    scores.append(float(cls.score) if cls else None)

                for i, lms in enumerate(res.multi_hand_landmarks):
                    hand = labels[i]
                    # 같은 라벨이 둘이면 어느 쪽인지 확정할 수 없다. 조용히 덮어쓰지 않는다.
                    if hand is None or labels.count(hand) != 1:
                        ambiguous = True
                        continue

                    for c in canvases:
                        draw.draw_landmarks(c, lms, mp_hands.HAND_CONNECTIONS,
                                            styles.get_default_hand_landmarks_style(),
                                            styles.get_default_hand_connections_style())

                    pixels = np.array([[l.x * w_img, l.y * h_img] for l in lms.landmark])
                    wx, wy = pixels[0]

                    # ---- (A) depth 기반 실측 3D ----
                    meas = None
                    if self.enable_depth3d:
                        meas = measure_depth_hand(pixels, self.latest_depth, self.depth_intr)
                        measures[hand] = meas

                    # 손 거리는 depth 측정 결과에서만 가져온다.
                    # (주변 화소 중앙값은 사실상 홀 필링이라 쓰지 않는다)
                    dist = None
                    if meas:
                        dist = meas['wrist_z_m'] if meas['wrist_z_m'] is not None else meas['hand_z_m']

                    # ---- (B) MediaPipe world landmark 3D ----
                    world = wl[i].landmark if (wl and i < len(wl)) else None
                    rec = self.build_3d(hand, world, t, dist)
                    if rec:
                        hands3d[hand] = rec

                    txt = f"{hand}  " + (f"{dist:.2f}m" if dist else "dist --")
                    if rec:
                        m = rec['metrics']
                        ap = m['aperture_mm_cal'] or m['aperture_mm']
                        txt += f" | MP {ap:.0f}mm" + ("*" if m['aperture_mm_cal'] else "")
                    if meas:
                        txt += (f" | RS {meas['aperture_mm']:.0f}mm"
                                if meas['aperture_mm'] is not None else " | RS --")
                        txt += f" ({meas['n_valid']}/21)"
                    overlays.append((txt, wx, wy))

                    # ---- 각도 산출 + 필터 (MediaPipe 경로) ----
                    src = world if world is not None else lms.landmark
                    W = np.array([[l.x, l.y, l.z] for l in src], dtype=np.float64)
                    raw = joint_angles(W)
                    raw['Grip_Aperture'] = float(np.linalg.norm(W[4] - W[8]) * 100)  # cm

                    # 랜드마크 원본(픽셀 + world 좌표)은 평활화 전 값으로 남긴다.
                    lm_meta[hand] = {'pixels': pixels.copy(), 'world': W.copy(),
                                     'score': scores[i], 'world_is_metric': world is not None}

                    canon_src = rec['canon'] if rec else palm_frame(W)[0]
                    pab, rab = thumb_abduction(canon_src)
                    raw['Thumb_PalmarAbd'] = pab if pab is not None else 0.0
                    raw['Thumb_RadialAbd'] = rab if rab is not None else 0.0

                    filt = {}
                    for k, v in raw.items():
                        if k == 'Grip_Aperture':
                            key = f"{hand}_ap"
                            self.ap_filters.setdefault(key, ApertureFilter(v))
                            filt[k] = self.ap_filters[key].update(t, v) if self.use_filter else v
                        elif k in ABD_KEYS:
                            key = f"{hand}_{k}"
                            self.ap_filters.setdefault(
                                key, ApertureFilter(v, vmax=180.0, cutoff=0.7, beta=0.015))
                            filt[k] = self.ap_filters[key].update(t, v) if self.use_filter else v
                        else:
                            key = f"{hand}_{k}"
                            self.filters.setdefault(key, AngleFilter(v))
                            filt[k] = self.filters[key].update(t, v) if self.use_filter else v
                    angles_out[hand] = {'raw': raw, 'filtered': filt}

            # ---- 랜드마크가 그려진 프레임 기록 (미러링 전) ----
            if self.rec_mp is not None:
                self.rec_mp.write(frame)
                self.rec_frames += 1

            frame_meta = {
                'frame_id': self.frame_id,
                'capture_monotonic_s': cap_mono, 'capture_unix_s': cap_unix,
                'color_frame_number': color_num, 'color_timestamp_ms': color_ts,
                'depth_frame_number': depth_num, 'depth_timestamp_ms': depth_ts,
                'ambiguous_handedness': ambiguous, 'hands': lm_meta,
            }

            # ---- 표시 직전에만 미러링 ----
            if self.mirror_mode:
                frame = cv2.flip(frame, 1)
                if dvis is not None:
                    dvis = cv2.flip(dvis, 1)
            w_disp = frame.shape[1]
            display = ([frame] if mode in (VIEW_COLOR, VIEW_BOTH) else []) + \
                      ([dvis] if (dvis is not None and mode in (VIEW_DEPTH, VIEW_BOTH)) else [])
            for txt, wx, wy in overlays:
                x = (w_disp - 1 - wx) if self.mirror_mode else wx
                for c in display:
                    self._put(c, txt, max(0, int(x) - 90), max(24, int(wy) - 16),
                              (0, 255, 0), 0.6)

            self.frame_processed.emit(self._compose(mode, frame, dvis),
                                      angles_out, fps, n_hands, hands3d, measures,
                                      frame_meta)

        self._close_writers()
        if pipe:
            try:
                pipe.stop()
            except Exception:
                pass
        if cap:
            cap.release()
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
        self.wait(2000)


# ============================ 실시간 차트 ============================
class LiveAngleChart(FigureCanvas):
    """오른손/왼손 5손가락 대표 굴곡각(PIP·엄지 IP) 2단 시계열."""

    def __init__(self, parent=None, w=6, h=4.2, dpi=100):
        self.fig = Figure(figsize=(w, h), dpi=dpi)
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
            ax.set_ylabel(f"{HAND_KR[hand]}\n굴곡각(°)", color="#cbd5e1", fontsize=8, fontweight='bold')
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
        self.fig.tight_layout(pad=1.2)
        self.fig.subplots_adjust(hspace=0.12)
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
        self.fig.subplots_adjust(left=.01, right=.99, top=.93, bottom=.02, wspace=.02)

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

    def update_hands(self, t, hands3d, measures=None):
        if self._last is not None and t - self._last < VIEW3D_INTERVAL:
            return
        self._last = t
        measures = measures or {}
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
            ap = m['aperture_mm_cal'] or m['aperture_mm']
            txt = f"{HAND_KR[hand]}  ·  MP {ap:.0f}mm"
            if m['aperture_mm_cal']:
                txt += "*"
            meas = measures.get(hand)
            if meas:
                txt += ("  ·  RS %.0fmm" % meas['aperture_mm']
                        if meas['aperture_mm'] is not None else "  ·  RS --")
                txt += f" ({meas['n_valid']}/21)"
            if m['wrist_dist_m']:
                txt += f"  ·  {m['wrist_dist_m']:.2f}m"
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
class ClinicalApp(QMainWindow):
    TABLE_COLS = ["회차", "손", "과제", "소요시간", "사이클", "주기(s)",
                  "TAM(°)", "CMC(°)", "외전(°)", "MGA(cm)", "굴곡속도", "SPARC",
                  "RS MGA(mm)", "RS유효%"]
    TASKS = ["Task 1: 맨손 쥐기/펴기 (Free Motion)", "Task 2: 구형 파지 (Sphere)",
             "Task 3: 원통형 파지 (Cylinder)", "Task 4: 정육면체 파지 (Cube)"]
    # 양손이 모두 인식돼야 기록하는 과제 (양손 동시 파지 프로토콜)
    BOTH_HANDS_TASKS = ("Task 4",)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 미러테라피 · 손 기능 평가 (MediaPipe 3D + RealSense depth)")
        self.resize(1660, 1010)
        self.setMinimumSize(1400, 880)
        self.setStyleSheet(QSS)

        self.session_on = self.trial_on = self.paused = False
        self.t_session = self.t_trial = 0.0
        self.auto_left, self._last_tick = 0.0, time.time()
        self.records, self.trials, self.trial_idx = [], [], 1
        self.frames_qc = []              # 프레임 단위 QC 로그 (손 미인식 프레임 포함)
        self.trial_interrupted = False   # 구간 중 손 놓침 여부
        self.prefix = ""
        self.folder = ""
        self.t_app = time.time()
        self.gauges, self.glabels, self.gtitles = {}, {}, {}
        self.qc_ok = deque(maxlen=QC_WINDOW)     # 프레임당 유효 랜드마크 수
        self.qc_dist = deque(maxlen=QC_WINDOW)

        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     "outputs", "데이터_저장"))
        os.makedirs(self.base_dir, exist_ok=True)

        self._build_ui()
        for key, fn in (("Q", self.close), ("q", self.close), ("Esc", self.close),
                        ("M", lambda: self.chk_mirror.toggle()),
                        ("m", lambda: self.chk_mirror.toggle()),
                        ("D", self._cycle_view), ("d", self._cycle_view),
                        ("Space", self._space)):
            QShortcut(QKeySequence(key), self).activated.connect(
                lambda f=fn: None if isinstance(self.focusWidget(), QLineEdit) else f())

        self.worker = VideoWorker(0)
        self.worker.frame_processed.connect(self.on_frame)
        self.worker.set_palm_calib(self.spin_palm.value())
        self.worker.set_enable_depth3d(self.chk_depth3d.isChecked())
        self.worker.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(100)

    # ------------------------------ UI ------------------------------
    def _build_ui(self):
        cw = QWidget(self)
        self.setCentralWidget(cw)
        main = QHBoxLayout(cw)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)
        main.addWidget(self._left_panel())
        main.addWidget(self._right_panel(), stretch=1)

    def _left_panel(self):
        panel = QWidget()
        panel.setFixedWidth(440)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

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
        self.txt_name = QLineEdit("")
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
                                  "입력하면 MediaPipe 파지폭(mm)이 피험자 손 크기로 보정됩니다.\n"
                                  "RealSense depth 측정값은 이미 실제 mm라 보정하지 않습니다.")
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
        f4.addWidget(self.cb_task)
        lay.addWidget(g4)

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
        auto_row.addWidget(QLabel("자동 측정 길이 (비장애인):"))
        auto_row.addWidget(self.spin_auto)
        f5.addLayout(auto_row)

        row = QHBoxLayout()
        self.btn_start = QPushButton("▶  전체 세션 시작")
        self.btn_start.setObjectName("start")
        self.btn_start.clicked.connect(self.start_session)
        self.btn_stop = QPushButton("■  세션 종료 및 저장")
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

        self.table = QTableWidget(0, len(self.TABLE_COLS))
        self.table.setHorizontalHeaderLabels(self.TABLE_COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setFixedHeight(180)
        f5.addWidget(self.table)
        lay.addWidget(g5)
        return panel

    def _right_panel(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        card = QFrame()
        card.setStyleSheet("background:#141724; border-radius:8px; border:1px solid #282f48;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)

        head = QHBoxLayout()
        self.lbl_session = QLabel("● READY (대기 중)")
        self.lbl_session.setStyleSheet("color:#10b981; font-weight:bold; font-size:14px;")
        self.lbl_trial = QLabel("대기 상태")
        self.lbl_trial.setStyleSheet("color:#94a3b8; font-weight:bold;")
        self.cb_view = QComboBox()
        self.cb_view.addItems(["컬러 영상", "Depth 영상", "컬러 + Depth"])
        self.cb_view.setFixedWidth(130)
        self.cb_view.currentIndexChanged.connect(self._on_view)

        self.chk_mirror = QCheckBox("미러링 (M)")
        self.chk_mirror.setToolTip("화면 출력만 좌우 반전합니다.\n"
                                   "랜드마크·depth·intrinsics는 항상 원본 좌표계로 측정됩니다.")
        self.chk_mirror.toggled.connect(self._on_mirror)
        self.chk_filter = QCheckBox("생체역학 필터")
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda v: self.worker.set_filter_mode(v))
        self.chk_3d = QCheckBox("MP 3D")
        self.chk_3d.setChecked(True)
        self.chk_3d.setToolTip("MediaPipe world landmark 기반 정준화 3D.")
        self.chk_3d.toggled.connect(self._on_3d)
        self.chk_depth3d = QCheckBox("Depth 3D 측정")
        self.chk_depth3d.setChecked(True)
        self.chk_depth3d.setToolTip("정렬된 RealSense depth를 intrinsics로 역투영해\n"
                                    "랜드마크의 실제 3D 좌표(m)를 계산합니다.")
        self.chk_depth3d.toggled.connect(self._on_depth3d)
        self.chk_smooth = QCheckBox("3D 좌표 스무딩")
        self.chk_smooth.setChecked(LM_SMOOTH_DEFAULT)
        self.chk_smooth.setToolTip("MediaPipe 랜드마크 (x,y,z)에 One-Euro를 겁니다.\n"
                                   "depth 측정 경로에는 적용되지 않습니다.")
        self.chk_smooth.toggled.connect(self._on_smooth)

        self.lbl_fps = QLabel("FPS: -- | Hands: 0")
        self.lbl_fps.setStyleSheet("color:#94a3b8; font-size:12px;")
        btn_folder = QPushButton("📂 저장 폴더")
        btn_folder.clicked.connect(self._open_folder)
        btn_exit = QPushButton("✕ 종료 (Q)")
        btn_exit.clicked.connect(self.close)

        head.addWidget(self.lbl_session)
        head.addSpacing(12)
        head.addWidget(self.lbl_trial)
        head.addStretch()
        head.addWidget(QLabel("보기:"))
        head.addWidget(self.cb_view)
        for w in (self.chk_mirror, self.chk_filter, self.chk_3d, self.chk_depth3d,
                  self.chk_smooth):
            head.addSpacing(8)
            head.addWidget(w)
        head.addSpacing(12)
        head.addWidget(self.lbl_fps)
        head.addWidget(btn_folder)
        head.addWidget(btn_exit)
        cl.addLayout(head)

        # 촬영 중에 결측을 알아채기 위한 QC 표시. 세션이 끝난 뒤에 발견하면 늦다.
        self.lbl_qc = QLabel("QC: depth 측정 대기 중")
        self.lbl_qc.setStyleSheet("color:#94a3b8; font-size:12px; font-weight:bold; "
                                  "padding:3px 8px; background:#12141f; border-radius:4px;")
        cl.addWidget(self.lbl_qc)

        self.lbl_video = QLabel("카메라 연결 중...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(300)
        self.lbl_video.setStyleSheet("background:#08090e; border-radius:6px;")
        cl.addWidget(self.lbl_video)

        grow = QHBoxLayout()
        grow.setSpacing(10)
        for hand in HANDS:
            grow.addWidget(self._gauge_panel(hand), stretch=1)
        cl.addLayout(grow)
        lay.addWidget(card, stretch=5)

        chart = QFrame()
        chart.setStyleSheet("background:#141724; border-radius:8px; border:1px solid #282f48;")
        cc = QVBoxLayout(chart)
        cc.setContentsMargins(8, 6, 8, 6)
        panes = QHBoxLayout()
        panes.setSpacing(10)
        self.chart = LiveAngleChart(self)
        self.view3d = Hand3DView(self)
        for title, w in (("5손가락 대표 굴곡각 궤적 (위: 오른손 / 아래: 왼손)", self.chart),
                         ("3D 관절 공간 (MP 정준화 · 제목에 RS 실측 파지폭 병기)", self.view3d)):
            col = QVBoxLayout()
            col.setSpacing(4)
            lbl = QLabel(title)
            lbl.setStyleSheet("font-size:11px; font-weight:bold; color:#e2e8f0;")
            col.addWidget(lbl)
            col.addWidget(w)
            panes.addLayout(col, stretch=1)
        cc.addLayout(panes)
        self.lbl_toast = QLabel("안내: [세션 시작] 후 동작 시작·종료 시 [Space]를 누르세요.")
        self.lbl_toast.setStyleSheet("color:#94a3b8; font-size:12px; padding:2px 6px;")
        cc.addWidget(self.lbl_toast)
        lay.addWidget(chart, stretch=5)
        return panel

    # ------------------ 게이지 (근위/중간/원위 · 엄지는 CMC/MCP/IP) ------------------
    def _gauge_panel(self, hand):
        panel = QFrame()
        panel.setStyleSheet("QFrame{background:#12141f;border:1px solid #282f48;border-radius:6px;}")
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(4)
        title = QLabel(f"{HAND_KR[hand]}  ·  미인식")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:11px; font-weight:bold; color:#64748b; border:none;")
        v.addWidget(title)
        self.gtitles[hand] = title

        row = QHBoxLayout()
        row.setSpacing(10)
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
                lbl.setFixedWidth(62)
                lbl.setStyleSheet(f"font-size:10px; font-weight:bold; color:{col_hex}; border:none;")
                bar = QProgressBar()
                bar.setRange(0, 180)
                bar.setValue(0)
                bar.setTextVisible(False)
                bar.setFixedHeight(9)
                bar.setStyleSheet(
                    "QProgressBar{background:#191c2b;border:1px solid #334155;border-radius:3px;}"
                    f"QProgressBar::chunk{{background:{col_hex};border-radius:2px;}}")
                bar.setEnabled(jname is not None)
                grid.addWidget(lbl, r, 0)
                grid.addWidget(bar, r, 1)
                self.gauges[hand][f][seg], self.glabels[hand][f][seg] = bar, lbl
            grid.setColumnStretch(1, 1)
            col.addLayout(grid)
            row.addLayout(col, stretch=1)
        v.addLayout(row)
        return panel

    def _update_gauge(self, hand, data, meas=None):
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
        dist = meas['wrist_z_m'] if (meas and meas['wrist_z_m'] is not None) else \
               (meas['hand_z_m'] if meas else None)
        head = f"{HAND_KR[hand]}  ·  인식됨  ·  " + (f"{dist:.2f} m" if dist else "dist --")
        if abd is not None and np.isfinite(abd):
            head += f"  ·  엄지 외전 {abd:.0f}°"
        if meas:
            head += ("  ·  RS %.0fmm" % meas['aperture_mm']
                     if meas['aperture_mm'] is not None else "  ·  RS --")
            head += f" ({meas['n_valid']}/21)"
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

    def _update_qc(self, measures):
        """유효 랜드마크 비율과 거리로 촬영 조건을 즉시 알려준다."""
        for m in measures.values():
            self.qc_ok.append(m['n_valid'] / 21.0)
            d = m['wrist_z_m'] if m['wrist_z_m'] is not None else m['hand_z_m']
            if d is not None:
                self.qc_dist.append(d)
        if not self.qc_ok:
            return
        rate = float(np.mean(self.qc_ok))
        dist = float(np.median(self.qc_dist)) if self.qc_dist else None
        msgs = [f"QC: 유효 랜드마크 {rate*100:.0f}%"]
        color = '#10b981'
        if dist is not None:
            msgs.append(f"거리 {dist:.2f} m")
            if dist < WORK_MIN_M:
                msgs.append(f"⚠ 너무 가까움 (권장 {WORK_MIN_M:.2f}~{WORK_MAX_M:.2f} m)")
                color = '#f97316'
            elif dist > WORK_MAX_M:
                msgs.append(f"⚠ 너무 멈 (권장 {WORK_MIN_M:.2f}~{WORK_MAX_M:.2f} m)")
                color = '#f97316'
        else:
            msgs.append("거리 --")
            color = '#f97316'
        if rate < 0.5:
            msgs.append("⚠ depth 결측 과다 · 배경/조명/거리 확인")
            color = '#ef4444'
        self.lbl_qc.setText("   ·   ".join(msgs))
        self.lbl_qc.setStyleSheet(f"color:{color}; font-size:12px; font-weight:bold; "
                                  "padding:3px 8px; background:#12141f; border-radius:4px;")

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
        # 표시만 반전되므로 필터·차트 상태를 리셋할 필요가 없다.
        self.worker.set_mirror_mode(v)
        self.toast(f"미러링(표시 전용): {'ON' if v else 'OFF'}")

    def _on_3d(self, v):
        self.worker.set_enable_3d(v)
        if not v:
            self.view3d.reset_view()
        self.toast(f"MediaPipe 3D: {'ON' if v else 'OFF'}")

    def _on_depth3d(self, v):
        self.worker.set_enable_depth3d(v)
        if not v:
            self.toast("Depth 3D 측정: OFF (RS 열이 빈 칸으로 저장됩니다)")
        elif self.worker.source_name != "realsense":
            self.toast("⚠️ RealSense 미연결 → depth 측정값을 얻을 수 없습니다.")
        else:
            self.toast("Depth 3D 측정: ON")

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
            + ("" if (not starting and self._auto_mode()) else " (Space)"))
        self.btn_trial.setStyleSheet("" if starting else
                                     "#trial{background:#ea580c;border:2px solid #fdba74;}")

    def _status(self, text, color):
        self.lbl_trial.setText(text)
        self.lbl_trial.setStyleSheet(f"color:{color}; font-weight:bold;")

    # ---------------------------- 세션 ----------------------------
    def start_session(self):
        name = self.txt_name.text().strip()
        if not name:
            return self.toast("경고: 피험자 이름을 입력해주세요!")

        d, age = f"{datetime.now():%Y%m%d}", self.spin_age.value()
        g = "남" if "남성" in self.cb_gender.currentText() else "여"
        sub = (f"{d}_비장애인_{name}_{age}세_{g}" if self.rb_healthy.isChecked() else
               f"{d}_환자_{name}_{age}세_{g}_FMA{self.spin_fma.value()}_BRS{self.cb_brs.currentIndex()+1}")
        self.folder = os.path.join(self.base_dir, sub)
        os.makedirs(self.folder, exist_ok=True)

        # 같은 피험자 폴더에서 세션을 여러 번 돌려도 파일이 겹치지 않도록
        # 마이크로초 + 난수 8자리를 붙인다. 영상 기록과 시작 시각이 일치한다.
        self.prefix = (f"Session_{datetime.now():%Y%m%d_%H%M%S_%f}"
                       f"_{uuid.uuid4().hex[:8]}")

        self.session_on, self.trial_on, self.paused = True, False, False
        self.t_session, self.trial_idx = time.time(), 1
        self.records.clear()
        self.trials.clear()
        self.frames_qc.clear()
        self.trial_interrupted = False
        self.table.setRowCount(0)
        self.chart.reset_chart()
        self.worker.start_recording(self.folder)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_trial.setEnabled(True)
        self._trial_btn(True)
        for w in (self.txt_name, self.spin_age, self.cb_gender,
                  self.rb_healthy, self.rb_patient, self.spin_auto):
            w.setEnabled(False)

        self.lbl_session.setText("● REC (기록 중...)")
        self.lbl_session.setStyleSheet("color:#ef4444; font-weight:bold; font-size:14px;")
        self._status("준비됨 (동작 시작 대기)", "#38bdf8")
        self.toast(f"▶ [{self.cb_task.currentText()}] 세션 시작! (영상 기록 포함)", ok=True)

    def toggle_trial(self):
        if not self.session_on or not self.records:
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
        self.trial_interrupted = False
        self.t_trial = time.time() - self.t_session
        if self._auto_mode():
            self.auto_left = float(self.spin_auto.value())
            self._last_tick = time.time()
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

    def _finish_trial(self):
        auto = self._auto_mode()
        interrupted = self.trial_interrupted
        requested = float(self.spin_auto.value()) if auto else None
        self.trial_on, self.auto_left = False, 0.0
        t = time.time() - self.t_session
        t0, dur = self.t_trial, max(0.01, t - self.t_trial)
        task = self.cb_task.currentText()
        short = task.split(":")[0].strip()

        low_qc = []
        for hand in HANDS:
            seg = [r for r in self.records if r['hand'] == hand and t0 <= r['time'] <= t]
            if not seg:
                continue
            tr = self._trial_metrics(seg)
            tr.update(trial=self.trial_idx, hand=hand, task=task, task_short=short,
                      start=t0, end=t, duration=dur, auto=auto,
                      requested=requested, interrupted=interrupted)
            self.trials.append(tr)
            if tr['rs_valid_n'] < RS_MIN_VALID_FRAMES:
                low_qc.append(HAND_KR[hand].split(' ')[0])

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
                     f"{tr['sparc']:.2f}" if tr['sparc'] is not None else "-",
                     f"{tr['rs_mga_p95']:.1f}" if tr['rs_mga_p95'] is not None else "-",
                     f"{tr['rs_valid_rate']*100:.0f}%"]
            for c, txt in enumerate(cells):
                self.table.setItem(row, c, QTableWidgetItem(txt))
        self.table.scrollToBottom()
        self.chart.add_trial_span(t0, t)

        self.trial_idx += 1
        self.btn_trial.setEnabled(self.session_on and not self.paused)
        self._trial_btn(True)
        self._status(f"완료됨 (총 {len({x['trial'] for x in self.trials})}회)", "#10b981")
        if low_qc:
            self.toast(f"⚠️ [Trial #{self.trial_idx-1}] {'/'.join(low_qc)} depth 유효 프레임 "
                       f"{RS_MIN_VALID_FRAMES}개 미만 → RS 요약값 미보고")
        else:
            self.toast(f"✅ [Trial #{self.trial_idx-1} - {short}] 기록 완료 ({dur:.2f}초)", ok=True)

    @staticmethod
    def _trial_metrics(seg):
        """구간 지표: 개폐 사이클/주기, TAM, 엄지 CMC/외전, MGA, 각속도, SPARC,
        그리고 depth 실측 경로의 파지폭·유효율·상태 분포."""
        filt = [r['filtered'] for r in seg]
        raws = [r['raw'] for r in seg]
        mga = max((f.get('Grip_Aperture', 0.0) for f in filt), default=0.0)   # cm
        pips = [f.get('Index_PIP', 180.0) for f in filt]
        rom = max(pips) - min(pips) if pips else 0.0

        # 관절별 ROM은 CMC 포함 전 관절, TAM 합산은 ASSH 정의(엄지 = MCP + IP)만
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
        times, flex = [], []
        for r in seg:
            vs = [r['filtered'][j] for j in CYCLE_JOINTS if r['filtered'].get(j) is not None]
            if vs:
                times.append(r['time'])
                flex.append(float(np.mean(vs)))
        cycles, period = count_cycles(times, flex)
        vel = ang_velocity(times, flex)
        fs = float(np.max(-vel)) if vel is not None and len(vel) else None
        es = float(np.max(vel)) if vel is not None and len(vel) else None
        sp = sparc(vel, times) if vel is not None else None

        def m3(key):
            vals = [r['metrics3d'].get(key) for r in seg if r.get('metrics3d', {}).get(key)]
            return max(vals) if vals else None

        p3 = [r['angles3d'].get('Index_PIP') for r in seg
              if r.get('angles3d', {}).get('Index_PIP') is not None]

        # 표본 사이가 크게 벌어진 구간(손 놓침)은 유효 측정시간에서 뺀다.
        all_t = [r['time'] for r in seg]
        valid_dur = float(sum(b - a for a, b in zip(all_t, all_t[1:])
                              if 0 < (b - a) < VALID_GAP_MAX_S))

        # ---- depth(RS) 경로 ----
        rs_ap = [r['rs']['aperture_mm'] for r in seg
                 if r.get('rs') and r['rs'].get('aperture_mm') is not None]
        rs_valid_n = len(rs_ap)
        rs_rate = rs_valid_n / len(seg) if seg else 0.0
        rs_pip = [r['rs']['angles'].get('Index_PIP') for r in seg
                  if r.get('rs') and r['rs']['angles'].get('Index_PIP') is not None]
        rs_nv = [r['rs']['n_valid'] for r in seg if r.get('rs')]
        rs_dist = [r['rs']['wrist_z_m'] for r in seg
                   if r.get('rs') and r['rs']['wrist_z_m'] is not None]
        # 최대값은 단일 프레임 이상치에 지배당한다. p95를 기본 지표로 쓰고
        # 유효 프레임이 부족하면 아예 보고하지 않는다.
        enough = rs_valid_n >= RS_MIN_VALID_FRAMES
        rs_p95 = float(np.percentile(rs_ap, 95)) if enough else None
        rs_max = float(np.max(rs_ap)) if enough else None

        # ---- MP vs RS 쌍 비교 (같은 프레임에서 둘 다 유효한 경우만) ----
        # 필터·보정을 거치지 않은 원본끼리 비교해야 두 방법의 차이가 그대로 남는다.
        mp_ap_raw = [d['Grip_Aperture'] * 10.0 for d in raws
                     if d.get('Grip_Aperture') is not None]
        diffs = []
        for r in seg:
            rsd = r.get('rs')
            mp_v = (r['raw'].get('Grip_Aperture') * 10.0
                    if r['raw'].get('Grip_Aperture') is not None else None)
            rs_v = rsd['aperture_mm'] if (rsd and rsd.get('aperture_mm') is not None) else None
            if mp_v is not None and rs_v is not None:
                diffs.append(rs_v - mp_v)

        st_count = {k: 0 for k in DEPTH_STATUSES}
        for r in seg:
            if not r.get('rs'):
                continue
            for st in r['rs']['status']:
                st_count[st] = st_count.get(st, 0) + 1

        return dict(mga=mga, rom=rom, tarom=tarom, tam_f=tam_f, tam_j=tam_j,
                    cmc_rom=tam_j.get('Thumb_CMC'),
                    pab_max=pab_max, pab_rom=pab_rom, rab_max=rab_max, rab_rom=rab_rom,
                    cycles=cycles, period=period,
                    flex_speed=fs, ext_speed=es, sparc=sp,
                    mga3d=m3('aperture_mm'), mga3d_cal=m3('aperture_mm_cal'),
                    rom3d=(max(p3) - min(p3)) if len(p3) >= 2 else None,
                    samples=len(seg), valid_duration=valid_dur,
                    mp_mga_raw=max(mp_ap_raw) if mp_ap_raw else None,
                    rs_mga_raw=float(np.max(rs_ap)) if rs_ap else None,
                    paired_n=len(diffs),
                    diff_mean=float(np.mean(diffs)) if diffs else None,
                    abs_diff_mean=float(np.mean(np.abs(diffs))) if diffs else None,
                    rs_mga_p95=rs_p95, rs_mga_max=rs_max,
                    rs_ap_mean=float(np.mean(rs_ap)) if enough else None,
                    rs_valid_n=rs_valid_n, rs_valid_rate=rs_rate,
                    rs_rom=(max(rs_pip) - min(rs_pip)) if len(rs_pip) >= 2 else None,
                    rs_landmarks_mean=float(np.mean(rs_nv)) if rs_nv else None,
                    rs_dist_median=float(np.median(rs_dist)) if rs_dist else None,
                    rs_status_count=st_count)

    def stop_session(self):
        if not self.session_on:
            return
        if self.trial_on:
            self._finish_trial()
        self.session_on = False
        self.worker.stop_recording()
        dur = time.time() - self.t_session

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_trial.setEnabled(False)
        for w in (self.txt_name, self.spin_age, self.cb_gender, self.rb_healthy, self.rb_patient):
            w.setEnabled(True)
        self.spin_auto.setEnabled(self.rb_healthy.isChecked())
        self.lbl_session.setText("● READY (세션 완료)")
        self.lbl_session.setStyleSheet("color:#10b981; font-weight:bold; font-size:14px;")

        n = len({x['trial'] for x in self.trials})
        self._status(f"총 {n}회차 저장됨", "#10b981")
        self.save_session(dur)
        self.toast(f"✅ 저장 완료! {n}개 회차 ({dur:.1f}초)", ok=True)

    # ---------------------------- 저장 ----------------------------
    @staticmethod
    def _f(v, fmt="{:.2f}"):
        """None/NaN은 빈 칸으로 (0으로 채우면 실제 0과 구분 불가)."""
        try:
            return fmt.format(v) if v is not None and np.isfinite(v) else ""
        except TypeError:
            return ""

    def _phase_of(self, rec):
        for tr in self.trials:
            if tr['hand'] == rec['hand'] and tr['start'] <= rec['time'] <= tr['end']:
                return tr['task'], f"Trial_{tr['trial']}", "Grasping"
        return rec['task'], "Rest", "Rest"

    def save_session(self, duration):
        if not self.records:
            return self.toast("⚠️ 수집된 데이터가 없어 저장을 건너뜁니다.")
        pre = self.prefix or f"Session_{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid.uuid4().hex[:8]}"

        self._save_continuous(os.path.join(self.folder, f"{pre}_continuous_raw.csv"))
        self._save_landmarks(os.path.join(self.folder, f"{pre}_landmarks.csv"))
        self._save_trials(os.path.join(self.folder, f"{pre}_trials_summary.csv"))
        self._save_frame_quality(os.path.join(self.folder, f"{pre}_frame_quality.csv"))
        self._save_distance(os.path.join(self.folder, f"{pre}_distance_comparison.csv"))

        self.export_plot(os.path.join(self.folder, f"{pre}_waveform.png"), pre)
        self.export_joint_plot(os.path.join(self.folder, f"{pre}_joint_angles.png"), pre)

        # 세션 메타데이터가 필요하면 아래 한 줄을 살리면 된다 (subject_metadata.json).
        # self._save_metadata(duration)

    def _save_continuous(self, path):
        """프레임 단위 지표 + 정준 좌표. 하나의 행 = 한 프레임의 한 손."""
        f = self._f
        head = ["time_s", "Task", "Trial", "Phase", "hand"]
        for j in JOINT_DEFS:
            head += [f"{j}_raw", f"{j}_filt"]
        head += ["Grip_Aperture_cm_raw", "Grip_Aperture_cm_filt",
                 "Thumb_PalmarAbd_raw", "Thumb_PalmarAbd_filt",
                 "Thumb_RadialAbd_raw", "Thumb_RadialAbd_filt", "Wrist_Depth_m"]
        head += [f"{j}_3D" for j in JOINT_DEFS]
        head += ["Grip_Aperture_mm_3D", "Grip_Aperture_mm_3D_cal",
                 "Grip_Aperture_pctPalm_3D", "Palm_Len_mm_3D", "Recon_Mode"]
        for nm in LM_NAMES:
            head += [f"{nm}_canon_X", f"{nm}_canon_Y", f"{nm}_canon_Z"]
        head += ["Frame_ID", "Protocol_Valid"]

        with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(head)
            for rec in self.records:
                task, tag, phase = self._phase_of(rec)
                a3, m3 = rec.get('angles3d') or {}, rec.get('metrics3d') or {}
                canon = rec.get('canon')
                row = [f"{rec['time']:.4f}", task, tag, phase, rec['hand']]
                for j in JOINT_DEFS:
                    row += [f(rec['raw'].get(j)), f(rec['filtered'].get(j))]
                row += [f(rec['raw'].get('Grip_Aperture')), f(rec['filtered'].get('Grip_Aperture'))]
                for k in ABD_KEYS:
                    row += [f(rec['raw'].get(k)), f(rec['filtered'].get(k))]
                row += [f(m3.get('wrist_dist_m'), "{:.5f}")]
                row += [f(a3.get(j)) for j in JOINT_DEFS]
                row += [f(m3.get('aperture_mm'), "{:.1f}"), f(m3.get('aperture_mm_cal'), "{:.1f}"),
                        f(m3.get('aperture_pct_palm')), f(m3.get('palm_len_mm'), "{:.1f}"),
                        m3.get('mode', '')]
                for i in range(21):
                    row += ([f"{v:.4f}" for v in canon[i]] if canon is not None else [""] * 3)
                row += [rec.get('frame_id', ''), int(bool(rec.get('protocol_valid', True)))]
                w.writerow(row)

    def _save_landmarks(self, path):
        """좌표 전용 long-format. 픽셀·MP world·RS 실측을 한 행에 나란히 둔다.
        어느 랜드마크가 어떤 이유로 빠졌는지 그대로 집계할 수 있다."""
        f = self._f
        with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(["Frame_ID", "time_s", "Hand", "Landmark_ID", "Landmark",
                        "Pixel_U", "Pixel_V", "MP_X_m", "MP_Y_m", "MP_Z_m",
                        "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Depth_m", "RS_Status"])
            for rec in self.records:
                px, world, rsd = rec.get('pixels'), rec.get('world'), rec.get('rs')
                for i, nm in enumerate(LM_NAMES):
                    row = [rec.get('frame_id', ''), f"{rec['time']:.6f}", rec['hand'], i, nm]
                    row += ([f"{px[i][0]:.4f}", f"{px[i][1]:.4f}"] if px is not None
                            else ["", ""])
                    row += ([f"{v:.8f}" for v in world[i]] if world is not None else [""] * 3)
                    if rsd:
                        row += [f(v, "{:.6f}") for v in rsd['points'][i]]
                        row += [f(rsd['depths'][i], "{:.6f}"), rsd['status'][i]]
                    else:
                        row += [""] * 5
                    w.writerow(row)

    def _save_trials(self, path):
        f = self._f
        joint_cols = list(JOINT_DEFS)
        with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(["Trial", "Hand", "Task", "Trial_Mode",
                        "Start_s", "End_s", "Duration_s", "Cycles", "Cycle_Period_s",
                        "TAM_total_deg", "MGA_cm", "Index_ROM_deg",
                        "Flex_Speed_deg_s", "Ext_Speed_deg_s", "SPARC",
                        "MGA_mm_3D", "MGA_mm_3D_cal", "Index_ROM_3D_deg",
                        "Thumb_CMC_ROM_deg",
                        "Thumb_PalmarAbd_max_deg", "Thumb_PalmarAbd_ROM_deg",
                        "Thumb_RadialAbd_max_deg", "Thumb_RadialAbd_ROM_deg"]
                       + [f"TAM_{x}_deg" for x in FINGERS]
                       + [f"ROM_{j}_deg" for j in joint_cols]
                       + ["Valid_Duration_s", "Samples", "RS_Valid_Samples",
                          "Paired_Samples", "MP_MGA_raw_mm", "RS_MGA_raw_mm",
                          "RS_minus_MP_mean_mm", "RS_MP_mean_abs_difference_mm",
                          "Requested_Duration_s", "Interrupted"])
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
                           + [f(tr['valid_duration']), tr['samples'], tr['rs_valid_n'],
                              tr['paired_n'], f(tr['mp_mga_raw']), f(tr['rs_mga_raw']),
                              f(tr['diff_mean']), f(tr['abs_diff_mean']),
                              f(tr.get('requested')), int(bool(tr.get('interrupted')))])

    def _save_frame_quality(self, path):
        """프레임 단위 취득 품질. 손이 잡히지 않은 프레임도 남겨야
        '왜 그 구간이 비었는가'를 사후에 되짚을 수 있다."""
        with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(["time", "frame_id", "task", "hands", "protocol_valid",
                        "ambiguous_handedness", "capture_monotonic_s", "capture_unix_s"])
            for fr in self.frames_qc:
                w.writerow([repr(fr['time']), fr['frame_id'], fr['task'], fr['hands'],
                            fr['protocol_valid'], fr['ambiguous'],
                            repr(fr['mono']), repr(fr['unix'])])

    def _save_distance(self, path):
        """MP 추정 파지폭과 RS 실측 파지폭의 프레임별 대조표.
        신뢰도 비교의 원자료라, 둘 중 하나가 결측인 프레임도 그대로 남긴다."""
        f = self._f
        with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(["Frame_ID", "time_s", "capture_monotonic_s", "capture_unix_s",
                        "Hand", "Task", "Protocol_Valid", "MP_Valid", "RS_Valid",
                        "MP_Aperture_raw_mm", "MP_Aperture_cal_mm", "RS_Aperture_raw_mm",
                        "RS_minus_MP_mm", "RS_Thumb_Status", "RS_Index_Status",
                        "Handedness_Score", "Color_Frame_Number", "Color_Timestamp_ms",
                        "Depth_Frame_Number", "Depth_Timestamp_ms"])
            for rec in self.records:
                m3, rsd = rec.get('metrics3d') or {}, rec.get('rs')
                mp_ap = (rec['raw'].get('Grip_Aperture') * 10.0
                         if rec['raw'].get('Grip_Aperture') is not None else None)
                rs_ap = rsd['aperture_mm'] if rsd else None
                diff = (rs_ap - mp_ap) if (rs_ap is not None and mp_ap is not None) else None
                w.writerow([rec.get('frame_id', ''), f"{rec['time']:.6f}",
                            f(rec.get('mono'), "{:.6f}"), f(rec.get('unix'), "{:.6f}"),
                            rec['hand'], rec['task'],
                            int(bool(rec.get('protocol_valid', True))),
                            int(bool(m3)), int(bool(rsd and rsd.get('valid'))),
                            f(mp_ap, "{:.4f}"), f(m3.get('aperture_mm_cal'), "{:.4f}"),
                            f(rs_ap, "{:.4f}"), f(diff, "{:.4f}"),
                            rsd['status'][4] if rsd else "",
                            rsd['status'][8] if rsd else "",
                            f(rec.get('score'), "{:.4f}"),
                            rec.get('color_num') if rec.get('color_num') is not None else "",
                            f(rec.get('color_ts'), "{:.6f}"),
                            rec.get('depth_num') if rec.get('depth_num') is not None else "",
                            f(rec.get('depth_ts'), "{:.6f}")])

    def _save_metadata(self, duration):
        # 세션 전체 QC 요약을 메타데이터에 함께 남긴다.
        st_all = {k: 0 for k in DEPTH_STATUSES}
        nv, dist = [], []
        for rec in self.records:
            rsd = rec.get('rs')
            if not rsd:
                continue
            for s in rsd['status']:
                st_all[s] = st_all.get(s, 0) + 1
            nv.append(rsd['n_valid'])
            if rsd['wrist_z_m'] is not None:
                dist.append(rsd['wrist_z_m'])
        total = sum(st_all.values())

        meta = {
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
                                "metacarpal. Both are magnitudes, so left and right hands are "
                                "directly comparable."),
            "joint_defs": {k: list(v) for k, v in JOINT_DEFS.items()},
            "measurement_paths": {
                "MP": ("MediaPipe world landmark + One-Euro smoothing + SVD palm "
                       "canonicalization. Monocular model-scale estimate; absolute mm are "
                       "only meaningful after hand-length calibration."),
                "RS": ("MediaPipe image pixels (unmirrored) + unfiltered colour-aligned depth "
                       "+ aligned depth intrinsics, deprojected to metres. Independent of the "
                       "MP path; the two are never blended."),
            },
            "depth_gating": {
                "stage_1_pixel": {"centre_pixel_only": True, "hole_filling": False,
                                  "neighbourhood_px": DEPTH_NEIGHBOR,
                                  "valid_range_m": [DEPTH_MIN_M, DEPTH_MAX_M],
                                  "edge_reject_p10_p90_m": DEPTH_EDGE_M},
                "stage_2_hand_consistency": {"max_deviation_from_hand_median_m": DEPTH_HAND_DEV_M,
                                             "min_samples_for_reference": DEPTH_HAND_MIN_SAMPLES},
                "stage_3_anatomical": {"max_span_from_wrist_mm": LM_MAX_SPAN_MM,
                                       "max_aperture_mm": APERTURE_MAX_MM},
                "rationale": ("A local window cannot separate a fingertip from the background "
                              "behind it, so a pixel-level gate alone lets implausible points "
                              "through. Stages 2 and 3 reject those; every rejection keeps a "
                              "status code and the sample stays NaN. Never interpolate before "
                              "computing reliability statistics."),
                "status_codes": list(DEPTH_STATUSES),
            },
            "deprojection": ("rs2_deproject_pixel_to_point, except for modified "
                             "Brown-Conrady intrinsics where cv2.undistortPoints is used "
                             "because the SDK does not support that model."),
            "post_processing_filters": ("spatial/temporal filters are applied to the DISPLAY "
                                        "depth image only; measurement always uses raw aligned "
                                        "depth."),
            "mirroring": ("display-only. MediaPipe, depth sampling and deprojection always run "
                          "on the unmirrored frame so pixels stay consistent with intrinsics."),
            "video_files": {VIDEO_RAW_NAME: "unmirrored colour frames, no overlay",
                            VIDEO_MP_NAME: "same frames with MediaPipe landmarks drawn",
                            "recorded_fps": self.worker.rec_fps,
                            "frames_written": self.worker.rec_frames,
                            "note": ("fps is the measured processing rate, not the camera "
                                     "rate; one written frame = one Frame_ID, so exact "
                                     "per-frame timing comes from capture_unix_s in the CSVs.")},
            "display_mirrored": self.chk_mirror.isChecked(),
            "depth3d_enabled": self.chk_depth3d.isChecked(),
            "reporting_rules": {
                "rs_mga_statistic": "p95 within trial (max is dominated by single-frame outliers)",
                "min_valid_frames": RS_MIN_VALID_FRAMES,
                "note": ("RS summary values are blank when RS_Valid_Samples is below the "
                         "threshold. Always report RS_Valid_Rate next to any RS value."),
            },
            "working_distance_m": [WORK_MIN_M, WORK_MAX_M],
            "session_qc": {
                "landmark_samples": total,
                "status_counts": st_all,
                "ok_rate": (st_all['ok'] / total) if total else None,
                "mean_valid_landmarks": float(np.mean(nv)) if nv else None,
                "median_wrist_distance_m": float(np.median(dist)) if dist else None,
            },
            "coord_units": {
                "canon": "canonical palm frame: wrist origin, palm length = 1.0, rotation removed",
                "RS": "metres, aligned colour camera frame (X right, Y down, Z forward)",
            },
            "palm_frame_landmarks": FRAME_IDS,
            "hand_length_calib_mm": self.spin_palm.value() or None,
            "aperture_units": {"Grip_Aperture_cm": "cm (MediaPipe world landmark)",
                               "Grip_Aperture_mm_3D": "mm (model hand scale)",
                               "Grip_Aperture_mm_3D_cal": "mm (subject-calibrated)",
                               "RS_Aperture_mm": "mm (measured depth, no calibration needed)"},
            "files": {
                "continuous_raw.csv": "per-frame metrics (angles, apertures, canonical coords)",
                "landmarks.csv": "long-format per-landmark pixels, MP world, depth and status",
                "trials_summary.csv": "per-trial metrics + MP/RS paired comparison",
                "frame_quality.csv": "per-frame capture and protocol validity log",
                "distance_comparison.csv": "per-frame MP vs RS aperture with frame timestamps",
            },
            "session_duration_sec": duration,
            "camera": self.worker.source_name,
            "camera_info": self.worker.camera_info,
            "known_limitation": ("DIP angles are least reliable under monocular occlusion. On "
                                 "the RS path, fingertips fail most often during fist closure, "
                                 "so a trial's RS values are only comparable to another at a "
                                 "similar valid rate."),
            "saved_at": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        }
        with open(os.path.join(self.folder, "subject_metadata.json"), 'w', encoding='utf-8') as fp:
            json.dump(meta, fp, ensure_ascii=False, indent=2)

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

    def export_depth_plot(self, path, title):
        """MP 추정과 RS 실측 파지폭을 나란히 보고, 결측 구간은 끊어 둔다.
        (기본 출력에서는 호출하지 않는다. 필요할 때 save_session에서 부르면 된다.)"""
        fig, axes = plt.subplots(3, 2, figsize=(13, 9), dpi=150,
                                 gridspec_kw={'height_ratios': [3, 2, 3]})
        fig.patch.set_facecolor('#ffffff')
        spans = list({t['trial']: t for t in self.trials}.values())

        for c, hand in enumerate(HANDS):
            seg = [r for r in self.records if r['hand'] == hand]
            ax0, ax1, ax2 = axes[0][c], axes[1][c], axes[2][c]
            ax0.set_title(HAND_KR[hand], fontsize=11, fontweight='bold')
            if not seg:
                for ax in (ax0, ax1, ax2):
                    ax.text(.5, .5, "데이터 없음", ha='center', transform=ax.transAxes)
                continue
            ts = [r['time'] for r in seg]
            mp = [(r.get('metrics3d') or {}).get('aperture_mm_cal')
                  or (r.get('metrics3d') or {}).get('aperture_mm') or np.nan for r in seg]
            rs_ap = [(r['rs']['aperture_mm'] if (r.get('rs') and r['rs']['aperture_mm'] is not None)
                      else np.nan) for r in seg]
            nv = [(r['rs']['n_valid'] if r.get('rs') else np.nan) for r in seg]

            ax0.plot(ts, mp, color='#94a3b8', lw=1.3, label='MP 추정 (mm)')
            ax0.plot(ts, rs_ap, color='#0ea5e9', lw=1.5, label='RS 실측 (mm)')
            ax0.set_ylim(0, APERTURE_MAX_MM)
            ax0.set_ylabel("파지폭 (mm)", fontweight='bold', fontsize=9)
            ax0.legend(loc='upper right', fontsize=7)

            ax1.plot(ts, nv, color='#22c55e', lw=1.2)
            ax1.set_ylim(0, 21)
            ax1.set_ylabel("유효 랜드마크\n(개/21)", fontweight='bold', fontsize=9)

            diff = [(a - b) if (np.isfinite(a) and np.isfinite(b)) else np.nan
                    for a, b in zip(rs_ap, mp)]
            ax2.axhline(0, color='#cbd5e1', lw=1)
            ax2.plot(ts, diff, color='#ef4444', lw=1.2)
            ax2.set_ylabel("RS − MP (mm)", fontweight='bold', fontsize=9)
            ax2.set_xlabel("Elapsed Time (s)", fontweight='bold')

            for ax in (ax0, ax1, ax2):
                for tr in spans:
                    ax.axvspan(tr['start'], tr['end'], color='#fef08a', alpha=.35)
                ax.grid(True, ls=':', alpha=.6)

        fig.suptitle(f"[{title}] depth 실측 vs MediaPipe 추정 (끊긴 구간 = depth 결측)",
                     fontsize=12, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.97])
        plt.savefig(path)
        plt.close(fig)

    def export_qc_plot(self, path, title):
        """랜드마크별 결측 원인. 어디를 고쳐야 하는지가 바로 나온다.
        (기본 출력에서는 호출하지 않는다.)"""
        rec_rs = [r for r in self.records if r.get('rs')]
        fig, axes = plt.subplots(1, 2, figsize=(13, 7), dpi=150, sharey=True)
        fig.patch.set_facecolor('#ffffff')
        cause_colors = {'ok': '#22c55e', 'depth_hole': '#ef4444', 'depth_edge': '#f59e0b',
                        'depth_off_hand': '#a855f7', 'implausible_span': '#ec4899',
                        'depth_out_of_range': '#0ea5e9', 'insufficient_depth': '#64748b'}
        shown = list(cause_colors)

        for c, hand in enumerate(HANDS):
            ax = axes[c]
            seg = [r for r in rec_rs if r['hand'] == hand]
            ax.set_title(f"{HAND_KR[hand]}  (n={len(seg)} frames)", fontsize=11, fontweight='bold')
            if not seg:
                ax.text(.5, .5, "데이터 없음", ha='center', transform=ax.transAxes)
                continue
            counts = {s: np.zeros(21) for s in shown}
            other = np.zeros(21)
            for r in seg:
                for i, st in enumerate(r['rs']['status']):
                    if st in counts:
                        counts[st][i] += 1
                    else:
                        other[i] += 1
            total = len(seg)
            left = np.zeros(21)
            ypos = np.arange(21)
            for s in shown:
                vals = counts[s] / total * 100
                ax.barh(ypos, vals, left=left, color=cause_colors[s], label=s, height=0.75)
                left += vals
            if other.any():
                ax.barh(ypos, other / total * 100, left=left, color='#cbd5e1',
                        label='other', height=0.75)
            ax.set_yticks(ypos)
            ax.set_yticklabels(LM_NAMES, fontsize=8)
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.set_xlabel("프레임 비율 (%)", fontweight='bold')
            ax.grid(True, axis='x', ls=':', alpha=.6)
            if c == 1:
                ax.legend(loc='lower right', fontsize=7)

        fig.suptitle(f"[{title}] 랜드마크별 depth 결측 원인 "
                     f"(hole 지배 → 거리·조명·프리셋 / off_hand·edge 지배 → 배경 분리)",
                     fontsize=12, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(path)
        plt.close(fig)

    # ---------------------------- 프레임 ----------------------------
    def on_frame(self, frame, angles, fps, n_hands, hands3d, measures, meta):
        cam = "RealSense" if self.worker.source_name == "realsense" else "Webcam"
        nv = [m['n_valid'] for m in measures.values()] if measures else []
        rs_txt = f" | RS: {'/'.join(str(x) for x in nv)}/21" if nv else ""
        self.lbl_fps.setText(f"{cam} | FPS: {fps:.1f} | Hands: {n_hands} | "
                             f"MP3D: {len(hands3d)}{rs_txt}")
        if measures:
            self._update_qc(measures)

        task_now = self.cb_task.currentText()
        both = any(k in task_now for k in self.BOTH_HANDS_TASKS)
        found = [h for h in HANDS if h in angles]
        ok = len(found) == 2 if both else len(found) >= 1

        if self.session_on:
            t = time.time() - self.t_session
            # 프레임 로그는 손 인식 여부와 무관하게 매 프레임 남긴다.
            self.frames_qc.append({
                'time': t, 'frame_id': meta['frame_id'], 'task': task_now,
                'hands': ';'.join(found), 'protocol_valid': bool(ok),
                'ambiguous': bool(meta['ambiguous_handedness']),
                'mono': meta['capture_monotonic_s'], 'unix': meta['capture_unix_s']})

            if ok:
                if self.paused:
                    self.paused = False
                    self.btn_trial.setEnabled(True)
                    self.toast("▶ 손 인식 완료! 측정을 재개합니다.", ok=True)
                for hand in found:
                    rec = hands3d.get(hand)
                    lm = meta['hands'].get(hand, {})
                    self.records.append({
                        'time': t, 'hand': hand, 'task': task_now,
                        'frame_id': meta['frame_id'],
                        'mono': meta['capture_monotonic_s'],
                        'unix': meta['capture_unix_s'],
                        'color_num': meta['color_frame_number'],
                        'color_ts': meta['color_timestamp_ms'],
                        'depth_num': meta['depth_frame_number'],
                        'depth_ts': meta['depth_timestamp_ms'],
                        'protocol_valid': True,
                        'score': lm.get('score'),
                        'pixels': lm.get('pixels'), 'world': lm.get('world'),
                        'raw': angles[hand]['raw'], 'filtered': angles[hand]['filtered'],
                        'angles3d': rec['angles'] if rec else {},
                        'metrics3d': rec['metrics'] if rec else {},
                        'canon': rec['canon'] if rec else None,
                        'rs': measures.get(hand)})
                self.chart.update_data(t, angles)
            else:
                need = "두 손" if both else "손"
                if self.trial_on:
                    self.trial_interrupted = True
                if not self.paused:
                    self.paused = True
                    self.btn_trial.setEnabled(False)
                    self.toast(f"⏸ {need}이 인식되지 않아 일시정지합니다.")
                self._status(f"⏸ 일시정지 ({need} 인식 필요)", "#f97316")

        if self.worker.enable_3d:
            self.view3d.update_hands(time.time() - self.t_app, hands3d, measures)
        for hand in HANDS:
            self._update_gauge(hand, angles.get(hand), measures.get(hand))

        h, w, ch = frame.shape
        img = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format.Format_BGR888)
        self.lbl_video.setPixmap(QtGui.QPixmap.fromImage(img).scaled(
            self.lbl_video.width(), self.lbl_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _tick(self):
        now = time.time()
        dt, self._last_tick = now - self._last_tick, now
        if not self.session_on:
            return
        self.lbl_session.setText(
            f"● REC ({now - self.t_session:.1f}초 | {len(self.records)} 프레임)")

        if not (self.trial_on and self._auto_mode()):
            return
        if self.paused:                 # 손을 놓치면 카운트다운도 멈춰 정해진 길이를 보장
            self._status(f"⏸ 일시정지 (남은 {self.auto_left:.1f}초)", "#f97316")
            return
        self.auto_left = max(0.0, self.auto_left - dt)
        if self.auto_left <= 0.0:
            self._finish_trial()
        else:
            self._trial_btn(False)
            self._status(f"🔴 [Trial #{self.trial_idx}] 자동 측정 {self.auto_left:.1f}초 남음",
                         "#f59e0b")

    def _open_folder(self):
        d = self.folder if os.path.exists(self.folder) else self.base_dir
        os.startfile(d) if sys.platform == 'win32' else self.toast(f"폴더: {d}")

    def closeEvent(self, e):
        if self.session_on:
            self.stop_session()
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
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
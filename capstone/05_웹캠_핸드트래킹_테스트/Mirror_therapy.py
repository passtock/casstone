"""공압장갑 미러테라피 / 손 기능 정량 평가 (고정 자세 쥐기-펴기)

3D 좌표: MediaPipe world landmark -> 랜드마크 One-Euro -> 손바닥 SVD 정준화
         (손목 원점, 손 길이 1.0). depth는 손목 거리 표시 전용.
주의: 정준화는 회전+균일스케일 변환이므로 관절각은 world landmark에서 바로
      계산한 값과 같다. 이득은 좌표 스무딩과 손 크기 정규화 두 가지다.
"""
import os
os.environ.update({'TF_ENABLE_ONEDNN_OPTS': '0', 'TF_CPP_MIN_LOG_LEVEL': '2',
                   'QT_ENABLE_HIGHDPI_SCALING': '1', 'QT_AUTO_SCREEN_SCALE_FACTOR': '1'})

import sys, csv, json, time, math
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
RS_DW, RS_DH = 848, 480          # depth는 3D에 안 쓰므로 저해상도
DEPTH_VIS_MIN, DEPTH_VIS_MAX = 0.4, 1.5
VIEW_COLOR, VIEW_DEPTH, VIEW_BOTH = "color", "depth", "both"

PALM_IDS = [0, 1, 5, 9, 13, 17]
LM_SMOOTH_DEFAULT = True
HOLD_MOTION_DEFAULT = False      # 팔 고정 과제에서는 OFF (오검출만 남음)
HOLD_MOTION_PX = 28.0
VIEW3D_INTERVAL, VIEW3D_R, VIEW3D_ALPHA = 0.20, 1.25, 0.15
APERTURE_MAX_CM, APERTURE_CUTOFF, APERTURE_BETA = 30.0, 0.8, 0.02
CYCLE_HYST, CYCLE_MIN_RANGE = 0.15, 15.0
LM_XY = (0.4, 0.08, 1.2)         # (min_cutoff, beta, d_cutoff)
LM_Z = (0.15, 0.002, 0.8)        # z는 단안 깊이 노이즈가 커서 강하게 억제

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
HANDS = ('Right', 'Left')
HAND_KR = {'Right': '오른손 (Right)', 'Left': '왼손 (Left)'}

JOINT_DEFS = {
    'Thumb_MCP': (1, 2, 3), 'Thumb_IP': (2, 3, 4),
    'Index_MCP': (0, 5, 6), 'Index_PIP': (5, 6, 7), 'Index_DIP': (6, 7, 8),
    'Middle_MCP': (0, 9, 10), 'Middle_PIP': (9, 10, 11), 'Middle_DIP': (10, 11, 12),
    'Ring_MCP': (0, 13, 14), 'Ring_PIP': (13, 14, 15), 'Ring_DIP': (14, 15, 16),
    'Pinky_MCP': (0, 17, 18), 'Pinky_PIP': (17, 18, 19), 'Pinky_DIP': (18, 19, 20),
}
FLEX_OF = {'Thumb': 'Thumb_IP', 'Index': 'Index_PIP', 'Middle': 'Middle_PIP',
           'Ring': 'Ring_PIP', 'Pinky': 'Pinky_PIP'}
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
    """파지폭 전용. 각도 필터는 raw<=0을 결측으로 보고 홀딩하는데,
    주먹을 완전히 쥐면 엄지-검지 거리가 0에 가까워져 핵심 구간이 얼어붙는다."""

    def __init__(self, init_val=0.0):
        self.euro = OneEuro(x0=init_val, min_cutoff=APERTURE_CUTOFF, beta=APERTURE_BETA)
        self.last = float(init_val)

    def update(self, t, v):
        if v is None or not np.isfinite(v):
            return self.last
        v = min(APERTURE_MAX_CM, max(0.0, float(v)))
        self.last = min(APERTURE_MAX_CM, max(0.0, self.euro.filter(t, v)))
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
    """손바닥 6점 SVD 평면으로 손 고유축 R을 만들고 손목 원점·손 길이 1.0으로 정규화."""
    c = pts[PALM_IDS].mean(axis=0)
    normal = np.linalg.svd(pts[PALM_IDS] - c)[2][2]
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


# ============================ 비디오 스레드 ============================
class VideoWorker(QThread):
    frame_processed = pyqtSignal(np.ndarray, dict, float, int, dict, dict)

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
        self.t0 = time.time()

    def _reset_state(self):
        self.filters, self.ap_filters, self.smoothers, self.prev_px = {}, {}, {}, {}

    def set_mirror_mode(self, v):
        self.mirror_mode = v
        self._reset_state()

    def set_filter_mode(self, v):
        self.use_filter = v

    def set_view_mode(self, v):
        self.view_mode = v

    def set_enable_3d(self, v):
        self.enable_3d = v
        self.smoothers = {}

    def set_smooth_3d(self, v):
        self.smooth_3d = v
        self.smoothers = {}

    def set_palm_calib(self, mm):
        self.palm_calib_mm = float(mm or 0.0)

    def set_hold_motion(self, v):
        self.hold_motion, self.prev_px = bool(v), {}

    # ---------------- RealSense ----------------
    def _open_realsense(self):
        if rs is None:
            print("[안내] pyrealsense2 미설치 → 웹캠으로 동작합니다.")
            return None
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
        x, y, r = int(round(px)), int(round(py)), win // 2
        p = self.latest_depth[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)]
        v = p[p > 0]
        return float(np.median(v)) if v.size else None

    # ---------------- 3D 재구성 ----------------
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
                            'palm_len_mm': palm_mm}}

    def _moved(self, hand, x, y):
        """화면상 손목 픽셀 이동량으로 팔 이동을 감지 (world landmark는 병진 불변이라 부적합)."""
        prev = self.prev_px.get(hand)
        self.prev_px[hand] = (x, y)
        if not self.hold_motion or prev is None:
            return False
        return math.hypot(x - prev[0], y - prev[1]) > HOLD_MOTION_PX

    # ---------------- 메인 루프 ----------------
    def run(self):
        pipe = align = cap = None
        got = self._open_realsense()
        if got:
            pipe, align = got
        else:
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
                # depth 후처리는 화면에 띄울 때만 (3D에는 쓰이지 않음)
                if df and self.depth_filters and self.view_mode != VIEW_COLOR:
                    try:
                        for f in self.depth_filters:
                            df = f.process(df)
                    except Exception:
                        pass
                frame = np.asanyarray(cf.get_data()).copy()
                self.latest_depth = (np.asanyarray(df.get_data()).astype(np.float32)
                                     * self.depth_scale) if df else None
            else:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                self.latest_depth = None

            now = time.time()
            fps = 1.0 / max(now - prev_t, 1e-6)
            prev_t, t = now, now - self.t0

            if self.mirror_mode:
                frame = cv2.flip(frame, 1)
                if self.latest_depth is not None:
                    self.latest_depth = cv2.flip(self.latest_depth, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            res = hands.process(rgb)

            has_depth = self.latest_depth is not None
            mode = self.view_mode if has_depth else VIEW_COLOR
            dvis = self._colorize_depth(self.latest_depth) if has_depth else None
            canvases = ([frame] if mode in (VIEW_COLOR, VIEW_BOTH) else []) + \
                       ([dvis] if mode in (VIEW_DEPTH, VIEW_BOTH) else [])

            angles_out, depths_out, hands3d, n_hands = {}, {}, {}, 0

            if res.multi_hand_landmarks:
                n_hands = len(res.multi_hand_landmarks)
                wl = res.multi_hand_world_landmarks
                h_img, w_img = frame.shape[:2]

                for i, lms in enumerate(res.multi_hand_landmarks):
                    hand = "Hand"
                    if res.multi_handedness and i < len(res.multi_handedness):
                        hand = res.multi_handedness[i].classification[0].label
                        # MediaPipe는 셀피(미러) 영상을 가정한다. 미러링 OFF면 라벨이 뒤집힘.
                        if not self.mirror_mode:
                            hand = "Right" if hand == "Left" else "Left"

                    for c in canvases:
                        draw.draw_landmarks(c, lms, mp_hands.HAND_CONNECTIONS,
                                            styles.get_default_hand_landmarks_style(),
                                            styles.get_default_hand_connections_style())

                    wx, wy = lms.landmark[0].x * w_img, lms.landmark[0].y * h_img
                    dist = self.depth_at(wx, wy)
                    depths_out[hand] = dist

                    world = wl[i].landmark if (wl and i < len(wl)) else lms.landmark
                    rec = self.build_3d(hand, wl[i].landmark if (wl and i < len(wl)) else None,
                                        t, dist)
                    if rec:
                        hands3d[hand] = rec
                        m = rec['metrics']
                        ap = m['aperture_mm_cal'] or m['aperture_mm']
                        txt2 = f"3D {rec['mode']}  A={ap:.0f}mm" + ("*" if m['aperture_mm_cal'] else "")
                    else:
                        txt2 = None

                    txt1 = f"{hand}  {dist:.2f} m" if dist else f"{hand}  depth --"
                    for c in canvases:
                        self._put(c, txt1, int(wx) - 60, max(24, int(wy) - 16),
                                  (0, 255, 0) if dist else (0, 165, 255))
                        if txt2:
                            self._put(c, txt2, int(wx) - 60, max(44, int(wy) + 8), (0, 255, 0), 0.6)

                    # ---- 각도 산출 + 필터 ----
                    W = np.array([[l.x, l.y, l.z] for l in world], dtype=np.float64)
                    raw = joint_angles(W)
                    raw['Grip_Aperture'] = float(np.linalg.norm(W[4] - W[8]) * 100)  # cm
                    hold = self._moved(hand, wx, wy)

                    filt = {}
                    for k, v in raw.items():
                        if k == 'Grip_Aperture':
                            key = f"{hand}_ap"
                            self.ap_filters.setdefault(key, ApertureFilter(v))
                            filt[k] = self.ap_filters[key].update(t, v) if self.use_filter else v
                        else:
                            key = f"{hand}_{k}"
                            self.filters.setdefault(key, AngleFilter(v))
                            filt[k] = (self.filters[key].update(t, v, hold)
                                       if self.use_filter else v)
                    angles_out[hand] = {'raw': raw, 'filtered': filt}

            self.frame_processed.emit(self._compose(mode, frame, dvis),
                                      angles_out, fps, n_hands, depths_out, hands3d)

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
    """오른손/왼손 5손가락 굴곡각 2단 시계열."""

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
            ap = m['aperture_mm_cal'] or m['aperture_mm']
            txt = f"{HAND_KR[hand]}  ·  {rec['mode']}  ·  파지폭 {ap:.0f}mm"
            if m['aperture_mm_cal']:
                txt += "*"
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
                  "TAROM(°)", "MGA(cm)", "굴곡속도", "SPARC"]
    TASKS = ["Task 1: 맨손 쥐기/펴기 (Free Motion)", "Task 2: 원통형 파지 (Cylinder 5cm)",
             "Task 3: 구형 파지 (Sphere 7cm)", "Task 4: 미러테라피 폐루프 (Mirror Therapy)"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("공압장갑 미러테라피 · 손 기능 평가 (정준화 3D)")
        self.resize(1660, 980)
        self.setMinimumSize(1400, 860)
        self.setStyleSheet(QSS)

        self.session_on = self.trial_on = self.paused = False
        self.t_session = self.t_trial = 0.0
        self.records, self.trials, self.trial_idx = [], [], 1
        self.folder = ""
        self.t_app = time.time()
        self.gauges, self.glabels, self.gtitles = {}, {}, {}

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
        self.worker.set_hold_motion(self.chk_hold.isChecked())
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
        self.rb_patient, self.rb_healthy = QRadioButton("편마비 환자군"), QRadioButton("정상인 대조군")
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
        self.spin_fma.setRange(0, 66)
        self.spin_fma.setValue(38)
        self.spin_fma.setSuffix(" / 66점")
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
        self.chk_mirror.toggled.connect(self._on_mirror)
        self.chk_filter = QCheckBox("생체역학 필터")
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda v: self.worker.set_filter_mode(v))
        self.chk_3d = QCheckBox("3D 재구성")
        self.chk_3d.setChecked(True)
        self.chk_3d.toggled.connect(self._on_3d)
        self.chk_smooth = QCheckBox("3D 좌표 스무딩")
        self.chk_smooth.setChecked(LM_SMOOTH_DEFAULT)
        self.chk_smooth.setToolTip("랜드마크 (x,y,z)에 One-Euro를 걸어 z 노이즈·계단현상을 제거합니다.")
        self.chk_smooth.toggled.connect(self._on_smooth)
        self.chk_hold = QCheckBox("팔 이동 보정")
        self.chk_hold.setChecked(HOLD_MOTION_DEFAULT)
        self.chk_hold.setToolTip("손목이 크게 움직인 프레임의 각도 갱신을 보류합니다.\n"
                                 "팔 고정 과제에서는 꺼 두세요.")
        self.chk_hold.toggled.connect(lambda v: self.worker.set_hold_motion(v))

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
        for w in (self.chk_mirror, self.chk_filter, self.chk_3d, self.chk_smooth, self.chk_hold):
            head.addSpacing(8)
            head.addWidget(w)
        head.addSpacing(12)
        head.addWidget(self.lbl_fps)
        head.addWidget(btn_folder)
        head.addWidget(btn_exit)
        cl.addLayout(head)

        self.lbl_video = QLabel("카메라 연결 중...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(400)
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
        for title, w in (("5손가락 굴곡각 궤적 (위: 오른손 / 아래: 왼손)", self.chart),
                         ("3D 관절 공간 (정준화 좌표 · 손 크기/거리 불변)", self.view3d)):
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
        row.setSpacing(6)
        self.gauges[hand], self.glabels[hand] = {}, {}
        for f in FINGERS:
            box = QVBoxLayout()
            box.setSpacing(2)
            lbl = QLabel(f"{f}: --°")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size:11px; font-weight:bold; color:#38bdf8; border:none;")
            bar = QProgressBar()
            bar.setRange(0, 180)
            bar.setValue(180)
            box.addWidget(lbl)
            box.addWidget(bar)
            row.addLayout(box)
            self.gauges[hand][f], self.glabels[hand][f] = bar, lbl
        v.addLayout(row)
        return panel

    def _update_gauge(self, hand, data, dist):
        title, color = self.gtitles[hand], "#38bdf8"
        if not data:
            title.setText(f"{HAND_KR[hand]}  ·  미인식")
            title.setStyleSheet("font-size:11px; font-weight:bold; color:#64748b; border:none;")
            for f in FINGERS:
                self.gauges[hand][f].setValue(0)
                self.glabels[hand][f].setText(f"{f}: --°")
            return
        title.setText(f"{HAND_KR[hand]}  ·  인식됨  ·  "
                      + (f"{dist:.2f} m" if dist else "depth --"))
        title.setStyleSheet("font-size:11px; font-weight:bold; color:#10b981; border:none;")
        filt = data.get('filtered', data)
        for f in FINGERS:
            val = filt.get(f"{f}_Flexion", 180.0)
            self.gauges[hand][f].setValue(int(val))
            self.glabels[hand][f].setText(f"{f}: {val:.1f}°")
            self.glabels[hand][f].setStyleSheet(
                f"font-size:11px; font-weight:bold; color:{color}; border:none;")

    # ---------------------------- 핸들러 ----------------------------
    def toast(self, msg, ok=False):
        self.lbl_toast.setText(f"[{datetime.now():%H:%M:%S}] {msg}")
        self.lbl_toast.setStyleSheet(
            f"color:{'#10b981' if ok else '#38bdf8'}; font-size:12px; font-weight:bold; padding:2px 6px;")

    def _on_group(self, healthy):
        self.g_clin.setEnabled(not healthy)
        self.toast("피험자 군: " + ("정상인 대조군" if healthy else "편마비 환자군"))

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
        self.chart.reset_chart()
        self.view3d.reset_view()
        for hand in HANDS:
            self._update_gauge(hand, None, None)
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

    def _trial_btn(self, starting):
        self.btn_trial.setText(
            f"{'▶' if starting else '⏹'}  [Trial #{self.trial_idx}] "
            f"{'동작 시작' if starting else '동작 완료'} (Space)")
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
        sub = (f"{d}_정상인_{name}_{age}세_{g}" if self.rb_healthy.isChecked() else
               f"{d}_환자_{name}_{age}세_{g}_FMA{self.spin_fma.value()}_BRS{self.cb_brs.currentIndex()+1}")
        self.folder = os.path.join(self.base_dir, sub)
        os.makedirs(self.folder, exist_ok=True)

        self.session_on, self.trial_on, self.paused = True, False, False
        self.t_session, self.trial_idx = time.time(), 1
        self.records.clear()
        self.trials.clear()
        self.table.setRowCount(0)
        self.chart.reset_chart()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_trial.setEnabled(True)
        self._trial_btn(True)
        for w in (self.txt_name, self.spin_age, self.cb_gender, self.rb_healthy, self.rb_patient):
            w.setEnabled(False)

        self.lbl_session.setText("● REC (기록 중...)")
        self.lbl_session.setStyleSheet("color:#ef4444; font-weight:bold; font-size:14px;")
        self._status("준비됨 (동작 시작 대기)", "#38bdf8")
        self.toast(f"▶ [{self.cb_task.currentText()}] 세션 시작!", ok=True)

    def toggle_trial(self):
        if not self.session_on or not self.records:
            return
        if self.paused:
            return self.toast("⏸ 손이 인식된 상태에서만 기록할 수 있습니다.")

        t = time.time() - self.t_session
        if not self.trial_on:
            self.trial_on, self.t_trial = True, t
            self._trial_btn(False)
            self._status(f"🔴 [Trial #{self.trial_idx}] 동작 진행 중...", "#f59e0b")
            return self.toast(f"▶ [Trial #{self.trial_idx}] 시작! 끝나면 [Space]")

        self.trial_on = False
        t0, dur = self.t_trial, max(0.01, t - self.t_trial)
        task = self.cb_task.currentText()
        short = task.split(":")[0].strip()

        for hand in HANDS:
            seg = [r for r in self.records if r['hand'] == hand and t0 <= r['time'] <= t]
            if not seg:
                continue
            tr = self._trial_metrics(seg)
            tr.update(trial=self.trial_idx, hand=hand, task=task, task_short=short,
                      start=t0, end=t, duration=dur)
            self.trials.append(tr)

            row = self.table.rowCount()
            self.table.insertRow(row)
            cells = [f"Trial #{self.trial_idx}", HAND_KR[hand].split(' ')[0], short,
                     f"{dur:.2f}초", f"{tr['cycles']}회",
                     f"{tr['period']:.2f}" if tr['period'] else "-",
                     f"{tr['tarom']:.1f}°", f"{tr['mga']:.1f}cm",
                     f"{tr['flex_speed']:.0f}°/s" if tr['flex_speed'] else "-",
                     f"{tr['sparc']:.2f}" if tr['sparc'] is not None else "-"]
            for c, txt in enumerate(cells):
                self.table.setItem(row, c, QTableWidgetItem(txt))
        self.table.scrollToBottom()
        self.chart.add_trial_span(t0, t)

        self.trial_idx += 1
        self._trial_btn(True)
        self._status(f"완료됨 (총 {len({x['trial'] for x in self.trials})}회)", "#10b981")
        self.toast(f"✅ [Trial #{self.trial_idx-1} - {short}] 기록 완료 ({dur:.2f}초)", ok=True)

    @staticmethod
    def _trial_metrics(seg):
        """구간 지표: 개폐 사이클/주기, TAROM, MGA, 각속도, SPARC, 3D 파지폭."""
        filt = [r['filtered'] for r in seg]
        mga = max((f.get('Grip_Aperture', 0.0) for f in filt), default=0.0)   # cm
        pips = [f.get('Index_PIP', 180.0) for f in filt]
        rom = max(pips) - min(pips) if pips else 0.0

        tarom = 0.0
        for j in FLEX_OF.values():
            vals = [f[j] for f in filt if f.get(j) is not None]
            if vals:
                tarom += max(vals) - min(vals)

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
        return dict(mga=mga, rom=rom, tarom=tarom, cycles=cycles, period=period,
                    flex_speed=fs, ext_speed=es, sparc=sp,
                    mga3d=m3('aperture_mm'), mga3d_cal=m3('aperture_mm_cal'),
                    rom3d=(max(p3) - min(p3)) if len(p3) >= 2 else None)

    def stop_session(self):
        if not self.session_on:
            return
        if self.trial_on:
            self.toggle_trial()
        self.session_on = False
        dur = time.time() - self.t_session

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_trial.setEnabled(False)
        for w in (self.txt_name, self.spin_age, self.cb_gender, self.rb_healthy, self.rb_patient):
            w.setEnabled(True)
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

    def save_session(self, duration):
        if not self.records:
            return self.toast("⚠️ 수집된 데이터가 없어 저장을 건너뜁니다.")
        pre = f"Session_{datetime.now():%Y%m%d_%H%M%S}"
        f = self._f

        # ---- 연속 시계열 ----
        head = ["time_s", "Task", "Trial", "Phase", "hand"]
        for j in JOINT_DEFS:
            head += [f"{j}_raw", f"{j}_filt"]
        head += ["Grip_Aperture_cm_raw", "Grip_Aperture_cm_filt", "Wrist_Depth_m"]
        head += [f"{j}_3D" for j in JOINT_DEFS]
        head += ["Grip_Aperture_mm_3D", "Grip_Aperture_mm_3D_cal",
                 "Grip_Aperture_pctPalm_3D", "Palm_Len_mm_3D", "Recon_Mode"]
        for nm in LM_NAMES:                       # 정준계 좌표 (손 회전 제거)
            head += [f"{nm}_canon_{ax}" for ax in "XYZ"]

        path_raw = os.path.join(self.folder, f"{pre}_continuous_raw.csv")
        with open(path_raw, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(head)
            for rec in self.records:
                t, tag, phase = rec['time'], "Rest", "Rest"
                task = rec['task']
                for tr in self.trials:
                    if tr['hand'] == rec['hand'] and tr['start'] <= t <= tr['end']:
                        task, tag, phase = tr['task'], f"Trial_{tr['trial']}", "Grasping"
                        break
                a3, m3 = rec.get('angles3d') or {}, rec.get('metrics3d') or {}
                row = [f"{t:.4f}", task, tag, phase, rec['hand']]
                for j in JOINT_DEFS:
                    row += [f(rec['raw'].get(j)), f(rec['filtered'].get(j))]
                row += [f(rec['raw'].get('Grip_Aperture')), f(rec['filtered'].get('Grip_Aperture')),
                        f(rec.get('wrist_depth'), "{:.4f}")]
                row += [f(a3.get(j)) for j in JOINT_DEFS]
                row += [f(m3.get('aperture_mm'), "{:.1f}"), f(m3.get('aperture_mm_cal'), "{:.1f}"),
                        f(m3.get('aperture_pct_palm')), f(m3.get('palm_len_mm'), "{:.1f}"),
                        m3.get('mode', '')]
                pts = rec.get('canon')
                row += ([f"{v:.4f}" for p in pts for v in p] if pts is not None else [""] * 63)
                w.writerow(row)

        # ---- 회차 요약 ----
        path_sum = os.path.join(self.folder, f"{pre}_trials_summary.csv")
        with open(path_sum, 'w', newline='', encoding='utf-8-sig') as fp:
            w = csv.writer(fp)
            w.writerow(["Trial", "Hand", "Task", "Start_s", "End_s", "Duration_s", "Cycles",
                        "Cycle_Period_s", "TAROM_deg", "MGA_cm", "Index_ROM_deg",
                        "Flex_Speed_deg_s", "Ext_Speed_deg_s", "SPARC",
                        "MGA_mm_3D", "MGA_mm_3D_cal", "Index_ROM_3D_deg"])
            for tr in self.trials:
                w.writerow([f"Trial #{tr['trial']}", tr['hand'], tr['task_short'],
                            f"{tr['start']:.2f}", f"{tr['end']:.2f}", f"{tr['duration']:.2f}",
                            tr['cycles'], f(tr['period']), f(tr['tarom']), f(tr['mga']),
                            f(tr['rom']), f(tr['flex_speed'], "{:.1f}"),
                            f(tr['ext_speed'], "{:.1f}"), f(tr['sparc'], "{:.3f}"),
                            f(tr['mga3d'], "{:.1f}"), f(tr['mga3d_cal'], "{:.1f}"), f(tr['rom3d'])])

        self.export_plot(os.path.join(self.folder, f"{pre}_waveform.png"), pre)

        meta = {
            "name": self.txt_name.text().strip(), "age": self.spin_age.value(),
            "gender": self.cb_gender.currentText(),
            "group": "Healthy" if self.rb_healthy.isChecked() else "Patient",
            "fma_score": self.spin_fma.value() if self.rb_patient.isChecked() else None,
            "brunnstrom": self.cb_brs.currentText() if self.rb_patient.isChecked() else None,
            "affected_side": self.cb_affected.currentText() if self.rb_patient.isChecked() else None,
            "total_trials": len({x['trial'] for x in self.trials}),
            "angle_3d_source": ("MediaPipe world landmark + One-Euro smoothing + SVD palm "
                                "canonicalization. Rotation+uniform-scale transform, so joint "
                                "angles equal those from raw world landmarks."),
            "coord_3d_units": "canonical palm frame: wrist origin, palm length = 1.0, rotation removed",
            "hand_length_calib_mm": self.spin_palm.value() or None,
            "aperture_units": {"Grip_Aperture_cm": "cm (world landmark)",
                               "Grip_Aperture_mm_3D": "mm (model hand scale)",
                               "Grip_Aperture_mm_3D_cal": "mm (subject-calibrated)",
                               "Grip_Aperture_pctPalm_3D": "% of palm length"},
            "hold_motion_correction": self.chk_hold.isChecked(),
            "session_duration_sec": duration,
            "camera": self.worker.source_name,
            "depth_usage": "wrist distance display only",
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

    # ---------------------------- 프레임 ----------------------------
    def on_frame(self, frame, angles, fps, n_hands, depths, hands3d):
        cam = "RealSense" if self.worker.source_name == "realsense" else "Webcam"
        self.lbl_fps.setText(f"{cam} | FPS: {fps:.1f} | Hands: {n_hands} | 3D: {len(hands3d)}")

        # 미러테라피(Task 4)만 양손 필수. 나머지는 한 손만 인식돼도 기록.
        both = "Task 4" in self.cb_task.currentText()
        found = [h for h in HANDS if h in angles]
        ok = len(found) == 2 if both else len(found) >= 1

        if self.session_on:
            if ok:
                if self.paused:
                    self.paused = False
                    self.btn_trial.setEnabled(True)
                    self.toast("▶ 손 인식 완료! 측정을 재개합니다.", ok=True)
                t = time.time() - self.t_session
                for hand in found:
                    rec = hands3d.get(hand)
                    self.records.append({
                        'time': t, 'hand': hand, 'task': self.cb_task.currentText(),
                        'raw': angles[hand]['raw'], 'filtered': angles[hand]['filtered'],
                        'angles3d': rec['angles'] if rec else {},
                        'metrics3d': rec['metrics'] if rec else {},
                        'canon': rec['canon'] if rec else None,
                        'wrist_depth': depths.get(hand)})
                self.chart.update_data(t, angles)
            else:
                need = "두 손" if both else "손"
                if not self.paused:
                    self.paused = True
                    self.btn_trial.setEnabled(False)
                    self.toast(f"⏸ {need}이 인식되지 않아 일시정지합니다.")
                self._status(f"⏸ 일시정지 ({need} 인식 필요)", "#f97316")

        if self.worker.enable_3d:
            self.view3d.update_hands(time.time() - self.t_app, hands3d)
        for hand in HANDS:
            self._update_gauge(hand, angles.get(hand), depths.get(hand))

        h, w, ch = frame.shape
        img = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format.Format_BGR888)
        self.lbl_video.setPixmap(QtGui.QPixmap.fromImage(img).scaled(
            self.lbl_video.width(), self.lbl_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _tick(self):
        if self.session_on:
            self.lbl_session.setText(
                f"● REC ({time.time()-self.t_session:.1f}초 | {len(self.records)} 프레임)")

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
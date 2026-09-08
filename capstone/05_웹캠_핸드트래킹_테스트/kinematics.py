import math
import numpy as np

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
    """Optional legacy spike limit; missing geometry is never invented."""

    def __init__(self, init_val=180.0, limit_deg=None):
        self.last = float(init_val) if init_val is not None and np.isfinite(init_val) else None
        self.limit_deg = limit_deg
        self.quality = 'uninitialized'
        self.missing = 0
        self.euro = OneEuro(x0=self.last or 0.0, min_cutoff=0.7, beta=0.015)

    def update(self, t, v, hold=False):
        if v is None or not np.isfinite(v):
            self.quality = 'invalid_geometry'
            return None
        if hold and self.last is not None:
            self.quality = 'motion_hold'
            self.euro.t = t
            return self.last
        self.quality = 'smoothed'
        if self.limit_deg is not None and self.last is not None and abs(v - self.last) > self.limit_deg:
            v = self.last + math.copysign(self.limit_deg, v - self.last)
            self.quality = 'clamped'
        self.last = self.euro.filter(t, float(v))
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
            return None
        self.last = self.euro.filter(t, float(v))
        return self.last


# =========================== 기하 / 지표 ===========================
def angle3(a, b, c):
    ba, bc = a - b, c - b
    n1, n2 = np.linalg.norm(ba), np.linalg.norm(bc)
    if not np.isfinite([n1, n2]).all() or n1 < 1e-7 or n2 < 1e-7:
        return None
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



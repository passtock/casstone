import math
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os

plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# Dimensions (meters)
DESK_W = 0.76; DESK_D = 0.49; DESK_H = 0.75
SHELF_W = 0.22; SHELF_D = 0.15; SHELF_H = 0.37; SHELF_Y_START = 0.20
CHAIR_H = 0.46
MIN_DEPTH_Z = 0.52

LANDMARKS = {
    "T1_시작(블록)":   {"pos": np.array([0.15, 0.10, 0.025]),       "req": ["T1"], "color": "#10b981"},
    "T1_목표(선반37cm)": {"pos": np.array([0.06, 0.25, 0.37 + 0.025]),"req": ["T1"], "color": "#059669"},
    "T2_시작(하부뚜껑)":   {"pos": np.array([-0.055, 0.095, 0.006]),    "req": ["T2"], "color": "#06b6d4"},
    "T2_목표(선반뚜껑)":   {"pos": np.array([-0.055, 0.246, 0.37 + 0.006]),"req": ["T2"], "color": "#0891b2"},
    "환측손(대기)":       {"pos": np.array([0.15, 0.05, 0.05]),       "req": ["T1","T2"], "color": "#3b82f6"},
    "환측팔꿈치":         {"pos": np.array([0.22, -0.05, 0.22]),      "req": ["T1","T2"], "color": "#6366f1"},
    "환측어깨(우)":       {"pos": np.array([0.18, -0.25, 0.25]),      "req": ["전체"], "color": "#8b5cf6"},
    "건측어깨(좌)":       {"pos": np.array([-0.18, -0.25, 0.25]),     "req": ["전체"], "color": "#a855f7"},
    "체간(등받이)":       {"pos": np.array([0.00, -0.30, 0.12]),      "req": ["전체"], "color": "#ec4899"},
    "정수리(T3목표)":     {"pos": np.array([0.00, -0.25, 0.58]),      "req": ["T3"], "color": "#f43f5e"},
    "환측무릎(T3시작)":   {"pos": np.array([0.12, -0.10, -0.25]),     "req": ["T3"], "color": "#e11d48"},
    "건측무릎":           {"pos": np.array([-0.12, -0.10, -0.25]),    "req": ["T3"], "color": "#9ca3af"},
}

D455_RGB_HFOV = math.radians(90.0)
D455_RGB_VFOV = math.radians(65.0)

def check_shelf_occlusion(cam_pos, pt_pos):
    """Line of sight ray intersection check with ARAT shelf (height 37cm)"""
    direction = pt_pos - cam_pos
    if abs(direction[1]) < 1e-6:
        return False
    # Check Y = 0.20 plane (front lip of shelf facing patient)
    t = (SHELF_Y_START - cam_pos[1]) / direction[1]
    if 0 < t < 1:
        intersect = cam_pos + t * direction
        if -SHELF_W/2 <= intersect[0] <= SHELF_W/2 and 0 <= intersect[2] <= SHELF_H:
            return True
    # Check top plane Z = 0.37
    if abs(direction[2]) > 1e-6:
        t_z = (SHELF_H - cam_pos[2]) / direction[2]
        if 0 < t_z < 1:
            intersect = cam_pos + t_z * direction
            if -SHELF_W/2 <= intersect[0] <= SHELF_W/2 and SHELF_Y_START <= intersect[1] <= SHELF_Y_START + SHELF_D:
                return True
    return False

def get_camera_matrix(pos, target, up=np.array([0, 0, 1])):
    pos = np.array(pos, dtype=float)
    target = np.array(target, dtype=float)
    forward = target - pos
    dist = np.linalg.norm(forward)
    forward = forward / dist
    right = np.cross(forward, up)
    if np.linalg.norm(right) < 1e-6:
        up = np.array([0, 1, 0])
        right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    true_up = np.cross(right, forward)
    R = np.vstack([right, -true_up, forward])
    t = -R @ pos
    return R, t, pos, forward, right, true_up

def project_point(p_world, R, t, hfov, vfov):
    p_cam = R @ p_world + t
    xc, yc, zc = p_cam
    if zc <= 0:
        return None, None, zc, False
    tan_h = math.tan(hfov / 2)
    tan_v = math.tan(vfov / 2)
    u_norm = (xc / zc) / tan_h
    v_norm = (yc / zc) / tan_v
    in_fov = (-1.0 <= u_norm <= 1.0) and (-1.0 <= v_norm <= 1.0)
    return u_norm, v_norm, zc, in_fov

def render_comparison():
    fig = plt.figure(figsize=(20, 9), facecolor='#0f172a')
    
    # --- Case 1: 정면 상측 (Frontal Upper: 맞은편 Y=0.85m, Z=0.80m, 하향 45°) ---
    cam_front = np.array([0.00, 0.85, 0.80])
    target_front = np.array([0.00, 0.05, 0.20])
    R_f, t_f, _, _, _, _ = get_camera_matrix(cam_front, target_front)
    
    # --- Case 2: 전외측 상측 (Anterolateral 40°: X=0.61m, Y=-0.58m, Z=0.58m) ---
    cam_obl = np.array([0.61, -0.58, 0.58])
    target_obl = np.array([0.05, 0.10, 0.18])
    R_o, t_o, _, _, _, _ = get_camera_matrix(cam_obl, target_obl)
    
    # Plot 1: 정면 상측 뷰 (D455 센서 화면)
    ax1 = fig.add_subplot(1, 2, 1, facecolor='#020617')
    ax1.set_xlim([-1.1, 1.1])
    ax1.set_ylim([1.1, -1.1])
    
    border1 = plt.Rectangle((-1.0, -1.0), 2.0, 2.0, fill=False, edgecolor='#f59e0b', lw=2.5)
    ax1.add_patch(border1)
    ax1.axhline(0, color='#1e293b', lw=0.8, linestyle='--')
    ax1.axvline(0, color='#1e293b', lw=0.8, linestyle='--')
    
    occluded_cnt = 0
    for name, data in LANDMARKS.items():
        u, v, zc, in_fov = project_point(data["pos"], R_f, t_f, D455_RGB_HFOV, D455_RGB_VFOV)
        is_occ = check_shelf_occlusion(cam_front, data["pos"])
        if is_occ: occluded_cnt += 1
        
        col = "#ef4444" if is_occ else "#10b981"
        if u is not None and v is not None and abs(u) < 1.4 and abs(v) < 1.4:
            ax1.scatter([u], [v], color=col, s=90, edgecolors='white', lw=1.2, zorder=5)
            tag = " [선반 가림!]" if is_occ else f" ({zc:.2f}m)"
            ax1.text(u + 0.03, v, f"{name.split('(')[0]}{tag}", color=col, fontsize=8, fontweight='bold', va='center', zorder=6)
            
    # Shelf shadow projection box on screen
    ax1.set_title("안 1. 맞은편 정면 상측 (Frontal Upper: 높이 80cm, 하향 45°)", color='white', fontsize=12, pad=12, fontweight='bold')
    ax1.text(-0.95, -0.92, "● 장점: 상체 대칭성 완벽, 양 어깨·정수리 한눈에 포괄", color='#38bdf8', fontsize=9, fontweight='bold')
    ax1.text(-0.95, -0.83, f"● 치명적 단점: 37cm 선반이 환자 손/시작물체를 가림! ({occluded_cnt}개 지점 가림)", color='#f43f5e', fontsize=9, fontweight='bold')
    ax1.text(-0.95, 0.95, "손등이 엄지-검지 파지를 가려 Pinch 패드 맞섬 판별 불리 / 등받이 접촉 육안 확인 어려움", color='#cbd5e1', fontsize=8.5)
    ax1.set_xticks([]); ax1.set_yticks([])
    for spine in ax1.spines.values(): spine.set_color('#1e293b')
    
    # Plot 2: 전외측 상측 (Anterolateral 40°)
    ax2 = fig.add_subplot(1, 2, 2, facecolor='#020617')
    ax2.set_xlim([-1.1, 1.1])
    ax2.set_ylim([1.1, -1.1])
    
    border2 = plt.Rectangle((-1.0, -1.0), 2.0, 2.0, fill=False, edgecolor='#10b981', lw=2.5)
    ax2.add_patch(border2)
    ax2.axhline(0, color='#1e293b', lw=0.8, linestyle='--')
    ax2.axvline(0, color='#1e293b', lw=0.8, linestyle='--')
    
    for name, data in LANDMARKS.items():
        u, v, zc, in_fov = project_point(data["pos"], R_o, t_o, D455_RGB_HFOV, D455_RGB_VFOV)
        col = "#10b981"
        if u is not None and v is not None and abs(u) < 1.4 and abs(v) < 1.4:
            ax2.scatter([u], [v], color=col, s=90, edgecolors='white', lw=1.2, zorder=5)
            ax2.text(u + 0.03, v, f"{name.split('(')[0]} ({zc:.2f}m)", color=col, fontsize=8, fontweight='bold', va='center', zorder=6)
            
    ax2.set_title("안 2. 환측 전외측 상측 (Anterolateral 40°: 높이 58cm, 하향 36°) ★ 연구 권장안", color='white', fontsize=12, pad=12, fontweight='bold')
    ax2.text(-0.95, -0.92, "● 장점 1: 선반 가림 0개 (블록/구슬/선반 100% 가시성)", color='#10b981', fontsize=9, fontweight='bold')
    ax2.text(-0.95, -0.83, "● 장점 2: 엄지-검지 파지 간격(K1) 패드 맞섬 측면 관측 최적", color='#38bdf8', fontsize=9, fontweight='bold')
    ax2.text(-0.95, 0.95, "● 장점 3: 의자 등받이와 등 사이 틈(체간 보상 lean)이 명확히 분리되어 보임", color='#cbd5e1', fontsize=8.5)
    ax2.set_xticks([]); ax2.set_yticks([])
    for spine in ax2.spines.values(): spine.set_color('#1e293b')
    
    fig.suptitle("정면 상측(Frontal Upper) vs 전외측 상측(Anterolateral 40°) 시뮬레이션 비교", color='white', fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    out_path = os.path.join(os.path.dirname(__file__), "frontal_vs_anterolateral_simulation.png")
    plt.savefig(out_path, dpi=200, facecolor='#0f172a', edgecolor='none')
    plt.close()
    print(f"[SUCCESS] Saved figure to: {out_path}")

if __name__ == "__main__":
    render_comparison()

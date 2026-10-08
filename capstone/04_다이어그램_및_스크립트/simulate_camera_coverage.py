import math
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os

# Set Korean-friendly fonts
plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# --- Dimensions (meters) ---
DESK_W = 0.76      # 76 cm width (X: -0.38 to +0.38)
DESK_D = 0.49      # 49 cm depth (Y: 0.0 to 0.49)
DESK_H = 0.75      # 75 cm height from floor (floor Z = -0.75)

SHELF_W = 0.22     # 22 cm width (X: -0.11 to +0.11)
SHELF_D = 0.15     # 15 cm depth (Y: 0.20 to 0.35)
SHELF_H = 0.37     # 37 cm height from desk surface
SHELF_Y_START = 0.20

CHAIR_H = 0.46     # 46 cm from floor -> Z = -0.29 from desk

# Key landmarks with clinical importance and task mapping
LANDMARKS = {
    "T1_시작(5cm블록)":   {"pos": np.array([0.15, 0.10, 0.025]),       "req": ["T1"], "color": "#10b981"},
    "T1_목표(선반위블록)": {"pos": np.array([0.06, 0.25, 0.37 + 0.025]),"req": ["T1"], "color": "#059669"},
    "T2_시작(하부뚜껑)":   {"pos": np.array([-0.055, 0.095, 0.006]),    "req": ["T2"], "color": "#06b6d4"},
    "T2_목표(선반위뚜껑)": {"pos": np.array([-0.055, 0.246, 0.37 + 0.006]),"req": ["T2"], "color": "#0891b2"},
    "환측손(대기자세)":    {"pos": np.array([0.15, 0.05, 0.05]),       "req": ["T1","T2"], "color": "#3b82f6"},
    "환측팔꿈치(도달중)":  {"pos": np.array([0.22, -0.05, 0.22]),      "req": ["T1","T2"], "color": "#6366f1"},
    "환측어깨(우측)":      {"pos": np.array([0.18, -0.25, 0.25]),      "req": ["T1","T2","T3"], "color": "#8b5cf6"},
    "건측어깨(좌측)":      {"pos": np.array([-0.18, -0.25, 0.25]),     "req": ["T1","T2","T3"], "color": "#a855f7"},
    "체간(등받이접촉)":    {"pos": np.array([0.00, -0.30, 0.12]),      "req": ["T1","T2","T3"], "color": "#ec4899"},
    "정수리(T3목표)":      {"pos": np.array([0.00, -0.25, 0.58]),      "req": ["T3"], "color": "#f43f5e"},
    "환측무릎(T3시작)":    {"pos": np.array([0.12, -0.10, -0.25]),     "req": ["T3"], "color": "#e11d48"},
    "건측무릎":            {"pos": np.array([-0.12, -0.10, -0.25]),    "req": ["T3"], "color": "#9ca3af"},
}

# RealSense D455 specs
D455_RGB_HFOV = math.radians(90.0)
D455_RGB_VFOV = math.radians(65.0)
MIN_DEPTH_Z = 0.52 # 52 cm

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

def draw_box(ax, x_range, y_range, z_range, color='gray', alpha=0.2, edgecolor='black', lw=1):
    x = [x_range[0], x_range[1]]
    y = [y_range[0], y_range[1]]
    z = [z_range[0], z_range[1]]
    vertices = [
        [[x[0], y[0], z[0]], [x[1], y[0], z[0]], [x[1], y[1], z[0]], [x[0], y[1], z[0]]],
        [[x[0], y[0], z[1]], [x[1], y[0], z[1]], [x[1], y[1], z[1]], [x[0], y[1], z[1]]],
        [[x[0], y[0], z[0]], [x[1], y[0], z[0]], [x[1], y[1], z[1]], [x[0], y[0], z[1]]],
        [[x[0], y[1], z[0]], [x[1], y[1], z[0]], [x[1], y[1], z[1]], [x[0], y[1], z[1]]],
        [[x[0], y[0], z[0]], [x[0], y[1], z[0]], [x[0], y[1], z[1]], [x[0], y[0], z[1]]],
        [[x[1], y[0], z[0]], [x[1], y[1], z[0]], [x[1], y[1], z[1]], [x[1], y[0], z[1]]]
    ]
    poly = Poly3DCollection(vertices, alpha=alpha, facecolor=color, edgecolor=edgecolor, linewidths=lw)
    ax.add_collection3d(poly)

def render_simulation(cam_pos, cam_target, output_path="camera_simulation_result.png"):
    R, t, pos, forward, right, up = get_camera_matrix(cam_pos, cam_target)
    
    fig = plt.figure(figsize=(18, 9), facecolor='#0f172a')
    
    # --- SUBPLOT 1: 3D Scene View ---
    ax1 = fig.add_subplot(1, 2, 1, projection='3d', facecolor='#0f172a')
    
    # 1. Floor & Desk
    draw_box(ax1, [-0.6, 0.6], [-0.6, 0.8], [-0.75, -0.74], color='#1e293b', alpha=0.5, edgecolor='#334155')
    # Desk Top (76cm x 49cm x 3cm, surface at Z=0)
    draw_box(ax1, [-DESK_W/2, DESK_W/2], [0, DESK_D], [-0.03, 0], color='#475569', alpha=0.6, edgecolor='#94a3b8', lw=1.5)
    # Desk 4 Legs
    for lx in [-DESK_W/2 + 0.03, DESK_W/2 - 0.03]:
        for ly in [0.03, DESK_D - 0.03]:
            draw_box(ax1, [lx-0.02, lx+0.02], [ly-0.02, ly+0.02], [-0.75, -0.03], color='#334155', alpha=0.5)
            
    # 2. Shelf (37cm height)
    draw_box(ax1, [-SHELF_W/2, SHELF_W/2], [SHELF_Y_START, SHELF_Y_START + SHELF_D], [SHELF_H - 0.015, SHELF_H], color='#38bdf8', alpha=0.7, edgecolor='#0284c7', lw=1.5)
    # Shelf Columns
    for cx in [-SHELF_W/2 + 0.03, SHELF_W/2 - 0.03]:
        draw_box(ax1, [cx-0.015, cx+0.015], [SHELF_Y_START+SHELF_D/2-0.015, SHELF_Y_START+SHELF_D/2+0.015], [0, SHELF_H - 0.015], color='#0284c7', alpha=0.6)
        
    # 3. Chair & Seated Mannequin
    # Chair seat (46cm high -> Z = -0.29)
    draw_box(ax1, [-0.22, 0.22], [-0.42, -0.12], [-0.32, -0.29], color='#64748b', alpha=0.5)
    # Chair backrest
    draw_box(ax1, [-0.20, 0.20], [-0.44, -0.42], [-0.29, 0.25], color='#475569', alpha=0.5)
    
    # Mannequin Stick Figure / Torso
    ax1.plot([0, 0], [-0.30, -0.25], [-0.29, 0.25], color='#cbd5e1', lw=4)
    # Shoulders
    ax1.plot([-0.18, 0.18], [-0.25, -0.25], [0.25, 0.25], color='#cbd5e1', lw=4)
    # Head sphere
    u_sph, v_sph = np.mgrid[0:2*np.pi:12j, 0:np.pi:6j]
    xsph = 0.09 * np.cos(u_sph)*np.sin(v_sph)
    ysph = -0.25 + 0.09 * np.sin(u_sph)*np.sin(v_sph)
    zsph = 0.46 + 0.11 * np.cos(v_sph)
    ax1.plot_wireframe(xsph, ysph, zsph, color='#e2e8f0', alpha=0.4)
    
    # Arm reach trajectory
    ax1.plot([0.18, 0.22, 0.15], [-0.25, -0.05, 0.05], [0.25, 0.22, 0.05], 'w--', lw=1.5, alpha=0.6)
    ax1.plot([0.15, 0.20, 0.06], [0.05, 0.15, 0.25], [0.05, 0.25, SHELF_H+0.025], 'c--', lw=2, label='T1 궤적 (블록→선반 37cm)')
    
    # 4. Camera Body & Tripod
    ax1.scatter([cam_pos[0]], [cam_pos[1]], [cam_pos[2]], color='#ef4444', s=120, marker='s', label='Intel RealSense D455')
    ax1.plot([cam_pos[0], cam_pos[0]], [cam_pos[1], cam_pos[1]], [-0.75, cam_pos[2]], color='#ef4444', lw=2, linestyle=':')
    ax1.plot([cam_pos[0], cam_target[0]], [cam_pos[1], cam_target[1]], [cam_pos[2], cam_target[2]], color='#f87171', lw=1.5, linestyle='--')
    
    # 5. Camera Frustum
    frustum_dist = 1.3
    tan_h = math.tan(D455_RGB_HFOV / 2)
    tan_v = math.tan(D455_RGB_VFOV / 2)
    corners_cam = [
        np.array([-tan_h, -tan_v, 1.0]) * frustum_dist,
        np.array([ tan_h, -tan_v, 1.0]) * frustum_dist,
        np.array([ tan_h,  tan_v, 1.0]) * frustum_dist,
        np.array([-tan_h,  tan_v, 1.0]) * frustum_dist,
    ]
    R_inv = R.T
    corners_world = [R_inv @ c + cam_pos for c in corners_cam]
    for cw in corners_world:
        ax1.plot([cam_pos[0], cw[0]], [cam_pos[1], cw[1]], [cam_pos[2], cw[2]], color='#38bdf8', lw=1, alpha=0.4)
    cw_loop = corners_world + [corners_world[0]]
    ax1.plot([c[0] for c in cw_loop], [c[1] for c in cw_loop], [c[2] for c in cw_loop], color='#38bdf8', lw=1.5, alpha=0.7)
    
    # Min Depth (0.52m) Plane
    min_corners = [R_inv @ (np.array([x, y, 1.0]) * MIN_DEPTH_Z) + cam_pos for x, y in [(-tan_h, -tan_v), (tan_h, -tan_v), (tan_h, tan_v), (-tan_h, tan_v)]]
    min_poly = Poly3DCollection([min_corners], alpha=0.2, facecolor='#f43f5e', edgecolor='#f43f5e', linewidths=1.5)
    ax1.add_collection3d(min_poly)
    
    # Plot landmarks
    res_table = []
    for name, data in LANDMARKS.items():
        pt = data["pos"]
        u, v, zc, in_fov = project_point(pt, R, t, D455_RGB_HFOV, D455_RGB_VFOV)
        depth_ok = zc >= MIN_DEPTH_Z if zc else False
        status = "안전(SAFE)" if (in_fov and depth_ok) else ("데드존(<52cm)" if in_fov and not depth_ok else "화면이탈(OUT)")
        res_table.append((name, data["color"], u, v, zc, status))
        
        m_color = '#10b981' if status == "안전(SAFE)" else ('#f59e0b' if status == "데드존(<52cm)" else '#ef4444')
        ax1.scatter([pt[0]], [pt[1]], [pt[2]], color=m_color, s=60, edgecolors='white', lw=1)
        ax1.text(pt[0], pt[1], pt[2]+0.03, name.split('(')[0], color='white', fontsize=7, ha='center')
        
    ax1.set_xlim([-0.6, 0.8])
    ax1.set_ylim([-0.5, 0.7])
    ax1.set_zlim([-0.4, 0.8])
    ax1.set_title("3D 실험실 시뮬레이션 (책상 75cm / 선반 37cm / D455 FOV)", color='white', fontsize=12, pad=12, fontweight='bold')
    ax1.view_init(elev=28, azim=130)
    ax1.axis('off')
    
    # --- SUBPLOT 2: Simulated Camera POV ---
    ax2 = fig.add_subplot(1, 2, 2, facecolor='#020617')
    ax2.set_xlim([-1.05, 1.05])
    ax2.set_ylim([1.05, -1.05])
    
    border = plt.Rectangle((-1.0, -1.0), 2.0, 2.0, fill=False, edgecolor='#38bdf8', lw=2.5, linestyle='-')
    ax2.add_patch(border)
    safe_box = plt.Rectangle((-0.85, -0.85), 1.7, 1.7, fill=False, edgecolor='#64748b', lw=1, linestyle=':')
    ax2.add_patch(safe_box)
    
    ax2.axhline(0, color='#334155', lw=0.8, linestyle='--')
    ax2.axvline(0, color='#334155', lw=0.8, linestyle='--')
    
    pass_cnt = 0
    total_cnt = len(res_table)
    for name, orig_col, u, v, zc, status in res_table:
        if u is not None and v is not None and abs(u) < 1.4 and abs(v) < 1.4:
            marker_col = '#10b981' if status == "안전(SAFE)" else ('#f59e0b' if status == "데드존(<52cm)" else '#ef4444')
            ax2.scatter([u], [v], color=marker_col, s=100, edgecolors='white', lw=1.5, zorder=5)
            badge = f" [zc={zc:.2f}m]" if zc else ""
            ax2.text(u + 0.03, v, f"{name}{badge}", color=marker_col, fontsize=8, fontweight='bold', va='center', zorder=6)
        if status == "안전(SAFE)":
            pass_cnt += 1
            
    hand_zc = [item[4] for item in res_table if "환측손" in item[0]][0]
    if hand_zc and hand_zc > 0:
        hand_px = (0.10 / (2 * hand_zc * math.tan(D455_RGB_HFOV / 2))) * 1280
        res_text = f"손바닥 폭 해상도: 약 {hand_px:.0f} px (1280x720 기준, MediaPipe 21 관절 추적 매우 양호)"
    else:
        res_text = "손바닥 거리 측정 불가"
        
    ax2.set_title(f"RealSense D455 화면 시뮬레이션 (화면 포괄률: {pass_cnt}/{total_cnt} 지점 통과)", color='white', fontsize=12, pad=12, fontweight='bold')
    ax2.text(-0.95, -0.92, "● D455 RGB FOV (90° x 65°)", color='#38bdf8', fontsize=9, fontweight='bold')
    ax2.text(-0.95, 0.90, f"최소심도 데드존 한계: 0.52m | {res_text}", color='#94a3b8', fontsize=8)
    
    cam_dist = np.linalg.norm(cam_pos - cam_target)
    info_str = f"카메라 위치: X={cam_pos[0]:.2f}m, Y={cam_pos[1]:.2f}m, Z={cam_pos[2]:.2f}m (작업거리={cam_dist:.2f}m)"
    ax2.text(-0.95, 0.98, info_str, color='#e2e8f0', fontsize=8)
    
    ax2.set_xticks([])
    ax2.set_yticks([])
    for spine in ax2.spines.values():
        spine.set_color('#1e293b')
        
    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=200, facecolor='#0f172a', edgecolor='none')
    plt.close()
    print(f"[SUCCESS] Saved simulation figure to: {output_path}")

if __name__ == "__main__":
    angle = math.radians(40.0)
    dist = 0.95
    cam_x = dist * math.sin(angle)
    cam_y = -dist * math.cos(angle) + 0.15
    cam_z = 0.58
    cam_pos = np.array([cam_x, cam_y, cam_z])
    cam_target = np.array([0.05, 0.10, 0.18])
    
    out_img = os.path.join(os.path.dirname(__file__), "camera_simulation_optimal.png")
    render_simulation(cam_pos, cam_target, out_img)

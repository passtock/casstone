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
    "T1_시작(블록)":   {"pos": np.array([0.15, 0.10, 0.025]),       "req": ["T1"]},
    "T1_목표(선반37cm)": {"pos": np.array([0.06, 0.25, 0.37 + 0.025]),"req": ["T1"]},
    "T2_시작(하부뚜껑)":   {"pos": np.array([-0.055, 0.095, 0.006]),    "req": ["T2"]},
    "T2_목표(선반뚜껑)":   {"pos": np.array([-0.055, 0.246, 0.37 + 0.006]),"req": ["T2"]},
    "환측손(대기)":       {"pos": np.array([0.15, 0.05, 0.05]),       "req": ["T1","T2"]},
    "환측팔꿈치":         {"pos": np.array([0.22, -0.05, 0.22]),      "req": ["T1","T2"]},
    "환측어깨(우)":       {"pos": np.array([0.18, -0.25, 0.25]),      "req": ["전체"]},
    "건측어깨(좌)":       {"pos": np.array([-0.18, -0.25, 0.25]),     "req": ["전체"]},
    "체간(등받이)":       {"pos": np.array([0.00, -0.30, 0.12]),      "req": ["전체"]},
    "정수리(T3목표)":     {"pos": np.array([0.00, -0.25, 0.58]),      "req": ["T3"]},
    "환측무릎(T3시작)":   {"pos": np.array([0.12, -0.10, -0.25]),     "req": ["T3"]},
    "건측무릎":           {"pos": np.array([-0.12, -0.10, -0.25]),    "req": ["T3"]},
}

D455_RGB_HFOV = math.radians(90.0)
D455_RGB_VFOV = math.radians(65.0)

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

def render_comparison_figure(output_path="camera_simulation_comparison.png"):
    configs = [
        {
            "title": "설정 A: 너무 가까운 배치 (거리 0.70m, 높이 45cm, 각도 30°)",
            "subtitle": "⚠️ 문제점: 정수리/무릎 잘림(OUT) + 손/팔꿈치 심도 데드존(<52cm) 발생!",
            "cam_pos": np.array([0.35, -0.55, 0.45]),
            "cam_target": np.array([0.05, 0.12, 0.15]),
            "border_color": "#f43f5e"
        },
        {
            "title": "설정 B: 권장 표준 최적 배치 (거리 0.95m, 높이 58cm, 각도 40°)",
            "subtitle": "✅ 최적: 12개 전 지점 100% 화면 포함 + 전 지점 심도 유효(>0.52m) + 체간 관찰 완벽",
            "cam_pos": np.array([0.61, -0.58, 0.58]),
            "cam_target": np.array([0.05, 0.10, 0.18]),
            "border_color": "#10b981"
        },
        {
            "title": "설정 C: T3 전신 포괄 광각 배치 (거리 1.15m, 높이 68cm, 각도 42°)",
            "subtitle": "✅ 안정: 정수리 위와 무릎 시작 위치까지 넉넉한 15% 여유 마진 확보",
            "cam_pos": np.array([0.75, -0.68, 0.68]),
            "cam_target": np.array([0.05, 0.08, 0.22]),
            "border_color": "#38bdf8"
        }
    ]

    fig, axes = plt.subplots(1, 3, figsize=(21, 7.5), facecolor='#0f172a')
    
    for idx, (ax, cfg) in enumerate(zip(axes, configs)):
        ax.set_facecolor('#020617')
        ax.set_xlim([-1.1, 1.1])
        ax.set_ylim([1.1, -1.1]) # Screen space top is -1
        
        # Border
        border = plt.Rectangle((-1.0, -1.0), 2.0, 2.0, fill=False, edgecolor=cfg["border_color"], lw=2.5)
        ax.add_patch(border)
        # Margin
        safe_box = plt.Rectangle((-0.85, -0.85), 1.7, 1.7, fill=False, edgecolor='#334155', lw=1, linestyle=':')
        ax.add_patch(safe_box)
        
        ax.axhline(0, color='#1e293b', lw=0.8, linestyle='--')
        ax.axvline(0, color='#1e293b', lw=0.8, linestyle='--')
        
        R, t, pos, forward, right, up = get_camera_matrix(cfg["cam_pos"], cfg["cam_target"])
        
        pass_cnt = 0
        dead_cnt = 0
        out_cnt = 0
        
        for name, data in LANDMARKS.items():
            u, v, zc, in_fov = project_point(data["pos"], R, t, D455_RGB_HFOV, D455_RGB_VFOV)
            depth_ok = (zc >= MIN_DEPTH_Z) if zc else False
            
            if not in_fov:
                status = "OUT"
                out_cnt += 1
                col = "#f43f5e"
            elif not depth_ok:
                status = "DEADZONE"
                dead_cnt += 1
                col = "#f59e0b"
            else:
                status = "SAFE"
                pass_cnt += 1
                col = "#10b981"
                
            if u is not None and v is not None and abs(u) < 1.4 and abs(v) < 1.4:
                ax.scatter([u], [v], color=col, s=80, edgecolors='white', lw=1.2, zorder=5)
                short_name = name.split('(')[0]
                ax.text(u + 0.03, v, f"{short_name}\n({zc:.2f}m)", color=col, fontsize=7.5, fontweight='bold', va='center', zorder=6)
                
        # Subplot Title & Stats
        ax.set_title(cfg["title"], color='#f8fafc', fontsize=11, fontweight='bold', pad=12)
        ax.text(0.0, 1.05, cfg["subtitle"], color='#cbd5e1', fontsize=8.5, ha='center', transform=ax.transAxes)
        
        # Summary Box
        score_text = f"통과: {pass_cnt}/12  |  데드존(<52cm): {dead_cnt}개  |  이탈: {out_cnt}개"
        score_col = '#10b981' if (pass_cnt == 12) else ('#f59e0b' if dead_cnt > 0 else '#ef4444')
        ax.text(-0.95, 0.95, score_text, color=score_col, fontsize=9, fontweight='bold')
        
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color('#1e293b')
            
    fig.suptitle("ARAT & 책상 기하 기반 Intel RealSense D455 카메라 배치 조건별 비교 시뮬레이션", color='white', fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=200, facecolor='#0f172a', edgecolor='none')
    plt.close()
    print(f"[SUCCESS] Saved comparison figure to: {output_path}")

if __name__ == "__main__":
    out_img = os.path.join(os.path.dirname(__file__), "camera_simulation_comparison.png")
    render_comparison_figure(out_img)

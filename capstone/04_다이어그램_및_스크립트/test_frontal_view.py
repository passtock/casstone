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

def check_shelf_occlusion(cam_pos, pt_pos):
    """
    Checks if the line of sight from cam_pos to pt_pos is blocked by the 37cm shelf.
    Shelf bounds: X in [-0.11, 0.11], Y in [0.20, 0.35], Z in [0, 0.37]
    """
    # Parametric line: P(t) = cam_pos + t * (pt_pos - cam_pos), t in [0, 1]
    # Check intersection with Y = 0.20 and Y = 0.35 planes
    direction = pt_pos - cam_pos
    if abs(direction[1]) < 1e-6:
        return False
        
    for y_plane in [0.20, 0.35]:
        t = (y_plane - cam_pos[1]) / direction[1]
        if 0 < t < 1:
            intersect = cam_pos + t * direction
            # Check if inside shelf X and Z bounds
            if -SHELF_W/2 <= intersect[0] <= SHELF_W/2 and 0 <= intersect[2] <= SHELF_H:
                return True
                
    # Also check top plane Z = 0.37
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

# Test 1: Frontal Upper View (맞은편 정면 상측: Y = +0.85m, Z = +0.80m, X = 0)
cam_front = np.array([0.00, 0.85, 0.80])
target_front = np.array([0.00, 0.05, 0.20])

print("=== 정면 상측 뷰 (Frontal Upper View) 분석 ===")
print(f"카메라 위치: {cam_front}, 타겟: {target_front}")
R, t, pos, forward, right, up = get_camera_matrix(cam_front, target_front)

for name, data in LANDMARKS.items():
    pt = data["pos"]
    u, v, zc, in_fov = project_point(pt, R, t, D455_RGB_HFOV, D455_RGB_VFOV)
    is_occluded = check_shelf_occlusion(cam_front, pt)
    print(f"  {name:16s}: zc={zc:.2f}m, in_fov={in_fov}, 선반가림(Occluded)={is_occluded}")

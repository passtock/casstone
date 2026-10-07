# -*- coding: utf-8 -*-
"""
02_analyze_offline.py — 녹화된 RGB-D 세션 사후 최고정밀 3D 관절 및 체간 분석기
=============================================================================
[특징]
- 실시간 제약이 없으므로 MediaPipe 최고 정밀도 모델(Pose Heavy complexity=2)을 사용하여
  가장 정확하고 노이즈 없는 3D 랜드마크를 추출합니다.
- 녹화된 원본 Color 영상과 Depth.npz를 1:1 동기화하여 역투영(Deprojection) 연산.
- 체간 전방 기울기(Trunk Forward Lean), 좌우 틸트, 어깨 및 손목 3D 거리/궤적을 일괄 계산.

[사용법]
  python 02_analyze_offline.py
    -> 가장 최근에 녹화된 세션 폴더를 자동으로 감지하여 분석합니다.
  python 02_analyze_offline.py --session recordings/session_20261007_163000

[출력 결과물]
  세션 폴더 내에 자동 생성:
    ├── pose_hands_3d.csv    (프레임별 전체 관절의 3D 좌표 [X, Y, Z 미터])
    ├── summary_report.txt   (체간 거리, 기울기 통계 및 보상움직임 분석 리포트)
    └── annotated_video.mp4  (스켈레톤과 3D 거리가 시각화된 검증용 영상)
"""

import os
import sys
import glob
import time
import math
import json
import csv
import cv2
import numpy as np
import mediapipe as mp


def backproject_pixel(u, v, z_m, intr):
    """카메라 내부파라미터(fx, fy, cx, cy)를 이용해 픽셀 (u, v)와 깊이 z(m)를 3D 좌표 (X, Y, Z 미터)로 역투영"""
    if intr is None or z_m is None or not np.isfinite(z_m) or z_m <= 0:
        return None
    fx, fy = intr.get("fx"), intr.get("fy")
    cx, cy = intr.get("ppx"), intr.get("ppy")
    if not (fx and fy and cx and cy):
        return None
    x = (float(u) - cx) / fx * float(z_m)
    y = (float(v) - cy) / fy * float(z_m)
    return (float(x), float(y), float(z_m))


def sample_depth_median(depth_m, u, v, win=5, valid_range=(0.15, 4.5)):
    """(u, v) 주변 win x win 윈도우의 유효 깊이 중앙값(미터) 추출"""
    if depth_m is None:
        return None
    h, w = depth_m.shape[:2]
    u_i, v_i = int(round(u)), int(round(v))
    if u_i < 0 or u_i >= w or v_i < 0 or v_i >= h:
        return None
    r = win // 2
    y0, y1 = max(0, v_i - r), min(h, v_i + r + 1)
    x0, x1 = max(0, u_i - r), min(w, u_i + r + 1)
    patch = depth_m[y0:y1, x0:x1].ravel()
    valid = patch[(patch >= valid_range[0]) & (patch <= valid_range[1]) & np.isfinite(patch)]
    if len(valid) == 0:
        return None
    return float(np.median(valid))


def find_latest_session(base_dir="recordings"):
    """피험자 및 과제별 하위 폴더까지 탐색하여 가장 최근에 녹화된 세션 폴더 찾기"""
    candidate_sessions = []
    if not os.path.exists(base_dir):
        return None

    # recordings 하위 모든 디렉토리 탐색
    for root, dirs, files in os.walk(base_dir):
        if "metadata.json" in files and "color.mp4" in files and "depth.npz" in files:
            candidate_sessions.append(root)

    if not candidate_sessions:
        return None

    # 수정 시간 기준 가장 최신 폴더 선택
    candidate_sessions.sort(key=lambda p: os.path.getmtime(p))
    return candidate_sessions[-1]



def analyze_session(session_dir):
    print("\n" + "="*70)
    print(f"  [사후 오프라인 분석기] 세션 폴더: {session_dir}")
    print("="*70)

    color_path = os.path.join(session_dir, "color.mp4")
    depth_path = os.path.join(session_dir, "depth.npz")
    meta_path = os.path.join(session_dir, "metadata.json")
    ts_path = os.path.join(session_dir, "timestamps.csv")

    if not (os.path.exists(color_path) and os.path.exists(depth_path) and os.path.exists(meta_path)):
        print(f"[오류] 세션 필수 파일이 없습니다: {session_dir}")
        return

    # 메타데이터 로드
    with open(meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    depth_scale = meta.get("depth_scale_m", 0.001)
    intrinsics = meta.get("intrinsics", {})
    fps = meta.get("fps", 30)

    # 깊이 압축 데이터 로드
    print("[1/4] 깊이(Depth) 데이터 로드 중...")
    depth_archive = np.load(depth_path)
    depth_keys = sorted(depth_archive.files)
    total_depth_frames = len(depth_keys)
    print(f"  * 깊이 프레임 수: {total_depth_frames}")

    # 비디오 열기
    print("[2/4] 원본 컬러 영상 로드 중...")
    cap = cv2.VideoCapture(color_path)
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  * 비디오: {width}x{height} @ {fps}fps (총 {total_video_frames} 프레임)")

    # 최고 정밀도 MediaPipe 모델 초기화
    print("[3/4] MediaPipe Heavy 모델 초기화 중 (최고 정밀도 complexity=2)...")
    mp_pose = mp.solutions.pose
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    # 실시간 제약이 없으므로 가장 정확한 complexity=2 사용!
    pose_model = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    hands_model = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 결과물 출력 설정
    out_csv_path = os.path.join(session_dir, "pose_hands_3d.csv")
    out_vid_path = os.path.join(session_dir, "annotated_video.mp4")
    out_rep_path = os.path.join(session_dir, "summary_report.txt")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(out_vid_path, fourcc, float(fps), (width, height))

    csv_rows = []
    # 통계용 리스트
    torso_z_list = []
    forward_lean_list = []
    lateral_tilt_list = []
    warning_frames = []

    print("[4/4] 프레임별 3D 좌표 역투영 및 체간 분석 시작...")
    frame_idx = 0
    t0 = time.time()

    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break

        frame_id = frame_idx + 1
        time_s = frame_idx / float(fps)

        # 1:1 매칭되는 depth 맵 조회
        depth_key = f"d_{frame_id:06d}"
        if depth_key in depth_archive:
            depth_u16 = depth_archive[depth_key]
            depth_m = depth_u16.astype(np.float32) * depth_scale
        else:
            depth_m = None

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        annotated = frame_bgr.copy()

        # 1. 몸통(Pose) Heavy 추론
        pose_res = pose_model.process(rgb)
        pose_3d = {}

        if pose_res.pose_landmarks:
            mp_drawing.draw_landmarks(
                annotated,
                pose_res.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=3),
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 220, 0), thickness=2)
            )

            for j, lm in enumerate(pose_res.pose_landmarks.landmark):
                u, v = lm.x * width, lm.y * height
                z_val = sample_depth_median(depth_m, u, v) if depth_m is not None else None
                pt_3d = backproject_pixel(u, v, z_val, intrinsics) if z_val else None

                x_3d, y_3d, z_3d = pt_3d if pt_3d else (np.nan, np.nan, np.nan)
                csv_rows.append([frame_id, f"{time_s:.4f}", "pose", j, f"{lm.visibility:.3f}",
                                 f"{x_3d:.4f}" if np.isfinite(x_3d) else "",
                                 f"{y_3d:.4f}" if np.isfinite(y_3d) else "",
                                 f"{z_3d:.4f}" if np.isfinite(z_3d) else ""])

                if pt_3d:
                    pose_3d[j] = pt_3d

            # 어깨(11, 12), 골반(23, 24), 코(0)
            l_sh, r_sh = pose_3d.get(11), pose_3d.get(12)
            l_hip, r_hip = pose_3d.get(23), pose_3d.get(24)
            nose = pose_3d.get(0)

            # 주요 관절에 거리 표기
            for j_idx, label in [(11, "L_Sh"), (12, "R_Sh"), (15, "L_Wr"), (16, "R_Wr")]:
                if j_idx in pose_3d:
                    u_j = int(pose_res.pose_landmarks.landmark[j_idx].x * width)
                    v_j = int(pose_res.pose_landmarks.landmark[j_idx].y * height)
                    cv2.putText(annotated, f"{label}:{pose_3d[j_idx][2]:.2f}m", (u_j + 8, v_j - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

            # 체간 거리 및 기울기 계산
            if l_sh and r_sh:
                sh_mid = np.array([(l_sh[i] + r_sh[i]) / 2.0 for i in range(3)])
                torso_z_list.append(sh_mid[2])

                if l_hip and r_hip:
                    hip_mid = np.array([(l_hip[i] + r_hip[i]) / 2.0 for i in range(3)])
                    vec = sh_mid - hip_mid
                    f_lean = math.degrees(math.atan2(-vec[2], -vec[1]))
                    l_tilt = math.degrees(math.atan2(vec[0], -vec[1]))
                elif nose:
                    vec = np.array(nose) - sh_mid
                    f_lean = math.degrees(math.atan2(vec[2], -vec[1]))
                    l_tilt = math.degrees(math.atan2(-vec[0], -vec[1]))
                else:
                    f_lean, l_tilt = None, None

                if f_lean is not None:
                    forward_lean_list.append(f_lean)
                    lateral_tilt_list.append(l_tilt)
                    is_warn = abs(f_lean) > 12.0
                    if is_warn:
                        warning_frames.append(frame_id)

                    # 영상 상단 HUD
                    col = (0, 0, 255) if is_warn else (0, 255, 0)
                    cv2.putText(annotated, f"Frame {frame_id:04d} | Torso Z: {sh_mid[2]:.2f}m | Lean: {f_lean:+.1f} deg",
                                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)

        # 2. 양손(Hands) 추론
        hands_res = hands_model.process(rgb)
        if hands_res.multi_hand_landmarks:
            for h_idx, (h_lms, h_meta) in enumerate(zip(hands_res.multi_hand_landmarks, hands_res.multi_handedness)):
                label = h_meta.classification[0].label
                mp_drawing.draw_landmarks(
                    annotated,
                    h_lms,
                    mp_hands.HAND_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0, 140, 255), thickness=1, circle_radius=2),
                    connection_drawing_spec=mp_drawing.DrawingSpec(color=(255, 80, 0), thickness=2)
                )
                for j, lm in enumerate(h_lms.landmark):
                    u, v = lm.x * width, lm.y * height
                    z_val = sample_depth_median(depth_m, u, v) if depth_m is not None else None
                    pt_3d = backproject_pixel(u, v, z_val, intrinsics) if z_val else None
                    x_3d, y_3d, z_3d = pt_3d if pt_3d else (np.nan, np.nan, np.nan)
                    csv_rows.append([frame_id, f"{time_s:.4f}", f"hand_{label}", j, "1.000",
                                     f"{x_3d:.4f}" if np.isfinite(x_3d) else "",
                                     f"{y_3d:.4f}" if np.isfinite(y_3d) else "",
                                     f"{z_3d:.4f}" if np.isfinite(z_3d) else ""])

        out_writer.write(annotated)
        frame_idx += 1

        # 진행률 표시
        if frame_idx % 15 == 0 or frame_idx == total_video_frames:
            pct = (frame_idx / total_video_frames) * 100
            bar = "=" * int(pct // 5) + ">" + " " * (20 - int(pct // 5))
            sys.stdout.write(f"\r  진행률: [{bar}] {pct:.1f}% ({frame_idx}/{total_video_frames} 프레임)")
            sys.stdout.flush()

    cap.release()
    out_writer.release()
    pose_model.close()
    hands_model.close()
    elapsed = time.time() - t0
    print(f"\n\n[분석 완료] 소요 시간: {elapsed:.1f}초 (초당 {frame_idx/max(elapsed, 0.01):.1f} 프레임 처리)")

    # 1. 3D 좌표 CSV 파일 저장
    csv_header = ["Frame_ID", "time_s", "type", "Landmark_ID", "visibility", "X_m", "Y_m", "Z_m"]
    with open(out_csv_path, "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(csv_header)
        w.writerows(csv_rows)
    print(f"  * 3D 좌표 CSV: {out_csv_path}")

    # 2. 통계 요약 리포트 작성
    avg_torso_z = np.mean(torso_z_list) if torso_z_list else 0.0
    avg_lean = np.mean(forward_lean_list) if forward_lean_list else 0.0
    max_lean = np.max(np.abs(forward_lean_list)) if forward_lean_list else 0.0
    warn_ratio = (len(warning_frames) / max(len(forward_lean_list), 1)) * 100

    subj_data = meta.get("subject", {})
    subj_name = subj_data.get("name", "미지정")
    subj_age = subj_data.get("age", "-")
    subj_gender = subj_data.get("gender", "-")
    task_name = meta.get("task", "자유_과제")

    report_lines = [
        "============================================================",
        f"  오프라인 RGB-D 3D 분석 리포트 - {os.path.basename(session_dir)}",
        "============================================================",
        f"피험자 정보: {subj_name} ({subj_age}세 / {subj_gender})",
        f"수행 과제  : {task_name}",
        f"분석 시각  : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"총 프레임 수: {frame_idx} 프레임 ({frame_idx / float(fps):.1f} 초)",
        f"사용 모델  : MediaPipe Pose Heavy (complexity=2) + Hands",
        "",
        "[1. 체간(Torso) 거리 통계]",
        f"  - 평균 체간(어깨 중심) 거리 : {avg_torso_z:.3f} m",
        f"  - 최소 ~ 최대 거리        : {np.min(torso_z_list) if torso_z_list else 0:.3f}m ~ {np.max(torso_z_list) if torso_z_list else 0:.3f}m",
        "",
        "[2. 체간 보상 움직임(Trunk Forward Lean) 분석]",
        f"  - 평균 전방 기울기 각도      : {avg_lean:+.1f} deg",
        f"  - 최대 전방 기울기 각도      : {max_lean:.1f} deg",
        f"  - 보상 움직임(>12도) 발생률 : {warn_ratio:.1f}% ({len(warning_frames)} / {len(forward_lean_list)} 프레임)",
        "",
        "[3. 생성된 파일]",
        f"  1) 3D 정밀 좌표 CSV     : {out_csv_path}",
        f"  2) 시각화 검증 비디오   : {out_vid_path}",
        "============================================================"
    ]
    report_text = "\n".join(report_lines)
    with open(out_rep_path, "w", encoding="utf-8") as fp:
        fp.write(report_text)

    print(f"  * 시각화 비디오: {out_vid_path}")
    print(f"  * 요약 리포트  : {out_rep_path}")
    print("\n" + report_text + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Offline 3D Pose & Hands Analyzer")
    parser.add_argument("--session", type=str, default="", help="분석할 세션 폴더 경로 (미지정 시 가장 최근 세션)")
    args = parser.parse_args()

    target = args.session
    if not target:
        target = find_latest_session("recordings")
        if not target:
            # 호진파일 폴더 내 recordings 탐색
            target = find_latest_session(os.path.join("capstone", "호진파일", "recordings"))

    if not target or not os.path.isdir(target):
        print("[오류] 분석할 세션 폴더를 찾지 못했습니다. 녹화를 먼저 실행해주세요.")
        print("사용법: python 02_analyze_offline.py --session <세션폴더경로>")
    else:
        analyze_session(target)

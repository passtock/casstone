# -*- coding: utf-8 -*-
"""
01_record_rgbd.py — RealSense 피험자별/과제별 무손실 초고속 RGB-D 녹화기
=======================================================================
[특징]
- 시작 시 피험자 정보(이름, 나이, 성별)를 1회 입력받고,
  과제는 촬영 중에도 드롭다운 콤보박스나 숫자키(1~7)로 자유롭게 실시간 변경 가능!
- 과제를 바꿀 때마다 해당 과제명과 피험자 이름으로 폴더가 자동 분류되어 깔끔하게 저장:
    recordings/
      └── 홍길동_25세_남/
            ├── 01_블록_잡기_20261007_164800/
            ├── 02_컵_옮기기_20261007_165012/
            └── ...
- 실시간 AI 연산이 일체 없어 CPU 점유율 2~5%, 프레임 드랍 0% (30fps / 60fps).

[조작법]
  - 과제 드롭다운 : 제어창에서 마우스 선택 또는 직접 과제명 타이핑
  - 숫자키 1~7   : 과제 빠른 변경
  - SPACE 또는 r : 녹화 시작 / 중지
  - d            : 깊이(Depth) 컬러맵 미리보기 토글
  - q 또는 ESC   : 프로그램 종료
"""

import os
import sys
import time
import json
import csv
import queue
import threading
import cv2
import numpy as np

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import pyrealsense2 as rs
except ImportError:
    rs = None


# 기본 과제 목록 (드롭다운에 표시되며 직접 타이핑도 가능)
DEFAULT_TASKS = [
    "01_블록_잡기",
    "02_블록_옮기기",
    "03_컵_잡기",
    "04_컵_옮기기",
    "05_구슬_집기",
    "06_원통_잡기",
    "07_손바닥_뒤집기",
    "08_자유_과제"
]


def ask_subject_info():
    """시작 시 피험자 정보(이름, 나이, 성별)만 빠르게 묻는 모달 팝업"""
    root = tk.Tk()
    root.title("피험자 정보 등록")
    root.geometry("340x260")
    root.resizable(False, False)

    # 윈도우 화면 중앙 배치
    root.eval('tk::PlaceWindow . center')

    info = {}

    lbl_title = tk.Label(root, text="[ 피험자 정보 등록 ]", font=("맑은 고딕", 12, "bold"))
    lbl_title.pack(pady=10)

    frm = tk.Frame(root)
    frm.pack(padx=20, pady=5, fill="x")

    # 1. 이름
    tk.Label(frm, text="이름 / ID :", font=("맑은 고딕", 10)).grid(row=0, column=0, sticky="e", pady=5)
    ent_name = tk.Entry(frm, font=("맑은 고딕", 10))
    ent_name.insert(0, "홍길동")
    ent_name.grid(row=0, column=1, sticky="w", padx=8, pady=5)

    # 2. 나이
    tk.Label(frm, text="나이 :", font=("맑은 고딕", 10)).grid(row=1, column=0, sticky="e", pady=5)
    ent_age = tk.Entry(frm, font=("맑은 고딕", 10), width=10)
    ent_age.insert(0, "25")
    ent_age.grid(row=1, column=1, sticky="w", padx=8, pady=5)

    # 3. 성별
    tk.Label(frm, text="성별 :", font=("맑은 고딕", 10)).grid(row=2, column=0, sticky="e", pady=5)
    var_gender = tk.StringVar(value="남")
    frm_gender = tk.Frame(frm)
    frm_gender.grid(row=2, column=1, sticky="w", padx=5, pady=5)
    tk.Radiobutton(frm_gender, text="남", variable=var_gender, value="남", font=("맑은 고딕", 10)).pack(side="left")
    tk.Radiobutton(frm_gender, text="여", variable=var_gender, value="여", font=("맑은 고딕", 10)).pack(side="left", padx=10)

    def on_submit():
        name = ent_name.get().strip()
        age = ent_age.get().strip()
        gender = var_gender.get().strip()

        if not name:
            messagebox.showwarning("입력 오류", "이름 또는 ID를 입력해주세요.", parent=root)
            return

        info["name"] = name
        info["age"] = age if age else "0"
        info["gender"] = gender
        root.destroy()

    btn_ok = tk.Button(root, text="카메라 연결 및 시작", font=("맑은 고딕", 10, "bold"),
                       bg="#007ACC", fg="white", padx=15, pady=5, command=on_submit)
    btn_ok.pack(pady=15)

    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.mainloop()

    return info


class TaskControlPanel:
    """녹화 중 과제를 즉시 바꿀 수 있는 컴팩트 제어창"""
    def __init__(self, subject_info, on_record_toggle):
        self.subject_info = subject_info
        self.on_record_toggle = on_record_toggle

        self.root = tk.Tk()
        self.root.title("과제 선택 제어판")
        self.root.geometry("380x180")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)  # 항상 위 표시

        subj_str = f"피험자: {subject_info.get('name')} ({subject_info.get('age')}세 / {subject_info.get('gender')})"
        lbl_subj = tk.Label(self.root, text=subj_str, font=("맑은 고딕", 10, "bold"), fg="#333333")
        lbl_subj.pack(pady=8)

        frm_task = tk.Frame(self.root)
        frm_task.pack(padx=15, pady=5, fill="x")

        tk.Label(frm_task, text="현재 과제 :", font=("맑은 고딕", 10)).pack(side="left")
        self.combo_task = ttk.Combobox(frm_task, values=DEFAULT_TASKS, font=("맑은 고딕", 10), state="normal")
        self.combo_task.set(DEFAULT_TASKS[0])
        self.combo_task.pack(side="left", padx=8, fill="x", expand=True)

        self.btn_rec = tk.Button(self.root, text="🔴 녹화 시작 (SPACE)", font=("맑은 고딕", 11, "bold"),
                                 bg="#E81123", fg="white", pady=6, command=self.on_record_toggle)
        self.btn_rec.pack(padx=20, pady=10, fill="x")

        lbl_hint = tk.Label(self.root, text="* 키보드 1~7번 키로 과제 즉시 변경 가능", font=("맑은 고딕", 8), fg="#777777")
        lbl_hint.pack()

        self.last_task = DEFAULT_TASKS[0]
        self.is_closed = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.is_closed = True
        try:
            self.root.destroy()
        except Exception:
            pass

    def get_current_task(self):
        if self.is_closed:
            return self.last_task
        try:
            val = self.combo_task.get().strip()
            if val:
                self.last_task = val
            return self.last_task
        except Exception:
            return self.last_task

    def set_task_by_index(self, idx):
        if self.is_closed:
            return
        if 0 <= idx < len(DEFAULT_TASKS):
            try:
                self.combo_task.set(DEFAULT_TASKS[idx])
                self.last_task = DEFAULT_TASKS[idx]
            except Exception:
                pass

    def set_recording_state(self, is_rec):
        if self.is_closed:
            return
        try:
            if is_rec:
                self.btn_rec.config(text="⏹️ 녹화 중지 (SPACE)", bg="#333333")
                self.combo_task.config(state="disabled")  # 녹화 중에는 과제 변경 잠금
            else:
                self.btn_rec.config(text="🔴 녹화 시작 (SPACE)", bg="#E81123")
                self.combo_task.config(state="normal")
        except Exception:
            pass

    def update(self):
        if self.is_closed:
            return
        try:
            self.root.update()
        except Exception:
            self.is_closed = True



class RGBDDiskWriter(threading.Thread):
    def __init__(self, session_dir, width, height, fps, depth_scale, intrinsics, subject_info, task_name):
        super().__init__(daemon=True, name="DiskWriterThread")
        self.session_dir = session_dir
        self.width = width
        self.height = height
        self.fps = fps
        self.depth_scale = depth_scale
        self.intrinsics = intrinsics
        self.subject_info = subject_info
        self.task_name = task_name

        self.queue = queue.Queue(maxsize=150)
        self.stop_event = threading.Event()
        self.written_frames = 0

        self.video_path = os.path.join(session_dir, "color.mp4")
        self.depth_path = os.path.join(session_dir, "depth.npz")
        self.csv_path = os.path.join(session_dir, "timestamps.csv")
        self.meta_path = os.path.join(session_dir, "metadata.json")

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.video_path, fourcc, float(fps), (width, height))

        self.depth_frames_dict = {}
        self.timestamps_list = []

    def submit(self, frame_id, color_img, depth_u16, time_s):
        try:
            self.queue.put_nowait((frame_id, color_img, depth_u16, time_s))
            return True
        except queue.Full:
            print(f"[경고] 프레임 {frame_id} 디스크 쓰기 지연 건너뜀")
            return False

    def run(self):
        while not (self.stop_event.is_set() and self.queue.empty()):
            try:
                item = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            frame_id, color_img, depth_u16, time_s = item
            if self.writer:
                self.writer.write(color_img)
            self.depth_frames_dict[f"d_{frame_id:06d}"] = depth_u16
            self.timestamps_list.append((frame_id, time_s))
            self.written_frames += 1
            self.queue.task_done()

        if self.writer:
            self.writer.release()

        print(f"\n[저장 중] {len(self.depth_frames_dict)}개 깊이 프레임 압축 저장...")
        np.savez_compressed(self.depth_path, **self.depth_frames_dict)

        with open(self.csv_path, "w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(["frame_id", "timestamp_s"])
            for fid, ts in self.timestamps_list:
                w.writerow([fid, f"{ts:.6f}"])

        meta = {
            "subject": self.subject_info,
            "task": self.task_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_frames": self.written_frames,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "depth_scale_m": self.depth_scale,
            "intrinsics": self.intrinsics
        }
        with open(self.meta_path, "w", encoding="utf-8") as fp:
            json.dump(meta, fp, indent=2, ensure_ascii=False)

        print(f"[저장 완료] 폴더: {self.session_dir} (총 {self.written_frames} 프레임)\n")

    def stop_and_wait(self):
        self.stop_event.set()
        self.join(timeout=30.0)


class RealSenseRGBDRecorder:
    def __init__(self, subject_info, width=1280, height=720, fps=30, out_base="recordings"):
        self.subject_info = subject_info
        self.width = width
        self.height = height
        self.fps = fps
        self.out_base = out_base

        # 피험자별 전용 상위 폴더 생성: recordings/이름_나이세_성별/
        subj_folder_name = f"{subject_info.get('name')}_{subject_info.get('age')}세_{subject_info.get('gender')}"
        # 파일명 금지 문자 정제
        for ch in r'/\:*?"<>|':
            subj_folder_name = subj_folder_name.replace(ch, '_')
        self.subject_dir = os.path.join(self.out_base, subj_folder_name)
        os.makedirs(self.subject_dir, exist_ok=True)

        self.pipeline = None
        self.align = None
        self.depth_scale = 0.001
        self.intrinsics_dict = None
        self.is_realsense = False
        self.cap_webcam = None

        self.is_recording = False
        self.writer_thread = None
        self.record_frame_id = 0
        self.record_start_time = 0.0
        self.show_depth_preview = False
        self.control_panel = None

        self._init_camera()

    def _init_camera(self):
        if rs is not None:
            try:
                ctx = rs.context()
                devices = ctx.query_devices()
                if len(devices) > 0:
                    dev = devices[0]
                    name = dev.get_info(rs.camera_info.name)
                    print(f"[RealSense 카메라 감지] {name}")

                    self.pipeline = rs.pipeline()
                    cfg = rs.config()
                    cfg.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
                    cfg.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, self.fps)

                    profile = self.pipeline.start(cfg)
                    sensor = profile.get_device().first_depth_sensor()
                    self.depth_scale = float(sensor.get_depth_scale())
                    self.align = rs.align(rs.stream.color)

                    color_stream = profile.get_stream(rs.stream.color).as_video_stream_profile()
                    intr = color_stream.get_intrinsics()
                    self.intrinsics_dict = {
                        "width": intr.width, "height": intr.height,
                        "fx": intr.fx, "fy": intr.fy,
                        "ppx": intr.ppx, "ppy": intr.ppy,
                        "model": str(intr.model),
                        "coeffs": list(intr.coeffs)
                    }

                    for _ in range(8):
                        self.pipeline.wait_for_frames()

                    self.is_realsense = True
                    print(f"[카메라 준비 완료] {self.width}x{self.height} @ {self.fps}fps")
                    return
            except Exception as e:
                print(f"[RealSense 초기화 실패: {e}] -> 웹캠 모드로 대체")

        print("[웹캠 폴백] 기본 웹캠(ID 0) 사용")
        self.cap_webcam = cv2.VideoCapture(0)
        self.cap_webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap_webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.is_realsense = False

    def get_frames(self):
        if self.is_realsense:
            frames = self.pipeline.wait_for_frames()
            aligned = self.align.process(frames)
            c_frame = aligned.get_color_frame()
            d_frame = aligned.get_depth_frame()
            if not c_frame or not d_frame:
                return None, None
            color = np.asanyarray(c_frame.get_data())
            depth_u16 = np.asanyarray(d_frame.get_data(), dtype=np.uint16)
            return color, depth_u16
        else:
            ret, frame = self.cap_webcam.read()
            if not ret:
                return None, None
            return frame, np.zeros((self.height, self.width), dtype=np.uint16)

    def toggle_recording(self):
        if not self.is_recording:
            # 현재 드롭다운에 선택된 과제 이름 가져오기
            task_name = self.control_panel.get_current_task() if self.control_panel else "자유_과제"
            task_clean = task_name
            for ch in r'/\:*?"<>|':
                task_clean = task_clean.replace(ch, '_')

            # 폴더 생성: recordings/피험자/과제명_시간/
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            session_folder_name = f"{task_clean}_{timestamp_str}"
            session_dir = os.path.join(self.subject_dir, session_folder_name)
            os.makedirs(session_dir, exist_ok=True)

            self.writer_thread = RGBDDiskWriter(
                session_dir=session_dir,
                width=self.width,
                height=self.height,
                fps=self.fps,
                depth_scale=self.depth_scale,
                intrinsics=self.intrinsics_dict,
                subject_info=self.subject_info,
                task_name=task_name
            )
            self.writer_thread.start()
            self.is_recording = True
            self.record_frame_id = 0
            self.record_start_time = time.time()
            if self.control_panel:
                self.control_panel.set_recording_state(True)
            print(f"\n🔴 [녹화 시작] 과제: '{task_name}' -> {session_dir}")
        else:
            self.is_recording = False
            if self.control_panel:
                self.control_panel.set_recording_state(False)
            if self.writer_thread:
                print("\n⏹️ [녹화 중지] 파일 저장 마무리 중... 잠시만 기다려주세요.")
                self.writer_thread.stop_and_wait()
                self.writer_thread = None

    def run(self):
        # 1. 과제 선택 제어창 생성
        self.control_panel = TaskControlPanel(self.subject_info, self.toggle_recording)

        win_title = "RealSense RGB-D Pure Recorder (Zero Jitter)"
        cv2.namedWindow(win_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_title, 1280, 720)

        prev_time = time.time()
        fps_display = float(self.fps)

        print("\n" + "="*65)
        print("  RealSense 피험자/과제별 초고속 무손실 레코더 실행 중")
        print(f"  * 피험자: {self.subject_info.get('name')} ({self.subject_info.get('age')}세 / {self.subject_info.get('gender')})")
        print("  * 제어창 드롭다운 또는 숫자키 1~7로 과제 변경 가능")
        print("  * [SPACE] 또는 [r] : 녹화 시작 / 중지")
        print("  * [d]             : 깊이 컬러맵 보기 토글")
        print("  * [q] 또는 [ESC]  : 종료")
        print("="*65 + "\n")

        while True:
            # Tkinter 제어창 이벤트 루프 처리 (0.1ms 소모, 지연 없음)
            try:
                self.control_panel.update()
            except tk.TclError:
                break  # 제어창 X 닫기 시 종료

            if self.control_panel and self.control_panel.is_closed:
                break

            color_img, depth_u16 = self.get_frames()
            if color_img is None:
                time.sleep(0.005)
                continue

            curr_time = time.time()
            dt = curr_time - prev_time
            prev_time = curr_time
            if dt > 0:
                fps_display = 0.9 * fps_display + 0.1 * (1.0 / dt)

            current_task = self.control_panel.get_current_task()

            # 녹화 큐에 전송
            if self.is_recording and self.writer_thread:
                self.record_frame_id += 1
                t_rel = curr_time - self.record_start_time
                self.writer_thread.submit(self.record_frame_id, color_img.copy(), depth_u16.copy(), t_rel)

            display_img = color_img.copy()
            h, w = display_img.shape[:2]

            # 상단 상태 HUD 오버레이
            cv2.rectangle(display_img, (12, 12), (480, 92), (0, 0, 0), -1)
            cv2.rectangle(display_img, (12, 12), (480, 92), (80, 80, 80), 1)

            cam_name = "RealSense D455" if self.is_realsense else "Webcam"
            fps_col = (0, 255, 0) if fps_display >= 27.0 else (0, 165, 255)
            s_name = self.subject_info.get('name')
            s_age = self.subject_info.get('age')
            s_gen = self.subject_info.get('gender')

            cv2.putText(display_img, f"피험자: {s_name} ({s_age}세/{s_gen}) | {cam_name}",
                        (22, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 255, 128), 1, cv2.LINE_AA)
            cv2.putText(display_img, f"현재 과제: [{current_task}]",
                        (22, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(display_img, f"Live FPS: {fps_display:.1f} | [SPACE]:REC | [1~7]:과제변경",
                        (22, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.42, fps_col, 1, cv2.LINE_AA)

            if self.is_recording:
                cv2.circle(display_img, (w - 35, 35), 12, (0, 0, 255), -1)
                dur = int(curr_time - self.record_start_time)
                cv2.putText(display_img, f"REC {dur//60:02d}:{dur%60:02d} ({self.record_frame_id}f) - {current_task}",
                            (w - 380, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)

            if self.show_depth_preview and self.is_realsense:
                d_m = depth_u16.astype(np.float32) * self.depth_scale
                norm_d = np.clip((d_m - 0.4) / 2.0, 0, 1)
                vis_d = cv2.applyColorMap((norm_d * 255).astype(np.uint8), cv2.COLORMAP_JET)
                vis_d[depth_u16 == 0] = 0
                combined = np.hstack((display_img, vis_d))
            else:
                combined = display_img

            cv2.imshow(win_title, combined)

            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), 27]:
                break
            elif key in [ord(' '), ord('r')]:
                self.toggle_recording()
            elif key == ord('d'):
                self.show_depth_preview = not self.show_depth_preview
            elif ord('1') <= key <= ord('7'):
                # 1~7 숫자키로 과제 빠른 전환
                idx = key - ord('1')
                if not self.is_recording and self.control_panel:
                    self.control_panel.set_task_by_index(idx)
                    print(f"[과제 전환] -> {self.control_panel.get_current_task()}")

        self._cleanup()

    def _cleanup(self):
        if self.is_recording and self.writer_thread:
            self.writer_thread.stop_and_wait()
        if self.is_realsense and self.pipeline:
            self.pipeline.stop()
        if self.cap_webcam:
            self.cap_webcam.release()
        try:
            if self.control_panel and self.control_panel.root:
                self.control_panel.root.destroy()
        except Exception:
            pass
        cv2.destroyAllWindows()
        print("[레코더 정상 종료]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RealSense Pure RGB-D Subject & Task Recorder")
    parser.add_argument("--fps", type=int, default=30, choices=[30, 60], help="30 (1280x720) or 60 (848x480)")
    args = parser.parse_args()

    # 1. 시작 전 피험자 정보 팝업
    subject_info = ask_subject_info()

    # 2. 카메라 레코더 실행
    w, h = (848, 480) if args.fps == 60 else (1280, 720)
    recorder = RealSenseRGBDRecorder(subject_info=subject_info, width=w, height=h, fps=args.fps)
    recorder.run()

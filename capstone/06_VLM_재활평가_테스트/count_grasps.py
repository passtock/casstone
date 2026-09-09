"""80초 전체 영상 기반 물체 파지 횟수 카운팅 (Repetition Counting) 스크립트
- 80초 전체 영상을 시간대별로 촘촘히 샘플링 (타임스탬프 각인)
- 질문: "80초 동안 물체를 몇 번 집었는가? (각 반복 구간 및 총 횟수 도출)"
- 실시간 진행률 게이지 및 결과 출력
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image

import cv2
import numpy as np
import torch
from vlm_rehab_eval import VLMRehabEvaluator


def sample_video_with_timestamps(video_path: str, num_frames: int = 40, max_width: int = 420):
    """80초 전체 영상에서 균일하게 프레임을 추출하고, 화면 상단에 타임스탬프를 표기"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps

    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames_pil = []
    timestamps = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        cur_sec = idx / fps
        timestamps.append(cur_sec)

        # 해상도 리사이즈 (RTX 3060 최적화: 폭 420px)
        h, w = frame.shape[:2]
        if w > max_width:
            new_w = max_width
            new_h = int(h * (new_w / w))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 프레임 좌측 상단에 시간(초) 오버레이 각인 (VLM이 시간 흐름을 시각적으로 인지하도록 보조)
        cv2.putText(
            frame, f"T={cur_sec:.1f}s", (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA
        )

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames_pil.append(Image.fromarray(frame_rgb))

    cap.release()
    return frames_pil, timestamps, duration_s


def main():
    video_path = "KakaoTalk_20260909_183548574.mp4"
    if not os.path.exists(video_path):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {video_path}")
        return

    start_total_time = time.time()

    print("=" * 65)
    print("  80초 전체 영상 분석: 제자리 잡고 놓기(Grasp & Release) 횟수 카운팅")
    print("=" * 65, flush=True)

    # 1. 영상 샘플링 (80초 전 구간을 40개 프레임으로 정밀 샘플링, 약 2.0초 간격)
    num_sample_frames = 40
    print(f"\n[■■■■■                    ] 20% | [1/4] 80초 전체 구간에서 {num_sample_frames}개 프레임 추출 중 (약 2.0초 간격)...", flush=True)
    frames, timestamps, duration_s = sample_video_with_timestamps(
        video_path, num_frames=num_sample_frames, max_width=420
    )
    print(f" -> 추출 완료: 총 {duration_s:.1f}초 영상에서 {timestamps[0]:.1f}초부터 {timestamps[-1]:.1f}초까지 {len(frames)}개 구간 샘플링 완료", flush=True)

    # 2. VLM 모델 로드
    print(f"\n[■■■■■■■■■■               ] 40% | [2/4] VLM 모델(Qwen2.5-VL-3B) 로컬 GPU 로드 중...", flush=True)
    t0 = time.time()
    evaluator = VLMRehabEvaluator(
        model_name="Qwen/Qwen2.5-VL-3B-Instruct",
        quantization="none"  # 3060 6GB 사용 시 '4bit'로 변경 가능
    )
    print(f" -> 모델 로드 완료 (소요 시간: {time.time() - t0:.1f}초)", flush=True)

    # 3. 파지 횟수 카운팅 질의 (제자리 잡고 놓기 임상 정의 적용)
    print(f"\n[■■■■■■■■■■■■■■■          ] 70% | [3/4] 80초 전 구간 제자리 잡고 놓기(Grasp-Release) 반복 횟수 분석 질의 중...", flush=True)
    t0 = time.time()

    prompt_counting = (
        f"You are an expert clinical motion analyst analyzing {num_sample_frames} chronological video frames spanning a {duration_s:.1f}-second rehabilitation session. "
        "Each frame has a timestamp 'T=...s' stamped on the top-left.\n\n"
        "### CLINICAL EXPERIMENT PROTOCOL:\n"
        "- The participant is performing a repetitive 'In-place Grasp and Release' (제자리 잡고 놓기) rehabilitation task with both hands.\n"
        "- IMPORTANT: The two spherical objects are mounted on stands on the table. The participant DOES NOT lift the objects off the table into the air. The task is strictly to reach/grasp the objects and then release/disengage hands in place.\n"
        "- **DEFINITION OF 1 REPETITION (1회 반복)**:\n"
        "   1. **Grasp / Contact (잡기)**: Hands reach out and grasp, hold, or place fingers onto the spherical objects.\n"
        "   2. **Release / Disengage (놓기)**: Hands let go, fingers open, or hands pull back/lift away from the objects.\n"
        "- **CRITICAL TIMING RULE**:\n"
        "   - Continuous contact across several consecutive frames without releasing is ONE single prolonged grasp episode, NOT multiple repetitions.\n"
        "   - A new repetition ONLY begins when the hands visibly release (let go / pull away / lift off / open fingers) and then re-grasp the objects.\n\n"
        "### YOUR ANALYSIS TASK:\n"
        "1. **Hand State Tracking**: Observe the participant's hands on both spheres over time. Note when hands are GRASPING (touching/holding) vs. RELEASING (hands pulled away, off the objects, resting off the spheres, or fingers opened).\n"
        "2. **Repetition Episodes**: Identify and list each distinct [Grasp -> Release] repetition with start and end timestamps (e.g., 'Repetition 1: Grasp at T=...s ~ Release at T=...s').\n"
        "3. **Total Count**: Conclude with the TOTAL number of completed grasp-and-release repetitions.\n"
        "4. **Clinical Summary in Korean**.\n\n"
        "Format your final response as follows:\n"
        "[최종 집계]\n"
        "- 총 잡고 놓기(파지-해제) 반복 횟수: X회\n"
        "- 각 반복 구간 목록 (시작 잡기 ~ 놓기):\n"
        "  1) 1회차: T=...s ~ T=...s\n"
        "  ...\n"
        "- 임상 소견 요약:"
    )

    answer = evaluator.ask(frames, prompt_counting, max_new_tokens=768)
    print(f" -> VLM 추론 완료 (추론 시간: {time.time() - t0:.1f}초)", flush=True)

    # 4. 결과 출력 및 저장
    print(f"\n[■■■■■■■■■■■■■■■■■■■■] 100% | [4/4] 결과 리포트 저장 중...", flush=True)
    total_elapsed = time.time() - start_total_time

    report_md = f"""# 80초 전체 영상 제자리 잡고 놓기(Grasp-Release) 횟수 카운팅 분석 결과

- **대상 영상**: `{video_path}`
- **분석 구간**: 0초 ~ {duration_s:.1f}초 (총 {duration_s:.1f}초 전 구간 분석)
- **샘플링**: {num_sample_frames}개 타임스탬프 프레임 (약 2.0초 간격)
- **소요 시간**: {total_elapsed:.1f}초
- **분석 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 📋 VLM 분석 결과

{answer}

---

## 🔬 연구 관점 고찰 (NYU 2026 논문 연계)
- **제자리 파지-해제(In-place Grasp & Release) 프로토콜 반영**: 공중으로 들어올리지 않는 정적 거치 물체에 대해, [접근/접촉(Grasp) -> 해제/손 떼기(Release)]의 전이(State Transition)를 1회 반복 주기로 모델에 명시함.
- **샘플링 밀도 확장(24 -> 40프레임)**: 약 2초 간격으로 샘플링 밀도를 높여, 참가자가 손을 뗐다가 다시 잡는 찰나의 해제 구간을 VLM이 놓치지 않도록 시계열 해상도를 개선함.
"""

    report_path = "grasp_count_result.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n" + "=" * 65)
    print("                   [최종 분석 결과]                   ")
    print("=" * 65)
    print(answer)
    print("=" * 65)
    print(f"[완료] 총 소요 시간: {total_elapsed:.1f}초")
    print(f"결과가 '{report_path}' 파일로 저장되었습니다.\n")


if __name__ == "__main__":
    main()

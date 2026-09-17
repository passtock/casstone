"""사용자 제공 재활 영상(KakaoTalk_20260909_183548574.mp4) 전용 VLM 분석 스크립트 (14프레임 정규화 샘플링 버전)
- 전체 80초 영상에서 균등하게 정규화된 14개 핵심 프레임(0% ~ 100%)을 추출
- 각 프레임에 타임스탬프(초) 및 진행률(%) 오버레이 각인 및 'sampled_14_frames/' 폴더에 시각화 저장
- 14개 시퀀스 프레임을 VLM에 멀티모달 시각 입력으로 전달하여 추론 속도 대폭 향상 및 집중 분석 수행
- 논문(NYU 2026)의 3대 핵심 평가 프로토콜 수행:
  1. 고수준 활동 및 세팅 식별 (Activity Identification)
  2. 양손 분해 판별 (Motion & Grasp Decomposed Prompting)
  3. 양손 대칭성 및 협응 평가 (Bimanual Coordination & Symmetry)
- 분석 결과를 화면 출력 및 'video_analysis_result_14frames.md' 파일로 저장
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple
from PIL import Image

import cv2
import numpy as np
import torch
from vlm_rehab_eval import VLMRehabEvaluator


def print_step(step: int, total: int, title: str):
    pct = int((step / total) * 100)
    bar_len = 25
    filled = int(bar_len * (step / total))
    bar = "■" * filled + " " * (bar_len - filled)
    print(f"\n[{bar}] {pct}% | [{step}/{total}] {title}", flush=True)


def extract_14_normalized_frames(
    video_path: str,
    output_dir: str = "sampled_14_frames",
    num_frames: int = 14,
    max_width: int = 512
) -> Tuple[List[Image.Image], List[dict], float]:
    """영상 전체 구간에서 균등하게 14개 프레임을 정규화 추출하고, 타임스탬프 각인 및 저장"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상 파일을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps

    os.makedirs(output_dir, exist_ok=True)

    # 0%부터 100%까지 균일하게 14개 인덱스 계산
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames_pil = []
    metadata_list = []

    print(f" -> 총 {total_frames} 프레임 ({duration_s:.1f}초) 중 정규화된 14개 인덱스 추출:")
    print(f"    인덱스: {list(indices)}")

    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            print(f" [경고] 프레임 {idx} 읽기 실패, 건너뜁니다.")
            continue

        sec = idx / fps
        pct = (idx / (total_frames - 1)) * 100.0 if total_frames > 1 else 0.0

        # 해상도 조절 (비율 유지)
        h, w = frame.shape[:2]
        if w > max_width:
            new_w = max_width
            new_h = int(h * (new_w / w))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 시각적 오버레이 추가 (상단 어두운 띠 + 텍스트)
        overlay_text = f"Frame {i+1}/{num_frames} | T={sec:.1f}s ({pct:.0f}%)"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), (20, 20, 20), -1)
        cv2.putText(
            frame, overlay_text, (12, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2, cv2.LINE_AA
        )

        # 이미지 저장
        save_path = os.path.join(output_dir, f"frame_{i+1:02d}_t{sec:04.1f}s.jpg")
        cv2.imwrite(save_path, frame)

        # RGB 변환 후 PIL 객체로 보관
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames_pil.append(Image.fromarray(frame_rgb))

        metadata_list.append({
            "frame_idx": i + 1,
            "video_frame_idx": int(idx),
            "timestamp_s": sec,
            "progress_pct": pct,
            "save_path": save_path
        })

    cap.release()
    return frames_pil, metadata_list, duration_s


def main():
    video_path = "C:/Users/passp/OneDrive/바탕 화면/jeayong/capstone/06_VLM_재활평가_테스트/KakaoTalk_20260909_183548574.mp4"
    if not os.path.exists(video_path):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {video_path}")
        return

    start_total_time = time.time()

    print("=" * 68)
    print("   Qwen2.5-VL-3B 로컬 재활 모션 분석기 [14-Frame Normalized Sampling]")
    print("=" * 68, flush=True)

    # 1. 14프레임 정규화 추출 및 시각화 저장
    print_step(1, 5, "영상에서 14개 정규화 프레임(0%~100%) 추출 및 타임스탬프 각인")
    frames_pil, meta, duration_s = extract_14_normalized_frames(
        video_path=video_path,
        output_dir="sampled_14_frames",
        num_frames=14,
        max_width=512
    )
    print(f" -> 14개 프레임 추출 완료! ('sampled_14_frames/' 폴더에 프리뷰 저장됨)", flush=True)

    # 2. VLM 모델 GPU 로드
    print_step(2, 5, "VLM 모델(Qwen2.5-VL-3B) 로컬 GPU 로드 중...")
    t0 = time.time()
    evaluator = VLMRehabEvaluator(
        model_name="Qwen/Qwen2.5-VL-3B-Instruct",
        quantization="4bit"  # RTX 3080/3060 최적화 4-bit 양자화
    )
    print(f" -> 모델 로드 완료 (소요 시간: {time.time() - t0:.1f}초)", flush=True)

    results = {}

    # 3. 과제 1: 14프레임 기반 장면 및 재활 활동 식별 (Activity Identification)
    print_step(3, 5, "과제 1: 14프레임 시퀀스 기반 장면 및 재활 활동 식별 추론")
    t0 = time.time()
    prompt_activity = (
        "These 14 chronological frames represent an entire upper-limb rehabilitation session "
        "sampled uniformly from start (0%) to end (100%). "
        "Watch and analyze the sequence carefully. Describe in detail: "
        "1) What objects are placed on the table and what the participant is doing with both hands throughout the sequence. "
        "2) Is the participant performing a bimanual (two-handed) grasping or stabilization task on the two round objects? "
        "Explain clearly."
    )
    results["activity"] = evaluator.ask(frames_pil, prompt_activity, max_new_tokens=256)
    print(f" -> 추론 완료 ({time.time() - t0:.1f}초)", flush=True)
    print(f" [활동 분석 결과]:\n{results['activity']}\n", flush=True)

    # 4. 과제 2: 14프레임 기반 양손 Motion & Grasp 이진 분해 판별
    print_step(4, 5, "과제 2: 14프레임 기반 양손 Motion & Grasp 이진 분해 판별")
    t0 = time.time()

    def eval_motion_and_grasp_14f(hand_name: str) -> dict:
        q_motion = (
            f"These 14 chronological frames show the movement progression from start to end. "
            f"Focus strictly on the subject's {hand_name} hand across all 14 frames. "
            f"Is the {hand_name} hand moving significantly? Answer 'Yes' or 'No' directly."
        )
        ans_motion = evaluator.ask(frames_pil, q_motion, max_new_tokens=16)

        q_grasp = (
            f"These 14 chronological frames show the movement progression from start to end. "
            f"Focus strictly on the subject's {hand_name} hand across all 14 frames. "
            f"Is the {hand_name} hand actively grasping or holding an object? Answer 'Yes' or 'No' directly."
        )
        ans_grasp = evaluator.ask(frames_pil, q_grasp, max_new_tokens=16)

        has_motion = "yes" in ans_motion.lower()
        has_grasp = "yes" in ans_grasp.lower()

        if not has_motion and not has_grasp:
            primitive = "Idle (대기/휴지)"
        elif not has_motion and has_grasp:
            primitive = "Stabilize (물체 유지/고정)"
        elif has_motion and has_grasp:
            primitive = "Transport (물체 쥐고 이동)"
        else:
            primitive = "Reach or Reposition (접촉 전 이동 또는 원위치 복귀)"

        return {
            "target_hand": hand_name,
            "motion_detected": has_motion,
            "motion_raw": ans_motion,
            "grasp_detected": has_grasp,
            "grasp_raw": ans_grasp,
            "estimated_primitive": primitive
        }

    print(" -> 오른손(Right Hand) 분석 중...", flush=True)
    mg_right = eval_motion_and_grasp_14f("right")
    print(f"    - 움직임(Motion): {'O (Yes)' if mg_right['motion_detected'] else 'X (No)'} ({mg_right['motion_raw']})")
    print(f"    - 물체파지(Grasp): {'O (Yes)' if mg_right['grasp_detected'] else 'X (No)'} ({mg_right['grasp_raw']})")
    print(f"    - 추정 프리미티브: {mg_right['estimated_primitive']}")

    print(" -> 왼손(Left Hand) 분석 중...", flush=True)
    mg_left = eval_motion_and_grasp_14f("left")
    print(f"    - 움직임(Motion): {'O (Yes)' if mg_left['motion_detected'] else 'X (No)'} ({mg_left['motion_raw']})")
    print(f"    - 물체파지(Grasp): {'O (Yes)' if mg_left['grasp_detected'] else 'X (No)'} ({mg_left['grasp_raw']})")
    print(f"    - 추정 프리미티브: {mg_left['estimated_primitive']}")

    results["mg_right"] = mg_right
    results["mg_left"] = mg_left
    print(f" -> 분해 판별 완료 ({time.time() - t0:.1f}초)", flush=True)

    # 5. 과제 3: 14프레임 기반 양손 대칭성 및 움직임 협응 평가
    print_step(5, 5, "과제 3: 14프레임 기반 양손 대칭성 및 움직임 협응 평가")
    t0 = time.time()
    prompt_symmetry = (
        "Across these 14 chronological frames covering the entire rehabilitation movement, "
        "observe the movement coordination between the left hand and the right hand. "
        "Are both hands placed and moved symmetrically over the two spherical objects? "
        "Does either hand show hesitation, tremor, or asymmetry?"
    )
    results["symmetry"] = evaluator.ask(frames_pil, prompt_symmetry, max_new_tokens=256)
    print(f" -> 추론 완료 ({time.time() - t0:.1f}초)", flush=True)
    print(f" [대칭성 분석 결과]:\n{results['symmetry']}\n", flush=True)

    total_elapsed = time.time() - start_total_time

    # 프레임 테이블 마크다운 생성
    table_rows = []
    for m in meta:
        table_rows.append(f"| #{m['frame_idx']} | {m['timestamp_s']:.1f}s | {m['progress_pct']:.0f}% | `{m['save_path']}` |")
    table_md = "\n".join(table_rows)

    # 결과 마크다운 리포트 생성 및 저장
    report_md = f"""# VLM 재활 영상 분석 결과 보고서 (14-Frame Normalized Sampling)

- **대상 영상**: `{video_path}` (길이: {duration_s:.1f}초)
- **샘플링 기법**: 전체 영상 균등 14프레임 정규화 추출 (0% ~ 100%)
- **분석 모델**: `Qwen/Qwen2.5-VL-3B-Instruct` (로컬 GPU 가속 4-bit 구동)
- **총 소요 시간**: {total_elapsed:.1f}초
- **분석 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 0. 정규화 추출된 14개 프레임 정보
| 프레임 번호 | 타임스탬프 | 영상 진행률 | 파일 저장 경로 |
|:---:|:---:|:---:|:---|
{table_md}

> 프레임 미리보기 이미지는 `sampled_14_frames/` 폴더에 타임스탬프 오버레이와 함께 저장되어 있습니다.

---

## 1. 전체 활동 및 세팅 식별 (Activity & Scene Identification)
{results['activity']}

---

## 2. 기능적 원초 동작 분해 판별 (Motion & Grasp Decomposition - NYU 2026 논문 방식)

### [오른손 (Right Hand)]
- **유의미한 움직임 감지 (Motion)**: {'O (Yes)' if mg_right['motion_detected'] else 'X (No)'} (응답 원문: `{mg_right['motion_raw']}`)
- **물체 파지/접촉 감지 (Grasp)**: {'O (Yes)' if mg_right['grasp_detected'] else 'X (No)'} (응답 원문: `{mg_right['grasp_raw']}`)
- **도출된 운동 프리미티브**: **{mg_right['estimated_primitive']}**

### [왼손 (Left Hand)]
- **유의미한 움직임 감지 (Motion)**: {'O (Yes)' if mg_left['motion_detected'] else 'X (No)'} (응답 원문: `{mg_left['motion_raw']}`)
- **물체 파지/접촉 감지 (Grasp)**: {'O (Yes)' if mg_left['grasp_detected'] else 'X (No)'} (응답 원문: `{mg_left['grasp_raw']}`)
- **도출된 운동 프리미티브**: **{mg_left['estimated_primitive']}**

---

## 3. 양손 대칭성 및 운동 협응 분석 (Bimanual Coordination & Symmetry)
{results['symmetry']}

---

## 4. 전체 영상 직접 처리 대비 14프레임 정규화의 장점 및 고찰
1. **추론 속도 및 계산 효율**:
   - 80초 고해상도 영상을 매 초 디코딩하는 대신, 전체 진행 단계를 대표하는 14개의 정규화 키프레임만 처리하므로 토큰 수와 GPU 연산량이 대폭 절감되어 훨씬 빠르게 응답을 얻을 수 있습니다.
2. **시간적 대표성 보장 (Normalized Progression)**:
   - 0% (시작 대기), 20~50% (접근 및 파지), 70~100% (유지 및 대칭적 동작) 등 모션의 핵심 전이 국면(Transition phase)을 균등하게 커버합니다.
3. **타임스탬프 시각적 각인 효과**:
   - 프레임마다 시간(T=X.Xs)과 진행률(%)이 표기되어 있어 VLM이 시간 경과에 따른 움직임 변화를 더 정확하게 추적할 수 있습니다.
"""

    report_path = "video_analysis_result_14frames.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("=" * 68)
    print(f"[분석 완료] 총 소요 시간: {total_elapsed:.1f}초")
    print(f"상세 결과 보고서가 '{report_path}' 파일로 저장되었습니다.")
    print("=" * 68, flush=True)


if __name__ == "__main__":
    main()

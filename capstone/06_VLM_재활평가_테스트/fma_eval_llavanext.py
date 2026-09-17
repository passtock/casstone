"""[VLM FMA 평가 코드 1/2] LLaVA-NeXT-Video-7B 기반 원통형 파지(Cylindrical Grasp) FMA 점수 측정
- 모델: llava-hf/LLaVA-NeXT-Video-7B-hf (4-bit 양자화 적용)
- 대상 과제: Task 3 - 원통형 파지 (Cylinder Grasp, 직경 5cm 원통 물체)
- 평가 프로토콜: FMA-UE Grasp C (Cylindrical Grasp) 임상 기준 및 3단계(Formation-Hold-Release) 분해 채점
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import torch
from PIL import Image

# 콘솔 UTF-8 출력 보장
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


DEFAULT_VIDEO_PATH = (
    r"C:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\호진파일\outputs\데이터_저장"
    r"\20260916_비장애인_test0916_62세_남\split\Task3_원통형파지Cylinder\Trial_1"
    r"\Session_20260916_173302_921069_4e1430f4_Task3_원통형파지Cylinder_Trial_1_original.avi"
)


def sample_and_annotate_frames(
    video_path: str,
    num_frames: int = 16,
    max_width: int = 384,
    save_preview_dir: str = "preview_frames_llavanext"
) -> Tuple[np.ndarray, List[dict], float]:
    """비디오에서 균등하게 프레임을 추출하고 타임스탬프 각인 후 (N, H, W, C) numpy 배열 반환"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps

    os.makedirs(save_preview_dir, exist_ok=True)
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames_rgb_list = []
    meta = []

    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        sec = idx / fps
        pct = (idx / (total_frames - 1)) * 100.0 if total_frames > 1 else 0.0

        # 해상도 비율 유지 축소
        h, w = frame.shape[:2]
        if w > max_width:
            new_w = max_width
            new_h = int(h * (new_w / w))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 타임스탬프 및 프레임 번호 시각화 오버레이
        overlay_text = f"F{i+1:02d} | T={sec:.1f}s ({pct:.0f}%)"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 28), (25, 25, 25), -1)
        cv2.putText(
            frame, overlay_text, (8, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 220), 2, cv2.LINE_AA
        )

        save_path = os.path.join(save_preview_dir, f"frame_{i+1:02d}.jpg")
        cv2.imwrite(save_path, frame)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames_rgb_list.append(frame_rgb)
        meta.append({
            "idx": i + 1,
            "sec": sec,
            "pct": pct,
            "path": save_path
        })

    cap.release()
    return np.array(frames_rgb_list), meta, duration_s


def build_cylindrical_fma_prompt(duration_s: float, num_frames: int) -> str:
    """원통형 파지(Task 3) 전용 정밀 FMA-UE 임상 평가 프롬프트 생성"""
    prompt = f"""You are a senior neurorehabilitation clinician and clinical biomechanics expert specializing in the Fugl-Meyer Assessment for Upper Extremity (FMA-UE).
Observe these {num_frames} sequential video frames ({duration_s:.1f} seconds total) of a subject performing 'Task 3: Cylindrical Grasp (원통형 파지)' using a cylindrical object (diameter 5.0 cm, height 10.0 cm).

[Task Context & Standard]:
- Target Task: Oppose the thumb and all fingers around the 5.0 cm diameter cylinder, hold the grasp stably through an observable pause, and actively release the fingers back toward the starting posture.
- Official FMA-UE Part VII (Hand: Grasp C - Cylindrical Grasp) Scoring Criteria:
  * Score 0 (Cannot be performed): Subject cannot grasp the cylinder at all; lacks finger flexion or thumb opposition; drops the object or fails to establish contacts.
  * Score 1 (Partially performed / Weak hold): Subject successfully forms the grasp around the cylinder, but the grasp is weak, unstable, or incomplete (e.g., immediate release without pause, or inability to actively open fingers to release).
  * Score 2 (Normal / Fully performed): Subject establishes complete cylindrical power grasp (thumb and fingers opposing and wrapping around the cylinder), holds it stably during an observable pause, and actively re-opens fingers cleanly to release.

[Clinical Evaluation Checklist]:
1. Formation (형성): Did the subject position the thumb and fingers around the cylinder and make solid contact?
2. Hold (유지): Was the achieved cylindrical grasp maintained stably through an observable pause before release?
3. Release (해제): Did the subject actively open the fingers (finger extension) to release the object, rather than just pulling the arm away?

[Required Output Format]:
Please evaluate the Right Hand and Left Hand thoroughly and output your assessment in the following structured format:

---
### 1. Motion & Grasp Kinematic Analysis
- **Right Hand**:
  - Reach & Approach: [Normal / Hesitant / Tremor / Compensatory]
  - Finger Flexion & Thumb Opposition: [Full / Incomplete / None]
  - Cylinder Enclosure: [Well-aligned / Loose / Slipping]
- **Left Hand**:
  - Reach & Approach: [Normal / Hesitant / Tremor / Compensatory]
  - Finger Flexion & Thumb Opposition: [Full / Incomplete / None]
  - Cylinder Enclosure: [Well-aligned / Loose / Slipping]

### 2. Stage-by-Stage Clinical Rubric
- **Right Hand**:
  - Formation: [Complete / Incomplete / Unreadable] - (Reasoning)
  - Hold: [Complete / Incomplete / Unreadable] - (Reasoning)
  - Release: [Complete / Incomplete / Unreadable] - (Reasoning)
- **Left Hand**:
  - Formation: [Complete / Incomplete / Unreadable] - (Reasoning)
  - Hold: [Complete / Incomplete / Unreadable] - (Reasoning)
  - Release: [Complete / Incomplete / Unreadable] - (Reasoning)

### 3. FMA-UE Grasp C (Cylindrical Grasp) Estimated Score
- **Right Hand FMA Score**: [0 or 1 or 2] / 2
- **Right Hand Clinical Rationale**: (Provide clear diagnostic evidence)
- **Left Hand FMA Score**: [0 or 1 or 2] / 2
- **Left Hand Clinical Rationale**: (Provide clear diagnostic evidence)

### 4. Overall Clinical Rehabilitation Summary
(2-3 sentences summarizing motor control, bimanual symmetry, and functional capacity.)
---
"""
    return prompt


def run_llavanext_evaluation(video_path: str, output_md_path: str = "fma_result_llavanext_cylindrical.md"):
    print("=" * 72)
    print(" [1/2] LLaVA-NeXT-Video-7B 모델 기반 원통형 파지(Cylinder) FMA 평가")
    print("=" * 72)
    print(f"[*] 대상 영상: {video_path}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"영상 파일이 존재하지 않습니다: {video_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] 연산 디바이스: {device}")

    # 1. 프레임 추출
    t0 = time.time()
    num_frames = 16
    print(f"[*] 비디오 프레임 추출 중 ({num_frames}개 균등 정규화 샘플링)...")
    video_arr, meta, duration_s = sample_and_annotate_frames(
        video_path=video_path,
        num_frames=num_frames,
        max_width=384,
        save_preview_dir="preview_frames_llavanext"
    )
    print(f"[+] 프레임 추출 완료! 영상 길이: {duration_s:.2f}초 | 텐서 크기: {video_arr.shape}")

    # 2. 모델 로드
    model_id = "llava-hf/LLaVA-NeXT-Video-7B-hf"
    print(f"\n[*] 모델 로딩 중: {model_id} (4-bit 양자화 적용)...")
    t_load = time.time()

    from transformers import LlavaNextVideoForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

    load_kwargs = {}
    if device == "cuda":
        compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True
        )
        load_kwargs["device_map"] = "cuda:0"
    else:
        load_kwargs["torch_dtype"] = torch.float32

    model = LlavaNextVideoForConditionalGeneration.from_pretrained(model_id, **load_kwargs)
    processor = AutoProcessor.from_pretrained(model_id)
    print(f"[+] 모델 로드 성공! (소요 시간: {time.time() - t_load:.1f}초)")

    # 3. 프롬프트 구성 및 입력 준비
    prompt = build_cylindrical_fma_prompt(duration_s, num_frames)

    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "video"},
            ],
        },
    ]
    prompt_text = processor.apply_chat_template(conversation, add_generation_prompt=True)

    print("\n[*] VLM 입력 텐서 인코딩 및 추론 시작...")
    inputs = processor(text=prompt_text, videos=video_arr, return_tensors="pt").to(model.device)

    t_infer = time.time()
    with torch.no_grad():
        out_ids = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
            temperature=None,
            top_p=None
        )
        in_len = inputs.input_ids.shape[1]
        response_text = processor.decode(out_ids[0][in_len:], skip_special_tokens=True).strip()

    infer_elapsed = time.time() - t_infer
    print(f"[+] 추론 완료! (소요 시간: {infer_elapsed:.1f}초)")

    # 4. 결과 출력 및 마크다운 파일 저장
    print("\n" + "=" * 72)
    print("                      [ FMA 평가 결과 보고서 ]")
    print("=" * 72)
    print(response_text)
    print("=" * 72)

    total_time = time.time() - t0

    report_content = f"""# FMA-UE Cylindrical Grasp Assessment Report (LLaVA-NeXT-Video-7B)

- **평가 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **분석 모델**: `{model_id}` (4-bit NF4 Quantization)
- **평가 대상 영상**: `{video_path}`
- **영상 길이**: {duration_s:.2f}초 ({len(meta)} 프레임 추출 분석)
- **총 소요 시간**: {total_time:.1f}초 (추론: {infer_elapsed:.1f}초)

---

## 📋 VLM 임상 평가 전문

{response_text}

---

## 🖼️ 추출 분석 프레임 목록
| 프레임 번호 | 타임스탬프 | 진행률 | 저장 경로 |
|:---:|:---:|:---:|:---|
"""
    for m in meta:
        report_content += f"| Frame {m['idx']:02d} | {m['sec']:.2f}s | {m['pct']:.1f}% | `{m['path']}` |\n"

    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[저장 완료] 마크다운 보고서가 저장되었습니다: {output_md_path}")
    return response_text


def main():
    parser = argparse.ArgumentParser(description="LLaVA-NeXT-Video-7B Cylindrical Grasp FMA Evaluator")
    parser.add_argument("--video", type=str, default=DEFAULT_VIDEO_PATH, help="평가할 비디오 파일 경로 (.avi, .mp4)")
    parser.add_argument("--output", type=str, default="fma_result_llavanext_cylindrical.md", help="출력 마크다운 리포트 경로")
    args = parser.parse_args()

    run_llavanext_evaluation(args.video, args.output)


if __name__ == "__main__":
    main()

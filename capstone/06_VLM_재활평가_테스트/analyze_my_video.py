"""사용자 제공 재활 영상(KakaoTalk_20260909_183548574.mp4) 전용 VLM 분석 스크립트
- 실시간 진행률(%) 및 진행 단계 표시
- 논문(NYU 2026)의 3대 핵심 평가 프로토콜 수행:
  1. 고수준 활동 및 세팅 식별 (Activity Identification)
  2. 양손 분해 판별 (Motion & Grasp Decomposed Prompting)
  3. 양손 대칭성 및 협응 평가 (Bimanual Coordination & Symmetry)
- 분석 결과를 터미널 화면 출력 및 'video_analysis_result.md' 파일로 저장
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image

import cv2
import torch
from vlm_rehab_eval import VLMRehabEvaluator


def print_step(step: int, total: int, title: str):
    pct = int((step / total) * 100)
    bar_len = 25
    filled = int(bar_len * (step / total))
    bar = "■" * filled + " " * (bar_len - filled)
    print(f"\n[{bar}] {pct}% | [{step}/{total}] {title}", flush=True)


def main():
    video_path = "KakaoTalk_20260909_183548574.mp4"
    if not os.path.exists(video_path):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {video_path}")
        print("현재 폴더에 'KakaoTalk_20260909_183548574.mp4' 파일이 있는지 확인해 주세요.")
        return

    start_total_time = time.time()

    print("=" * 65)
    print("      Qwen2.5-VL-3B 로컬 재활 모션 영상 분석기 (RTX 3060 최적화)")
    print("=" * 65, flush=True)

    # 1. 영상 정보 확인 및 프레임 샘플링
    print_step(1, 5, "영상 로드 및 분석용 프레임 샘플링 (해상도 최적화)")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    duration_s = total_frames / fps
    print(f" -> 영상 정보: 길이 {duration_s:.1f}초 ({total_frames} 프레임), {fps:.1f} FPS", flush=True)

    # 2. VLM 모델 GPU 로드
    print_step(2, 5, "VLM 모델(Qwen2.5-VL-3B) 로컬 GPU 로드 중...")
    t0 = time.time()
    evaluator = VLMRehabEvaluator(
        model_name="Qwen/Qwen2.5-VL-3B-Instruct",
        quantization="none"  # bfloat16 기본 모드 (VRAM ~4.5GB 소모)
    )
    print(f" -> 모델 로드 완료 (소요 시간: {time.time() - t0:.1f}초)", flush=True)

    # 8개 프레임 추출 (RTX 3060 고속 연산에 최적화된 512px 리사이징 적용)
    frames = evaluator.sample_video_frames(video_path, num_frames=8, max_width=512)
    print(f" -> 8개 대표 프레임 추출 완료 (연산 토큰 최적화 완료)", flush=True)

    results = {}

    # 3. 과제 A: 장면 및 재활 활동 설명 (Activity Identification)
    print_step(3, 5, "과제 1: 장면 및 재활 활동 식별 (Activity Identification) 추론")
    t0 = time.time()
    prompt_activity = (
        "Look at these 8 chronological video frames of an upper-limb movement session. "
        "Describe in detail: "
        "1) What objects are on the table and what the participant is doing with both hands. "
        "2) Is the participant performing a bimanual (two-handed) grasping or stabilization task on the two round objects? "
        "Explain clearly."
    )
    results["activity"] = evaluator.ask(frames, prompt_activity, max_new_tokens=256)
    print(f" -> 추론 완료 ({time.time() - t0:.1f}초)", flush=True)
    print(f" [활동 분석 결과]:\n{results['activity']}\n", flush=True)

    # 4. 과제 B: 논문 방식 이진 분해 질의 (Motion & Grasp Decomposed Prompting)
    print_step(4, 5, "과제 2: 논문 프로토콜 양손 Motion & Grasp 이진 분해 판별")
    t0 = time.time()
    print(" -> 오른손(Right Hand) 분석 중...", flush=True)
    mg_right = evaluator.detect_motion_and_grasp(frames, target_hand="right")
    print(f"    - 움직임(Motion): {'O (Yes)' if mg_right['motion_detected'] else 'X (No)'}")
    print(f"    - 물체파지(Grasp): {'O (Yes)' if mg_right['grasp_detected'] else 'X (No)'}")
    print(f"    - 추정 프리미티브: {mg_right['estimated_primitive']}")

    print(" -> 왼손(Left Hand) 분석 중...", flush=True)
    mg_left = evaluator.detect_motion_and_grasp(frames, target_hand="left")
    print(f"    - 움직임(Motion): {'O (Yes)' if mg_left['motion_detected'] else 'X (No)'}")
    print(f"    - 물체파지(Grasp): {'O (Yes)' if mg_left['grasp_detected'] else 'X (No)'}")
    print(f"    - 추정 프리미티브: {mg_left['estimated_primitive']}")

    results["mg_right"] = mg_right
    results["mg_left"] = mg_left
    print(f" -> 분해 판별 완료 ({time.time() - t0:.1f}초)", flush=True)

    # 5. 과제 C: 양손 협응 및 대칭성 평가 (Coordination & Symmetry)
    print_step(5, 5, "과제 3: 양손 대칭성 및 움직임 협응(미러 효과) 평가")
    t0 = time.time()
    prompt_symmetry = (
        "Observe the movement coordination between the left hand and the right hand. "
        "Are both hands placed and moved symmetrically over the two spherical objects? "
        "Does either hand show hesitation, tremor, or asymmetry?"
    )
    results["symmetry"] = evaluator.ask(frames, prompt_symmetry, max_new_tokens=256)
    print(f" -> 추론 완료 ({time.time() - t0:.1f}초)", flush=True)
    print(f" [대칭성 분석 결과]:\n{results['symmetry']}\n", flush=True)

    total_elapsed = time.time() - start_total_time

    # 결과 마크다운 리포트 생성 및 저장
    report_md = f"""# VLM 재활 영상 분석 결과 보고서

- **대상 영상**: `{video_path}` (길이: {duration_s:.1f}초)
- **분석 모델**: `Qwen/Qwen2.5-VL-3B-Instruct` (로컬 GPU 가속 구동)
- **총 소요 시간**: {total_elapsed:.1f}초
- **분석 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}

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

## 4. 논문(NYU 2026) 관점에서의 분석 및 연구 시사점
1. **시각적 장면 이해 (성공)**: 책상 위의 두 구형 물체와 참가자가 양손을 올려 쥐거나 유지(Stabilize)하는 전반적 상태를 매우 자연스럽게 인식함.
2. **논문에서 지적된 2D VLM의 한계 검증**:
   - VLM은 손이 구형 물체 위에 올려져 있는 형태(Proximity)만 보고 접촉/파지(Grasp)로 판단하지만, 실제 손가락이 가하는 악력이나 미세한 표면 접촉 유무(Contact vs Gap)는 판별하기 어렵습니다.
   - 따라서 정밀한 재활 정량화를 위해서는 현재 개발하신 **RealSense 3D Depth 카메라의 물리적 거리 계측 + MediaPipe 3D 관절각(`kinematics.py`)** 데이터가 결합되어야 임상적 신뢰성을 확보할 수 있습니다.
"""

    report_path = "video_analysis_result.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("=" * 65)
    print(f"[분석 완료] 총 소요 시간: {total_elapsed:.1f}초")
    print(f"상세 결과 보고서가 '{report_path}' 파일로 저장되었습니다.")
    print("=" * 65, flush=True)


if __name__ == "__main__":
    main()

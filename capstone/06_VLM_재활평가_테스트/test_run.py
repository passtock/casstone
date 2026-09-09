"""VLM 재활 평가 모델 자체 동작 테스트 스크립트
- 테스트용 샘플 손동작 이미지 1장을 자동 생성하고,
- Qwen2.5-VL 모델이 정상적으로 로드 및 추론되는지 즉시 검증합니다.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

from vlm_rehab_eval import VLMRehabEvaluator


def create_sample_test_image(output_path: str = "sample_test_hand.jpg"):
    """테스트용 간단한 합성 이미지 생성 (손 윤곽 + 물체)"""
    img = np.ones((480, 640, 3), dtype=np.uint8) * 240  # 밝은 회색 배경

    # 테이블 그리기
    cv2.rectangle(img, (50, 320), (590, 450), (180, 160, 140), -1)

    # 원통형 물체(두루마리 휴지/컵 유사) 그리기
    cv2.rectangle(img, (280, 240), (360, 340), (220, 220, 255), -1)
    cv2.circle(img, (320, 240), 40, (200, 200, 240), -1)

    # 손과 손가락 그리기 (물체를 향해 뻗는 형태)
    # 손목/손바닥
    cv2.ellipse(img, (180, 290), (50, 35), 20, 0, 360, (210, 185, 170), -1)
    # 손가락들
    cv2.line(img, (210, 275), (275, 260), (210, 185, 170), 16)  # 검지
    cv2.line(img, (210, 290), (270, 285), (210, 185, 170), 16)  # 중지
    cv2.line(img, (190, 265), (240, 240), (210, 185, 170), 14)  # 엄지

    # 텍스트 안내
    cv2.putText(img, "Synthetic Rehabilitation Test Scene", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2)

    cv2.imwrite(output_path, img)
    print(f"[+] 샘플 테스트 이미지 생성 완료: {output_path}")
    return output_path


def main():
    print("==========================================================")
    print("  Qwen2.5-VL 뇌졸중 재활 모션 평가기 로컬 구동 테스트  ")
    print("==========================================================")

    sample_img_path = create_sample_test_image()

    # RTX 3060 환경에 가장 알맞은 Qwen2.5-VL-3B-Instruct 모델 로드
    # (VRAM이 6GB 수준인 경우 quantization='4bit'로 변경하면 더욱 가볍게 실행됩니다)
    evaluator = VLMRehabEvaluator(
        model_name="Qwen/Qwen2.5-VL-3B-Instruct",
        quantization="none"  # "4bit" 설정 가능
    )

    print("\n[테스트 1] 손 동작 및 파지(Grasp) 분석 질의 중...")
    prompt = (
        "Look at the image carefully. Describe what the hand is doing. "
        "Is the hand reaching towards the object, or is it already grasping the object? "
        "Explain briefly."
    )

    img = Image.open(sample_img_path).convert("RGB")
    answer = evaluator.ask([img], prompt, max_new_tokens=100)

    print("\n==================== [모델 응답 결과] ====================")
    print(answer)
    print("==========================================================")
    print("[성공] VLM 모델이 로컬 GPU에서 성공적으로 실행되었습니다!")


if __name__ == "__main__":
    main()

"""[코드 4/8] Qwen2.5-VL-32B-Instruct 대형 모델 - 14프레임 정규화 추출 평가 실행 스크립트
※ 14프레임 정규화 추출로 입력 토큰을 최소화하여 32B 모델의 VRAM 부담을 경감합니다.
"""

import os
from multi_vlm_evaluator import UnifiedVLMRehabRunner, save_markdown_report


def main():
    video_path = "C:/Users/passp/OneDrive/바탕 화면/jeayong/capstone/06_VLM_재활평가_테스트/KakaoTalk_20260909_183548574.mp4"
    if not os.path.exists(video_path):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {video_path}")
        return

    print("=" * 68)
    print("   [4/8] Qwen2.5-VL-32B-Instruct : 14프레임 정규화(14-Frame) 평가")
    print("   (토큰 절감 모드로 32B 대형 모델 추론 속도 최적화)")
    print("=" * 68)

    runner = UnifiedVLMRehabRunner(model_type="qwen25_32b", quantization="4bit")
    res = runner.run_rehab_evaluation(video_path, mode="14frames")

    output_report = "result_qwen25_32b_14frames.md"
    save_markdown_report(res, output_report)
    print(f"[완료] 총 소요 시간: {res['total_elapsed']:.1f}초")


if __name__ == "__main__":
    main()

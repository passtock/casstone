"""[코드 3/8] Qwen2.5-VL-32B-Instruct 대형 모델 - 전체 영상 직접 투입 평가 실행 스크립트
※ 16GB VRAM 초과 시 자동으로 CPU 메모리를 공유하여 구동됩니다.
"""

import os
from multi_vlm_evaluator import UnifiedVLMRehabRunner, save_markdown_report


def main():
    video_path = "C:/Users/passp/OneDrive/바탕 화면/jeayong/capstone/06_VLM_재활평가_테스트/KakaoTalk_20260909_183548574.mp4"
    if not os.path.exists(video_path):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {video_path}")
        return

    print("=" * 68)
    print("   [3/8] Qwen2.5-VL-32B-Instruct : 전체 동영상(Full Video) 평가")
    print("   (주의: 32B 대형 모델로 16GB VRAM 초과 시 CPU 오프로딩 가동)")
    print("=" * 68)

    runner = UnifiedVLMRehabRunner(model_type="qwen25_32b", quantization="4bit")
    res = runner.run_rehab_evaluation(video_path, mode="full")

    output_report = "result_qwen25_32b_full.md"
    save_markdown_report(res, output_report)
    print(f"[완료] 총 소요 시간: {res['total_elapsed']:.1f}초")


if __name__ == "__main__":
    main()

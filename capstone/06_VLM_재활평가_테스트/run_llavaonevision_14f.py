"""[코드 8/8] LLaVA-OneVision-7B 모델 - 14프레임 정규화 추출 평가 실행 스크립트"""

import os
from multi_vlm_evaluator import UnifiedVLMRehabRunner, save_markdown_report


def main():
    video_path = "C:/Users/passp/OneDrive/바탕 화면/jeayong/capstone/06_VLM_재활평가_테스트/KakaoTalk_20260909_183548574.mp4"
    if not os.path.exists(video_path):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {video_path}")
        return

    print("=" * 68)
    print("   [8/8] LLaVA-OneVision-7B : 14프레임 정규화(14-Frame) 평가")
    print("=" * 68)

    runner = UnifiedVLMRehabRunner(model_type="llavaonevision", quantization="4bit")
    res = runner.run_rehab_evaluation(video_path, mode="14frames")

    output_report = "result_llavaonevision_14frames.md"
    save_markdown_report(res, output_report)
    print(f"[완료] 총 소요 시간: {res['total_elapsed']:.1f}초")


if __name__ == "__main__":
    main()

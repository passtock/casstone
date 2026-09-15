"""통합 벤치마크 러너 (Unified Benchmark Runner)
- 4개 모델 x 2개 모드(14frames / full) = 총 8개 조합을 자유롭게 선택 실행
- 실행 예시:
    python benchmark_runner.py --list
    python benchmark_runner.py --model qwen3_8b --mode 14frames
    python benchmark_runner.py --model llavanext --mode full
    python benchmark_runner.py --all-14f       (14프레임 모드로 4개 모델 일괄 비교)
"""

import os
import sys
import argparse
from multi_vlm_evaluator import UnifiedVLMRehabRunner, save_markdown_report

MODELS = {
    "1": ("qwen3_8b", "Qwen3-VL-8B-Instruct"),
    "2": ("qwen25_32b", "Qwen2.5-VL-32B-Instruct"),
    "3": ("llavanext", "LLaVA-NeXT-Video-7B"),
    "4": ("llavaonevision", "LLaVA-OneVision-7B"),
}


def main():
    parser = argparse.ArgumentParser(description="VLM 재활 평가 8대 벤치마크 통합 러너")
    parser.add_argument("--model", type=str, choices=["qwen3_8b", "qwen25_32b", "llavanext", "llavaonevision"], help="실행할 모델")
    parser.add_argument("--mode", type=str, choices=["14frames", "full"], default="14frames", help="영상 분석 모드 (14frames 또는 full)")
    parser.add_argument("--video", type=str, default="KakaoTalk_20260909_183548574.mp4", help="대상 영상 경로")
    parser.add_argument("--quant", type=str, default="4bit", choices=["4bit", "none"], help="양자화 설정")
    parser.add_argument("--list", action="store_true", help="8개 스크립트 목록 보기")
    args = parser.parse_args()

    if args.list:
        print("\n====================================================================")
        print("                 VLM 재활 평가 8대 실행 스크립트 목록")
        print("====================================================================")
        print(" [Qwen3-VL-8B-Instruct]")
        print("   1. run_qwen3_8b_full.py          : 전체 영상 직접 투입")
        print("   2. run_qwen3_8b_14f.py           : 14프레임 정규화 추출")
        print("\n [Qwen2.5-VL-32B-Instruct]")
        print("   3. run_qwen25_32b_full.py        : 전체 영상 직접 투입")
        print("   4. run_qwen25_32b_14f.py         : 14프레임 정규화 추출")
        print("\n [LLaVA-NeXT-Video-7B]")
        print("   5. run_llavanext_full.py         : 전체 영상 직접 투입")
        print("   6. run_llavanext_14f.py          : 14프레임 정규화 추출")
        print("\n [LLaVA-OneVision-7B]")
        print("   7. run_llavaonevision_full.py    : 전체 영상 직접 투입")
        print("   8. run_llavaonevision_14f.py     : 14프레임 정규화 추출")
        print("====================================================================\n")
        return

    if not args.model:
        print("[!] --model 인자를 지정해 주세요. 목록 확인: python benchmark_runner.py --list")
        return

    if not os.path.exists(args.video):
        print(f"[오류] 영상 파일을 찾을 수 없습니다: {args.video}")
        return

    runner = UnifiedVLMRehabRunner(model_type=args.model, quantization=args.quant)
    res = runner.run_rehab_evaluation(args.video, mode=args.mode)
    out_file = f"result_{args.model}_{args.mode}.md"
    save_markdown_report(res, out_file)
    print(f"\n[완료] {args.model} ({args.mode}) 평가가 완료되었습니다. 리포트: {out_file}")


if __name__ == "__main__":
    main()

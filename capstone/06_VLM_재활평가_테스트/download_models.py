"""VLM 모델 가중치 로컬 다운로더 스크립트
- 지원 모델:
  1. lmms-lab/LLaVA-NeXT-Video-7B (~13.2 GB)
  2. lmms-lab/llava-onevision-qwen2-7b-ov (~15.0 GB)
  3. Qwen/Qwen3-VL-8B-Instruct (~16.3 GB)
  4. Qwen/Qwen3-VL-30B-A3B-Instruct (~57.9 GB)
  5. Qwen/Qwen2.5-VL-32B-Instruct (~63.6 GB)
- 기능:
  - huggingface_hub snapshot_download 활용 (이어받기/캐시 자동 지원)
  - 개별 또는 전체 다운로드 선택 지원
  - 하드웨어(VRAM 16GB) 적합도 안내
"""

import os
import sys
import argparse
import time
from huggingface_hub import snapshot_download

SUPPORTED_MODELS = {
    "llava-next": {
        "repo_id": "lmms-lab/LLaVA-NeXT-Video-7B",
        "name": "LLaVA-NeXT-Video-7B",
        "approx_gb": 13.2,
        "vram_rec": "8GB 이상 (4-bit 시 ~5.5GB, 16GB VRAM 환경 완벽 호환)",
        "compatible_16gb": True
    },
    "llava-onevision": {
        "repo_id": "lmms-lab/llava-onevision-qwen2-7b-ov",
        "name": "LLaVA-OneVision-7B",
        "approx_gb": 15.0,
        "vram_rec": "10GB 이상 (4-bit 시 ~6GB, 16GB VRAM 환경 완벽 호환)",
        "compatible_16gb": True
    },
    "qwen3-8b": {
        "repo_id": "Qwen/Qwen3-VL-8B-Instruct",
        "name": "Qwen3-VL-8B-Instruct",
        "approx_gb": 16.3,
        "vram_rec": "12GB 이상 (4-bit 시 ~6.5GB, 16GB VRAM 환경 완벽 호환)",
        "compatible_16gb": True
    },
    "qwen3-30b": {
        "repo_id": "Qwen/Qwen3-VL-30B-A3B-Instruct",
        "name": "Qwen3-VL-30B-A3B-Instruct",
        "approx_gb": 57.9,
        "vram_rec": "32GB 이상 (4-bit 시 ~18~20GB 필요 -> 16GB VRAM 초과, CPU 오프로딩 필수)",
        "compatible_16gb": False
    },
    "qwen2.5-32b": {
        "repo_id": "Qwen/Qwen2.5-VL-32B-Instruct",
        "name": "Qwen2.5-VL-32B-Instruct",
        "approx_gb": 63.6,
        "vram_rec": "40GB 이상 (4-bit 시 ~20GB 필요 -> 16GB VRAM 초과, CPU 오프로딩 필수)",
        "compatible_16gb": False
    }
}


def download_single_model(key: str, info: dict, target_dir: str = None):
    repo_id = info["repo_id"]
    print("=" * 65)
    print(f"[*] 모델 다운로드 시작: {info['name']}")
    print(f"    - HuggingFace Repo: {repo_id}")
    print(f"    - 예상 크기: 약 {info['approx_gb']} GB")
    print(f"    - VRAM 권장: {info['vram_rec']}")
    if not info["compatible_16gb"]:
        print("    [!] 주의: 해당 대형 모델은 16GB VRAM을 초과하여 추론 시 CPU 메모리 공유가 필요합니다.")
    print("=" * 65, flush=True)

    t0 = time.time()
    for attempt in range(1, 4):
        try:
            kwargs = {
                "repo_id": repo_id,
                "max_workers": 2,
            }
            if target_dir:
                kwargs["local_dir"] = os.path.join(target_dir, key)

            local_path = snapshot_download(**kwargs)
            elapsed = time.time() - t0
            print(f"\n[+] 다운로드 완료! ({elapsed/60:.1f}분 소요)")
            print(f"    저장 경로: {local_path}\n", flush=True)
            return True
        except Exception as e:
            print(f"\n[-] 다운로드 중 오류 (시도 {attempt}/3): {e}", flush=True)
            time.sleep(5)
    return False


def main():
    parser = argparse.ArgumentParser(description="VLM 모델 로컬 다운로더")
    parser.add_argument(
        "--model",
        type=str,
        default="menu",
        help="다운로드할 모델 식별자 (쉼표 구분 복수 지정 가능: llava-next, llava-onevision, qwen3-8b, qwen3-30b, qwen2.5-32b, all, recommended)"
    )
    parser.add_argument("--save-dir", type=str, default=None, help="커스텀 저장 경로 (지정하지 않으면 기본 HuggingFace 캐시 디렉터리 사용)")
    args = parser.parse_args()

    if args.model == "menu":
        print("\n=======================================================")
        print("          VLM 모델 다운로드 대상 목록 및 현황")
        print("=======================================================")
        print(" [현재 시스템 GPU: NVIDIA RTX 3080 Laptop (16GB VRAM)]\n")
        for idx, (k, v) in enumerate(SUPPORTED_MODELS.items(), 1):
            compat_tag = "[16GB VRAM 추천]" if v["compatible_16gb"] else "[16GB VRAM 초과 주의]"
            print(f" {idx}. {k:16s} | {v['name']:28s} | ~{v['approx_gb']:4.1f} GB | {compat_tag}")
        print("-------------------------------------------------------")
        print(" 실행 예시:")
        print("   python download_models.py --model qwen3-8b")
        print("   python download_models.py --model llava-next,llava-onevision,qwen3-8b")
        print("   python download_models.py --model recommended")
        print("   python download_models.py --model all")
        print("=======================================================\n")
        return

    requested = [m.strip() for m in args.model.split(",") if m.strip()]
    targets = []
    for req in requested:
        if req == "all":
            targets = list(SUPPORTED_MODELS.keys())
            break
        elif req == "recommended":
            targets.extend([k for k, v in SUPPORTED_MODELS.items() if v["compatible_16gb"]])
        elif req in SUPPORTED_MODELS:
            if req not in targets:
                targets.append(req)
        else:
            print(f"[경고] 알 수 없는 모델 키입니다: {req}")

    print(f"\n[*] 총 {len(targets)}개 모델 다운로드를 진행합니다: {targets}\n")
    for key in targets:
        download_single_model(key, SUPPORTED_MODELS[key], target_dir=args.save_dir)


if __name__ == "__main__":
    main()

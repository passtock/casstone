"""VLM 모델 다운로드 실시간 진행률 확인 스크립트
터미널에서 언제든지 'python check_download.py'를 실행하여 확인 가능
"""

import os
import sys

# 윈도우 터미널 UTF-8 인코딩 보장
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    hub_path = os.path.expanduser("~/.cache/huggingface/hub")

    target_models = {
        "models--lmms-lab--LLaVA-NeXT-Video-7B": ("LLaVA-NeXT-Video-7B", 13.2),
        "models--lmms-lab--llava-onevision-qwen2-7b-ov": ("LLaVA-OneVision-7B", 15.0),
        "models--Qwen--Qwen3-VL-8B-Instruct": ("Qwen3-VL-8B-Instruct", 16.3),
        "models--Qwen--Qwen2.5-VL-32B-Instruct": ("Qwen2.5-VL-32B-Instruct", 63.6),
    }

    print("=" * 68)
    print("              VLM 모델 다운로드 실시간 진행 현황")
    print("=" * 68)

    for folder_name, (display_name, total_gb) in target_models.items():
        folder_dir = os.path.join(hub_path, folder_name)
        if not os.path.exists(folder_dir):
            status = "대기 중 (0.0 GB / 0%)"
            bar = "[                    ]"
            print(f"- {display_name:24s} : {bar} {status}")
            continue

        # 폴더 내 모든 파일 (임시 다운로드 파일 포함) 크기 합산
        total_bytes = 0
        for root, _, files in os.walk(folder_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except Exception:
                    pass

        curr_gb = total_bytes / (1024 ** 3)
        pct = min(100.0, (curr_gb / total_gb) * 100.0) if total_gb > 0 else 0.0

        bar_len = 20
        filled = int(bar_len * (pct / 100.0))
        bar = "[" + "#" * filled + " " * (bar_len - filled) + "]"

        if pct >= 99.0:
            status_tag = f"완료 ({curr_gb:.2f} GB / 100%)"
        elif curr_gb > 0:
            status_tag = f"다운로드 중 ({curr_gb:.2f} GB / {total_gb:.1f} GB, {pct:.1f}%)"
        else:
            status_tag = "준비 중"

        print(f"- {display_name:24s} : {bar} {status_tag}")

    print("=" * 68)
    print("※ 터미널에서 'python check_download.py'를 실행하시면 언제든지 확인하실 수 있습니다.")
    print("=" * 68)


if __name__ == "__main__":
    main()

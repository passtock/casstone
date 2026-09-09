# 06_VLM_재활평가_테스트 (RTX 3060 로컬 최적화 가이드)

이 폴더는 2026년 최신 논문(*Vision-language models for human motion understanding: Lessons from stroke rehabilitation*, NYU)에서 사용된 **VLM 기반 재활 모션 정량 평가 파이프라인**을 로컬 GPU(RTX 3060 기준)에서 직접 테스트해 볼 수 있도록 구축된 모듈입니다.

---

## 1. 모델 구성 및 VRAM 요구 사양

RTX 3060(6GB Laptop 또는 12GB Desktop) 및 일반 PC 환경에 맞추어 모델을 선택할 수 있습니다:

| 모델명 | 정밀도 / 양자화 | 소모 VRAM | 추천 실행 환경 | 특징 |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen2.5-VL-3B-Instruct** (기본) | 기본 (bfloat16) | **약 6.5 GB** | RTX 3060 (12GB) / 3080 | 초고속 추론, 텍스트/영상 이해 균형 우수 |
| **Qwen2.5-VL-3B-Instruct** | 4-bit 양자화 | **약 3.2 GB** | RTX 3060 (6GB 노트북) | 극도로 가벼운 VRAM, 완벽 구동 |
| **Qwen2.5-VL-7B-Instruct** (논문 모델) | 4-bit 양자화 | **약 5.5 GB** | RTX 3060 (6GB / 12GB) | 논문에서 77.5% 정확도를 기록한 SOTA 모델 |
| **Qwen2.5-VL-7B-Instruct** | 기본 (bfloat16) | **약 14.8 GB** | 16GB VRAM (현재 PC) | 원본 무손실 가중치 추론 |

---

## 2. 패키지 설치

필요한 라이브러리가 이미 설치 중이거나 설치되어 있지 않다면 아래 명령어로 설치할 수 있습니다:

```bash
# 1. PyTorch CUDA 버전 설치 (CUDA 12.4 기준)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# 2. VLM 및 비전 처리 패키지 설치
pip install transformers accelerate qwen-vl-utils bitsandbytes opencv-python pillow
```

---

## 3. 실행 방법

### (1) 빠른 자체 동작 검증 (Quick Test)
샘플 이미지를 자동 생성하여 VLM 추론이 정상 작동하는지 확인합니다:
```bash
python test_run.py
```

### (2) 실제 재활 영상 분석
웹캠으로 녹화한 영상이나 재활 평가 영상을 분석합니다:
```bash
# 기본 3B 모델로 9대 ADL 활동 및 손 움직임 분석
python vlm_rehab_eval.py --video "내_재활_영상.avi"

# 6GB VRAM 환경일 때 4bit 양자화 옵션 적용
python vlm_rehab_eval.py --video "내_재활_영상.avi" --quant 4bit

# 논문에 나온 7B 모델로 테스트해보고 싶을 때
python vlm_rehab_eval.py --video "내_재활_영상.avi" --model "Qwen/Qwen2.5-VL-7B-Instruct" --quant 4bit
```

### (3) 특정 이미지에 대한 자유 질문 (VQA)
```bash
python vlm_rehab_eval.py --image "sample_test_hand.jpg" --prompt "손이 물체를 잡고 있나요, 아니면 뻗고 있나요?"
```

---

## 4. 논문과의 연계 분석 포인트
- **과제 1 (Activity Identification)**: 8개 프레임 균일 추출 후 9개 일상 활동 분류
- **과제 2 (Decomposed Prompting)**: 복잡한 5개 동작을 "Motion(움직임) O/X", "Grasp(쥐기) O/X" 이진 질문으로 분해하여 추론

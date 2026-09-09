"""VLM 기반 뇌졸중 재활 동작 평가 및 기능 분석 모듈
- 대상 모델: Qwen2.5-VL-3B-Instruct (RTX 3060 6GB/12GB 최적화)
             또는 Qwen2.5-VL-7B-Instruct (논문 주요 테스트 모델, 4-bit 권장)
- 주요 기능:
  1. 9대 재활 활동 식별 (Activity Identification - 직접/최적화 프롬프트)
  2. 원초 동작 분해 판별 (Motion & Grasp Decomposed Prompting)
  3. 커스텀 영상/이미지 VQA 분석
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Union

import cv2
import torch
import numpy as np
from PIL import Image


class VLMRehabEvaluator:
    """RTX 3060 환경에서 효율적으로 구동되는 VLM 재활 평가기"""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct",
        quantization: str = "none",  # "4bit", "8bit", "none"
        device: Optional[str] = None
    ):
        self.model_name = model_name
        self.quantization = quantization
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[*] VLMRehabEvaluator 초기화: {model_name} (장치: {self.device}, 양자화: {quantization})")

        self.model = None
        self.processor = None
        self._load_model()

    def _load_model(self):
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

        print(f"[*] 모델 가중치 로드 중: {self.model_name}...")

        load_kwargs = {}
        if self.device == "cuda":
            if self.quantization == "4bit":
                from transformers import BitsAndBytesConfig
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
                load_kwargs["device_map"] = "auto"
            elif self.quantization == "8bit":
                from transformers import BitsAndBytesConfig
                load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                load_kwargs["device_map"] = "auto"
            else:
                # bfloat16 또는 float16 사용
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                load_kwargs["torch_dtype"] = dtype
                load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["torch_dtype"] = torch.float32

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_name,
            **load_kwargs
        )
        min_pixels = 256 * 28 * 28
        max_pixels = 512 * 28 * 28
        self.processor = AutoProcessor.from_pretrained(
            self.model_name,
            min_pixels=min_pixels,
            max_pixels=max_pixels
        )
        print("[+] 모델 로드 완료!")

    def sample_video_frames(self, video_path: Union[str, Path], num_frames: int = 8, max_width: int = 512) -> List[Image.Image]:
        """비디오에서 균일하게 지정 개수의 프레임을 추출하여 PIL Image 리스트로 반환 (RTX 3060 최적화 해상도 조정)"""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise FileNotFoundError(f"비디오를 열 수 없습니다: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            raise ValueError("비디오 프레임 수가 유효하지 않습니다.")

        indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                if w > max_width:
                    new_w = max_width
                    new_h = int(h * (new_w / w))
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))
        cap.release()
        return frames

    def ask(self, images: List[Image.Image], prompt: str, max_new_tokens: int = 128) -> str:
        """프레임 이미지들과 프롬프트를 입력받아 VLM 텍스트 추론 반환"""
        from qwen_vl_utils import process_vision_info

        content = []
        for img in images:
            content.append({"type": "image", "image": img})
        content.append({"type": "text", "text": prompt})

        messages = [
            {"role": "user", "content": content}
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        )
        inputs = inputs.to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            response = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

        return response.strip()

    def identify_activity(self, video_or_frames: Union[str, Path, List[Image.Image]], optimized: bool = True) -> str:
        """논문 과제 1: 9대 일상 재활 활동(ADL) 식별 (8프레임 기반)"""
        if isinstance(video_or_frames, (str, Path)):
            frames = self.sample_video_frames(video_or_frames, num_frames=8)
        else:
            frames = video_or_frames

        if optimized:
            # 논문에서 제안한 모델 어휘 기반 최적화 프롬프트
            prompt = (
                "You are an expert rehabilitation analyzer. Look at these 8 video frames from an upper limb rehabilitation session. "
                "Identify which of the following 9 activities is being performed:\n"
                "1. Brushing teeth\n"
                "2. Combing hair\n"
                "3. Applying deodorant\n"
                "4. Drinking water\n"
                "5. Washing face\n"
                "6. Eating\n"
                "7. Putting on/taking off glasses\n"
                "8. Radial tabletop task (moving a roll on a table horizontally)\n"
                "9. Shelf task (moving a roll vertically on shelves)\n\n"
                "Answer with the exact activity name only."
            )
        else:
            prompt = "What rehabilitation activity is the person performing in these frames? Choose from: brushing teeth, combing hair, applying deodorant, drinking water, washing face, eating, glasses, tabletop task, shelf task."

        return self.ask(frames, prompt)

    def detect_motion_and_grasp(self, video_or_frames: Union[str, Path, List[Image.Image]], target_hand: str = "right") -> dict:
        """논문 과제 2: 원초 기능 동작 분해 (Decomposed Prompting: Motion & Grasp)"""
        if isinstance(video_or_frames, (str, Path)):
            frames = self.sample_video_frames(video_or_frames, num_frames=8)
        else:
            frames = video_or_frames

        # Q1: 움직임 여부
        q_motion = f"Focus strictly on the subject's {target_hand} hand. Is the {target_hand} hand moving significantly during these frames? Answer 'Yes' or 'No' directly."
        ans_motion = self.ask(frames, q_motion, max_new_tokens=16)

        # Q2: 파지(Grasp) 여부
        q_grasp = f"Focus strictly on the subject's {target_hand} hand. Is the {target_hand} hand actively grasping or holding an object? Answer 'Yes' or 'No' directly."
        ans_grasp = self.ask(frames, q_grasp, max_new_tokens=16)

        has_motion = "yes" in ans_motion.lower()
        has_grasp = "yes" in ans_grasp.lower()

        # 기능적 프리미티브 기본 추론
        if not has_motion and not has_grasp:
            primitive = "Idle (대기/휴지)"
        elif not has_motion and has_grasp:
            primitive = "Stabilize (물체 유지/고정)"
        elif has_motion and has_grasp:
            primitive = "Transport (물체 쥐고 이동)"
        else:
            primitive = "Reach or Reposition (접촉 전 이동 또는 원위치 복귀)"

        return {
            "target_hand": target_hand,
            "motion_detected": has_motion,
            "motion_raw": ans_motion,
            "grasp_detected": has_grasp,
            "grasp_raw": ans_grasp,
            "estimated_primitive": primitive
        }


def main():
    parser = argparse.ArgumentParser(description="VLM 뇌졸중 재활 평가 로컬 테스트")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-VL-3B-Instruct",
                        help="HuggingFace 모델 ID (기본: Qwen/Qwen2.5-VL-3B-Instruct, 대안: Qwen/Qwen2.5-VL-7B-Instruct)")
    parser.add_argument("--quant", type=str, default="none", choices=["none", "4bit", "8bit"],
                        help="양자화 모드 (RTX 3060 6GB의 경우 4bit 추천, 12GB/16GB는 none 추천)")
    parser.add_argument("--image", type=str, default=None, help="테스트할 단일 이미지 경로")
    parser.add_argument("--video", type=str, default=None, help="테스트할 비디오 파일 경로")
    parser.add_argument("--prompt", type=str, default=None, help="자유 질문 프롬프트")
    args = parser.parse_args()

    evaluator = VLMRehabEvaluator(model_name=args.model, quantization=args.quant)

    if args.image:
        img = Image.open(args.image).convert("RGB")
        prompt = args.prompt or "Describe the hand pose and whether the hand is holding any object."
        print(f"\n[질문]: {prompt}")
        res = evaluator.ask([img], prompt)
        print(f"[답변]: {res}\n")

    elif args.video:
        print("\n--- [과제 1: 재활 활동 분류 (Activity Identification)] ---")
        act = evaluator.identify_activity(args.video)
        print(f"식별된 활동: {act}")

        print("\n--- [과제 2: 원초 동작 분해 판별 (Motion & Grasp)] ---")
        mg = evaluator.detect_motion_and_grasp(args.video, target_hand="right")
        print(f"오른손 분석 결과: {mg}")

    else:
        print("\n[안내] 테스트할 이미지(--image) 또는 비디오(--video) 경로를 전달해 주세요.")
        print("예시: python vlm_rehab_eval.py --image test_sample.jpg --quant 4bit")


if __name__ == "__main__":
    main()

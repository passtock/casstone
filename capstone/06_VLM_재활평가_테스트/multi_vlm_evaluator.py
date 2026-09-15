"""다중 VLM 통합 재활 모션 평가 엔진 (Unified Multi-VLM Rehabilitation Evaluator)
- 지원 모델군:
  1. Qwen3-VL-8B-Instruct (Qwen/Qwen3-VL-8B-Instruct)
  2. Qwen2.5-VL-32B-Instruct (Qwen/Qwen2.5-VL-32B-Instruct)
  3. LLaVA-NeXT-Video-7B (lmms-lab/LLaVA-NeXT-Video-7B)
  4. LLaVA-OneVision-7B (lmms-lab/llava-onevision-qwen2-7b-ov)
  (추가: 기본 Qwen2.5-VL-3B-Instruct 호환)
- 지원 모드:
  1. "14frames" : 전체 영상 균등 14프레임 정규화 추출 (0%~100%) + 타임스탬프 각인
  2. "full"     : 전체 영상 직접 투입 (동영상 네이티브 또는 1fps 균등 샘플링)
- 평가 프로토콜 (NYU 2026 논문 기준):
  - Task 1: 활동 및 세팅 식별 (Activity & Scene Identification)
  - Task 2: 양손 원초 동작 이진 분해 판별 (Motion & Grasp Decomposition)
  - Task 3: 양손 대칭성 및 운동 협응 분석 (Bimanual Coordination & Symmetry)
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Union, Optional
from PIL import Image

import cv2
import numpy as np
import torch


def print_step(step: int, total: int, title: str):
    pct = int((step / total) * 100)
    bar_len = 25
    filled = int(bar_len * (step / total))
    bar = "■" * filled + " " * (bar_len - filled)
    print(f"\n[{bar}] {pct}% | [{step}/{total}] {title}", flush=True)


def extract_14_normalized_frames(
    video_path: str,
    output_dir: str = "sampled_14_frames",
    num_frames: int = 14,
    max_width: int = 512
) -> Tuple[List[Image.Image], List[dict], float]:
    """전체 80초 영상에서 균등하게 14개 프레임(0%~100%) 정규화 추출 및 타임스탬프 각인"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps

    os.makedirs(output_dir, exist_ok=True)
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames_pil = []
    meta = []

    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        sec = idx / fps
        pct = (idx / (total_frames - 1)) * 100.0 if total_frames > 1 else 0.0

        h, w = frame.shape[:2]
        if w > max_width:
            new_w = max_width
            new_h = int(h * (new_w / w))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        overlay_text = f"Frame {i+1}/{num_frames} | T={sec:.1f}s ({pct:.0f}%)"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), (20, 20, 20), -1)
        cv2.putText(
            frame, overlay_text, (12, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2, cv2.LINE_AA
        )

        save_path = os.path.join(output_dir, f"frame_{i+1:02d}_t{sec:04.1f}s.jpg")
        cv2.imwrite(save_path, frame)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames_pil.append(Image.fromarray(frame_rgb))
        meta.append({
            "frame_idx": i + 1,
            "video_frame_idx": int(idx),
            "timestamp_s": sec,
            "progress_pct": pct,
            "save_path": save_path
        })

    cap.release()
    return frames_pil, meta, duration_s


def sample_video_uniform_array(video_path: str, max_frames: int = 32, max_width: int = 384) -> Tuple[np.ndarray, float]:
    """LLaVA 등 동영상 텐서 입력을 위한 프레임 균등 추출 numpy array 반환 (N, H, W, C)"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps

    num_samples = min(max_frames, total_frames)
    indices = np.linspace(0, total_frames - 1, num_samples, dtype=int)
    frames_list = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        h, w = frame.shape[:2]
        if w > max_width:
            new_w = max_width
            new_h = int(h * (new_w / w))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames_list.append(frame_rgb)

    cap.release()
    return np.array(frames_list), duration_s


class UnifiedVLMRehabRunner:
    """4개 VLM 모델에 대해 통일된 재활 평가 파이프라인을 제공하는 실행기"""

    def __init__(
        self,
        model_type: str,  # "qwen3_8b", "qwen25_32b", "llavanext", "llavaonevision", "qwen25_3b"
        quantization: str = "4bit",
        device: Optional[str] = None
    ):
        self.model_type = model_type
        self.quantization = quantization
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None
        self.repo_id = self._get_repo_id()

        print(f"[*] UnifiedVLMRehabRunner 초기화: {self.model_type} ({self.repo_id})")
        print(f"    - 디바이스: {self.device} | 양자화: {self.quantization}")
        self._load_model()

    def _get_repo_id(self) -> str:
        mapping = {
            "qwen3_8b": "Qwen/Qwen3-VL-8B-Instruct",
            "qwen25_32b": "Qwen/Qwen2.5-VL-32B-Instruct",
            "llavanext": "lmms-lab/LLaVA-NeXT-Video-7B",
            "llavaonevision": "lmms-lab/llava-onevision-qwen2-7b-ov",
            "qwen25_3b": "Qwen/Qwen2.5-VL-3B-Instruct"
        }
        if self.model_type not in mapping:
            raise ValueError(f"지원하지 않는 model_type: {self.model_type}")
        return mapping[self.model_type]

    def _load_model(self):
        t0 = time.time()
        print(f"[*] 모델 가중치 로드 중: {self.repo_id}...")

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
            else:
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                load_kwargs["torch_dtype"] = dtype
                load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["torch_dtype"] = torch.float32

        # 모델 패밀리별 최적 클래스 선택
        if self.model_type in ["qwen3_8b", "qwen25_32b", "qwen25_3b"]:
            from transformers import AutoProcessor, AutoModelForImageTextToText
            try:
                if "qwen3" in self.model_type:
                    from transformers import Qwen3VLForConditionalGeneration
                    self.model = Qwen3VLForConditionalGeneration.from_pretrained(self.repo_id, **load_kwargs)
                else:
                    from transformers import Qwen2_5_VLForConditionalGeneration
                    self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(self.repo_id, **load_kwargs)
            except Exception:
                self.model = AutoModelForImageTextToText.from_pretrained(self.repo_id, **load_kwargs)

            self.processor = AutoProcessor.from_pretrained(
                self.repo_id,
                min_pixels=256 * 28 * 28,
                max_pixels=512 * 28 * 28
            )

        elif self.model_type == "llavanext":
            from transformers import LlavaNextVideoForConditionalGeneration, LlavaNextVideoProcessor
            self.model = LlavaNextVideoForConditionalGeneration.from_pretrained(self.repo_id, **load_kwargs)
            self.processor = LlavaNextVideoProcessor.from_pretrained(self.repo_id)

        elif self.model_type == "llavaonevision":
            from transformers import LlavaOnevisionForConditionalGeneration, LlavaOnevisionProcessor
            self.model = LlavaOnevisionForConditionalGeneration.from_pretrained(self.repo_id, **load_kwargs)
            self.processor = LlavaOnevisionProcessor.from_pretrained(self.repo_id)

        print(f"[+] 모델 로드 완료! (소요 시간: {time.time() - t0:.1f}초)")

    def ask(self, vision_input: Union[str, Path, List[Image.Image], np.ndarray], prompt: str, max_new_tokens: int = 256) -> str:
        """Qwen 계열 및 LLaVA 계열을 아우르는 범용 질의 인터페이스"""
        if self.model_type in ["qwen3_8b", "qwen25_32b", "qwen25_3b"]:
            return self._ask_qwen(vision_input, prompt, max_new_tokens)
        elif self.model_type == "llavanext":
            return self._ask_llavanext(vision_input, prompt, max_new_tokens)
        elif self.model_type == "llavaonevision":
            return self._ask_llavaonevision(vision_input, prompt, max_new_tokens)

    def _ask_qwen(self, vision_input, prompt: str, max_new_tokens: int) -> str:
        from qwen_vl_utils import process_vision_info
        content = []
        if isinstance(vision_input, (str, Path)):
            content.append({"type": "video", "video": str(vision_input), "fps": 0.5, "max_pixels": 256 * 28 * 28})
        elif isinstance(vision_input, list):
            for img in vision_input:
                content.append({"type": "image", "image": img})
        elif isinstance(vision_input, np.ndarray):
            for frame in vision_input:
                content.append({"type": "image", "image": Image.fromarray(frame)})

        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)

        proc_kwargs = {
            "text": [text],
            "images": image_inputs,
            "videos": video_inputs,
            "padding": True,
            "return_tensors": "pt"
        }
        if video_inputs is not None:
            proc_kwargs["cap_pixels_per_frame"] = True

        inputs = self.processor(**proc_kwargs).to(self.model.device)
        with torch.no_grad():
            out_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
            trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, out_ids)]
            res = self.processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return res.strip()

    def _ask_llavanext(self, vision_input, prompt: str, max_new_tokens: int) -> str:
        if isinstance(vision_input, (str, Path)):
            video_arr, _ = sample_video_uniform_array(str(vision_input), max_frames=16, max_width=384)
        elif isinstance(vision_input, list):
            video_arr = np.stack([np.array(img) for img in vision_input])
        elif isinstance(vision_input, np.ndarray):
            video_arr = vision_input

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "video"},
                ],
            },
        ]
        prompt_text = self.processor.apply_chat_template(conversation, add_generation_prompt=True)
        inputs = self.processor(text=prompt_text, videos=video_arr, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
            in_len = inputs.input_ids.shape[1]
            res = self.processor.decode(out[0][in_len:], skip_special_tokens=True)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return res.strip()

    def _ask_llavaonevision(self, vision_input, prompt: str, max_new_tokens: int) -> str:
        if isinstance(vision_input, (str, Path)):
            video_arr, _ = sample_video_uniform_array(str(vision_input), max_frames=16, max_width=384)
        elif isinstance(vision_input, list):
            video_arr = np.stack([np.array(img) for img in vision_input])
        elif isinstance(vision_input, np.ndarray):
            video_arr = vision_input

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "video"},
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        prompt_text = self.processor.apply_chat_template(conversation, add_generation_prompt=True)
        inputs = self.processor(text=prompt_text, videos=video_arr, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
            in_len = inputs.input_ids.shape[1]
            res = self.processor.decode(out[0][in_len:], skip_special_tokens=True)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return res.strip()

    def run_rehab_evaluation(self, video_path: str, mode: str = "14frames") -> dict:
        """3대 재활 평가 프로토콜 수행 및 결과 딕셔너리 반환"""
        t_start = time.time()
        print_step(1, 4, f"영상 입력 준비 (모드: {mode})")

        if mode == "14frames":
            vision_data, meta, dur = extract_14_normalized_frames(video_path, output_dir="sampled_14_frames", num_frames=14)
            p_prefix = "These 14 chronological frames represent an upper-limb rehabilitation movement sequence from start (0%) to end (100%). "
        else:
            vision_data = video_path
            meta = []
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
            cap.release()
            p_prefix = "Watch this upper-limb rehabilitation movement session video carefully. "

        # Task 1: 활동 및 세팅 식별
        print_step(2, 4, "과제 1: 장면 및 재활 활동 식별 (Activity Identification)")
        t0 = time.time()
        prompt_act = (
            f"{p_prefix}Describe in detail: "
            "1) What objects are on the table and what the participant is doing with both hands. "
            "2) Is the participant performing a bimanual grasping or stabilization task on the two round objects?"
        )
        res_act = self.ask(vision_data, prompt_act, max_new_tokens=256)
        print(f" -> 추론 완료 ({time.time() - t0:.1f}초)")

        # Task 2: 양손 동작 및 파지 분해 판별
        print_step(3, 4, "과제 2: 양손 Motion & Grasp 이진 분해 판별 (NYU 2026 논문 프로토콜)")
        t0 = time.time()

        def eval_hand(hand: str) -> dict:
            q_m = f"{p_prefix}Focus strictly on the subject's {hand} hand. Is the {hand} hand moving significantly? Answer 'Yes' or 'No' directly."
            ans_m = self.ask(vision_data, q_m, max_new_tokens=16)
            q_g = f"{p_prefix}Focus strictly on the subject's {hand} hand. Is the {hand} hand actively grasping or holding an object? Answer 'Yes' or 'No' directly."
            ans_g = self.ask(vision_data, q_g, max_new_tokens=16)

            has_m = "yes" in ans_m.lower()
            has_g = "yes" in ans_g.lower()

            if not has_m and not has_g:
                prim = "Idle (대기/휴지)"
            elif not has_m and has_g:
                prim = "Stabilize (물체 유지/고정)"
            elif has_m and has_g:
                prim = "Transport (물체 쥐고 이동)"
            else:
                prim = "Reach or Reposition (접촉 전 이동 또는 원위치 복귀)"

            return {"hand": hand, "motion": has_m, "motion_raw": ans_m, "grasp": has_g, "grasp_raw": ans_g, "primitive": prim}

        mg_right = eval_hand("right")
        mg_left = eval_hand("left")
        print(f" -> 분해 판별 완료 ({time.time() - t0:.1f}초)")

        # Task 3: 대칭성 및 협응 분석
        print_step(4, 4, "과제 3: 양손 대칭성 및 운동 협응 분석 (Bimanual Coordination & Symmetry)")
        t0 = time.time()
        prompt_sym = (
            f"{p_prefix}Observe the movement coordination between the left hand and right hand. "
            "Are both hands placed and moved symmetrically over the two spherical objects? "
            "Does either hand show hesitation, tremor, or asymmetry?"
        )
        res_sym = self.ask(vision_data, prompt_sym, max_new_tokens=256)
        print(f" -> 추론 완료 ({time.time() - t0:.1f}초)")

        total_elapsed = time.time() - t_start

        return {
            "model_type": self.model_type,
            "repo_id": self.repo_id,
            "mode": mode,
            "video_path": video_path,
            "duration_s": dur,
            "total_elapsed": total_elapsed,
            "activity": res_act,
            "mg_right": mg_right,
            "mg_left": mg_left,
            "symmetry": res_sym,
            "frame_meta": meta
        }


def save_markdown_report(result: dict, output_path: str):
    """분석 결과를 깔끔한 마크다운 보고서로 저장"""
    r = result
    report_md = f"""# VLM 재활 평가 분석 리포트 [{r['model_type'].upper()} - {r['mode'].upper()}]

- **분석 모델**: `{r['repo_id']}`
- **분석 모드**: `{'14프레임 정규화 추출' if r['mode'] == '14frames' else '전체 동영상 직접 투입'}`
- **대상 영상**: `{r['video_path']}` (길이: {r['duration_s']:.1f}초)
- **총 분석 소요 시간**: {r['total_elapsed']:.1f}초
- **분석 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. 전체 활동 및 세팅 식별 (Activity & Scene Identification)
{r['activity']}

---

## 2. 기능적 원초 동작 분해 판별 (Motion & Grasp Decomposition - NYU 2026 논문)

### [오른손 (Right Hand)]
- **움직임 (Motion)**: {'O (Yes)' if r['mg_right']['motion'] else 'X (No)'} (응답 원문: `{r['mg_right']['motion_raw']}`)
- **파지 (Grasp)**: {'O (Yes)' if r['mg_right']['grasp'] else 'X (No)'} (응답 원문: `{r['mg_right']['grasp_raw']}`)
- **도출 프리미티브**: **{r['mg_right']['primitive']}**

### [왼손 (Left Hand)]
- **움직임 (Motion)**: {'O (Yes)' if r['mg_left']['motion'] else 'X (No)'} (응답 원문: `{r['mg_left']['motion_raw']}`)
- **파지 (Grasp)**: {'O (Yes)' if r['mg_left']['grasp'] else 'X (No)'} (응답 원문: `{r['mg_left']['grasp_raw']}`)
- **도출 프리미티브**: **{r['mg_left']['primitive']}**

---

## 3. 양손 대칭성 및 운동 협응 분석 (Bimanual Coordination & Symmetry)
{r['symmetry']}

---

## 4. 임상적 시사점 및 고찰
- VLM 모델(`{r['repo_id']}`)의 시각적 인지 결과와 RealSense 3D Depth + Kinematics 정량 계측 데이터를 결합하여 보다 높은 신뢰성의 재활 평가 지표를 완성할 수 있습니다.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n[+] 상세 리포트가 '{output_path}'에 저장되었습니다.")

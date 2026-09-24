# -*- coding: utf-8 -*-
"""
VLM 실행 하네스 (v6.1 프로토콜 §7) — 조건 → 프레임 → 프롬프트 → 모델 → 점수 → predictions.csv
=============================================================================================

목적
----
`make_conditions.py`가 만든 조건 목록(`conditions.csv` + `prompts/`)을 입력으로 받아,
프로토콜 §7의 프레임 규칙으로 영상을 샘플링하고, VLM에 물어보고, 출력을 파싱해
**`analysis_harness.py`가 바로 읽는 `predictions.csv`** 를 만든다.

이것이 완성되면 **조건 생성 → VLM 실행 → 분석**이 코드로 연결된다.

백엔드 3종
----------
| backend | 하는 일 | 언제 |
|---|---|---|
| `dry`   | 프레임 추출 + 프롬프트만. **모델 호출 없음.** manifest만 기록 | 컴퓨트 없이 배선·프레임 수 검증 |
| `mock`  | 결정론적 가짜 점수. **모델 출력이 아니다.** 출력 파일명이 `predictions_MOCK.csv` | 파이프라인 배선 검증 |
| `qwen`  | 실제 Qwen2.5-VL (transformers). GPU·모델 필요 | 실제 실행 |

⚠️ **`mock`은 절대 결과가 아니다.** 파일명·rationale·경고문에 표시된다. 논문 인용 금지.

프레임 규칙 (프로토콜 §7, 동결)
------------------------------
- 앞 **5.0초 = 10 Hz → 50프레임**
- 5초 초과분 = **2 Hz**
- **총 상한 64**
- **640×480** 축소, 원본은 30 fps로 별도 보존

출력 (predictions.csv)
----------------------
participant_id,trial_id,task,condition,injection,run,predicted_score,rationale,output_status,k1_provided,k2_provided

- `trial_id` 규칙: `{pid}__{side}__{task_code}__{trial_code}`  (예: `S01__Right__T2__t1`)
- `k1_provided`/`k2_provided`: 프롬프트에 그 수치가 실제로 들어갔는가 (1/0)
  → `analysis_harness.py`의 **보류율** 계산 입력

실행
----
  python experiments/vlm/run_vlm.py --selftest
  python experiments/vlm/run_vlm.py --conditions <dir>/conditions.csv --out <dir> --backend dry
  python experiments/vlm/run_vlm.py --conditions <dir>/conditions.csv --out <dir> --backend mock
  python experiments/vlm/run_vlm.py --conditions <dir>/conditions.csv --out <dir> --backend qwen \\
      --model Qwen/Qwen2.5-VL-72B-Instruct
  python experiments/vlm/run_vlm.py --scores-to-reference <score_sheet.csv> --out <dir>
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import zlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---- 프로토콜 §7 (동결) ----
HEAD_SEC = 5.0
HEAD_HZ = 10
TAIL_HZ = 2
FRAME_CAP = 64
FRAME_W, FRAME_H = 640, 480
DEFAULT_FPS = 30.0

# K1/K2 로 쓰는 지표 이름 (make_conditions.py 의 metric 이름과 일치해야 함)
K1_METRIC = "MGA_mm_3D_cal"
K2_METRIC = "PV_mm_s"

CONDITIONS = ["A1", "A2", "A3", "A4", "R"]
MOCK_MARK = "[MOCK — 모델 출력 아님]"


# ===========================================================================
# 이미지 안전 저장 (결함 D-7: cv2.imwrite가 비ASCII 절대경로에서 조용히 실패)
# ===========================================================================
def safe_imwrite(path, img, ext=".png"):
    """cv2.imencode + numpy.tofile 로 저장. 저장 후 크기 검증. 실패 시 예외.

    Windows에서 `cv2.imwrite`는 한글 경로에 대해 False를 반환하고 파일을 만들지 않는다.
    """
    import cv2
    import numpy as np
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError("imencode 실패: %s" % path)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    buf.tofile(path)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise IOError("저장 실패(크기 0): %s" % path)
    return os.path.getsize(path)


# ===========================================================================
# 프레임 추출
# ===========================================================================
def frame_indices(total_frames, fps, head_sec=HEAD_SEC, head_hz=HEAD_HZ,
                  tail_hz=TAIL_HZ, cap=FRAME_CAP):
    """프로토콜 §7 규칙으로 뽑을 프레임 인덱스 목록 (오름차순, 중복 없음)."""
    if total_frames <= 0 or fps <= 0:
        return []
    idx = []
    head_n = int(round(head_sec * head_hz))
    step_h = max(1, int(round(fps / head_hz)))
    for i in range(head_n):
        j = i * step_h
        if j >= total_frames:
            break
        idx.append(j)
    n_head = len(idx)
    remain = cap - n_head
    if remain > 0:
        step_t = max(1, int(round(fps / tail_hz)))
        start = int(round(head_sec * fps))
        j = start
        while len(idx) < cap:
            if j >= total_frames:
                break
            idx.append(j)
            j += step_t
    # 중복 제거 + 정렬 + 상한
    idx = sorted(set(idx))[:cap]
    return idx


def extract_frames(video, out_dir, fps_hint=DEFAULT_FPS):
    """영상 → 640×480 PNG 목록. 반환 (paths, meta).

    ⚠️ 실제 fps를 우선 사용한다(메타데이터). 없으면 fps_hint.
    ⚠️ 저장 실패는 **예외**로 올린다(조용한 실패 금지 — D-7).
    """
    import cv2
    if not os.path.isfile(video):
        raise FileNotFoundError("영상 없음: %s" % video)
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise IOError("영상 열기 실패: %s" % video)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or fps_hint
        if not fps or fps <= 0 or fps != fps:      # NaN 방어
            fps = fps_hint
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        want = frame_indices(total, fps)
        want_set = set(want)
        os.makedirs(out_dir, exist_ok=True)
        paths = []
        fi = 0
        saved = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if fi in want_set:
                frame = cv2.resize(frame, (FRAME_W, FRAME_H), interpolation=cv2.INTER_AREA)
                p = os.path.join(out_dir, "f%04d.png" % fi)
                safe_imwrite(p, frame, ".png")
                paths.append(p)
                saved += 1
            fi += 1
        meta = {
            "video": video,
            "fps": round(float(fps), 4),
            "total_frames_read": fi,
            "expected_n": len(want),
            "saved_n": saved,
            "frame_cap": FRAME_CAP,
        }
        if saved != len(want):
            raise IOError("프레임 수 불일치: 기대 %d, 저장 %d (%s)" % (len(want), saved, video))
        return paths, meta
    finally:
        cap.release()


# ===========================================================================
# 출력 파싱
# ===========================================================================
_SCORE_HEAD = re.compile(r"^([0-3])(?:\s*점|\s*$|[\s.,;:!?)\]}])")
_MD_CHARS = re.compile(r"[*_`#~]+")
_BULLET = re.compile(r"^[\-\u2022\u00b7\.\)\s]+")


def _clean_line(s):
    """마크다운 강조·불릿을 제거한다. VLM 이 `**2**`, `- 0 점` 처럼 내보내는 경우가 흔하다."""
    s = _MD_CHARS.sub("", (s or "").strip())
    s = _BULLET.sub("", s)
    return s.strip()


def parse_score(text):
    """VLM 출력 → (score|None, rationale, status).

    규칙: **첫 줄을 마크다운 정리 후 먼저 보고**, 없으면 전체에서 "점수: N" 형태를 찾는다.
    그래도 없으면 (None, ..., 'parse_failed').
    """
    if text is None:
        return None, "", "parse_failed"
    t = text.strip()
    if not t:
        return None, "", "parse_failed"
    lines = t.splitlines()
    first = _clean_line(lines[0])
    m = _SCORE_HEAD.match(first)
    if m:
        rationale = " ".join(ln.strip() for ln in lines[1:] if ln.strip())
        return int(m.group(1)), rationale, "ok"
    # 첫 줄에 없으면 전체에서 "점수: N"
    m = re.search(r"점수\s*[:=]?\s*([0-3])", t)
    if m:
        rest = t[m.end():].strip()
        return int(m.group(1)), rest, "ok"
    return None, "", "parse_failed"


def cap_sentences(text, n=2):
    """근거를 최대 n문장으로 자른다 (프로토콜: 최대 2문장)."""
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?。])\s+", text.strip())
    return " ".join(parts[:n]).strip()


# ===========================================================================
# trial_id 규칙
# ===========================================================================
def norm_task_code(task_str):
    """'Task 1: 맨손 쥐기/펴기' → 'T1'"""
    s = task_str or ""
    m = re.search(r"(?i)task\s*#?\s*([12])", s)
    if m:
        return "T" + m.group(1)
    m = re.search(r"(?i)\bT([12])\b", s)
    if m:
        return "T" + m.group(1)
    return "TX"


def norm_trial_code(trial_str):
    """'Trial #1' → 't1'"""
    s = trial_str or ""
    m = re.search(r"(\d+)", s)
    return "t" + m.group(1) if m else "tX"


def make_trial_id(pid, side, task_str, trial_str):
    """`{pid}__{side}__{T1|T2}__{t1..}` — conditions.csv 와 채점시트가 공유하는 정본 규칙."""
    return "%s__%s__%s__%s" % (pid, side, norm_task_code(task_str), norm_trial_code(trial_str))


# ===========================================================================
# 조건 로딩
# ===========================================================================
def load_conditions(path):
    rows = []
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({k: (v if v is not None else "") for k, v in row.items()})
    return rows


def provided_flag(row, metric):
    """그 지표가 프롬프트에 실제로 들어갔는가 (값 열이 비어 있지 않으면 1)."""
    v = (row.get("v_" + metric) or "").strip()
    return 1 if v else 0


def read_prompt(row, cond_dir):
    """prompts/<key>.txt 를 읽는다. 없으면 None."""
    rel = (row.get("prompt_path") or "").strip()
    if not rel:
        return None
    p = os.path.join(cond_dir, rel.replace("\\", os.sep).replace("/", os.sep))
    if not os.path.isfile(p):
        base = os.path.join(cond_dir, "prompts", (row.get("key") or "") + ".txt")
        if os.path.isfile(base):
            p = base
        else:
            return None
    with io.open(p, encoding="utf-8") as f:
        return f.read()


# ===========================================================================
# 백엔드
# ===========================================================================
def backend_dry(prompt, frame_paths, key):
    """모델 호출 없음."""
    h = hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()[:12]
    return "", "dry", h


def backend_mock(prompt, frame_paths, key):
    """결정론적 가짜 점수. **모델 출력이 아니다.**

    점수를 `key` 해시에서 뽑는다 → 같은 입력이면 같은 출력(재현 가능).
    ⚠️ 이 점수에는 **아무 과학적 의미가 없다.** 배선 검증 전용.
    """
    h = zlib.crc32(key.encode("utf-8"))
    score = h % 4
    text = "%d\n%s 프레임 %d장.\n%s 키=%s 해시=%d" % (
        score, MOCK_MARK, len(frame_paths), MOCK_MARK, key, h)
    return text, "ok", hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()[:12]


_QUEN_STATE = {}


def backend_qwen(prompt, frame_paths, key):
    """실제 Qwen2.5-VL. GPU·모델 필요. transformers 없으면 명확히 실패한다."""
    try:
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        from PIL import Image
    except Exception as e:            # pragma: no cover
        raise RuntimeError(
            "실제 VLM 백엔드를 쓰려면 transformers/torch/PIL 이 필요합니다: %s" % e)
    model_id = _QUEN_STATE["model_id"]
    if "model" not in _QUEN_STATE:
        _QUEN_STATE["model"] = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id, torch_dtype="auto", device_map="auto")
        _QUEN_STATE["proc"] = AutoProcessor.from_pretrained(model_id)
    model = _QUEN_STATE["model"]
    proc = _QUEN_STATE["proc"]
    imgs = [Image.open(p).convert("RGB") for p in frame_paths]
    messages = [{"role": "user", "content": [{"type": "image"} for _ in imgs]
                 + [{"type": "text", "text": prompt}]}]
    chat = proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = proc(text=[chat], images=imgs, return_tensors="pt").to(model.device)
    gen = {"max_new_tokens": _QUEN_STATE["max_new_tokens"], "do_sample": False}
    with torch.no_grad():
        out = model.generate(**inputs, **gen)
    trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, out)]
    text = proc.batch_decode(trimmed, skip_special_tokens=True)[0]
    return text, "ok", hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()[:12]


BACKENDS = {"dry": backend_dry, "mock": backend_mock, "qwen": backend_qwen}


# ===========================================================================
# 메인 실행
# ===========================================================================
def run_all(cond_csv, out_dir, backend="dry", limit=None, run_idx=1,
            model_id="Qwen/Qwen2.5-VL-72B-Instruct", max_new_tokens=256,
            frames_root=None, retry=1, save_frames=True):
    rows = load_conditions(cond_csv)
    if limit:
        rows = rows[:limit]
    cond_dir = os.path.dirname(os.path.abspath(cond_csv))
    frames_root = frames_root or os.path.join(out_dir, "frames")
    os.makedirs(frames_root, exist_ok=True)
    fn = BACKENDS[backend]
    if backend == "qwen":
        _QUEN_STATE["model_id"] = model_id
        _QUEN_STATE["max_new_tokens"] = max_new_tokens

    out_rows = []
    manifest = []
    n_fail = 0
    for i, r in enumerate(rows, 1):
        key = r.get("key") or ("row%d" % i)
        pid = (r.get("pid") or "").strip()
        side = (r.get("hand") or "").strip()
        task = (r.get("task") or "").strip()
        trial = (r.get("trial") or "").strip()
        cond = (r.get("condition") or "").strip()
        inj = (r.get("injection") or "none").strip() or "none"
        video = (r.get("video") or "").strip()
        tid = make_trial_id(pid, side, task, trial)

        prompt = read_prompt(r, cond_dir)
        if prompt is None:
            prompt = ""
            prompt_src = "missing"
        else:
            prompt_src = "file"

        fpaths, fmeta = [], {}
        status = "ok"
        text = ""
        phash = ""
        try:
            if video:
                fpaths, fmeta = extract_frames(
                    video, os.path.join(frames_root, key))
            text, status, phash = fn(prompt, fpaths, key)
        except Exception as e:
            status = "api_failed"
            text = ""
            fmeta = dict(fmeta, error=str(e)[:300])
            # 1회 재시도
            for _ in range(retry):
                try:
                    text, status, phash = fn(prompt, fpaths, key)
                    if status == "ok":
                        break
                except Exception as e2:
                    fmeta = dict(fmeta, error=str(e2)[:300])
        if status != "ok" or backend == "dry":
            score, rationale, pstat = None, "", "parse_failed"
            if backend != "dry" and status == "ok":
                score, rationale, pstat = parse_score(text)
        else:
            score, rationale, pstat = parse_score(text)
            status = pstat
        if status != "ok":
            n_fail += 1
        out_rows.append({
            "participant_id": pid,
            "trial_id": tid,
            "task": task,
            "condition": cond,
            "injection": inj,
            "run": run_idx,
            "predicted_score": "" if score is None else score,
            "rationale": cap_sentences(rationale, 2),
            "output_status": status,
            "k1_provided": provided_flag(r, K1_METRIC),
            "k2_provided": provided_flag(r, K2_METRIC),
        })
        manifest.append({
            "key": key, "trial_id": tid, "condition": cond, "injection": inj,
            "backend": backend, "prompt_source": prompt_src,
            "prompt_sha256_12": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12] if prompt else "",
            "n_frames": len(fpaths), "frames_meta": fmeta,
            "raw_output": text[:2000], "status": status,
        })
        if i % 25 == 0 or i == len(rows):
            print("  [%d/%d] %s" % (i, len(rows), key))

    return out_rows, manifest, n_fail


def write_predictions(rows, path):
    cols = ["participant_id", "trial_id", "task", "condition", "injection", "run",
            "predicted_score", "rationale", "output_status",
            "k1_provided", "k2_provided"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    return len(rows)


# ===========================================================================
# 채점시트 → reference.csv
# ===========================================================================
def scores_to_reference(score_sheet, out_dir):
    """치료사 채점시트(SCORE_FIELDS) → analysis_harness 가 읽는 reference.csv.

    점수는 `task`·`side`·`trial_index` 로 `trial_id` 를 재구성해 붙인다.
    `phase` 가 practice 인 행은 **제외**한다(모델 평가는 본 시행만).
    """
    rows = []
    with io.open(score_sheet, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            phase = (r.get("phase") or "").strip().lower()
            if phase in ("practice", "연습"):
                continue
            pid = (r.get("participant_id") or "").strip()
            side = (r.get("side") or "").strip()
            task = (r.get("task") or "").strip()
            trial = (r.get("trial_index") or "").strip()
            tid = make_trial_id(pid, side, task, trial)
            rows.append({
                "participant_id": pid,
                "trial_id": tid,
                "task": task,
                "therapist_score": (r.get("score") or "").strip(),
                # 눈가림 평가자는 별도 열 이름으로 들어온다고 가정 (없으면 빈칸)
                "independent_score": (r.get("independent_score") or "").strip(),
            })
    p = os.path.join(out_dir, "reference.csv")
    os.makedirs(out_dir, exist_ok=True)
    with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["participant_id", "trial_id", "task",
                                          "therapist_score", "independent_score"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return p, len(rows)


# ===========================================================================
# 오라클
# ===========================================================================
def selftest():
    ok_all = True
    log = []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-54s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="vlm_selftest_")

    print("[V1] 프레임 인덱스 규칙 (프로토콜 §7)")
    idx = frame_indices(210, 30.0)          # 30fps, 7초
    # 앞 5초 = 10Hz → 50프레임 (0,3,...,147) ; 초과 2초 = 2Hz → 150,165,180,195
    chk("7초/30fps → 54프레임", len(idx) == 54, "got %d" % len(idx))
    chk("첫 프레임 0 · 간격 3", idx[0] == 0 and idx[1] == 3, str(idx[:4]))
    chk("50번째 = 147", idx[49] == 147, "got %d" % idx[49])
    chk("꼬리 간격 15", idx[50] == 150 and idx[51] == 165, str(idx[50:54]))
    idx_long = frame_indices(30 * 60, 30.0)  # 60초
    chk("긴 영상도 상한 64", len(idx_long) == 64, "got %d" % len(idx_long))
    chk("빈 영상 → 0", frame_indices(0, 30.0) == [])

    print("[V2] 비ASCII 경로 저장 (결함 D-7 재발 방지)")
    import numpy as np
    han = os.path.join(tmp, "한글경로_테스트", "f0000.png")
    sz = safe_imwrite(han, np.zeros((8, 8, 3), dtype=np.uint8), ".png")
    chk("한글 경로에 저장됨", os.path.isfile(han) and sz > 0, "size=%d" % sz)

    print("[V3] 점수 파싱")
    chk("'2' → 2", parse_score("2")[0] == 2)
    chk("'3\\n정상 수행' → 3", parse_score("3\n정상 수행")[0] == 3)
    chk("'점수: 1' → 1", parse_score("점수: 1")[0] == 1)
    chk("'- 0 점' → 0", parse_score("- 0 점")[0] == 0)
    chk("'**2**' → 2 (마크다운 제거)", parse_score("**2**")[0] == 2, str(parse_score("**2**")[0]))
    chk("'2.' → 2", parse_score("2.")[0] == 2, str(parse_score("2.")[0]))
    chk("'`1`' → 1", parse_score("`1`")[0] == 1, str(parse_score("`1`")[0]))
    chk("'- 점수: 3' → 3", parse_score("- 점수: 3")[0] == 3, str(parse_score("- 점수: 3")[0]))
    chk("'4점' 은 척도 밖 → parse_failed", parse_score("4점")[2] == "parse_failed",
        str(parse_score("4점")[:1]))
    s, r, st = parse_score("2\n첫 문장. 둘째 문장. 셋째 문장.")
    chk("근거 캡처됨", s == 2 and r.startswith("첫 문장"), r[:20])
    chk("2문장 제한", cap_sentences("가. 나. 다. 라.", 2) == "가. 나.", cap_sentences("가. 나. 다. 라.", 2))
    chk("점수 없음 → parse_failed", parse_score("잘 모르겠습니다")[2] == "parse_failed")
    chk("빈 문자열 → parse_failed", parse_score("")[2] == "parse_failed")

    print("[V4] trial_id 규칙")
    chk("Task 1 → T1", norm_task_code("Task 1: 맨손 쥐기/펴기") == "T1")
    chk("T2 → T2", norm_task_code("T2") == "T2")
    chk("Trial #3 → t3", norm_trial_code("Trial #3") == "t3")
    chk("조합", make_trial_id("S01", "Right", "Task 2", "Trial #1") == "S01__Right__T2__t1",
        make_trial_id("S01", "Right", "Task 2", "Trial #1"))

    print("[V5] 합성 영상 → 프레임 추출 (엔드투엔드)")
    import cv2
    vdir = os.path.join(tmp, "vid")
    os.makedirs(vdir, exist_ok=True)
    vpath = os.path.join(vdir, "합성_테스트.avi")
    vw = cv2.VideoWriter(vpath, cv2.VideoWriter_fourcc(*"MJPG"), 30.0, (320, 240))
    if not vw.isOpened():
        chk("VideoWriter 열기", False, "MJPG 미지원?")
    else:
        for fi in range(210):     # 7초
            frame = np.full((240, 320, 3), fi % 255, dtype=np.uint8)
            vw.write(frame)
        vw.release()
        chk("합성 영상 생성", os.path.isfile(vpath), "size=%d" % os.path.getsize(vpath))
        paths, meta = extract_frames(vpath, os.path.join(tmp, "fr"))
        chk("프레임 54장 저장", meta["saved_n"] == 54, str(meta))
        chk("640×480 로 축소", cv2.imread(paths[0], cv2.IMREAD_COLOR).shape[:2] == (480, 640),
            str(cv2.imread(paths[0], cv2.IMREAD_COLOR).shape[:2]))
        chk("파일 크기 > 0", all(os.path.getsize(p) > 0 for p in paths))

    print("[V6] mock 백엔드 엔드투엔드 → predictions.csv")
    cond = os.path.join(tmp, "conditions.csv")
    with io.open(cond, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "pid", "session", "trial", "hand", "task", "condition",
                    "injection", "r_seed", "video", "n_numbers", "held", "q_pass",
                    "q_reasons", "T_s", "v_" + K1_METRIC, "v_" + K2_METRIC,
                    "inject_notes", "prompt_path"])
        for cond_name, k1v, k2v in (("A1", "", ""), ("A2", "97.8", "7947"),
                                    ("A3", "97.8", ""), ("A4", "97.8", ""), ("R", "", "7947")):
            w.writerow(["k_%s" % cond_name, "S01", "sess", "Trial #1", "Right",
                        "Task 1: 맨손", cond_name, "none", "20260922", vpath,
                        "2", "", "1", "", "7.89", k1v, k2v, "", "prompts/x.txt"])
    rows, manifest, n_fail = run_all(cond, os.path.join(tmp, "out"), backend="mock")
    chk("행 5개 생성", len(rows) == 5, "got %d" % len(rows))
    by = {r["condition"]: r for r in rows}
    chk("trial_id 규칙 적용", by["A2"]["trial_id"] == "S01__Right__T1__t1",
        by["A2"]["trial_id"])
    chk("A2 는 K1·K2 모두 제공", by["A2"]["k1_provided"] == 1 and by["A2"]["k2_provided"] == 1)
    chk("A1 은 수치 없음", by["A1"]["k1_provided"] == 0 and by["A1"]["k2_provided"] == 0)
    chk("A3 은 K1만 제공", by["A3"]["k1_provided"] == 1 and by["A3"]["k2_provided"] == 0)
    chk("R 은 K2만 제공", by["R"]["k1_provided"] == 0 and by["R"]["k2_provided"] == 1)
    chk("mock 점수 0..3", all(r["predicted_score"] in (0, 1, 2, 3) for r in rows),
        str([r["predicted_score"] for r in rows]))
    chk("mock 표시가 rationale 에 있음",
        all(MOCK_MARK in r["rationale"] for r in rows))
    chk("output_status == ok", all(r["output_status"] == "ok" for r in rows))
    pp = os.path.join(tmp, "out", "predictions_MOCK.csv")
    write_predictions(rows, pp)
    chk("predictions.csv 저장", os.path.isfile(pp) and os.path.getsize(pp) > 0)

    print("[V7] dry 백엔드 (모델 호출 없음)")
    rows_d, man_d, nf_d = run_all(cond, os.path.join(tmp, "out_dry"), backend="dry", limit=2)
    chk("dry 는 점수 없음(parse_failed)", all(r["predicted_score"] == "" for r in rows_d))
    chk("dry 는 실패로 계수", nf_d == 2, "n_fail=%d" % nf_d)
    chk("manifest 에 프레임 수 기록", man_d[0]["n_frames"] == 54, str(man_d[0]["n_frames"]))

    print("[V8] 채점시트 → reference.csv")
    sheet = os.path.join(tmp, "score_sheet.csv")
    with io.open(sheet, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["participant_id", "side", "task", "phase", "trial_index",
                    "score", "rater"])
        w.writerow(["S01", "Right", "Task 1: 맨손", "practice", "1", "3", "T"])
        w.writerow(["S01", "Right", "Task 1: 맨손", "main", "1", "2", "T"])
        w.writerow(["S01", "Right", "Task 1: 맨손", "main", "2", "1", "T"])
    rp, n = scores_to_reference(sheet, os.path.join(tmp, "ref"))
    chk("연습 1건 제외 → 2행", n == 2, "n=%d" % n)
    with io.open(rp, encoding="utf-8-sig", newline="") as f:
        got = list(csv.DictReader(f))
    chk("trial_id 가 conditions 규칙과 일치", got[0]["trial_id"] == "S01__Right__T1__t1",
        got[0]["trial_id"])
    chk("점수 보존", got[0]["therapist_score"] == "2" and got[1]["therapist_score"] == "1")

    print("[V9] analysis_harness 와 연결")
    import subprocess
    ah = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "analysis", "analysis_harness.py")
    refs_csv = os.path.join(tmp, "ref2")
    scores_to_reference(sheet, refs_csv)
    r = subprocess.run([sys.executable, ah, "--predictions", pp,
                        "--reference", os.path.join(refs_csv, "reference.csv"),
                        "--out", os.path.join(tmp, "res", "per_patient_mae.csv")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    sout = r.stdout or ""
    chk("analysis_harness 가 오류 없이 실행", r.returncode == 0,
        (r.stderr or "")[-200:] if r.returncode else "")
    if r.returncode == 0:
        chk("보고서에 PR-1 포함", "PR-1" in sout, "stdout %d자" % len(sout))
        chk("보류율 표가 계산됨", "≥1개 보류율" in sout)
        chk("PR-1 배선 표기 확인", "MAE(A2) − MAE(A3)" in sout)

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "vlm_oracle.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("[saved] %s" % out)
    shutil.rmtree(tmp, ignore_errors=True)
    return ok_all


# ===========================================================================
# CLI
# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--conditions", help="conditions.csv 경로")
    ap.add_argument("--out", default="vlm_run_out")
    ap.add_argument("--backend", default="dry", choices=["dry", "mock", "qwen"])
    ap.add_argument("--model", default="Qwen/Qwen2.5-VL-72B-Instruct")
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--limit", type=int, help="앞 N행만 (스모크 테스트)")
    ap.add_argument("--run", type=int, default=1, help="1=주결과, 2=반복 안정성")
    ap.add_argument("--scores-to-reference", help="채점시트 CSV → reference.csv")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest() else 1)

    if a.scores_to_reference:
        p, n = scores_to_reference(a.scores_to_reference, a.out)
        print("연습 제외 후 %d행 → %s" % (n, p))
        return

    if not a.conditions:
        print(__doc__)
        return

    print("백엔드: %s%s" % (a.backend,
                          "  ⚠️ mock 은 모델 출력이 아니다" if a.backend == "mock" else ""))
    rows, manifest, n_fail = run_all(
        a.conditions, a.out, backend=a.backend, limit=a.limit, run_idx=a.run,
        model_id=a.model, max_new_tokens=a.max_new_tokens)

    name = "predictions_MOCK.csv" if a.backend == "mock" else "predictions.csv"
    pp = os.path.join(a.out, name)
    write_predictions(rows, pp)
    with io.open(os.path.join(a.out, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"backend": a.backend, "model": a.model if a.backend == "qwen" else None,
                   "conditions": os.path.abspath(a.conditions),
                   "n_rows": len(rows), "n_fail": n_fail,
                   "frame_rule": {"head_sec": HEAD_SEC, "head_hz": HEAD_HZ,
                                  "tail_hz": TAIL_HZ, "cap": FRAME_CAP,
                                  "size": [FRAME_W, FRAME_H]},
                   "manifest": manifest}, f, ensure_ascii=False, indent=2)
    print("")
    print("행 %d개 / 출력 실패 %d개 → %s" % (len(rows), n_fail, pp))
    print("manifest → %s" % os.path.join(a.out, "run_manifest.json"))
    if a.backend == "mock":
        print("")
        print("⚠️ **mock 결과는 과학적 결과가 아니다.** 배선 검증 전용. 논문 인용 금지.")
        print("   실제 실행은 --backend qwen (GPU·모델 필요).")
    if n_fail and a.backend != "dry":
        print("⚠️ 출력 실패 %d건은 analysis_harness 에서 '손실=3'으로 처리된다." % n_fail)


if __name__ == "__main__":
    main()

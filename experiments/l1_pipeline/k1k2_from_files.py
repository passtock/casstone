# -*- coding: utf-8 -*-
"""
L1 파이프라인 — 실제 파일 입력판 (v6 프로토콜 §6·§8 실행기)
=============================================================

`k1k2_reference.py`(합성 오라클)의 **실데이터 입력 버전**이다.
세션 폴더를 읽어 시행별 K1·K2·Q·T를 계산하고 L2 JSON을 쓴다.
**치구 135기록과 비장애인/장애인 촬영에 바로 쓸 수 있다.**

입력 구조 (프로토콜 §6)
-----------------------
data/H01/
  meta.json                            # intrinsics·fps·해상도
  L1_track/H01_T1_t01_landmarks.csv    # 프레임별 랜드마크
  L0_raw/H01_T1_t01_depth/*.png        # 16-bit, 값 = depth(mm)
출력
  L2_metric/H01_T1_t01.json            # K1·K2·Q·T + 사용가능 판정

landmarks CSV 헤더
------------------
frame,t_s,thumb_u,thumb_v,index_u,index_v,wrist_u,wrist_v,occlusion_state,edge_mixing_suspect
- 랜드마크 없음 = 빈 칸
- occlusion_state ∈ visible / partially_occluded / not_assessable / (빈칸)
- edge_mixing_suspect ∈ 0 / 1

⚠️ 이 스크립트는 **계산기**다. 파이프라인 자체의 정당성은 k1k2_reference.py의
   오라클(T1~T6)로 검증되어 있고, 이 스크립트의 **파일 I/O 경로**는
   --selftest로 검증한다.

실행:
  python experiments/l1_pipeline/k1k2_from_files.py --selftest
  python experiments/l1_pipeline/k1k2_from_files.py --session data/H01
  python experiments/l1_pipeline/k1k2_from_files.py --session data/H01 --q1-min 0.7
"""

import argparse
import csv
import glob
import io
import json
import math
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import numpy as np
    import cv2
    _HAVE_CV = True
except Exception:
    _HAVE_CV = False

WRIST, THUMB_TIP, INDEX_FINGER_TIP = 0, 4, 8

# --- 프로토콜 §8 동결 파라미터 ---------------------------------------------
WINDOW_K = 5
MIN_VALID_FRAC = 0.5
MAX_GAP_S = 0.1            # K2 계산 시 프레임 간격 상한
# 🔴 V-1 (2026-09-25) — **dt 하한이 없으면 속도가 수십 배 증폭된다.**
#    실측(20260915 Trial #1 Right): 인접행 dt가 실제 프레임 간격(59.1 ms)의
#    **1/34인 1.747 ms**까지 작아져 **PV = 7.947 m/s** 라는 불가능한 값이 나왔다.
#    상한(MAX_GAP_S)만으로는 못 막는다 — 하한이 필요하다.
#    → dt_min 미만 쌍은 **계산에서 제외**하고 그 수를 L2 JSON에 기록한다.
#    dt_min 기본값 = 해당 시행 중앙 dt의 절반(DT_MIN_AUTO_DIVISOR). CLI --dt-min 으로 고정.
DT_MIN_AUTO_DIVISOR = 2.0
HAND_DIST_LO_MM = 60.0
HAND_DIST_HI_MM = 230.0

# ✅ Q1 = 유효 depth 비율 **하한**. 2026-09-30 확정: **0.3** (사용자 결정).
#    근거: 파일럿(20260915) 유효 depth 비율 **0–63%, 중앙값 ≈0.30** → 0.7은 전부 탈락시킴.
#    ⚠️ 이 파일럿 값은 원시 depth 미저장(D-16) 상태의 파생값이라 과소추정일 수 있다.
#    → 새 파이프라인 치구·개발군 분포가 크게 다르면 **본평가 전 동결 회의에서 1회 조정**, 이후 변경 금지.
Q1_MIN_DEFAULT = 0.3

Q2_MAX_GAP_S = 0.3         # 초과 시 보류
Q3_MIN_SAMPLES = 50        # 미만 시 보류
Q4_MAX_EDGE_FRAC = 0.5     # 초과 시 보류
Q5_MAX_NA_FRAC = 0.5       # 못 봄 비율. ⚠️ 2026-09-30: 기본은 **게이트에 넣지 않음**
                           #    (사람 프레임별 주석 = 현장 비현실적). 별도 검증 지표로 기록.


# ===========================================================================
# 1. 입력 읽기
# ===========================================================================
def load_meta(session_dir):
    with io.open(os.path.join(session_dir, "meta.json"), encoding="utf-8") as f:
        return json.load(f)


def read_landmarks(path):
    """CSV -> 레코드 리스트. 반환: [{'frame','t_s','uv':{pt:uv|None}, 'occ','edge'}]"""
    recs = []
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            def num(k):
                v = (row.get(k) or "").strip()
                if v == "":
                    return None
                try:
                    return float(v)
                except ValueError:
                    return None
            uv = {}
            for key, name in (("thumb", THUMB_TIP), ("index", INDEX_FINGER_TIP),
                              ("wrist", WRIST)):
                u, v = num(key + "_u"), num(key + "_v")
                uv[name] = (int(round(u)), int(round(v))) if (u is not None and v is not None) else None
            edge = (row.get("edge_mixing_suspect") or "").strip()
            recs.append({
                "frame": int(float(row["frame"])),
                "t_s": num("t_s"),
                "uv": uv,
                "occ": (row.get("occlusion_state") or "").strip(),
                "edge": 1 if edge in ("1", "true", "True") else 0,
            })
    return recs


def _imwrite16(path, arr):
    """16비트 깊이 PNG 저장.

    🚨 왜 cv2.imwrite를 직접 안 쓰는가:
    OpenCV(Windows)는 **비ASCII 경로에서 조용히 False를 반환**한다.
    우리 작업 폴더가 `C:\\Users\\...\\바탕 화면\\...` 이므로
    cv2.imwrite를 쓰면 **깊이 프레임이 전부 저장되지 않는다**(CSV만 남아 원인 파악이 어렵다).
    → imencode + numpy.tofile 을 쓴다. 실패하면 예외를 올린다.
    """
    ok, buf = cv2.imencode(".png", arr)
    if not ok:
        raise RuntimeError("PNG 인코딩 실패: %s" % path)
    buf.tofile(path)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise RuntimeError("깊이 PNG 저장 실패(경로 문제): %s" % path)
    return True


def _imread16(path):
    """16비트 깊이 PNG 읽기 (비ASCII 경로 안전)."""
    if not os.path.exists(path):
        return None
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except Exception:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)


class DepthSeq:
    """L0_raw/<trial>_depth/*.png 를 프레임 번호로 조회."""

    def __init__(self, folder, depth_scale=1.0):
        self.folder = folder
        self.scale = depth_scale
        self.cache = {}
        self.files = {}
        for p in glob.glob(os.path.join(folder, "*.png")):
            stem = os.path.splitext(os.path.basename(p))[0]
            try:
                self.files[int(stem)] = p
            except ValueError:
                continue

    def get(self, frame):
        if frame not in self.files:
            return None
        if frame in self.cache:
            return self.cache[frame]
        raw = _imread16(self.files[frame])
        if raw is None:
            return None
        if raw.ndim == 3:
            raw = raw[:, :, 0]
        arr = raw.astype(np.float64) * self.scale
        arr[arr <= 0] = 0.0
        self.cache[frame] = arr
        return arr


# ===========================================================================
# 2. 기하 계산 (k1k2_reference.py와 동일 규칙)
# ===========================================================================
def median_window_np(arr, u, v, k=WINDOW_K, min_frac=MIN_VALID_FRAC):
    h, w = arr.shape
    half = k // 2
    if u < 0 or v < 0 or u >= w or v >= h:
        return None, 0.0
    v0, v1 = max(0, v - half), min(h, v + half + 1)
    u0, u1 = max(0, u - half), min(w, u + half + 1)
    patch = arr[v0:v1, u0:u1]
    valid = patch[patch > 0]
    frac = patch.size and (valid.size / float(k * k))
    if frac < min_frac or valid.size == 0:
        return None, frac
    return float(np.median(valid)), frac


def backproject(u, v, d_mm, intr):
    return ((u - intr["cx"]) * d_mm / intr["fx"],
            (v - intr["cy"]) * d_mm / intr["fy"], d_mm)


def dist3(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def p95(xs):
    if not xs:
        return None
    s = sorted(xs)
    k = 0.95 * (len(s) - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def surface_point(arr, uv, intr):
    if uv is None or arr is None:
        return None, "no_landmark"
    d, frac = median_window_np(arr, uv[0], uv[1])
    if d is None:
        return None, "no_valid_depth(%.2f)" % frac
    return backproject(uv[0], uv[1], d, intr), "ok"


def hand_consistency(wrist_pt, tip_pt):
    if wrist_pt is None or tip_pt is None:
        return False, None
    dd = dist3(wrist_pt, tip_pt)
    return (HAND_DIST_LO_MM <= dd <= HAND_DIST_HI_MM), dd


# ===========================================================================
# 3. 시행 처리
# ===========================================================================
def process_trial(session_dir, meta, trial_id, depth_scale=1.0, dt_min=None):
    lm_path = os.path.join(session_dir, "L1_track", trial_id + "_landmarks.csv")
    depth_folder = os.path.join(session_dir, "L0_raw", trial_id + "_depth")
    recs = read_landmarks(lm_path)
    seq = DepthSeq(depth_folder, depth_scale) if _HAVE_CV else None
    intr = meta

    pts = []            # (t_s, wrist|None, thumb|None, index|None, reason dict, edge, occ)
    counts = {}
    for r in recs:
        arr = seq.get(r["frame"]) if seq else None
        wp, wr = surface_point(arr, r["uv"][WRIST], intr)
        tp, tr = surface_point(arr, r["uv"][THUMB_TIP], intr)
        ip, ir = surface_point(arr, r["uv"][INDEX_FINGER_TIP], intr)
        for nm, rs in ((WRIST, wr), (THUMB_TIP, tr), (INDEX_FINGER_TIP, ir)):
            counts[rs.split("(")[0]] = counts.get(rs.split("(")[0], 0) + 1
        for nm, p, rs in ((THUMB_TIP, tp, tr), (INDEX_FINGER_TIP, ip, ir)):
            ok, dd = hand_consistency(wp, p)
            if not ok and p is not None:
                counts["hand_consistency_fail"] = counts.get("hand_consistency_fail", 0) + 1
                if nm == THUMB_TIP:
                    tp, tr = None, "hand_consistency_fail(%.0fmm)" % (dd or -1)
                else:
                    ip, ir = None, "hand_consistency_fail(%.0fmm)" % (dd or -1)
        pts.append({"t": r["t_s"], "wrist": wp, "thumb": tp, "index": ip,
                    "edge": r["edge"], "occ": r["occ"]})

    # --- 관찰 구간 T ---
    ts = [p["t"] for p in pts if p["t"] is not None]
    T = (max(ts) - min(ts)) if len(ts) >= 2 else 0.0

    # --- K1 (엄지-검지) ---
    k1_vals, k1_mask = [], []
    for p in pts:
        good = p["thumb"] is not None and p["index"] is not None
        k1_mask.append(good)
        if good:
            k1_vals.append(dist3(p["thumb"], p["index"]))
    k1 = p95(k1_vals)

    # --- K2 (손목 속도) — dt 하한 필수 (V-1) ---
    _dts = []
    for _i in range(1, len(pts)):
        _a, _b = pts[_i - 1], pts[_i]
        if (_a["wrist"] is not None and _b["wrist"] is not None
                and _a["t"] is not None and _b["t"] is not None):
            _d = _b["t"] - _a["t"]
            if _d > 0:
                _dts.append(_d)
    if dt_min is None:
        dt_min_used = (float(np.median(_dts)) / DT_MIN_AUTO_DIVISOR) if _dts else 0.0
    else:
        dt_min_used = float(dt_min)

    k2_vals, k2_pairs, prev = [], 0, None
    n_excl_small, n_excl_large = 0, 0
    for p in pts:
        if p["wrist"] is None:
            prev = None
            continue
        if prev is not None and p["t"] is not None and prev[1] is not None:
            dt = p["t"] - prev[1]
            if dt > MAX_GAP_S:
                n_excl_large += 1
            elif dt <= 0:
                pass
            elif dt < dt_min_used:
                n_excl_small += 1          # 🔴 V-1: 하한 미만 → 제외
            else:
                k2_vals.append(dist3(p["wrist"], prev[0]) / dt)
                k2_pairs += 1
        prev = (p["wrist"], p["t"])
    k2 = p95(k2_vals)

    # --- Q ---
    n = len(pts)
    n_pairs_valid = sum(k1_mask)
    n_points_total = 3 * n
    n_points_valid = 0
    for p in pts:
        n_points_valid += (1 if p["wrist"] is not None else 0) \
            + (1 if p["thumb"] is not None else 0) \
            + (1 if p["index"] is not None else 0)
    q1_pair = (n_pairs_valid / float(n)) if n else 0.0
    q1_pt = (n_points_valid / float(n_points_total)) if n_points_total else 0.0
    max_gap = _max_gap_s(pts, k1_mask)
    n_edge = sum(p["edge"] for p in pts)
    n_na = sum(1 for p in pts if p["occ"] == "not_assessable")
    n_blank = sum(1 for p in pts if p["occ"] == "")
    q = {
        "q1_pair_valid_ratio": round(q1_pair, 4),
        "q1_point_valid_ratio": round(q1_pt, 4),
        "q2_max_gap_s": round(max_gap, 4),
        "q3_valid_samples_k1": len(k1_vals),
        "q3_valid_samples_k2": k2_pairs,
        "q4_edge_mixing_frac": round(n_edge / float(n), 4) if n else 0.0,
        "q5_not_assessable_frac": round(n_na / float(n), 4) if n else 0.0,
        "q5_blank_frac": round(n_blank / float(n), 4) if n else 0.0,
        "dt_min_used_s": round(dt_min_used, 6),
        "n_pairs_excluded_dt_small": n_excl_small,
        "n_pairs_excluded_dt_large": n_excl_large,
    }
    return {"trial_id": trial_id, "task": trial_id.split("_")[1] if "_" in trial_id else "",
            "observation_window_s": round(T, 4),
            "k1_thumb_index_surface_p95_mm": None if k1 is None else round(k1, 4),
            "k2_wrist_surface_speed_p95_mm_s": None if k2 is None else round(k2, 4),
            "t": {"n_frames": n, "counts": counts},
            "q": q}


def _max_gap_s(pts, mask):
    """mask가 False인 구간의 최대 시간 길이(초)."""
    best, start = 0.0, None
    for p, good in zip(pts, mask):
        if not good and start is None:
            start = p["t"]
        elif good and start is not None:
            if p["t"] is not None and start is not None:
                best = max(best, p["t"] - start)
            start = None
    if start is not None and pts and pts[-1]["t"] is not None:
        best = max(best, pts[-1]["t"] - start)
    return best


def apply_q_rules(rec, q1_min=0.0, use_q5=False):
    """프로토콜 §8의 Q 규칙으로 사용가능/보류를 판정한다.

    ⚠️ 2026-09-30 재설계: **A3의 주 게이트는 자동 검사만**(Q1~Q4 + 손-일관성).
    **Q5는 사람 주석(프레임별 '못 봄')**이므로 **기본적으로 게이트에 넣지 않는다**(`use_q5=False`).
    대신 Q5는 **시행 단위 검증 지표**로 별도 기록한다(`q5_verdict`).
    근거: 사람이 프레임별로 일일이 체크하는 것은 현장에서 비현실적이며,
    A3를 자동으로 유지해야 "자동 선별"로 주장할 수 있다(계획서 §7.3).
    """
    q = rec["q"]
    reasons = []
    if q["q1_pair_valid_ratio"] < q1_min:
        reasons.append("Q1(%.2f<%.2f)" % (q["q1_pair_valid_ratio"], q1_min))
    if q["q2_max_gap_s"] > Q2_MAX_GAP_S:
        reasons.append("Q2(gap %.2fs>%.1fs)" % (q["q2_max_gap_s"], Q2_MAX_GAP_S))
    if q["q4_edge_mixing_frac"] > Q4_MAX_EDGE_FRAC:
        reasons.append("Q4(edge %.2f)" % q["q4_edge_mixing_frac"])
    if use_q5 and q["q5_not_assessable_frac"] > Q5_MAX_NA_FRAC:
        reasons.append("Q5(NA %.2f)" % q["q5_not_assessable_frac"])
    # Q5는 게이트와 무관하게 **항상 기록** — 사람 주석 기반 검증 지표.
    _blank = q.get("q5_blank_frac", 0.0)
    if _blank >= 1.0:
        rec["q5_verdict"] = "no_annotation"          # 사람 주석이 아예 없음
    elif q["q5_not_assessable_frac"] > Q5_MAX_NA_FRAC:
        rec["q5_verdict"] = "not_assessable"
    else:
        rec["q5_verdict"] = "assessable"
    k1_ok = not reasons and q["q3_valid_samples_k1"] >= Q3_MIN_SAMPLES
    k2_ok = (not reasons) and q["q3_valid_samples_k2"] >= Q3_MIN_SAMPLES
    r_k1 = list(reasons)
    r_k2 = list(reasons)
    if q["q3_valid_samples_k1"] < Q3_MIN_SAMPLES:
        r_k1.append("Q3(%d<%d)" % (q["q3_valid_samples_k1"], Q3_MIN_SAMPLES))
    if q["q3_valid_samples_k2"] < Q3_MIN_SAMPLES:
        r_k2.append("Q3(%d<%d)" % (q["q3_valid_samples_k2"], Q3_MIN_SAMPLES))
    rec["usable"] = {"k1": bool(k1_ok), "k2": bool(k2_ok),
                     "reasons_k1": r_k1, "reasons_k2": r_k2}
    # 🔴 A2 조건은 **Q 판정과 무관하게 계산된 값**을 보여준다(계획 §6).
    #    따라서 Q 이전 원값을 별도 키로 보존한다 — A3는 Q-gated 값을 쓴다.
    #    `q_held_*` = "값이 있었지만 Q가 보류시켰다" → 이 값이 A2와 A3의 **차이 그 자체**다.
    raw_k1 = rec.get("k1_thumb_index_surface_p95_mm")
    raw_k2 = rec.get("k2_wrist_surface_speed_p95_mm_s")
    rec["k1_raw_mm"] = raw_k1
    rec["k2_raw_mm"] = raw_k2
    rec["q_held_k1"] = bool(raw_k1 is not None and not k1_ok)
    rec["q_held_k2"] = bool(raw_k2 is not None and not k2_ok)
    # 보류된 값은 null로 표시 (프로토콜 §9)
    if not k1_ok:
        rec["k1_thumb_index_surface_p95_mm"] = None
    if not k2_ok:
        rec["k2_wrist_surface_speed_p95_mm_s"] = None
    return rec


def process_session(session_dir, q1_min=Q1_MIN_DEFAULT, write=True, dt_min=None, use_q5=False):
    meta = load_meta(session_dir)
    lm_files = sorted(glob.glob(os.path.join(session_dir, "L1_track", "*_landmarks.csv")))
    out = []
    for p in lm_files:
        trial_id = os.path.basename(p).replace("_landmarks.csv", "")
        rec = process_trial(session_dir, meta, trial_id,
                            depth_scale=meta.get("depth_scale", 1.0), dt_min=dt_min)
        rec["provenance"] = {
            "session": os.path.basename(session_dir.rstrip("/\\")),
            "camera_model": meta.get("camera_model", ""),
            "fx": meta.get("fx"), "fy": meta.get("fy"),
            "cx": meta.get("cx"), "cy": meta.get("cy"),
            "fps": meta.get("fps"), "q1_min": q1_min, "use_q5": use_q5,
            "dt_min_cli": dt_min,  # None 이면 시행별 auto (중앙 dt / 2)
            "dt_rule": "V-1: dt < dt_min 쌍 제외 · dt > %.2fs 제외 · dt <= 0 제외" % MAX_GAP_S,
            "units": {"k1": "mm", "k2": "mm/s", "t": "s"},
            "pipeline": "l1_pipeline/k1k2_from_files.py",
        }
        rec = apply_q_rules(rec, q1_min, use_q5=use_q5)
        out.append(rec)
        if write:
            d = os.path.join(session_dir, "L2_metric")
            os.makedirs(d, exist_ok=True)
            with io.open(os.path.join(d, trial_id + ".json"), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
    return out, meta


# ===========================================================================
# 4. 오라클 (파일 I/O 경로 검증)
# ===========================================================================
def _write_synthetic_session(root, w=640, h=480, fx=500.0, fy=500.0, n=60,
                             z=750.0, thumb_index_mm=15.0, step_px=3.0,
                             gap_frames=(0, 0), bg_thumb_frames=(0, 0),
                             edge_frac=0.0, na_frac=0.0, fps=30.0,
                             dt_spike_frac=0.0, dt_spike_dt=0.0017):
    """합성 세션을 디스크에 쓴다.

    dt_spike_frac>0: 홀수 프레임의 t를 **직전 프레임 + dt_spike_dt** 로 덮어쓴다.
      → 실측 V-1 재현용. 일부 페어(약 frac/2 비율)의 dt가 **프레임 간격보다 훨씬 작아진다**.
      ⚠️ 단일 스파이크로는 못 잡는다 — **P95 집계가 1개 이상치를 걸러내기** 때문이다.
         실측 20260915에서는 dt<20 ms가 **22.4%** 였으므로 다수 붕괴를 재현해야 한다.
    """
    os.makedirs(os.path.join(root, "L1_track"), exist_ok=True)
    os.makedirs(os.path.join(root, "L0_raw", "SYN_T1_t01_depth"), exist_ok=True)
    mm_per_px = z / fx
    d_px = thumb_index_mm / mm_per_px              # 요구 K1을 픽셀 차이로 환산
    d_px = float(int(round(d_px)))                 # 정수 픽셀(양자화)
    eff_k1_mm = d_px * mm_per_px
    eff_k2_mm_s = step_px * mm_per_px * fps

    # 손이 화면 안에 머무는지 확인 (초과 시 오라클이 무의미해진다)
    u0, v0 = 200, 160
    assert u0 + step_px * (n - 1) + 8 < w, "합성 궤적이 프레임 폭을 벗어남"
    assert v0 + 8 < h, "합성 궤적이 프레임 높이를 벗어남"
    assert 60.0 <= (50 * mm_per_px) <= 230.0, "손목-손끝 거리가 손-일관성 범위 밖"

    meta = {"participant_id": "SYN", "group": "selftest",
            "camera_model": "SYNTHETIC", "width": w, "height": h, "fps": fps,
            "fx": fx, "fy": fy, "cx": w / 2.0, "cy": h / 2.0,
            "depth_scale": 1.0, "aligned_to": "color"}
    with io.open(os.path.join(root, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    n_edge = int(round(edge_frac * n))
    n_na = int(round(na_frac * n))
    rows = []
    for i in range(n):
        t = i / fps
        if dt_spike_frac > 0 and (i % 2 == 1) and i <= int(round(dt_spike_frac * n)):
            t = (i - 1) / fps + dt_spike_dt   # 🔴 V-1: dt 붕괴
        arr = np.full((h, w), 2400, dtype=np.uint16)          # 배경
        u = int(round(u0 + step_px * i))
        v = v0

        def disc(cu, cv_, r, d):
            y0, y1 = max(0, cv_ - r), min(h, cv_ + r + 1)
            x0, x1 = max(0, cu - r), min(w, cu + r + 1)
            if y0 >= y1 or x0 >= x1:
                return
            yy, xx = np.ogrid[y0:y1, x0:x1]
            m = (yy - cv_) ** 2 + (xx - cu) ** 2 <= r * r
            arr[y0:y1, x0:x1][m] = d

        in_gap = gap_frames[0] <= i < gap_frames[1]
        if in_gap:
            rows.append([i, "%.6f" % t, "", "", "", "", "", "", "", ""])
            _imwrite16(os.path.join(root, "L0_raw", "SYN_T1_t01_depth",
                                    "%06d.png" % i), arr)
            continue

        thumb_v = v - 50
        index_v = thumb_v + int(d_px)
        disc(u, v, 6, int(z))                       # wrist
        bg = bg_thumb_frames[0] <= i < bg_thumb_frames[1]
        disc(u, thumb_v, 4, 2400 if bg else int(z))  # thumb (배경이면 배경깊이)
        disc(u, index_v, 4, int(z))                  # index

        occ = "partially_occluded" if bg else "visible"
        if i < n_na:
            occ = "not_assessable"
        edge = 1 if i < n_edge else 0
        rows.append([i, "%.6f" % t, u, thumb_v, u, index_v, u, v, occ, edge])
        _imwrite16(os.path.join(root, "L0_raw", "SYN_T1_t01_depth",
                                "%06d.png" % i), arr)

    with io.open(os.path.join(root, "L1_track", "SYN_T1_t01_landmarks.csv"),
                 "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t_s", "thumb_u", "thumb_v", "index_u", "index_v",
                     "wrist_u", "wrist_v", "occlusion_state", "edge_mixing_suspect"])
        wr.writerows(rows)

    expected = {"k1_mm": round(eff_k1_mm, 6), "k2_mm_s": round(eff_k2_mm_s, 6),
                "n_frames": n, "n_bg": max(0, bg_thumb_frames[1] - bg_thumb_frames[0]),
                "n_edge": n_edge, "n_na": n_na,
                "gap_s": (gap_frames[1] - gap_frames[0]) / fps if gap_frames[1] > gap_frames[0] else 0.0}
    return meta, expected


def selftest():
    if not _HAVE_CV:
        print("cv2/numpy 없음 — selftest 불가"); return False
    import shutil
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest")
    if os.path.isdir(base):
        shutil.rmtree(base)
    os.makedirs(base)
    log = []
    ok_all = True

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-46s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    def run(tag, **kw):
        q1 = kw.pop("q1_min", 0.7)
        root = os.path.join(base, tag)
        os.makedirs(root)
        meta, exp = _write_synthetic_session(root, **kw)
        recs, _ = process_session(root, q1_min=q1, write=True)
        return recs[0], exp, root

    print("[S1] 정상 세션 (파일 -> JSON 전 구간)")
    r, exp, root = run("good", n=60, thumb_index_mm=15.0, step_px=3.0)
    chk("K1 == 생성기 기대값 %.2f mm" % exp["k1_mm"],
        r["k1_thumb_index_surface_p95_mm"] is not None
        and abs(r["k1_thumb_index_surface_p95_mm"] - exp["k1_mm"]) < 0.05,
        "got %s" % r["k1_thumb_index_surface_p95_mm"])
    chk("K2 == 생성기 기대값 %.1f mm/s" % exp["k2_mm_s"],
        r["k2_wrist_surface_speed_p95_mm_s"] is not None
        and abs(r["k2_wrist_surface_speed_p95_mm_s"] - exp["k2_mm_s"]) < 1.0,
        "got %s" % r["k2_wrist_surface_speed_p95_mm_s"])
    chk("K1·K2 모두 사용가능", r["usable"]["k1"] and r["usable"]["k2"], str(r["usable"]))
    chk("L2 JSON 생성", os.path.exists(os.path.join(root, "L2_metric", "SYN_T1_t01.json")))

    print("[S2] 0.4초 결측 -> Q2로 보류")
    r2, exp2, _ = run("gap", n=60, gap_frames=(20, 32))
    chk("max_gap == %.2f초" % exp2["gap_s"],
        abs(r2["q"]["q2_max_gap_s"] - exp2["gap_s"]) < 0.04,
        "got %.3f" % r2["q"]["q2_max_gap_s"])
    chk("K1 보류 + 값 null", r2["usable"]["k1"] is False
        and r2["k1_thumb_index_surface_p95_mm"] is None, str(r2["usable"]["reasons_k1"]))

    print("[S3] 유효 샘플 40개(<50) -> Q3로 보류")
    r3, exp3, _ = run("few", n=40)
    chk("K1 보류(Q3)", r3["usable"]["k1"] is False
        and any("Q3" in x for x in r3["usable"]["reasons_k1"]),
        str(r3["usable"]["reasons_k1"]))

    print("[S4] 배경에 찍힌 랜드마크 %d건 -> 손-일관성 검사" % 10)
    r4, exp4, _ = run("bg", n=60, bg_thumb_frames=(20, 30))
    chk("검출 카운트 == 10", r4["t"]["counts"].get("hand_consistency_fail", 0) == 10,
        str(r4["t"]["counts"]))

    print("[S5] edge_mixing 60%% -> Q4로 보류")
    r5, exp5, _ = run("edge", n=60, edge_frac=0.6, q1_min=0.0)
    chk("edge_frac == 0.60", abs(r5["q"]["q4_edge_mixing_frac"] - 0.6) < 0.02,
        "got %.2f" % r5["q"]["q4_edge_mixing_frac"])
    chk("K1 보류(Q4)", r5["usable"]["k1"] is False
        and any("Q4" in x for x in r5["usable"]["reasons_k1"]),
        str(r5["usable"]["reasons_k1"]))

    print("[S5b] Q 보류 시 원값 보존 (A2가 필요로 하는 계약)")
    chk("Q4 보류된 K1도 k1_raw_mm 에는 값이 남아 있음",
        r5["k1_thumb_index_surface_p95_mm"] is None and r5.get("k1_raw_mm") is not None,
        "gated=%s raw=%s" % (r5["k1_thumb_index_surface_p95_mm"], r5.get("k1_raw_mm")))
    chk("q_held_k1 플래그가 True", r5.get("q_held_k1") is True, str(r5.get("q_held_k1")))
    chk("Q2 보류 건에서도 raw 보존",
        r2["k1_thumb_index_surface_p95_mm"] is None and r2.get("k1_raw_mm") is not None,
        "raw=%s" % r2.get("k1_raw_mm"))

    print("[S6] 🔴 V-1 회귀: dt 붕괴 프레임 페어 → dt 하한이 막는가")
    phys = 3.0 * (750.0 / 500.0) * 30.0      # step_px * mm_per_px * fps = 135 mm/s
    rootA = os.path.join(base, "dt_off"); os.makedirs(rootA)
    _write_synthetic_session(rootA, n=60, step_px=3.0, fps=30.0, dt_spike_frac=0.5)
    recsA, _ = process_session(rootA, q1_min=0.0, write=True, dt_min=0.0)
    k2off = recsA[0]["k2_wrist_surface_speed_p95_mm_s"]
    rootB = os.path.join(base, "dt_on"); os.makedirs(rootB)
    _write_synthetic_session(rootB, n=60, step_px=3.0, fps=30.0, dt_spike_frac=0.5)
    recsB, _ = process_session(rootB, q1_min=0.0, write=True, dt_min=None)
    r6 = recsB[0]; k2on = r6["k2_wrist_surface_speed_p95_mm_s"]
    chk("하한 해제(dt_min=0) → K2 폭발 (>1000 mm/s, 물리 %.0f)" % phys,
        k2off is not None and k2off > 1000.0, "off=%s" % k2off)
    chk("auto 하한 → K2 폭발하지 않음 (보류(None) 또는 <300 mm/s)",
        (k2on is None) or (k2on < 300.0), "on=%s" % k2on)
    rootC = os.path.join(base, "dt_on_long"); os.makedirs(rootC)
    _write_synthetic_session(rootC, n=120, step_px=3.0, fps=30.0, dt_spike_frac=0.5)
    recsC, _ = process_session(rootC, q1_min=0.0, write=True, dt_min=None)
    r6c = recsC[0]; k2c = r6c["k2_wrist_surface_speed_p95_mm_s"]
    chk("긴 시행(n=120)에서는 K2가 보고되고 폭발 안 함 (<300)",
        k2c is not None and k2c < 300.0, "long=%s" % k2c)
    chk("제외된 dt<min 쌍 수 기록 (>5)",
        (r6["q"].get("n_pairs_excluded_dt_small") or 0) > 5,
        "got %s" % r6["q"].get("n_pairs_excluded_dt_small"))
    chk("dt_min_used 기록",
        bool(r6["q"].get("dt_min_used_s")) and r6["q"]["dt_min_used_s"] > 0,
        str(r6["q"].get("dt_min_used_s")))

    print("")
    print("[S7] 동결값 확인")
    chk("Q1 동결값 == 0.3 (§7.3)", Q1_MIN_DEFAULT == 0.3, str(Q1_MIN_DEFAULT))
    chk("Q2=0.3s · Q3=50 · Q4=0.5s", (Q2_MAX_GAP_S, Q3_MIN_SAMPLES, Q4_MAX_EDGE_FRAC) == (0.3, 50, 0.5))

    print("[S7b] Q5 재설계: 기본은 자동 게이트(Q1~Q4), Q5는 별도 검증 지표")

    def _rq(na, blank):
        return {"q": {"q1_pair_valid_ratio": 1.0, "q2_max_gap_s": 0.0,
                      "q3_valid_samples_k1": 100, "q3_valid_samples_k2": 100,
                      "q4_edge_mixing_frac": 0.0,
                      "q5_not_assessable_frac": na, "q5_blank_frac": blank}}

    r5a = apply_q_rules(_rq(0.9, 0.0))
    chk("기본(use_q5=False): 90% 못 봄이어도 게이트 통과(자동)",
        r5a["usable"]["k1"] is True, str(r5a["usable"]["reasons_k1"]))
    chk("q5_verdict = not_assessable 로 별도 기록", r5a["q5_verdict"] == "not_assessable")
    r5b = apply_q_rules(_rq(0.9, 0.0), use_q5=True)
    chk("use_q5=True 이면 Q5로 보류(옵션)", r5b["usable"]["k1"] is False)
    r5c = apply_q_rules(_rq(0.0, 1.0))
    chk("주석이 비면 q5_verdict = no_annotation", r5c["q5_verdict"] == "no_annotation")
    r5d = apply_q_rules(_rq(0.1, 0.0))
    chk("일부만 못 봄이면 assessable", r5d["q5_verdict"] == "assessable")

    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    print("※ 합성 데이터다. 실제 카메라·손 성능이 아니다.")
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "l1_files_oracle.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("[saved] %s" % out)
    return ok_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--session")
    ap.add_argument("--q1-min", type=float, default=Q1_MIN_DEFAULT,
                    help="Q1 유효 depth 비율 하한 (동결값 %.2f)" % Q1_MIN_DEFAULT)
    ap.add_argument("--use-q5", action="store_true",
                    help="Q5(사람 주석)를 게이트에 포함(기본 False = 자동 게이트만)")
    ap.add_argument("--dt-min", type=float, default=None,
                    help="K2 dt 하한(s). 미지정 시 시행별 중앙 dt/2 자동 (V-1)")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.session:
        print(__doc__); return
    recs, meta = process_session(a.session, q1_min=a.q1_min, write=True,
                                 dt_min=a.dt_min, use_q5=a.use_q5)
    for r in recs:
        q = r.get("q", {})
        print("%-16s K1=%s  K2=%s  usable=%s/%s  dt_min=%ss  제외(dt<min)=%s" % (
            r["trial_id"],
            r["k1_thumb_index_surface_p95_mm"], r["k2_wrist_surface_speed_p95_mm_s"],
            r["usable"]["k1"], r["usable"]["k2"],
            q.get("dt_min_used_s"), q.get("n_pairs_excluded_dt_small")))
    print("\n[%d trials] L2_metric/ 에 JSON 기록" % len(recs))


if __name__ == "__main__":
    main()

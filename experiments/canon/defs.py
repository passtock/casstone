# -*- coding: utf-8 -*-
"""정본 정의 (canonical) — 계획서 v13.2 기준. 신규 파일(기존 코드 미수정).

존재 이유
  2026-10-02 독립 검토에서 **내 v15 코드의 엄지 관절 정의가 계획서와 다름**이 확인됐다.
  계획서 §7.1: "엄지는 CMC–MCP–IP와 MCP–IP–TIP의 2개"
      → CMC=1, MCP=2, IP=3, TIP=4  ⇒  (1,2,3) 과 (2,3,4)
  내 v15 코드와 v14/29차 코드는 (0,1,2)·(1,2,3) 을 썼다(= 손목–CMC–MCP / CMC–MCP–IP). **오류였다.**
  이 파일이 **앞으로 유일한 정의 출처**다. 재현 코드는 여기서만 가져다 쓴다.

범위
  · 계획서 §7.1(지표 정의) 과 §8.2(분절·손-일관성·설정표) 의 수치를 그대로 옮긴다.
  · 여기서는 **정의만** 둔다. 파일럿 자료 재분석은 하지 않는다(사용자 지시 2026-10-02).

출처: capstone/실험계획서_v13.2_최종본.md 363·366·480·482·494·502행, 세 설정표
"""
from __future__ import annotations

# ── 랜드마크 (MediaPipe Hands 21점) ───────────────────────────────────────────
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_TIP, RING_TIP, PINKY_TIP = 12, 16, 20

# ── §7.1 굴곡각 14개 (⚠ 엄지는 (1,2,3)·(2,3,4) 다. (0,1,2)가 아니다) ──────────
FLEX14 = {
    "Thumb_CMC_MCP_IP": (1, 2, 3),      # 엄지 CMC–MCP–IP
    "Thumb_MCP_IP_TIP": (2, 3, 4),      # 엄지 MCP–IP–TIP
    "Index_MCP": (0, 5, 6),             # 손목–MCP–PIP
    "Index_PIP": (5, 6, 7),             # MCP–PIP–DIP
    "Index_DIP": (6, 7, 8),             # PIP–DIP–TIP
    "Middle_MCP": (0, 9, 10),
    "Middle_PIP": (9, 10, 11),
    "Middle_DIP": (10, 11, 12),
    "Ring_MCP": (0, 13, 14),
    "Ring_PIP": (13, 14, 15),
    "Ring_DIP": (14, 15, 16),
    "Pinky_MCP": (0, 17, 18),
    "Pinky_PIP": (17, 18, 19),
    "Pinky_DIP": (18, 19, 20),
}
FLEX_NAMES = tuple(FLEX14)                      # 14개
FINGER_OF_FLEX = {
    "Thumb_CMC_MCP_IP": "Thumb", "Thumb_MCP_IP_TIP": "Thumb",
    "Index_MCP": "Index", "Index_PIP": "Index", "Index_DIP": "Index",
    "Middle_MCP": "Middle", "Middle_PIP": "Middle", "Middle_DIP": "Middle",
    "Ring_MCP": "Ring", "Ring_PIP": "Ring", "Ring_DIP": "Ring",
    "Pinky_MCP": "Pinky", "Pinky_PIP": "Pinky", "Pinky_DIP": "Pinky",
}
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")

# ── §8.2 분절 15개 ──────────────────────────────────────────────────────────
SEGMENTS_15 = [
    (1, 2), (2, 3), (3, 4),                 # 엄지
    (5, 6), (6, 7), (7, 8),                 # 검지
    (9, 10), (10, 11), (11, 12),            # 중지
    (13, 14), (14, 15), (15, 16),           # 약지
    (17, 18), (18, 19), (19, 20),           # 소지
]
SEGMENTS_TI6 = SEGMENTS_15[:6]              # D_TI_max 에는 엄지·검지 6분절
FINGER_OF_SEG = {}
for s in [(1, 2), (2, 3), (3, 4)]:
    FINGER_OF_SEG[s] = "Thumb"
for name, segs in (("Index", [(5, 6), (6, 7), (7, 8)]),
                   ("Middle", [(9, 10), (10, 11), (11, 12)]),
                   ("Ring", [(13, 14), (14, 15), (15, 16)]),
                   ("Pinky", [(17, 18), (18, 19), (19, 20)])):
    for s in segs:
        FINGER_OF_SEG[s] = name

# ── §8.2 지표별 랜드마크 쌍 ─────────────────────────────────────────────────
D_TI_MAX_PAIR = (THUMB_TIP, INDEX_TIP)      # MP 4–8 거리 ×1000, 시행 최댓값(상한 캡 없음)
HAND_CONSISTENCY_ANCHOR = WRIST             # 손목(0)
HAND_CONSISTENCY_TIPS = (THUMB_TIP, INDEX_TIP, MIDDLE_TIP)   # 4 · 8 · 12
HAND_CONSISTENCY_MM = (60.0, 230.0)         # [60, 230] mm

# ── §8.2 분절 규칙 파라미터 ─────────────────────────────────────────────────
SEG_TOL_FLOOR = 0.20            # tol_seg = max(0.20, K_tol × s_seg)
SEG_K_TOL = 3.0
SEG_MIN_AGREE = 2               # "2개 이상 동시 위반" 프레임만 불일치로 센다
SEG_BASELINE_FRAMES_MIN = 8     # 시행 전 정지 2초의 유효 프레임 최소
SEG_BASELINE_WINDOW_S = 2.0     # §6.3.1 정지 구간

# ── §8.2 시간·추적 규칙 ─────────────────────────────────────────────────────
DT_REF_SCOPE = "session"        # 세션당 1회 계산해 전 지표 공통 적용
GAP_RATIO_MAX = 2.5             # 기본 설정
GAP_S_MAX = 0.20                # 세 설정 공통
MAX_MISSED_RUN_DT = 5           # 연속 미검출 ≤ 5 × dt_ref
MIN_VALID_FRAMES = 8

# ── §8.2 세 설정표 (느슨함 / 기본 / 엄격함) ─────────────────────────────────
SETTINGS = {
    "loose":  {"hand_valid_min": 0.70, "seg_dev_max": 0.40, "gap_ratio_max": 3.0,
               "acquire_miss_max": 0.20, "interp_max": 0.15, "td_baseline_sd_mm": 15.0},
    "default": {"hand_valid_min": 0.80, "seg_dev_max": 0.30, "gap_ratio_max": 2.5,
                "acquire_miss_max": 0.15, "interp_max": 0.10, "td_baseline_sd_mm": 10.0},
    "strict": {"hand_valid_min": 0.90, "seg_dev_max": 0.20, "gap_ratio_max": 2.0,
               "acquire_miss_max": 0.10, "interp_max": 0.05, "td_baseline_sd_mm": 5.0},
}
DEFAULT_SETTING = "default"
FPS_FLOOR_HZ = 12.5             # §8.2 획득률 하한 (세 설정 동일)
COMMON_FS_HZ = 30.0             # §7.2 공통 격자
COMMON_FC_HZ = 10.0

# ── ★ §8.2 분절 규칙의 지위: 2026-10-02 사용자 지시로 '진단값'으로 격하 ──────
#   계획서 v13.2는 이 규칙을 손 M1·M2 게이트의 한 조건으로 두었다.
#   그러나 ① 미주입 파일럿에서 위반비율 중앙 0.878 → 90백분위 상한이 0.996으로 퇴화하고,
#         ② 손끝 한 점 오류는 "2개 이상 동시 위반" 조건에서 원리적으로 검출되지 않으며
#            (§8.2 '알려진 사각지대' — 계획서가 이미 명시. 손-일관성 4·8·12가 보완),
#         ③ 정지 2초 기준선이 없는 자료에서는 8/8 `segment_baseline_unavailable` 이었다.
#   → 사용자 결정(2026-10-02): 게이트에서 제외하고 **참고용 진단값으로만 기록**한다.
SEGMENT_RULE_IS_GATE = False

# 손 M1·M2 게이트를 구성하는 조건 (분절 규칙 제외 후)
HAND_GATE_CONDITIONS = (
    "hand_track_rate",        # 대상 손 추적률 ≥ hand_valid_min
    "max_missed_run",         # 연속 미검출 ≤ MAX_MISSED_RUN_DT × dt_ref
    "min_valid_frames",       # 실제 유효 프레임 ≥ MIN_VALID_FRAMES
    "hand_consistency",       # 0→4 / 0→8 / 0→12 ∈ [60,230] mm (프레임 무효)
)
# 진단값으로만 기록하고 판정에 쓰지 않는 항목
HAND_DIAGNOSTIC_ONLY = (
    "segment_deviation",      # 분절 불일치 비율·위반 분절 이름
    "motion_unresolved",      # 이동량 미해소 참고 표시 (§8.2: 보류 조건으로 쓰지 않음)
    "ring_pinky_tip_span",    # 약지끝(16)·소지끝(20) 이탈
)

# -*- coding: utf-8 -*-
"""
정적 치구 검증용 측정 시트 생성기 (v6 계획 §7-1)
=================================================

v5 §6.1이 요구한 "정적 거리 검증"을 실제로 돌리기 위한 CSV 시트를 만든다.

설계 (v5 §6.1 준수):
- 치구 크기 5종: 20 / 40 / 60 / 80 / 100 mm (캘리퍼로 확인한 무광 치구)
- 작업영역 3거리: near(0.65 m) / mid(0.75 m) / far(0.85 m)  ← 카메라-작업영역 거리
- 방향 3종: frontal / oblique30 / lateral
- 각 조건 3회 재배치
- 총 5 × 3 × 3 × 3 = 135 기록  ← v5가 요구한 숫자와 일치

출력:
  1) gauge_sheet_template.csv          : 빈 시트(실제 측정에 사용)
  2) gauge_sheet_DEMO_synthetic.csv    : 합성 데모(파이프라인 검증용, 절대 실측으로 인용 금지)

실행: python experiments/gauge_validation/make_gauge_sheet.py
"""

import csv
import io
import os
import random
import sys

# Windows 콘솔(cp949)에서 이모지·한글 출력 시 죽지 않도록 UTF-8로 재설정
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

random.seed(20260922)

HERE = os.path.dirname(os.path.abspath(__file__))

DISTANCES_MM = [20, 40, 60, 80, 100]        # 치구 크기
ZONES = [("near", 0.65), ("mid", 0.75), ("far", 0.85)]   # (이름, 카메라거리 m)
DIRECTIONS = ["frontal", "oblique30", "lateral"]
REPEATS = [1, 2, 3]

HEADER = [
    "record_id", "date", "operator", "session_id",
    "camera_model", "firmware", "sdk", "rgb_res", "depth_res", "fps",
    "zone", "camera_distance_m", "direction",
    "true_distance_mm", "repeat",
    "measured_mm", "valid_flag", "note",
]


def rows():
    i = 0
    for zone, cam_d in ZONES:
        for direction in DIRECTIONS:
            for true_mm in DISTANCES_MM:
                for rep in REPEATS:
                    i += 1
                    yield {
                        "record_id": "G%03d" % i,
                        "date": "",
                        "operator": "",
                        "session_id": "",
                        "camera_model": "D455",
                        "firmware": "",
                        "sdk": "",
                        "rgb_res": "1280x800",
                        "depth_res": "1280x720",
                        "fps": "30",
                        "zone": zone,
                        "camera_distance_m": cam_d,
                        "direction": direction,
                        "true_distance_mm": true_mm,
                        "repeat": rep,
                        "measured_mm": "",
                        "valid_flag": "",
                        "note": "",
                    }


def write_csv(path, recs):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in recs:
            w.writerow(r)
    print("[saved] %s  (%d rows)" % (path, len(recs)))


# ---------------------------------------------------------------------------
# 1) 빈 템플릿
# ---------------------------------------------------------------------------
template = list(rows())
write_csv(os.path.join(HERE, "gauge_sheet_template.csv"), template)

# ---------------------------------------------------------------------------
# 2) 합성 데모 (파이프라인 검증 전용)
#    - 거리에 따라 오차가 커지는 형태를 흉내낸다(깊이 오차는 거리에 비례해 커짐)
#    - 방향에 따라 오차 크기를 다르게 둔다(Scano 2020의 구역별 신뢰도 차이 흉내)
#    - 일부 행을 무효(valid_flag=0)로 만들어 무효율 계산을 검증한다
# ---------------------------------------------------------------------------
ZONE_SIGMA = {"near": 1.5, "mid": 2.5, "far": 4.0}       # mm, 카메라거리 효과
DIR_SIGMA = {"frontal": 1.0, "oblique30": 1.4, "lateral": 1.8}
ZONE_BIAS = {"near": 0.3, "mid": 0.8, "far": 1.6}        # mm, 계통 편향

demo = []
for r in template:
    r = dict(r)
    sigma = ZONE_SIGMA[r["zone"]] * DIR_SIGMA[r["direction"]]
    b = ZONE_BIAS[r["zone"]]
    val = r["true_distance_mm"] + b + random.gauss(0, sigma)
    r["measured_mm"] = round(val, 2)
    r["valid_flag"] = 1
    r["note"] = "SYNTHETIC-DEMO"
    demo.append(r)

# 무효 5건(깊이 경계 혼합 흉내)
for idx in [7, 22, 58, 91, 120]:
    demo[idx]["valid_flag"] = 0
    demo[idx]["measured_mm"] = ""
    demo[idx]["note"] = "SYNTHETIC-DEMO invalid(depth-mixing-simulated)"

write_csv(os.path.join(HERE, "gauge_sheet_DEMO_synthetic.csv"), demo)

print("")
print("행 구성 확인: 5치구 x 3거리 x 3방향 x 3반복 = %d" % (5 * 3 * 3 * 3))
print("템플릿 행 수 = %d (135여야 함)" % len(template))
assert len(template) == 135, "행 수가 135가 아님"
print("OK: 135행")
print("")
print("※ DEMO 파일은 합성이다. 실측 결과로 인용 금지.")

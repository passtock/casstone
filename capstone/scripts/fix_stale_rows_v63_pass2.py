# -*- coding: utf-8 -*-
"""2차 패치 — 계획서 §9·§13의 '코드/오라클' 서술 정정.

발견 경위(검증 패스 2회차):
- experiments/analysis/analysis_harness.py:531-533 실제 배선:
    pr1 = paired_diff(a2, a1)      # MAE(A2) - MAE(A1)
    pr2 = paired_diff(a2, a3)      # MAE(A2) - MAE(A3)
    pr3 = paired_diff(r_cond, a3)  # MAE(R)  - MAE(A3)
- experiments/results/analysis_oracle.txt 실제 로그:
    PR-1 = MAE(A2)-MAE(A1) == +2.0 PASS [2.0]
    PR-2 = MAE(A2)-MAE(A3) == +2.0 PASS [2.0]
    A3(1) - A1(1) == 0.0 (조건 미분리 감지) PASS [0.0]
- 오라클 케이스 라벨은 [A1]~[A10] (10개).

계획서는 ① 라인 번호 528-529 ② pr1 = paired_diff(a2,a3) ③ 로그 문구
'PR-1 = MAE(A2)-MAE(A3)' 와 '구 배선(A3 none - A3 none)' 을 적고 있었다 — 전부 실제와 불일치.
"""
import shutil
from pathlib import Path

PLAN = Path("outputs/research-plan-v6.md")
BACKUP = Path("outputs/03-검증/provenance/_backup_stale_fix_20260928")
BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copyfile(PLAN, BACKUP / "research-plan-v6.pre2.md")

text = PLAN.read_text(encoding="utf-8")

edits = [
    # §13 — 오라클 케이스 수
    (
        "bootstrap CI·Holm·가중 κ·혼동행렬·실패 손실·라벨 불확실. 오라클 A1~A6 ALL PASS.",
        "bootstrap CI·Holm·가중 κ·혼동행렬·실패 손실·라벨 불확실. 오라클 A1~A10 ALL PASS.",
    ),
    # §13 — 배선 설명 + 오라클 로그 인용을 실제 파일과 일치시킴
    (
        "`analysis_harness.py:528-529` 가 `pr1 = paired_diff(a2, a3)` = `MAE(A2) − MAE(A3)`, "
        "`pr2 = paired_diff(r_cond, a3)` = `MAE(R) − MAE(A3)` 를 구현한다. "
        "오염전파(bias_3u)는 **H5 기전·탐색적**으로 내려가 있다. "
        "**오라클 로그 `experiments/results/analysis_oracle.txt` 에 "
        "`PR-1 = MAE(A2)-MAE(A3) == +2.0 PASS` 와 "
        "`구 배선(A3 none - A3 none) == 0.0 (구분됨) PASS` 가 있어, 회귀도 잠겨 있다.** "
        "→ **D-12 해소 확인.**",
        "`analysis_harness.py:531-533` 이 `pr1 = paired_diff(a2, a1)` = `MAE(A2) − MAE(A1)`, "
        "`pr2 = paired_diff(a2, a3)` = `MAE(A2) − MAE(A3)`, "
        "`pr3 = paired_diff(r_cond, a3)` = `MAE(R) − MAE(A3)` 를 구현한다. "
        "오염전파(bias_3u)는 **H5 기전·탐색적**으로 내려가 있다. "
        "**오라클 로그 `experiments/results/analysis_oracle.txt` 에 "
        "`PR-1 = MAE(A2)-MAE(A1) == +2.0 PASS [2.0]`, "
        "`PR-2 = MAE(A2)-MAE(A3) == +2.0 PASS [2.0]`, "
        "`A3(1) - A1(1) == 0.0 (조건 미분리 감지) PASS [0.0]` 가 있어, 회귀도 잠겨 있다.** "
        "→ **D-12 해소 확인.** "
        "*(2026-09-28 정정: 이전 판본은 라인 528-529·`pr1 = paired_diff(a2, a3)`·"
        "로그 `PR-1 = MAE(A2)-MAE(A3)` 로 잘못 적혀 있었다 — 실제 코드/로그와 불일치.)*",
    ),
    # §9 ② — '현재 구현하고 있다'를 '해소됨'으로
    (
        "② ⚠️ **기존 코드와 재설계가 불일치한다 (결함 D-12).** "
        "`experiments/analysis/analysis_harness.py`는 **현재 “오염 전파” PR-1**"
        "(`MAE(A3,주입3u) − MAE(A3,원래)`)을 구현하고 있다.",
        "② ✅ **해소된 결함 D-12 (기존 코드–재설계 불일치).** "
        "`experiments/analysis/analysis_harness.py`는 재작성되어 "
        "**PR-1·PR-2·PR-3** 대응비교를 구현하고, "
        "구 “오염 전파”(`MAE(A3,주입3u) − MAE(A3,원래)`)는 H5(탐색적)로 내려갔다 "
        "(§13·§15.2 D-12). *(이전 판본은 “현재 구현하고 있다”고 적혀 있었다.)*",
    ),
    # §9 ③ — 오라클 케이스 수
    (
        "→ **오라클 A1~A6은 재사용 가능**(부트스트랩·Holm·가중κ는 조건 이름과 무관).",
        "→ **오라클 A1~A10은 재사용 가능**(부트스트랩·Holm·가중κ는 조건 이름과 무관).",
    ),
]

for i, (old, new) in enumerate(edits, 1):
    n = text.count(old)
    assert n == 1, f"edit#{i} 일치 {n}회: {old[:80]!r}"
    text = text.replace(old, new)

PLAN.write_text(text, encoding="utf-8")
print(f"patched research-plan-v6.md: {len(edits)} edits")
print("backup:", BACKUP / "research-plan-v6.pre2.md")

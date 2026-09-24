# -*- coding: utf-8 -*-
"""
세션 준비 도구 (v6 프로토콜 §3·§4·§6) — 주 1에 바로 사용
============================================================

두 가지를 만든다.
1) 세션 폴더 트리 + meta.json 템플릿   (프로토콜 §6)
2) 채점 시트 CSV 실물                  (프로토콜 §4, 16필드)

실행:
  python experiments/session_tools/make_session.py H01 --group healthy_dev
  python experiments/session_tools/make_session.py S07 --group stroke_main --trials 5
  python experiments/session_tools/make_session.py S07 --group stroke_main --trials 15
  python experiments/session_tools/make_session.py --list-groups

⚠️ 환자 식별정보(이름·생년월일·병록번호)를 파일명·경로에 넣지 않는다.
   ID는 S01.. / H01.. 형태만 쓴다 (데이터 거버넌스).
"""

import argparse
import csv
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

GROUPS = {
    "healthy_dev":  {"prefix": "H", "practice": 2, "default_trials": 5,
                     "note": "건강인 개발 — 파이프라인·가림 주석·Q 후보 개발"},
    "healthy_val":  {"prefix": "H", "practice": 2, "default_trials": 5,
                     "note": "건강인 독립 기술검증 — 규칙 동결 후"},
    "stroke_dev":   {"prefix": "S", "practice": 2, "default_trials": 5,
                     "note": "환자 개발 — 가림·채점 가능성, 프롬프트 동결"},
    "stroke_main":  {"prefix": "S", "practice": 2, "default_trials": 5,
                     "note": "환자 본평가 — 과제당 본 1–3회를 모델 평가에 사용"},
}

# 채점 시트 필드 (프로토콜 §4)
SCORE_FIELDS = [
    "participant_id", "side", "task", "phase", "trial_index", "score", "time_s",
    "finger_used", "pad_used", "voluntary_lift", "reached_target", "released",
    "abnormal_arm", "posture_loss", "not_assessable", "rater", "blinded", "note",
]

DIRS = [
    ("L0_raw", None),
    ("L1_track", None),
    ("L2_metric", None),
    ("L3_vlm", None),
]


def make_dirs(root):
    created = []
    for d, _ in DIRS:
        p = os.path.join(root, d)
        os.makedirs(p, exist_ok=True)
        created.append(p)
    return created


def make_meta(root, pid, group, camera="D455", trials=5):
    meta = {
        "participant_id": pid,
        "group": group,
        "group_note": GROUPS[group]["note"],
        "date": "",
        "operator": "",
        "rater": "",
        "camera_model": camera,
        "firmware": "",
        "sdk": "",
        "width": 1280, "height": 800,
        "depth_res": "1280x720",
        "fps": 30.0,
        "fx": None, "fy": None, "cx": None, "cy": None,
        "depth_scale": None,
        "aligned_to": "color",
        "preset": "",                 # left_oblique / right_oblique / frontal
        "practice_per_task": GROUPS[group]["practice"],
        "main_trials_per_task": trials,
        "task_order": "T1 practice -> T1 main -> rest2min -> T2 practice -> T2 main -> rest2min -> T1 tail -> T2 tail",
        "observation_window_rule": "manual_start_end_applied_to_all_conditions",
        "notes": "fx/fy/cx/cy/depth_scale 는 장치에서 읽어 반드시 채운다(비우면 L1 계산 불가)",
    }
    p = os.path.join(root, "meta.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return p


def make_score_sheet(root, pid, trials=5, practice=2, rater_blind=True):
    """치료사용 채점 시트. 연습 + 본 시행 행을 미리 만들어 둔다."""
    rows = []
    for task in ("T1", "T2"):
        for i in range(1, practice + 1):
            rows.append({"participant_id": pid, "side": "", "task": task,
                         "phase": "practice", "trial_index": i})
        for i in range(1, trials + 1):
            rows.append({"participant_id": pid, "side": "", "task": task,
                         "phase": "main", "trial_index": i})
    for r in rows:
        for k in SCORE_FIELDS:
            r.setdefault(k, "")
        r["rater"] = ""
        r["blinded"] = 1 if rater_blind else 0
    p = os.path.join(root, "%s_score.csv" % pid)
    with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCORE_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return p, len(rows)


def make_landmarks_template(root, pid, task, trials, practice, fps=30.0,
                            n_frames_default=None):
    """랜드마크 CSV 헤더 템플릿을 시행별로 만든다(값은 비어 있음)."""
    made = []
    d = os.path.join(root, "L1_track")
    for phase, count in (("practice", practice), ("main", trials)):
        for i in range(1, count + 1):
            tid = "%s_%s_%s%02d" % (pid, task, "p" if phase == "practice" else "t", i)
            p = os.path.join(d, tid + "_landmarks.csv")
            with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["frame", "t_s", "thumb_u", "thumb_v", "index_u",
                            "index_v", "wrist_u", "wrist_v",
                            "occlusion_state", "edge_mixing_suspect"])
                if n_frames_default:
                    for fr in range(n_frames_default):
                        w.writerow([fr, "%.6f" % (fr / fps), "", "", "", "", "", "", "", ""])
            made.append(tid)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?")
    ap.add_argument("--root", default="data")
    ap.add_argument("--group", default="healthy_dev", choices=list(GROUPS.keys()))
    ap.add_argument("--trials", type=int, default=None, help="과제당 본 시행 수 (기본 5)")
    ap.add_argument("--camera", default="D455")
    ap.add_argument("--list-groups", action="store_true")
    a = ap.parse_args()

    if a.list_groups:
        for k, v in GROUPS.items():
            print("%-14s prefix=%s  practice=%d  default_trials=%d  %s"
                  % (k, v["prefix"], v["practice"], v["default_trials"], v["note"]))
        return

    if not a.pid:
        print(__doc__); return

    g = GROUPS[a.group]
    if not a.pid.startswith(g["prefix"]):
        print("⚠️ 그룹 %s 의 ID 관례는 %s... 입니다. 그대로 진행합니다." % (a.group, g["prefix"]))
    trials = a.trials if a.trials else g["default_trials"]
    root = os.path.join(a.root, a.pid)
    os.makedirs(root, exist_ok=True)

    dirs = make_dirs(root)
    meta_p = make_meta(root, a.pid, a.group, a.camera, trials)
    sheet_p, n_rows = make_score_sheet(root, a.pid, trials, g["practice"])
    tids = make_landmarks_template(root, a.pid, "T1", trials, g["practice"]) \
        + make_landmarks_template(root, a.pid, "T2", trials, g["practice"])

    print("세션 준비 완료: %s" % root)
    print("  폴더 %d개: %s" % (len(dirs), ", ".join(os.path.basename(d) for d in dirs)))
    print("  meta.json: %s" % meta_p)
    print("  채점 시트: %s  (%d행 = 연습 %d×2 + 본 %d×2)"
          % (sheet_p, n_rows, g["practice"], trials))
    print("  랜드마크 템플릿 %d개: %s ..." % (len(tids), tids[0]))
    print("")
    print("다음 할 일:")
    print("  1) meta.json 의 fx/fy/cx/cy/depth_scale 을 장치에서 읽어 채운다")
    print("  2) 촬영 후 L0_raw/<trial_id>_depth/ 에 16비트 PNG(mm) 저장")
    print("     ⚠️ cv2.imwrite 금지 — 비ASCII 경로에서 조용히 실패한다. imencode+tofile 사용.")
    print("  3) L1_track/<trial_id>_landmarks.csv 를 채운다")
    print("  4) python experiments/l1_pipeline/k1k2_from_files.py --session %s" % root)
    print("  6) 채점 시트를 치료사에게 전달")


if __name__ == "__main__":
    main()

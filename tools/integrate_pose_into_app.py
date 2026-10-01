# -*- coding: utf-8 -*-
"""녹화 앱에 Pose 기록기를 주입하는 패처 (신규 도구).

기존 앱을 손으로 고치지 않는다. 이 스크립트가 **정확히 3곳**에만 삽입하고,
삽입 결과가 문법적으로 유효한지 검사한 뒤에만 쓴다. 기본값은 **미리보기(--dry-run)** 다.

삽입 지점 (앵커는 각각 파일 내 유일해야 한다):
  ① `class VideoWorker(QThread):` 앞  → import + 모듈 함수 2개(`_pose_submit`, `_pose_finalize`)
  ② `self.rec_ids.append(self.frame_id)` 뒤 → 기록 프레임마다 `_pose_submit(...)` 1줄
  ③ `_close_writers` 의 `_finalize_recording()` 블록 뒤 → `_pose_finalize(self)` 1줄

설계 원칙:
  · PoseRecorder 가 없거나 오류가 나도 **앱은 평소처럼 동작한다**(try/except, 로그만).
  · 삽입 코드에는 `POSE-PATCH v1` 마커가 있어 **재적용을 감지**한다(멱등성).
  · `--apply` 는 원본을 `.bak_YYYYmmdd_HHMMSS` 로 백업한 뒤 덮어쓴다.
  · `--out` 은 원본을 건드리지 않고 다른 파일로 저장한다.

실행:
  python tools/integrate_pose_into_app.py --dry-run
  python tools/integrate_pose_into_app.py --out /tmp/patched_app.py
  python tools/integrate_pose_into_app.py --apply
"""
from __future__ import annotations

import argparse
import difflib
import io
import os
import py_compile
import shutil
import sys
import tempfile
from datetime import datetime

DEFAULT_APP = os.path.join("capstone", "호진파일", "Mirror_therapy_clock_v3.py")
MARKER = "POSE-PATCH v1"

ANCHOR_CLASS = "class VideoWorker(QThread):"
ANCHOR_IDS = "                self.rec_ids.append(self.frame_id)"
ANCHOR_CLOSE = """        if had:
            try:
                self.last_recording = self._finalize_recording()
            except Exception as e:
                print(f"[경고] 영상 마무리 처리 실패: {e}")
                self.last_recording = None"""

INJECT_BLOCK = '''# =====================================================================
# [POSE-PATCH v1] Pose 기록기 연결
#   tools/integrate_pose_into_app.py 가 삽입했다. 기존 동작을 바꾸지 않는다.
#   pose_recorder.py 가 없거나 오류가 나면 앱은 평소처럼 동작하고 로그만 남긴다.
# =====================================================================
try:
    from pose_recorder import PoseRecorder as _PoseRecorder
except Exception as _pose_import_err:
    _PoseRecorder = None
    print(f"[POSE] pose_recorder 를 불러오지 못했습니다: {_pose_import_err}")


def _pose_submit(worker, frame_bgr, time_s, cap_mono, cap_unix):
    """기록 프레임마다 1회. Pose 는 워커 스레드가 처리하므로 캡처를 막지 않는다."""
    if _PoseRecorder is None:
        return
    try:
        rec = getattr(worker, "_pose_rec", None)
        if rec is None:
            folder = getattr(worker, "_rec_folder", None)
            if not folder:
                return
            rec = _PoseRecorder(folder, model_complexity=1, threaded=True)
            start = getattr(rec, "start", None)
            if callable(start):
                start()
            worker._pose_rec = rec
            print(f"[POSE] 기록 시작 -> {rec.csv_path}")
        rec.submit(getattr(worker, "frame_id", None), time_s, frame_bgr,
                   depth_m=getattr(worker, "latest_depth", None),
                   intr=getattr(worker, "depth_intr", None),
                   cap_mono=cap_mono, cap_unix=cap_unix)
    except Exception as exc:
        worker._pose_error_count = getattr(worker, "_pose_error_count", 0) + 1
        if worker._pose_error_count <= 3:
            print(f"[POSE ERROR] {type(exc).__name__}: {exc}")


def _pose_finalize(worker):
    """세션 종료 시 1회. pose_landmarks.csv 와 meta.json 을 마감한다."""
    rec = getattr(worker, "_pose_rec", None)
    if rec is None:
        return
    try:
        path = rec.finalize()
        print(f"[POSE] 마감 -> {path} {rec.stats()}")
    except Exception as exc:
        print(f"[POSE ERROR] 마감 실패: {exc}")
    finally:
        worker._pose_rec = None


'''

CALL_SUBMIT = "                _pose_submit(self, frame, t, cap_mono, cap_unix)   # [%s]" % MARKER
CALL_FINALIZE = """        if had:
            try:
                self.last_recording = self._finalize_recording()
            except Exception as e:
                print(f"[경고] 영상 마무리 처리 실패: {e}")
                self.last_recording = None
        _pose_finalize(self)   # [%s]""" % MARKER


def _count(src, needle):
    return src.count(needle)


def build_patch(src):
    """(patched_text, report) 또는 예외."""
    report = {"anchors": {}, "already": False}
    if MARKER in src:
        report["already"] = True
        return src, report

    for name, anchor in (("class", ANCHOR_CLASS), ("ids", ANCHOR_IDS), ("close", ANCHOR_CLOSE)):
        n = _count(src, anchor)
        report["anchors"][name] = n
        if n != 1:
            raise ValueError("앵커 '%s' 가 %d회 발견됐다(정확히 1회여야 한다). "
                             "앱이 바뀌었을 수 있으니 패처를 갱신하라." % (name, n))

    out = src.replace(ANCHOR_CLASS, INJECT_BLOCK + ANCHOR_CLASS, 1)
    out = out.replace(ANCHOR_IDS, ANCHOR_IDS + "\n" + CALL_SUBMIT, 1)
    out = out.replace(ANCHOR_CLOSE, CALL_FINALIZE, 1)
    return out, report


def verify_syntax(text, label="patched"):
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        io.open(tmp, "w", encoding="utf-8").write(text)
        py_compile.compile(tmp, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="녹화 앱에 Pose 기록기 주입")
    ap.add_argument("--app", default=DEFAULT_APP)
    ap.add_argument("--out", default=None, help="결과를 다른 파일로 저장(원본 불변)")
    ap.add_argument("--apply", action="store_true", help="원본을 백업하고 덮어쓴다")
    ap.add_argument("--dry-run", action="store_true", help="(기본) 미리보기만")
    a = ap.parse_args(argv)

    if not os.path.exists(a.app):
        print("[오류] 앱 파일을 찾을 수 없다: %s" % a.app)
        return 2
    src = io.open(a.app, encoding="utf-8").read()
    try:
        patched, report = build_patch(src)
    except ValueError as e:
        print("[오류] %s" % e)
        return 2

    if report["already"]:
        print("[건너뜀] 이미 패치되어 있다(마커 '%s' 발견). 아무것도 하지 않았다." % MARKER)
        return 0

    ok, err = verify_syntax(patched)
    if not ok:
        print("[오류] 패치 결과가 문법 오류다. 아무것도 쓰지 않았다.\n%s" % err)
        return 3

    diff = "".join(difflib.unified_diff(
        src.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile=a.app, tofile=a.app + " (patched)", n=3))
    added = sum(1 for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    print("앵커 확인: %s" % report["anchors"])
    print("추가 %d줄 / 삭제 %d줄 / 문법검사 통과" % (added, removed))
    print("-" * 72)
    print(diff if len(diff) < 8000 else diff[:8000] + "\n... (생략)")
    print("-" * 72)

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(patched)
        print("[저장] %s (원본 '%s' 는 그대로)" % (a.out, a.app))
        return 0
    if a.apply:
        bak = "%s.bak_%s" % (a.app, datetime.now().strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(a.app, bak)
        io.open(a.app, "w", encoding="utf-8").write(patched)
        print("[적용] %s  (백업: %s)" % (a.app, bak))
        print("되돌리려면: copy \"%s\" \"%s\"" % (bak, a.app))
        return 0
    print("[미리보기] 실제로 쓰지 않았다. 적용하려면 --apply, 다른 파일로 저장하려면 --out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

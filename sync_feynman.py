#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feynman Session Git Sync Tool
==============================
Feynman 대화 세션 기록(*.jsonl, *.json)과 모델 설정(models.json)을 Git 저장소와 동기화하는 도구입니다.
CLI 세션과 웹 UI(Workbench) 세션을 모두 완벽하게 보존 및 복원합니다.

사용법:
  python sync_feynman.py save     : 현재 PC의 Feynman 세션을 Git 저장소(feynman-sessions/)로 백업
  python sync_feynman.py load     : Git 저장소의 세션을 현재 PC의 Feynman으로 완벽 복원
  python sync_feynman.py status   : 동기화 상태 및 세션 파일 목록 확인
"""

import sys
import os
import glob
import json
import shutil
from pathlib import Path

# Windows 콘솔 인코딩 대응
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent
GIT_SESSIONS_DIR = REPO_ROOT / "feynman-sessions"
GIT_CONFIG_DIR = GIT_SESSIONS_DIR / "config"

FEYNMAN_HOME = Path(os.environ.get("FEYNMAN_HOME", Path.home() / ".feynman"))
LOCAL_SESSIONS_DIR = FEYNMAN_HOME / "sessions"
LOCAL_AGENT_DIR = FEYNMAN_HOME / "agent"
LOCAL_MODELS_PATH = LOCAL_AGENT_DIR / "models.json"
ORGS_DIR = FEYNMAN_HOME / "orgs"


def get_workbench_session_dirs():
    """현재 PC의 모든 활성 워크스페이스 내 sessions 디렉토리 목록 반환"""
    dirs = []
    if ORGS_DIR.exists():
        for wb_sessions in ORGS_DIR.glob("**/workbench/workspaces/*/sessions"):
            dirs.append(wb_sessions)
    return dirs


def ensure_dirs():
    GIT_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    GIT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_AGENT_DIR.mkdir(parents=True, exist_ok=True)
    for d in get_workbench_session_dirs():
        d.mkdir(parents=True, exist_ok=True)


def cmd_save():
    """현재 PC의 Feynman 세션(JSONL 및 웹 UI JSON) 및 설정을 Git 저장소로 복사"""
    ensure_dirs()
    print("[Feynman Sync] 현재 PC -> Git 저장소 백업 시작...")

    copied_jsonl = 0
    if LOCAL_SESSIONS_DIR.exists():
        for f in LOCAL_SESSIONS_DIR.glob("*.jsonl"):
            dst = GIT_SESSIONS_DIR / f.name
            if not dst.exists() or dst.stat().st_size != f.stat().st_size:
                shutil.copy2(f, dst)
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f" [+] JSONL 세션 백업: {f.name} ({size_mb:.2f} MB)")
                copied_jsonl += 1

    # 웹 UI Workbench 세션 JSON 파일 백업
    copied_json = 0
    for wb_dir in get_workbench_session_dirs():
        for f in wb_dir.glob("session-*.json"):
            dst = GIT_SESSIONS_DIR / f.name
            if not dst.exists() or dst.stat().st_size != f.stat().st_size:
                shutil.copy2(f, dst)
                print(f" [+] Workbench 세션 백업: {f.name}")
                copied_json += 1

    # 모델 설정(models.json) 동기화
    if LOCAL_MODELS_PATH.exists():
        dst_models = GIT_CONFIG_DIR / "models.json"
        shutil.copy2(LOCAL_MODELS_PATH, dst_models)
        print(" [+] 모델 설정 백업 완료 (models.json)")

    print(f"\n[완료] 총 {copied_jsonl}개 JSONL 세션, {copied_json}개 Workbench 세션이 feynman-sessions/ 에 반영되었습니다.")
    print("-> 이제 아래 명령어로 Git에 올리시면 됩니다:")
    print("   git add feynman-sessions/ sync_feynman.py sync-feynman.bat")
    print('   git commit -m "chore: sync feynman sessions"')
    print("   git push")


def cmd_load():
    """Git 저장소의 세션 및 설정을 현재 PC의 Feynman으로 복원"""
    ensure_dirs()
    print("[Feynman Sync] Git 저장소 -> 현재 PC 복원 시작...")

    if not GIT_SESSIONS_DIR.exists():
        print("[-] Git 세션 폴더(feynman-sessions/)가 없습니다.")
        return

    repo_str = str(REPO_ROOT)
    wb_dirs = get_workbench_session_dirs()

    # 1. JSONL 세션 복원 및 cwd 헤더 보정
    restored_jsonl = 0
    for f in GIT_SESSIONS_DIR.glob("*.jsonl"):
        dst = LOCAL_SESSIONS_DIR / f.name
        # 헤더의 cwd를 현재 저장소 경로로 자동 보정하여 복원
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as in_f:
                lines = in_f.readlines()
            if lines:
                hdr = json.loads(lines[0])
                hdr["cwd"] = repo_str
                lines[0] = json.dumps(hdr, ensure_ascii=False) + "\n"
                with open(dst, "w", encoding="utf-8") as out_f:
                    out_f.writelines(lines)
            size_mb = dst.stat().st_size / (1024 * 1024)
            print(f" [+] JSONL 세션 복원: {f.name} ({size_mb:.2f} MB)")
            restored_jsonl += 1
        except Exception as e:
            shutil.copy2(f, dst)
            restored_jsonl += 1

    # 2. Workbench 세션 JSON 파일 복원
    restored_json = 0
    for f in GIT_SESSIONS_DIR.glob("session-*.json"):
        for target_dir in wb_dirs:
            dst = target_dir / f.name
            shutil.copy2(f, dst)
        print(f" [+] Workbench 세션 복원: {f.name}")
        restored_json += 1

    # 3. 모델 설정 복원
    git_models = GIT_CONFIG_DIR / "models.json"
    if git_models.exists():
        shutil.copy2(git_models, LOCAL_MODELS_PATH)
        print(" [+] 모델 설정(DeepSeek 4.1 등) 복원 완료 (models.json)")

    print(f"\n[완료] 총 {restored_jsonl}개 JSONL 세션 및 {restored_json}개 Workbench 세션이 복원되었습니다!")
    print("-> 이제 웹 UI나 터미널에서 Feynman을 실행하시면 이전 대화 기록이 그대로 활성화됩니다.")


def cmd_status():
    """동기화 상태 확인"""
    ensure_dirs()
    print("[Feynman Sync] 상태 점검")
    print(f" - Git 저장소 세션 경로: {GIT_SESSIONS_DIR}")
    print(f" - 현재 PC 세션 경로  : {LOCAL_SESSIONS_DIR}")

    git_jsonl = list(GIT_SESSIONS_DIR.glob("*.jsonl"))
    git_json = list(GIT_SESSIONS_DIR.glob("session-*.json"))
    local_jsonl = list(LOCAL_SESSIONS_DIR.glob("*.jsonl"))
    
    wb_json_count = 0
    for wb_dir in get_workbench_session_dirs():
        wb_json_count = max(wb_json_count, len(list(wb_dir.glob("session-*.json"))))

    print(f"\n[Git 저장소에 저장된 세션 ({len(git_jsonl)}개 JSONL, {len(git_json)}개 Workbench JSON)]")
    for f in git_jsonl:
        print(f"  - {f.name} ({f.stat().st_size / (1024 * 1024):.2f} MB)")

    print(f"\n[현재 PC 로컬 세션 ({len(local_jsonl)}개 JSONL, {wb_json_count}개 Workbench JSON)]")
    for f in local_jsonl:
        print(f"  - {f.name} ({f.stat().st_size / (1024 * 1024):.2f} MB)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        cmd_status()
        return

    arg = sys.argv[1].lower()
    if arg in ("save", "backup", "push"):
        cmd_save()
    elif arg in ("load", "restore", "pull"):
        cmd_load()
    elif arg in ("status", "info"):
        cmd_status()
    else:
        print(f"[!] 알 수 없는 명령어: {arg}")
        print("사용 가능한 명령어: save, load, status")


if __name__ == "__main__":
    main()

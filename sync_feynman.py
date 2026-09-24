#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feynman Session Git Sync Tool
==============================
Feynman 대화 세션 기록(*.jsonl)과 모델 설정(models.json)을 Git 저장소와 동기화하는 도구입니다.

사용법:
  python sync_feynman.py save     : 현재 PC의 Feynman 세션을 Git 저장소(feynman-sessions/)로 백업
  python sync_feynman.py load     : Git 저장소의 세션을 현재 PC의 Feynman(~/.feynman/sessions/)으로 복원
  python sync_feynman.py status   : 동기화 상태 및 세션 파일 목록 확인
"""

import sys
import os
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


def ensure_dirs():
    GIT_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    GIT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_AGENT_DIR.mkdir(parents=True, exist_ok=True)


def cmd_save():
    """현재 PC의 Feynman 세션 및 설정을 Git 저장소로 복사"""
    ensure_dirs()
    print("[Feynman Sync] 현재 PC -> Git 저장소 백업 시작...")

    if not LOCAL_SESSIONS_DIR.exists():
        print(f"[-] 로컬 세션 경로가 존재하지 않습니다: {LOCAL_SESSIONS_DIR}")
        return

    copied_sessions = 0
    for f in LOCAL_SESSIONS_DIR.glob("*.jsonl"):
        dst = GIT_SESSIONS_DIR / f.name
        # 파일이 없거나 크기가 다를 때만 복사
        if not dst.exists() or dst.stat().st_size != f.stat().st_size:
            shutil.copy2(f, dst)
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f" [+] 세션 백업: {f.name} ({size_mb:.2f} MB)")
            copied_sessions += 1
        else:
            print(f" [=] 이미 최신 상태: {f.name}")

    # 모델 설정(models.json) 동기화 (DeepSeek 4.1 등)
    if LOCAL_MODELS_PATH.exists():
        dst_models = GIT_CONFIG_DIR / "models.json"
        shutil.copy2(LOCAL_MODELS_PATH, dst_models)
        print(" [+] 모델 설정 백업 완료 (models.json)")

    print(f"\n[완료] 총 {copied_sessions}개 신규/수정 세션이 feynman-sessions/ 에 반영되었습니다.")
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

    restored_sessions = 0
    for f in GIT_SESSIONS_DIR.glob("*.jsonl"):
        dst = LOCAL_SESSIONS_DIR / f.name
        if not dst.exists() or dst.stat().st_size != f.stat().st_size:
            shutil.copy2(f, dst)
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f" [+] 세션 복원: {f.name} ({size_mb:.2f} MB)")
            restored_sessions += 1
        else:
            print(f" [=] 이미 로컬에 최신 세션이 있음: {f.name}")

    # 모델 설정 복원
    git_models = GIT_CONFIG_DIR / "models.json"
    if git_models.exists():
        shutil.copy2(git_models, LOCAL_MODELS_PATH)
        print(" [+] 모델 설정(DeepSeek 4.1 등) 복원 완료 (models.json)")

    print(f"\n[완료] 총 {restored_sessions}개 세션 및 모델 설정이 현재 PC에 복원되었습니다!")
    print("-> 이제 터미널에서 Feynman을 실행하시면 이전 대화 기록과 DeepSeek 4.1 설정을 그대로 쓰실 수 있습니다.")


def cmd_status():
    """동기화 상태 확인"""
    ensure_dirs()
    print("[Feynman Sync] 상태 점검")
    print(f" - Git 저장소 세션 경로: {GIT_SESSIONS_DIR}")
    print(f" - 현재 PC 세션 경로  : {LOCAL_SESSIONS_DIR}")

    git_files = {f.name: f.stat().st_size for f in GIT_SESSIONS_DIR.glob("*.jsonl")}
    local_files = {f.name: f.stat().st_size for f in LOCAL_SESSIONS_DIR.glob("*.jsonl")}

    print(f"\n[Git 저장소에 저장된 세션 ({len(git_files)}개)]")
    for name, size in git_files.items():
        print(f"  - {name} ({size / (1024 * 1024):.2f} MB)")

    print(f"\n[현재 PC 로컬 세션 ({len(local_files)}개)]")
    for name, size in local_files.items():
        print(f"  - {name} ({size / (1024 * 1024):.2f} MB)")


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

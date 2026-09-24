# Feynman 대화 세션 및 설정 동기화 저장소

이 디렉토리는 Feynman의 대화 세션 기록(`*.jsonl`)과 커스텀 모델 설정(`config/models.json`)을 Git으로 동기화하기 위한 폴더입니다.

---

## 🚀 다른 컴퓨터와 동기화하는 방법

### 1. 현재 컴퓨터에서 작업 후 (GitHub에 올릴 때)
작업이 끝난 후 터미널(저장소 루트)에서 아래 명령어를 실행합니다:

```powershell
# 1) Feynman 세션을 이 폴더로 복사
python sync_feynman.py save

# 2) Git 커밋 및 푸시
git add feynman-sessions/
git commit -m "chore: sync feynman sessions"
git push
```

---

### 2. 다른 컴퓨터에서 (이전 기록을 가져올 때)
새 컴퓨터에서 GitHub 저장소를 pull 받은 후 아래 명령어를 실행합니다:

```powershell
# 1) 최신 커밋 받아오기
git pull

# 2) 이 폴더의 세션과 모델 설정을 새 컴퓨터의 Feynman으로 복원
python sync_feynman.py load
```

복원이 끝나면 새 컴퓨터에서 Feynman을 실행했을 때 이전 대화 기록 및 DeepSeek 4.1 설정이 그대로 유지됩니다.

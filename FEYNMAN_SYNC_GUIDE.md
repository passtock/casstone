# 📘 Feynman 다른 컴퓨터와 동기화 사용 가이드

이 문서는 집/연구실 등 여러 대의 컴퓨터에서 **Feynman 대화 세션 기록**과 **DeepSeek V4.1 모델 설정**을 Git을 통해 완벽하게 동기화하고 이어쓰는 방법을 정리한 가이드입니다.

---

## 💻 1. 지금 컴퓨터에서 작업이 끝났을 때 (GitHub에 올리기)

파인만 작업을 마치고 다른 컴퓨터로 이동하기 전, 터미널(프로젝트 루트)에서 다음 3단계를 입력합니다:

```powershell
# 1) 최신 대화 기록 및 모델 설정을 깃 폴더(feynman-sessions/)로 복사
.\sync-feynman save

# 2) Git에 추가 및 커밋
git add .
git commit -m "chore: sync feynman sessions"

# 3) GitHub에 푸시
git push
```

---

## 💻 2. 다른 컴퓨터에서 이전 기록을 불러올 때

새 컴퓨터에서 프로젝트를 열고 다음 2단계를 입력합니다:

```powershell
# 1) GitHub 최신 커밋 가져오기
git pull

# 2) 다른 PC의 파인만으로 세션 및 DeepSeek 4.1 설정 자동 복원
.\sync-feynman load
```

> **복원 완료 후**: 새 컴퓨터에서 `feynman`을 실행하면 이전 대화 기록과 `opencode-go/deepseek-v4.1-flash` 모델 설정이 그대로 활성화되어 바로 이어갈 수 있습니다!

---

## 💡 파인만 기본 실행 팁

1. **파인만 실행 명령어**:
   - 파인만 실행은 `feynman serve`가 아니라 단순히 **`feynman`**만 입력하시면 됩니다.
   - 현재 등록된 모델 확인: `feynman model list`
   - 모델 변경: `feynman model set <모델명>`
2. **`feynman` 명령어가 터미널에서 안 뜰 때**:
   - PowerShell 창을 새로 닫았다가 다시 열면 정상 인식됩니다.
   - 현재 창에서 바로 인식시키려면 아래 명령어를 한 번 실행해 주세요:
     ```powershell
     $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User")
     ```
3. **현재 활성화된 모델**:
   - **`opencode-go/deepseek-v4.1-flash`** (OpenCode Go 최신 DeepSeek Flash 4.1)

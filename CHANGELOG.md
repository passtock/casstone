# Lab Notebook & Research Changelog

## 2026-09-22: ARAT/FMA 8대 핵심 선행연구 종합 조사 완료
- **Active Slug**: `arat-fma-comprehensive-lit-review`
- **Output Files**:
  - [`outputs/arat-fma-comprehensive-lit-review.md`](file:///c:/Users/passp/OneDrive/바탕%20화면/jeayong/outputs/arat-fma-comprehensive-lit-review.md)
  - [`outputs/arat-fma-comprehensive-lit-review.provenance.md`](file:///c:/Users/passp/OneDrive/바탕%20화면/jeayong/outputs/arat-fma-comprehensive-lit-review.provenance.md)
- **Key Findings**:
  1. FMA/ARAT의 임상적 한계(천장/바닥 효과, 평가자 주관성, 보상 운동 미구분) 체계화.
  2. SPARC, PAp, TPAp, TAPV, 체간 변위 등 4대 운동학 지표의 상관관계 수식 근거 확보.
  3. 기존 딥러닝(지도학습)의 데이터 기근/블랙박스 한계 정리.
  4. VLM 단독 사용 시의 'Kinematic Blindness' 및 'Score Flatlining' 결함 규명.
  5. 뇌졸중 환자의 비정상적 시너지 및 체간 보상 기전 정리.
  6. 비장애인 파지 다양성(Santello 1998, Calinon 2007) 및 GMM 서브타이핑/매니폴드 모델링의 공학적 당위성 확립.
  7. 무마커 RGB-D(MediaPipe+Depth)의 Vicon 대비 타당성(Amprimo 2024) 확보.
  8. 비디오+수치 지식 증강 VLM(Wang et al. MICCAI 2024)을 통한 2-Stage 하이브리드 아키텍처 정당성 확립.
- **Verification**: `[verified]` 24편 핵심 논문 APA 인용 및 매핑 완료.
- **Next Step**: 건강인 예비 실험 데이터 기반 GMM 6차원 벡터 정의 및 Stage 1 알고리즘 구현.

---

## 2026-09-22 (2차): 증거맵·아틀라스 확장 + v6 실험계획 나이브 초안

### A. 두 조사문서에 비전문가 해설 전면 추가
- `outputs/rgbd-grasp-vlm-protocol-analysis.md` → **논문 43편 전부**에 `🔎 쉬운 설명` 6줄 블록
- `outputs/arat-fma-ue-evidence-map.md` → **논문 40개 절 전부**에 동일 블록
- §0-3 전체 용어집(약 100항목) + 어려운 두 논문(E-3·E-4)에 `🧩 용어 풀이` 추가
- 오타 9종 수정(굴힘→굽힘 등), grep으로 잔여 0건 확인

### B. 검증에서 발견한 문서 오류 2건 (사용자 지적)
1. **범위 초과 서술:** 문서가 “우리는 6차원 GMM을 쓴다”고 서술했으나, **v5 §1·§5는 정상 GMM·군집화를 명시적으로 범위 밖**으로 둔다. “6차원”은 프로젝트 배경 설명문의 표현이었다.
2. **입력 정의 불일치:** 두 문서에 v5의 실제 입력 이름 **K1·K2·Q·T가 0건**이었다. “PAp”로 쓴 곳은 v5의 **K1**(표면점 거리 P95)과 동일하지 않으며, v5는 K1을 “실제 최대 벌림·관절 중심 거리로 확정하지 말 것”을 명시한다.
- **조치:** 양쪽 문서 상단에 **v5 범위 주의문 + 표현 대응표** 삽입. `6-component GMM` 잔여 0건. `provenance.md`에 정정 기록.

### C. 신규 산출물: `outputs/experiment-plan-v6-naive.md`
- 문헌 근거로 전체 실험계획을 재배치한 **나이브 1차 초안** (16절, 47개 출처)
- **건강인 최소 인원 결정:** v5의 8명 → **최소 20명**(개발 8 + 독립 기술검증 12), 권장 30명. 근거: 검증 문헌의 건강인 N이 15/20/22/24/26에 몰려 있고(Scano 15, Li 2026 20, Hamilton 22, Jarque-Bou 20 24, Faity 26), ICC는 사람 수가 적으면 구간이 폭발한다.
- **후속 정상모형이 필요해지면 별도 코호트 60~100명+** 필요(Jarque-Bou 2019 = 77명, UbiPhysio = 104명). 이번에 GMM을 빼는 결정과 일관됨.
- **원본 저장 계층 L0~L3 분리**로 후처리 계산 가능성 확보. 14프레임은 L3 파생물이며, 운동학 수치는 L1 추적 스트림에서 계산해 JSON으로 주입.
- **fps 결정:** 원본 30 fps 유지(15 fps는 Faity의 속도 ICC 0.21 실패를 악화시킬 위험).
- **14프레임 산술:** 15 fps면 0.93초, 30 fps면 0.47초 → ARAT 3점 기준(5초)의 9~19%만 덮음. 따라서 **균등 샘플링 + 사람 구간선택 금지**를 제안(결정 필요 #1).
- **환자 15명은 유지**하되 **검정력 계산을 하지 않았음을 명시**하고, “12명이면 충분하다”고 쓰지 않도록 제한.
- **Verification**: `[verified]` v5 원문의 A0~A4/R 정의·K1/K2/Q/T 정의·판정표를 grep/read로 직접 확인. `[unverified]` 검정력, 14프레임 정보 충분성, Q 규칙 성능, u의 크기.
- **Next Step**: 결정 목록 #1~#3 마감(14프레임 절단 규칙 → u 정의 → Q 임계값 골격), 그 다음 정적 치구 검증 135기록 실행.

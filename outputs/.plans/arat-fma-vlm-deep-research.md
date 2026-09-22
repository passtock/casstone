# Deep Research Plan: arat-fma-vlm-deep-research

- **Topic**: ARAT 및 FMA 상지 기능 평가를 위한 RGB-D 운동학 정보 및 VLM 융합 8대 선행연구 심층 조사
- **Slug**: `arat-fma-vlm-deep-research`
- **Lead Agent**: Antigravity (Feynman Protocol)
- **Status**: PENDING_USER_CONFIRMATION

---

## 1. Key Questions

1. **Q1 (임상적 한계)**: 기존 FMA-UE 및 ARAT의 평가자 간/내 신뢰도(ICC), 천장/바닥 효과 발생률, 검사 소요 시간, 보상 운동 미구분 문제를 정량적으로 지적한 핵심 의학 논문은 무엇인가?
2. **Q2 (운동학 상관성)**: SPARC, LDLJ, PAp, TPAp, TAPV, 체간 변위 등 운동학 지표가 FMA/ARAT 점수와 상관계수(r) 얼마의 유의미한 관계를 가지는가? (수식 및 역학적 기전)
3. **Q3 (기존 ML/DL 자동화)**: 웨어러블 IMU 센서 및 RGB/스켈레톤(ST-GCN, SlowFast) 기반 자동 평가의 SOTA 성능(정확도, $R^2$)과 임상 도입 실패 요인(데이터 기근, 블랙박스)은 무엇인가?
4. **Q4 (VLM 재활 평가 및 결함)**: Li et al. (2026) 등 VLM을 재활 평가에 적용한 최신 연구의 프롬프트 구성 및 점수 평탄화(Flatlining), 시공간 역학 맹점(Kinematic Blindness)의 실증적 증거는 무엇인가?
5. **Q5 (정상 vs 편마비 차이)**: 뇌졸중 편마비 환자의 비정상 굴곡 시너지, 파지 개구 형성(preshaping) 지연, 체간 보상 이동량(cm)의 정량적 비교 데이터는 어떻게 보고되었는가?
6. **Q6 (건강인 파지 다양성 및 GMM)**: 비장애인의 파지 동작이 단일 궤적이 아닌 다중 서브타입으로 분화됨을 입증한 손 시너지(Santello 1998) 및 GMM/매니폴드 군집화(Calinon 2007) 선행연구는 무엇인가?
7. **Q7 (무마커 RGB-D 신뢰도)**: Vicon/Optotrak 골드 스탠다드 대비 RealSense/Azure Kinect 및 MediaPipe 기반 3차원 손/관절 추적 오차(mm/cm)와 검사-재검사 신뢰도(ICC) 검증 연구는 무엇인가?
8. **Q8 (지식 증강 VLM 융합)**: Wang et al. (MICCAI 2024) 등 센서/운동학 수치 지표(JSON/임베딩)를 VLM에 함께 주입하여 진단/평가 정확도를 끌어올린 멀티모달 지식 증강의 구체적 구조와 성능 향상치는 얼마인가?

---

## 2. Evidence Needed

- PubMed / IEEE Xplore / arXiv / ACM / Springer에 등재된 피어리뷰 논문 원문 메타데이터 및 초록.
- 각 논문별 구체적 피험자 수(환자군 N, 대조군 N), 사용 센서/카메라 모델, 통계적 지표($r$, ICC, $R^2$, Accuracy, MAE).
- 수식 정의: SPARC 수식, Qiu 4대 지표 정의 구간, GMM 및 마할라노비스 거리 수식.

---

## 3. Scale Decision

- **결정**: **Direct Multi-Angle Search Mode**
- **사유**: 8대 세부 질문이 명확히 정의되어 있으며, 각 축별로 고유한 학술 검색 쿼리(축당 2~3개, 총 16~20개 정밀 쿼리)를 순차 실행하여 실제 논문 본문/초록 데이터를 긁어와 직접 교차 검증 및 인용 합성하는 것이 가장 높은 신뢰도와 정합성을 담보함.

---

## 4. Task Ledger

| Task ID | 목표 질문 | 담당 | 산출물 위치 / 상태 |
| :--- | :--- | :--- | :--- |
| **T1** | Q1: FMA/ARAT 임상 한계 논문 심층 검색 | Lead | `outputs/.drafts/arat-fma-vlm-deep-research-research-direct.md` (대기) |
| **T2** | Q2: SPARC, Qiu 파라미터 상관관계 수치 검색 | Lead | 동일 파일 (대기) |
| **T3** | Q3: ML/DL 기반 자동 평가 SOTA 및 한계 검색 | Lead | 동일 파일 (대기) |
| **T4** | Q4: VLM 재활 평가 논문(Li 2026 등) 원문 및 한계 검색 | Lead | 동일 파일 (대기) |
| **T5** | Q5: 정상 vs 편마비 파지/체간 보상 정량치 검색 | Lead | 동일 파일 (대기) |
| **T6** | Q6: 건강인 파지 다양성 및 GMM/시너지 모델링 검색 | Lead | 동일 파일 (대기) |
| **T7** | Q7: MediaPipe+RGB-D vs Vicon 신뢰도 논문 검색 | Lead | 동일 파일 (대기) |
| **T8** | Q8: 멀티모달 수치 지식 증강 VLM 선행연구 검색 | Lead | 동일 파일 (대기) |
| **T-Synth** | 초안 작성 (Drafting) | Lead | `outputs/.drafts/arat-fma-vlm-deep-research-draft.md` |
| **T-Cite** | 인용 및 URL 전수 검증 | Lead | `outputs/.drafts/arat-fma-vlm-deep-research-cited.md` |
| **T-Review** | 치명적 결함(FATAL) 검토 및 최종 납품 | Lead | `outputs/arat-fma-vlm-deep-research.md` + `.provenance.md` |

---

## 5. Verification Log

- [ ] 검색 쿼리 및 URL 도달 가능성 전수 확인
- [ ] 피험자 수(N) 및 통계치 원문 대조 확인
- [ ] VLM 결함(Flatlining, Kinematic Blindness)에 대한 원문 근거 확인
- [ ] GMM 서브타입 당위성 관련 수식/참고문헌 검증

---

## 6. Decision Log

- **2026-09-22**: 초기 계획 수립. 8대 질문을 독립된 검색 축으로 분리하여 실시간 웹/학술 검색을 단계별로 실행하기로 결정.

# 체계적 검색 · 신규성 감사 (Novelty Audit)

**작성일:** 2026-09-23 · **v2 확장:** 2026-09-24
**목적:** "우리 연구가 정말 새로운가"를 검증한다. 이전에 내가 한 **"공백이다"라는 주장 3개를 검증**하고, 반박되면 정정한다.
**계기:** 사용자가 "이게 진짜 없어?"라고 의심 → 검색 → **내 주장 3개가 모두 반박됨.**
**방법 v1:** `web_search`(복수 provider) + `feynman_science_database_search`(PubMed). 검색어는 아래 각 절에 기록.
**방법 v2 (§11~§14):** **Semantic Scholar Graph API(bulk search)** 직접 호출 + **OpenAlex** API. 9개 S2 질의 + 4개 OpenAlex 질의. §11에 전문 기록.
**⚠️ 한계:** **PRISMA식 전수조사가 아니다.** PubMed/웹/S2/OpenAlex에서 표적 검색한 결과이며, **Scopus·Embase·Web of Science·ACM DL·IEEE Xplore 전체**를 훑지 않았다. 따라서 **"없다"고 단정하지 않는다.**

> **📌 v2 읽기 안내**
> - **§0~§10 = 감사 v1** (2026-09-23). "이전 주장 3개가 틀렸다"는 기록.
> - **§11 = 확장 검색 전문** (Semantic Scholar + OpenAlex, 질의·건수·출처 전부 기록).
> - **§12 = 갱신된 신규성 판정.** v1에서 살아남았다고 본 후보 B가 **부분 반박**됨 (NeuroSift 2026 · Edges Before Embeddings 2026).
> - **§13 = 차별점 재설계 (Plan B 중심축).** 무엇을 주장하고 무엇을 주장하지 않을지.
> - **§14 = 연구계획서에 반영할 정확한 변경 목록.**

---

## 0. 결론 (먼저)

| 이전 내 주장 | 검증 결과 |
|---|---|
| "손가락 수준 RGB-D 검증이 공백이다" | ❌ **틀렸다.** GMH-D 등 **5편 이상** 존재 |
| "품질 게이팅 규칙을 제안한 연구가 없다" | ❌ **틀렸다.** EVGS 품질평가·JMIR 사후 QC 등 **5편** 존재 |
| "가림 조건의 정량적 실패 특성이 없다" | ❌ **틀렸다.** Hand Visibility Detector·Metamorphic Testing **4편** 존재 |
| "수치 오류가 AI 판정에 전파되는지 아무도 시험 안 했다" | ⚠️ **대부분 반박.** 개념은 2022년부터 존재. **특정 조합만 남음** |

**→ 현재 남은 것은 "여러 기존 요소의 교집합"이며, 그 교집합이 독립 논문을 지탱할 만큼 큰지 불확실하다.**

**→ 그리고 가장 아픈 사실:** GMH-D(Amprimo 2024)는 **사용자의 초기 노트(`CHANGELOG.md` 2026-09-22 항목 7번)에 이미 적혀 있었다.** 내가 그걸 다시 읽지 않고 "공백"이라고 썼다.

---

## 1. 반박된 주장 ①: 손가락 수준 RGB-D 검증

**내 주장:** "Faity는 trunk/wrist/elbow만 검증했고 손가락은 안 했다. Scano는 workspace, Hamilton은 knee/elbow. **손가락 수준 RGB-D 검증은 공백이다.**"

**검색어:** `MediaPipe hand landmark accuracy validation against motion capture finger joint angles`, `markerless hand tracking occlusion fingertip accuracy validation`

### 실제로 존재하는 논문

| # | 논문 | 무엇을 했나 | 게재지·ID |
|---|---|---|---|
| **1** | **Amprimo et al. (2024). Hand tracking for clinical applications: Validation of the Google MediaPipe Hand (GMH) and the depth-enhanced GMH-D frameworks** | **MediaPipe(GMH)와 RGB-Depth 강화판(GMH-D)을 모션캡처와 비교 검증.** 손가락 수준. **거리(near 60–80cm / far 80–100cm)·속도·과제 종류**를 요인으로 분석. "both frameworks achieve good-to-high spatial accuracy". **인용 57회** | Biomed Signal Process Control, doi 10.1016/j.bspc.2024.106508 · arXiv:2308.01088 |
| 2 | Optimisation and Comparison of Markerless and Marker-Based Motion Capture Methods for Hand and Finger Movement Analysis (2025) | **Leap Motion vs MediaPipe vs 마커 기반** 손가락 비교. **MediaPipe RMSE 10.9° vs Leap 14.7°** | Sensors 25(4):1079, doi 10.3390/s25041079 |
| 3 | Verification of Criterion-Related Validity for Developing a Markerless Hand Tracking Device (2024) | MediaPipe 스마트폰 앱으로 **편마비 환자 손 마비 추정**. 적합타당도 검증 | Biomimetics 9(7):400, doi 10.3390/biomimetics9070400 |
| 4 | Proof of Concept and Validation of Single-Camera AI-Assisted Live Thumb Motion Capture (2025) | **단일카메라 AI 엄지(CMC) 모션캡처** 검증 | Sensors 25(15):4633, doi 10.3390/s25154633 |
| 5 | Measuring arm and hand joint kinematics to estimate impairment during a functional reach and grasp task in stroke participants | **센서 장갑으로 뇌졸중 환자의 reach-to-grasp 중 손가락/손/팔 관절** 정확도·정밀도 특성화 후 손상 추정 | PMC10330436 |
| 6 | Accuracy and Reliability of Markerless Pose Estimation for Upper Limb Kinematic Analysis (2026) | MediaPipe vs SMART-DX 8-camera 모캡, 60fps 1080p | Applied Sciences 16(3):1202, doi 10.3390/app16031202 |

### 영향

**"손가락 수준 RGB-D 검증"은 확립된 분야입니다.** 특히 **GMH-D는 선생님 설정(MediaPipe + RGB-D + 손가락 + 임상)과 거의 동일**하며, 거리·속도·과제 요인까지 이미 다뤘습니다.

**→ 1편을 "센서 검증"으로 독립 출판하는 것은 정면 충돌합니다.**
**→ 대신 GMH-D를 "우리 방법의 타당성 근거"로 인용하는 것이 맞습니다.**

---

## 2. 반박된 주장 ②: 품질 게이팅 / 프레임 선택

**내 주장:** "기존 validation 논문은 '오차가 얼마다'로 끝난다. **'어느 프레임을 믿어야 하는가'는 제안하지 않는다.**"

**검색어:** `automatic quality control frame selection pose estimation clinical movement assessment`

### 실제로 존재하는 논문

| # | 논문 | 무엇을 했나 | 게재지·ID |
|---|---|---|---|
| **1** | **Automated Video Quality Assessment for the Edinburgh Visual Gait Score (EVGS)** (2025) | **MoveNet으로 자세를 뽑아** 다중 인물 검출·관심 인물 추적·**평면 방향 평가**·**겹침 검출**·**줌 아티팩트 검출**·품질 평가 → **보행 채점 영상의 자동 품질 게이팅** | Methods and Protocols 8(4):71, doi 10.3390/mps8040071 |
| **2** | **Proposal for Post Hoc Quality Control in Instrumented Motion Analysis Using Markerless Motion Capture** | **무마커 모캡의 사후 품질관리 표준 도구** 제안 — "quality concerns를 식별·통제하는 표준화 도구" | JMIR Preprints, doi 10.2196/preprints.26825 |
| 3 | AGMA-PESS: deep learning-based infant pose estimator and **sequence selector** (2024) | 영아 자세 추정 + **GMA용 시퀀스 자동 선택** | Front Pediatr 12:1465632 |
| 4 | Sparse frame selection for graph-based deadlift form assessment (2026) | **프레임 선택**으로 운동 자세 평가 정확도 향상 | Sci Rep, doi 10.1038/s41598-026-67912-0 |
| 5 | Tify: A quality-based frame selection tool (2019) | 품질 기반 프레임 선택 도구 | PLOS ONE, doi 10.1371/journal.pone.0213162 |
| 6 | Deep Learning for Classification and Selection of Cine CMR Images (2021) | **완전 자동 품질관리 선택** 파이프라인 (심장 MRI) | Front Cardiovasc Med 8:742640 |

### 영향

**"품질 게이팅"과 "프레임 선택"은 이미 확립된 개념입니다.** 특히 **EVGS 논문은 보행 채점에서 우리와 같은 일**을 하고, **JMIR 논문은 "무마커 모캡 사후 품질관리"를 정면으로 다룹니다.**

**→ 남은 차이:** 그들은 **골격 기반 분류기(DL)** 를 쓰고, 우리는 **생성형 VLM**입니다. **"생성형 VLM 입력에서의 품질 게이팅"** 은 아직 못 찾았습니다.

---

## 3. 반박된 주장 ③: 가림 조건의 정량적 실패 특성

**내 주장:** "랜드마크가 배경에 찍히면 K1이 110배 오염된다. **아무도 이걸 정량화하지 않았다.**"

**검색어:** `occlusion detection hand pose estimation failure quantification fingertip tracking`

### 실제로 존재하는 논문

| # | 논문 | 무엇을 했나 | 게재지·ID |
|---|---|---|---|
| **1** | **Hand Visibility Detector: Per-Keypoint Visibility Estimation for Hands** (2026) | **손 관절별 가시성(visibility)을 명시적으로 추정.** "대부분의 HPE는 가시성을 출력하지 않는다"를 문제로 제기하고 해결 | arXiv:2608.11574 |
| **2** | **Robustness Evaluation in Hand Pose Estimation Models using Metamorphic Testing** (2023) | **가림·노출 저하·기타 불확실성이 HPE 성능을 저하시키는 것을 체계적으로 정량 평가** | IEEE, doi 10.1109/MET59151.2023.00012 · arXiv:2303.04566 |
| 3 | Real-Time Hand Tracking Under Occlusion from an Egocentric RGB-D Sensor (2017) | RGB-D + CNN 2단계로 **가림 하 손 추적** | ICCVW 2017, doi 10.1109/iccvw.2017.82 |
| 4 | Hidden Hands: Tracking Hands With an Occlusion Aware Tracker (2016) | 단안 RGB에서 **가림 인식 추적기** | CVPRW 2016 |
| 5 | Capturing Hand Motion with an RGB-D Sensor, Fusing a Generative Model with Salient Points (2014) | RGB-D + 생성모델 융합, "**severe occlusions and self-similarity between fingers**"를 문제로 명시 | GCPR 2014 |

### 영향

**"가림이 손 추적을 망친다"는 것은 2014년부터 알려진 문제**이고, **관절별 가시성 추정(2026)** 과 **변형 테스트 기반 정량화(2023)** 가 이미 있습니다.

**→ 남은 차이:** 그들은 **HPE 모델의 성능 지표**(관절 오차)로 보고, 우리는 **임상 지표(K1)의 배수 오염**과 **VLM 채점 영향**으로 갑니다. **응용 층이 다릅니다.**

---

## 4. 부분 반박: 수치 오류 → AI 판정 전파

**내 주장:** "'수치가 틀리면 VLM 판정도 틀리는가'를 아무도 시험하지 않았다."

**검색어:** `measurement error propagation machine learning clinical prediction`, `LLM prompt sensitivity numeric perturbation`, `VLM robustness corrupted inputs`, `sensor accuracy requirements AI medical device`

### A. 개념적으로 같은 선행연구 (센서/정형데이터)

| # | 논문 | 핵심 |
|---|---|---|
| **1** | **Characterizing sensor accuracy requirements in an AI-enabled medical device** (2022) | 🔴 초록: "**Inaccurate sensor inputs affect score outputs** in AI-enabled devices" / "**Simulation-based method can predict how sensor inaccuracy affects algorithmic output**" / "can be used to **determine design requirements**" — **개념적으로 우리 PR-1과 거의 동일** | doi 10.1016/j.ipemt.2022.100004 (ScienceDirect S2667258822000024) — *IPEM-Translation* 2022; 정식 제목은 "...in an **artificial intelligence**-enabled medical device" ([PROV-AUDIT 2026-09-25] 누락 DOI 복원) |
| 2 | Addressing Measurement Error in Random Forests Using Quantitative Bias Analysis | 측정 오류가 ML 예측 성능·변수중요도에 미치는 영향 | PMC8408353 |
| 3 | The impact of covariate measurement error on risk prediction | 예측변수 측정오류의 영향 | Stat Med, doi 10.1002/sim.6498 |
| 4 | Impact of predictor measurement heterogeneity across settings | 세팅 간 측정 이질성의 영향 | Stat Med, doi 10.1002/sim.8183 |

### B. LLM/VLM 입력 민감도 (활발한 분야)

| # | 논문 | 핵심 |
|---|---|---|
| 1 | LLM Sensitivity Evaluation Framework for Clinical Diagnosis (COLING 2025) | GPT-3.5/4·Gemini·Claude3·LLaMA2에 **perturbation 전략 주입** → 진단 변화 | aclanthology 2025.coling-main.207 |
| 2 | Evaluating prompt and **data perturbation** sensitivity in LLMs (2025) | 방사선 보고서 분류에서 프롬프트·**데이터 교란** 민감도 | PMC12343119 |
| 3 | How Robust Are LLMs for Clinical Numeracy? (ClinicNumRobBen, 2026) | **임상 수치 이해의 견고성** | ACL Findings 2026 |
| 4 | LAPD: Latent Fragility under Agentic Perturbations in Clinical LLMs (2025) | 잠재 표현 취약성 진단 | arXiv:2507.21188 |
| 5 | When LLMs Fail in Healthcare: Sensitivity to Prompt Variations (2026) | 프롬프트 변형 민감도 체계 분석 | arXiv:2606.07237 |
| 6 | **Prompt injection attacks on VLMs for surgical decision support** (2026) | **VLM에 텍스트·시각 주입 공격** → 11개 임상 과제 성능 변화 | Nature, doi 10.1038/s44484-026-00014-6 |
| 7 | **ST-VLM: Kinematic Instruction Tuning for Spatio-Temporal Reasoning** | 🔴 **VLM이 kinematic 요소(거리·속도) 추론을 못 한다**는 것을 데이터셋으로 보이고 instruction tuning으로 개선 | ST-VLM 벤치마크 |
| 8 | Understanding the robustness of VLMs to medical image artefacts (2025) | 의료영상 아티팩트에 대한 VLM 견고성 | npj Digital Medicine, doi 10.1038/s41746-025-02108-w |
| 9 | On the Robustness of Medical VLMs (MediMeta-C, 2025) | 의료 VLM corruption 벤치마크 | arXiv:2505.15425 |

### C. VLM + 생체역학/수치 융합

| # | 논문 | 핵심 |
|---|---|---|
| **1** | **BioGait-VLM** (2026) | **tri-modal Vision-Language-Biomechanics** 보행 평가. **Biomechanical Tokenization branch**로 생체역학 정보를 토큰화 | arXiv:2603.08564 |
| 2 | Unger et al. (2026) | ARAT에 무마커 모캡 삽입, **순서형 점수 밖의 정보** | arXiv:2607.23608 |
| 3 | Li et al. (2025/2026) | VLM으로 재활 dose·impairment 평가, 한계 보고 | arXiv:2511.17727 · PLOS Digit Health |

### 영향

**"센서 오차 → AI 출력"은 2022년 논문이 이미 개념을 세웠고, "LLM/VLM 입력 교란 민감도"는 매우 활발한 분야입니다.** 특히:
- **ST-VLM**이 "**VLM은 kinematic 수치를 못 읽는다**"를 이미 보였습니다 → **우리 PR-1의 부정적 결과가 나오면 ST-VLM의 반복**이 됩니다.
- **Nature 2026 prompt injection**이 "**VLM 입력 조작 → 출력 변화**"를 보였습니다 → **우리 PR-1의 긍정적 결과가 나오면 그 연장**입니다.

**→ 즉 PR-1은 어느 방향이든 "기존 결과의 재확인"으로 보일 위험이 있습니다.**

---

## 5. 분야별 현황 지도 — ARAT 자동채점은 특히 붐빕니다

| # | 논문 | 방법 | 게재지·ID |
|---|---|---|---|
| 1 | Ahmed & Rikakis (2025) | 다중시점 비디오 + SlowFast/I3D/Transformer + HBM | arXiv:2505.01680 |
| 2 | Weikert et al. (2025) | **item-level ARAT**, 웨어러블 센서 | ICORR 2025, PMID 40644012 |
| 3 | (ICORR 2025) | body-worn IMU로 ARAT 추정 | doi 10.1109/icorr66766.2025.11063104 |
| 4 | **IdentiARAT** (2025) | wrist IMU + MiniROCKET로 **ARAT 항목 자동 식별** | ICORR 2025, arXiv:2504.12921 |
| 5 | RAST-G@ (2025) | **RGB-D + ST-GCN + transformer attention** → 재활 운동 품질 점수. KIMORE/NRC | arXiv:2510.00049 · code: github.com/LimSuH/NRC-rehab |
| 6 | 15-item ARAT 신뢰도·타당도 (2025) | ARAT 단축판 결정규칙 | Disabil Rehabil, doi 10.1080/09638288.2025.2603843 |
| 7 | Using Wearable IMU to Estimate Clinical Scores (2022) | ARAT 합계 R²=0.93, MAE 2.9점 | PMC9110656 |
| 8 | IMAS (2025) | multimodal(clinical+sensor+neuroimaging) ML로 FMA 예측 R²=0.75 | PMC12646571 |
| 9 | Phase-specific multimodal biomarkers (2025) | 근골격 운동역학 모델링으로 설명가능 평가 | Front Neurosci, doi 10.3389/fnins.2025.1737407 |
| 10 | Padilla-Magaña et al. (2022) | ARAT 16활동 장갑 계측 | Sensors 22(10):3604 |

**→ "ARAT를 센서/영상으로 자동 채점"은 2022–2025 사이에 최소 10편이 나왔습니다.** 우리가 그중 하나가 되려면 차별점이 매우 날카로워야 합니다.

---

## 6. 살아남은 좁은 공백 후보 3개 (모두 불확실)

| # | 후보 | 왜 아직 살아있나 | 방어 가능성 |
|---|---|---|---|
| **A** | **생성형 VLM(영상+언어)에게 주입된 운동학 수치의 오류가 ARAT 순서형 항목 점수로 전파되는가** | 검색한 선행연구는 (a) **정형 센서 점수**(2022), (b) **이미지 아티팩트**(npj 2025), (c) **텍스트 프롬프트 교란**(COLING 2025), (d) **프롬프트 주입 공격**(Nature 2026) 중 하나. **"영상+운동학 수치 → 순서형 임상 항목 점수"의 오류 전파는 못 찾음** | 🟡 **중** — 조합이 특수하지만, 요소들이 전부 선행됨. **심사에서 "incremental" 판정 위험** |
| **B** | **생성형 VLM 입력에서의 품질 게이팅 효과** | EVGS·JMIR QC는 **골격 기반 DL 분류기**를 씀. **생성형 VLM의 프롬프트 입력을 품질로 선별**하는 연구는 못 찾음 | 🟡 **중** — 개념은 선행, 적용 대상만 다름 |
| **C** | **가림이 임상 지표(K1)를 몇 배 오염시키는지의 정량화** | Hand Visibility Detector는 **HPE 관절 오차**로 보고. **임상 지표 배수**로 환산한 것은 못 찾음 | 🟠 **낮음** — "단위 변환"에 가까움 |

### ⚠️ 후보 A의 치명적 약점

**ST-VLM이 "VLM은 kinematic 요소를 못 읽는다"를 이미 보였습니다.**
→ **우리 PR-1이 null이면** "VLM이 수치를 안 읽는다"는 **ST-VLM의 반복**입니다.
→ **우리 PR-1이 유의하면** "입력 오염 → 출력 변화"는 **Nature 2026 prompt injection의 연장**입니다.

**즉 PR-1 단독으로는 어느 방향이든 신규성이 약합니다.**

---

## 7. 권고 (수정된 전략)

| 이전 전략 | 수정 |
|---|---|
| 1편 = 손가락 RGB-D 검증 (독립) | ❌ **철회.** GMH-D와 충돌 |
| 2편 = 오류 전파 (주 논문) | 🟡 **유지하되 차별점 재설계 필요** |
| — | ✅ **새 중심축 후보: "품질 게이팅 + 보류(abstention)의 효과를 생성형 VLM에서 검증"** |
| — | ✅ **또는 "1편+2편을 합쳐 하나의 논문으로"** (검증 + 응용) |

### 왜 "품질 게이팅 + 보류"를 중심에 두는가

1. **EVGS·JMIR QC는 "품질을 평가"에서 멈춥니다.** "품질로 입력을 선별하면 **AI 판정이 실제로 좋아지는가**"는 그 다음 질문인데, 그들은 **DL 분류기**를 씁니다.
2. **생성형 VLM은 "보류"가 자연스럽습니다** (`null`을 주면 "추정 없음"으로 처리). 이건 **xAARA(보류)와 EVGS(품질평가)의 교집합**인데, **생성형 VLM에서 검증된 적이 없습니다.**
3. **우리 A3 vs R 설계가 정확히 이걸 겨냥합니다.** 즉 **설계를 바꿀 필요 없이 프레이밍만 바꾸면 됩니다.**

---

## 8. 검색 한계 (반드시 명시)

| 항목 | 상태 |
|---|---|
| 검색 DB | PubMed(E-utilities), 웹 검색(복수 provider) |
| **미검색 DB** | **Scopus, Embase, Web of Science, ACM DL, IEEE Xplore 전체, Google Scholar 전체** |
| 검색어 | 각 절에 기록 (약 15개) |
| **전수조사 여부** | ❌ **아니다.** PRISMA식 체계적 검색이 아니다 |
| **따라서** | **"없다"고 단정하지 않는다.** 표현은 **"내가 확인한 범위에서는 못 찾았다"** |
| 반복 실패 | PubMed에서 복잡한 불리언 조합 3건이 `totalCount=0` → **PubMed 검색식이 너무 좁았다.** 이건 **결과 없음이 아니라 검색 실패**다 |

**⚠️ 이 감사 자체가 불완전합니다.** 진짜 "새로운가"를 확정하려면 **Scopus/IEEE Xplore에서 별도 검색**이 필요합니다.

---

## 9. 내가 틀린 이유 (기록)

| 원인 | 내용 |
|---|---|
| **타깃 검색만 했다** | "우리 계획과 겹치는 것"만 찾았고, **분야 전체를 훑지 않았다** |
| **사용자 기존 노트를 교차확인하지 않았다** | `CHANGELOG.md` 2026-09-22 항목 7번에 **"Amprimo 2024"** 가 이미 있었다 |
| **"없다"를 너무 쉽게 말했다** | 정확한 표현은 **"내가 확인한 범위에서는 못 찾았다"** |
| **검색 실패를 결과 없음으로 오해했다** | PubMed `totalCount=0`을 "선행연구 없음"으로 해석했다. 실제로는 **검색식이 너무 좁았다** |

---

## 10. 새로 확인된 핵심 논문 (우리 논문에 인용 필요)

| # | 논문 | 우리 논문에서의 역할 |
|---|---|---|
| 1 | **Amprimo et al. 2024 (GMH-D)**, doi 10.1016/j.bspc.2024.106508 | **"MediaPipe + RGB-D가 손가락 수준에서 쓸 만하다"는 타당성 근거** |
| 2 | **EVGS 품질평가 2025**, doi 10.3390/mps8040071 | **품질 게이팅의 선행** — "우리는 생성형 VLM으로 확장" |
| 3 | **JMIR Post Hoc QC**, doi 10.2196/preprints.26825 | **무마커 모캡 품질관리의 선행** |
| 4 | **Hand Visibility Detector**, arXiv:2608.11574 | **관절별 가시성 추정의 선행** |
| 5 | **Metamorphic Testing HPE 2023**, arXiv:2303.04566 | **가림이 HPE를 망친다는 정량 근거** |
| 6 | **ST-VLM** | 🔴 **"VLM은 kinematic을 못 읽는다" — 우리 PR-1의 직접 경쟁** |
| 7 | **Nature 2026 prompt injection**, doi 10.1038/s44484-026-00014-6 | **VLM 입력 조작 → 출력 변화의 선행** |
| 8 | **Characterizing sensor accuracy requirements 2022** | **센서오차→AI 출력의 개념 선행** |
| 9 | **BioGait-VLM**, arXiv:2603.08564 | **VLM + 생체역학 토큰화의 선행** |
| 10 | **RAST-G@**, arXiv:2510.00049 | **RGB-D + ST-GCN 재활 품질 점수의 선행** |

---

# v2 확장 (2026-09-24) — Semantic Scholar + OpenAlex

## 11. 확장 검색 전문 (재현 가능 기록)

### 11.1 사용한 도구·엔드포인트

| 도구 | 엔드포인트 | 인증 | 비고 |
|---|---|---|---|
| Semantic Scholar | `https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=...&fields=title,year,externalIds,citationCount,venue[,abstract]&limit=N` | **없음(무키)** | `fetch_content`로 직접 호출. **무키 공용 풀은 rate limit이 있어 첫 시도에서 429**("Too Many Requests"). 재시도로 성공. **1초 1회 권장** |
| OpenAlex | `https://api.openalex.org/works?search=...` | **없음** (`OPENALEX_API_KEY missing`) | `feynman_science_database_search(source="openalex")`. **익명/데모 예산으로 throttle 경고 발생** |

**S2 질의 문법:** `+`=AND, `|`=OR, `"..."`=구문. `limit` 상한 1000.

### 11.2 Semantic Scholar 질의 9건

| # | 질의 | 총건수 | 상위 히트(신규 판정에 영향) |
|---|---|---|---|
| S2-1 | `"vision language model" + (abstention\|refusal\|deferral)` | **140** | Selective "Selective Prediction" (ACL 2024) · MedVIGIL (2605.07919) · Confident but Unreliable (2608.02790) · Calibrated Triage (2606.15910) · PARITY (2609.05540) · VirtueBench (2603.07071) · Explicit Abstention Knobs (2601.00138) · Look Again Before You Abstain (2606.16667) |
| S2-2 | `("pose estimation"\|"hand tracking"\|"RGB-D") + rehabilitation + validity` | **29** | Gait & Posture 2025 무마커 모캡 SR(38회) · **Impact of Hand Impairment and Occlusions on HPE (2606.17427)** · From Optical to AI-Driven Markerless MoCap (Bioengineering 2026) · C-MORE Box and Blocks (2026) · contactless finger motion depth (CBM 2021, 23회) |
| S2-3 | `"Fugl-Meyer" + (automatic\|automated\|AI) + scoring` | **109** | **Automated RGB-D FMA-UE (Brain Sci 2022)** · **Clinical validation of depth-camera FMA-UE (Clin Rehabil 2024)** · FMA-UE from wearable (IEEE JBHI 2025) · Cellphone-based FMA (TNSRE 2019) · Automated FMA (TNSRE 2018, 104회) · Learning to assess quality of stroke rehab exercises (IUI 2019, 78회) |
| S2-4 | `("quality gating"\|"quality gate"\|"input quality"\|"quality control") + ("vision language model"\|"video language model"\|"multimodal large language")` | **134** | 🔴 **Edges Before Embeddings: Confidence-Aware Blur Gate for VLM Pipelines (2606.25838)** · 🔴 **VLM for automated quality control (Sci Rep 2026, PMC13439064)** · Med-K2N · Quality-Driven Efficiency in VLM Customization (UBMK 2025) |
| S2-5 | `("frame selection"\|"keyframe selection"\|"frame sampling"\|"sparse frame") + (video) + (quality\|reliability\|robust)` | **600** | KFS-Bench (WACV 2026) · VideoEspresso (CVPR 2025, 101회) · Task-Driven Dual-Path Keyframe Selection (IEEE Access 2026) · KS-FQA (IET IP 2020) · Systematic frame selection and QA (Multimedia Systems 2025) |
| S2-6 | `"Action Research Arm Test" + (automatic\|automated\|machine learning\|deep learning\|scoring)` | **733** | Weikert item-level ARAT (ICORR 2025) · ARAT skipping-item psychometrics (2022) · ASAR 감정상태 (ICMI 2023) · ARAT vs FMA 비교 (APMR 2006, 162회) · ARAT 조기측정 특성 (APMR 2006, 234회) |
| S2-7 | `("hand pose estimation"\|"hand tracking") + occlusion + (accuracy\|error\|degradation)` | **203** | **Impact of Hand Impairment and Occlusions on HPE (2606.17427)** · Visual-inertial hand tracking robust to occlusion (Science Robotics 2021, 75회) · Partially Occluded Hands dataset (ACCV 2018) · 3D-AMTA occlusion-aware (IROS 2025) · Aleatoric uncertainty for 3D HPE (2509.01242) |
| S2-8 | `(rehabilitation\|"motor assessment"\|"clinical assessment") + ("vision language model"\|"multimodal large language model"\|"video language model") + (assessment\|scoring\|evaluation)` | **38** | 🔴 **Li 2026 PLOS Digit Health (pdig.0001506)** · 🔴 **Ye 2026 MLLM 재활 벤치마크 (Sci Rep, s41598-026-71999-w)** · 🔴 **Auditing MLLM Raters: Central Tendency Bias in Clinical Ordinal Scoring (2605.16386)** · RehabGen (IMWUT 2026) · MoChat (IEEE JBHI 2025) · Perception/assessment/coaching SR (Front Rehabil Sci 2026) |
| S2-9 | `("Action Research Arm Test"\|"Fugl-Meyer"\|ARAT) + ("vision language"\|"GPT-4V"\|"multimodal large language"\|"video language")` | **0** | **결과 없음.** ⚠️ **질의가 좁아서 0일 수 있다.** "ARAT/FMA × 생성형 VLM" 조합의 직접 선행을 못 찾았다는 **약한 음성 증거**로만 사용 |

### 11.3 OpenAlex 질의 4건

| # | 질의 | 총건수 | 상위 히트 |
|---|---|---|---|
| O-1 | `vision language model abstention deferral clinical decision` | 235 | Capabilities of Gemini Models in Medicine (W4396570449, 2024) |
| O-2 | `input quality selection gating improves machine learning clinical assessment` | 23,714 | Litjens 2017 의료영상 DL 서베이 (W2592929672) |
| O-3 | `video language model frame sampling selection rehabilitation movement assessment` | 10,071 | Cochrane VR 재활 리뷰 (W2121860971, 2015) |
| O-4 | `vision language model ordinal clinical score rehabilitation video input quality abstention` | **3** | 🔴 **NeuroSift: Task-Aware QA of Multimedia Data in Remote Parkinson Assessment (W7167579981, JMIR 2026, PMID 42612206)** · Ye 2026 (W7213604003) · 정신분열 재활 AI 스코핑 리뷰 (W7134224588) |

**O-4는 질의가 매우 좁아 총 3건만 나왔고, 그중 1건(NeuroSift)이 §12의 최근접 경쟁자다.** 이는 "이 조합을 정면으로 다룬 논문이 거의 없다"는 신호이지만, **동시에 OpenAlex 익명 예산으로 50건씩 잘려(`records_truncated: true`) 전수 확인이 안 됐다는 뜻**이기도 하다.

### 11.4 v2 검색의 한계 (v1보다 개선됐지만 여전히 불완전)

| 항목 | 상태 |
|---|---|
| 새로 추가된 DB | Semantic Scholar(전 분야, 초록 포함), OpenAlex(2.5억+ works) |
| **여전히 미검색** | **Scopus · Embase · Web of Science · ACM DL · IEEE Xplore (전체 열람) · Google Scholar 전체** |
| S2 rate limit | 무키 공용 풀 → 429 발생. **재현 시 1초 간격 필요** |
| OpenAlex 예산 | 익명 → `records_truncated: true`, **질의당 50건 상한** |
| S2-9 = 0건 | **질의 설계 의존.** "없다"의 근거로 쓰지 않음 |
| 결론 | **여전히 PRISMA식 전수조사가 아니다.** 표현은 **"내가 확인한 범위에서는 못 찾았다"** |

---

## 12. 갱신된 신규성 판정

### 12.1 🔴 최근접 경쟁자 5편 (Plan B를 직접 위협)

| # | 논문 | 무엇을 했나 | 우리와의 거리 | ID |
|---|---|---|---|---|
| **C1** | **NeuroSift: Task-Aware Quality Assurance of Multimedia Data in Remote Parkinson Disease Assessment** (2026) | **원격 파킨슨 평가용 멀티미디어 데이터의 "과제 인지형 품질 보증"** ML 모델 개발·검증. University of Rochester(Hoque lab) | **가장 가깝다.** "원격 재활 + 멀티미디어 + 품질 보증 + 과제 인지"가 정확히 겹침. **차이: (a) ML 분류기지 생성형 VLM 아님 (b) 파킨슨이지 뇌졸중/ARAT 아님 (c) 품질 보증 자체가 목적이지 "게이팅이 점수를 개선하는가"의 효과 측정이 아님** | JMIR 2026, doi 10.2196/91756, PMID 42612206, OpenAlex W7167579981 |
| **C2** | **Edges Before Embeddings: A Confidence-Aware Blur Gate for Vision-Language Pipelines** (2026-06-24) | **이미지 품질 게이트**(sharp/blurred/**uncertain** 3분류)를 만들어 **VLM 파이프라인에 라우팅**. 고전적 **selective prediction**에 근거한 confidence-aware routing 형식화. F1 0.9803 / AUC 0.9989 / 17MB ONNX / CPU ~7ms. **"Magika 콘텐츠타입 검출 · risk-controlled OCR with VLMs · DocVLM에서 반복되는 설계 패턴"이라고 명시** | **방법론적 직계 선행.** "게이트 → VLM 라우팅"이 이미 제안됨. **차이: (a) blur 축(가림/추적실패 아님) (b) 문서/OCR 도메인(임상 운동 아님) (c) 순서형 임상 점수 없음 (d) 단일 시드·단일 blur 분포·calibration 미측정(저자 자인)** | arXiv:2606.25838, doi 10.5281/zenodo.19765336 |
| **C3** | **Vision-language models for human motion understanding: Lessons from stroke rehabilitation** (2026-07-06) | **건강인 20명 + 뇌졸중 51명.** VLM으로 **재활 dose와 impairment를 영상에서 추정**. 결과: **"dose 추정치는 시각정보를 배제한 기준선과 비슷하고, impairment 점수는 신뢰성 있게 예측 불가"**. 모델: LLaVA-OneVision, NVILA, **Qwen2.5-VL**, InternVL3, Video-LLaVA, Gemini 2.5, GPT-4 | 🔴 **우리 PR-1/PR-2의 직접 경쟁.** "VLM은 재활 영상에서 세밀한 운동을 못 읽는다"를 **대규모로 이미 보임**. **우리는 이걸 반박하는 게 아니라 "게이팅이 이 실패를 완화하는가"로 가야 함** | PLOS Digit Health 5(7):e0001506, doi 10.1371/journal.pdig.0001506, PMID 42406872 |
| **C4** | **Systematic benchmarking of evaluation paradigms, safety boundaries, and clinical reasoning gaps for multimodal LLMs in rehabilitation** (2026-09-19) | MLLM의 **재활 평가 패러다임·안전 경계·임상 추론 격차**를 체계 벤치마크. 키워드에 **Kinematics·Situation awareness·Eye tracking** 포함 | **프레이밍 경쟁.** "재활 MLLM의 안전 경계"를 이미 제목에 걸었다. **우리는 "게이팅 개입의 효과"라는 인과 결과가 필요** | Sci Rep 2026, doi 10.1038/s41598-026-71999-w, OpenAlex W7213604003 |
| **C5** | **Auditing Multimodal LLM Raters: Central Tendency Bias in Clinical Ordinal Scoring** (2026) | **MLLM 채점자가 임상 순서형 채점에서 중심경향 편향을 보임**을 감사 | 🔴 **우리 PR-2의 직접 위협.** "순서형 채점"에서 LLM 편향이 이미 감사됨. **우리 게이팅은 이 편향을 줄이는 개입으로 포지셔닝 가능** | arXiv:2605.16386 |

### 12.2 VLM 입력 열화 · 보류/abstention (Tier 2 — 활발한 분야)

| # | 논문 | 핵심 | ID |
|---|---|---|---|
| 1 | **MedVIGIL: Evaluating Trustworthy Medical VLMs Under Broken Visual Evidence** (2026) | **깨진 시각 증거** 하 의료 VLM 신뢰성 | arXiv:2605.07919 |
| 2 | **Confident but Unreliable: A Behavioral Safety Audit of VLMs on Brain MRI** (2026) | 뇌 MRI에서 VLM이 **확신하지만 부정확** | arXiv:2608.02790 |
| 3 | **Small VLMs Know When They Are Wrong But Cannot Say So: Stated vs Internal Confidence Under Realistic Image Degradation** (2026) | **표현된 확신 ≠ 내부 확신** (이미지 열화 하) | arXiv:2607.22034 |
| 4 | **Bigger or Cheaper? Scale and Quantization Effects on Uncertainty Signals in VLMs Under Image Degradation** (2026) | 열화 하 **불확실성 신호**에 대한 규모/양자화 효과 | arXiv:2607.24440 |
| 5 | **Selective "Selective Prediction": Reducing Unnecessary Abstention in Vision-Language Reasoning** (ACL 2024) | 🔴 **"불필요한 보류(over-abstention)"를 명명된 문제로 제기** | arXiv:2402.15610 (인용 42) |
| 6 | **Learning Conformal Abstention Policies for Adaptive Risk Management in LLM and VLM** (2025) | conformal **보류 정책 학습** | arXiv:2502.06884 (인용 22) |
| 7 | **Calibrated Triage, Not Autonomy: Confidence Estimation for Medical VLMs** (2026) | 의료 VLM **확신도 추정** → 자율 아닌 분류 | arXiv:2606.15910 |
| 8 | **Explicit Abstention Knobs for Predictable Reliability in Video Question Answering** (2025) | **보류 손잡이**로 예측 가능한 신뢰성 | arXiv:2601.00138 |
| 9 | **Look Again Before You Abstain: Budgeted Conformal Evidence Acquisition for Reliable VLM** (2026) | 보류 전 **증거 추가 수집** | arXiv:2606.16667 |
| 10 | **VirtueBench: Evaluating Trustworthiness under Uncertainty in Long Video Understanding** (2026) | **긴 영상** 불확실성 하 신뢰성 벤치 | arXiv:2603.07071 |
| 11 | **Knowing When Not to Answer: Abstention and Refusal Reasoning in VLMs (PARITY)** (2026) | 답할 수 없는 질의에서 **보류/거부** 감사 | arXiv:2609.05540 |
| 12 | **Act or ask: Interactive construction robots via VLMs with confidence-guided decision deferral** (2026) | **확신도 기반 결정 보류(deferral)** — 임상 밖 | Adv Eng Inform, doi 10.1016/j.aei.2026.104454 |
| 13 | **Enhancing Clinician Decision-Making via Uncertainty-Aware Multi-Expert Fusion for Stroke Rehabilitation** (2026) | 🔴 **뇌졸중 재활 + 불확실성 인지** | arXiv:2606.24960 |
| 14 | **PEER: Patience-Based Early Exiting with Rejection** (2026) | **거부(rejection)**로 신뢰성↑ (MIMIC-III 90.73%, 2.79%만 거부) | J Biomed Inform, doi 10.1016/j.jbi.2026.104988, PMID 41571171 |
| 15 | **Accuracy Overstates Evidence Grounding and Abstention Reliability in Mammography VLMs** (2026) | 정확도가 **보류 신뢰성을 과대평가** | medRxiv, doi 10.64898/2026.09.10.26361944 |

### 12.3 가림 · 손 자세 (Tier 3 — 우리 가림 축의 선행)

| # | 논문 | 핵심 | ID |
|---|---|---|---|
| **1** | **Impact of Hand Impairment and Occlusions on Hand Pose Estimation Accuracy in Augmented Reality Applications** (2026) | 🔴 **손상(impairment) × 가림 × HPE 정확도**를 함께 다룸 | arXiv:2606.17427 |
| 2 | **Visual-inertial hand motion tracking with robustness against occlusion, interference, and contact** (2021) | 가림·간섭·접촉에 견고한 손 추적 | Science Robotics, doi 10.1126/scirobotics.abe1315 (인용 75) |
| 3 | Partially Occluded Hands: A Challenging New Dataset for Single-Image HPE (2018) | **부분 가림 손** 데이터셋 | ACCV, doi 10.1007/978-3-030-20873-8_6 |
| 4 | 3D-AMTA: Occlusion-Aware Real-Time 3D Hand Pose Estimation (2025) | **가림 인지** 손 자세 | IROS, doi 10.1109/IROS60139.2025.11246826 |
| 5 | Learning Correlation-aware Aleatoric Uncertainty for 3D Hand Pose Estimation (2025) | HPE **불확실성 추정** | arXiv:2509.01242 |
| 6 | Reliability and validity of current computer vision based motion capture systems in gait analysis: A systematic review (2025) | **무마커 모캡 SR** | Gait & Posture, doi 10.1016/j.gaitpost.2025.04.016 (인용 38) |
| 7 | From Optical to AI-Driven Markerless Motion Capture in Motor Learning and Rehabilitation (2026) | 무마커 모캡 리뷰(재활) | Bioengineering, doi 10.3390/bioengineering13070776, PMID 42510442 |
| 8 | Perception, assessment, and coaching: a systematic review and taxonomy of CV-based physical rehabilitation (2026) | **CV 재활 기법 SR + 택소노미** | Front Rehabil Sci, doi 10.3389/fresc.2026.1906327, PMID 42548713 |

### 12.4 RGB-D/depth 카메라 FMA·ARAT 자동화 (Tier 4 — **v2에서 대량 신규 발견**)

| # | 논문 | 무엇을 했나 | ID |
|---|---|---|---|
| **1** | **A Novel Automated RGB-D Sensor-Based Measurement of Voluntary Items of the FMA-UE: A Feasibility Study** (2022) | 🔴 **RGB-D 센서로 FMA-UE 자발 항목 자동 측정** | Brain Sci 12(10):1380, doi 10.3390/brainsci12101380, PMID 36291314 |
| **2** | **Clinical validation of automated depth camera-based measurement of the FMA-UE** (2024) | 🔴 **depth 카메라 FMA-UE의 임상 타당도 검증** | Clin Rehabil, doi 10.1177/02692155241251434, PMID 38693881 |
| 3 | Estimating Upper Extremity FMA Scores From Reaching Motions Using Wearable Sensors (2025) | 웨어러블로 **FMA 점수 추정** | IEEE JBHI, doi 10.1109/JBHI.2025.3542037, PMID 40031831 |
| 4 | Cellphone-Based Automated FMA (2019) | 스마트폰으로 **자동 FMA** | IEEE TNSRE, doi 10.1109/TNSRE.2019.2939587, PMID 31502981 (인용 36) |
| 5 | Automated Evaluation of Upper-Limb Motor Function Impairment Using FMA (2018) | **자동 FMA 평가** | IEEE TNSRE, doi 10.1109/TNSRE.2017.2755667, PMID 28952944 (인용 104) |
| 6 | Learning to assess the quality of stroke rehabilitation exercises (2019) | **뇌졸중 재활 운동 품질 평가 학습** | IUI, doi 10.1145/3301275.3302273 (인용 78) |
| 7 | Automatic rehabilitation assessment method of upper limb motor function based on posture and distribution force (2024) | 자세+분포력 기반 자동 평가 | Front Neurosci, doi 10.3389/fnins.2024.1362495, PMID 38440394 |
| 8 | Estimation of FMA-UE Sub-Scores Using a Mixup-Augmented LSTM Autoencoder and Wearable Sensor Data (2025) | **FMA-UE 하위점수** 추정 | Sensors, doi 10.3390/s25216663, PMID 41228884 |
| 9 | Automated Prediction of Item-Level ARAT Scores From Wearable Sensors (2025) | **ARAT 항목 수준** 자동 예측 | ICORR, doi 10.1109/ICORR66766.2025.11063162, PMID 40644012 |
| 10 | AI-driven low-cost rehabilitation exergame as a lightweight framework for stroke assessment (2026) | 저비용 **재활 엑서게임** 평가 | npj Digit Med, doi 10.1038/s41746-026-02383-1, PMID 41606212 |
| 11 | C-MORE: Computer Vision for Movement Observation and Recovery Enhancement — Box and Blocks Test (2026) | **CV로 BBT** | Bioengineering, doi 10.3390/bioengineering13060602, PMID 42351847 |
| 12 | A contactless method to measure real-time finger motion using depth-based pose estimation (2021) | **depth 기반 손가락 운동** | Comput Biol Med, doi 10.1016/j.compbiomed.2021.104282, PMID 33631496 (인용 23) |
| 13 | Exercise repetition rate measured with simple sensors at home can be used to estimate Upper Extremity FMA score (2023) | **가정 반복률 → FMA 추정** | Front Rehabil Sci, doi 10.3389/fresc.2023.1181766, PMID 37404979 |
| 14 | Extended reality to assess post-stroke manual dexterity: BBT vs immersive VR(컨트롤러) vs **hand-tracking** vs mixed-reality (2024) | 4가지 조건 **직접 비교** | J NeuroEng Rehabil, doi 10.1186/s12984-024-01332-x, PMID 38491540 (인용 31) |
| 15 | Psychometric properties of the ARAT using decision rules for skipping items (2022) | ARAT **항목 건너뛰기 규칙** 심리측정 | Disabil Rehabil, doi 10.1080/09638288.2022.2153177, PMID 36476063 |
| 16 | ASAR Dataset and Computational Model for Affective State Recognition During ARAT Assessment (2023) | **ARAT 수행 중 정서상태** 인식 | ICMI Companion, doi 10.1145/3610661.3617154 |

**⚠️ Tier 4의 의미:** **"depth 카메라로 FMA-UE를 자동 채점"은 이미 임상 검증까지 끝난 분야**다. 즉 **"RGB-D로 FMA/ARAT 자동채점"은 신규성이 없다.** 우리 차별점은 **생성형 VLM + 품질 게이팅**이어야 하며, 그 점에서 Tier 1(C1·C2·C3)이 진짜 경계다.

### 12.5 프레임 선택 for 비디오 LM (Tier 5)

| # | 논문 | ID |
|---|---|---|
| 1 | KFS-Bench: Comprehensive Evaluation of Key Frame Sampling in Long Video Understanding (2026) | WACV 2026, arXiv:2512.14017 |
| 2 | VideoEspresso: Chain-of-Thought Dataset via **Core Frame Selection** (2025) | CVPR 2025, arXiv:2411.14794 (인용 101) |
| 3 | Task-Driven Dual-Path Keyframe Selection: Enhancing Multimodal Video Understanding (2026) | IEEE Access, doi 10.1109/ACCESS.2026.3698553 |
| 4 | Optimizing Frame Selection for Improved Video Quality Assessment Through Embedding Similarity (2025) | Electron Imaging, doi 10.2352/ei.2025.37.9.iqsp-251 |
| 5 | Systematic frame selection and quality assessment for efficient video summarization (2025) | Multimedia Systems, doi 10.1007/s00530-025-01860-z |
| 6 | KS-FQA: Keyframe selection based on face quality assessment (2020) | IET Image Process, doi 10.1049/ipr2.12008 (인용 16) |
| 7 | Quality-Based Score Normalization and Frame Selection for Video-Based Person Authentication (2008) | doi 10.1007/978-3-540-89991-4_1 |

**→ "품질 기반 프레임 선택"은 2008년부터 있고, 비디오 LM용 keyframe sampling은 2024~2026에 매우 활발하다.** 우리 R 조건(품질 게이트)은 **이 흐름의 임상 버전**이다.

### 12.6 후보 B 재판정

| v1 판정 | v2 판정 |
|---|---|
| 후보 B = **"생성형 VLM 입력에서의 품질 게이팅 효과"**, 🟡 중, "개념은 선행, 적용 대상만 다름" | **🟡 중 유지, 단 근거가 바뀜.** |
| — | **새 반박:** C1(NeuroSift 2026)이 **"원격 재활 멀티미디어 과제인지형 품질보증"**을 이미 했고, C2(arXiv:2606.25838)가 **"게이트 → VLM 라우팅 + selective prediction"**을 이미 형식화했다. |
| — | **살아남은 것:** **"품질 게이팅이 생성형 VLM의 순서형 임상 점수를 실제로 개선하는가"**와 **"그 대가로 얼마나 과잉 보류하는가"**는 **측정된 적이 없다.** C2는 calibration을 "질적"으로만 봤고(저자 자인), C1은 ML 분류기이며, C5는 편향을 감사했을 뿐 개입하지 않았다. |
| — | **즉 신규성은 "제안"이 아니라 "측정"에 있다.** → §13에서 이 표현으로 재설계한다. |

---

## 13. 차별점 재설계 — Plan B 중심축

### 13.1 새 중심축 (한 문장)

> **"품질 게이팅 + 보류(abstention)를 생성형 VLM의 순서형 임상 채점에 적용하면, 점수 정확도가 실제로 오르는가 — 그리고 그 대가는 과잉 보류(over-abstention)인가?"**

**v1의 "PR-1 = 오류 전파"는 중심축에서 내려간다.** 이유: §4·§12.1에서 보듯 C3(Li 2026)와 ST-VLM이 "VLM은 재활 운동 수치를 못 읽는다"를 이미 보였다. **PR-1은 어느 방향이든 재확인으로 보일 위험이 크다.** 대신 PR-1은 **"왜 게이팅이 필요한가"의 기전 증거**로 격하한다.

### 13.2 3개 연구질문 (재설계)

| RQ | 질문 | 설계 대응 | 지위 |
|---|---|---|---|
| **RQ-B1 (효과)** | 품질 게이팅이 생성형 VLM의 **ARAT 순서형 채점 오차를 줄이는가?** | **A2(전체 수치) vs A3(품질 통과 수치)** — 같은 영상·같은 라벨, 수치 집합만 다름 | **확증적 (PR-1)** |
| **RQ-B2 (대가)** | 게이팅의 이득이 **정보량 감소로 설명되지 않는가**? 과잉 보류의 크기는? | **A3 vs R**(같은 양 무작위 제거) = **PR-2** + **보류율(A3)** + **(보류율, MAE) Pareto**(Q1 sweep) | **확증적 (PR-2)** + 1급 기술 |
| **RQ-B3 (안전)** | 게이팅이 **큰 오차(≥2점) 비율**을 줄이는가? (평균이 아니라 위험) | **A2 vs A3의 "큰 오차 비율"** + 순서형 오차 분포 | **탐색적** |
| — | (기전, 격하) 주입 오류가 점수로 전파되는가 | **bias_3u** (H5) | **탐색적·기전** |

**⚠️ 조건 이름 정정 (2026-09-24):** 계획서 §6의 실제 조건명은 **A1=영상만(수치 없음), A2=영상+전체 수치, A3=영상+품질통과 수치, A4=수치만(RGB 없음), R=같은 양 무작위 제거**다.
**→ "게이팅 on/off"는 A1 vs A2가 아니라 A2 vs A3이다.** (초안에서 A1 vs A2로 잘못 적었음)

### 13.3 포지셔닝 표 — "이미 있는 것"과 "없는 것"

| 구성요소 | 이미 있는 것 | 출처 | **우리가 더하는 것** |
|---|---|---|---|
| 이미지 품질 게이트 → VLM 라우팅 | ✅ blur 3분류 게이트 + selective prediction 형식화 | **C2 (arXiv:2606.25838)** | **가림/추적실패 축** · **순서형 임상 점수** · **규칙 기반(학습 불필요)** |
| 원격 재활 멀티미디어 품질 보증 | ✅ 과제인지형 QA | **C1 (NeuroSift, JMIR 2026)** | **생성형 VLM** · **게이팅의 인과 효과 측정** |
| VLM은 재활 수치를 못 읽음 | ✅ 20+51명 실증 | **C3 (Li 2026, PLOS DH)** | **그 실패를 게이팅이 완화하는지** |
| VLM 보류/abstention | ✅ conformal 정책·over-abstention 명명 | **Selective Selective Prediction 2024** · arXiv:2502.06884 | **임상 순서형 채점에서의 보류** |
| 순서형 채점 편향 | ✅ 중심경향 편향 감사 | **C5 (arXiv:2605.16386)** | **편향을 줄이는 개입(게이팅)으로서** |
| 품질 게이팅(골격 DL) | ✅ EVGS 2025 · JMIR QC · AGMA-PESS | §2 | **생성형 VLM 입력** |
| RGB-D로 FMA/ARAT 자동채점 | ✅ **임상 검증까지 완료** | **Tier 4: Brain Sci 2022 · Clin Rehabil 2024** | (없음 — **이 축은 신규성 없음**) |

### 13.4 세 가지 프레이밍 옵션과 권고

| 옵션 | 주장 | 점유 상태 | 위험 |
|---|---|---|---|
| **F1 안전 중심** | "게이팅은 평균 정확도를 크게 못 올리지만 **위험한 오채점(≥2점)을 줄인다**" | 부분 점유(C2가 calibration 미측정, C4가 safety boundary 언급) | 평균 효과가 null이면 논문이 약해 보임 |
| **F2 대가 중심** ⭐ | "게이팅의 **진짜 비용은 과잉 보류**다. (보류율, MAE) Pareto를 처음 측정한다" | **거의 비어 있음.** over-abstention은 NLP에서 명명됐지만 **임상 순서형 채점에서의 비용 곡선은 없음** | "비용만 측정"이라 기여가 작아 보일 수 있음 → F1과 묶어야 함 |
| **F3 기준선 중심** | "생성형 VLM 게이팅 **vs** 골격 DL 분류기 게이팅(EVGS/JMIR 방식) head-to-head" | 비어 있음 | **비교 대상 DL 분류기를 우리가 직접 구현해야 함** → 공수 큼. n이 작아 우열 판정 어려움 |

**권고: F2를 주 프레이밍, F1을 보조 결과로.** 즉 **"게이팅의 이득(위험 감소)과 비용(과잉 보류)을 함께 보고하는 첫 연구"**. F3은 **탐색적·후속 과제**로 남긴다(구현 공수·검정력 문제).

### 13.5 주장할 것 / 주장하지 않을 것 (심사 방어)

| ✅ 주장할 것 | ❌ 주장하지 않을 것 |
|---|---|
| "게이팅이 **생성형 VLM의 순서형 임상 점수**를 개선하는지 **처음 측정**한다" | "품질 게이팅 **개념**을 처음 제안한다" — C2·C1·EVGS가 선행 |
| "게이팅의 **과잉 보류 비용 곡선**을 처음 보고한다" | "VLM이 재활 운동을 못 읽는다" — C3가 이미 보임 (우리 출발점) |
| "규칙 기반 랜드마크 게이트로 **재현성·비용 우위**를 보인다" | "학습 게이트보다 우수하다" — 미검증 |
| "RGB-D로 FMA/ARAT를 자동 채점한다" → **인용만** | "RGB-D로 FMA/ARAT 자동채점이 새롭다" — Tier 4가 임상검증 완료 |
| "가림이 임상지표를 오염시킨다" → **기전 설명용** | "가림이 임상지표를 N배 오염시킨다"가 독립 기여라고 주장 (후보 C, 🟠 낮음) |

### 13.6 필요한 설계 추가 (최소 변경)

| # | 추가 | 이유 | 공수 |
|---|---|---|---|
| 1 | **보류율(abstention rate)을 1급 결과로 승격** | RQ-B2. Q 게이트가 이미 있으므로 **계산만** 하면 됨 | 낮음 |
| 2 | **Q1 임계값 sweep → (보류율, MAE) Pareto 곡선** | RQ-B2의 핵심 그림 | 중간 (재채점 N회) |
| 3 | **"큰 오차(≥2점) 비율" 별도 보고** | RQ-B3. 평균 MAE는 위험을 숨김 | 낮음 |
| 4 | **A4를 "Li 2026 시각정보 제거 기준선"으로 명시** (조건 추가 불필요) | C3(Li 2026)의 "dose ≈ 시각정보 배제 기준선"에 대응하는 조건이 **이미 A4(수치만, RGB 없음)** 다. 프레이밍만 추가 | 문서만 |
| 5 | **게이트 성격 명시**: "학습된 분류기가 아니라 **랜드마크 기하 규칙**" | C2(arXiv:2606.25838)와의 **정직한 차이** | 문서만 |
| 6 | **C5(중심경향 편향) 대응**: 순서형 오차의 **분포**(중심 쏠림)를 보고 | C5가 편향을 감사했으므로, 우리는 **개입 후 편향 변화**를 봄 | 낮음 |

**⚠️ 설계 골격(A0~R, Q 게이트, A1/A2/A3, PR-1/PR-2)은 바뀌지 않는다.** 프레이밍·결과 승격·기준선 1개 추가뿐이다.

### 13.7 신규성 등급 (정직한 자기평가)

| 항목 | 등급 | 근거 |
|---|---|---|
| "게이트 → VLM 라우팅" 개념 | **D (신규성 없음)** | C2가 형식화 |
| "원격 재활 멀티미디어 품질보증" | **D** | C1이 수행 |
| "RGB-D FMA/ARAT 자동채점" | **D** | Tier 4가 임상검증까지 완료 |
| **"생성형 VLM 순서형 임상채점에서의 게이팅 효과"** | **C+ ~ B−** | **개념은 선행, 이 조합의 인과 측정은 못 찾음** |
| **"과잉 보류 비용 곡선"** | **B−** | over-abstention은 NLP에서 명명, 임상 순서형에서 비용 곡선은 못 찾음 |
| **"게이팅이 큰 오차(위험)를 줄이는가"** | **C+** | 안전성 지표 관점은 C4가 인접 |

**→ 종합: 🟡 중.** **"incremental이지만 방어 가능"**. 심사에서 "요소들이 전부 선행됨"이라는 지적이 나올 것이 확실하므로, **§13.5 표를 초록·서론에 그대로 반영**해야 한다. **"우리가 처음 제안"이 아니라 "우리가 처음 측정"**으로 문장을 고정한다.

---

## 14. 연구계획서(`research-plan-v6.md`)에 반영할 변경 목록

| # | 위치 | 변경 | 근거 |
|---|---|---|---|
| 1 | §한장요약 | 중심축을 **"게이팅 효과 + 과잉 보류 비용"**으로 교체. "오류 전파"는 기전으로 격하 | §13.1 |
| 2 | §가설 H1~H4 | **H1(게이팅 효과)·H2(과잉 보류 비용)**를 주 가설로 승격. 오류 전파 가설을 H3(기전)으로 이동 | §13.2 |
| 3 | §PR-1/PR-2 | **PR-1 = 게이팅 효과(A1 vs A2)**, **PR-2 = 과잉 보류 Pareto(A2/A3/R)**, PR-3(탐색)=큰 오차 비율, PR-4(기전, 격하)=bias_3u | §13.2 |
| 4 | §다중비교 | 확증적 검정 = **PR-1·PR-2 2개만 Holm 유지** (개수 동일, 내용만 교체) | §13.2 |
| 5 | §실험 절차 | **Q1 sweep + Pareto 곡선** 단계 추가. **A1에 시각정보 제거 기준선** 추가 | §13.6 |
| 6 | §판정표 | "보류율"과 "큰 오차 비율" 행 추가 | §13.6 |
| 7 | §결정 근거 대장 | **신규 5건 등재**: C1 NeuroSift · C2 arXiv:2606.25838 · C3 Li 2026 · C4 Ye 2026 · C5 arXiv:2605.16386 | §12.1 |
| 8 | §금지사항 | **"품질 게이팅을 처음 제안한다" 표현 금지** 추가 | §13.5 |
| 9 | §서론/차별점 절 | **§13.3 포지셔닝 표를 그대로 삽입** | §13.3 |
| 10 | §인용 목록 | **Tier 4 (RGB-D/depth FMA 자동화) 16편 추가** — "우리 방법의 배경"으로 | §12.4 |

### 폐기·축소 확정

| 항목 | 조치 |
|---|---|
| "1편 = 손가락 RGB-D 검증" | ❌ **철회 확정** (v1에서 이미 철회, v2에서 Tier 4가 추가 확증) |
| "PR-1(오류 전파) = 주 결과" | ⬇️ **기전으로 격하** (C3·ST-VLM이 직접 경쟁) |
| "게이팅은 우리가 처음 제안" | ❌ **표현 금지** (C2) |
| "RGB-D로 FMA/ARAT 자동채점이 새롭다" | ❌ **표현 금지** (Tier 4) |

### 남은 외부 의존 (변경 없음)

Scopus·Embase·Web of Science·ACM DL·IEEE Xplore 전체 열람 · 임상 참조 점수(치료사 ARAT 3번·12번 채점) · 동결 해시·사전등록 체크박스.

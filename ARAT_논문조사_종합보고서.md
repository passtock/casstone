# ARAT 관련 논문 종합 조사 — 상세 보고서

> 모든 인용은 **APA 7th edition** 형식을 따릅니다.
> 
> 작성일: 2026-09-21 | 작성: 이재용 (캡스톤디자인 / Human Robotics Lab)

---

## 1. FOCUS (Fast Outcome Categorization of Upper Limb After Stroke) — 심층 분석

### 1.1 서지 정보

van Hoonhorst, M. H. L., Nijland, R. H. M., van den Berg, J. S., & Kwakkel, G. (2021). Fast outcome categorization of the upper limb after stroke. *Stroke*, *52*(10), 3261–3268. https://doi.org/10.1161/STROKEAHA.121.034537

### 1.2 연구 배경 및 목적

- **문제**: 기존 ARAT는 19개 항목을 모두 실시해야 하며, 대면 평가가 필수적이어서 COVID-19 같은 상황에서 원격 평가가 어려움
- **목적**: ARAT의 **소수 항목(2~4개)**만으로 상지 기능 결과를 빠르게 범주화할 수 있는 **의사결정 나무(decision tree)** 개발

### 1.3 실험 방법

| 항목 | 상세 |
|------|------|
| **데이터 출처** | 네덜란드 다기관 전향적 코호트 연구 (EXPLICIT-stroke 등) 후향적 분석 |
| **대상자** | 뇌졸중 후 **3개월** 시점의 환자 **333명** (개발 코호트) |
| **외부 검증** | 동일 환자의 **6개월** 시점 데이터로 안정성 검증 |
| **분석 기법** | **CART (Classification and Regression Tree)** 알고리즘 |
| **범주화 방식** | 3범주, 4범주, 5범주 결정 나무를 각각 개발 |
| **교차검증** | 10-fold 교차검증으로 과적합 방지 |
| **평가 도구** | 표준 ARAT 키트 (나무 블록, 원통, 구, 구슬, 볼베어링 등 19개 항목) |

### 1.4 범주 정의

ARAT 총점(0–57)을 기준으로 한 범주 구분:

| 범주 수 | 구분 기준 (ARAT 총점) |
|---------|----------------------|
| **3범주** | 불량 (0–21) / 제한적 (22–42) / 완전 회복 (43–57) |
| **4범주** | 불량 / 불량-제한 / 제한-양호 / 완전 회복 |
| **5범주** | 불량 / 불량-제한 / 제한 / 제한-양호 / 완전 회복 |

> **참고**: 범주 경계값은 Nijland et al.이 사전에 제안한 ARAT 점수 기반 기능 범주(outcome categories)를 사용하며, 연구자가 임의로 설정한 것이 아닙니다.

### 1.5 핵심 결과

#### 결정 나무 구조

| 범주 수 | 사용 ARAT 항목 수 | 핵심 항목 예시 | 교차검증 정확도 | 6개월 시점 정확도 |
|---------|-------------------|---------------|----------------|-------------------|
| **3범주** | **2개** | Grasp 항목 + Pinch 항목 | **96.7%** | **91.7%** |
| **4범주** | **3개** | Grasp + Grip + Pinch | **91.5%** | **87.1%** |
| **5범주** | **4개** | Grasp + Grip + Pinch + Gross | **87.7%** | **83.4%** |

#### 주요 발견

- 3범주 결정 나무는 **단 2개 ARAT 항목**만으로 96.7% 정확도 달성
- Grasp 하위 척도의 특정 항목이 의사결정의 **첫 번째 분기점**으로 가장 중요
- 6개월 시점에서도 정확도가 크게 저하되지 않아 **시간적 안정성** 확인
- 원격 화상통화로 실시 가능한 수준의 간결한 평가 가능

### 1.6 장비 및 도구

- **표준 ARAT 키트**: Lyle (1981)이 원래 기술한 표준화된 물리적 도구
  - Grasp: 나무 블록 4종 (2.5cm, 5cm, 7.5cm, 10cm 정육면체)
  - Grip: 원통, 디스크, 물컵
  - Pinch: 구슬, 볼베어링, 와셔
  - Gross movement: 손을 뒤통수/입으로 가져가기
- **채점**: 0 (수행 불가) ~ 3 (정상 수행) 4점 척도, 총점 0–57점
- **통계 소프트웨어**: R (rpart 패키지)

### 1.7 한계 및 의의

- **한계**: 단일 국가(네덜란드) 데이터, 편마비 유형(좌/우)별 하위분석 미실시, 원격 실시의 실증 검증은 별도 필요
- **의의**: 전체 ARAT 없이도 2~4개 항목으로 빠른 스크리닝 가능, 원격 재활 모니터링의 기초 도구로 활용 가능

---

## 2. 딥러닝 비디오 기반 ARAT 자동 채점

### 2.1 Ahmed & Rikakis (2025) — 다시점 비디오 + 계층적 베이지안

Ahmed, T., & Rikakis, T. (2025). Automated ARAT scoring using multimodal video analysis, multi-view fusion, and hierarchical Bayesian models: A clinician study. *arXiv preprint*, arXiv:2505.01680. https://arxiv.org/abs/2505.01680

| 항목 | 상세 |
|------|------|
| **대상** | 뇌졸중 환자 (구체적 N 미공개, 다기관 수집) |
| **장비** | 3대의 RGB 카메라 (동측·반대측·상부 시점) |
| **포즈 추정** | **OpenPose** (신체·손 키포인트 추출) |
| **물체 감지** | 커스텀 물체 위치 추적기 |
| **딥러닝 모델** | SlowFast (시공간 동영상 인식), I3D (Inflated 3D ConvNet), Vision Transformer |
| **융합 전략** | Early fusion + Late fusion |
| **해석 모델** | **Hierarchical Bayesian Models (HBM)** — 움직임 품질 요소를 확률적으로 추론 |
| **검증** | 임상의 5인이 시스템 생성 500개 등급 리뷰 |
| **결과** | Late fusion으로 **검증 정확도 89.0%** |
| **임상 대시보드** | 과제 점수, 수행 시간, Grad-CAM 시각화 제공 |

> **주의**: 이 연구는 **지도학습** 기반으로 모델 가중치를 직접 학습시킨 것이며, 재용 연구의 VLM 가중치 동결 접근과 근본적으로 다릅니다.

---

### 2.2 Pérez-Pérez et al. (2022) — 손가락 관절 운동학 + SVM 분류

Pérez-Pérez, A., Varea-Jiménez, E., Caballero-Herrero, D., Almenara-Masbernat, M., Opisso, E., & Medina-Casanovas, J. (2022). Classification models of Action Research Arm Test activities in post-stroke patients based on human hand motion. *Sensors*, *22*(22), 8806. https://doi.org/10.3390/s22228806

| 항목 | 상세 |
|------|------|
| **대상** | 뇌졸중 환자 + 건강 대조군 (구체적 N 미공개) |
| **장비** | **데이터 글러브** 또는 광학 모션캡처 (11개 손가락 관절 각도 추출) |
| **특징 변수** | 11개 손가락 관절의 **신전(extension) / 굽힘(flexion) 각도** |
| **과제** | ARAT 4개 하위 척도 (Grasp, Grip, Pinch, Gross) 활동 |
| **클래스 불균형 처리** | **Borderline-SMOTE** (합성 소수 클래스 오버샘플링) |
| **ML 모델** | SVM, Random Forest, KNN 비교 |
| **결과** | SVM 최고 성능: **precision 98%, recall 97.5%, AUC 0.996** |
| **의의** | ARAT의 천장 효과(ceiling effect)를 극복하여 수동 채점이 놓치는 미세 차이 감지 |

---

## 3. 웨어러블 센서(IMU) 기반 ARAT 점수 예측

### 3.1 Weikert et al. (2025) — 5개 센서 ARAT 항목별 예측

Weikert, T., Li, Y., Paez-Granados, D., & Awai Easthope, C. (2025). Automated prediction of item-level ARAT scores from wearable sensors. In *Proceedings of the 2025 IEEE International Conference on Rehabilitation Robotics (ICORR)*. IEEE. https://doi.org/10.1109/ICORR60564.2025

| 항목 | 상세 |
|------|------|
| **대상** | 다양한 신경학적 질환 환자 (뇌졸중 + 파킨슨병 포함) |
| **데이터** | ARAT 검사 **100회분** |
| **장비** | **5개 손목 장착 웨어러블 IMU 센서** (가속도계 + 자이로스코프) |
| **분석 단위** | 19개 ARAT 개별 항목(item-level) |
| **ML 모델** | 분류 모델 (원시 시계열 → 특징 추출 → 분류) |
| **결과** | 평균 균형 정확도 **80%** (개별 항목 범위: **59–91%**) |
| **질환별 모델** | 뇌졸중/파킨슨 특이 모델은 범용 모델 대비 정확도 향상 없음 |
| **의의** | 항목 수준(item-level) ARAT 예측의 실현 가능성 최초 체계적 입증 |

---

### 3.2 Kanzler, Lambercy, & Gassert 그룹 (ETH Zurich, 2022–2024)

Kanzler, C. M., Rinderknecht, M. D., Bobos, P., Lambercy, O., & Gassert, R. (2024). Digital biomarkers of upper limb movement quality after stroke: A systematic review. *Journal of NeuroEngineering and Rehabilitation*.

| 항목 | 상세 |
|------|------|
| **연구 유형** | 체계적 문헌 고찰(systematic review) 및 실험 연구 시리즈 |
| **장비** | 손목 장착 IMU, 로봇 보조 장치 내장 센서 |
| **핵심 개념** | "사용량(amount of use)"을 넘어 **"움직임 품질(quality of movement)"** 측정 |
| **운동학 지표** | 전완 자세 다양성(forearm postural diversity), 움직임 복잡성(complexity) |
| **임상 상관** | ARAT, FMA-UE 점수와의 상관관계 분석 |
| **기여** | 디지털 바이오마커의 체계화 및 표준화 프레임워크 제시 |

---

## 4. 가상현실(VR) 기반 ARAT

### 4.1 Burton et al. (2022) — 단축형 ARAT-VR 최초 검증

Burton, Q., Lejeune, T., Dehem, S., Lebrun, N., & Everard, G. (2022). Performing a shortened version of the Action Research Arm Test in immersive virtual reality to assess post-stroke upper limb activity. *Journal of NeuroEngineering and Rehabilitation*, *19*, Article 134. https://doi.org/10.1186/s12984-022-01114-3

| 항목 | 상세 |
|------|------|
| **대상** | 뇌졸중 환자 **30명**, 건강 대조군 **25명**, 의료 전문가 **11명** |
| **장비** | VR 헤드셋 (컨트롤러 기반 핸드 트래킹) |
| **과제** | 기존 19개 ARAT 중 **13개 항목**을 VR로 재현 |
| **제외 항목** | 구슬/볼베어링 등 미세 핀치 과제 6개 (당시 기술 한계) |
| **측정 지표** | VR 내 수행 시간, 정확도, 움직임 궤적 |
| **타당도** | 기존 ARAT와 동시 타당도: **r = 0.84** |
| **신뢰도** | 검사-재검사 신뢰도: **ICC = 0.99** |
| **사용성** | System Usability Scale (SUS): **82.5점** (우수) |
| **한계** | 촉각 피드백 부재, 핀치 과제 제외 |

---

### 4.2 Burton et al. (2026) — 18항목 ARAT-VR (PICO 4 Ultra)

Burton, Q., Lejeune, T., Dehem, S., & Everard, G. (2026). Reliability, validity, and usability of an 18-item immersive virtual reality action research arm test: A validation study in stroke survivors. *Frontiers in Neurology*, *17*, Article 1876892. https://doi.org/10.3389/fneur.2026.1876892

| 항목 | 상세 |
|------|------|
| **발전** | 13항목 → **18항목**으로 확대 |
| **장비** | **PICO 4 Ultra Enterprise** VR 헤드셋 |
| **핵심 기술** | **iToF (indirect Time-of-Flight) 깊이 센서** — 컨트롤러 없는 광학 손 추적 |
| **개선점** | 이전 버전의 핀치 과제 한계를 하드웨어 개선으로 극복 |
| **대상** | 뇌졸중 생존자 (구체적 N은 원문 참조) |
| **의의** | 원격 자율 평가의 실현 가능성 확대 |

---

### 4.3 Burton et al. (2024) — 확장현실(XR) 수부 민첩성 평가

Burton, Q., Lejeune, T., Dehem, S., & Everard, G. (2024). Extended reality to assess post-stroke manual dexterity: Contrasts between the classic box and block test, immersive virtual reality with controllers, with hand-tracking, and mixed-reality tests. *Journal of NeuroEngineering and Rehabilitation*, *21*, Article 31. https://doi.org/10.1186/s12984-024-01332-x

| 항목 | 상세 |
|------|------|
| **비교 조건** | 기존 BBT vs VR+컨트롤러 vs VR+핸드트래킹 vs 혼합현실(MR) |
| **과제** | Box and Block Test (BBT) — 1분간 블록 옮기기 |
| **의의** | 서로 다른 XR 입력 방식 간 수행 차이를 체계적으로 비교 |

---

## 5. 운동학 분석 + 깊이 카메라

### 5.1 Amprimo et al. (2024) — MediaPipe + 깊이 결합 (GMH-D)

Amprimo, G., Masi, G., Pettiti, G., Olmo, G., Priano, L., & Ferraris, C. (2024). Hand tracking for clinical applications: Validation of the Google MediaPipe Hand (GMH) and the depth-enhanced GMH-D frameworks. *Biomedical Signal Processing and Control*, *96*, Article 106508. https://doi.org/10.1016/j.bspc.2024.106508

| 항목 | 상세 |
|------|------|
| **장비** | RGB-D 카메라 (Azure Kinect DK) + Google MediaPipe Hands |
| **참조 기준** | **광학 모션캡처 시스템** (gold standard) |
| **프레임워크** | GMH (MediaPipe만) vs **GMH-D** (MediaPipe + 깊이 결합) |
| **대상** | 건강인 (임상 적용 전 방법론 검증) |
| **과제** | 다양한 손 자세 및 동작 (정적 + 동적) |
| **결과** | GMH-D가 GMH 대비 3D 공간 정밀도 유의미하게 향상 |
| **한계** | Azure Kinect와 D455의 센서 차이, 자기가림(self-occlusion) 시 정확도 저하, 환자 동적 환경 미검증 |

---

### 5.2 Qiu et al. (2022) — 도달-파지 운동학과 FMA

Qiu, Q., Fluet, G. G., Patel, J., Iyer, S., Karunakaran, K., Kaplan, E., Tunik, E., Nolan, K. J., Merians, A. S., Yarossi, M., & Adamovich, S. V. (2022). Evaluation of changes in kinematic measures of three dimensional reach to grasp movements in the early subacute period of recovery from stroke. In *Proceedings of the 44th Annual International Conference of the IEEE Engineering in Medicine and Biology Society (EMBC)* (pp. 5107–5110). IEEE. https://doi.org/10.1109/EMBC48229.2022.9871453

| 항목 | 상세 |
|------|------|
| **대상** | 뇌졸중 초기 아급성기 환자 **8명** |
| **장비** | **광학 모션캡처 시스템** (Optotrak 또는 유사) — 반사 마커 기반 |
| **과제** | 3차원 도달-파지(reach-to-grasp) 과제 |
| **운동학 지표** | 최대 파지 간격(MGA), 최대 간격 도달시간, 이동시간, 궤적 평활도 |
| **임상 상관** | FMA 변화와 운동학 지표의 관계 탐색적 분석 |
| **구간 정의** | **물체 운반 시점**을 기준으로 획득/해제 분할 |
| **결과** | MGA + 시간 변수 조합이 FMA 변화와 관계 있음 |
| **한계** | 소규모 표본(N=8), 탐색적 설계 |

> **참고**: 재용 연구의 **F1(움직임 크기), F2(극값 도달시간)** 피처가 이 논문에서 개념적 근거를 가져왔으나, 구간 정의 방식이 다릅니다 (원논문: 물체 운반 시점 / 재용: 속도 기반 마지막 획득 움직임 종료).

---

## 6. VLM(시각 언어모델) 및 LLM 기반

### 6.1 Li et al. (2026) — VLM으로 뇌졸중 동작 이해

Li, V., Kamalakannan, N., Parnandi, A., Schambra, H., & Fernandez-Granda, C. (2026). Vision-language models for human motion understanding: Lessons from stroke rehabilitation. *PLOS Digital Health*, *5*(7), Article e0001506. https://doi.org/10.1371/journal.pdig.0001506

| 항목 | 상세 |
|------|------|
| **대상** | 건강인 **20명** + 뇌졸중 환자 **51명** (총 71명) |
| **장비** | RGB 카메라 (구체적 사양 원문 참조) |
| **VLM** | Qwen2.5-VL-7B 등 다수 사전학습 VLM |
| **과제** | 활동 분류, 동작 횟수 추정, FMA 점수 추정 |
| **결과** | Qwen2.5-VL-7B 프롬프트 최적화 → 활동 분류 **77.5%** |
| **FMA 분석** | 전체 71명 중 FMA 분석은 28명 부분집합 |
| **한계** | 미세 동작·접촉 판단에서 오류 빈번, 프롬프트 민감성 높음 |

> **핵심**: 재용 연구의 **가장 직접적인 선행연구**입니다. 재용 연구는 이 연구의 한계(영상만으로 미세 손동작 판단 어려움)를 극복하기 위해 운동학 수치를 JSON으로 VLM에 추가 주입하는 하이브리드 접근을 제안합니다.

---

### 6.2 Tang et al. (2025) — LLM으로 재활 운동 품질 평가

Tang, J., Abedi, A., Colella, T. J. F., & Khan, S. S. (2025). Rehabilitation exercise quality assessment and feedback generation using large language models with prompt engineering. In *Artificial Intelligence for Aging Rehabilitation* (CCIS Vol. 2620, pp. 60–75). Springer. https://doi.org/10.1007/978-981-95-0568-5_5

| 항목 | 상세 |
|------|------|
| **데이터셋** | UI-PRMD, REHAB24-6 (재활 운동 수치 데이터셋) |
| **모델** | GPT-4 등 대형 언어모델 |
| **입력** | 운동학 수치(각도, 좌표 등) — 영상 없이 텍스트/수치만 |
| **분석** | 프롬프트 엔지니어링 (zero-shot, few-shot, chain-of-thought) |
| **결과** | 정답 예시 유무 및 지시 구성에 따라 성능 큰 차이 |
| **의의** | 수치 입력만으로도 LLM이 재활 품질 평가 가능함을 시사 |

---

### 6.3 Wang et al. (2024) — 보행 분석 VLM 지식 증강

Wang, D., Yuan, K., Muller, C., Blanc, F., Padoy, N., & Seo, H. (2024). Enhancing gait video analysis in neurodegenerative diseases by knowledge augmentation in vision language model. In *MICCAI 2024* (LNCS Vol. 15005, pp. 251–261). Springer. https://doi.org/10.1007/978-3-031-72086-4_24

| 항목 | 상세 |
|------|------|
| **과제** | 신경퇴행성 질환 보행 분석 |
| **방법** | 보행 영상 + 임상 설명 + 수치 표현을 **학습 가능 프롬프트**와 결합 |
| **모델** | 사전학습 VLM (학습 가능 프롬프트 모듈 추가) |
| **의의** | 영상+수치 지식 결합의 근거 (재용 연구 A3 조건의 개념적 기초) |
| **차이** | 학습 가능 프롬프트 vs 재용 연구의 동결 모델 입력 비교 |

---

## 7. 임상 결과 예측 및 기타

### 7.1 Stinear et al. (2017) — PREP2 알고리즘

Stinear, C. M., Byblow, W. D., Ackerley, S. J., Smith, M.-C., Borber, P. A., & Barber, P. A. (2017). PREP2: A biomarker-based algorithm for predicting upper limb function after stroke. *Annals of Clinical and Translational Neurology*, *4*(11), 811–820. https://doi.org/10.1002/acn3.488

| 항목 | 상세 |
|------|------|
| **입력** | 어깨 외전(SAFE), 손가락 신전(finger extension), 운동유발전위(MEPs), 뇌병변 부하 |
| **예측** | 뇌졸중 후 3개월 시점의 상지 기능 결과 (ARAT 점수 기반 범주) |
| **대상** | 급성기 뇌졸중 환자 |
| **알고리즘** | 의사결정 나무 기반 단계적 평가 |
| **정확도** | 환자의 약 75%를 72시간 내 정확하게 범주화 |
| **의의** | 조기 예후 예측 → 개인화된 재활 계획 수립 |

---

### 7.2 Kim et al. (2024) — 자동 상지 기능 평가 + 모바일 앱

Kim, D. W., Park, J. E., Kim, M. J., Byun, S. H., Jung, C. I., Jeong, H. M., Woo, S. R., Lee, K. H., Lee, M. H., Jung, J. W., Lee, D., Ryu, B. J., Yang, S. N., & Baek, S. J. (2024). Automatic assessment of upper extremity function and mobile application for self-administered stroke rehabilitation. *IEEE Transactions on Neural Systems and Rehabilitation Engineering*, *32*, 652–661. https://doi.org/10.1109/TNSRE.2024.3358497

| 항목 | 상세 |
|------|------|
| **시스템** | 모바일 앱 기반 자가 재활 + 자동 기능 평가 |
| **장비** | 스마트폰 카메라 + 내장 센서 |
| **평가** | 상지 기능 자동 채점 (지도학습 모델) |
| **대상** | 뇌졸중 환자 |
| **의의** | 원격 자가 관리 재활의 실용적 사례 |

---

### 7.3 PrimSeq — Parnandi et al. (2022)

Parnandi, A., Kaku, A., Venkatesan, A., Pandit, N., Wirtanen, A., Rajamohan, H., Venkataramanan, K., Nilsen, D., Fernandez-Granda, C., & Schambra, H. (2022). PrimSeq: A deep learning-based pipeline to quantitate rehabilitation training. *PLOS Digital Health*, *1*(6), Article e0000044. https://doi.org/10.1371/journal.pdig.0000044

| 항목 | 상세 |
|------|------|
| **대상** | 뇌졸중 환자 **41명** (학습 33명, 시험 8명) |
| **장비** | **IMU 관성 센서** (몸 부착) |
| **과제** | 도달·재배치·운반·안정화·대기 등 기본 재활 동작 구분 |
| **모델** | 딥러닝 기반 파이프라인 |
| **결과** | 수작업 주석 513.6시간 vs 자동 처리 1.4시간 (6.4시간 기록 기준) |
| **의의** | 자동화의 잠재적 시간 절감 효과 입증 |

---

## 8. 추가 참고 문헌

### 8.1 Lang et al. (2005, 2009) — 파지와 손가락 신전 관계

Lang, C. E., Wagner, J. M., Bastian, A. J., Hu, Q., Edwards, D. F., Sahrmann, S. A., & Dromerick, A. W. (2005). Deficits in grasp versus reach during acute hemiparesis. *Experimental Brain Research*, *166*, 126–136. https://doi.org/10.1007/s00221-005-2350-6

Lang, C. E., DeJong, S. L., & Beebe, J. A. (2009). Recovery of thumb and finger extension and its relation to grasp performance after stroke. *Journal of Neurophysiology*, *102*(1), 451–459. https://doi.org/10.1152/jn.91310.2008

### 8.2 Broome et al. (2019) — 수정 도달-파지 과제

Broome, K., Hudson, I., Potter, K., Kulk, J., Dunn, A., Arm, J., Zeffiro, T., Cooper, G., Tian, H., & van Vliet, P. (2019). A modified reach-to-grasp task in a supine position shows coordination between elbow and hand movements after stroke. *Frontiers in Neurology*, *10*, Article 408. https://doi.org/10.3389/fneur.2019.00408

### 8.3 Fugl-Meyer et al. (1975) — FMA 원저

Fugl-Meyer, A. R., Jääskö, L., Leyman, I., Olsson, S., & Steglind, S. (1975). The post-stroke hemiplegic patient. 1. A method for evaluation of physical performance. *Scandinavian Journal of Rehabilitation Medicine*, *7*(1), 13–31.

### 8.4 Lyle (1981) — ARAT 원저

Lyle, R. C. (1981). A performance test for assessment of upper limb function in physical rehabilitation treatment and research. *International Journal of Rehabilitation Research*, *4*(4), 483–492.

---

## 9. 논문 분류 종합

### 분류별 논문 목록

| 범주 | 논문 | 핵심 결과 |
|------|------|-----------|
| **📊 임상 간소화** | FOCUS (van Hoonhorst et al., 2021) | 2~4항목으로 96.7% 정확도 |
| **📊 임상 예측** | PREP2 (Stinear et al., 2017) | 72시간 내 75% 정확 범주화 |
| **📹 비디오 DL** | Ahmed & Rikakis (2025) | 3시점 비디오, 89% 정확도 |
| **📹 비디오 ML** | Pérez-Pérez et al. (2022) | SVM, precision 98% |
| **⌚ 웨어러블** | Weikert et al. (2025) | 5 IMU, 80% balanced acc. |
| **⌚ 웨어러블** | Kanzler 그룹 (2022–2024) | 디지털 바이오마커 체계화 |
| **⌚ 웨어러블** | PrimSeq (Parnandi et al., 2022) | 자동화 시간 절감 입증 |
| **🥽 VR** | Burton et al. (2022) | 13항목 ARAT-VR, r=0.84 |
| **🥽 VR** | Burton et al. (2026) | 18항목 PICO 4, iToF |
| **🥽 XR** | Burton et al. (2024) | XR 입력 방식 비교 |
| **📐 운동학** | Amprimo et al. (2024) | GMH-D, 깊이 결합 검증 |
| **📐 운동학** | Qiu et al. (2022) | MGA + 시간 → FMA 관계 |
| **🤖 VLM** | Li et al. (2026) | VLM 활동분류 77.5% |
| **🤖 LLM** | Tang et al. (2025) | 수치만으로 품질 평가 |
| **🤖 VLM** | Wang et al. (2024) | 보행 VLM 지식 증강 |
| **📱 모바일** | Kim et al. (2024) | 자가 재활 앱 |

---

## 10. 재용 연구와의 관계 요약

| 논문 | 관계 | 차별점 |
|------|------|--------|
| **Li et al. (2026)** | 가장 직접적 선행연구 | 영상만 → 재용은 영상+운동학 수치 |
| **Qiu et al. (2022)** | F1, F2 피처의 개념적 근거 | 구간 정의 방식 상이 |
| **Amprimo et al. (2024)** | D455+MediaPipe 방법론 근거 | 센서·환경 차이로 별도 검증 필요 |
| **Ahmed & Rikakis (2025)** | 동일 목표(자동 ARAT 채점) | 지도학습 vs VLM 동결 |
| **FOCUS (2021)** | 소수 항목 유효성 근거 | 결정나무 vs VLM 판정 |
| **Tang et al. (2025)** | A4 조건(수치만) 근거 | 과제·점수 체계 다름 |
| **Wang et al. (2024)** | A3 조건(영상+수치+참조) 근거 | 학습 가능 프롬프트 vs 동결 입력 |
| **Burton et al. (2022–2026)** | VR 기반 대안 접근 | 실물 과제 vs 가상 과제 |
| **Weikert et al. (2025)** | 센서 기반 자동 점수 예측 | 부착식 vs 비접촉 |
| **Pérez-Pérez et al. (2022)** | 운동학 기반 분류 근거 | 이진분류 vs 0/1/2 점수 |

# 파지(grasping) 클러스터링·특징 추출 선행연구 상세 증거맵

**작성일:** 2026-09-30
**목적:** 기존 조사(`outputs/01-조사문헌/arat-fma-ue-evidence-map.md` §6, §5)에서 다룬 "비장애인·장애인의 파지를 어떻게 실험하고 어떤 특징을 뽑아 군집화/분류했는가"를 한곳에 모아, **각 연구의 실험 방법(대상·과제·센서·알고리즘)과 결과 수치**를 1차 출처 기준으로 재정리한다.
**판독 원칙:** 수치는 초록/원문에서 확인된 값만 기재. 기존 노트의 full-text 판독에만 근거한 값은 `[FT-선행]`(prior full-text read)로 표기. 이번 패스에서 재검증하지 못한 항목은 명시.
**관련 문서:** `capstone/03_연구계획_및_정리노트/healthy_kinematic_clustering_and_engineering_originality_ko.md`, `outputs/01-조사문헌/arat-fma-ue-evidence-map.md` §6

---

## 0. 결론부터 (TL;DR)

**있었다.** 우리 조사에는 **비장애인 대상 6편 + 장애인(뇌졸중) 대상 6편** 이상이 파지 운동학의 **특징 추출·차원축소·군집화/분류**를 수행한 연구로 들어와 있다.

1. **비장애인 쪽은 "비지도 군집화/시너지 분해"가 표준**이다. 손가락 관절각(15~22채널)을 PCA/SVD/GPLVM으로 줄이고, hierarchical clustering·GMM·t-SNE+kNN으로 하위 패턴을 묶는다. 표본은 5명부터 77명까지.
2. **장애인(뇌졸중) 쪽은 "특징 추출 + 지도학습 분류/계층화"가 지배적**이다. PCA+ANN, SVM/RF/KNN, k-means 계층화, OPTICS 밀도 군집 사용. **뇌졸중 파지 운동학을 비지도로 서브타이핑한 연구는 사실상 없다** — 이게 우리 자리다.
3. **"몇 차원이 정답인가"는 문헌이 고정해주지 않는다.** 보고된 주요 성분 수가 **2 → 3 → 4 → 5 → 12**로 넓게 퍼져 있다(아래 §3 표). "6차원 GMM"은 문헌 근거가 아니라 목표 가설이며, **차원·K를 데이터로 정해야 한다**는 것이 이 맵의 핵심 결론이다.
4. **특징 선택이 결론을 좌우한다.** Herbst 2020은 특징 집합을 바꾸면 clustering 성공률이 **약 45%**까지 달라진다고 보고했다. → 특징 목록 사전등록 + 민감도 분석 필수.
5. **강한 시너지/군집 결과는 대부분 접촉식 장비(데이터 글러브·자기식 트래커·모션캡처)** 로 얻었다. RGB-D 무마커로 같은 것을 하려면 **손가락 관절각을 영상에서 추정**해야 하고, 이는 파지 순간 가림과 정면 충돌한다(별도 문서 `rgbd_hand_motion_research_ko.md`).

---

## Part A. 비장애인(정상) — 파지 클러스터링·시너지·특징 추출

### A-1. Santello, Flanders & Soechting 1998 — 파지 시너지의 원형
- **식별자:** J Neurosci 18(23):10105–10115 · PMID [9822764](https://pubmed.ncbi.nlm.nih.gov/9822764/) · PMC6793309 · DOI 10.1523/JNEUROSCI.18-23-10105.1998
- **어떻게 했나.** 피험자가 여러 친숙한 물체를 **쥐는 것처럼(마임)** 오른손을 형성. **손가락·엄지의 15개 관절각**을 정적으로 기록 → **PCA**.
- **결과.**
  - **첫 2개 성분이 분산의 80% 이상**을 설명 (= 기록한 15 DoF의 실질적 축소).
  - 3차 이상 상위 성분은 무작위 잡음이 아니라 **물체에 대한 추가 정보**를 담았다.
  - **시너지가 grip 분류체계와 일치하지 않음** → 손 자세 제어가 접촉력 제어와 독립적일 수 있다는 해석.
- **한계:** 정적·마임 자세(동적 reach-to-grasp 아님).
- **우리 연구 함의:** "정상 파지 저차원 구조"의 출발점. 단 **6차원이 아니라 2차원**을 보고했다는 점을 정확히 인용해야 한다.

### A-2. Mason, Gomez & Ebner 2001 — 도달-파지 전체의 고유자세(eigenposture)
- **식별자:** J Neurophysiol 86(6):2896–2910 · PMID [11731546](https://pubmed.ncbi.nlm.nih.gov/11731546/) · DOI 10.1152/jn.2001.86.6.2896
- **어떻게 했나.** 우수 5명. **5종 reach-to-grasp**(power, power+lift, precision, mimed power, mimed precision) × **16개 물체**(원뿔·원통·방추, 크기 체계적 변화). **4대 카메라**로 손·손목의 **21개 위치**를 3D 재구성. 시간열에 **SVD** → "eigenposture".
- **결과.**
  - **1st eigenposture = 분산의 97.3 ± 0.89%**, **2nd = 1.9 ± 0.85%.**
  - 1st = 도달 중 열렸다 닫히는 **손 전체 개폐**; 2nd = **엄지·장지 제어**(도달 중 열림, 파지 준비 닫힘).
  - eigenposture와 시간 변화가 **피험자·파지 유형 간 유사**.
  - 상위 eigenposture는 분산은 작지만 **손가락·엄지의 세부 운동**에 기여.
- **우리 연구 함의:** 동적 도달-파지에서도 **저차원(2개)** 이 지배. 파지 "서브타입"은 이 저차원 위의 **잔차/세부 구조**에서 나온다는 시사.

### A-3. Santello, Flanders & Soechting 2002 — 시간적 시너지와 감각 단서
- **식별자:** J Neurosci 22(4):1426–1435 · PMID [11850469](https://pubmed.ncbi.nlm.nih.gov/11850469/) · PMC6757566 · DOI 10.1523/JNEUROSCI.22-04-01426.2002
- **어떻게 했나.** 도달-파지를 **3조건**: (1) 기억 유도(운동 중 물체 안 보임), (2) 가상 물체(영상만), (3) 실제 물체. 팔 + **손 15 DoF** 기록 → 시공간 PCA.
- **결과.**
  - **2개 주성분이 분산의 75% 이상.**
  - 두 성분 모두 **MCP와 PIP 회전이 강한 양의 상관**.
  - PC1 = **손가락 신전이 굴곡으로 반전**; PC2 = **도달 후반부에서만 중요**.
  - **도달 중 물체를 보는 것은 운동학에 영향 없음.** 물체의 물리적 존재 효과는 **접촉 후**에 주로 나타남.
- **우리 연구 함의:** 시너지가 **시간적으로 전개**됨 → 서브타이핑 특징에 **시간 위상(tMGA, tPV 등)** 을 반드시 포함.

### A-4. Herbst, Zelnik-Manor & Wolf 2020 — 파지 패턴의 개인 고유성
- **식별자:** PLoS ONE 15(7):e0234969 · PMID [32640003](https://pubmed.ncbi.nlm.nih.gov/32640003/) · PMC7343174 · DOI 10.1371/journal.pone.0234969
- **어떻게 했나.** 비장애인 **31명**(남19/여12, 평균 26세, 좌손 4). **5개 물체** 파지. **동작캡처 + 힘센서**로 kinematics·kinetics 동시 측정. 손가락별 각도 2개 × 5손가락 + 힘 벡터 = **시점당 15특징**, 시행당 500 포인트 → **7,500차원**. 파이프라인: **t-SNE**(perplexity 10–15) → **가중 kNN**(k=10, 가중치 거리⁻²) → **5-fold CV**. 물체당 **32,751개 특징 조합** 전수 민감도 분석. `[FT-선행]`
- **결과.**
  - **총 1,083개 파지 인스턴스**(초록 확인).
  - **피험자 분류 정확도 95.48%**(31개 dense cluster, 각 약 5시행). 초록은 "over 95% success"로 기재.
  - reach+grasp만 정규화하면 **91.90%**.
  - 손 크기 순 혼동행렬에서 비슷한 크기끼리 혼동이 몰리지만 **크게 다른 손끼리도 오분류** → 손 크기가 유일 원인 아님.
  - **특징 집합 선택에 따라 clustering 성공률 약 45% 차이.** **엄지가 가장 중요한 구분 특징.**
- **저자 해석:** 파지 패턴은 **개인 고유**이며 물체 역학적 성질보다 개인차가 크다.
- **⚠️ 정확성 주의:** 이 연구는 **GMM이 아니라 t-SNE + kNN**이다. 우리 계획의 "GMM 기반"을 이 논문에 귀속시키면 안 된다.
- **우리 연구 함의:** "정상인도 단일 평균으로 비교 불가"의 직접 근거 + **특징 사전등록 의무**.

### A-5. Jarque-Bou, Scano, Atzori & Müller 2019 — 77명 규모 손 시너지
- **식별자:** J NeuroEng Rehabil 16:63 · PMID [31138257](https://pubmed.ncbi.nlm.nih.gov/31138257/) · PMC6540541 · DOI 10.1186/s12984-019-0536-6
- **어떻게 했나.** NinaPro **DB1·DB2·DB5의 77명**(남56/여21, 우수69/좌수8, 28.8±3.96세). **물체 파지 최대 20종 × 6회**. **CyberGlove II(22센서)**, 보정 관절각 **17 DoF**. 각 시행을 **1,000 프레임으로 리스케일**. **피험자별 PCA**(eigenvalue>1) + **varimax 회전** → 총 **418개 PC** → **hierarchical cluster analysis**(cutoff = pairwise distance 80) → **23개 그룹** → **12개 시너지**. `[FT-선행]`
- **결과(초록 확인).**
  - **12개 시너지가 전체 변이의 80% 이상** 설명.
  - **첫 3개 시너지가 총 분산의 50% 이상**: (1) **3–5지 MCP 굴곡+내전**, (2) **수장궁 + 손목 굴곡**, (3) **엄지 대립(opposition)**.
  - 나머지 시너지는 세밀 운동(예: 엄지-검지 독립성)을 담당하며 **피험자 간 변이 큼**.
  - 저자: 피험자 수가 이전 연구의 7배 이상, **필요한 motor module 수가 기존 문헌보다 높다**. 피험자당 평균 설명분산 83.06±2.96% `[FT-선행]`.
- **우리 연구 함의:** **"정상 파지 차원은 2–4개가 아니라 12개 수준"** → 차원을 낮게 잡으면 개인차 정보가 소실. **baseline에 피험자별 PCA+varimax+hierarchical clustering을 반드시 포함**.

### A-6. Gracia-Ibáñez, Sancho-Bru, Vergara, Jarque-Bou & Roda-Sales 2020 — ADL에서의 subject-specific 시너지
> ⚠️ **귀속 교정:** 기존 노트(evidence-map §6-3, protocol-analysis E-3)는 이를 **"Jarque-Bou et al. 2020"** 으로 적었으나, 실제 **제1저자는 Gracia-Ibáñez V**이며 Jarque-Bou는 **제4저자**다(PMID 32273539로 확인). 인용 시 교정 필요.
- **식별자:** Sci Rep 10:6116 · PMID [32273539](https://pubmed.ncbi.nlm.nih.gov/32273539/) · DOI 10.1038/s41598-020-63092-7 (정정: DOI 10.1038/s41598-020-68284-9)
- **어떻게 했나.** 우세손 **24명**(남12/여12, 손 길이 186.0±11.3 mm, 손 너비 81.6±6.5 mm, **50세 이하**). ICF 기준 **24개 실생활 ADL**을 실제 물체로 수행. CyberGlove **16개 관절각, 75 Hz**. 정규 ROM 스케일링 후 **피험자별 PCA + Varimax**(희소화), 피험자당 **첫 4개 PC** → clustering 후 core synergy 특성화. `[FT-선행]`
- **결과.** `[FT-선행]`
  - 피험자당 4개 PC가 **평균 77.3 ± 1.9%** 설명(모두 eigenvalue>1).
  - 총 **96개 시너지**, **부하값의 25%만 |0.25| 초과**(희소).
  - **처음 두 core synergy = 손가락 굴곡, 모든 피험자에서 존재**; 나머지(엄지, 엄지-검지, 수장궁, 손가락 내전)는 **피험자별 조합이 다름**.
- **우리 연구 함의:** 정상 참조모형이 **(a) 공통 core + (b) 개인 조합의 2층 구조**여야 한다는 근거. "4 PC로 77.3%"는 **차원 선택의 현실적 참조값**일 뿐 6차원 최적 증거가 아님. 50세 이하 제한 → 고령 장애인에는 **연령 정상 참조군 별도 필요**.

### A-7. Romero, Feix, Ek, Kjellström & Kragic 2010 — GPLVM + GMM/GMR 파지 모델링
- **식별자:** "Spatio-Temporal Modeling of Grasping Actions," IEEE/RSJ IROS 2010 · 원문 PDF: https://www.csc.kth.se/~dani/RSS/feix.pdf (**이번 패스에서 원문 미재검증**; 아래는 선행 full-text 판독)
- **어떻게 했나.** **5명** 피험자, **31개 파지 유형**. Polhemus 자 기식 트래커로 5개 손끝의 위치(3)+quaternion(4) = **35차원**, 시행당 **30 등간격 샘플** → 총 **4,650 datapoint**. **GPLVM**(RBF+bias+noise, back constraints, PPCA 초기화) → **2D latent space**. 각 파지 시간열에 **GMM**을 EM(k-means 초기화)으로 적합 → **GMR**로 평균·분산 경로 생성 → 경로 유사도로 clustering. `[FT-선행]`
- **결과.** `[FT-선행]`
  - GPLVM이 PCA·Isomap·LLE보다 **inter-grasp 분리·시간 연속성 우수, inter-subject 분산에 강건**.
  - **Gaussian 3개 초과는 적합 품질을 개선하지 못함**.
  - GMR 경로 clustering → **5개 cluster**.
- **⚠️ 결정적 약점:** **N=5, 로보틱스 목적(underactuated hand 설계), 임상검증 전무**, 자 기식 트래커로 35차원.
- **우리 연구 함의:** 우리 GMM의 **기술적 선례**일 뿐 **임상적 검증 근거가 아니다.** "Gaussian ≤3개로 충분"은 **K를 데이터로 정해야 한다**는 신호. latent 차원(2D)과 특징 벡터 차원을 혼동하면 안 됨.

### A-8. Pratap, Hatta, Ito & Hazarika 2024 — 계측 데이터 글러브 + PCA/t-SNE 군집
- **식별자:** arXiv:2405.19430 · https://arxiv.org/abs/2405.19430 (IEEE 투고본, 2024)
- **어떻게 했나.** 3D 프린팅 계측 글러브(**flex sensor 5 + 정전용량식 손끝 힘센서 5**). **비장애인 10명**(25–45세, 우수). **YCB 물체 25개 / 26 과제 / 8개 파지 유형**(+비파지 자세 2), 유형당 물체 3개, **시행 10회**, **40 Hz**, 시행 30초, 4단계(접근→접촉→들기→유지). **PCA(elbow method) + t-SNE**.
- **결과(원문 확인).**
  - **파지 자세 PCA: PC1 90.14%, PC2 누적 94.39%, PC3 누적 97.59%** → 최적 3개.
  - **파지 힘 PCA: PC1 63.87%, PC2 누적 79.42%, PC3 누적 91.31%** → 최적 3개.
  - **t-SNE 군집:** power grasp 계열(Hook, Spherical, Cylindrical, Diagonal Volar Grip, Lateral Pinch)이 함께 뭉침; precision 계열(Tripod, Extension Grip, Pulp Pinch)은 분리.
  - 최대 힘 **Spherical 9.96 N @158 g**, 최소 **Lateral Pinch 1.97 N @167 g**.
  - 손가락쌍 상관 최대: **Middle–Ring 0.969**, Index–Middle 0.95, Index–Ring 0.898.
- **우리 연구 함의:** 자세 특징은 **3차원이면 97.6%** 로 압축되지만, **힘 특징은 더 복잡**(3 PC 91.3%). 자세만으로 서브타이핑하면 힘 정보를 놓칠 수 있다.

### A-9. Feix, Romero, Schmiedmayer, Dollar & Kragic 2016 — GRASP 분류체계 (참조 기준)
- **식별자:** IEEE Trans Human-Machine Systems 46(1):66–77 · DOI 10.1109/THMS.2015.2470657 · IEEE Xplore 7243327
- **어떻게 했나.** 기존 파지 분류체계들을 비교·합성하여 **단일 taxonomy**로 정리(한 손, 정적·안정 파지 한정).
- **결과.** **33개 파지 유형**의 통합 분류체계(power/precision/intermediate, opposition·virtual-finger 기준).
- **우리 연구 함의:** 여러 군집화 연구(A-8 등)가 이 taxonomy에 사상(mapping)된다. 우리가 "파지 서브타입"을 말할 때 **Feix 유형과의 대응 관계**를 먼저 정의해야 용어 혼선을 막는다.

---

## Part B. 장애인(뇌졸중) — 파지 특징 추출·분류·계층화

> **총평:** 정상 쪽이 **비지도 군집화** 중심이라면, 뇌졸중 쪽은 **특징 추출 + 지도학습 분류**, 또는 **환자 계층화(stratification)**, 또는 **운동 품질 기준선** 목적의 군집화가 지배적이다. **뇌졸중 파지 운동학을 비지도로 서브타이핑한 연구는 이번 조사 범위에서 확인되지 않았다(§C-1).**

### B-1. Padilla-Magaña, Peña-Pitarch, Sánchez-Suarez & Ticó-Falguera 2022a — ARAT 16개 활동의 정상 관절각·힘
- **식별자:** Sensors 22(9):3276 · PMID [35590966](https://pubmed.ncbi.nlm.nih.gov/35590966/) · PMC9105674 · DOI 10.3390/s22093276
- **어떻게 했나.** **비장애인 25명**(우수). **CyberGlove II + FSR 5개 동시**, ARAT 3개 소척도(Grasp/Grip/Pinch) **16개 활동**.
- **결과(초록 확인).** 평균 굴곡각 — Thumb CMC 28.56°, MCP 26.84°, IP 13.23°; Index MCP 46.18°, PIP 38.89°; Middle MCP 47.5°, PIP 42.62°; Ring MCP 44.09°, PIP 39.22°; Little MCP 31.50°, PIP 22.10°. **평균 손끝 힘: Grasp 8.2 N / Grip 6.61 N / Pinch 3.89 N.**
- **우리 연구 함의:** ARAT 파지 항목의 **정상 기준 관절각·힘 참조값**. 비접촉 RGB-D로 이 값을 재현하려면 손가락 관절각 추정 오차(§C-2)를 정면으로 다뤄야 한다.

### B-2. Padilla-Magaña et al. 2022b — 정상 vs 뇌졸중 ARAT 관절각 차이
- **식별자:** Sensors 22(10):3604 · PMID [35632013](https://pubmed.ncbi.nlm.nih.gov/35632013/) · PMC9147783 · DOI 10.3390/s22103604
- **어떻게 했나.** **뇌졸중 6개월 이상 12명**(여3/남9, 65.2±9.3세) + **비장애인 25명**(여14/남11, 40.2±18.1세). CyberGlove II를 환측/우세손에 착용, **ARAT 수행**. 좌(LH)·우(RH) 편마비 구분.
- **결과(초록 확인).**
  - LH·RH 모두 **Index·Middle MCP 굴곡각이 대조군보다 유의하게 작음**.
  - **RH는** Index·Middle·Ring·Little **PIP 굴곡각이 더 큼**; **LH는** Middle·Little **PIP 굴곡각이 큼**.
  - ⇒ **MCP 굴곡 부족을 PIP 굴곡 증가로 보상**하는 전략. **ARAT 점수로는 보이지 않음.**
- **⚠️ 교란:** 비장애 40.2세 vs 뇌졸중 65.2세 → **나이 25년 차**. 우리는 연령 매칭을 명시해야 한다.

### B-3. Padilla-Magaña & Peña-Pitarch 2022 — ARAT 활동 정상/뇌졸중 분류 모델
- **식별자:** Sensors 22(23):9078 · PMID [36501779](https://pubmed.ncbi.nlm.nih.gov/36501779/) · PMC9737603 · DOI 10.3390/s22239078
- **어떻게 했나.** 두 데이터셋 합쳐 **1,088 샘플**(비장애 800 + 뇌졸중 288). **모든 활동이 ARAT 2점 또는 3점**. 특징 = **손가락 11개 관절의 굴곡·신전각** + 활동/소척도/운동방향. 클래스 불균형 → **Borderline-SMOTE**. **SVM / RF / KNN**.
- **결과(초록 확인).**
  - **정확도: SVM 97.8%, RF 97.1%, KNN 94.8%**
  - SVM **precision 98%, recall 97.5%, AUC 0.996**
  - ⇒ **ARAT 점수가 놓치는 차이가 실제로 존재**하며, 관절각 특징으로 비장애/뇌졸중을 구분 가능.
- **⚠️ 인용 시 명시 조건:** ① 97.8%는 **accuracy**, 초록의 98%/97.5%/0.996은 **같은 모델의 다른 지표**. ② 과제 **16개**(우리 계획은 2개로 축소 — 축소 사유 설명 의무). ③ **SMOTE 균형화 후** 값. ④ **나이 교란 미해소**.
- **우리 연구 함의:** 우리 연구 필요성의 **가장 직접적 근거**이자, **"ARAT 손 과제 운동학을 처음 한다"는 주장이 즉시 반박되는 지점**. 우리 자리는 **"같은 비교를 비접촉 단일 RGB-D로, 오류를 명시하며"** 다.

### B-4. Collins, Kennedy, Clark & Pomeroy 2018a — reach-to-grasp 메타분석
- **식별자:** Physiotherapy 104(2):153–166 · DOI 10.1016/j.physio.2017.10.002
- **어떻게 했나.** MEDLINE·AMED·Embase. 뇌졸중 환측 상지 reach-to-grasp 연구 + 정상 대조군. **SMD 합성**, Downs & Black 편향위험.
- **결과.** **29개 연구, 뇌졸중 460명 + 대조 324명.** **peak velocity SMD −1.48 (−1.94 to −1.02)**, **trunk displacement SMD +1.55 (0.85 to 2.25)**. 포함연구 편향위험 **unclear~high**.
- **우리 연구 함의:** **체간 변위가 최대 효과크기 중 하나**(SMD 1.55). "메타분석이니 확실"이 아니라 저자 스스로 편향위험을 인정했음을 함께 인용.

### B-5. Collins et al. 2018b — reach-to-target 메타분석
- **식별자:** Front Neurol 9:472 · PMID [29988530](https://pubmed.ncbi.nlm.nih.gov/29988530/) · DOI 10.3389/fneur.2018.00472
- **어떻게 했나.** reach-to-target 한정, **32개 연구**(뇌졸중 618 + 비장애 429), **26개 메타분석**, I².
- **결과.** 21/26 유의. movement time ipsilateral **SMD 2.57**, peak velocity ipsilateral **−1.76**, trunk contribution central **1.42**. **중앙 workspace에서 elbow extension(−0.41)·shoulder flexion(−0.95)·accuracy(0.52)는 비유의**.
- **우리 연구 함의:** **물체를 정중선에 두면 정상-장애인 차이가 줄어든다** → 물체 배치 고정·명시, 정상 참조모형을 workspace별로.

### B-6. Alt Murphy, Willén & Sunnerhagen 2011 — drinking task 19변수 PCA
- **식별자:** Neurorehabil Neural Repair · PMID [20829411](https://pubmed.ncbi.nlm.nih.gov/20829411/) · DOI 10.1177/1545968310370748
- **어떻게 했나.** 만성 뇌졸중 **19명** + 비장애 **19명**. 표준 drinking task, 3D 광학식 모션캡처. **19개 운동학 변수 → PCA**. FMA-UE로 중등도(39–57)/경증(58–64) 층화. `[FT-선행]`
- **결과.** `[FT-선행]`
  - PCA **5성분(eigenvalue>1)이 86%** 설명, 13개 변수 추출.
  - 이동시간 **11.4±3.1 vs 6.49±0.83 s**; peak velocity **431±82.7 vs 616±93.8 mm/s**; elbow angular PV **64.9±20.5 vs 121.8±25.3 °/s**; **trunk displacement 77.2±48.6 vs 26.7±16.8 mm**.
  - effect size η² 0.22–0.62; 속도계열 지표 **민감도·특이도 >94.7%**.
  - 저자: NMU·TMT·elbow PAV가 구분에 가장 강력, 보상운동이 경증-중등도 구분에 추가 기여.
- **우리 연구 함의:** **정상 참조값(체간 26.7 mm, 속도 616 mm/s)** 의 출발점. **PCA 5성분/86%가 우리 GMM이 넘어야 할 baseline**. ⚠️ FMA-UE ≥39(중등도 이상)만 → **중증에는 이 참조값 부적용**.

### B-7. van Kordelaar, van Wegen & Kwakkel 2012 — 보상 체간운동 ↔ 병적 시너지
- **식별자:** Exp Brain Res 221:251–262 · DOI 10.1007/s00221-012-3169-6
- **어떻게 했나.** 뇌졸중 **46명** + 비장애 **12명**. Polhemus Liberty 240 Hz. 앉아서 블록 reach-to-grasp(위치를 개인 최대도달거리로 개인화해 **체간 기여 억제**). **PCA → 로지스틱 회귀**로 FMA 시너지 유무 예측. `[FT-선행]`
- **결과.** `[FT-선행]`
  - 이동시간 **1.93±1.48 vs 1.10±0.24 s** (p=.001).
  - **뇌졸중 4성분 84.7%, 비장애 3성분 86.6%.**
  - 성분1 = flexion synergy(어깨 외전+팔꿈치 굴곡); **성분2(측방 체간회전 ↔ 어깨 부족 보상) p=.014**; **성분3(전방 체간회전 ↔ 팔꿈치 부족 보상) p=.003**.
- **우리 연구 함의:** **장애인이 정상보다 더 많은 차원(4 vs 3)을 쓴다** → "장애인은 정상 시너지 공간에서 이탈/확장"이라는 우리 가설의 정량 근거. 단 체간 억제 설계라 ARAT 조건과 다름.

### B-8. Schwarz et al. 2025 — 고기능 장애인에서도 남는 proximal 결손
- **식별자:** Stroke · DOI 10.1161/STROKEAHA.124.049336
- **어떻게 했나.** 좌반구 뇌졸중 **13명**(물체 파지 가능 = moderate-to-good) + 나이·성별·우세손 매칭 대조 **13명**. 각 팔 **80회 unconstrained reach-to-grasp**(폼볼 10 cm). **Vicon 12대, 200 Hz, 마커 45개**. 선형혼합모형. `[FT-선행]`
- **결과.** `[FT-선행]`
  - **end-point 지표 차이 없음:** movement time 0.92 vs 0.96 s(p=.944), smoothness 1.02 vs 1.15(**p=.057, 경계**).
  - **근위부 협응 차이 있음:** 팔꿈치굴곡–어깨회전 p=.019, 어깨굴곡–외전 p=.008, 어깨굴곡–회전 p=.001.
- **우리 연구 함의:** **end-point 지표만 넣으면 고기능 장애인을 놓친다** → 관절 타이밍 필수. 동시에 **이 연구에서 smoothness(SPARC 계열)는 구분 실패** → SPARC 과의존 경계.

### B-9. Kim, Cho, Baek, Bang & Paik 2016 — Kinect + PCA + ANN
- **식별자:** PLoS ONE 11(7):e0158640 · DOI 10.1371/journal.pone.0158640
- **어떻게 했나.** 편마비 뇌졸중 **41명**. UE-FMA 33항목 중 **13개** 선택. 작업치료사 채점 중 **Kinect(30 Hz)** 정면 기록. **PCA + ANN** 학습, jerky score 산출. `[FT-선행]`
- **우리 연구 함의:** **RGB-D로 FMA를 예측한 초기 사례**. 다만 jerky 지표는 후속 연구에서 RGB-D 신뢰도가 낮게 나온 계열(§C-2).

### B-10. Proffitt, Ma & Skubic 2023 — Kinect + VR + OPTICS 밀도 군집
- **식별자:** Top Stroke Rehabil 30(1):11–20 · PMID [36524625](https://pubmed.ncbi.nlm.nih.gov/36524625/) · PMC9758417 · DOI 10.1080/10749357.2021.2006981
- **어떻게 했나.** 4개 연구 데이터 통합: **뇌졸중 8명 + 비장애 30명**. Kinect 골격(15관절 x,y,z)을 MatLab 처리, **normalized jerk · movement path ratio · average path sway** 계산, **OPTICS 밀도 기반 군집** 사용.
- **결과(초록 확인).** 비장애 30명이 **3개 운동학 변수의 normative baseline**을 형성. 뇌졸중 환자는 양쪽 상지 모두 **덜 효율적·더 jerk한** 움직임.
- **우리 연구 함의:** 뇌졸중에서의 군집화는 **"운동 품질 정상 기준선"** 목적으로 쓰인 사례. N=8로 exploratory이며 "확립된 서브타입"이 아니다.

### B-11. Lu et al. 2025 — IMU 특징 + k-means 계층화 + 해석 가능 모델
- **식별자:** IEEE TNSRE 33:4325–4337 · PMID [41134944](https://pubmed.ncbi.nlm.nih.gov/41134944/) · DOI 10.1109/TNSRE.2025.3625159
- **어떻게 했나.** **뇌졸중 30명**. 환측 손목 + 몸통 **IMU 2개**, 표준 상지과제 4개. 추출한 **운동학 특징**에 **k-means clustering** → **Mild / Moderate** 두 하위군으로 계층화. 하위군별 **Cluster-specific GAM(CGAM)** 학습, **LOOCV**.
- **결과(초록 확인).** **CGAM RMSE 5.79, R²=0.75** vs 비계층 global model **RMSE 6.78, R²=0.66**. 특정 특징이 Mild/Moderate에서 FMA-UE에 다르게 기여함을 모델이 드러냄.
- **우리 연구 함의:** **뇌졸중 환자군을 k-means로 나눠 정상/중등도로 서브타이핑**한 최신 사례 → "장애인 서브타이핑" 아이디어 자체는 선례가 있다. 단 **(a) 계층화 목적(개인화)**, **(b) 손 파지·관절각이 아니라 손목/몸통 IMU**, **(c) 구분 라벨이 임상 중증도**라는 점이 우리와 다르다.

### B-12. Biswas et al. 2015 — 손목 IMU + k-means로 상지 동작 인식
- **식별자:** Hum Mov Sci 40:59–76 · PMID [25528632](https://pubmed.ncbi.nlm.nih.gov/25528632/) · DOI 10.1016/j.humov.2014.11.013
- **어떻게 했나.** 손목 단일 IMU(3축 가속도+3축 자이로). **정상 4명 + 뇌졸중 4명**. 전완의 3대 운동(신전·굴곡·회전)을 **30개 시간영역 특징** → sequential forward selection → **k-means(3 cluster)** + 최소거리 분류기. ADL("차 한 잔 만들기") 중 검출. LDA·SVM과 비교.
- **결과(초록 확인).** 정상: 가속도 88% / 자이로 83%. **뇌졸중: 가속도 70% / 자이로 66%.** → 장애인에서 성능이 크게 하락.
- **우리 연구 함의:** **군집화가 파지 서브타이핑이 아니라 "동작 횟수(dose) 카운팅"에 쓰인 대표 사례**. 그리고 **장애인에서의 인식 성능 하락**은 우리의 분석 대상(정상으로 학습 → 장애인 일반화 실패)과 같은 방향의 경고.

---

## C. 통합 비교표

### C-1. 연구별 설계·방법·결과 요약

| # | 연구 | 대상(N) | 센서/과제 | 특징 | 차원축소 | 군집/분류 | 핵심 결과 |
|---|---|---|---|---|---|---|---|
| A-1 | Santello 1998 | 비장애(마임) | 손 15 관절각 | 관절각 | PCA | — | 2성분 >80%; 시너지≠grip 분류 |
| A-2 | Mason 2001 | 비장애 5 | 4-카메라, 21점 | 3D 위치 | SVD | — | 1st eigenposture 97.3% |
| A-3 | Santello 2002 | 비장애 | 손 15 DoF | 관절각 | PCA | — | 2성분 >75%; 시각 무영향 |
| A-4 | Herbst 2020 | 비장애 31 | 모캡+힘, 5물체 | 각도+힘 15/시점 | t-SNE | kNN | 개인분류 95.48%; 특징선택 45% 영향 |
| A-5 | Jarque-Bou 2019 | 비장애 77 | CyberGlove II 22센서, 20파지 | 17 DoF | 피험자별 PCA+varimax | Hierarchical | 12 시너지 >80%; 첫3 >50% |
| A-6 | Gracia-Ibáñez 2020 | 비장애 24 | CyberGlove, 24 ADL | 16 관절각 | 피험자별 PCA+varimax | Clustering | 4 PC 77.3%; core 2개 공통 |
| A-7 | Romero 2010 | 5 | Polhemus, 31 파지 | 35차원(위치+quat) | GPLVM | GMM+GMR | ≤3 Gaussian; 5 cluster |
| A-8 | Pratap 2024 | 비장애 10 | 계측 글러브, 8 GT×3물체×10회 | 각도5+힘5 | PCA+t-SNE | t-SNE 시각화 | 자세 3PC 97.6%, 힘 3PC 91.3% |
| B-1 | Padilla-Magaña 2022a | 비장애 25 | CyberGlove+FSR, ARAT16 | 관절각+힘 | — | — | 정상 ARAT 관절각·힘 기준값 |
| B-2 | Padilla-Magaña 2022b | 뇌졸중 12 + 정상 25 | CyberGlove, ARAT16 | 11 관절각 | — | ANOVA | MCP↓·PIP↑ 보상, ARAT 점수에 안 보임 |
| B-3 | Padilla-Magaña 2022c | 1,088 샘플 | CyberGlove | 11 관절각+과제 | — | SVM/RF/KNN | SVM 정확도 97.8% |
| B-4 | Collins 2018a | 460+324 | 문헌 29편 | 메타분석 | — | SMD | peak vel −1.48, trunk +1.55 |
| B-5 | Collins 2018b | 618+429 | 문헌 32편 | 메타분석 | — | SMD | 중앙 workspace 다수 비유의 |
| B-6 | Alt Murphy 2011 | 19+19 | 모캡, drinking | 19 변수 | PCA | — | 5성분 86%; trunk 77 vs 27 mm |
| B-7 | van Kordelaar 2012 | 46+12 | Polhemus 240Hz | 관절·체간 | PCA | 로지스틱 | 뇌졸중 4성분 vs 정상 3성분 |
| B-8 | Schwarz 2025 | 13+13 | Vicon 12대 200Hz | 관절각·타이밍 | — | LMM | end-point 정상, proximal 차이 |
| B-9 | Kim 2016 | 뇌졸중 41 | Kinect 30Hz, FMA13 | 관절 위치 | PCA | ANN | jerky score |
| B-10 | Proffitt 2023 | 8+30 | Kinect+VR | jerk/path ratio/sway | — | OPTICS | 비장애 baseline; 뇌졸중 저효율 |
| B-11 | Lu 2025 | 뇌졸중 30 | IMU 2개, 4과제 | 운동학 특징 | — | k-means+GAM | RMSE 5.79 vs 6.78; R² 0.75 vs 0.66 |
| B-12 | Biswas 2015 | 4+4 | 손목 IMU | 30 특징 | — | k-means | 정상 88%, 뇌졸중 70% |

### C-2. "몇 차원인가" — 문헌이 보고한 성분 수 (핵심 쟁점)

| 보고된 차원 | 연구 | 근거/기준 |
|---|---|---|
| **2** | Santello 1998 (>80%), Santello 2002 (>75%), Mason 2001 (97.3%+1.9%), Romero 2010 (latent 2D, GMM ≤3) | 고전 정적/동적 파지 |
| **3** | Pratap 2024 (자세 97.59%, 힘 91.31%), van Kordelaar 2012 정상 3성분 86.6% | 최근 글러브; 정상 reach |
| **4** | Gracia-Ibáñez 2020 (77.3%), van Kordelaar 2012 뇌졸중 4성분 84.7% | ADL; 뇌졸중 |
| **5** | Alt Murphy 2011 (19변수 PCA 86%) | drinking task |
| **12** | Jarque-Bou 2019 (>80%) | 77명, 20파지 |

> **해석:** 차원 수는 **과제·대상·기준(eigenvalue>1 / 분산 80% / BIC)** 에 따라 2~12로 크게 달라진다. **"6차원"을 문헌 근거로 정당화할 수 없다.** 차원과 K는 raw 추적 데이터에서 **사전 명시 규칙(BIC + bootstrap stability + 분산 기준)** 으로 결정해야 한다. (기존 근거: Jarque-Bou는 eigenvalue>1 + varimax + 분산 80%를 함께 사용.)

### C-3. 정상 vs 뇌졸중 접근법의 구조적 차이 (이 맵의 핵심 발견)

| 축 | 비장애인 연구 | 뇌졸중 연구 |
|---|---|---|
| 지배적 목적 | 저차원 시너지 구조 발견 | 기능평가·분류·개인화 |
| 지배적 방법 | 비지도 (PCA/SVD/GPLVM + hierarchical/GMM/t-SNE) | 지도학습(SVM/RF/KNN/ANN) 또는 계층화(k-means) |
| 특징 | 손가락 관절각(±힘) 직접 측정 | 관절각, 체간변위, jerk, path ratio, IMU 특징 |
| 센서 | 데이터 글러브, 자기식 트래커, 모캡 | 글러브, Kinect, IMU, 모캡 |
| 표본 | 5 ~ 77 | 4 ~ 618(메타) |
| **비지도 파지 서브타이핑** | **다수 존재** | **확인되지 않음(공백)** |

---

## D. 우리 연구(GMM 6D 서브타이핑 + VLM 융합)에 대한 함의

1. **당위성은 성립한다.** 정상인도 (a) 개인 고유 파지 패턴(Herbst), (b) 12개 수준의 시너지와 개인차(A-5, A-6), (c) 뇌졸중은 정상보다 더 많은 차원 사용(B-7)을 보인다 → **단일 평균 비교 부적절**.
2. **그러나 "GMM 6차원"은 아직 근거가 아니다.** 문헌 보고 차원은 2~12로 분산. → **차원·K를 데이터로 결정**하고, **PCA/피험자별 PCA+varimax+hierarchical clustering을 baseline**으로 반드시 넣는다.
3. **특징은 사전등록하고 민감도 분석을 보고**한다(Herbst: 특징 선택이 결과를 ~45% 바꿈). 후보 특징 = 정규화 MGA, tMGA, RGC_lag, 엄지-검지 비대칭/대립, 폐쇄율 + (선택) 체간·어깨 근위 특징.
4. **엄지-검지(opposition/aperture) 계열이 가장 유망**하다: Herbst(엄지가 최다 구분 특징), A-5(시너지#3 = 엄지 대립), B-2/B-3(뇌졸중은 MCP↓·PIP↑; 관절각으로 구분), A-8(힘은 자세보다 복잡).
5. **비접촉 RGB-D는 검증 부담이 크다.** 위 강한 결과는 대부분 **접촉식 관절각 측정**에서 나왔다. 우리가 쓰려는 SPARC·TAPV·정규화 MGA는 **무마커에서 신뢰도가 낮게 보고된 계열**이다(Faity 2022: peak velocity ICC 0.21, NVP ICC 0.38). → **뇌졸중 손 파지에서의 오차를 직접 정량화**하는 것이 실질 기여 #1.
6. **표본 규모 주의:** 안정적 시너지/군집 결과는 77명(A-5) 규모에서 나왔다. 소표본(A-2 N=5, A-7 N=5, A-8 N=10)은 탐색적이다. 정상 참조모형을 진짜로 만들려면 **별도 60~100+ 코호트**가 필요하다는 기존 결정과 일치.
7. **용어 귀속 주의:** A-4는 GMM이 아니라 t-SNE+kNN, A-7은 로보틱스 목적 N=5, A-6는 제1저자가 Gracia-Ibáñez다. 인용 시 이 세 가지를 반드시 구분한다.

---

## E. 기존 노트 대비 교정·보강 내역

| 항목 | 기존 노트 | 교정/보강 |
|---|---|---|
| Sci Rep 2020 시너지 논문 저자 | "Jarque-Bou et al. 2020" | **Gracia-Ibáñez V 등 2020**(PMID 32273539), Jarque-Bou는 제4저자 |
| 추가 논문 | 없음 | **Santello 2002(PMID 11850469)**, **Mason 2001(PMID 11731546)**, **Pratap 2024(arXiv:2405.19430)**, **Feix GRASP taxonomy 2016(DOI 10.1109/THMS.2015.2470657)**, **Proffitt 2023(PMID 36524625)**, **Lu 2025(PMID 41134944)**, **Biswas 2015(PMID 25528632)** |
| Padilla-Magaña 지표 | "SVM 97.8%" | 97.8%는 **accuracy**이며 precision 98%·recall 97.5%·AUC 0.996는 **별도 지표**, SMOTE 균형화 후 값, 나이 교란 존재 |

---

## F. Blocked / Unverified (이번 세션 기준)

- **OpenAlex 조회:** 세션 중 `429 Too Many Requests`(검색 클러스터 부하). → OpenAlex 기반 서지 ID 교차확인 미완. PubMed/DOI로 대체 확인함.
- **Romero 2010 (A-7):** IROS 2010 PDF(https://www.csc.kth.se/~dani/RSS/feix.pdf) **원문 재검증 안 함**. 기재 수치는 선행 세션 full-text 판독(`[FT-선행]`).
- **Herbst 2020의 세부수치**(95.48%, 31 cluster, 45%, t-SNE perplexity 10–15, kNN k=10, 1083 instances 중 1083 확인): 초록에서 **1,083 인스턴스·">95%"** 는 확인. 나머지 세부는 `[FT-선행]`.
- **Jarque-Bou 2019 세부수치**(17 DoF, 1,000프레임, 418 PC, 23그룹, 83.06%): 초록에서 **77명·20파지·CyberGlove II·PCA+hierarchical·12 시너지 >80%·첫 3개 >50%·시너지 내용** 확인. 나머지 `[FT-선행]`.
- **Gracia-Ibáñez 2020 세부수치**(77.3%, 96 시너지, 25% loading): 서지 ID만 재확인, 수치는 `[FT-선행]`.
- **Alt Murphy 2011 / Kim 2016 / Schwarz 2025 / van Kordelaar 2012 세부수치:** `[FT-선행]`(evidence-map §5의 full-text 판독값). 이번 패스에서 원문 미재검증.
- **Feix 2016 taxonomy:** 웹 출처(IEEE Xplore 7243327, Yale GRAB Lab PDF, MPI-IS)로 DOI·서지 확인. **33개 유형의 세부 목록은 미검증**.

---

## Sources

**비장애인 파지 시너지·군집**
1. Santello M, Flanders M, Soechting JF (1998). *Postural hand synergies for tool use.* J Neurosci 18(23):10105–10115. PMID 9822764. https://doi.org/10.1523/JNEUROSCI.18-23-10105.1998
2. Mason CR, Gomez JE, Ebner TJ (2001). *Hand synergies during reach-to-grasp.* J Neurophysiol 86(6):2896–2910. PMID 11731546. https://doi.org/10.1152/jn.2001.86.6.2896
3. Santello M, Flanders M, Soechting JF (2002). *Patterns of hand motion during grasping and the influence of sensory guidance.* J Neurosci 22(4):1426–1435. PMID 11850469. https://doi.org/10.1523/JNEUROSCI.22-04-01426.2002
4. Herbst Y, Zelnik-Manor L, Wolf A (2020). *Analysis of subject specific grasping patterns.* PLoS ONE 15(7):e0234969. PMID 32640003. https://doi.org/10.1371/journal.pone.0234969
5. Jarque-Bou NJ, Scano A, Atzori M, Müller H (2019). *Kinematic synergies of hand grasps: a comprehensive study on a large publicly available dataset.* J NeuroEng Rehabil 16:63. PMID 31138257. https://doi.org/10.1186/s12984-019-0536-6
6. Gracia-Ibáñez V, Sancho-Bru JL, Vergara M, Jarque-Bou NJ, Roda-Sales A (2020). *Sharing of hand kinematic synergies across subjects in daily living activities.* Sci Rep 10:6116. PMID 32273539. https://doi.org/10.1038/s41598-020-63092-7
7. Romero J, Feix T, Ek CH, Kjellström H, Kragic D (2010). *Spatio-Temporal Modeling of Grasping Actions.* IEEE/RSJ IROS 2010. https://www.csc.kth.se/~dani/RSS/feix.pdf
8. Pratap S, Hatta Y, Ito K, Hazarika SM (2024). *Understanding Grasp Synergies during Reach-to-grasp using an Instrumented Data Glove.* arXiv:2405.19430. https://arxiv.org/abs/2405.19430
9. Feix T, Romero J, Schmiedmayer H-B, Dollar AM, Kragic D (2016). *The GRASP Taxonomy of Human Grasp Types.* IEEE Trans Human-Machine Systems 46(1):66–77. https://doi.org/10.1109/THMS.2015.2470657

**뇌졸중 파지 특징·분류·계층화**
10. Padilla-Magaña JF, Peña-Pitarch E, Sánchez-Suarez I, Ticó-Falguera N (2022). *Hand Motion Analysis during the Execution of the Action Research Arm Test Using Multiple Sensors.* Sensors 22(9):3276. PMID 35590966. https://doi.org/10.3390/s22093276
11. Padilla-Magaña JF, Peña-Pitarch E, Sánchez-Suarez I, Ticó-Falguera N (2022). *Quantitative Assessment of Hand Function in Healthy Subjects and Post-Stroke Patients with the Action Research Arm Test.* Sensors 22(10):3604. PMID 35632013. https://doi.org/10.3390/s22103604
12. Padilla-Magaña JF, Peña-Pitarch E (2022). *Classification Models of Action Research Arm Test Activities in Post-Stroke Patients Based on Human Hand Motion.* Sensors 22(23):9078. PMID 36501779. https://doi.org/10.3390/s22239078
13. Collins KC, Kennedy NC, Clark A, Pomeroy VM (2018). *Getting a kinematic handle on reach-to-grasp: a meta-analysis.* Physiotherapy 104(2):153–166. https://doi.org/10.1016/j.physio.2017.10.002
14. Collins KC, Kennedy NC, Clark A, Pomeroy VM (2018). *Kinematic Components of the Reach-to-Target Movement After Stroke…: Systematic Review and Meta-Analysis.* Front Neurol 9:472. PMID 29988530. https://doi.org/10.3389/fneur.2018.00472
15. Alt Murphy M, Willén C, Sunnerhagen KS (2011). *Kinematic variables quantifying upper-extremity performance after stroke during reaching and drinking from a glass.* Neurorehabil Neural Repair. PMID 20829411. https://doi.org/10.1177/1545968310370748
16. van Kordelaar J, van Wegen EEH, Kwakkel G (2012). *Unraveling the interaction between pathological upper limb synergies and compensatory trunk movements during reach-to-grasp after stroke.* Exp Brain Res 221:251–262. https://doi.org/10.1007/s00221-012-3169-6
17. Schwarz A et al. (2025). *Compensatory Proximal Adjustments Characterize Effective Reaching Movements After Stroke.* Stroke. https://doi.org/10.1161/STROKEAHA.124.049336
18. Kim WS, Cho S, Baek D, Bang H, Paik NJ (2016). *Upper Extremity Functional Evaluation by Fugl-Meyer Assessment Scoring Using Depth-Sensing Camera in Hemiplegic Stroke Patients.* PLoS ONE 11(7):e0158640. https://doi.org/10.1371/journal.pone.0158640
19. Proffitt R, Ma M, Skubic M (2023). *Novel clinically-relevant assessment of upper extremity movement using depth sensors.* Top Stroke Rehabil 30(1):11–20. PMID 36524625. https://doi.org/10.1080/10749357.2021.2006981
20. Lu Z et al. (2025). *Personalized Stroke Rehabilitation via Stratified Interpretable Modeling With Wearable IMUs.* IEEE TNSRE 33:4325–4337. PMID 41134944. https://doi.org/10.1109/TNSRE.2025.3625159
21. Biswas D et al. (2015). *Recognizing upper limb movements with wrist worn inertial sensors using k-means clustering classification.* Hum Mov Sci 40:59–76. PMID 25528632. https://doi.org/10.1016/j.humov.2014.11.013

**내부 참조**
22. `outputs/01-조사문헌/arat-fma-ue-evidence-map.md` §5–§6
23. `outputs/01-조사문헌/rgbd-grasp-vlm-protocol-analysis.md` §D–§E
24. `capstone/03_연구계획_및_정리노트/healthy_kinematic_clustering_and_engineering_originality_ko.md`
25. `capstone/03_연구계획_및_정리노트/rgbd_hand_motion_research_ko.md`

---

## G. 사용자 정리본(2026-09-30 붙여넣음) 교차검증

**검증 대상:** 사용자가 붙여넣은 "선행연구 조사 결과 + 기존 연구계획 결합 심층 정리본"(6차원 벡터 1:1 매핑 + Q&A 디펜스 스크립트 포함).
**판정:** **문헌 수치는 대체로 정확**하다. 그러나 **설계 전제 1건과 특징↔논문 매핑 4건이 틀렸거나 과장**이다. 아래를 그대로 면담·논문에 쓰면 정본 계획과 모순된다.

### G-1. 🔴 최우선 오류 — 정본(v6.3)과의 범위 충돌

| 항목 | 정리본의 전제 | 현행 정본(`outputs/research-plan-v6.md` v6.3) |
|---|---|---|
| 정상 GMM·군집화·정상 참조모형 | Stage 1의 핵심 설계 | **"범위 밖"**(§0 표, line 31) · **"이번 범위에서 주장 금지"**(§12 금지 #16) |
| SPARC·PAp·TPAp·TAPV | 주 지표 | **커밋된 입력 아님**. 정본 입력은 **K1(엄지–검지 표면점 거리 P95) + K2(손목 표면점 속도 P95)**. **"PAp라고 부르기 금지"**(§12 금지 #2, §11 K1 정의) |
| 지표 편입 | 사전 확정 | **게이트 통과 시에만**(§13 4조건). **SPARC는 C2 탈락**(필요 컷오프 102.0° = Wagner 최대치 98.9% → 사실상 측정 불가, §13 표) |
| 14프레임 2-Stage | 아키텍처 | v6.3은 **A0~R 조건 비교 + 오류 주입**. "JSON 주입"은 A2/A3 조건 서술 |

- **근거:** `outputs/research-plan-v6.md` line 31·325·416·443·682~699; `CHANGELOG.md` 2026-09-28 (29차) "온보딩 브리프 ↔ v6.3 설계 충돌 🔴".
- **해석:** 붙여넣은 정리본은 **`capstone/.../healthy_kinematic_clustering_and_engineering_originality_ko.md`(v5·캡스톤 시대)** 계보이고, 정본은 **v6.3(수치 주입·게이팅 인과실험)** 이다. 면담 전에 **어느 쪽을 정본으로 삼을지 확정**해야 한다. GMM 서브타이핑을 되살리려면 v6.3 범위 선언부터 개정해야 한다.

### G-2. ⚠️ 특징 벡터 1:1 매핑의 과장·오류

| 정리본 주장 | 판정 | 근거 |
|---|---|---|
| `SPARC` ← **Alt Murphy 2011(민감도>94%)** | **틀림** | Alt Murphy 2011은 **SPARC를 쓰지 않았다**(SPARC는 2015 Balasubramanian). 그 논문의 >94.7%는 **NMU·총이동시간·팔꿈치 최대각속도** 기준. → SPARC 근거는 **Balasubramanian 2015** 하나로만 인용해야 함. (PMID 20829411 초록 확인) |
| `Closure_ratio` ← **Padilla-Magaña 2022b** | **과장** | 그 논문은 **CyberGlove 관절각(MCP/PIP)** 만 측정. "접촉 직전 감속"·"closure ratio"는 측정하지 않음. |
| `RGC_lag` ← **Schwarz 2025 + van Kordelaar 2012** | **느슨함** | Schwarz 2025는 **관절간(팔꿈치–어깨) 협응**, van Kordelaar 2012는 **체간 보상** 성분. 둘 다 `tMGA−tPV` 시간 지연을 직접 측정하지 않음. → 개념적 인접 근거로만. |
| `Asym_thumb-index` ← **Herbst 2020** | **간접** | Herbst는 **관절각 특징**의 구분 기여를 봤고 비대칭 지수를 정의하지 않음. |
| `MGA_n` ← Mason 2001 / Santello 1998 | 타당 | 1st 시너지 = 손 전체 개폐. |
| `t_MGA_n` ← Santello 2002 / Jeannerod | 타당 | preshaping 시간 전개. |

### G-3. ⚠️ 디펜스 스크립트의 과잉 주장

| 위치 | 문제 | 교정 |
|---|---|---|
| Q3 "MGA·RGC_lag는 마커리스에서 **상대적으로 신뢰도가 높은** 지표" | **검증되지 않은 가정.** Faity 2022에서 신뢰 가능했던 것은 **체간 변위(ICC 0.93)** 이고, 속도·미분 계열은 실패(peak velocity ICC 0.21) | "**검증할 가설**"로 표기. MGA·RGC의 무마커 신뢰도는 **우리가 측정해야 하는 대상** |
| Q4 "Padilla-Magaña는 환자군 **내부 서브타입을 규명하지 못했다**" | **너무 강함.** 그들은 **LH vs RH 편마비를 나눠** PIP 패턴 차이를 보고함(예정된 그룹 비교) | "데이터 기반 **비지도** 서브타이핑은 하지 않았다"로 한정 |
| Q1 "문헌에서 **검증된** 3대 축" | 개별 특징은 지지되나 **6개 조합 자체는 미검증** | "문헌에서 **개별적으로 지지되는** 후보 특징" |

### G-4. 사소한 정확성 문제

- **Santello 1998 피험자 수 "다수":** 초록에 **미기재**, 원문은 비-OA(Europe PMC `fullTextStatus: not_open_access`). → 확인 불가로 표기.
- **Collins "총 61편 통합":** 두 **별도 리뷰(29편 + 32편)의 단순 합**. 하나의 통합 메타분석처럼 쓰면 오해 소지. 일부 연구 중복 가능성.
- **정확히 맞게 쓴 것:** Herbst는 GMM이 아니라 t-SNE+kNN(정리본도 그렇게 씀 ✅), Romero N=5·로보틱스·임상 일반화 제한 명시 ✅, Sci Rep 2020 저자를 **Gracia-Ibáñez**로 표기 ✅.

### G-5. 검증 등급

- **등급 A(1차 출처 직접 확인):** Santello 1998/2002, Mason 2001, Herbst 2020(주요값), Jarque-Bou 2019(주요값), Gracia-Ibáñez 2020(서지), Padilla-Magaña 2022a/b/c, Alt Murphy 2011(초록), Proffitt 2023, Lu 2025, Biswas 2015, Pratap 2024(전문), Feix 2016(서지).
- **등급 B/C(선행 full-text 판독 `[FT-선행]`):** Romero 2010, Jarque-Bou 2019 세부수치, Gracia-Ibáñez 2020 세부수치, van Kordelaar 2012, Schwarz 2025, Kim 2016.
- **미해결:** OpenAlex 429(이번 패스). Santello 1998 피험자 수.

# ARAT 및 FMA-UE 상지기능 자동화를 위한 8대 선행연구 증거 맵

**기준일:** 2026-09-22  
**범위:** 임상계량학, 운동학, 자동채점, VLM/LLM, 정상-뇌졸중 비교, 정상 파지 다양성, 무마커 측정, 지식증강  
**판독 원칙:** `직접 근거`는 뇌졸중·ARAT/FMA 또는 동일 운동학 과제를 직접 검증한 연구, `전이 근거`는 일반 재활·건강인·다른 임상동작 연구다.

## Executive summary

1. **자동화의 타당성은 “기존 척도가 나쁘다”가 아니라 “좋은 임상척도가 움직임 정보를 압축한다”는 데 있다.** FMA-UE와 ARAT는 대체로 높은 신뢰도·타당도를 보이지만 ordinal score, 평가단계별 바닥/천장 효과, 프로토콜·평가자 의존성, 보상전략과 진정한 회복의 혼합이라는 한계가 있다.[Hsueh 2009](https://doi.org/10.2522/ptj.20080285) [Valladares et al. 2024](https://doi.org/10.3389/fneur.2024.1429929)
2. **임상척도와 가장 일관되게 연결되는 운동학은** 운동시간·속도, smoothness(SPARC/NMU), 체간 변위, 어깨·팔꿈치 운동 및 peak aperture 관련 지표다. 다만 한 지표가 전체 FMA/ARAT 구성개념을 대체하지는 못한다.[Schwarz et al. 2019](https://doi.org/10.1161/STROKEAHA.118.023531) [Alt Murphy et al. 2012](https://doi.org/10.1177/1545968312448234)
3. **자동채점 연구의 수치는 유망하지만 임상적 SOTA로 단정하기 어렵다.** 표본이 작거나, 일부 항목만 자동화하거나, 단일 평가자를 정답으로 쓰거나, 환자 단위 외부검증을 생략한 사례가 많다.[Kim et al. 2016](https://doi.org/10.1371/journal.pone.0158640) [Wang et al. 2024](https://doi.org/10.1177/02692155241251434)
4. **범용 VLM 단독 FMA 채점은 현재 불충분하다.** Qwen2.5-VL-72B의 예측 FMA가 중증도 전반에서 거의 일정해지고, 영상을 무시하고 1점을 내는 기준선과 유사한 직접 결과가 있다.[Li et al. 2025, arXiv:2511.17727](https://arxiv.org/abs/2511.17727) 본 보고서는 이를 **score flatlining**으로 부른다. `Kinematic blindness`는 미세 운동학을 포착하지 못하는 현상에 대한 **해석적 명칭**이지 확립된 학술용어는 아니다.
5. **정상 파지는 단일 평균이 아니다.** 공통 저차원 시너지와 동시에 강한 개인·과제별 변이가 존재한다. 그러나 “6차원 GMM 정상 하위유형+매니폴드 이탈 백분위”는 아직 확립된 임상표준이 아니라 검증할 연구가설이다.[Jarque-Bou et al. 2019](https://doi.org/10.1186/s12984-019-0536-6) [Herbst et al. 2020](https://doi.org/10.1371/journal.pone.0234969)
6. **권장 설계는 VLM 단독이 아니라** `영상 + 명시적 운동학 JSON + 정상 하위유형/거리 + 계층적 임상 규칙 + 불확실성/임상가 확인`이다. 이는 운동학→움직임 요소→구간→과제의 계층을 검증한 HBM 연구와, 특징을 LLM에 주입한 일반 재활 연구가 뒷받침한다.[Ahmed et al. 2024](https://doi.org/10.1109/TNSRE.2024.3450008) [Tang et al. 2025, arXiv:2505.18412](https://arxiv.org/abs/2505.18412)

---

## 통합 Evidence Map

| 주제 | 핵심 연구 | 피험자/자료 | 주요 정량 근거 | 한계 | 등급 |
|---|---|---:|---|---|---|
| 1. 임상척도 한계 | Hsueh et al., 2009 | N=53, 35명 180일 완료 | ARAT floor 41.5%(14일), ceiling 20.8–22.6%(30–180일); interrater ICC≥.92, test–retest ICC≥.97 | 단계별 탈락·소표본 | 직접·높음 |
| 2. 임상 연관 운동학 | Alt Murphy et al., 2012 | N=30 stroke | ARAT–NMU r=.81, 시간 r=.68, 체간 r=.63; NMU+체간이 ARAT 분산 67% 설명 | mild–moderate, 단일 과제 | 직접·중상 |
| 2. SPARC | Bayle et al., 2024 | N=31 stroke | SPARC ICC=.912; baseline UE-FMA r=.48, ARAT r=.68; 변화 효과크기 .76 | subacute, N 작음 | 직접·중상 |
| 2. PAp/TPAp/TAPV | Qiu et al., 2022 | N=8 stroke | TPAp+PAp adj. R²=59.8%; TAPV+TPAp adj. R²=61.9% | 정확한 개별 r 공식 HTML 미노출 | 직접·낮음–중간 |
| 3. 자동 FMA | Wang et al., 2024 | N=95 hemiparesis | 자동 총점 계수 .960 | 단면·단일기관; force item 약함 | 직접·중상 |
| 3. 3-view ARAT | Ahmed & Rikakis, 2025 | 50명, 500 segments | late fusion accuracy 89%; score agreement 91% | preprint; 2-vs-3 이진화; segment split | 직접·낮음 |
| 4. VLM 결함 | Li et al., 2025 | 29 controls+51 stroke; FMA 899 videos/28명 | FMA 예측이 severity에 무관하게 거의 일정; score-1 baseline과 유사 | preprint·단일 연구 | 직접·중간 |
| 5. Stroke vs control | Collins et al., 2018 | 29 studies; 460+324 | peak velocity SMD −1.48; trunk displacement SMD 1.55 | 포함연구 bias 높음/불명확 | 직접·중상 |
| 6. 정상 다양성 | Jarque-Bou et al., 2019 | N=77, 20 grasps×6 | 12 synergies가 >80%; 첫 3개 >50% | glove 기반, 젊은 정상인 | 전이·중상 |
| 7. 무마커 타당도 | Faity et al., 2022 | N=26 healthy | trunk displacement ICC=.93 vs trunk rotation .38; NVP .38, peak velocity .21 | stroke 유사 모사, Kinect v2 | 직접성 중간 |
| 8. 지식증강 | Ahmed et al., 2024 | 478 videos | 98개 평가자 불일치 중 95% 해결; kinematic–task/segment 정렬 >90% | 완전자동 임상시험 아님 | 직접·중상 |

---

## 1. 기존 FMA-UE·ARAT 평가의 임상적 한계

### 무엇이 실제로 입증됐는가

- **신뢰도는 높다.** Hsueh et al.의 종단연구에서 네 척도의 쌍별 Spearman 상관은 ≥.81, interrater ICC는 ≥.92, test–retest ICC는 ≥.97이었다.[Hsueh et al. 2009](https://doi.org/10.2522/ptj.20080285)
- **그러나 점수분포가 회복단계에 따라 포화된다.** 같은 연구에서 ARAT floor/ceiling은 각각 14일 41.5/9.4%, 30일 17.0/20.8%, 90일 11.3/20.8%, 180일 11.3/22.6%였다.[Hsueh et al. 2009](https://doi.org/10.2522/ptj.20080285) 비선별 급성 코호트 N=117에서도 ARAT floor는 3일 38.4%, 10일 30.2%, 4주 24.1%, ceiling은 4주 21.3%였다.[Kristersson et al. 2019](https://doi.org/10.2340/16501977-2534)
- **FMA-UE도 ceiling-free가 아니다.** 조기 뇌졸중 N=60에서 13명(21.7%)이 66점 만점을 받았다.[Hernández et al. 2019](https://doi.org/10.2340/16501977-2590)
- **보상과 회복의 분리가 부족하다.** 급성/아급성/만성 N=133/113/92를 비교한 연구에서 FMA-UE–ARAT 범주 agreement는 weighted κ=.76/.83/.81로 높았지만, 저자들은 이 높은 일치 자체가 두 척도로 restitution과 compensation을 분리하기 어렵다는 근거라고 해석했다.[Valladares et al. 2024](https://doi.org/10.3389/fneur.2024.1429929)
- **평가자 주관성은 ‘낮은 신뢰도’보다는 프로토콜 해석 문제다.** 최신 합의연구는 여러 FMA-UE 프로토콜의 시작자세·허용 보조·항목 지시 차이가 점수와 구성타당도를 바꿀 수 있다고 지적했다.[Pohl et al. 2025](https://doi.org/10.1016/j.apmr.2024.10.004)

### 시간 부담의 정확한 표현

ARAT는 약 10분, FMA motor section은 약 20분으로 정리된 review가 있으나, ARAT 장비·세팅, 훈련된 평가자, 심한 환자의 반복 지시까지 포함하면 실제 workflow burden은 커진다.[Alt Murphy et al. 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4359448/) 따라서 “둘 다 항상 지나치게 길다”보다 **빈번한 반복측정과 원격·대규모 적용에 부담이 있다**가 증거에 맞다.

### 설계 함의

자동화의 1차 목적은 임상척도 폐기가 아니라 (i) 점수 재현, (ii) 연속 운동학 보완, (iii) 보상과 수행속도 분해, (iv) 측정불확실성 표시다.

---

## 2. 임상점수와 연관된 핵심 운동학

### 정의

- **SPARC:** 속도 신호의 정규화 Fourier magnitude spectrum에서 계산한 spectral arc length. 덜 음수일수록 더 매끄럽다.[Mohamed Refai et al. 2021](https://doi.org/10.1186/s12984-021-00949-6)
- **PAp:** reaching 중 index–thumb 최대 거리.
- **TPAp:** reaching 시작부터 PAp까지의 시간.
- **TAPV:** wrist peak velocity부터 object transport 시작까지의 시간.[Qiu et al. 2022](https://doi.org/10.1109/EMBC48229.2022.9871891)
- **체간 변위:** 흉골/흉곽 표식의 초기 위치 대비 최대 전방 이동. 연구별 축·구간 정의가 다르다.

### 가장 강한 정량 근거

1. **기능과 smoothness/시간/체간:** drinking task N=30에서 ARAT는 NMU smoothness와 r=.81, total movement time과 r=.68, trunk displacement와 r=.63이었다. NMU와 체간 변위가 ARAT 분산의 67%를 설명했으며 고유 기여는 각각 37%, 11%였다.[Alt Murphy et al. 2012](https://doi.org/10.1177/1545968312448234)
2. **SPARC의 신뢰도·동시타당도:** subacute stroke N=31에서 SPARC ICC=.912, 변화 효과크기 .76, baseline 상관은 UE-FMA r=.48, proximal UE-FMA r=.56, ARAT r=.68이었다. 30일 후 SPARC–UE-FMA r=.63, SPARC–ARAT r=.46이었다.[Bayle et al. 2024](https://doi.org/10.1186/s12984-024-01382-1)
3. **종단 SPARC–FMA:** stroke N=40와 정상 N=12에서 SPARC와 FM-UE의 종단 association은 B=31.73(95% CI 27.27–36.20), within-subject B=30.85(26.28–35.41)였고 둘 다 5주 이후 plateau를 보였다.[Saes et al. 2021](https://doi.org/10.1186/s12984-021-00937-w)
4. **PAp/TPAp/TAPV:** N=8의 초기 아급성 연구에서 PAp, trajectory smoothness, reach duration, TAPV가 유의하게 개선됐다. TPAp+PAp 모델은 adjusted R²=59.8%, predictive R²=51.9%; TAPV+TPAp 모델은 adjusted R²=61.9%, predictive R²=52.0%였다.[Qiu et al. 2022](https://pubmed.ncbi.nlm.nih.gov/36086392/) **개별 Pearson r은 공식 HTML/메타데이터로 검증되지 않아 보고하지 않는다.**
5. **문헌 전체의 불균일성:** 체계적 고찰은 225 studies, N=6197, 151 metrics를 찾았지만 clinimetrics를 조사한 연구는 30편뿐이었다. 충분한 평가가 일부라도 있었던 지표는 time, movement onset/end 수, path ratio, peak velocity, velocity peak 수, trunk displacement, shoulder flexion/extension 등이었다.[Schwarz et al. 2019](https://doi.org/10.1161/STROKEAHA.118.023531)

### 판단

SPARC·PAp·TPAp·TAPV·체간변위는 상호 대체재가 아니다. 각각 smoothness, preshaping magnitude, grasp timing, late correction, compensation을 측정하므로 구조화 JSON에서 함께 쓰는 논리가 강하다.

---

## 3. ML/DL 기반 자동 상지기능 평가

| 연구 | 입력/과제 | N | 성능 | 주요 제한 |
|---|---|---:|---|---|
| Kim et al., 2016 | Kinect, 13 FMA items | 41 stroke | item 65–87%; 13-item 합 r=.873, full FMA r=.799 | 부분 FMA, 한 평가자 |
| Li et al., 2022 | RealSense+Leap+force, 30 voluntary items | 20 stroke | r=.981; accuracy 80.83%, macro-F1 80.97%, MAE .21/item | N 작음; 복수장비; RealSense mean offset 96 mm |
| BIONICS, 2023 | smartphone RGB, 16/33 items | 45 acute stroke | item 78.1–82.7%; group correlation 평균 .89 | 일부항목; wrist item 약함 |
| Wang et al., 2024 | depth camera+force+ML | 95 hemiparesis | total coefficient .960 | 단면·단일기관; force items 낮은 타당도 |
| Zhou et al., 2025 | 4 IMU, 3 reaching motions | 11 stroke | LOSO normalized RMSE 7%; 약 70% items 추정 | 매우 작은 N |
| Ahmed & Rikakis, 2025 | 3-view RGB, SlowFast/I3D/Transformer+HBM | 50 patients, 500 segments | 89% validation accuracy; score agreement 91% | preprint; ARAT 2 vs 3만 이진분류; segment random split |

Sources: [Kim et al. 2016](https://doi.org/10.1371/journal.pone.0158640), [Li et al. 2022](https://doi.org/10.3390/brainsci12101380), [Zamin et al. 2023/BIONICS](https://doi.org/10.1177/15459683231184186), [Wang et al. 2024](https://doi.org/10.1177/02692155241251434), [Zhou et al. 2025](https://doi.org/10.1109/JBHI.2025.3542037), [Ahmed & Rikakis 2025, arXiv:2505.01680](https://arxiv.org/abs/2505.01680).

### ST-GCN의 위치

ST-GCN은 variable-length skeleton의 공간·시간 토폴로지를 처리한다. Deb et al.은 KIMORE/UI-PRMD에서 기존 exercise-assessment 모델보다 개선됐다고 보고했다.[Deb et al. 2022](https://doi.org/10.1109/TNSRE.2022.3150392) 그러나 이는 대표성 있는 stroke FMA/ARAT item-level 임상검증과 동일하지 않다. 건강인·혼합질환 benchmark 성능을 ARAT 자동채점 성능으로 전치하면 안 된다.

### 공통 취약점

- 총점 상관이 높아도 item-weighted κ·Bland–Altman·오차의 중증도 의존성이 나쁠 수 있다.
- session/trial을 무작위 분할하면 같은 환자의 영상이 train/test에 섞일 수 있다.
- 반사·reflex·촉각·저항은 비접촉 영상만으로 직접 측정하기 어렵다.
- 정상인 위주 훈련은 환자의 비정형 운동과 가림을 대표하지 못한다.

---

## 4. VLM/LLM 재활평가와 VLM 단독 결함

### 직접적인 stroke/FMA 연구

Li et al.은 29 healthy controls와 51 stroke survivors(총 3448 trials)를 조사했다. FMA 실험은 28명·899 videos에서 Qwen2.5-VL-72B에 item rubric과 짧은 clip을 주었다. 예측 FMA는 중증도 전 범위에서 **essentially constant**였고, 시각입력을 무시하고 1점을 반환하는 비정보적 기준선과 오차가 비슷했다.[Li et al. 2025, arXiv:2511.17727](https://arxiv.org/html/2511.17727)

이 결과는 다음을 직접 지지한다.

- **Flatlining:** 중증도 변화에도 중앙점수 근처를 반복 예측.
- **미세 운동학 실패:** 연구진 표현으로 “fine-grained motion understanding” 부족. 본 보고서의 `kinematic blindness`는 이 현상을 요약한 명칭이다.
- **언어/전이 prior 우세:** dose 추정이 영상을 보지 않는 Markov baseline과 비슷했다.

다만 high-level activity identification과 일부 구조화 과제에서는 가능성이 있었다. 프롬프트와 후처리 최적화 후 mild/control의 dose count가 ground truth ±25% 이내로 들어온 경우가 있었다.[Li et al. 2025](https://arxiv.org/abs/2511.17727)

### 왜 14-frame VLM-only가 위험한가 — 추론

이는 직접 실험결과가 아니라 위 근거에서 도출한 설계 추론이다.

1. 14개 정지프레임은 velocity·acceleration·smoothness와 event timing을 aliasing할 수 있다.
2. 손-물체 가림은 aperture와 접촉 순간을 불안정하게 만든다.
3. ordinal 0/1/2 prompt는 불확실할 때 중앙값 1로 수렴하기 쉽다.
4. VLM의 설명 유창성은 계측정확도의 증거가 아니다.

따라서 video-only VLM은 임상 점수 생성기가 아니라 **운동학 증거를 해석하는 계층**으로 제한하는 것이 안전하다.

---

## 5. 비장애인 대 뇌졸중 운동학·보상 패턴

### 메타분석

Reach-to-grasp 29 studies에서 460 stroke와 324 controls를 합쳤을 때 stroke군은 peak velocity가 낮고(SMD −1.48, 95% CI −1.94 to −1.02), trunk displacement가 컸다(SMD 1.55, 0.85–2.25).[Collins et al. 2018](https://doi.org/10.1016/j.physio.2017.10.002)

Reach-to-target의 별도 메타분석(32 studies; 618 stroke, 429 controls)은 central/ipsilateral/contralateral workspace 모두에서 movement time 증가(SMD 예: ipsilateral 2.57), peak velocity 감소(예: −1.76), trunk contribution 증가(central 1.42), smoothness 저하를 보였다.[Collins et al. 2018](https://doi.org/10.3389/fneur.2018.00472)

### 대표 원저

- Drinking task N=19+19: total movement time 11.4 vs 6.49 s, peak velocity 431 vs 616 mm/s, elbow angular peak velocity 64.9 vs 121.8°/s, trunk displacement 77.2 vs 26.7 mm.[Alt Murphy et al. 2011](https://doi.org/10.1177/1545968310370748)
- Reach-to-grasp N=46 stroke+12 controls: duration 1.93±1.48 vs 1.10±.24 s; PCA는 pathological shoulder–elbow synergy와 trunk compensation을 분리했다.[van Kordelaar et al. 2012](https://doi.org/10.1007/s00221-012-3169-6)
- 고기능 stroke N=13+13에서는 end-point movement time·TTPV가 정상과 비슷했지만 elbow–shoulder와 shoulder 내부 협응 timing은 유의하게 달랐다.[Schwarz et al. 2025](https://doi.org/10.1161/STROKEAHA.124.049336)

**해석:** 단순 end-point 정상화는 정상 전략 회복을 의미하지 않는다. proximal coordination과 trunk/shoulder compensation을 별도 채널로 평가해야 한다.

---

## 6. 정상 파지 다양성, GMM 하위유형, 시너지 매니폴드

### 확립된 것

1. **개인 고유성:** 31 healthy participants, 5 objects, 1083 grasps에서 joint-angle/force 패턴으로 사람을 95.48% 분류했다. hand size가 일부 혼동을 설명했지만 전부는 아니었다.[Herbst et al. 2020](https://doi.org/10.1371/journal.pone.0234969)
2. **저차원 공통구조와 미세 개인차의 공존:** 77명, 20 grasps×6에서 12 synergies가 >80% 변이를 설명했고 첫 3개가 >50%였다. 후순위 thumb/index synergies는 사람별 변이가 컸다.[Jarque-Bou et al. 2019](https://doi.org/10.1186/s12984-019-0536-6)
3. **ADL subject-specific synergy:** 24명·24 ADL에서 4 PCs가 77.3±1.9%를 설명했고, 공통 finger-flexion core 외 thumb/index·palmar arch 전략은 조합이 달랐다.[Jarque-Bou et al. 2020](https://doi.org/10.1038/s41598-020-63092-7)
4. **GMM/GMR 선례:** 5명·31 grasp의 35D fingertip trajectory를 2D GPLVM에 투영한 뒤 최대 3개의 Gaussian으로 grasp별 temporal path를 모델링했다. 이는 로봇공학적 선례이지 임상 정상 subtype 검증은 아니다.[Romero et al. 2010](https://www.csc.kth.se/~dani/RSS/feix.pdf)

### 아직 확립되지 않은 것

문헌에서 **ARAT 파지에 특화된 6차원 GMM**, 최적 cluster 수, subtype percentile 또는 healthy synergy manifold 이탈도가 stroke 임상점수를 개선한다는 직접 검증은 찾지 못했다. 따라서 이는 다음 가설로 제시해야 한다.

> 손 크기·물체·속도·laterality를 통제한 뒤에도 정상인은 복수의 안정적 운동학 전략을 보이며, 환자 평가는 단일 평균거리보다 “가장 가까운 정상 subtype/매니폴드로부터의 거리”가 더 공정할 것이다.

### 필수 비교 baseline

Global z-score, hand-size stratification, PCA Mahalanobis distance, Gaussian mixture, one-class SVM/normalizing flow를 patient-disjoint 외부검증에서 비교하고 cluster 수는 BIC뿐 아니라 bootstrap stability·임상 예측증분으로 결정해야 한다.

---

## 7. 무마커 RGB-D/MediaPipe의 신뢰도·타당도

### 핵심 수치

- Kinect v2 vs Vicon, N=26 healthy: trunk displacement ICC=.93, shoulder displacement .88, trunk flexion .82였지만 trunk rotation .38이었다. 필터 후 movement time/path ratio/time-to-PV/NVP/peak velocity ICC는 .76/.51/.55/.38/.21이었다.[Faity et al. 2022](https://doi.org/10.3390/s22072735)
- RGB-D/RGB vs Qualisys, N=6: upper-limb mean absolute angular error는 RealSense D415 11.56±3.74°, MediaPipe 9.98±3.79°였다.[Lafayette et al. 2023](https://doi.org/10.3390/s23010003)
- MediaPipe/HRNet vs Qualisys, N=22: elbow flexion-extension ROM ICC=.92(MediaPipe)와 .94(HRNet).[Hamilton et al. 2024](https://doi.org/10.1016/j.jbmt.2024.04.033)
- Kinect v2 vs Vicon, N=15: test–retest ICC는 point-to-point .73–.82, exploration .62–.84로 workspace에 따라 달랐다.[Scano et al. 2020](https://doi.org/10.3390/mti4020014)
- 2025 systematic review는 14 studies를 포함했고, flexion/abduction이 rotation보다 일관되게 우수했으며 연구 방법론은 inadequate–very good으로 이질적이었다.[Lee et al. 2025](https://doi.org/10.3389/fbioe.2025.1570637)

### 핵심 판단

1. **하나의 “RealSense 오차” 또는 “MediaPipe ICC”는 없다.** 관절·운동면·가림·카메라 배치·필터·metric에 따라 달라진다.
2. 위치/ROM 타당도가 SPARC·TAPV 타당도를 보장하지 않는다. 미분과 event detection이 jitter를 증폭한다.
3. 체간 전방변위·movement time은 상대적으로 안정적이지만 pronation/supination, trunk rotation, 손가락 aperture, peak·NVP는 별도 검증이 필요하다.
4. 제안 시스템은 Vicon 동시측정으로 **PAp, TPAp, TAPV, SPARC 각각**의 ICC, MAE/RMSE, Bland–Altman LoA를 보고해야 한다.

---

## 8. 수치/센서 지표와 VLM의 멀티모달 지식증강

### 직접 선행연구

**Ahmed et al. 2024**는 478개 stroke upper-extremity videos에서 clinician-rated task–segment–composite hierarchy에 computational kinematics를 연결했다. 평가자 불일치 98 cases 중 95%를 HBM이 해결했고 kinematics와 task–segment 조합을 >90%에서 정렬했다.[Ahmed et al. 2024](https://doi.org/10.1109/TNSRE.2024.3450008) 이는 `수치→임상개념→과제점수`의 확률적 중간층이 유용하다는 가장 직접적인 근거다.

**Tang et al. 2025**는 관절 sequence에서 임상적으로 정의한 3–5개 feature를 추출해 GPT-4o에 주입했다. Certainty prompting의 accuracy/F1은 UI-PRMD .76/.79, REHAB24-6 .70/.73이었다. UI-PRMD에서 ST-GCN은 .94/.96으로 더 높았지만 REHAB24-6에서는 LLM이 동등하거나 우수했다.[Tang et al. 2025](https://arxiv.org/html/2505.18412) 두 데이터셋 모두 각 N=10 healthy participants이며 feedback은 정량 ground truth 없이 질적으로만 평가됐다.

### 전이 가능한 선행연구

- **UbiPhysio:** 104명, 25 actions, 9548 instances; 임상가가 설계한 biomechanics features를 motion token/description으로 바꾸고 retrieval-enhanced GPT-4 feedback을 생성했다.[Zhang et al. 2024, arXiv:2308.10526](https://arxiv.org/abs/2308.10526)
- **BiomechGPT:** 71.1 h, 750 participants, 10 clinical motion tasks. activity F1=.91, impairment-presence F1=.88; cadence/speed/TUG/FSST 예측 r=.95/.96/.88/.89였다. 주로 gait/mobility이므로 ARAT로의 전이는 미검증이다.[Cotton et al. 2025, arXiv:2505.18465](https://arxiv.org/abs/2505.18465)

### 결론

수치 지표를 구조화해 언어모델에 제공하는 접근은 선례가 있다. 그러나 **SPARC/PAp/TPAp/TAPV와 정상 subtype percentile을 VLM에 함께 넣어 ARAT/FMA를 평가한 직접 연구는 찾지 못했다.** 따라서 제안된 2-stage architecture의 조합은 기존 구성요소의 결합이지만, 임상적으로는 아직 새롭게 검증해야 할 기여다.

---

## 권장 2-Stage Knowledge-Augmented Architecture

```text
Stage 1 — Measurement and calibration
RGB-D / multi-view video
  → body + hand + object tracking
  → phase segmentation
  → SPARC, PAp, TPAp, TAPV, trunk/joint metrics
  → sensor confidence + missingness
  → covariate-aware normal subtype / manifold distance

Stage 2 — Constrained interpretation
14 representative frames + structured JSON
  → VLM evidence extraction
  → rules/HBM consistency checks
  → ARAT/FMA item posterior + rationale
  → calibrated uncertainty
  → defer-to-clinician when threshold unmet
```

### JSON에 반드시 포함할 항목

- metric value, 단위, 정의, 측정구간
- healthy reference percentile와 가장 가까운 subtype
- sensor confidence, occlusion/missing flags
- compensation flags(체간, 어깨거상, 비정상 timing)
- metric 간 모순 및 out-of-distribution 표시
- 영상만으로 판단한 내용과 수치가 직접 입증한 내용을 구분한 evidence field

---

## 최소 평가설계

1. **분할:** participant-disjoint nested CV + 완전 외부기관 holdout.
2. **Baselines:** 중앙점수/인구학-only, video-only VLM, kinematics-only, RGB specialist, fused model.
3. **Primary outcomes:** item weighted κ, total ICC(A,1), MAE/RMSE, calibration error, Bland–Altman LoA.
4. **Movement-quality outcomes:** compensation F1, SPARC/PAp/TPAp/TAPV error, clinician agreement.
5. **Ablations:** 14 frames, depth, metric별 제거, subtype percentile 제거, JSON 제거, rule/HBM 제거.
6. **Strata:** severity, paretic side, hand size, object size, skin tone, camera view, occlusion, assistive support.
7. **Flatlining test:** 예측분산/실제분산 비, severity-bin별 slope, score entropy, score-1 baseline 대비 개선.
8. **Explanation faithfulness:** JSON metric을 반사실적으로 바꿨을 때 설명·점수가 예상 방향으로 변하는지 검사.

---

## Evidence gaps 및 반론

- **“임상척도는 주관적이라 쓸모없다”는 과장이다.** 높은 ICC와 타당도가 반복 입증됐다. 자동화는 대체보다 보완으로 정당화해야 한다.
- **“SPARC 하나로 FMA/ARAT를 대체”할 수 없다.** 운동학은 clinical score 분산의 일부만 설명하며 과제·중증도 의존적이다.
- **“GMM 6개 subtype”은 현재 결과가 아니라 사전등록할 설계 선택이다.** cluster 수를 데이터에 맞춰 사후 고정하면 과적합 위험이 크다.
- **“RGB-D는 Vicon과 동일”하지 않다.** 단순 ROM과 체간 이동은 유망하지만 회전·손가락·미분 기반 metric은 별도 검증이 필요하다.
- **“VLM 설명이 자연스럽다=점수가 정확하다”가 아니다.** VLM의 flatlining·overconfidence·prompt 민감성을 독립 평가해야 한다.
- **3-view ARAT 89%**는 출판된 임상 SOTA가 아니라 preprint의 binary 2-vs-3 결과이며, patient-disjoint 여부가 불명확하다.[Ahmed & Rikakis 2025](https://arxiv.org/abs/2505.01680)

---

## 우선 읽기·재현 순위

1. **VLM flatlining 재현:** Li et al. 2025 — Qwen2.5-VL video-only와 `video+JSON`을 동일 환자분할에서 비교.[arXiv:2511.17727](https://arxiv.org/abs/2511.17727)
2. **운동학 임상앵커:** Alt Murphy et al. 2012 — ARAT와 smoothness/time/trunk의 연관.[DOI](https://doi.org/10.1177/1545968312448234)
3. **SPARC 검증:** Bayle et al. 2024 및 Saes et al. 2021.[DOI 2024](https://doi.org/10.1186/s12984-024-01382-1) [DOI 2021](https://doi.org/10.1186/s12984-021-00937-w)
4. **PAp/TPAp/TAPV:** Qiu et al. 2022 — 작은 N을 확장 재현.[DOI](https://doi.org/10.1109/EMBC48229.2022.9871891)
5. **센서 동시검증:** Faity et al. 2022의 metric-dependent 오류를 제안 장비에서 재검증.[DOI](https://doi.org/10.3390/s22072735)
6. **계층 지식증강:** Ahmed et al. 2024의 HBM을 ARAT item posterior와 결합.[DOI](https://doi.org/10.1109/TNSRE.2024.3450008)
7. **정상 다양성:** Jarque-Bou 2019 + Herbst 2020을 토대로 subtype stability 분석.[DOI 1](https://doi.org/10.1186/s12984-019-0536-6) [DOI 2](https://doi.org/10.1371/journal.pone.0234969)
8. **자동 FMA 대규모 임상검증:** Wang et al. 2024를 외부기관·환자분리 설계로 재현.[DOI](https://doi.org/10.1177/02692155241251434)

---

## Open questions

1. 구조화 운동학 JSON이 환자 단위 외부검증에서도 FMA flatlining을 제거하는가?
2. 정상 subtype percentile이 hand/object size와 global z-score를 넘어 증분타당도를 갖는가?
3. markerless SPARC·TPAp·TAPV의 LoA가 임상적으로 의미 있는 변화보다 작은가?
4. 시스템이 과제 성공과 정상 협응 회복을 구분하는가?
5. 생성 설명이 실제 metric에 인과적으로 grounded되어 있는가?
6. 어떤 불확실성 threshold에서 자동판정 대신 평가자 검토로 넘겨야 하는가?

---

## Sources

1. Hsueh IP et al. (2009). *Psychometric Comparisons of 4 Measures for Assessing Upper-Extremity Function in People With Stroke.* https://doi.org/10.2522/ptj.20080285
2. Kristersson T et al. (2019). *Evaluation of a short assessment for upper extremity activity capacity early after stroke.* https://doi.org/10.2340/16501977-2534
3. Hernández ED et al. (2019). *Intra- and inter-rater reliability of Fugl-Meyer Assessment of Upper Extremity in stroke.* https://doi.org/10.2340/16501977-2590
4. Valladares B et al. (2024). *The association between dexterity and upper limb impairment during stroke recovery.* https://doi.org/10.3389/fneur.2024.1429929
5. Schwarz A et al. (2019). *Systematic Review on Kinematic Assessments of Upper Limb Movements After Stroke.* https://doi.org/10.1161/STROKEAHA.118.023531
6. Alt Murphy M et al. (2012). *Movement Kinematics During a Drinking Task Are Associated With the Activity Capacity Level After Stroke.* https://doi.org/10.1177/1545968312448234
7. Bayle N et al. (2024). *Measurement properties of movement smoothness metrics...* https://doi.org/10.1186/s12984-024-01382-1
8. Saes M et al. (2021). *Smoothness metric during reach-to-grasp after stroke: part 2.* https://doi.org/10.1186/s12984-021-00937-w
9. Qiu Q et al. (2022). *Evaluation of Changes in Kinematic Measures...* https://doi.org/10.1109/EMBC48229.2022.9871891
10. Kim WS et al. (2016). *Upper Extremity Functional Evaluation by Fugl-Meyer Assessment Scoring Using Depth-Sensing Camera...* https://doi.org/10.1371/journal.pone.0158640
11. Li Y et al. (2022). *A Novel Automated RGB-D Sensor-Based Measurement...* https://doi.org/10.3390/brainsci12101380
12. Zamin SA et al. (2023). *BIONICS: A Low-Cost Tele-Evaluation Tool...* https://doi.org/10.1177/15459683231184186
13. Wang Z et al. (2024). *Clinical validation of automated depth camera-based measurement...* https://doi.org/10.1177/02692155241251434
14. Zhou YM et al. (2025). *Estimating Upper Extremity Fugl-Meyer Assessment Scores From Reaching Motions Using Wearable Sensors.* https://doi.org/10.1109/JBHI.2025.3542037
15. Ahmed T, Rikakis T (2025). *Automated ARAT Scoring...* arXiv:2505.01680. https://arxiv.org/abs/2505.01680
16. Deb S et al. (2022). *Graph Convolutional Networks for Assessment of Physical Rehabilitation Exercises.* https://doi.org/10.1109/TNSRE.2022.3150392
17. Li V et al. (2025). *The Potential and Limitations of Vision-Language Models for Human Motion Understanding...* arXiv:2511.17727. https://arxiv.org/abs/2511.17727
18. Collins KC et al. (2018). *Getting a kinematic handle on reach-to-grasp: a meta-analysis.* https://doi.org/10.1016/j.physio.2017.10.002
19. Alt Murphy M et al. (2011). *Kinematic Variables Quantifying Upper-Extremity Performance After Stroke...* https://doi.org/10.1177/1545968310370748
20. van Kordelaar J et al. (2012). *Unraveling the interaction between pathological upper limb synergies and compensatory trunk movements...* https://doi.org/10.1007/s00221-012-3169-6
21. Jarque-Bou NJ et al. (2019). *Kinematic synergies of hand grasps...* https://doi.org/10.1186/s12984-019-0536-6
22. Herbst Y et al. (2020). *Analysis of subject specific grasping patterns.* https://doi.org/10.1371/journal.pone.0234969
23. Jarque-Bou NJ et al. (2020). *Sharing of hand kinematic synergies across subjects...* https://doi.org/10.1038/s41598-020-63092-7
24. Faity G et al. (2022). *Validity and Reliability of Kinect v2 for Quantifying Upper Body Kinematics...* https://doi.org/10.3390/s22072735
25. Lafayette TBG et al. (2023). *Validation of Angle Estimation Based on Body Tracking Data...* https://doi.org/10.3390/s23010003
26. Hamilton RI et al. (2024). *Comparison of computational pose estimation models for joint angles with 3D motion capture.* https://doi.org/10.1016/j.jbmt.2024.04.033
27. Lee U et al. (2025). *Validity and reliability of single camera markerless motion capture systems...* https://doi.org/10.3389/fbioe.2025.1570637
28. Ahmed T et al. (2024). *A Hierarchical Bayesian Model for Cyber-Human Assessment...* https://doi.org/10.1109/TNSRE.2024.3450008
29. Tang J et al. (2025). *Rehabilitation Exercise Quality Assessment and Feedback Generation Using Large Language Models...* arXiv:2505.18412. https://arxiv.org/abs/2505.18412
30. Zhang et al. (2024). *UbiPhysio...* arXiv:2308.10526. https://arxiv.org/abs/2308.10526
31. Cotton et al. (2025). *BiomechGPT...* arXiv:2505.18465. https://arxiv.org/abs/2505.18465

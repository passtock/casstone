# 임상 손가락 3D 추적 알고리즘 비교 및 품질관리 가이드

**조사 기준일:** 2026-09-18  
**적용 맥락:** 단일 RGB-D 카메라로 뇌졸중 환자의 손가락 랜드마크를 추적하여 파지 간격, 관절각, 속도·시간 지표를 산출하는 연구

## 결론부터

1. **현재 연구의 실시간 주 파이프라인은 MediaPipe 2D 랜드마크 + D455 깊이 융합으로 유지하는 것이 합리적**이다. 다만 MediaPipe의 `world_landmarks`를 mm 기준값으로 쓰지 말고, RGB에 정렬된 깊이와 카메라 내부 파라미터로 다시 카메라 좌표계에 복원해야 한다.
2. **WiLoR를 오프라인 2차 추정기와 품질관리 모델로 추가하는 것이 가장 실용적**이다. HaMeR보다 작고 최신 임상 유사 비교에서 가장 낮은 오류를 보였지만, WiLoR 역시 단안 RGB의 MANO 추정이므로 절대 위치·척도를 직접 보장하지 않는다.
3. 깊이 결합은 **보이는 표면점의 척도 문제**는 상당 부분 해결하지만, **가려진 관절의 위치 문제**는 해결하지 못한다. 가려진 좌표는 측정값이 아니라 모델 기반 대치값이다.
4. 현재 과제 중 **손목/손바닥 궤적, 접촉 전 MGA와 tMGA**는 검증 후 주 지표로 사용할 가능성이 높다. 반면 **원통·구·측면 집기 중 접촉 이후의 PIP/DIP 각도**는 단일 시점에서 주 지표로 두기 어렵다.
5. 필터는 잘못된 좌표를 올바른 좌표로 만들지 않는다. **먼저 관측 지지 여부와 불확실성을 판정하고, 그 다음에 통과한 좌표만 평활화**해야 한다. 특히 떨림을 결과로 볼 경우 일반 저역통과 필터는 실제 임상 신호까지 지운다.

---

## 1. 비교 수치를 읽는 법

모델 논문의 숫자는 같은 시험이 아니다.

- **PA-MPJPE**는 예측과 정답을 Procrustes 유사변환으로 정렬한 뒤 계산한다. 즉 평행이동·회전·척도 차이를 제거한 *손 모양 오차*에 가깝다. PA-MPJPE 5 mm가 카메라 좌표계의 절대 위치 오차 5 mm라는 뜻은 아니다.
- **PCK@0.05**는 손 크기로 정규화된 2D 임계값 안에 들어온 관절 비율이다. mm 오차가 아니다.
- **COCO hand AP**는 2D OKS 기반 검출 지표다. 3D 물리 정확도가 아니다.
- 속도 역시 전체 영상 파이프라인, 손 검출기만, 잘린 손 영상의 자세 추정기만을 각각 보고하는 경우가 섞여 있다.

따라서 아래 표는 숫자의 우열보다 **출력의 성격과 임상 계측 적합성**을 비교하는 용도로 읽어야 한다.

## 2. 주요 모델 비교

| 모델 | 핵심 방식·출력 | 대표 정확도 | 공개 속도와 범위 | 임상 계측 판단 |
|---|---|---|---|---|
| **MediaPipe Hand Landmarker** | 손바닥 검출 후 21개 랜드마크 회귀. 정규화된 2.5D 좌표와 손 중심 `world_landmarks` 제공 | 원 논문은 Full 모델 MSE 10.05를 보고하지만 모델 내부 지표라 다른 모델의 mm 오차와 비교 불가. 2026년 cSCI/건강인 실물 파지 연구에서는 WiLoR·HaMeR보다 정확도가 낮고, 채택된 정답 프레임의 약 22%에서 예측을 내지 못함 | 공식 Pixel 6 전체 파이프라인: CPU 17.12 ms, GPU 12.27 ms, 약 58/81 fps | **실시간 2D 검출기로 최적**. 깊이와 결합할 때 유용하지만, 자체 3D를 절대 mm로 사용하면 안 됨 |
| **HaMeR (CVPR 2024)** | 대규모 ViT-H로 MANO 손 메시·21 관절을 프레임별 복원. 대규모 혼합 데이터 학습 | FreiHAND 6.0 mm, HO3Dv2 7.7 mm **PA-MPJPE**. HInt NewDays PCK@0.05가 보이는 관절 60.8%에서 가려진 관절 27.2%로 하락 | 논문에 재현 가능한 표준 전체 FPS 없음. 0.5B+ 파라미터급 백본이라 실시간 임상 수집보다 오프라인 분석에 적합 | 어려운 포즈에 강한 2차 모델. 하지만 무가림 벤치마크 수치와 절대 mm를 혼동하면 안 됨 |
| **WiLoR (CVPR 2025)** | 빠른 다중 손 검출기 + ViT MANO 복원 + 영상 정렬 refinement. 14개 데이터셋, 총 4.2M 영상 학습 | FreiHAND 5.5 mm, HO3Dv2 7.5 mm **PA-MPJPE**. 논문 내부 동적 지표에서 jitter 5.92 대 HaMeR 20.43이지만 이 수치는 임상 mm가 아님 | RTX 4090에서 검출기만 Small 175 fps, Medium 138 fps. 전체 복원 FPS는 동일 조건으로 별도 제시되지 않음 | 질문에 든 모델 중 **오프라인 2차 추정/QC 1순위**. 절대 좌표는 깊이 또는 별도 정합 필요 |
| **FrankMocap** | ResNet-50 기반 손 모듈을 신체·얼굴과 SMPL-X로 결합한 2020–2021 세대 모듈형 시스템 | 당시 STB/RHD 등에서 강했으나 최신 HInt의 가림·실사용 조건에서는 HaMeR보다 크게 낮음 | RTX 2080에서 copy-and-paste 전체 9.5 fps, 모델부 13 fps | 재현·역사적 기준선에는 유용하나 **새 임상 파이프라인의 선택 근거는 약함** |
| **MMPose Hand / RTMPose·RTMW** | 단일 모델이 아니라 2D·3D 모델과 데이터셋을 묶는 툴박스. heatmap/SimCC 계열이라 관절별 score를 활용하기 쉬움 | RTMW-x 384×288의 COCO-WholeBody **hand AP 66.4**. RTMW3D-x hand AP 62.7. 3D z는 root-relative | RTMW-l 384×288 CPU pose stage 47.62 ms, 약 21 fps. 사람/손 검출 단계는 제외 | **환자 데이터로 2D 모델을 미세조정할 때 가장 유연**. “MMPose 정확도”라는 단일 숫자는 존재하지 않음 |
| **HandOS (CVPR 2025, 참고)** | 손 검출·좌우 판정·2D/3D·메시를 한 단계로 통합 | FreiHAND 5.0 mm PA-MPJPE, HInt-Ego4D PCK@0.05 64.6% | 임상용 동일 조건 전체 속도 비교는 부족 | 최신 연구 기준선으로는 중요하지만, 뇌졸중·RGB-D 임상 검증 없이 주 모델로 교체하기는 이르다 |

근거: [MediaPipe 공식 문서](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker), [MediaPipe Hands 논문](https://arxiv.org/abs/2006.10214), [HaMeR](https://arxiv.org/abs/2312.05251), [WiLoR](https://arxiv.org/abs/2409.12259), [FrankMocap](https://arxiv.org/abs/2008.08324), [RTMW](https://arxiv.org/abs/2407.08634), [MMPose 공식 저장소](https://github.com/open-mmlab/mmpose), [HandOS](https://arxiv.org/abs/2412.01537).

### 최신 연구 프런티어의 의미

- **StableHand(2026 preprint)**는 프레임별 관측 품질을 명시적으로 추정하고, 나쁜 구간을 생성적 동작 사전으로 복원한다. 가림 구간을 매끄럽게 메우는 데는 유망하지만, 임상에서는 그 결과를 “관측된 좌표”가 아니라 **모델 기반 대치**로 표시해야 한다.
- **UST-Hand(CVPR 2026)**는 불확실성 분포와 시공간 point-cloud 상호작용을 학습한다. RGB-D를 적극 이용하는 차세대 방향이지만, self-supervised 벤치마크 성능이 현재 연구 프로토콜의 절대 관절 계측 타당성을 대신하지는 않는다.
- **Hand Visibility Detector(2026 preprint)**처럼 관절별 가시성을 별도로 추정하는 모델은 좌표 자체를 한 번 더 평활화하는 것보다 품질관리 관점에서 더 유용하다.

근거: [StableHand](https://arxiv.org/abs/2605.18553), [UST-Hand](https://arxiv.org/abs/2605.17742), [Hand Visibility Detector](https://arxiv.org/abs/2608.11574).

---

## 3. MediaPipe 3D 좌표와 깊이 결합

### 3.1 “MediaPipe 3D는 mm가 아니다”의 정확한 해석

현재 API에는 두 좌표가 있다.

- `landmarks`: x·y는 영상 크기로 정규화되고, z는 손목을 원점으로 하며 x와 비슷한 척도를 쓰는 상대값이다.
- `world_landmarks`: 공식 문서는 미터 단위, 손의 기하학적 중심 원점이라고 설명한다.

그러나 `world_landmarks`는 깊이 센서가 측정한 카메라 좌표가 아니라 **단안 영상에서 모델이 복원한 손 중심 3D**다. 초기 MediaPipe 논문에서 상대 깊이는 합성 영상만으로 학습되었다. 따라서 숫자 단위가 meter로 표기되더라도 개인의 실제 손 크기, 카메라까지의 절대 거리, 병적 관절 형태에 대해 계측학적 추적성을 보장하지 않는다. 실무적으로 사용자의 문제 제기, 즉 “그 값을 바로 mm로 해석하면 안 된다”는 판단이 맞다. [공식 좌표 정의](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python), [원 논문](https://arxiv.org/abs/2006.10214)

### 3.2 올바른 deprojection

RGB 영상의 랜드마크 \((u_i,v_i)\)에 대응하는 정렬 깊이를 \(Z_i\)라 하면 카메라 좌표는 다음과 같다.

\[
X_i=\frac{(u_i-c_x)Z_i}{f_x},\qquad
Y_i=\frac{(v_i-c_y)Z_i}{f_y},\qquad
Z_i=Z_i
\]

필수 조건은 다음과 같다.

1. 깊이를 RGB 좌표계로 정렬하고, **정렬 후 좌표계에 맞는 내부 파라미터**를 사용한다.
2. 단일 픽셀 깊이 대신 작은 패치의 중앙값을 사용하되, 손 segmentation과 같은 표면의 깊이 군집만 남긴다.
3. 패치 내 유효 깊이 비율, depth MAD, 깊이 경계까지의 거리, 손/물체 마스크를 함께 저장한다.
4. 깊이 불연속부에서 bilinear 보간을 쓰면 전경·배경 또는 손·물체 깊이가 섞일 수 있으므로 피한다.
5. RGB–depth 시간차와 rolling shutter를 확인한다. 빠른 손가락에서는 수 ms의 시차도 다른 표면을 샘플링하게 한다.

### 3.3 직접 관절별 깊이 샘플링의 함정

deprojection이 주는 것은 해당 픽셀의 **보이는 피부 표면점**이지 해부학적 관절 중심이 아니다.

- 손가락 끝이나 윤곽선에서는 패치가 배경 또는 물체 깊이를 집을 수 있다.
- 물체 접촉 후에는 랜드마크 픽셀의 깊이가 손이 아니라 물체일 수 있다.
- 가린 관절에는 실제 깊이 관측이 없으므로 deprojection 자체가 불가능하다.
- 2D 랜드마크가 잘못된 손가락에 놓이면 정확한 깊이를 붙여도 잘못된 3D 좌표다.

이 때문에 더 안정적인 구현은 다음 두 방식을 조합한다.

- 손목·손바닥·잘 보이는 MCP처럼 넓은 표면에는 **robust local depth**를 직접 사용한다.
- 손가락 전체에는 2D 재투영, 관측된 depth point cloud, 피험자별 bone length, soft joint constraint를 함께 최소화하여 skeleton/MANO를 맞춘다. 단, 병적 자세를 지우지 않도록 정상인 관절 범위를 hard constraint로 두지 않는다.

### 3.4 임상 근거는 어디까지인가

Amprimo 등의 GMH-D 검증은 Azure Kinect의 손목 깊이와 MediaPipe 상대 z를 결합했다. OptiTrack과 동시 측정한 건강인 10명, 200개 영상, 60–100 cm의 열기/닫기·한 손가락/여러 손가락 tapping 과제에서, 가까운 거리의 multi-finger tapping은 손가락별 평균 RMSE가 1 cm 이하였고 single-finger tapping ROM의 평균 bias는 1 mm, 약 94%의 차이는 -13.2~15.1 mm 범위였다. 이는 깊이 결합의 이점을 보여주지만 **건강인, 비접촉 반복과제, 제한된 관절만의 결과**다. 실물 원통·구를 쥔 뇌졸중 손의 가려진 PIP/DIP를 1 cm 이내로 측정했다는 근거는 아니다. [GMH-D 임상 검증](https://arxiv.org/abs/2308.01088)

2026년 cSCI 13명과 건강인 15명의 실물 파지 연구에서는 WiLoR·HaMeR·MediaPipe 등을 비교했으며 전체 평균 PA-MPJPE가 약 13 mm였다. 군 차이는 유의하지 않았지만, MediaPipe는 채택된 정답 프레임의 약 22%에서 예측이 없었다. 또한 전체 후보 프레임 중 엄격한 정답 품질기준을 통과한 것은 약 38%뿐이고, 중증 참가자 2명은 시야 유지 문제로 제외되었으며 정답도 marker system이 아닌 다중 시점 2D 모델의 삼각측량이었다. 따라서 “손상 환자에도 일반화한다”는 긍정적 신호이지, 중증 뇌졸중 손의 절대 계측 타당성 증명은 아니다. [2026 손상·가림 비교 연구](https://arxiv.org/abs/2606.17427)

### 판정

**깊이 결합은 임상적으로 방어 가능한 방법이지만, 자체적으로 신뢰성을 획득하는 방법은 아니다.** 대상 환자, 과제, 카메라 거리, 임상 지표별로 gold standard와 검증해야 한다.

---

## 4. 뇌졸중 환자에서 예상되는 실패 모드

직접적인 중증 뇌졸중 손 데이터의 대규모 공개 벤치마크는 아직 부족하다. 아래는 모델 구조, 가림 연구, cSCI·뇌졸중 임상 연구를 종합한 예상 실패다.

| 상황 | 전형적 출력 증상 | 임상 지표에 생기는 편향 |
|---|---|---|
| 강한 굴곡·주먹 형태 | 손 ROI 축소/소실, 손바닥 검출 실패, 굽힌 손가락을 평균적 자세로 펴서 복원 | 굴곡 정도와 장애 중증도 과소평가, ROM 축소 또는 허위 증가 |
| 손가락끼리 겹침 | index–middle 등 ID 교환, 두 손가락을 하나로 합침, 앞뒤 깊이 순서 반전 | finger-specific angle 불연속, 가짜 속도 peak, 잘못된 TAM |
| 물체에 의한 가림 | 가려진 관절을 MANO prior로 매끄럽게 생성, 물체 깊이를 손 깊이로 할당 | 접촉 후 joint angle과 파지 유지 자세가 실제보다 정상적으로 보임 |
| 불완전 신전·구축 | 정상인 중심 shape/pose prior가 더 곧은 손가락으로 끌어당김 | 신전 결손과 좌우 비대칭 과소평가 |
| 떨림·빠른 release | motion blur, 프레임 누락, ROI 재검출 jump, 30 fps aliasing | 속도·가속도 과대/과소평가, 실제 떨림과 추적 jitter 혼동 |
| 양손 또는 보조 손 개입 | left/right label flip, 손 ID 교환, 한 손 ROI가 다른 손으로 이동 | 좌우·마비측 시계열 혼합 |
| 반사 마커·보조기·붕대·피부/조명 변화 | OOD 검출 저하, 깊이 hole | 특정 중증도 집단의 선택적 결측으로 집단 비교 편향 |
| RGB–depth 정렬·동기 오차 | x·y는 손 위인데 z는 배경/물체, 깊이 spike | 3D 거리·속도에 큰 순간 오류 |

MediaPipe 자체 연구에서도 상대 z는 합성 데이터로만 학습되었고, 별도 강건성 시험에서는 대각선 motion blur가 들어가면 MediaPipe의 손 검출 실패가 50% 이상 발생했으며 네 관절만 가려도 성능이 크게 저하되었다. [강건성 metamorphic test](https://arxiv.org/abs/2303.04566)

중요한 역설은 **MANO·생체역학 제약이 출력을 보기 좋게 만들수록 병적 손을 정상화할 수도 있다는 점**이다. MS-MANO 같은 생체역학 모델은 비현실적 관절을 줄이는 데 유용하지만, 뇌졸중 구축·경직에 건강인 제약을 강하게 적용하면 진짜 병리를 이상치로 제거한다. 제약은 피험자별 bone length와 넓은 soft range로 사용하고, 임상 이상 자체를 배제하는 hard range로 쓰지 않는 편이 안전하다. [MS-MANO](https://arxiv.org/abs/2404.10227)

---

## 5. Jitter와 hallucination을 분리해서 다루는 법

### 5.1 둘은 다른 문제다

- **Jitter:** 실제 위치 주변에서 고주파로 흔들리는 측정 잡음. 시간 필터가 도움이 된다.
- **Hallucination:** 관측이 없거나 틀렸는데 모델 prior가 그럴듯한 좌표를 만든 상태. 매끄럽게 평활화할수록 더 믿을 만해 보일 수 있다.

따라서 “평활화 후 보기 좋다”는 품질 근거가 아니다.

### 5.2 관절별 품질 점수

각 관절·프레임에 다음 정보를 결합한 품질값 \(Q_{j,t}\)를 별도로 계산하는 것이 좋다.

\[
Q_{j,t}=f(\text{visibility},\ \text{depth support},\ \text{edge distance},\
\text{reprojection},\ \text{bone residual},\ \text{temporal innovation},\
\text{model disagreement})
\]

구성 요소는 다음과 같다.

1. **관측 지지:** depth patch 유효 픽셀 비율, local depth MAD, 깊이 경계까지의 거리, hand/object segmentation 일치.
2. **기하학:** 피험자별 bone length의 robust median에서 벗어난 정도, 재투영 오차, 메시와 관측 point cloud 거리, 손·물체의 비현실적 관통.
3. **시간:** Kalman innovation, 속도·가속도·jerk의 robust z-score, forward/backward optical flow 일치도, ROI 재검출 직후 jump.
4. **모델 불일치:** MediaPipe-depth와 WiLoR를 손목 중심/척도 정렬한 후의 관절별 차이, test-time augmentation 또는 ensemble 분산.
5. **가시성:** 별도 관절 가시성 모델 또는 사람이 표본 라벨링한 visible/self-occluded/object-occluded 상태.

MediaPipe의 `min_hand_detection_confidence`, `min_hand_presence_confidence`, `min_tracking_confidence`는 각각 손 검출·손 존재·프레임 간 bounding-box IoU 수준의 문턱값이다. **21개 관절 각각의 정확도 확률이 아니다.** 이 값 하나로 PIP/DIP의 hallucination을 판정하면 안 된다. [MediaPipe 옵션 정의](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)

품질 점수는 뇌졸중 검증 표본에서 “오차가 임상 허용치 이하인가”를 목표로 logistic/isotonic calibration 또는 conformal calibration하여 확률로 바꾸는 것이 가장 좋다. 임의의 confidence 0.5는 임상 문턱값이 아니다.

### 5.3 시간 필터의 역할

| 목적 | 권장 방법 | 주의점 |
|---|---|---|
| 실시간 화면·feedback | One Euro filter, quality-adaptive Kalman/UKF | 속도에 따라 지연이 변하므로 임상 endpoint용 원시값도 보존 |
| 오프라인 gross kinematics | Hampel로 단발 spike 제거 후 zero-phase Butterworth 또는 Savitzky–Golay | cutoff를 데이터와 과제에 맞춰 정하고 전후 결과를 보고 |
| 최적 시계열 재구성 | heteroscedastic Kalman + RTS smoother, kinematic state-space model | 낮은 품질 구간의 측정 covariance를 크게 설정 |
| 떨림 분석 | 원시·보정 신호의 PSD/wavelet, sensor noise floor 비교 | gross-motion용 저역통과 신호와 분리. 떨림 대역을 필터로 제거하지 않음 |

[One Euro filter 원 논문](https://doi.org/10.1145/2207676.2208639)은 실시간 jitter–lag 절충에 유용하지만, 가림 구간의 정답을 복원하는 알고리즘은 아니다.

### 5.4 결측 처리

- 30 fps에서 2–3 프레임 정도의 짧은 gap은 양쪽 끝이 고품질이고 접촉·MGA 같은 중요 사건을 가로지르지 않을 때만 보간을 고려한다.
- 긴 gap, 손가락 ID 교환, 접촉 중 object-occlusion은 **결측으로 유지**한다.
- 모델로 메운 좌표는 `IMPUTED` 또는 `MODEL_ONLY`, 깊이까지 관측된 좌표는 `OBSERVED`, 거부한 좌표는 `MISSING`으로 분리한다.
- 주 분석은 `OBSERVED`만, 보조 민감도 분석에서 `MODEL_ONLY`를 포함하는 방식이 가장 투명하다.

### 5.5 작은 위치 오차가 각도·속도에 미치는 영향

손가락 분절은 짧아서 위치 오차가 증폭된다. 예를 들어 각 끝점의 독립 위치 오차가 5 mm이고 phalanx 길이가 25 mm라면, 한 분절 방향의 1차 근사 오차가 약 \(\sqrt{2}\times5/25\approx0.28\) rad, 즉 약 16°가 될 수 있다. 두 분절로 만든 관절각은 더 불안정할 수 있다.

또한 30 fps에서 연속 두 프레임의 독립 5 mm jitter를 미분하면 속도 잡음의 크기는 대략 \(\sqrt{2}\times5/0.033\approx214\) mm/s다. 따라서 “랜드마크가 대략 맞아 보인다”는 것과 관절각·peak velocity가 임상적으로 맞는다는 것은 전혀 다른 주장이다.

---

## 6. 현재 연구 과제별 권고

| 예정 지표·과제 | 단일 D455 + 랜드마크의 현실성 | 권고 분석 지위 |
|---|---|---|
| 손목/손바닥 3D 궤적, TAPV | 넓은 표면이라 깊이가 안정적이고 가림이 상대적으로 적음 | **검증 후 주 지표 가능** |
| 원통·구·측면 집기의 접촉 전 MGA | thumb/index가 동시에 보이는 프레임을 선택하면 비교적 양호 | **품질조건부 주 지표 가능** |
| tMGA | 절대 척도보다 동기·phase detection에 민감 | **주 지표 가능**, RGB-depth timestamp 검증 필수 |
| 접촉·유지 중 fingertip gap | 물체 깊이 혼입과 occlusion이 큼 | 보조 또는 제외 |
| 맨손 열기/닫기 중 MCP/PIP/DIP 각도 | 정면·측면 배치와 완전 가시 구간에서는 가능하나 짧은 분절 때문에 오차 증폭 | 관절별 검증 후 보조/주 지표 결정 |
| 원통·구 파지 중 PIP/DIP 각도/TAM | self/object occlusion이 구조적으로 큼 | **탐색적 지표**, 가려진 구간은 측정으로 주장하지 않음 |
| 떨림·고주파 운동 | 30 fps는 임상 떨림과 추적 잡음 분리에 불리함 | 가능하면 60 fps 이상 별도 촬영·분석 |

### 권장 모델 구성

1. **실시간:** MediaPipe의 2D \((u,v)\)만 의미론적 랜드마크로 사용한다.
2. **척도:** D455의 정렬 깊이와 calibration으로 보이는 점을 camera-space 3D로 변환한다.
3. **오프라인 감사:** 동일 프레임에 WiLoR를 실행하고, MediaPipe-depth와의 관절별 불일치를 QC feature로 저장한다.
4. **환자 특이 개선:** pilot에서 심한 굴곡·겹침 실패율이 높으면 HaMeR로 단순 교체하기보다, MMPose의 전용 2D hand model을 환자 영상과 occlusion label로 미세조정하는 편이 관절 가시성과 confidence를 통제하기 쉽다.
5. **원자료 보존:** RGB, raw depth, 정렬 depth, 원시 랜드마크, 필터 랜드마크, 품질 플래그와 제외 사유를 모두 저장한다.

### 최소 검증 항목

현재 설계의 “validated 3D kinematics”라는 표현을 유지하려면 다음을 같은 환자군·같은 물체·같은 phase에서 확인해야 한다.

- marker-based system과 동시 측정한 **camera-space MPJPE/RMSE** 및 x·y·z 축별 오차
- landmark별, 과제별, phase별, visible/self-occluded/object-occluded별 오차
- MGA, tMGA, 각도, peak velocity의 Bland–Altman bias와 95% limits of agreement
- ICC와 반복시험 신뢰도, 단 ICC만으로 agreement를 대신하지 않음
- 프레임 검출률, 유효 관절 비율, 최장 연속 gap, trial 제외율을 건강인/뇌졸중 및 중증도별로 보고
- 성공 프레임만의 정확도와 전체 실패율을 반드시 함께 보고

2023년 뇌졸중 생존자 연구에서는 Quest 2의 markerless tracking이 손 위치·속도 같은 일부 지표에서 marker system과 유사한 결과를 냈지만, 실물 파지에 의한 손가락 가림은 포함하지 않았다. 따라서 gross hand motion의 가능성을 뒷받침할 뿐, 현재 과제의 finger-joint validity를 대신하지 않는다. [뇌졸중 HMD–marker 비교](https://doi.org/10.3390/s23187906)

---

## 7. 최종 선택

현재 연구에는 다음 조합이 가장 방어 가능하다.

- **주 추정:** MediaPipe 2D + D455 robust depth deprojection
- **주 지표:** 손목/손바닥 운동, 접촉 전 MGA, tMGA
- **2차 추정·QC:** WiLoR
- **환자 데이터 미세조정 플랫폼:** MMPose 2D Hand
- **비추천:** FrankMocap을 새 주 모델로 채택, HaMeR/WiLoR의 PA-MPJPE를 절대 mm 정확도로 인용, 가려진 관절의 매끄러운 MANO 좌표를 실제 측정으로 취급
- **필수 원칙:** 가시성·깊이 지지·모델 불일치를 통과한 좌표만 임상 계측에 사용하고, 나머지는 대치 또는 결측으로 명시

핵심은 더 큰 모델 하나를 고르는 것이 아니라 **관측된 좌표와 추론된 좌표를 데이터 구조와 통계 분석에서 분리하는 것**이다. 이 구분이 지켜지면 단일 RGB-D 시스템은 일부 임상 운동학 지표에 유용하다. 이 구분이 없으면 출력이 아무리 매끄러워도 장애를 정상화하거나 가림을 수치로 위장할 위험이 있다.

## 주요 근거 문헌

1. Zhang et al. [MediaPipe Hands: On-device Real-time Hand Tracking](https://arxiv.org/abs/2006.10214), 2020.
2. Google AI Edge. [Hand Landmarker 공식 문서](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker), 2026-08-17 갱신.
3. Pavlakos et al. [Reconstructing Hands in 3D with Transformers (HaMeR)](https://arxiv.org/abs/2312.05251), CVPR 2024.
4. Potamias et al. [WiLoR: End-to-end 3D Hand Localization and Reconstruction in-the-wild](https://arxiv.org/abs/2409.12259), CVPR 2025.
5. Rong et al. [FrankMocap](https://arxiv.org/abs/2008.08324), ICCV Workshop 2021.
6. Jiang et al. [RTMW](https://arxiv.org/abs/2407.08634), 2024.
7. Chen et al. [HandOS](https://arxiv.org/abs/2412.01537), CVPR 2025.
8. Amprimo et al. [Hand tracking for clinical applications: validation of GMH and GMH-D](https://arxiv.org/abs/2308.01088), Biomedical Signal Processing and Control, 2024.
9. Manzone et al. [Impact of Hand Impairment and Occlusions on Hand Pose Estimation Accuracy](https://arxiv.org/abs/2606.17427), preprint, 2026.
10. Pu et al. [Robustness Evaluation in Hand Pose Estimation Models using Metamorphic Testing](https://arxiv.org/abs/2303.04566), 2023.
11. Xie et al. [MS-MANO: Enabling Hand Pose Tracking with Biomechanical Constraints](https://arxiv.org/abs/2404.10227), CVPR 2024.
12. Casile et al. [Markerless HMD vs marker-based hand kinematics in stroke survivors](https://doi.org/10.3390/s23187906), Sensors, 2023.

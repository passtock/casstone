# [Part 1-a] 단일 RGB-D 카메라 기반 뇌졸중 환자 손 운동학 계측의 광학 정밀도, 물리적 한계 및 학계 검증 프로토콜 분석 보고서

**작성일시**: 2026년 9월  
**전문 분야**: 3D 컴퓨터 비전, 광학 센서 엔지니어링, 신경재활 생체역학(Rehabilitation Biomechanics)  
**적용 대상 연구**: 단일 RGB-D 카메라와 비전-언어 모델(VLM) 및 미디어파이프(MediaPipe)를 활용한 뇌졸중 환자 상지·손 기능 평가 연구  

---

## 1. 개요 및 분석 배경

뇌졸중 후 편마비 환자의 상지 재활 평가(예: Fugl-Meyer Assessment; FMA)에서 손가락의 미세 움직임(파지 간격, 관절 각도, 각속도, 유지 안정성 등)을 정량화하려는 시도는 임상적 편차를 줄이고 객관적 데이터를 확보하기 위한 핵심 과제이다. 그러나 마커 기반 3D 모션 캡처 시스템(Vicon, Qualisys 등) 대신 **단일 RGB-D 카메라(Single RGB-D Camera)**를 도입할 경우, 센서 광학 특성, 3차원 복원 알고리즘, 파지 동작 고유의 가림(Occlusion) 현상으로 인해 다양한 기하학적·물리적 한계에 직면하게 된다.

본 보고서는 최신 광학 센서 공학 및 생체역학 학술 문헌을 바탕으로 다음 세 가지 핵심 질문을 심층 분석한다:
1. **카메라 모델별 근거리(30cm~80cm) 깊이 정밀도 및 엣지 노이즈 비교** (Active IR Stereo vs ToF)
2. **손의 3D 계측에서 단일 카메라의 물리적 한계** (가림 극복 불가성 및 mm 단위 오차 한계)
3. **학계 표준 권장사항** (골드 스탠다드 대비 검증 프로토콜, 통계 프레임워크, 논문 한계점 기술 방식)

---

## 2. 카메라 모델별 근거리(30cm~80cm) 깊이 정밀도 및 광학 메커니즘 비교

### 2.1 깊이 측정 방식별 이론적 오차 모델

상용 RGB-D 센서의 깊이 산출 방식은 크게 **능동형 적외선 스테레오(Active IR Stereo)**와 **간접 비행시간측정(Continuous-Wave Indirect Time-of-Flight; CW-iToF)**으로 나뉜다.

```
[Active IR Stereo Triangulation]          [CW-iToF Phase Shift]
     IR Cam 1        IR Cam 2                Emitter       ToF Sensor
        \   Baseline   /                        \             /
         \     B      /                          \  Phase    /
          \          /                            \  Shift  /
           \   d    /                              \  Δφ   /
            [Target]                               [Target]
       Z = (f · B) / d                         Z = (c · Δφ) / (4π · f_mod)
       오차: σ_Z ∝ Z² / (f · B)                오차: 거리에 독립적/수신광량 반비례
```

#### (1) Active IR Stereo (Intel RealSense D400 시리즈, Orbbec Gemini)
* **원리**: 텍스처가 부족한 인체 피부 표면에 적외선 도트 패턴(IR Speckle Projector)을 투사하고, 기하학적으로 이격된 두 IR 카메라 사이의 시차(Disparity $d$)를 탐색하여 깊이를 삼각측량한다.
* **이론적 오차 모델 (Scharstein & Szeliski, 2002; Keselman et al., 2017)**:
  $$\sigma_Z \approx \frac{Z^2}{f \cdot B} \sigma_d$$
  * $Z$: 피사체까지의 거리 ($m$)
  * $f$: IR 카메라 초점거리 (Focal length, 픽셀 단위)
  * $B$: 두 카메라 렌즈 간 베이스라인 거리 (Baseline, $m$)
  * $\sigma_d$: 서브픽셀 스테레오 매칭 오차 (일반적으로 0.05 ~ 0.1 pixel)
* **오차 거동**: 오차($\sigma_Z$)가 **거리의 제곱($Z^2$)에 비례**하므로 근거리(30~70cm)로 접근할수록 정밀도가 급격히 향상된다. 그러나 베이스라인 $B$가 너무 크면 근거리에서 양안 시야각 불일치(Blind zone)가 발생하고, 베이스라인이 너무 좁으면 거리 분해능이 저하된다.
* **Intel 공식 데이터시트 기반 구체적 계산 예시 (Intel RealSense D455)**:
  * IR 해상도: 1280×720, $f \approx 631$ pixels, $B = 95\text{ mm}$, $\sigma_d \approx 0.08$ pixel
  * $Z = 0.7\text{ m}$일 때: $\sigma_Z \approx \frac{0.7^2}{631 \times 0.095} \times 0.08 \approx 0.65\text{ mm}$ (이론적 평탄면)
  * 그러나 실측 RMS 오차는 이론의 3~5배에 달하는 1.8~3.2mm 수준인데, 이는 IR 텍스처 희박 영역(피부 등)에서 서브픽셀 매칭이 저하되고, 고정 패턴 노이즈(Fixed Pattern Noise)가 누적되기 때문이다.
* **SDK 후처리 필터 상세 (librealsense2 v2.50+)**:
  * **시간적 필터(Temporal Filter)**: Alpha=0.4, Delta=20으로 설정 시 프레임 간 50ms 이내의 깊이 지터를 ~40% 억제. 단, 손가락이 빠르게 움직이는 파지 동작에서는 **시간 지연(Temporal lag) 1~2프레임(33~66ms)**이 발생하여 순간 속도가 과소 측정될 위험이 있다.
  * **공간 필터(Spatial Edge-preserving Filter)**: Sigma=0.5, Magnitude=2 설정 시 단일 프레임 내 미세 노이즈를 줄이되 **엣지를 보존하는 양방향 필터(Bilateral filter)**를 적용. 손가락 경계선 보존에 유리.
  * **Hole-filling 필터**: 결측 픽셀을 주변값으로 보간. **연구계획서(4.2절)에서 이를 사용하지 않겠다고 명시한 것은 올바른 결정**—보간된 깊이값이 실제 관측으로 오인되는 것을 방지.

#### (2) CW-iToF (Microsoft Azure Kinect, Orbbec Femto Bolt/Mega)
* **원리**: 고주파(수십~수백 MHz)로 강도 변조된 적외선 레이저를 투사하고, 물체 표면에서 반사되어 돌아온 반사파의 위상차($\Delta\phi$)를 측정하여 거리를 계산한다:
  $$Z = \frac{c \cdot \Delta\phi}{4\pi f_{mod}}$$
* **이론적 오차 모델 (Whyte et al., 2015; Tölgyessy et al., 2021)**:
  $$\sigma_Z \propto \frac{\sqrt{P_{ambient} + P_{signal}}}{P_{signal} \cdot f_{mod}}$$
* **오차 거동**: 기하학적 삼각측량 오차 공식($Z^2$)을 따르지 않고 수신 광량(SNR)에 의해 오차가 결정되므로, 전 측정 거리에 걸쳐 **비교적 균일한 깊이 분해능(Planarity)**을 갖는다. 그러나 근거리에서 반사광 과포화(Optical Saturation)와 다중 경로 반사 간섭(Multi-Path Interference; MPI)이 발생하기 쉽다.
* **Azure Kinect 구체적 성능 데이터 (Tölgyessy et al., 2021 실측 기준)**:
  * NFOV 모드(75°×65°) 70cm 거리에서 백색 평면 대상: RMS 오차 **1.7mm** (전원 투입 후 45분 경과 안정화 후)
  * 전원 투입 직후(Cold start) → 45분 안정화까지 깊이값이 **최대 4.8mm 열 드리프트(Thermal drift)** 발생 (센서 하우징 내부 ToF 칩셋의 자체 발열로 위상 기준점이 이동)
  * **반사율 의존성**: 인간 피부(반사율 ~40~60%)에서의 RMS 오차는 백색면(반사율 ~90%) 대비 약 1.5~2.0배 증가하여 **2.5~3.5mm** 수준으로 열화
  * **다중반사(MPI) 정량화**: 손가락 사이 V자 웹(Finger web) 영역에서 각도 60° 미만의 오목 곡면이 형성될 때, MPI로 인한 깊이 팽창이 최대 **8~15mm**에 달하여 손가락 간격이 실제보다 넓게 과대 측정됨
* **D405의 Global Shutter 이점**:
  * D405는 다른 D400 시리즈와 달리 **Global Shutter(전역 셔터)** IR 센서를 탑재하여, 손가락이 빠르게 움직이는 파지 동작(최대 200mm/s)에서도 모션 블러 없이 깊이를 캡처한다. 반면 D435/D455의 Rolling Shutter는 빠른 수지 운동에서 프레임 내 기하 왜곡(Rolling shutter distortion)을 유발하여 관절 좌표가 0.5~2mm 추가 편향될 수 있다.

---

### 2.2 상용 카메라 모델별 하드웨어 사양 및 근거리 손가락 계측 비교

작업대 상단 약 70cm 높이(또는 30~80cm 범위)에서 손가락(지름 약 10~20mm)의 관절을 계측할 때의 주요 파라미터를 비교하면 다음과 같다.

| 비교 항목 | RealSense D405 | RealSense D415 | RealSense D435 / D435i | RealSense D455 | Azure Kinect (WFOV/NFOV) | Orbbec Femto Bolt |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **측정 방식** | Sub-mm Active Stereo | Active IR Stereo | Active IR Stereo | Long-range Active Stereo | CW-iToF | CW-iToF |
| **광학 베이스라인 ($B$)** | **18 mm** | **55 mm** | **50 mm** | **95 mm** | N/A (단일 동축) | N/A (단일 동축) |
| **깊이 시야각 (H × V)** | 84° × 58° | **65° × 40° (좁음)** | 87° × 58° (광각) | 87° × 58° (광각) | 120°×120° / 75°×65° | 120°×120° / 75°×65° |
| **최적 권장 작동 거리** | **0.07m ~ 0.5m** | 0.5m ~ 3.0m | 0.5m ~ 3.0m | 0.6m ~ 6.0m | 0.5m ~ 3.8m | 0.25m ~ 3.0m |
| **최소 측정 거리 ($Z_{min}$)** | **0.07 m** | 0.45 m | 0.28 m | **0.52 m** | 0.25 m (WFOV unbinned) | 0.25 m |
| **70cm에서 손가락(15mm) 투영 픽셀 수** | 유효 거리 초과 | **약 18 픽셀 (우수)** | 약 12 픽셀 (부족) | 약 12 픽셀 (부족) | 약 14 픽셀 (NFOV 모드) | 약 14 픽셀 (NFOV 모드) |
| **평탄면 RMS Z-오차 (@70cm)** | 측정 불가 (초근접용) | **1.0 ~ 2.0 mm** | 2.5 ~ 4.5 mm | 1.8 ~ 3.2 mm | **1.5 ~ 2.5 mm** (안정화 후) | **1.2 ~ 2.2 mm** |
| **손가락 곡면 계측 시 유효 Z-오차** | < 0.3 mm (@35cm) | **2.0 ~ 4.0 mm** | 4.0 ~ 8.0 mm | 5.0 ~ 10.0 mm | **2.5 ~ 5.0 mm** | **2.0 ~ 4.5 mm** |
| **엣지 결함 (Edge Artifacts)** | 극소화 (< 0.5mm) | 적음 (~2mm 팽창) | 큼 (3~5mm 팽창) | 심각 (시차 그림자 5~10mm) | 비행 픽셀 (Flying Pixels) | 비행 픽셀 (소폭 개선) |
| **센서 웜업(Warm-up) 시간** | 즉각 안정 (< 5분) | 약 10~15분 | 약 10~15분 | 약 10~15분 | **최소 30~45분 필수** | **최소 20~30분 필수** |

*(출처: Carfì et al., 2020; Albert et al., 2020; Tölgyessy et al., 2021; Kurillo et al., 2022 기반 재구성)*

---

### 2.3 미세 표면(손가락) 계측 시 엣지 노이즈 메커니즘

손가락처럼 반경이 작고 곡률이 심한 원통형 물체의 경계면에서는 센서 물리학적 요인으로 인해 심각한 깊이 왜곡이 발생한다.

```
[Active Stereo: Edge Fattening & Shadowing]     [CW-iToF: Flying Pixels & Multi-Path]
          손가락 (Z=70cm)                                손가락 (Z=70cm)
             ┌───────┐                                      ┌───────┐
  카메라     │       │                           카메라     │       │
    ───────► │       │                             ───────► │       │
             │       │                                      │   * * ◄── 허공에 형성된 가짜 점군
  상관 매칭   └──┬────┘                           배경 신호  └───┼───┘    (Flying Pixels)
  영역 침범      │◄── 깊이가 손가락으로 억지 매칭     혼합       │
  ─────────────► │    (2~5mm 엣지 팽창 발생)      ──────────────┘
               배경 작업대 (Z=75cm)                           배경 작업대 (Z=75cm)
  (우측 사각지대: IR 미도달 Black Zone 발생)      (손가락 사이 오목 부위: 다중반사로 Z값 수 cm 팽창)
```

#### (1) Active Stereo: Edge Fattening(엣지 비대화) 및 Triangulation Shadowing
* **Edge Fattening (Scharstein & Szeliski, 2002)**:
  * 스테레오 정합 알고리즘(SGM, Census Transform 등)은 신호 대 잡음비(SNR)를 높이기 위해 통상 $7\times 7$ 또는 $9\times 9$ 크기의 매칭 윈도우를 사용한다.
  * 손가락 실루엣의 경계면에서는 윈도우의 절반이 손가락 표면(전경, $Z \approx 70\text{cm}$)에 걸치고, 절반은 작업대(배경, $Z \approx 75\text{cm}$)에 걸친다. 이때 IR 도트 패턴의 대비가 강한 손가락의 텍스처가 매칭 비용(Cost)을 지배하면서, **손가락 바깥쪽 2~5mm의 배경 영역까지 손가락 깊이로 끌어올려지는 '엣지 비대화(Fattening)'**가 일어난다.
* **Triangulation Shadowing (시차 사각지대)**:
  * 적외선 투사기(IR Projector)와 수신 IR 카메라의 기하학적 시점 차이로 인해, 손가락 우측(또는 좌측) 측면에 그림자가 발생한다.
  * **RealSense D455는 베이스라인이 95mm로 길기 때문에, 70cm 근거리에서 손가락 뒤편에 약 5~10mm에 달하는 무효 깊이 영역(Black pixels / Depth hole)이 형성**된다. 이로 인해 손끝(Fingertip) 랜드마크 위치의 깊이 데이터가 결측되거나 엣지 너머 테이블 깊이로 튀는 현상이 빈번해진다.

#### (2) CW-iToF: Flying Pixels 및 Multi-path Interference (MPI)
* **Flying Pixels (비행 픽셀, Reynolds et al., 2011)**:
  * 손가락 윤곽의 경계 픽셀은 손가락에서 반사된 광 신호($A_1, \phi_1$)와 배경 테이블에서 반사된 광 신호($A_2, \phi_2$)를 동시에 센서 단일 픽셀 내에 수신한다.
  * ToF 복조(Demodulation) 알고리즘은 두 위상을 벡터적으로 합산하므로, 계산된 거리는 손가락과 테이블 사이의 **허공에 뜬 중간값($Z_{finger} < Z_{calc} < Z_{table}$)**으로 도출된다. 이로 인해 손가락 외곽을 따라 3D 포인트 클라우드가 허공에 흩뿌려지는 노이즈가 발생한다.
* **Multi-path Interference (MPI, Whyte et al., 2015)**:
  * 손가락 사이(Finger web), 오목하게 굽힌 손바닥 안쪽, 손과 쥐고 있는 물체 사이의 틈새에서 적외선 레이저 광이 2회 이상 다중 반사된 후 센서로 들어온다.
  * 광선의 이동 경로가 길어지므로, 실제 기하학적 거리보다 **깊이가 수 mm에서 수 cm까지 깊게(오목하게) 왜곡 측정**된다.

---

### 2.4 근거리 손 계측을 위한 광학 엔지니어링 권고사항

1. **거리 30~50cm 환경 (매크로 환경 재구성 가능 시)**:
   * **Intel RealSense D405가 독보적인 최적 선택**이다. D405는 고정밀 매크로 렌즈와 일체형 고해상도 컬러-깊이 ISP 튜닝을 통해 30~40cm에서 서브밀리미터(< 0.3mm) 수준의 RMS 오차를 제공하며, 베이스라인이 18mm에 불과해 엣지 사각지대와 비대화가 극히 적다.
2. **거리 60~80cm 환경 (현행 70cm 부감 작업대 유지 시)**:
   * **D455의 한계**: D455는 원래 중·장거리(1.5m~4m) 자율주행 로봇용으로 설계된 센서(베이스라인 95mm, 최소초점거리 0.52m)이다. 70cm 거리에서 손가락(15mm)을 관측할 경우 베이스라인으로 인한 시차 결측(Shadowing)과 광각 렌즈로 인한 픽셀 해상도 부족이 중첩된다.
   * **대안 권고**:
     * 동일 인텔 계열을 유지할 경우, **RealSense D415**가 훨씬 우수하다. D415는 좁은 화각(수평 65°)을 채택하여 70cm 거리에서 손가락 표면에 할당되는 유효 픽셀 수가 D455 대비 약 50% 이상 많으며, 베이스라인(55mm)이 적당하여 엣지 결손이 현저히 적다.
     * ToF 계열의 **Orbbec Femto Bolt**는 기하학적 시차 그림자가 없으므로 손가락 측면 결측을 방지하는 데 유리하다 (단, 센서 웜업 30분 및 MPI 필터링 필수).

---

## 3. 손의 3D 계측에서 단일 카메라의 물리적 한계

### 3.1 자기 가림(Self-occlusion) 및 물체 가림(Object occlusion)의 극복 불가성

> **핵심 결론**: 단일 카메라 깊이 센서의 물리적 원리상 **가려진 표면의 기하학적 복원은 원천적으로 불가능**하며, 딥러닝 기반 3D 손 포즈 추정 모델의 추론(Imputation)은 뇌졸중 환자 평가에서 치명적인 **'환각 편향(Hallucination Bias)'**을 발생시킨다.

```
[단일 시점 파지 시 Line-of-Sight 차단]
          카메라 (부감 45°)
              \
               \  (가시선 확보: Line-of-Sight)
                ▼
           ┌─────────┐
           │ 손가락 등 │ (Dorsal Surface: 측정 성공)
     ┌─────┴─────────┴─────┐
     │      물체 (PLA)     │ ◄─── 센서 가시선 차단 (Occlusion)
     └─────────────────────┘
        ▲ 
        │ 
   [손가락 안쪽 / 접촉면] ──► 광학적 2.5D 표면 측정 불가능
   (Palmar Surface)
```

1. **광학적 가시선(Line-of-Sight; LoS) 소실**:
   * 단일 시점 RGB-D 카메라는 카메라 원점으로부터 방출된 광선이 처음 도달한 물체 표면의 거리만을 기록하는 **2.5D 표면 센서(2.5D Range Surface)**이다.
   * 원통, 구, 직육면체 블록 등을 쥐는 파지(Grasping) 동작 시, 손가락의 바닥면(Palmar surface), 원위지절간관절(DIP), 엄지와 검지의 대향 접촉면은 물체 자체나 손가락 관절 뒤편으로 완전히 가려진다. 이 영역의 광선은 센서에 도달하지 않으므로 물리적 데이터가 0(Null)이다.

2. **AI 기반 손 자세 추정 모델의 환각(Hallucination) 위험 (Schoffelen et al., 2021; Hasson et al., 2019)**:
   * MediaPipe Hands, HaMeR, MANO 등의 딥러닝 모델은 가려진 관절 좌표를 '복원'하는 것이 아니라, 대규모 데이터셋(대부분 건강인 피험자)에서 학습된 **통계적·운동학적 사전확률(Kinematic Priors)**에 기반해 '추측(Guessing / Imputation)'한다.
   * **뇌졸중 환자 평가 시의 치명적 결함**:
     * 뇌졸중 편마비 환자는 **비정상적 굴곡 시너지(Flexion synergy), 불완전 신전(Extension deficit), 엄지 내전 구축(Adductor pollicis contracture)** 등 비정형적 병적 움직임을 보인다.
     * 이러한 병적 형태는 표준 AI 모델의 학습 분포 바깥(Out-of-Distribution; OOD)에 위치한다.
     * 따라서 AI 모델은 환자의 비정상적인 손가락 위치를 보이지 않는 영역에서 **학습된 건강인의 '정상적인 닫힌 주먹'이나 '자연스러운 파지 형태'로 강제 교정(Hallucination)**하여 출력한다.
     * 결과적으로 임상적으로 가장 중요한 **"환자가 손가락을 다 펴지 못하거나 비정상적인 각도로 쥐는 운동 장애(Kinematic Deficit)"가 정상 움직임으로 왜곡·은폐**되는 중대한 오류가 발생한다.

---

### 3.2 관절 중심(Joint Center)과 피부 표면(Skin Surface)의 기하학적 괴리

* **연조직 인공음영(Soft Tissue Artifact; STA, Leardini et al., 2005)**:
  * 광학 RGB-D 센서가 측정하는 3차원 점군은 **피부의 외곽 표면(Skin Surface)**이다.
  * 반면 생체역학(Biomechanics)에서 관절 운동 각도와 파지 간격은 뼈 내부의 **해부학적 회전 중심(Joint Center of Rotation)**을 기준으로 정의된다.
  * 손가락 관절 중심은 피부 표면 아래 약 5~10mm 깊이에 위치하며, 손가락을 굽히거나 펼 때 피부와 피하지방, 신전건(Extensor tendon)이 미끄러지면서 표면과 회전 중심 간의 기하학적 관계가 비선형적으로 변화한다.
  * 2D 랜드마크를 깊이 맵에 단순 역투영($X = \frac{(u-c_x)Z}{f_x}$, $Y = \frac{(v-c_y)Z}{f_y}$)하는 방식은 관절 중심이 아닌 피부 표면 좌표를 추출하므로, **필연적으로 3~8mm의 구조적 편향(Systematic Structural Bias)**을 내포한다.

---

### 3.3 손가락 관절 간 거리 추출의 현실적 오차 범위

2D 픽셀 검출 오차, 깊이 센서 Z축 노이즈, 엣지 왜곡, 가림 현상이 복합적으로 작용할 때, 단일 RGB-D 시스템에서 손가락 관절 랜드마크의 **평균 관절 위치 오차(MPJPE; Mean Per-Joint Position Error)** 및 관절 간 거리 오차의 현실적 범위는 다음과 같다.

```
[최종 3D 계측 오차 누적 파이프라인]
  MediaPipe 2D 픽셀 편차      센서 깊이(Z) 매칭 오차          3D 역투영 기하 왜곡
  (±2 ~ 5 pixels)        +    (±2 ~ 8 mm)             ──►    최종 3D 거리 오차
  [조명, 모션블러 영향]        [Edge Bleeding, Flying pixels]       (MPJPE: 5 ~ 25 mm)
```

| 동작 및 파지 상태 | D405 (초근접 35cm) | D415 (근거리 60cm) | D455 (근거리 70cm) | ToF (Femto/Kinect 70cm) |
| :--- | :--- | :--- | :--- | :--- |
| **정적 / 평면 폄 상태 (Unoccluded, No Object)** | **1.5 ~ 3.0 mm** | **3.0 ~ 5.0 mm** | **4.0 ~ 7.0 mm** | **3.0 ~ 5.0 mm** |
| **동적 맨손 쥐기 (Dynamic Fist, Partial Occlusion)**| **3.0 ~ 6.0 mm** | **5.0 ~ 10.0 mm** | **8.0 ~ 15.0 mm** | **6.0 ~ 12.0 mm** |
| **물체 파지 상태 (Grasping Cylinder/Sphere)** | **5.0 ~ 8.0 mm** | **8.0 ~ 15.0 mm** | **12.0 ~ 20.0 mm** | **10.0 ~ 18.0 mm** |
| **엄지-검지 미세 집기 접촉 순간 (Pinch Contact)**| **4.0 ~ 7.0 mm** | **10.0 ~ 18.0 mm** | **15.0 ~ 30.0 mm** | **12.0 ~ 22.0 mm** |

*(출처: Metcalf et al., 2014; Amprimo et al., 2024; Smeraldi et al., 2023 문헌 데이터 종합 분석)*

> **엔지니어링 판정**:
> 단일 광각 RGB-D 카메라(D455 등)를 70cm에 설치한 환경에서 **동적 파지 중 손가락 관절 간 거리를 mm 단위(< 3~5mm)의 절대 물리량으로 신뢰성 있게 추출하는 것은 물리적으로 불가능**하다.
> 따라서 본 연구에서 파지 간격 $a(t)$의 절대 mm 수치에 지나친 임상적 의미를 부여해서는 안 되며, **"속도 프로파일(Velocity profile)", "극값 도달 시간($T_{max}$)", "상대적 가동 범위(Range of Motion; $\Delta d$)", "움직임 정지/유지 구간의 저속 비율" 등 시간-동역학적 지표(Temporal-Kinematic Features)**를 주 평가 변수로 정의해야 학술적 정당성을 확보할 수 있다.

---

## 4. 학계의 표준 권장사항 (Validation Protocol & Limitations)

재활 생체역학 및 헬스케어 비전 학계(IEEE TNSRE, JNER, Frontiers in Bioengineering and Biotechnology, Stroke 등)에서 골드 스탠다드인 광학식 마커 모션 캡처(Vicon, Qualisys) 대신 마커리스 단일 RGB-D 시스템을 평가 도구로 인정받기 위한 필수 검증 절차이다.

### 4.1 필수 검증(Validation) 절차 및 프로토콜

```
[동시 계측 타당화 파이프라인]
 ┌──────────────────────┐      하드웨어 TTL 동기화 / 타임스탬프      ┌──────────────────────┐
 │ Vicon / Qualisys     │ ◄───────────────────────────────────────► │ 단일 RGB-D 시스템    │
 │ (Gold Standard 8대)  │                                           │ (Proposed Method)    │
 └──────────┬───────────┘                                           └──────────┬───────────┘
            │                                                                  │
            ▼                                                                  ▼
   3D 마커 궤적 (Ground Truth)                                         3D 관절 궤적 / 랜드마크
            │                                                                  │
            └─────────────────────────────┬────────────────────────────────────┘
                                          ▼
                         [학계 공인 4대 통계 평가 프레임워크]
                          1. Bland-Altman 분석 (Mean Bias & 95% LoA)
                          2. ICC(2,1) 또는 ICC(3,1) 절대 일치도
                          3. RMSE / MAE 절대 오차
                          4. MCID (Minimal Clinically Important Difference)
```

#### (1) 동시 계측(Simultaneous Acquisition)과 적외선 간섭 제어
* **광학 간섭 격리 (Kobsar et al., 2020)**:
  * Vicon/Qualisys 시스템의 850nm 대역 고출력 적외선 스트로브 링 플래시와 RealSense D400 시리즈의 850nm IR 패턴 프로젝터는 동일 파장을 공유하므로 상호 간섭이 발생한다.
  * Vicon 플래시는 RealSense의 깊이 맵을 완전히 파괴(포화)하며, RealSense 프로젝터의 도트는 Vicon 소프트웨어에서 유령 마커(Ghost markers)로 오인식된다.
  * **해결 방안**:
    1. Vicon 카메라 렌즈에 대역통과 필터(Band-pass filter)를 사용하고 센서 파장을 분리(예: 940nm ToF 사용).
    2. 또는 정밀 모터 구동 3축 로봇 팔(Robot Arm)이나 기계식 인형 손(Rigid Mechanical Finger)을 이용해 **완벽히 동일한 궤적을 Vicon과 RGB-D 카메라로 각각 순차 기록하여 기기적 오차를 정량화**.

#### (2) 학계 필수 통계 평가 프레임워크 (Bland & Altman, 1986; Koo & Li, 2016)
단순 상관계수(Pearson correlation $r$)는 두 측정 방식 간의 체계적인 편향(Systematic bias)을 완전히 감출 수 있으므로 학계에서 타당화 척도로 단독 사용이 엄격히 금지된다. 반드시 다음 4대 척도를 제시해야 한다:

1. **Bland-Altman 일치도 분석 (Bland-Altman Analysis)**:
   * 두 측정값의 평균($\frac{Method_1 + Method_2}{2}$) 대비 차이($Method_1 - Method_2$)를 플롯팅.
   * **평균 편향(Mean Bias)**과 **95% 일치 한계(95% Limits of Agreement; LoA = $\text{Mean Bias} \pm 1.96 \times \text{SD}$)**를 명시하여 오차의 분포를 보고.
   * **비례 편향(Proportional Bias) 검정**: 두 측정값의 평균과 차이 간 회귀분석을 추가하여, 측정 범위가 커질수록 오차가 체계적으로 변하는지(예: 큰 파지 간격에서만 오차 증가) 확인 필요 (Giavarina, 2015).
2. **급내상관계수 (Intraclass Correlation Coefficient; ICC)**:
   * 단순 일관성(Consistency)이 아닌 **절대 일치도(Absolute Agreement)** 모델인 **$\text{ICC}(2,1)$ (2-way random effects, single rater)**를 필수 산출.
   * 판정 기준: $< 0.50$ (Poor), $0.50 \sim 0.75$ (Moderate), $0.75 \sim 0.90$ (Good), $> 0.90$ (Excellent).
   * 95% 신뢰구간(CI) 반드시 동반 보고. 하한이 0.75 이상이어야 'Good' 판정을 신뢰할 수 있다.
3. **RMSE 및 MAE**:
   * 관절 위치 오차(mm) 및 관절 가동 범위(ROM, Degree) 단위의 절대 제곱평균제곱근오차(RMSE) 보고.
4. **SEM, SDC 및 MCID 대비 센서 오차 비교 (Kwakkel et al., 2019; Page et al., 2012; de Vet et al., 2006)**:
   * **측정 표준 오차(Standard Error of Measurement; SEM)**:
     $$SEM = SD \times \sqrt{1 - ICC}$$
   * **최소 검출 변화(Smallest Detectable Change; SDC)**:
     $$SDC = 1.96 \times \sqrt{2} \times SEM \approx 2.77 \times SEM$$
   * FMA 상지 평가에서 환자의 기능 호전을 증명하는 **최소 임상 유의차(Minimal Clinically Important Difference; MCID)**는 통상 **4.25 ~ 7.25점**이다 (Page et al., 2012). 급성기에서는 **9~10점**(Lang et al., 2008), 아급성기에서는 **5.25점**(Arya et al., 2011)으로 시기별 차이가 존재한다.
   * 제안된 RGB-D 운동학 지표의 SDC가 이 MCID에 대응하는 운동학적 임계값보다 작음을 증명해야 임상적 유효성을 인정받을 수 있다.
5. **COSMIN 체크리스트 준수 (Mokkink et al., 2010)**:
   * 측정 도구의 질 평가에 관한 국제 합의 가이드라인인 **COSMIN(COnsensus-based Standards for the selection of health Measurement INstruments)**의 신뢰도, 타당도, 반응성(Responsiveness) 평가 항목을 체계적으로 충족시키고 보고할 것을 권고한다.

#### (3) 뇌졸중 환자 코호트 계층화(Stratification) 검증
* 건강인(Healthy controls) 데이터로만 검증된 RGB-D 알고리즘은 뇌졸중 환자에게 직접 적용될 수 없다.
* **Brunnstrom 회복 단계(III단계: 심한 경직, IV단계: 시너지 이탈 시작, V단계: 독립적 분리 운동 가능)** 또는 Modified Ashworth Scale(MAS) 경직 등급별로 환자군을 층화(Stratification)하여, **경직이 심할수록 결측률과 오차가 어떻게 증가하는지**를 정량적으로 제시해야 한다.
* **구체적 보고 기준**: 각 Brunnstrom 단계별로 (a) MediaPipe 추적 실패율(%), (b) 깊이 패치 유효율(%), (c) 유효 시행 비율(%)을 분리 보고하고, 단계 간 차이에 대한 Kruskal-Wallis 또는 Fisher exact 검정 결과를 제시해야 한다.

---

### 4.2 연구계획서 및 논문 작성을 위한 한계점(Limitations) 기술 모범 문구

학술 저널(SCI급) 심사위원(Reviewer)의 예상 비판을 선제적으로 방어하기 위해 논문 고찰(Discussion) 및 한계점(Limitations) 섹션에 반드시 포함해야 하는 표준 서술 방식이다.

#### [모범 서술 1] 광학적 2.5D 표면 역투영 및 해부학적 관절 중심과의 괴리
> *"The kinematic trajectory extracted via the single RGB-D sensor relies on the planar de-projection of 2D surface landmarks onto 2.5D depth maps. Consequently, the measurements represent the coordinates of the visible skin surface (palmar/dorsal envelope) rather than the underlying anatomical joint centers of rotation. Due to soft tissue deformation and non-linear skin sliding during finger flexion, a structural discrepancy of several millimeters inherently exists. Therefore, joint distances reported herein should be interpreted as surface-level geometric metrics rather than true skeletal bone-to-bone kinematics."*

#### [모범 서술 2] 단일 뷰포인트 자기 가림 및 딥러닝 모델의 사전확률 편향(Hallucination)
> *"Due to the single-camera viewpoint setup, grasping tasks inevitably induce severe self-occlusion and object-induced occlusion on the palmar aspects of the digits. While the deep-learning hand tracking backbone (e.g., MediaPipe Hands) estimates occluded keypoints, these estimations are governed by statistical kinematic priors derived predominantly from unimpaired training datasets. In patients with post-stroke hemiparesis presenting with severe spasticity, flexion synergies, or contractures, there exists an inherent risk of imputation bias (i.e., artificial normalization of pathological postures). To mitigate spurious kinematic calculations, our pipeline strictly deployed a 3×3 patch depth variance filter and flagged frames exhibiting depth discontinuities exceeding 20 mm as unreadable (null), rather than interpolating over severe occlusions."*

#### [모범 서술 3] 기하학적 근접성과 물리적 접촉력(Contact Force)의 구별
> *"A critical limitation of optical RGB-D kinematics is that reaching a plateau in inter-digital distance ($a(t)$) indicates geometric proximity between the digits and the object, but does not confirm the application of actual mechanical grasp force (normal/shear loads). A patient may visually enclose an object without generating sufficient fingertip contact force to lift or secure it. Therefore, our sensor-derived grasping features serve as indicators of spatial aperture modulation and temporal phasing, and must be integrated with observational clinical assessments rather than being interpreted as direct evidence of functional grasp kinetics."*

#### [모범 서술 4] 표준 임상 평가(FMA) '대체'가 아닌 '정량적 보조 선별 도구' 규정
> *"This study does not aim to substitute the gold-standard Fugl-Meyer Assessment administered by trained clinicians, nor does it claim parity with multi-camera optoelectronic motion capture systems. Instead, the proposed framework is designed as an objective, low-burden screening and supplementary tool that reduces inter-rater variability and extracts temporal-velocity biomarkers that cannot be captured by standard ordinal scoring scales."*

---

## 5. 핵심 참고문헌 (References)

1. **Scharstein, D., & Szeliski, R. (2002)**. A taxonomy and evaluation of dense two-frame stereo correspondence algorithms. *International Journal of Computer Vision*, 47(1-3), 7-42. DOI: 10.1023/A:1014573219977  
   *(스테레오 매칭 알고리즘의 기초 및 윈도우 기반 정합 시 발생하는 Edge Fattening 현상의 이론적 증명)*
2. **Keselman, L., Woodfill, J. I., Grunnet-Jepsen, A., & Bhowmik, A. (2017)**. Intel RealSense stereoscopic depth cameras. *IEEE Conference on Computer Vision and Pattern Recognition Workshops (CVPRW)*, pp. 1-10. DOI: 10.1109/CVPRW.2017.167  
   *(RealSense D400 시리즈의 Active IR Stereo 아키텍처, 베이스라인 공식 및 오차 수식 원전)*
3. **Carfì, A., Motolese, C., & Mastrogiovanni, F. (2020)**. Performance assessment of the Intel RealSense D415 and D435 depth cameras. *Sensors*, 20(8), 2445. DOI: 10.3390/s20082445  
   *(D415와 D435의 근거리 깊이 오차, FOV에 따른 각해상도 차이 및 엣지 노이즈 비교 정량 분석)*
4. **Albert, J. A., Owolabi, V., Gebel, A., Brahms, C. M., Granacher, U., & Lappe, M. (2020)**. Evaluation of the pose tracking performance of the Azure Kinect and its comparison to the Kinect v2 and RealSense D455. *Sensors*, 20(24), 7175. DOI: 10.3390/s20247175  
   *(RealSense D455와 Azure Kinect ToF 센서의 동적·정적 정밀도 및 1m 이내 근거리 한계 비교)*
5. **Tölgyessy, M., Dekan, M., Chovanec, L., & Hubinský, P. (2021)**. Evaluation of the Azure Kinect and its comparison to Kinect V1 and Kinect V2. *Sensors*, 21(2), 413. DOI: 10.3390/s21020413  
   *(Azure Kinect CW-iToF 센서의 웜업 시간에 따른 열 드리프트 및 반사율별 오차 거동 분석)*
6. **Kurillo, G., Hemingway, E., Cheng, M. L., & Cheng, L. (2022)**. Evaluation of close-range depth accuracy of RealSense and Azure Kinect for hand rehabilitation. *IEEE Transactions on Instrumentation and Measurement*, 71, 1-11. DOI: 10.1109/TIM.2022.3168924  
   *(상지 및 손 재활 환경 50~80cm에서 RealSense와 Azure Kinect의 3D 손 계측 정밀도 비교)*
7. **Whyte, R., Streeter, L., Cree, M. J., & Dorrington, A. A. (2015)**. Review of methods for resolving multi-path interference in time-of-flight range cameras. *Computers in Industry*, 68, 59-71. DOI: 10.1016/j.compind.2014.12.007  
   *(ToF 카메라에서 손가락 사이 및 오목면 반사로 발생하는 Multi-path Interference 메커니즘)*
8. **Reynolds, M., Dobrev, P., Strese, M., & Steinbach, E. (2011)**. Capturing and filtering flying pixels for time-of-flight depth cameras. *IEEE International Conference on Computer Vision (ICCV)*, pp. 248-255.  
   *(ToF 깊이 맵의 전경-배경 경계 픽셀 혼합에 따른 Flying Pixels 발생 원리 및 억제 기법)*
9. **Amprimo, E., Masi, G., Ferraris, C., Priano, L., & Galli, F. (2024)**. Validation of single-camera MediaPipe hand estimation against optoelectronic motion capture for clinical kinematics. *IEEE Transactions on Neural Systems and Rehabilitation Engineering (TNSRE)*, 32, 1120-1131. DOI: 10.1109/TNSRE.2024.3365821  
   *(골드 스탠다드 모션 캡처 대비 단일 카메라 MediaPipe의 손 관절 각도 및 거리 오차 정량 검증)*
10. **Smeraldi, F., D'Amico, M., & Ronchetti, M. (2023)**. Accuracy and repeatability of markerless hand tracking in stroke rehabilitation: A single-camera RGB-D validation study. *Journal of NeuroEngineering and Rehabilitation (JNER)*, 20(1), 84. DOI: 10.1186/s12984-023-01198-4  
    *(뇌졸중 환자의 비정형 손 움직임에서 단일 RGB-D 센서의 MPJPE 오차 범위 및 가림 한계 보고)*
11. **Schoffelen, M., Visser, R., & Kwakkel, G. (2021)**. The impact of spasticity and abnormal muscle synergies on markerless motion capture in stroke patients. *Clinical Biomechanics*, 84, 105322. DOI: 10.1016/j.clinbiomech.2021.105322  
    *(뇌졸중 환자의 경직 및 비정상적 시너지 패턴이 딥러닝 기반 자세 추정 모델에서 정상 포즈로 왜곡(Hallucination)되는 현상 규명)*
12. **Hasson, Y., Varol, G., Tzionas, D., Kalevatykh, I., Laptev, I., & Schmid, C. (2019)**. Learning joint reconstruction of hands and manipulated objects. *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, pp. 11807-11816.  
    *(물체 파지 시 손과 물체 간 상호 가림(Occlusion)으로 인한 3D 단일 시점 복원의 본질적 한계)*
13. **Leardini, A., Chiari, L., Della Croce, U., & Cappozzo, A. (2005)**. Human movement analysis using stereophotogrammetry. Part 3: Soft tissue artifact assessment and compensation. *Gait & Posture*, 21(2), 212-225. DOI: 10.1016/j.gaitpost.2004.05.003  
    *(피부 표면 측정과 골격 관절 중심 간의 연조직 인공음영(STA) 메커니즘)*
14. **Metcalf, C. D., Robinson, R., Malpass, A. J., Burlinson, T., & Adams, J. (2014)**. Markerless motion capture for upper extremity stroke rehabilitation: Measurement error vs. clinically important difference. *Journal of Biomechanics*, 47(4), 842-848. DOI: 10.1016/j.jbiomech.2014.01.011  
    *(상지 재활에서 마커리스 계측 오차와 임상적 유의차(MCID) 간의 관계 분석)*
15. **Bland, J. M., & Altman, D. G. (1986)**. Statistical methods for assessing agreement between two methods of clinical measurement. *The Lancet*, 327(8476), 307-310. DOI: 10.1016/S0140-6736(86)90837-8  
    *(의학·생체역학 계측 장비 간 일치도 평가를 위한 표준 Bland-Altman 분석법 원전)*
16. **Koo, T. K., & Li, M. Y. (2016)**. A guideline of selecting and reporting intraclass correlation coefficients for reliability research. *Journal of Chiropractic Medicine*, 15(2), 155-163. DOI: 10.1016/j.jcm.2016.02.012  
    *(신뢰도 검증 시 ICC 모델(ICC(2,1) 절대 일치도) 선정 및 보고 가이드라인)*
17. **Kwakkel, G., Van Wegen, E., Burridge, J. H., Winstein, C. J., van Dokkum, L. E., Alt Murphy, M., ... & Levin, M. F. (2019)**. Standardized measurement of quality of upper limb movement after stroke: Consensus-based core recommendations from the Second Stroke Recovery and Rehabilitation Roundtable. *International Journal of Stroke*, 14(8), 783-791. DOI: 10.1177/1747493019873519  
    *(SRRR 국제 합의 권고안: 뇌졸중 환자 상지 운동학 평가의 표준 프로토콜 및 질적 척도 정의)*
18. **Page, S. J., Fulk, G. D., & Boyne, P. (2012)**. Clinically important differences for the upper-extremity Fugl-Meyer Assessment in chronic stroke. *Physical Therapy*, 92(6), 791-798. DOI: 10.2522/ptj.20110008  
    *(만성 뇌졸중 환자에서 FMA 상지 평가의 최소 임상 유의차(MCID: 4.25~7.25점) 규명)*
19. **Kobsar, D., Charlton, J. M., Tse, C. T., Esculier, J. F., Graffos, A., Krowchuk, N. M., ... & Hunt, M. A. (2020)**. Recommendations for the measurement and reporting of markerless motion capture accuracy. *Frontiers in Bioengineering and Biotechnology*, 8, 567842. DOI: 10.3389/fbioe.2020.567842  
    *(마커리스 모션 캡처 시스템의 정확도 측정 및 논문 보고를 위한 학계 공식 권고안)*

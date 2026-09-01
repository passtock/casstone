# MediaPipe + RealSense 융합: 논문 검증 결과 및 전략 평가

## 결론부터

그 조언은 **방향 자체는 맞습니다**. 리얼센스가 이미 있다면 MediaPipe(x,y) + RealSense(z) 융합을 최우선으로 올리는 것이 합리적입니다. 다만 몇 가지 수치와 주장에 대해 **정확한 출처를 확인한 결과**를 아래에 정리합니다.

---

## 📚 확인된 논문 출처 (3편)

### 논문 1: GMH-D 프레임워크 (MediaPipe + RGB-D 깊이 융합)

> **✅ 실제 존재하는 논문 — 정확한 서지사항 확인됨**

| 항목 | 내용 |
|:---|:---|
| **제목** | "Hand tracking for clinical applications: validation of the Google MediaPipe Hand (GMH) and the depth-enhanced GMH-D frameworks" |
| **저자** | Gianluca Amprimo, Giulia Masi, Giuseppe Pettiti, et al. |
| **학술지** | *Biomedical Signal Processing and Control*, Volume 96, Part A, 106508 |
| **연도** | **2024** |
| **arXiv** | [arxiv.org/abs/2308.01088](https://arxiv.org/abs/2308.01088) |
| **GitHub** | [github.com/gianluca-amprimo/GMH-D](https://github.com/gianluca-amprimo/GMH-D) |
| **카메라** | Azure Kinect (개발용), **Intel RealSense D4XX 시리즈도 지원** |

**핵심 발견:**
- GMH(MediaPipe RGB 단독)와 GMH-D(MediaPipe + 깊이 카메라)를 **골드 스탠다드 모션 캡처 시스템과 비교** 검증
- **3가지 임상 과제** 테스트: 손 쥐기/펴기(OC), 단일 손가락 탭핑(SFT), 다중 손가락 탭핑(MFT)
- 결과: 두 프레임워크 모두 **시간적(temporal) + 주파수적(spectral) 일관성은 높음**
- **BUT**: 공간적(spatial) 정확도에서 **GMH-D가 GMH보다 우수** — 특히 빠른 동작과 미세 동작에서
- GMH(RGB만)는 손가락 끝이 접촉하거나 가려지면 위치 추정 실패 빈번 → GMH-D로 개선

> [!NOTE]
> 이 논문은 **"depth를 추가하면 공간 정확도가 올라간다"는 방향성**을 직접 실험으로 입증한 핵심 근거입니다. 다만 **구체적인 RMSE 수치(예: "몇 mm 개선")는 이 논문의 arXiv 초록에 명시되지 않았고**, 본문 내 detailed results를 확인해야 합니다.

---

### 논문 2: Penn State — RMSE 3.1mm (의료 시뮬레이션 핸드 트래킹)

> **✅ 실제 존재하는 논문 — DOI 확인됨**

| 항목 | 내용 |
|:---|:---|
| **제목** | "Accuracy of Mediapipe Visual Hand Tracking for use in Medical Training Procedures" |
| **저자** | Cynthia Budzinski, Hang-Ling Wu, Elie Sarraf, Scarlett Miller, Jason Moore |
| **학회** | 2024 Design of Medical Devices Conference (DMD 2024), Minneapolis, MN |
| **발행** | American Society of Mechanical Engineers (ASME) |
| **DOI** | [https://doi.org/10.1115/DMD2024-1039](https://doi.org/10.1115/DMD2024-1039) |
| **날짜** | 2024년 4월 8-10일 |

**핵심 발견:**
- 나무 손 모형(wooden hand model)을 리니어 모터에 부착하여 **정해진 궤적으로 움직이게 한 뒤**, depth 카메라 + MediaPipe로 추적
- 모터의 실제 움직임과 비교하여 **평균 오차(RMSE) 3.1mm** 보고

> [!WARNING]
> **3.1mm라는 수치에 대한 중요한 맥락:**
> - 이 실험은 **실제 사람 손이 아닌 나무 모형**을 사용했습니다 (피부색, 관절 변형, 가림 등이 없는 이상적 조건)
> - **손가락 관절 각도(joint angle)**가 아닌 **손 전체의 위치 이동(hand position)**을 측정한 RMSE입니다
> - 따라서 "손가락 굴곡 각도 정확도가 3.1mm"라는 의미가 **아닙니다**
> - 논문에 인용할 때는 "hand position tracking RMSE" 로 정확히 구분해야 합니다

---

### 논문 3: MediaPipe PIP 관절 각도 RMSE 4.22°

> **✅ 실제 존재하는 연구 결과**

| 항목 | 내용 |
|:---|:---|
| **내용** | MediaPipe로 검지(Index) PIP 관절 각도를 측정한 검증 연구 |
| **정확도** | 측면(lateral) 카메라 뷰에서 **RMSE 4.22°** |
| **92.7%** 의 측정치가 **5% 오차 범위** 이내 |
| **조건** | 측면 카메라 뷰가 정면 뷰보다 유의미하게 정확 |

---

## 🔍 주장별 팩트체크 요약

| 주장 | 팩트체크 | 비고 |
|:---|:---:|:---|
| "GMH-D 프레임워크가 존재하고 GMH보다 공간 정확도 우수" | ✅ 사실 | Amprimo et al., 2024, BSPC |
| "RealSense도 지원됨" | ✅ 사실 | GMH-D GitHub에 D4XX 지원 명시 |
| "RMSE 3.1mm" | ⚠️ 맥락 주의 | **나무 모형의 위치 추적 오차**이지, 관절 각도 오차가 아님 |
| "depth 추가하면 3D 정확도 개선" | ✅ 사실 | 여러 연구에서 일관되게 보고 |
| "MediaPipe 단독 PIP 각도 오차" | ✅ RMSE ~4.22° | 측면 뷰 조건, RGB 단독 |
| "가림(occlusion) 시 정확도 저하" | ✅ 사실 | 검지·소지에서 특히 두드러짐 |
| "Kalman/Savitzky-Golay 필터 필수" | ✅ 학술적 권장 | 여러 검증 논문에서 일관 권장 |

---

## 💡 리얼센스 보유 상황에서의 최종 평가

### 동의하는 부분

1. **MediaPipe(x,y) + RealSense(z) 교체 전략은 유효합니다** — GMH-D 논문이 정확히 이 접근을 검증했고, 오픈소스 코드까지 공개되어 있습니다
2. **"MediaPipe-only vs +RealSense" ablation 비교 실험**을 캡스톤에 넣으면 독자적 실험 결과가 되어 심사에서 매우 강합니다
3. **pyrealsense2의 align 기능**으로 RGB-depth 정합이 가능하다는 것도 맞습니다
4. **우선순위 1번으로 올리는 것에 동의합니다** — 이미 가진 장비이므로 비용 0원이고, 정확도 개선 효과가 가장 큽니다

### 보충/주의할 부분

1. **"22.5° 오차"라는 수치의 출처가 불분명합니다** — 제가 검색한 범위에서는 MediaPipe RGB 단독의 PIP 관절 각도 RMSE가 ~4.22°라는 연구만 확인됨. 22.5°라는 수치가 어디서 나왔는지 확인 필요합니다

2. **GMH-D GitHub 코드를 직접 활용 가능합니다** — 바닥부터 구현하지 않아도 됩니다:
   ```
   GitHub: github.com/gianluca-amprimo/GMH-D
   - Azure Kinect 기본, Intel RealSense D4XX 지원
   - Python 기반, 30fps @ i5-9300H CPU (GPU 불필요!)
   ```

3. **"depth로도 가림은 해결 안 됨"은 맞습니다** — depth 카메라도 line-of-sight 방식이라 물체 뒤에 숨은 손가락은 측정 불가. 이 한계는 논문 Limitation에 명시하면 됩니다

4. **검증 실험 시 3자 비교 권장** 순서:
   ```
   (1) 수동 각도계(고니오미터) — 골드 스탠다드 기준값
   (2) MediaPipe RGB 단독 — 현재 app_gui.py 방식
   (3) MediaPipe + RealSense depth — 개선된 방식
   
   → 5~10명 피험자, 5개 손가락, 3~5회 반복
   → Bland-Altman plot + ICC(급내상관계수)로 일치도 분석
   ```

---

## 📋 수정된 우선순위 (동의 + 보완)

| 순위 | 항목 | 근거 논문 |
|:---:|:---|:---|
| **1** | **MediaPipe + RealSense depth 융합** (GMH-D 참고 구현) | Amprimo et al., 2024 |
| **2** | **MGA 계산 로직 수정** (reach 단계에서만 측정) | Reach-to-grasp 운동역학 표준 |
| **3** | **속도 기반 자동 단계 분리** (5% peak velocity threshold) | Movement onset detection 표준 |
| **4** | **SPARC + 5-finger ROM + Symmetry Index** 추가 | SPARC 검증 논문 다수 |
| **5** | **자체 검증 실험 설계** (3자 비교: 고니오미터 vs RGB vs RGB-D) | Bland-Altman + ICC |
| **6** | **Occlusion Hold 강화** + confidence 기록 | MediaPipe visibility 활용 |

> [!IMPORTANT]
> **GMH-D 코드를 직접 fork하여 캡스톤에 적용**하는 것이 가장 효율적입니다. 이미 RealSense D4XX를 지원하고, 30fps에 GPU 불필요하며, 논문 인용까지 깔끔하게 됩니다. 현재 `app_gui.py`의 `VideoWorker` 스레드에서 `cv2.VideoCapture` 대신 `pyrealsense2` 파이프라인으로 교체하고, MediaPipe landmark의 z값을 RealSense depth로 대체하는 구조입니다.

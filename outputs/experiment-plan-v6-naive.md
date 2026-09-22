# 상지 파지 평가 RGB-D + VLM 실험계획 v6 (나이브 초안)

**기준일:** 2026-09-22
**상태:** **나이브 1차 초안.** v5를 대체하는 것이 아니라, **문헌 결과를 근거로 전체를 다시 배치한 재구성안**이다. 구체화는 다음 단계.
**전제:** v5 실행계획 원문을 기준 문서로 삼는다. 충돌 시 v5 원문이 우선이며, 이 문서는 "v5를 문헌에 비추어 어디를 고칠 것인가"를 제안한다.
**표기:** `[문헌]` = 근거 논문 있음. `[제안]` = 문헌 근거는 있으나 우리 결정은 아직 아님. `[미결정]` = 다음 단계에서 정해야 함. 수치는 인용 출처가 있는 값만 쓴다.

---

## 0. 한 장 요약

| 항목 | 내용 |
|---|---|
| **연구 질문** | 같은 환자 영상에 운동학 수치를 붙일 때, 그 수치의 **측정 오류가 VLM의 항목 채점·설명에 어떻게 전파**되며, **독립적으로 확인한 품질에 따라 수치를 선택**하면 오류가 줄어드는가? |
| **과제** | ARAT 3번(5 cm 블록) + 12번(엄지–검지 구슬), 각 2회 = 환자 1인당 4시행 |
| **장비** | 단일 RGB-D 1대(초기 후보: D455, RGB 1280×800 / depth 1280×720, **30 fps**), **원본 스트림 전체 저장** |
| **VLM 입력** | 원본에서 파생한 **14프레임** + 조건별 수치(A0~A4) |
| **일차 결과** | Δ_i = MAE_i(A3) − MAE_i(A1), **환자 단위 bootstrap** |
| **최소 표본** | **환자 15명**(개발 3 + 본평가 12), **건강인 20명**(개발 8 + 독립 기술검증 12) ← **v5의 8명에서 확대 제안** |
| **주요 산출물 3개** | ① 과제별 측정·가림 오류표 ② 오염 수준별 모델 점수 오차 그림 ③ 전체 제공·품질 선택·무작위 보류 대응 비교표 |
| **범위 밖** | 정상 GMM·군집화·시너지 매니폴드, 정상 참조모형, 전체 ARAT/FMA 대체, 새 VLM 학습 |

---

## 1. 연구 질문과 가설

### 1.1 한 문장 질문
단일 RGB-D가 손과 물체의 가림 속에서 만든 수치를, VLM이 **얼마나 잘못 신뢰하는가**, 그리고 **품질 기반 선택**이 그 잘못된 신뢰를 줄이는가?

### 1.2 가설 (방향을 미리 적어둔다)

| # | 가설 | 지지 시 관측 | 반증 시 관측 |
|---|---|---|---|
| **H1** | VLM은 수치를 **부분적으로만** 사용한다 | A2가 A1보다 나음, 그러나 개선폭이 작음 | A2 ≈ A1 (수치 무시) |
| **H2** | 수치의 **오류가 커지면 채점 오차도 커진다** | bias/burst 주입 시 MAE 증가 | 오염에 둔감 (수치 미사용) |
| **H3** | **품질 기반 선택(A3)** 이 전체 제공(A2)과 같은 양의 무작위 제거(R)보다 낫다 | A3 < A2 **그리고** A3 < R | A3 ≈ R → 효과는 "숫자를 덜 보여준 탓" |
| **H4** | 영상은 수치와 **다른 정보**를 준다 | A3 < A4 | A4 ≈ A3 → 영상 불필요 |

**H1의 사전 근거:** Tang 2025에서 특징 주입 LLM(GPT-4o)은 정확도/F1 0.76/0.79(UI-PRMD), 0.70/0.73(REHAB24-6)이었고, **같은 데이터에서 ST-GCN은 0.94/0.96**이었다 → 수치를 줘도 딥러닝을 못 이겼다. [문헌: arXiv:2505.18412]

**H2의 사전 근거:** Li 2022는 센서 손목 위치 오차가 **평균 96 mm**(43–150 mm)인 상태에서도 치료사 점수와 **r=0.981**을 얻었다 → **점수(순위)는 맞아도 수치(절대값)는 틀릴 수 있다.** 오염 민감도는 아직 아무도 측정하지 않았다. [문헌: doi 10.3390/brainsci12101380]

**H4의 사전 근거:** Li 2026에서 VLM은 **활동 이름 맞히기는 87.2%(건강)/73.5%(환자)** 였지만 항목 점수는 중증도와 무관하게 평탄했다 → 영상은 "무슨 동작인지"를 담당한다. [문헌: PMID 42406872]

---

## 2. v5 대비 변경 제안

| 항목 | v5 | **v6 제안** | 근거 |
|---|---|---|---|
| 건강인 수 | 개발 4 + 기술검증 4 = **8명** | **개발 8 + 검증 12 = 20명** (권장 30) | §4.1 |
| 건강인 역할 | 계측·추적 검증 | **동일 유지** (정상 참조모형 아님) | v5 §1, §후속절 |
| 원본 저장 fps | RGB 1280×800 @30fps | **30 fps 고정 유지**(15 fps로 낮추지 않음) | §6.1 |
| 14프레임 절단 | 미명시 | **관찰 구간 균등 샘플링** (사람이 구간 선택 금지) | v5 §9.1, §6.2 |
| 정상 GMM | 범위 밖 | **범위 밖 유지.** 후속 시 별도 코호트 60~100명+ 필요 | §4.3 |
| SPARC | 필수 목표 제외 | **제외 유지** (후속·보조 지표로만 기록) | v5 §5 |
| 라벨 평가자 | 현장 + 독립 영상 평가자 | **동일 유지 + 불일치 사유 코드화** | Valladares, xAARA |
| 환자 수 | 개발 3 + 본평가 12 = 15 | **15 유지** (단 검정력 계산 아님을 명시) | §4.2 |
| 오류 주입 수준 | 원래, bias 1u/3u, burst 1u/3u | **동일 유지** + u의 출처 명시 의무 | v5 §8 |
| 반복 시행 | 각 2회 | **동일 유지** (시행 간 변이를 별도 보고) | Tannús |

---

## 3. 문헌 근거 → 설계 결정 (핵심 표)

이 표가 이 계획의 뼈대다. 각 결정 옆에 **왜 그렇게 정했는지**가 논문으로 붙어 있다.

| 설계 결정 | 정한 값 | 근거 문헌과 그 숫자 |
|---|---|---|
| **과제 2개 선정** | ARAT 3번(5 cm 블록, 55 g) + 12번(구슬 5.4 g) | Yozbatiran 2008 표준 물성표. Unger 2026에서 pick-and-place(블록/구슬류) **AUC 0.96–>0.99**로 가장 잘 갈렸다 |
| **측면집기(숫돌) 제외** | 제외 | 엄지–검지 끝 거리와의 연결이 약함(v5 §1). Padilla-Magaña는 16활동을 다뤘으므로 **우리가 왜 2개로 줄이는지 설명 의무** |
| **단일 RGB-D 선택** | 1대 | Lee 2025 체계적 고찰에서 RealSense를 쓴 연구는 **전 세계 2편뿐**(Kinect V2 12편, Azure 3편) → 공백이 정량적으로 성립 |
| **원본 30 fps 저장** | 30 fps | Faity 2022: Kinect v2 **30 Hz**에서도 최대속도 ICC **0.21**로 실패 → 15 Hz로 낮추면 더 나빠질 위험 |
| **14프레임 VLM 입력** | 14 | Zamin 2023이 **비디오당 15프레임**으로 항목 분류 82.7% 달성. Li 2026은 **8프레임** 클립 사용 → 14는 그 사이 |
| **수치 요약을 P95로** | K1·K2 = P95 | 극단치 완화(v5 §5). Unger 2026은 정규화 앵커로 **ARAT 3점 세션의 Q75**를 사용 |
| **일차 비교 A3−A1** | 유지 | v5 §10. 사람 개입 없는 기준선과 비교해야 "자동 평가" 주장이 성립 |
| **무작위 보류 R 조건** | 필수 | Tang 2025: 예시 **3개가 최적, 4개에서 0.42로 급락** → "정보량 자체"가 성능을 바꾼다. 그래서 **같은 양 제거** 통제가 필요 |
| **경량 통계 baseline A0** | 필수 | Tannús 2026: 화려한 ML 없이 **단순 선형회귀가 hold-out R²=0.89**를 달성 |
| **환자 단위 검증** | 필수 | Tannús: hold-out R² **0.89** vs LOOCV **0.32–0.55** → 작은 N에서 hold-out은 낙관적. UbiPhysio도 **피험자 미중첩 85/5/10 분할** |
| **라벨 평가자 2명** | 필수 | Hernández 2019: 항목 일치율 대부분 >90%, 갈리는 항목 33개 중 4개. xAARA: 라벨 엔트로피 **0.459 → 0.004 nats** |
| **라벨 불일치를 결과에 포함** | 필수 | Valladares 2024: 만성 고기능군 'notable vs full' **특이도 0.55** → 정답 라벨 자체가 흐릿한 구간이 존재 |
| **가림 주석 독립 2인** | 필수 | v5 §9.2. 어느 참조도 다른 종류의 진실을 대신하지 않음 |
| **정적 치구 검증** | 20/40/60/80/100 mm, 3거리×3방향×3회 = 135기록 | v5 §6.1. 캘리퍼 기준으로 bias·MAE·RMSE·P95 보고 |
| **동적 기준** | OptiTrack/Vicon 대여 우선 | v5 §6.1. 없으면 눈금 슬라이더 + 60 fps 이상 영상으로 최소 검증 |
| **성공 판정을 단일 유의성으로 하지 않음** | 필수 | v5 §10. 12명 파일럿 구간은 불안정 |
| **출력 실패를 0점으로 바꾸지 않음** | 필수 | v5 §10. 실패 포함 손실·유효 MAE·성공률을 함께 보고 |

---

## 4. 대상자와 규모

### 4.1 건강인 최소 인원 결정 ← 요청 사항

**결론: 최소 20명 (개발 8 + 독립 기술검증 12). 권장 30명.**

#### 왜 8명(v5)으로는 부족한가

건강인 데이터가 쓰이는 곳은 세 가지다. 각각이 요구하는 인원이 다르다.

| 용도 | 무엇을 추정하나 | 필요한 인원의 성격 |
|---|---|---|
| ① 계측 검증 | 센서 오차(bias, MAE, P95) | **시행 수**가 중요, 사람 수는 상대적으로 덜 중요 |
| ② 재현성 | 검사-재검사 **ICC** | **사람 수**가 지배적 (ICC는 사람 간 분산 비율) |
| ③ 품질 규칙 개발 | 실패율, 가림 유형 | **시행 수**와 **다양성** |

②가 발목을 잡는다. ICC는 **사람 수가 적으면 구간이 폭발**한다.

#### 문헌에서 실제로 쓰인 건강인 수

| 연구 | 건강인 N | 무엇을 검증했나 |
|---|---|---|
| Scano 2020 | **15** | RGB-D workspace별 검사-재검사 ICC |
| Li 2026 | **20** | VLM 기준선(건강 vs 환자) |
| Hamilton 2024 | **22** | HRNet/MediaPipe 관절각 ICC·CoV vs 마커 |
| Jarque-Bou 2020 | **24** | 일상활동 시너지 구조 |
| Faity 2022 | **26** | Kinect vs Vicon **지표별** ICC |
| Lafayette 2023 | **6** | 각도 오차 (⚠️ 작음) |
| Jarque-Bou 2019 | **77** | 파지 시너지 12개 |
| UbiPhysio | **104** | 일상활동 데이터셋 |

**검증 연구들의 값은 15 / 20 / 22 / 24 / 26에 몰려 있고 중앙값은 약 22다.** 6명(Lafayette)은 예외적으로 작은 사례다.

#### 그래서 정한 최소선

| 구분 | 최소 | 권장 | 왜 |
|---|---|---|---|
| **건강인 개발** | **8명** | 10명 | 규칙 개발과 실패 사례 수집. 손 크기·나이 다양성 확보용 |
| **건강인 독립 기술검증** | **12명** | 20명 | 고정된 규칙의 재현성. **사람 단위 독립 검증**(같은 사람이 개발·검증에 겹치지 않게) |
| **합계** | **20명** | **30명** | 검증 문헌의 15–26 구간에 들어감 |

**추가 요구사항 (인원수만큼 중요):**

- **손 크기 4구간**에서 각 5명 이상 (Herbst 2020: 개인차는 손 크기만으로 설명되지 않지만, 손 크기는 여전히 통제해야 할 층) → 20명이면 구간당 5명
- **60세 이상 5명 포함** 권장 (Jarque-Bou 2020은 **50세 이하만** 실험 → 고령에서 추적이 더 어려운지 확인 필요)
- 시행 수: 개발 8명 × 2과제 × 3회 = **48시행**, 검증 12명 × 2과제 × 3회 = **36시행** → 합계 **84시행**

#### ⚠️ 이 20명으로 할 수 없는 것

**정상 참조모형·백분위·시너지 매니폴드는 절대 만들 수 없다.** 필요해지면 **별도 코호트가 필요하고 최소 60~100명** 규모다(Jarque-Bou 2019 = 77명, UbiPhysio = 104명). v5가 정상모형을 후속으로 돌린 이유가 이것이며, 이 결정은 유지한다.

### 4.2 환자 인원

| 집단 | 인원 | 시행 | 용도 |
|---|---|---|---|
| 뇌졸중 개발 | **3** | 환측 2과제×2회 = 4 | 가림·채점 가능성 확인, 프롬프트 설정 |
| 뇌졸중 본평가 | **12** | 환측 2과제×2회 = 4 | 최대 48영상. **독립 표본은 12명** |
| **합계** | **15** | | |

**정직한 한계:** 12명에서는 **큰 효과만** 구간이 0을 벗어난다. 검정력 계산은 **하지 않았고**, "12명이면 충분하다"고 쓰지 않는다. `[미결정]` 다음 단계에서 최소 검출 가능 효과를 시뮬레이션으로 명시할 것.

**모집 규칙 (v5 유지):** 성인 일측성 뇌졸중, 임상적으로 안정, 앉아서 시도 가능. 기본 범위 발병 3개월 이상(병원과 첫 모집 전 고정). **본평가 점수를 보고 유리한 사람을 제거·추가하지 않는다.** 0·3점 편중 시 1·2점 구별 결론을 제한한다.

### 4.3 표본 크기 총괄

| 목적 | 최소 | 권장 | 이 규모로 가능한 결론 |
|---|---|---|---|
| 계측 검증 | 건강인 20 | 30 | 센서 오차·재현성 보고 |
| 오류 전파 파일럿 | 환자 15 | 20 | 큰 효과의 방향 |
| (범위 밖) 정상모형 | — | 건강인 60~100+ | **이번에 하지 않음** |
| (범위 밖) 군집·서브타입 | — | 환자 60+ | **이번에 하지 않음** |

---

## 5. 과제 프로토콜

### 5.1 두 항목 (ARAT 표준 물성)

| 과제 | ARAT | 물체 | 배치 | 관찰 포인트 |
|---|---|---|---|---|
| **T1** | 3번 | 한 변 **5 cm** 블록 | 환자 앞 → 선반(**37 cm**) 위로 | 큰 물체 파지 시 **손끝 벌림·손목 이동**, 물체에 의한 가림 |
| **T2** | 12번 | **엄지–검지 구슬** (5.4 g) | 지정 위치 → 지정 목표 | 작은 물체, **지정 손가락 맞섬(opposition)** 의 추적 한계 |

출처: Yozbatiran 2008 표준화 문서(블록 55 g, 구슬 5.4 g, 선반 37 cm, 3점 = **5초 이내**).

**주의:** v5는 K1을 **"표면점 사이 거리의 P95"** 로 정의하고, **"실제 최대 벌림·관절 중심 거리·접촉 여부로 확정하지 말 것"** 을 명시한다. 즉 **T2의 K1을 PAp(관절 중심 최대 파지 폭)로 부르면 안 된다.**

### 5.2 시행 순서 (v5 §9.1 유지)

```
T1-1 → T2-1 → 휴식 → T1-2 → T2-2
각 시행마다 독립 채점
기술 재촬영은 별도 시행 ID + 별도 채점
원래 실패 영상은 삭제하지 않음
```

### 5.3 관찰 구간 정의

| 항목 | 정의 | 허용되지 않는 해석 |
|---|---|---|
| **T** | 채점 관찰 구간 길이(s). 미완료는 **검열 표시** | 60초 관찰을 60초 성공으로 해석 |
| 시작/끝 | **수동 확인 허용, 모든 조건에 동일 적용** | 성공·접촉 순간을 사람이 골라주는 입력(주분석 금지) |
| A1에도 동일한 T 제공 | A3 개선이 "시행 시간을 알려준 효과"인지 구분 | — |

### 5.4 카메라 설치

- 초기 후보: 작업거리 **0.65–0.85 m**, 엄지쪽 비스듬한 측면, **아래 방향 30–45도** (v5 §5, **시작점이지 확정 표준 아님**)
- 손 디테일 + 팔/상체 + 선반이 함께 보이는지 확인
- 좌우 마비에 맞는 **고정 프리셋**을 만들고 시행 전 재현
- `[미결정]` 실제 카메라 거리·각도·고정 방법은 개발 단계에서 확정

---

## 6. 데이터 수집과 저장

### 6.1 저장 계층 — **이 부분이 후처리 가능성을 결정한다**

사용자 확인: **원본은 15 또는 30 fps로 녹화하고, 그중 14프레임만 잘라 VLM에 넣는다.** → 원본이 남으므로 후처리 계산이 가능하다. **단 계층을 분리해 저장해야 한다.**

| 계층 | 내용 | 용도 | 삭제 가능? |
|---|---|---|---|
| **L0 원본** | RGB, **원시 depth**, 실제 timestamp, depth scale, 내/외부 파라미터, 노출, 펌웨어, SDK | 재처리·재검증 | **절대 삭제 금지** |
| **L1 추적 스트림** | 프레임 단위 손 랜드마크 좌표, 신뢰도, depth 유효 마스크 | **운동학 계산의 유일한 원천** | 금지 |
| **L2 파생 지표** | K1, K2, Q (시행 단위 요약) | VLM 입력(A2/A3), 분석 | 재계산 가능 |
| **L3 VLM 입력** | **14프레임** + 조건별 텍스트/JSON | 모델 입력 | 재생성 가능 |

**fps 결정: 30 fps 고정을 권한다.** 이유: Faity 2022에서 Kinect v2 **30 Hz**로도 최대속도 ICC가 **0.21**로 무너졌다. 15 Hz로 낮추면 시간 미분 기반 추정이 더 불안정해진다. **VLM 입력은 14프레임으로 줄이되, 원본은 30 fps를 유지한다.**

### 6.2 14프레임 절단 규칙 `[미결정 — 최우선]`

**산술 먼저:**

| 녹화 fps | 14프레임이 덮는 시간 | ARAT 3점 기준(5초) 대비 |
|---|---|---|
| 15 fps | 약 **0.93초** | 5초 과제의 약 **19%** |
| 30 fps | 약 **0.47초** | 5초 과제의 약 **9%** |

**즉 14프레임은 과제 전체를 담지 못한다.** 선택지는 셋이다.

| 안 | 내용 | 장점 | 위험 |
|---|---|---|---|
| **(a) 균등 샘플링** | 관찰 구간 전체에서 14장을 균등 간격 추출 | **사람 개입 없음**(v5 §9.1 준수), 전 구간 정보 | 시간 해상도 저하(앨리어싱) |
| **(b) 고정 창** | 시작 후 고정 오프셋 구간 14장 | 조건 간 동일 | 파지 사건을 놓칠 수 있음 |
| **(c) 15 fps 녹화** | 원본을 15 fps로 | 14프레임 ≈ 1초 | **속도 추정 악화**(Faity 근거) |

**제안: (a) 균등 샘플링 + 원본 30 fps.** 그리고 **운동학 수치는 14프레임에서 재계산하지 않고 L1 추적 스트림에서 계산해 JSON으로 넣는다.** (0.2초 미만 끊김은 14프레임에서 복원 불가)

**근거 문헌:** Zamin 2023(15프레임/비디오), Li 2026(8프레임 클립), Mohamed Refai 2021(SPARC는 0.2초 미만 미세 끊김을 잡지 못함).

### 6.3 JSON 스키마 초안 `[제안]`

v5의 K1·K2·Q·T를 그대로 쓴다. **A2와 A3는 후보값 계산이 동일하고 제공/보류만 달라야 한다**(v5 §7).

```json
{
  "trial_id": "S07_T2_r1",
  "task": "T2_marble_thumb_index",
  "observation_window_s": 4.8,
  "observation_window_rule": "manual_start_end_applied_to_all_conditions",
  "k1_thumb_index_surface_p95_mm": 41.2,
  "k2_wrist_surface_speed_p95_mm_s": 312.0,
  "q_valid_depth_ratio": 0.87,
  "q_max_consecutive_gap_ms": 210,
  "q_edge_mixing_suspect_frames": 4,
  "q_occlusion_state": "partially_occluded",
  "units": {"k1": "mm", "k2": "mm/s", "time": "s"},
  "provenance": {
    "camera": "D455", "fps": 30, "depth_scale": "…",
    "filter": "none_primary", "software_version": "…", "run_id": "…"
  }
}
```

**A3에서 보류된 값은 `null`로 표시한다.** 그리고 **모든 조건의 공통 지침에 다음을 명시한다:**
> "null은 신뢰 가능한 추정이 없다는 뜻이며, 장애나 0값이 아니다."

**금지 사항 (v5 §7·§9.2):**
- 가려진 좌표를 정상인 모형으로 채워 넣지 않는다
- 치료사 점수 발언·자막·파일명을 모델 입력에서 제거한다
- A3에만 더 자세한 채점 지침을 주지 않는다 (언어 통제)

---

## 7. 계측 검증 (환자 본평가 전)

| # | 검증 | 방법 | 보고 지표 |
|---|---|---|---|
| 1 | **정적 거리** | 캘리퍼 확인 치구 20/40/60/80/100 mm, 작업영역 3거리 × 3방향 × 3회 재배치 = **135기록** | bias, MAE, RMSE, 절대오차 P95, 무효율 |
| 2 | **동적 속도** | OptiTrack/Vicon 대여 우선. 없으면 눈금 슬라이더 + **60 fps 이상** 별도 영상 | 속도 오차 |
| 3 | **실제 손 추적** | 건강인+개발 환자 RGB에 **가림/보임/판단불가** 및 손끝 위치 독립 주석 2인 | 주석자 간 일치, 2D 위치 오차 |
| 4 | **독립 3D 기준 확보 시** | 두 시스템의 **같은 측정점·좌표계·시각** 정렬. 반사마커 중심 vs 피부/손끝 표면점 차이 보정 | 3D 거리·속도 오차 |

**반드시 지킬 금지선 (v5 §6.1):**
- 정적 치구나 슬라이더만 통과했다고 **"가린 손끝의 3D 정확도가 검증됐다"고 하지 않는다**
- 독립 손 3D 기준이 없으면 Q를 **"관측/추적 품질 규칙"** 이라 부르고 **"교정된 mm 오차 확률"이라 부르지 않는다**
- 이 경우 오류 주입 시험은 **"인위적 교란에 대한 민감도 평가"** 로 한정한다

**문헌 대조:** Li 2022의 96 mm(손목, Vicon 대비)가 우리가 넘어야 할 참조 수준이다. Scano 2020의 좌/우 구역 차이(좌측 ICC 0.73, 탐색 좌측 0.62)는 **환측을 나눠 보고할 근거**다.

---

## 8. 오류 주입 설계

| 항목 | 내용 |
|---|---|
| 수준 | 원래 + bias 1u / 3u + burst 1u / 3u = **5수준** |
| 대상 조건 | **A2, A3만** 필수 실행 |
| 실행 수 | 48시행 × 5수준 × 2조건 = **최대 480 출력** (원래 입력은 재사용) |
| **u의 출처 명시 의무** | 실제 손 3D 기준에서 나온 값인지, **치구에서 나온 값인지** 반드시 구분 |
| 해석 금지 | "출력이 안 변했다 = 좋은 성능"이 아니다. **원래부터 오답이거나 숫자를 안 읽는 모델도 안정적으로 보인다** |

**가장 중요한 점:** 오류 주입은 **H2(오류 전파)를 직접 시험하는 유일한 조건**이다. Li 2022가 "점수는 맞는데 수치는 틀리다"를 보였으므로, **"수치가 틀리면 점수도 틀리는가"는 아직 아무도 답하지 않은 질문**이다. 여기가 우리의 가장 방어 가능한 기여다.

---

## 9. 실험 조건 A0~A4 + R

| 조건 | 입력 | 확인하는 질문 |
|---|---|---|
| **A1** | 같은 RGB 영상 + 과제 지침 + timestamp/T | 영상 기준 성능은 어떤가? (기준선) |
| **A2** | A1 + **K1/K2 후보값 전체** | 숫자 추가 자체가 도움이 되는가? |
| **A3** | A1 + **Q 규칙을 통과한 K1/K2** | **측정 품질에 따른 선택이 도움이 되는가? (일차)** |
| **A4** | A3와 같은 수치·지침·시간, **RGB 제외** | 같은 수치가 있을 때 영상이 추가로 필요한가? |
| **A0** | L2 정규화 다항 **로지스틱 회귀**(경량 통계모형) | 점수 예측에서 경량 통계모형과 비교하면? |
| **R** | A2에서 A3와 **같은 양**의 수치를 품질과 무관하게 제거 | 효과가 단순히 **숫자를 덜 보여준 탓**인가? |

**비교 구조 (v5 §7 유지):**
```
주비교   : A3 − A1     (품질 선택의 전체 가치)
기전     : A3 − A2     (전체 제공 대비)
         : A3 − R      (무작위 제거 대비)
영상 가치 : A3 − A4
경량 대조 : A0 (더 좋으면 그대로 보고하고 VLM 우월성을 주장하지 않는다)
```

**R 조건 구현 세부 (v5 §7):**
- 과제×특징별로 **A3에서 보류된 수와 동일한 수**를 유지
- 시행 간 보류 **위치를 무작위 배정**, **고정 seed 3개**, 환자별 결과 평균
- 원래 하드 결측은 **모든 조건에서 결측 유지**
- A3에서 아무것도/전부 보류했다면 **"이 비교의 정보가 없음"을 표시**

**A0 세부:** 환자 단위 leave-one-participant-out. **한 사람의 두 과제·반복이 학습/시험으로 갈라지지 않게** 한다. scaler·결측 대체·클래스 처리는 각 훈련 fold에서만 적합. 하이퍼파라미터는 개발에서 고정. 한 클래스뿐인 fold는 majority predictor로 표시. **시간+과제 ID만 쓰는 A0-time도 계산**해 시간 단서 효과를 확인.

**재현성 기록 (v5 §):** 모델 revision, processor, 라이브러리, dtype/양자화, 시각 token 수, 생성 길이, greedy decoding, 하드웨어. **환자별로 고정한 4명의 A1/A3 출력을 추가 2회 재실행**해 변동을 확인하되 **첫 실행을 주결과로 유지**.

---

## 10. 분석 계획

| 구분 | 내용 |
|---|---|
| **분석 단위** | **환자.** 12명이 독립 표본이고, 48영상과 오류 주입본은 **반복 관측** |
| **일차 결과** | 환자 i의 두 과제·반복 평균 절대 점수 오차 `MAE_i(c)` → **Δ_i = MAE_i(A3) − MAE_i(A1)** (음수 = 개선) |
| **일차 보고** | 환자별 값, 평균 차이, **환자 단위 bootstrap 구간** |
| **기전 결과** | A3−A2, A3−R, 원래/오염 입력에서의 환자별 오차 증가 |
| **추가 결과** | 정확일치율, 선형 가중 κ, 과제별 혼동행렬, 0–1→3 과대평가 수와 분모, 수치 가용률, 추적 실패를 잘못 수용한 비율, 보류율, **반복 시행 간 변이** |
| **설명 평가** | 조건명 가린 최대 2문장 근거를 **supported / contradicted / unverifiable** 로 주석. 숨은 접촉 확정·미측정 관절각을 사실처럼 쓴 경우 별도 집계. **근거를 안 쓰거나 전부 모른다고 한 출력이 유리해지지 않도록** 유용한 관찰 수와 review 비율도 보고 |
| **출력 실패** | 동일 입력 기술적 재시도 **1회**, 지속 실패는 별도 기록. **실패를 제거하고 정확도만 높이지 않는다.** 실패 포함 손실(최대 손실 3) + 유효 출력 MAE + 출력 성공률을 함께 보고. **실패를 임상 0점으로 바꾸지 않는다** |

**모든 조건이 같은 영상을 보도록 하고, 같은 보류량 비교와 전체 영상 기준 손실을 함께 제시한다.**

---

## 11. 판정표 (v5 §10 유지)

| 관측 결과 | 허용되는 결론 |
|---|---|
| A3가 A1·A2·R보다 좋고 **실제 불량 관측**에서 효과 확인 | 이 표본/과제에서 **측정 품질에 따른 입력 선택의 추가 가치** |
| A3가 A1보다 좋지만 A2/R와 차이 작음 | 정보 추가 효과는 가능하나 **품질 규칙의 고유 기여는 미확인** |
| A0/A4가 영상 VLM보다 좋음 | **이 점수 예측에서 VLM 영상 입력의 추가 가치는 입증되지 않음** |
| A3가 다수를 보류해야만 좋아짐 | **보류–정확도 절충** 결과. 포괄적 자동화 성공이 아님 |

**어느 칸이든 "VLM이 임상 채점을 대체한다"고 쓰지 않는다.**

---

## 12. 피해야 할 과잉 주장 (문헌 근거부)

| 주장하면 안 되는 것 | 이미 한 연구 | 그들이 한 일 |
|---|---|---|
| "ARAT 손 과제 운동학을 처음 측정했다" | **Padilla-Magaña 2022** (PMID 35632013) | 건강 25 + 환자 12, CyberGlove II로 ARAT 16활동 계측. **2–3점 구간만으로 SVM 97.8%** |
| "건강인과 환자를 숫자로 구분한다는 발상이 새롭다" | **Padilla-Magaña & Peña-Pitarch 2022** (PMID 36501779) | 장갑 관절각으로 분류 모델 구축 |
| "JSON·구조화 프롬프트·특징 주입이 최초다" | **Tang 2025**(arXiv:2505.18412), **Xing 2025**(PMID 40067873) | 특징+규칙을 LLM에 제공. Xing은 정확도 0.91 |
| "모든 VLM은 재활 평가에 실패한다" | **Li 2026** (PMID 42406872) | 특정 모델·프로토콜에서 실패를 보고. **일반화 금지** |
| "불확실성 처리·설명·판단 보류가 최초다" | **xAARA**(arXiv:2606.24960), **Ahmed 2024**(PMID 39186425) | 다중 시점 + 2명 평가자, 엔트로피 0.459→0.004 |
| "운동학이 순서형 점수보다 상세하다는 게 새롭다" | **Unger 2026**(arXiv:2607.23608) | ARAT 만점 이후에도 MCID 15 pp 변화 검출 |
| "영상과 수치의 결합이 최초다" | **UbiPhysio**(arXiv:2308.10526), **BiomechGPT**(arXiv:2505.18465) | 임상가 설계 특징 + retrieval / motion token + LM |
| "GMM으로 정상 하위유형을 처음 모델링한다" | **Romero 2010**, **Jarque-Bou 2019/2020** | GPLVM+GMM/GMR, 시너지 PCA+군집 |

**그리고 우리 문서 자체의 규칙:** `flatlining`은 **현상명**, `kinematic blindness`는 **우리가 붙인 해석적 명칭**이다. 표준 학술용어로 선결하지 않는다.

---

## 13. 결정 필요 목록 (구체화 단계의 입력)

우선순위 순. 이 목록이 다음 작업의 체크리스트다.

| # | 결정 사항 | 왜 지금 필요한가 | 관련 문헌 |
|---|---|---|---|
| 1 | **14프레임 절단 규칙** (균등 샘플링 / 고정 창) | VLM 입력의 시간 정보량을 결정. H4 해석이 여기 달려 있다 | Zamin 2023, Li 2026 |
| 2 | **u(오류 단위)의 정의와 출처** | bias/burst 크기가 결과를 좌우. 치구 기준인지 3D 기준인지 명시 의무 | v5 §6.1, §8 |
| 3 | **Q 규칙의 구체 임계값** | A3의 전부. ARAT 점수나 VLM 정답률로 임계값을 고르면 안 됨 | v5 §6.2 |
| 4 | **가림 주석 프로토콜** (몇 명, 무엇을, 언제) | 품질 규칙의 정답 기준 | Scano 2020 |
| 5 | **동적 기준장비 확보 여부** | 확보 실패 시 Q를 "교정된 mm 오차"로 부를 수 없음 | v5 §6.1 |
| 6 | **환자 기능 수준 분포 목표** | 0·3점 편중 시 1·2점 결론 제한 | Hernández 2019, Kristersson 2019 |
| 7 | **최소 검출 가능 효과 시뮬레이션** | 12명으로 무엇을 주장할 수 있는지 미리 못박기 | Tannús 2026 |
| 8 | **VLM 모델·버전·프롬프트 확정** | 재현성 기록 요건 | v5 §, Li 2026 |
| 9 | **건강인 모집 창구와 손 크기 4구간 확보 방법** | 20명 최소선의 실행 가능성 | Herbst 2020 |
| 10 | **설명 평가자 선정과 눈가림 절차** | supported/contradicted/unverifiable 판정의 신뢰도 | v5 §10 |

---

## 14. 나이브 일정 (16주 가정)

| 주 | 해야 할 일 | 끝나야 하는 산출물 |
|---|---|---|
| 1–2 | 결정 목록 1~5 확정, 카메라 프리셋, 저장 파이프라인(L0/L1) | 프로토콜 동결본, 저장 검증 |
| 3–4 | 정적 치구 검증, 동적 기준 확보, Q 규칙 후보 | **과제별 측정 오류표(초안)** |
| 5–6 | 추적·국소 depth·Q 구현, 원본 보존/결측 검사 | 동일 후보값에서 A2/A3 입력 생성 코드 |
| 7–9 | **건강인 개발 8명** 촬영, 품질 규칙 동결 | 품질 규칙 동결본 + 실패 사례 목록 |
| 10–11 | **건강인 독립 검증 12명** 촬영 | 규칙 재현성 보고(사람 단위 독립) |
| 12–13 | **환자 개발 3명** 촬영, 프롬프트 설정 | 프롬프트 동결본 |
| 14–15 | **환자 본평가 12명** 촬영 (48시행) | 원본·주석·참조 점수 완비 |
| 15–16 | A0/A1/A2/A3/A4/R 실행 + 오류 주입 | **조건별 점수·근거·실행/실패 기록**, **오염 수준별 오차 그림**, **대응 비교표** |

**v5 대비 변화:** v5는 건강인을 8명으로 잡았으나, 이 계획은 **20명**이므로 주 7–11이 늘어난다. 일정 전체가 2~3주 밀릴 수 있다. `[미결정]` 건강인 모집을 병렬화할지 결정 필요.

---

## 15. 검증 상태와 한계 (정직한 기록)

**이 문서에서 검증된 것**
- 인용한 모든 수치는 `outputs/rgbd-grasp-vlm-protocol-analysis.md`와 `outputs/arat-fma-ue-evidence-map.md`에 출처와 함께 등록된 값이다
- v5 원문의 A0~A4/R 정의, K1/K2/Q/T 정의, 판정표는 **원문 grep으로 직접 확인**했다

**이 문서에서 검증되지 않은 것**
- **환자 15명·건강인 20명의 검정력**: 계산하지 않았다. "충분하다"고 주장하지 않는다
- **14프레임의 정보 충분성**: 실험 전이므로 알 수 없다
- **Q 규칙의 실제 성능**: 존재하지 않는다
- **u의 크기**: 치구/3D 기준 검증 전에는 정할 수 없다
- **D455의 최소 깊이 거리와 손 해상도**: 제조사 데이터시트 확인 필요
- **건강인 20명 모집의 현장 가능성**: 미확인

**다음 단계 제안 순서**
1. 결정 목록 1~3을 먼저 닫는다 (14프레임 규칙, u 정의, Q 임계값 골격)
2. 그 다음 §7 계측 검증을 실제로 돌린다 (치구 135기록은 사람 없이 가능)
3. 그 결과로 §4의 규모를 다시 계산한다

---

## Sources

1. Yozbatiran N, Der-Yeghiaian L, Cramer SC (2008). *A Standardized Approach to Performing the Action Research Arm Test.* Neurorehabil Neural Repair. https://doi.org/10.1177/1545968307305353
2. Hsueh IP et al. (2009). *Psychometric Comparisons of 4 Measures for Assessing Upper-Extremity Function in People With Stroke.* Phys Ther. https://doi.org/10.2522/ptj.20080285
3. Kristersson T, Persson HC, Alt Murphy M (2019). *Evaluation of a short assessment for upper extremity activity capacity early after stroke.* J Rehabil Med 51(4):257–263. https://doi.org/10.2340/16501977-2534
4. Hernández ED et al. (2019). *Intra- and inter-rater reliability of Fugl-Meyer Assessment of Upper Extremity in stroke.* J Rehabil Med. PMID 31448807. https://doi.org/10.2340/16501977-2590
5. Valladares B et al. (2024). *The association between dexterity and upper limb impairment during stroke recovery.* Front Neurol. PMID 39224885. https://doi.org/10.3389/fneur.2024.1429929
6. Schwarz A, Kanzler CM, Lambercy O, Luft AR, Veerbeek JM (2019). *Systematic Review on Kinematic Assessments of Upper Limb Movements After Stroke.* Stroke 50(3):718–727. PMID 30776997. https://doi.org/10.1161/STROKEAHA.118.023531
7. Mohamed Refai MI et al. (2021). *Smoothness metrics for reaching performance after stroke. Part 1.* J NeuroEng Rehabil. PMID 34702281. https://doi.org/10.1186/s12984-021-00949-6
8. Bayle N et al. (2024). *Measurement properties of movement smoothness metrics in moderate to severe subacute stroke.* J NeuroEng Rehabil. https://doi.org/10.1186/s12984-024-01382-1
9. Saes M et al. (2021). *Smoothness metric during reach-to-grasp after stroke: part 2.* J NeuroEng Rehabil. https://doi.org/10.1186/s12984-021-00937-w
10. Alt Murphy M, Willén C, Sunnerhagen KS (2012). *Movement kinematics during a drinking task are associated with the activity capacity level after stroke.* Neurorehabil Neural Repair. PMID 22647879. https://doi.org/10.1177/1545968312448234
11. Alt Murphy M, Willén C, Sunnerhagen KS (2011). *Kinematic variables quantifying upper-extremity performance after stroke during reaching and drinking from a glass.* Neurorehabil Neural Repair. PMID 20829411. https://doi.org/10.1177/1545968310370748
12. Qiu Q et al. (2022). *Evaluation of Changes in Kinematic Measures of Three Dimensional Reach to Grasp Movements.* IEEE EMBC 2022:5107–5110. PMID 36086392. https://doi.org/10.1109/EMBC48229.2022.9871891
13. van Kordelaar J, van Wegen EEH, Kwakkel G (2012). *Unraveling the interaction between pathological upper limb synergies and compensatory trunk movements.* Exp Brain Res 221:251–262. https://doi.org/10.1007/s00221-012-3169-6
14. Schwarz A et al. (2025). *Compensatory Proximal Adjustments Characterize Effective Reaching Movements After Stroke.* Stroke. https://doi.org/10.1161/STROKEAHA.124.049336
15. Kim WS, Cho S, Baek D, Bang H, Paik NJ (2016). *Upper Extremity Functional Evaluation by Fugl-Meyer Assessment Scoring Using Depth-Sensing Camera in Hemiplegic Stroke Patients.* PLoS ONE 11(7):e0158640. https://doi.org/10.1371/journal.pone.0158640
16. Li Y et al. (2022). *A Novel Automated RGB-D Sensor-Based Measurement of Voluntary Items of the Fugl-Meyer Assessment for Upper Extremity.* Brain Sci 12(10):1380. https://doi.org/10.3390/brainsci12101380
17. Zamin SA et al. (2023). *aBnormal motION capture In aCute Stroke (BIONICS).* Neurorehabil Neural Repair 37(9):591–602. PMID 37592867, PMC10602593. https://doi.org/10.1177/15459683231184186
18. Wang Z et al. (2024). *Clinical validation of automated depth camera-based measurement of the Fugl-Meyer assessment for upper extremity.* Clin Rehabil 38(8):1091–1100. PMID 38693881. https://doi.org/10.1177/02692155241251434
19. Zhou YM et al. (2025). *Estimating Upper Extremity Fugl-Meyer Assessment Scores From Reaching Motions Using Wearable Sensors.* IEEE J Biomed Health Inform. PMID 40031831. https://doi.org/10.1109/JBHI.2025.3542037
20. Deb S, Islam MF, Rahman S, Rahman S (2022). *Graph Convolutional Networks for Assessment of Physical Rehabilitation Exercises.* IEEE TNSRE 30:410–419. https://doi.org/10.1109/TNSRE.2022.3150392
21. Ahmed T, Rikakis T (2025). *Automated ARAT Scoring Using Multimodal Video Analysis, Multi-View Fusion, and Hierarchical Bayesian Models.* arXiv:2505.01680. https://arxiv.org/abs/2505.01680
22. Ahmed T, Rikakis T, Kelliher A, Wolf SL (2024). *A Hierarchical Bayesian Model for Cyber-Human Assessment of Movement in Upper Extremity Stroke Rehabilitation.* IEEE TNSRE 32:3157–3166. PMID 39186425. https://doi.org/10.1109/TNSRE.2024.3450008
23. Li V, Kamalakannan N, Parnandi A, Schambra H, Fernandez-Granda C (2026). *Vision-language models for human motion understanding: Lessons from stroke rehabilitation.* PLOS Digit Health 5(7):e0001506. PMID 42406872. https://doi.org/10.1371/journal.pdig.0001506
24. Tang J, Abedi A, Colella TJF, Khan SS (2025). *Rehabilitation Exercise Quality Assessment and Feedback Generation Using Large Language Models with Prompt Engineering.* arXiv:2505.18412. https://arxiv.org/abs/2505.18412
25. Xing Q, Xing X, Guo P, Tang Z, Shen Y (2025). *LLM-FMS: A fine-grained dataset for functional movement screen action quality assessment.* PLOS ONE 20(3):e0313707. PMID 40067873. https://doi.org/10.1371/journal.pone.0313707
26. Unger et al. (2026). *Markerless Motion Capture in Routine Clinical Upper Limb Assessments: Validity and Insights Beyond Ordinal Scoring.* arXiv:2607.23608. https://arxiv.org/html/2607.23608
27. Ahmed T, Rikakis T et al. (2026). *Enhancing Clinician Decision-Making via Uncertainty-Aware Multi-Expert Fusion for Stroke Rehabilitation (xAARA).* arXiv:2606.24960. https://arxiv.org/html/2606.24960
28. Padilla-Magaña JF, Peña-Pitarch E, Sánchez-Suarez I, Ticó-Falguera N (2022). *Quantitative Assessment of Hand Function in Healthy Subjects and Post-Stroke Patients with the Action Research Arm Test.* Sensors 22(10):3604. PMID 35632013. https://doi.org/10.3390/s22103604
29. Padilla-Magaña JF, Peña-Pitarch E, Sánchez-Suarez I, Ticó-Falguera N (2022). *Hand Motion Analysis during the Execution of the Action Research Arm Test Using Multiple Sensors.* Sensors 22(9):3276. PMID 35590966. https://doi.org/10.3390/s22093276
30. Padilla-Magaña JF, Peña-Pitarch E (2022). *Classification Models of Action Research Arm Test Activities in Post-Stroke Patients Based on Human Hand Motion.* Sensors 22(23):9078. PMID 36501779. https://doi.org/10.3390/s22239078
31. Herbst Y, Zelnik-Manor L, Wolf A (2020). *Analysis of subject specific grasping patterns.* PLoS ONE 15(7):e0234969. PMID 32640003. https://doi.org/10.1371/journal.pone.0234969
32. Jarque-Bou NJ, Scano A, Atzori M, Müller H (2019). *Kinematic synergies of hand grasps.* J NeuroEng Rehabil 16:63. https://doi.org/10.1186/s12984-019-0536-6
33. Jarque-Bou NJ, Sancho-Bru JL, Vergara M (2020). *Sharing of hand kinematic synergies across subjects in daily living activities.* Sci Rep 10:6116. https://doi.org/10.1038/s41598-020-63092-7
34. Romero J, Feix T, Ek CH, Kjellström H, Kragic D (2010). *Spatio-Temporal Modeling of Grasping Actions.* IEEE/RSJ IROS 2010. https://www.csc.kth.se/~dani/RSS/feix.pdf
35. Faity G, Mottet D, Froger J (2022). *Validity and Reliability of Kinect v2 for Quantifying Upper Body Kinematics during Seated Reaching.* Sensors 22(7):2735. PMID 35408349. https://doi.org/10.3390/s22072735
36. Lafayette TBG et al. (2023). *Validation of Angle Estimation Based on Body Tracking Data from RGB-D and RGB Cameras for Biomechanical Assessment.* Sensors 23(1):3. PMID 36616603. https://doi.org/10.3390/s23010003
37. Hamilton RI et al. (2024). *Comparison of computational pose estimation models for joint angles with 3D motion capture.* J Bodyw Mov Ther. PMID 39593603. https://doi.org/10.1016/j.jbmt.2024.04.033
38. Scano A et al. (2020). *Analysis of Upper-Limb and Trunk Kinematic Variability: Accuracy and Reliability of an RGB-D Sensor.* MTI 4(2):14. https://doi.org/10.3390/mti4020014
39. Lee U, Lee S, Kim SA, Kim Y, Lee S (2025). *Validity and reliability of single camera markerless motion capture systems with RGB-D sensors for measuring shoulder range-of-motion: a systematic review.* Front Bioeng Biotechnol 13:1570637. PMID 40486204. https://doi.org/10.3389/fbioe.2025.1570637
40. Tannús J, Valentini C, Naves E (2026). *AI-driven low-cost rehabilitation exergame as a lightweight framework for stroke assessment.* npj Digit Med 9:196. https://doi.org/10.1038/s41746-026-02383-1
41. UbiPhysio (2024). *Support Daily Functioning, Fitness, and Rehabilitation with Action Understanding and Feedback in Natural Language.* arXiv:2308.10526. https://arxiv.org/abs/2308.10526
42. BiomechGPT (2025). *Extending Motion-Language Models to Clinical Motion Understanding.* arXiv:2505.18465. https://arxiv.org/abs/2505.18465
43. Collins KC, Kennedy NC, Clark A, Pomeroy VM (2018a). *Getting a kinematic handle on reach-to-grasp: a meta-analysis.* Physiotherapy 104(2):153–166. https://doi.org/10.1016/j.physio.2017.10.002
44. Collins KC, Kennedy NC, Clark A, Pomeroy VM (2018b). *Kinematic Components of the Reach-to-Target Movement After Stroke: A Systematic Review and Meta-Analysis.* Front Neurol 9:472. PMID 29988530. https://doi.org/10.3389/fneur.2018.00472
45. Černek A, Sedmidubský J, Budíková P (2024). *REHAB24-6: Physical Therapy Dataset for Analyzing Pose Estimation Methods.* LNCS:18–33. https://doi.org/10.1007/978-3-031-75823-2_2
46. Intel RealSense D400 Series Datasheet (2020). https://www.realsenseai.com/wp-content/uploads/2020/06/Intel-RealSense-D400-Series-Datasheet-June-2020.pdf
47. 실행계획 v5 (사용자 업로드, 2026-09-22). `뇌졸중_손기능_RGBD_VLM_통합실험계획_2026-09.md`

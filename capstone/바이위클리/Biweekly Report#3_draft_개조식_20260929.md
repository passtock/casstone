# Biweekly Report #3 — 초안 · 이재용 22000561

> `〔그림 N〕` = 그림 삽입 위치. 처음 나오는 전문용어는 **한글(약어)** 로 풀어 씀.

---

# 한눈에 보는 요약

- **한 일** — 실험을 **ARAT 2과제·5개 비교조건**으로 재설계하고, 수집 프로그램에 **원시 RGB-D 저장**을 추가했다.
- **검증한 것** — SPARC 계산식이 원논문과 일치, K2(손목 속도) 계산 **6종 시험 통과**, 결과 파일 구조 정상(78열).
- **다음 할 일** — 실제 카메라로 **10~20초 촬영** → 원시 저장 확인 → **형식 변환 후 K1·K2·Q 계산**.

---

# 표지

| 항목 | 내용 |
|---|---|
| Name | 이재용 |
| Advisor | 김재효 (signature) |
| Period | Week 8~9 (2026.09 하순~10월 초) |
| WBS | 1.1. 세부연구주제 및 프로토콜 확정 / 1.2. 수집·검증 파이프라인 |

---

# 주요 용어 (처음 보는 독자를 위해)

| 용어 | 뜻 |
|---|---|
| **ARAT** | Action Research Arm Test. 뇌졸중 후 상지 기능을 보는 **국제 표준 수행 평가**. **19개 과제**(블록·공·구슬 집기 등)를 치료사가 **0~3점**(0=못함, 1=일부 수행, 2=완료했으나 어려움·느림, 3=정상)으로 채점, 총 0~57점. |
| **K1** | 엄지 끝–검지 끝 표면 사이 거리의 95백분위(mm). "손 벌림"의 대리값. |
| **K2** | 손목 표면점의 3차원 이동 속도의 95백분위(mm/s). "손 이동 속도"의 대리값. |
| **Q** | 품질 지표. 깊이 유효율·연속 결측·가림으로 수치의 신뢰 가능 여부를 판단. |
| **SPARC** | 움직임 평활도(부드러움) 지표. 0에 가까울수록 부드러움. |
| **MAE** | 평균 절대 오차. 예측 점수와 정답 점수의 평균 차이. |
| **P95** | 95백분위. 극단값 영향을 줄이려는 대표값. |
| **처리 흐름** | 원본 수집 → 수치 계산(K1·K2·Q) → 시행 요약 → AI(VLM) 평가 |
| **VLM** | 영상과 글을 함께 이해하는 AI 모델(이 연구에서는 채점에 사용, 재학습 없이 실행). |

---

# Research Results in This Biweek

## (1) 실험 설계: ARAT 2과제 + 5개 비교조건

**과제 (Why: 임상 정답이 있는 표준 과제로 전환)**

- **T1** = ARAT 3번 — 5 cm 블록 55 g, 선반 37 cm → *큰 물체 파지·수직 도달*
- **T2** = ARAT 12번 — 엄지–검지 구슬 ⌀1.5 cm, 5.4 g → *정밀 집기*
- 기존 임의 20 cm 도달–잡기는 **치료사 채점 기준(임상 정답)이 없고** 수직 거상·정밀 집기를 담지 못한다.
- 19개 전체 항목은 환자 **피로·경직으로 수행이 왜곡**된다.

`〔그림 1〕 ARAT 물리 세팅 도식 (테이블 75 cm · 의자 46 cm · 선반 37 cm · 카메라 D455 30~45° 하향, 작업거리 0.75 m)`

**ARAT 요약**
- 뇌졸중 후 상지 기능을 보는 **국제 표준 수행 평가**. **19개 과제**를 치료사가 **0~3점**으로 채점(총 0~57점).
- 점수 뜻: **0=못함 / 1=일부 / 2=완료했으나 어려움·느림 / 3=정상 완료**.
- 이 연구는 **총점이 아니라 두 과제의 항목 점수**를 정답으로 쓰고, **ARAT 전체 자동화가 아니라 “수치를 주었을 때 채점 오차가 어떻게 변하는가”** 를 본다.

**ARAT 19개 항목 중 왜 이 2개인가 — 선정 기준**

- 전제: 우리는 **ARAT 자동화가 아니라 수치 정확도 변화**를 보는 연구 → 항목을 늘릴 이유가 없음.

| 선정 기준 | 통과 | 제외(예) |
|---|---|---|
| ① 치료사 항목 점수(정답)가 존재 | 전 항목 | — |
| ② K1·K2가 그 항목 수행을 반영 | **3번 블록**(큰 물체 파지·이동), **12번 구슬**(엄지–검지 정밀 핀치) | 숫돌·큰 관·와셔/볼트(도구 조작 → 손끝 거리와 무관), 물 붓기 |
| ③ 단일 RGB-D로 관측 가능(가림 관리) | 3번·12번 | gross movement(몸통·어깨 중심) |
| **→ 결과** | **2항목** | 나머지 제외 |

**문헌 근거 — 왜 이 2개인가** (Unger 2026 원문 직접 확인)
- 운동학 수치는 **“했냐/못했냐”(0·1점 vs 2·3점)는 잘 가른다** → AUC **0.91–1.00** `[10]`.
- 그러나 **“2점(어렵게 완료) vs 3점(정상 완료)”는 약하다** → AUC **0.70–0.84** `[10]`.
  - (AUC는 1에 가까울수록 잘 구분. 0.9 이상 우수, 0.7 내외 보통)
- 즉 수치는 **완수/실패는 잘 맞히지만 “얼마나 잘했는가”는 잘 못 가른다** → 그래서 채점이 실제로 갈리는 **두 과제**에 집중한다.
- 물성·배치·채점은 **ARAT 표준 매뉴얼 그대로**(블록 5 cm 55 g / 구슬 ⌀1.5 cm 5.4 g / 선반 37 cm / 3점 = 5초 이내) `[1]`.
- ARAT를 손 운동학으로 측정·분류한 선행연구가 **이미 있다** `[7]` → **“ARAT 자동화” 자체는 새롭지 않다**. 우리 기여는 **“수치를 주면 채점 오차가 어떻게 변하는가”** 이다.

**비교조건 (Why: 세 질문을 분리하기 위해)**

| 조건 | 입력 |
|---|---|
| **A1** | 영상만 |
| **A2** | 영상 + 전체 수치 |
| **A3** | 영상 + **품질 통과** 수치 |
| **A4** | 수치만 (영상 없음) |
| **R** | A2에서 A3와 **같은 개수**를 무작위로 뺀 조건 |
| **A0** | 경량 통계모형 (비교용) |

- ① "수치를 주면 채점이 좋아지는가" → **A2 − A1**
- ② "품질로 골라 주면 나아지는가" → **A2 − A3**
- ③ "그 이득이 단순히 수치를 덜 봐서인가" → **R − A3**

**주 결과**

| 표기 | 정의 | 의미 |
|---|---|---|
| **PR-1** | MAE(A2) − MAE(A1) | 수치를 준 효과 (**양수 = 수치가 해로움**) |
| **PR-2** | MAE(A2) − MAE(A3) | 품질 선택 효과 (같은 영상·같은 정답) |
| **PR-3** | MAE(R) − MAE(A3) | 품질 선택의 고유 가치 |
| 대가 | 보류율(A3) · (보류율–오차) 곡선 | 품질 선택의 **대가**를 숨기지 않음 |

**지표** — K1(엄지–검지 거리)·K2(손목 속도)·Q(품질). SPARC 등 미분 지표는 **잡음에 민감**하여 이번 필수 지표에서 제외(탐색용).

`〔그림 2〕 수집 → 수치 계산 → AI 평가 처리 흐름과 지표 정의`

## (2) 수집 프로그램이 저장하는 데이터

- **RGB 영상** — 원본 영상과 손 관절 표시 영상
- **깊이 기록** — 정렬 전 원시 깊이 + 색상에 정렬한 깊이 (프레임별, 16비트 원본)
- **손 관절(스켈레톤) 기록** — 21개 관절의 픽셀 좌표와 3차원 좌표(MediaPipe · RealSense), 깊이 유효 여부
- **프레임별 각도·상태** — 관절 각도와 깊이 결측 이유
- **프레임 ↔ 촬영 시각 대응표**
- **시행별 요약** — 사이클 수·주기·ROM·평활도(SPARC)·손목 속도(K2)
- **카메라·세션 정보** — 해상도·프레임레이트·카메라 내부 파라미터

- 모든 기록은 **프레임 번호로 서로 연결**된다.

`〔그림 3〕 저장 데이터 구성`


## (3) 정확성 점검 (이번 기간 수행)

| 점검 항목 | 방법 | 결과 |
|---|---|---|
| SPARC 계산식이 원논문과 같은가 `[5]` | 원저자 공개 참조 프로그램과 같은 입력으로 비교 | **값 일치** (4건 중 3건 계산 정밀도 수준, 1건 0.5% 이내) |
| 한 주기 단위 SPARC가 나뉘어 계산되는가 | 여러 주기를 인위적으로 만든 시험 신호 | **주기별로 분리되어 정상 산출** |
| 결과 파일(CSV) 구조가 어긋나지 않는가 | 항목 행과 데이터 행의 **열 개수 일치** | **78 = 78 (일치)** |
| K2(손목 속도) 계산이 옳은가 | 6가지 인위 시험 | **6종 전부 통과** (알려진 속도 정확 산출 / 이상 구간 제외 / 표본 부족 시 미보고 / 정지 시 0) |
| 원시 깊이가 저장·복원되는가 | 저장 후 **다시 읽어 원본과 대조** | **전부 통과** (깊이 값·자료형·프레임 정보 일치) |
| 실험 조건 생성 프로그램이 계획서대로인가 | 항목별 자체 점검 시험 | **43항목 전부 통과, 실패 0** |
| 수집본→계산 입력 **형식 변환 도구**가 작동하는가 | 합성 수집 세션으로 **변환 → 수치 계산 → 결과 파일**까지 실행 | **전부 통과** — 변환 후 K1=83.33 mm 산출, 결과 파일 생성(80프레임) |

`〔그림 4〕 SPARC 참조 프로그램 대조 결과`

## (4) 오류 정정

- **구슬 규격 ⌀1.6 cm → ⌀1.5 cm.** 근거: ARAT 표준 채점지 원문 "Marble, 1.5 cm". 프로그램·프로토콜·계획서까지 통일.
- **SPARC 편입 판정 "탈락" → "보류".** 이전 102%는 **시간 오류가 있던 예전 파일럿** 값이라, 교정 후 재계산 전에는 판정할 수 없음.
- **표현 완화** — "같은 정답이라 오류에 면역" → "조건 간 비교를 맞출 뿐, **정답 자체 오류의 영향은 제거되지 않음**".
- **인용 대조** — Li 등 2022 원문 직접 확인(RealSense + SPARC 사용, Vicon 기준 손목 위치 차 54/43/138/150 mm·평균 96 mm) `[2]`.

---

# Research Items in Next Biweek

| # | 계획 | 확보할 산출물 |
|---|---|---|
| ① | **짧은 수집 시험** — RealSense로 10~20초 촬영, 원시 저장 개수·오류 확인 | 촬영 폴더(원시 파일·영상·CSV), **실측 fps** |
| ② | **실제 촬영 자료로 변환·수치 계산 실행** — 촬영본 → 계산 입력으로 변환, K1·K2·Q 산출 | 계산 결과 파일(`L2_metric/*.json`) |
| ③ | **검증률 확인** — K1/K2 가용률·결측률·유효 프레임 수, 반복 변동 | **검증률 요약표** |
| ④ | **VLM 1회 시범** — A1/A2/A3/A4 프롬프트로 1회 추론, 점수 파싱·토큰 실측 | `predictions.csv`(예측 결과 로그) |
| ⑤ | **보조 K2 ↔ 정식 K2 일치 검증** | 정의 대조표 |

`〔그림 5〕 다음 단계 검증 절차 순서도`

---

# Issues and Overall Progress

## 지도교수 면담 제기사항 및 실제 조치

| 제기된 사항 | 실제 조치 (이번 기간) |
|---|---|
| 기존 모델·지표의 결합에서 무엇이 개선되는지 불명확 | 주 결과를 **수치 주입 효과(PR-1)** 와 **품질 선택 효과(PR-2·PR-3)** 로 구체화. A1~A4·R 비교조건으로 **입력만 바꿔** 채점 오차 변화를 측정하도록 확정 |
| 제한된 행동 과제의 선정 근거 보완 필요 | **선정 기준 3가지**(① 치료사 정답 존재 ② K1·K2가 수행 반영 ③ 단일 RGB-D 관측 가능)로 ARAT 19개를 걸러 **2항목(3번 블록·12번 구슬)** 채택. 항목 확대는 이번 범위 밖(전제: 자동화가 아니라 수치 정확도 변화). **상세·근거는 (1) 참조** `[1][7][10]` |
| 당기는 저항 등 힘 관련 평가 가능성 검토 | **영상·운동학만으로 힘을 직접 측정할 수 없음**을 확인. 이번 범위는 **K1(거리)·K2(속도)로 한정**하고, 힘은 별도 센서가 필요하므로 **제외** |
| 환자와 비장애인의 개인별 특성 분석 제안 | **개인별 반복 변동만 기술적으로 보고**(검증률·반복 변동), **새 유형 발견·군집화는 범위 밖**으로 명시 |

## 진행도와 중간 결론

| 항목 | 현재 상태 |
|---|---|
| 실험 설계(ARAT 2과제·5조건) | **확정** |
| 물리 세팅 | 구축·검증 완료 |
| 수집 프로그램(원시 RGB-D) | **구현 완료 · 자체 검증 통과** |
| 계산 프로그램 | 자체 점검 통과 / **실제 자료 실행은 미완** |
| 수집↔계산 연결 | **형식 변환 도구 작성·자체 시험 통과** (실제 촬영 자료 적용은 촬영 후) |
| VLM 실행 | 준비 완료 / **실행 0회** |
| 실제 자료 검증 | **아직 없음** |

> **중간 결론:** 설계·프로그램은 거의 정리됐으나 **본실험 준비는 아직**이다. 남은 관문은 ①원시 저장 실측 ②형식 변환 후 수치 계산 ③VLM 연결이다.

---

# 참고문헌

✅ = 이번 기간 원문/Crossref/arXiv에서 직접 확인

본문 직접 인용: `[1]` ARAT 표준 매뉴얼 · `[5]` SPARC 원논문 · `[7]` ARAT 손 운동학 자동화 선행 · `[10]` 운동학 수치의 채점 판별력.
배경 문헌: `[2]` RGB-D FMA 자동채점 · `[3]` VLM 재활 한계 · `[4]` 운동학 표준화 권고 · `[6]` 운동학 측정 반복성(MDC) · `[8]` MediaPipe 손추적 타당도 · `[9]` LLM 재활 피드백.

[1] Yozbatiran, N., Der-Yeghiaian, L., & Cramer, S. C. (2008). A standardized approach to performing the Action Research Arm Test. *Neurorehabilitation and Neural Repair, 22*(1), 78–90. https://doi.org/10.1177/1545968307305353  ✅

[2] Li, Y., Li, C., Shu, X., Sheng, X., Jia, J., & Zhu, X. (2022). A novel automated RGB-D sensor-based measurement of voluntary items of the Fugl-Meyer Assessment for Upper Extremity: A feasibility study. *Brain Sciences, 12*(10), 1380. https://doi.org/10.3390/brainsci12101380  ✅

[3] Li, V., Kamalakannan, N., Parnandi, A., Schambra, H., & Fernandez-Granda, C. (2026). Vision-language models for human motion understanding: Lessons from stroke rehabilitation. *PLOS Digital Health, 5*(7), e0001506. https://doi.org/10.1371/journal.pdig.0001506  ✅

[4] Kwakkel, G., Van Wegen, E. E. H., Burridge, J. H., Winstein, C. J., van Dokkum, L. E. H., Alt Murphy, M., Levin, M. F., & Krakauer, J. W. (2019). Standardized measurement of quality of upper limb movement after stroke: Consensus-based core recommendations from the Second Stroke Recovery and Rehabilitation Roundtable. *International Journal of Stroke, 14*(8), 783–791. https://doi.org/10.1177/1747493019873519  ✅

[5] Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015). On the analysis of movement smoothness. *Journal of NeuroEngineering and Rehabilitation, 12*, 112. https://doi.org/10.1186/s12984-015-0090-9  ✅

[6] Wagner, J. M., Rhodes, J. A., & Patten, C. (2008). Reproducibility and minimal detectable change of three-dimensional kinematic analysis of reaching tasks in people with hemiparesis after stroke. *Physical Therapy, 88*(5), 652–663. https://doi.org/10.2522/ptj.20070255  ✅

[7] Padilla-Magaña, J. F., & Peña-Pitarch, E. (2022). Classification models of Action Research Arm Test activities in post-stroke patients based on human hand motion. *Sensors, 22*(23), 9078. https://doi.org/10.3390/s22239078  ✅

[8] Amprimo, G., Masi, G., Pettiti, G., Olmo, G., Priano, L., & Ferraris, C. (2024). Hand tracking for clinical applications: Validation of the Google MediaPipe Hand (GMH) and the depth-enhanced GMH-D frameworks. *Biomedical Signal Processing and Control, 96*, 106508. https://doi.org/10.1016/j.bspc.2024.106508  ✅

[9] Tang, J., Abedi, A., Colella, T. J. F., & Khan, S. S. (2025). Rehabilitation exercise quality assessment and feedback generation using large language models with prompt engineering. *arXiv*. https://arxiv.org/abs/2505.18412  ✅

[10] Unger, T., Lambercy, O., Gassert, R., Luft, A. R., Cotton, R. J., & Easthope Awai, C. (2026). Markerless motion capture in routine clinical upper limb assessments: Validity and insights beyond ordinal scoring. *arXiv*. https://arxiv.org/abs/2607.23608  ✅

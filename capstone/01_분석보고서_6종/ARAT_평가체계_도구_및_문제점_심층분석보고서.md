# [학술 조사 보고서] Action Research Arm Test (ARAT)의 평가 프로토콜, 측정 도구, 임상적·공학적 한계점 및 선행 연구 종합 분석

**작성 일자**: 2026년 10월  
**연구 분야**: 신경재활의학(Neurorehabilitation), 바이오메카닉스(Biomechanics), 재활공학 및 컴퓨터 비전(Rehabilitation Engineering & Vision AI)  
**보고서 목적**: 뇌졸중 편마비 상지 기능 표준 평가 도구인 **ARAT(Action Research Arm Test)**의 임상 평가 체계, 도구 구성, 문제점 및 이를 센서·인공지능으로 자동화·객관화하려는 최신 선행 연구 동향을 체계적으로 조사 및 분석

---

## 1. 서론: ARAT의 정의 및 임상적 위상

### 1.1 ARAT의 기원 및 정의
**Action Research Arm Test (ARAT)**는 1981년 Lyle이 뇌졸중 및 뇌손상 환자의 상지(Upper Extremity) 기능 회복을 정량적으로 측정하기 위해 고안한 19개 항목의 수행 기반 임상 평가 도구이다 [Lyle, 1981]. 본래 1965년 Carroll이 개발한 **UEFT (Upper Extremity Function Test)**를 기반으로, 임상 현장에서 보다 빠르고 신뢰성 있게 수행할 수 있도록 재설계되었다. 이후 2008년 Yozbatiran, Der-Yeghiaian, Cramer에 의해 물체 규격, 의자 및 테이블 배치, 표준화된 채점 룰북이 정립되면서 전 세계 신경재활 임상 시험과 연구의 골드 스탠다드로 자리잡았다 [Yozbatiran et al., 2008].

### 1.2 ICF (국제기능장애건강분류) 프레임워크에서의 위치
WHO의 ICF 모델에 따르면 상지 평가 도구는 크게 **신경학적 손상(Impairment)** 수준과 **활동 제한(Activity limitation / Capacity)** 수준으로 구분된다.

```
[ICF 기반 상지 평가 도구의 층위 비교]
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. 신체 구조 및 기능 / 손상 층위 (Body Function & Impairment)          │
│    ▶ FMA-UE (Fugl-Meyer Assessment - Upper Extremity)                   │
│    - 수의적 분리 운동(Fractionation), 반사, 비정상적 시너지 패턴 평가   │
│    - "물체 없이 팔/손가락을 독립적으로 움직일 수 있는가?"                │
├─────────────────────────────────────────────────────────────────────────┤
│ 2. 활동 및 활동 제한 층위 (Activity & Activity Capacity)               │
│    ▶ ARAT (Action Research Arm Test) ★                                 │
│    - 중력에 대항하여 다양한 일상 물체를 도달(Reach)·파지(Grasp)·        │
│      운반(Transport)·해제(Release)하는 과제 수행 능력 측정              │
│    - "일상생활 도구를 조작하여 목표 위치에 성공적으로 놓을 수 있는가?"   │
└─────────────────────────────────────────────────────────────────────────┘
```

* **FMA-UE와의 차별점**: FMA-UE가 관절별 분리 운동과 시너지 이탈 여부를 정밀하게 측정한다면, ARAT는 물체 조작을 동반한 **실제 기능적 작업 수행(Functional task performance)** 능력을 평가한다.
* **운동학(Kinematics)과의 연계성**: 3차원 동작 분석 연구에 따르면, 상지 운동학 지표(Movement units, Smoothness, 체간 변위 등)는 FMA-UE 총점($r = 0.38 \sim 0.42$)보다 ARAT 총점($r = 0.81$, 설명변량 약 67%)과 훨씬 강력한 상관관계를 보인다 [Alt Murphy et al., 2012]. 즉, 운동학적 정량 데이터는 손상 척도보다 활동 척도인 ARAT와 직접적으로 연동된다.

---

## 2. ARAT 평가 프로토콜 및 세부 항목

ARAT는 총 **4개 하위 척도(Subscales), 19개 항목(Items)**으로 구성되며, 만점은 **57점**이다.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                ARAT (19항목 / 57점)                          │
├───────────────────┬───────────────────┬───────────────────┬──────────────────┤
│ 1. Grasp (쥐기)   │ 2. Grip (잡기)    │ 3. Pinch (집기)   │ 4. Gross (대동작)│
│    6개 항목 (18점)│    4개 항목 (12점)│    6개 항목 (18점)│    3개 항목 (9점)│
└───────────────────┴───────────────────┴───────────────────┴──────────────────┘
```

### 2.1 4대 하위 척도 세부 구성

| 하위 척도 | 항목 번호 | 과제 동작 | 사용 물체 및 규격 | 측정 목적 및 생체역학적 의의 |
| :--- | :---: | :--- | :--- | :--- |
| **1. Grasp**<br>(쥐기, 6항목) | 1 | 10cm 목재 블록 선반 이동 | $10 \times 10 \times 10\text{ cm}$ 큐브 (목재) | 최대 손가락 외번 및 대형 파워 파지 |
| | 2 | 2.5cm 목재 블록 선반 이동 | $2.5 \times 2.5 \times 2.5\text{ cm}$ 큐브 | 작은 정육면체 파지 및 들어올리기 |
| | **3** | **5cm 목재 블록 선반 이동** | **$5 \times 5 \times 5\text{ cm}$ 큐브** | **중간 크기 파지 (대표 과제)** |
| | 4 | 7.5cm 목재 블록 선반 이동 | $7.5 \times 7.5 \times 7.5\text{ cm}$ 큐브 | 넓은 손가락 개구 및 중량 리프팅 |
| | 5 | 크리켓 공 선반 이동 | 직경 $7.5\text{ cm}$ 구(Sphere) | 구형 파지 (Spherical Grasp) 및 수지 굴곡 |
| | 6 | 불규칙 돌 선반 이동 | 약 $10 \times 2.5\text{ cm}$ 불규칙 암석 | 비정형 표면 적응 파지 |
| **2. Grip**<br>(잡기, 4항목) | 7 | 물 따르기 (Pour water) | 컵 2개 (물 200ml 포함) | 전완 회내/회외(Pronation/Supination) 및 양손 협응 |
| | 8 | 2.25cm 튜브 페그에 끼우기 | 외경 $2.25\text{ cm}$, 길이 $16\text{ cm}$ 튜브 | 원통형 파지 및 정밀 삽입 조작 |
| | 9 | 1cm 튜브 페그에 끼우기 | 외경 $1.0\text{ cm}$, 길이 $16\text{ cm}$ 튜브 | 좁은 원통형 파지 및 정렬 제어 |
| | 10 | 와셔 볼트에 끼우기 | 외경 $3.5\text{ cm}$ 와셔, 볼트 스탠드 | 얇은 평면 물체 파지 및 조준 |
| **3. Pinch**<br>(집기, 6항목) | 11 | 6mm 볼베어링 (엄지-약지) | 직경 $6\text{ mm}$ 금속 구슬 | 엄지-약지 대립 및 정밀 끝 집기 |
| | **12** | **1.5cm 구슬 용기에 넣기** | **직경 $1.5\text{ cm}$ 대리석 구슬** | **엄지-검지 끝 집기 (Tip/Pincer Pinch)** |
| | 13 | 6mm 볼베어링 (엄지-중지) | 직경 $6\text{ mm}$ 금속 구슬 | 엄지-중지 삼각 파지/끝 집기 |
| | 14 | 6mm 볼베어링 (엄지-검지) | 직경 $6\text{ mm}$ 금속 구슬 | 엄지-검지 초정밀 끝 집기 |
| | 15 | 1.5cm 구슬 (엄지-약지) | 직경 $1.5\text{ cm}$ 구슬 | 약지 분리 조작 능력 |
| | 16 | 1.5cm 구슬 (엄지-중지) | 직경 $1.5\text{ cm}$ 구슬 | 중지 분리 조작 능력 |
| **4. Gross**<br>(대동작, 3항목) | 17 | 손 머리 뒤로 올리기 | 도구 없음 (자유 상지) | 견관절 외전/외회전, 주관절 굴곡 (뒤통수 접촉) |
| | **18** | **손 정수리 위로 올리기** | **도구 없음 (자유 상지)** | **견관절 굴곡 거상 (정수리 접촉, 체간 보상 관측)** |
| | 19 | 손 입으로 가져가기 | 도구 없음 (자유 상지) | 주관절 굴곡 및 전완 조절 (섭식 동작 모사) |

---

### 2.2 채점 기준 체계 (4점 순서 척도, 0~3점)

ARAT의 각 시행은 **시간 기준(Time)**, **완성도(Completion)**, **자세 및 동작의 정상성(Movement Quality & Posture)**의 3대 기준에 따라 0점부터 3점까지 평가된다 [Yozbatiran et al., 2008].

| 점수 | 평가 정의 | 세부 임상 판단 기준 | 생체역학적 특성 |
| :---: | :--- | :--- | :--- |
| **3점** | **정상 수행 (Normal)** | **5초 이내**에 과제를 완전히 완료하며, 비정상적인 체간 보상(Trunk compensation)이나 협응 장애 없이 매끄럽게 수행. | 의자 등받이에 몸통 접촉 유지, 부드러운 단일 벨로시티 프로파일, 대칭적 어깨 높이 |
| **2점** | **수행 완료했으나 지연/비정상 (Abnormal completion)** | 과제를 완전히 완수했으나 **5초 초과 60초 이내** 소요되거나, 심한 어려움(Great difficulty), 떨림, 또는 비정상적 보상 동작(체간 기울임, 과도한 어깨 거상)을 동반. | **몸통이 등받이에서 완전히 떨어짐(Loss of backrest contact)**, 어깨 으쓱임(Shoulder hiking), 다중 속도 피크(Submovements) |
| **1점** | **부분 수행 (Partial performance)** | 과제를 **60초 이내**에 부분적으로만 수행 (예: 물체를 집어 테이블에서 5cm 이상 들어 올렸으나 선반에 올리지 못함, 또는 운반 중 떨어뜨림). | 중력 대항 수직 리프팅은 가능하나 선반 도달 또는 능동 해제(Active Release) 실패 |
| **0점** | **수행 불가 (No movement / Complete failure)** | 물체를 전혀 움직이지 못하거나 60초 이내에 과제의 어떤 유의미한 부분도 완료하지 못함. | 수의적 수지 굴곡/신전 불가, 심한 이완성 또는 경직성 마비 |

```
[채점 알고리즘 결정 트리]
                       [과제 시작]
                            │
               ┌────────────┴────────────┐
             [성공]                    [실패]
               │                         │
      ┌────────┴────────┐         ┌──────┴──────┐
   [≤ 5초]           [> 5초]   [물체 들어올림] [전혀 불가]
      │                 │         (부분 성공)       │
 [정상 자세?]           │            │              │
 ┌────┴────┐            │            │              │
[예]      [아니오]       │            │              │
 │         │            │            │              │
 ▼         ▼            ▼            ▼              ▼
[3점]     [2점]        [2점]        [1점]          [0점]
```

> **핵심 임상 규칙 (Yozbatiran 2008 가이드라인)**:
> 1. **등받이 접촉 기준**: 환자는 평가 내내 의자 등받이에 몸통을 대고 있어야 한다. 과제를 5초 내에 완수했더라도 **몸통이 등받이에서 완전히 떨어지는 전방 굴곡(Trunk displacement)** 보상을 사용하면 3점이 아닌 **2점**을 부여한다.
> 2. **지정 파지 기준**: Pinch 하위검사에서는 지정된 손가락(예: 엄지와 약지)만을 사용해야 하며, 다른 손가락이 개입하면 감점 요인이 된다.
> 3. **낙하 기준**: 물체를 들고 가다가 떨어뜨렸을 때, 물체를 테이블에서 일정 높이 들어 올린 사실이 입증되면 0점이 아닌 1점을 부여한다.

---

### 2.3 거트만 척도(Guttman Scalogram) 기반 계층적 단축 프로토콜

ARAT의 가장 독창적인 특징 중 하나는 **Guttman 척도화(Hierarchical structure)**를 적용하여 19개 전 항목을 일일이 검사하지 않고도 평가 시간을 획기적으로 단축할 수 있다는 점이다.

```
[각 Subscale별 거트만 채점 흐름]
                      [해당 하위검사 시작]
                               │
                      [Item 1 수행 (최난도)]
                               │
               ┌───────────────┴───────────────┐
           [3점 통과]                      [< 3점 실패]
               │                               │
               ▼                               ▼
     ★ 하위검사 전 항목 3점!          [Item 2 수행 (최저난도)]
        (즉시 다음 하위검사로 이동)              │
                                       ┌───────┴───────┐
                                    [0점 실패]     [> 0점 통과]
                                       │               │
                                       ▼               ▼
                             ★ 하위검사 전 항목 0점!  남은 항목들
                                (다음 하위검사 이동)   (Item 3, 4, ...)
                                                      순차적 개별 평가
```

1. **규칙 1 (상위 패스)**: 각 하위 척도에서 가장 어려운 첫 번째 항목(Item 1)을 수행하여 **3점**을 받으면, 해당 영역의 나머지 모든 항목을 검사하지 않고 모두 **3점**으로 기록한다.
2. **규칙 2 (하위 패스)**: Item 1에서 3점을 받지 못한 경우, 가장 쉬운 두 번째 항목(Item 2)을 수행한다. 여기서 **0점**을 받으면, 해당 영역의 나머지 항목을 수행할 능력이 없다고 판단하여 모두 **0점**으로 기록한다.
3. **규칙 3 (전체 검사)**: Item 2에서 1점 또는 2점을 받은 경우에만 나머지 항목들을 3번부터 차례대로 검사한다.
* **임상적 효과**: 이 규칙 덕분에 고기능 환자나 완전 중증 환자는 4~8번의 시도만으로 검사가 종료되어 약 5~10분 내에 평가가 완료된다.

---

## 3. ARAT 평가에 사용되는 도구 및 장비

ARAT는 환자의 주관적 설문이 아니라 실제 물리적 환경과의 상호작용을 측정하므로, 하드웨어 도구의 규격이 매우 엄격하게 규정되어 있다.

### 3.1 표준 물리적 키트 (Standard Clinical Kit) 구성

| 구분 | 도구 명칭 | 상세 물리 규격 및 재질 | 배치 및 용도 |
| :--- | :--- | :--- | :--- |
| **평가 가구** | 표준 책상 (Table) | 높이 약 $76\text{ cm}$, 평평한 상판 | 평가 기본 작업대 |
| | 조절식 의자 (Chair) | 등받이가 직각에 가까운 견고한 의자 | 환자 착석 (발바닥 지면 밀착, 몸통 등받이 지지) |
| | 2단 평가 선반 (Shelf) | 베이스 높이 $37\text{ cm}$, 깊이 $25\text{ cm}$ 목재 선반 | 책상 중앙에 배치. 물체를 집어 올리는 최종 목표 지점 |
| **Grasp 도구** | 목재 큐브 블록 (4종) | $10\text{ cm}$, $7.5\text{ cm}$, $5\text{ cm}$, $2.5\text{ cm}$ 정육면체 목재 | 크기별 쥐기 및 들어올리기 |
| | 크리켓 공 | 직경 $7.5\text{ cm}$ 단단한 구형 공 | 구형 파지 (Spherical grasp) |
| | 불규칙한 형태의 돌 | 약 $10 \times 2.5\text{ cm}$ 불규칙 암석 | 비정형 표면 파지 |
| **Grip 도구** | 플라스틱 컵 (2개) | 일반 음료용 플라스틱 컵, 물 200ml | 컵 간 물 따르기 (양손 및 전완 회전) |
| | 튜브 2종 및 지지대 | 대형: $\varnothing 2.25\text{ cm} \times 16\text{ cm}$<br>소형: $\varnothing 1.0\text{ cm} \times 16\text{ cm}$ | 테이블 위 수직 페그(말뚝)에 튜브 끼우기 |
| | 와셔 및 볼트 스탠드 | 외경 $3.5\text{ cm}$ 평와셔, 수직 볼트 | 와셔를 집어 볼트에 통과시키기 |
| **Pinch 도구** | 볼 베어링 (쇠구슬) | 직경 $6\text{ mm}$ 강철 구슬 4개 | 정밀 끝 집기 (Tip pinch) |
| | 대리석/유리 구슬 | 직경 $1.5\text{ cm}$ 구슬 | 구슬을 집어 선반 위 깡통 뚜껑에 넣기 |
| | 금속 캔/수납 뚜껑 | 직경 약 $10\text{ cm}$, 높이 약 $2\text{ cm}$ 용기 | 구슬 보관 및 목표 투입 용기 |
| **계측 도구** | 스톱워치 (Stopwatch) | 1/100초 정밀도 디지털 초시계 | 과제 개시부터 선반 안착까지 소요 시간 측정 (5초 경계 판정) |

---

### 3.2 연구 및 자동화에 도입된 첨단 디지털 계측 장비

최근 15년간 컴퓨터 공학과 바이오메카닉스 연구자들은 ARAT의 수동 평가 한계를 극복하기 위해 다양한 하드웨어 및 소프트웨어 계측 시스템을 접목해 왔다.

```
[디지털 ARAT 연구에 사용되는 계측 기술 생태계]
  1. 광학식 모션 캡처 (Vicon, Qualisys)  ──► 3D 반사 마커 기반 골드 스탠다드 운동학 (밀리미터급)
  2. RGB-D 심도 센서 (RealSense, Kinect) ──► 비마커 3D 포인트클라우드, 관절 궤적 및 체간 변위
  3. AI 비전 / 포즈 추정 (MediaPipe, OpenPose) ──► 21개 손 랜드마크, 상체 골격 자동 추출
  4. 웨어러블 / 데이터 글러브 (CyberGlove, IMU)──► 손가락 관절 각도(ROM), 가속도, 손떨림 정량화
  5. 스마트 오브젝트 (Sensorized Objects)  ──► 로드셀·IMU 내장 블록/컵으로 파지력(Force) 측정
  6. 비전-언어 모델 (VLM, GPT-4o, Qwen)   ──► 멀티모달 비디오 추론 기반 자동 채점 및 피드백
```

1. **광학 마커 기반 모션 캡처 (Optical Motion Capture - Vicon, Qualisys, Optotrak)**:
   * **원리**: 상체 및 손등에 10~30개의 재귀반사 마커를 부착하고 6~12대의 적외선 카메라로 100~200Hz로 캡처.
   * **연구 적용**: Alt Murphy et al. (2012) 등에서 도달-파지 동작 중 어깨-팔꿈치 관절각, 움직임 단위 수(Submovements), 체간 전방 이동량(Trunk displacement)을 밀리미터 단위로 정밀 분석하는 연구 기준(Ground truth)으로 활용.
2. **RGB-D 심도 카메라 (Intel RealSense D435/D455, Microsoft Azure Kinect)**:
   * **원리**: 적외선 패턴 투사 및 스테레오 비전을 통해 컬러 영상과 밀리미터 단위 3D Depth 맵을 동시 획득.
   * **연구 적용**: 마커 부착 없이 환자의 도달 궤적, 손목 속도, 등받이 접촉 상실(Trunk lean)을 추적하여 ARAT 채점을 보조 [Faity et al., 2022; Wang et al., 2024].
3. **웨어러블 데이터 글러브 및 관성 센서 (Data Gloves & IMU)**:
   * **원리**: 유연 휨 센서(Bend sensor)나 광섬유 스트레인 게이지가 내장된 장갑을 착용하여 손가락 14개 관절(MCP, PIP, DIP) 각도를 실시간 수집.
   * **연구 적용**: Padilla-Magaña et al. (2022) 연구에서는 뇌졸중 환자가 ARAT 16개 과제를 수행하는 동안 데이터 글러브를 착용시켜 개별 수지 굴곡 가동범위와 협응 패턴을 정량화함 [Padilla-Magaña et al., 2022].
4. **마커리스 컴퓨터 비전 및 포즈 추정 알고리즘**:
   * **Google MediaPipe Hands / Pose**: 21개 손 키포인트 및 33개 신체 포즈를 실시간(30~60fps)으로 추정.
   * **OpenPose / DeepLabCut**: 임상 환경의 웹캠 비디오로부터 관절 좌표를 추출하여 도달 시간($T_{\text{reach}}$) 및 궤적 곡률 자동 계산.
5. **멀티모달 AI 및 비전-언어 모델 (Vision-Language Models: VLM)**:
   * **원리**: 비디오 프레임과 임상 평가 지침(Prompt)을 거대 멀티모달 신경망에 입력하여 직접 0~3점 점수를 산출.
   * **최신 동향**: Li et al. (2026, PLOS Digital Health) 및 Ahmed & Rikakis (2026, xAARA) 등에서 비전 기반 비디오 분석과 전문가 앙상블을 통한 자동 채점 가능성을 타진 중 [Li et al., 2026; Ahmed & Rikakis, 2026].

---

## 4. 기존 ARAT의 임상적·측정학적 문제점 및 한계

ARAT는 널리 검증된 도구이지만, 고유의 설계 구조와 임상 환경의 제약으로 인해 학계에서 지속적으로 여러 한계점이 지적되어 왔다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            기존 ARAT의 3대 핵심 한계                        │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│ 1. 측정학적 한계         │ 2. 임상 운영상 한계      │ 3. 운동학적 한계      │
│ - 바닥/천장 효과         │ - 시간 및 전문 인력 소모 │ - 회복 vs 보상 미구분 │
│ - 0~3점 순서척도 해상도  │ - 비표준 키트 도구 편차  │ - 힘(Force)/근긴장도  │
│ - 2↔3 경계의 주관성      │ - 평가자 간 편차         │   정량화 불가         │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

### 4.1 바닥 효과(Floor Effect)와 천장 효과(Ceiling Effect)
* **급성기/중증 마비에서의 바닥 효과 (Floor Effect)**:
  * 뇌졸중 초기 또는 중증 편마비 환자는 손가락의 수의적 신전이 불가능하다. ARAT는 물체를 들어 올리지 못하면 무조건 0점을 부여하므로, **환자의 잔존 근수축, 미세 관절 가동성, 또는 경직 개선 여부를 전혀 감지하지 못하고 점수가 0점에 군집(Clustering)**된다 [Lin et al., 2009].
  * *비교*: FMA-UE는 물체 없이도 반사 반응이나 굴곡 시너지를 평가하므로 초기 회복 변화를 감지할 수 있는 반면, ARAT는 초기 변화에 극도로 둔감하다.
* **만성기/경증 환자에서의 천장 효과 (Ceiling Effect)**:
  * 경증 환자는 손의 미세 기민성(Dexterity)이나 근력 저하가 남아있음에도 불구하고, 대충 5초 안에 과제를 완수하여 **57점 만점에 도달하는 현상(Ceiling effect)**이 빈번히 발생한다 [Kristersson et al., 2019].
  * 실제 일상생활 복귀 시 환자가 느끼는 피로감, 미세 협응 이상, 속도 저하를 57점 만점 척도로는 변별할 수 없다.

### 4.2 신경학적 회복(True Restitution)과 기능적 보상(Compensation)의 미분리
* **보상적 움직임의 문제**:
  * 환자가 마비된 손가락과 팔꿈치를 제대로 펴지 못하더라도, **몸통을 앞으로 푹 숙이거나(Trunk flexion), 어깨를 과도하게 치켜올려(Shoulder hiking) 외전**시키면 5초 이내에 블록을 선반 위에 올려놓을 수 있다.
* **임상 지침과 현장의 괴리**:
  * Yozbatiran(2008) 지침에는 "등받이에서 떨어지면 2점"이라는 자세 규정이 명시되어 있으나, 실제 바쁜 임상 현장에서는 치료사가 **스톱워치 확인과 물체 낙하 방지에 시선이 집중되어 환자의 미세한 체간 기울임이나 견갑골 보상을 놓치고 3점을 부여**하는 경우가 흔하다.
  * 결과적으로 '진정한 뇌신경 운동 회복(Neural restitution)'과 '보상적 적응(Behavioral compensation)'이 점수 상에서 왜곡되어 혼재된다 [Kwakkel et al., 2019; Valladares et al., 2024].

### 4.3 순서 척도(Ordinal Scale)의 해상도 한계 및 2점↔3점 경계의 주관성
* **연속적 변화 감지 불가**: 0, 1, 2, 3점의 불연속적 4점 척도 구조로 인해 환자의 운동 궤적이 얼마나 부드러워졌는지(Smoothness), 속도가 몇 % 향상되었는지 등의 연속적인 회복 지표를 반영하지 못한다.
* **높은 최소감지변화량 (MDC / MCID)**:
  * ARAT의 측정 오차를 벗어나는 최소 감지 변화량(Minimal Detectable Change, MDC)은 약 **13.1점**에 달하며, 임상적으로 의미 있는 최소 변화량(MCID)은 **5.7~12점**으로 보고된다 [Lin et al., 2009; Lang et al., 2008]. 이는 수 주의 재활 치료 후에도 점수가 1~2점 오르는 데 그쳐 치료 효과를 통계적으로 입증하기 어렵게 만든다.
* **2점과 3점 경계의 모호성**:
  * 5초 컷오프는 스톱워치로 판별되지만, **"수행에 심한 어려움을 겪음(Great difficulty)"**이나 **"비정상적 파지 형태(Abnormal grasp posture)"**는 평가자의 주관적 임상 경험에 전적으로 의존한다. 동일한 환자의 동작을 보고도 치료사마다 2점과 3점 판정이 갈리는 주된 원인이 된다 [van der Lee et al., 2001].

### 4.4 임상 운영 및 물류(Logistics) 상의 한계
* **도구 키트의 복잡성 및 비표준화**:
  * 19개 항목을 위한 블록, 컵, 선반, 구슬 등 수십 개의 소품을 보관·유지 관리해야 한다.
  * 상용화된 공인 키트(예: Rolyan ARAT Kit)는 가격이 고가(수백 달러)여서 많은 병원이 자체 목공소에서 모작 키트를 제작해 사용하는데, 이 과정에서 **블록 모서리 챔퍼(Chamfer), 표면 마찰력(Varnish 도색 여부), 큐브 무게의 오차**가 발생하여 기관 간 데이터 호환성이 떨어진다.
* **치료사 업무 부하**:
  * 환자 1명당 세팅, 설명, 수행, 기록까지 최소 15~30분이 소요되며, 치료사가 1:1로 밀착 감시해야 하므로 임상 인력 소모가 극심하다.

---

## 5. 센서·비전·AI 기반 ARAT 자동화 연구에서의 공학적 기술적 문제점

임상 현장의 수동 평가 한계를 극복하기 위해 컴퓨터 비전과 센서를 도입하려는 시도가 활발하지만, 공학적으로도 해결하기 까진 복잡한 기술적 장벽들이 존재한다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       센서·비전 자동화의 4대 기술적 난제                    │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│ 1. 동적 가림 및 접촉     │ 2. 다중 공간 스케일 차이 │ 3. 시공간 역학 미검출 │
│ - 파지 시 손끝 가림 폭증 │ - 체간(m) vs 손가락(cm)   │ - 정적 프레임 한계    │
│ - 키포인트 ID 스와핑     │ - 단일 FOV 해상도 한계   │ - 힘/가속도/떨림 부재 │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

### 5.1 심각한 동적 가림(Dynamic Occlusion)과 키포인트 붕괴
* **물체에 의한 가림**: 환자가 블록이나 컵을 감싸 쥐는 순간(Grasp phase), 손바닥과 손가락 복측(Palmar surface)이 물체에 완전히 가려진다. 단일 시점 카메라에서는 손가락 끝 랜드마크가 소실되거나 엉뚱한 위치로 튀는 현상(Jitter)이 발생한다.
* **자가 가림 및 키포인트 충돌 (Keypoint Collision & ID Swapping)**:
  * 특히 **Pinch(집기)** 하위검사(구슬 집기 등)에서는 엄지 끝과 검지 끝이 맞닿으면서 두 관절 좌표가 하나의 픽셀 덩어리로 병합(Collapse)되거나, 엄지와 검지의 랜드마크 ID가 뒤바뀌는 스와핑 에러가 빈번하게 발생한다.

### 5.2 근위부(체간)와 원위부(손가락)의 공간적 멀티스케일(Multiscale) 딜레마
* **광각(Wide FOV) vs 고해상도(Zoom)**:
  * 환자의 등받이 접촉 상실(체간 보상)과 어깨 거상을 관찰하려면 카메라 시야각이 상체 전체($1\text{ m} \times 1\text{ m}$)를 포괄해야 한다.
  * 그러나 시야각을 넓히면 $1920 \times 1080$ 해상도에서도 6mm 볼베어링을 쥐는 환자의 손가락 끝 랜드마크 영역은 불과 수십 픽셀(Pixel)에 불과하여, 정밀한 손가락 관절 각도(ROM)나 개구 간격(Aperture)을 정확히 계측하기 불가능해진다.

### 5.3 시공간 역학(Spatiotemporal Dynamics) 및 물리적 접촉력의 결여
* **비전 기반 AI의 한계**:
  * 2D 비디오나 간헐적 프레임을 입력받는 최신 Vision-Language Model(VLM)은 "환자가 손을 뻗어 블록을 잡았다"는 정성적 장면(Semantic action)은 쉽게 인식하지만, **정확히 몇 초에 물체가 테이블에서 떨어졌는지($T_{\text{lift}}$), 몇 초에 선반에 안착했는지($T_{\text{place}}$)와 같은 밀리초 단위의 시간 경계**를 측정하는 능력이 현저히 떨어진다 [Li et al., 2026].
* **물리적 힘과 저항의 부재**:
  * 카메라만으로는 환자가 물체를 얼마나 강하게 쥐고 있는지(Grip-to-load force), 경직으로 인해 뻣뻣하게 쥐고 있는지 등의 역학적 정보를 측정할 수 없다.

---

## 6. 기존 선행 연구 종합 조사 및 분류

ARAT를 둘러싼 기존 연구들은 (1) 임상 타당도 검증, (2) 생체역학 운동학 규명, (3) 웨어러블/글러브 정량화, (4) 비전/카메라 자동화, (5) AI/VLM 채점 모델로 진화해 왔다.

```
[ARAT 연구의 역사적 발전 계보]
  [1981] Lyle: ARAT 원형 개발 (19항목, 4소검사)
    │
  [2001] van der Lee et al.: 평가자 간/내 신뢰도 및 Guttman 구조 검증
    │
  [2008] Yozbatiran et al.: 프로토콜 표준화 (5초 컷오프, 키트 규격, 등받이 기준 확립)
    │
  [2012] Alt Murphy et al.: 모션캡처 운동학 분석 (ARAT vs FMA 상관성 r=.81 입증)
    │
  [2019] Kwakkel et al. (SRRR 합의): 상지 움직임 질 평가의 체간 보상 측정 표준화 권고
    │
  [2022] Padilla-Magaña et al.: 데이터 글러브를 이용한 ARAT 16개 과제 수지 운동학 정량화
    │
  [2026] Unger et al. (arXiv): 임상 루틴 내 3개 마커리스 웹캠 도입 (1,174 trial 자동분류)
  [2026] Li, Schambra et al. (PLOS Digit Health): VLM의 뇌졸중 재활 채점 한계 및 교훈 규명
  [2026] Ahmed & Rikakis (arXiv, xAARA): 다중시점 불확실성 인지 전문가 융합 및 보류 프레임워크
```

### 6.1 핵심 선행 연구 요약 매트릭스

| 연구 (연도) | 연구 대상 및 장비 | 주요 방법론 | 핵심 발견 및 임상적/공학적 의의 | 한계 및 남겨진 과제 |
| :--- | :--- | :--- | :--- | :--- |
| **Lyle**<br>(1981) [1] | 뇌손상 환자<br>(물리 키트) | 19항목 4점 척도 개발, Guttman 계층 척도화 제안 | ARAT의 최초 정립. 빠른 임상 선별 평가의 기틀 마련. | 세부 치수 및 자세 보상에 대한 표준 매뉴얼 미흡. |
| **van der Lee et al.**<br>(2001) [2] | 만성 뇌졸중 22명<br>(물리 키트) | 검사자 간(Inter-rater) 및 검사자 내(Intra-rater) 신뢰도 평가 | ICC > 0.98로 매우 높은 신뢰도 입증. Guttman 척도화의 유효성 검증. | 2점과 3점 사이의 미세 채점 불일치 존재 확인. |
| **Yozbatiran et al.**<br>(2008) [3] | 만성 뇌졸중 36명, 건측/환측<br>(표준 키트) | 사진과 세부 치수가 포함된 표준화 매뉴얼 수립 | **현재 전 세계 표준 프로토콜 확립**. 5초 시간 상한 및 등받이 접촉 규칙 공식화. | 물리 키트의 복잡성과 수동 평가의 시간 소요 잔존. |
| **Lin et al.**<br>(2009) [4] | 뇌졸중 57명<br>(임상 비교) | FMA, ARAT, Wolf(WMFT), FIM 비교 심리측정학 분석 | ARAT의 바닥 효과 및 천장 효과 정량화. **MDC = 13.1점** 산출. | 범주형 점수로 인한 미세 호전 감지 한계 실증. |
| **Alt Murphy et al.**<br>(2012) [5] | 뇌졸중 30명, 건강대조군<br>(광학 모션캡처 5대) | 물 마시기 과제 중 관절각, 움직임 단위(MU), 체간 변위(TD) 분석 | **운동학 지표가 FMA($r=.38\sim.42$)보다 ARAT($r=.81$)와 훨씬 강하게 연동됨 규명**. ARAT 분산의 67%를 운동학이 설명. | 고가의 광학 마커 장비 필요, 일상 임상 적용 불가. |
| **Kwakkel et al.**<br>(2019) [6] | 국제 전문가 패널<br>(SRRR 2차 라운드테이블) | 뇌졸중 상지 움직임 질 측정에 대한 합의 가이드라인 도출 | **체간 보상(Trunk compensation)을 상지 평가에 반드시 결합할 것을 권고**. 회복과 보상 분리 촉구. | 구체적 단일 센서 임상 계측 도구는 미제시. |
| **Padilla-Magaña et al.**<br>(2022) [7] | 뇌졸중 10명, 건강군 10명<br>(CyberGlove 데이터글러브) | ARAT 16개 활동 수행 중 14개 손가락 관절 각도(ROM) 측정 | 건강군 대비 뇌졸중 환자의 MCP/PIP 가동범위 축소 및 수지 간 분리 운동 결함 정량화. | 장갑 착용으로 인한 고유수용감각 저해, 탈착 불편, 높은 비용. |
| **Faity et al.**<br>(2022) [8] | 건강 성인<br>(Kinect v2 심도카메라) | 좌위 도달 운동 중 무마커 체간 및 팔 운동학 타당도 검증 | 저비용 깊이 센서로 체간 변위 측정이 가능함을 입증. | 빠른 움직임에서 모션 블러 및 손가락 계측 불가. |
| **Unger et al.**<br>(2026) [9] | 아급성/만성 뇌졸중<br>(웹캠 3대, 마커리스 비전) | 정규 ARAT 세션에 카메라 삽입 (1,174회 trial), 3D 골격 추정 및 머신러닝 채점 | **완수 vs 실패(Tier 1: 0/1 vs 2/3) 판별에서 AUC 0.91~1.00 달성**. 반면 미세한 2점 vs 3점 구분은 정확도 저하. | 평활도(Smoothness) 지표 제외, 단일 시점 대비 3대 카메라 동기화 부담. |
| **Li, Schambra et al.**<br>(2026) [10] | 뇌졸중 재활 비디오<br>(Vision-Language Model) | VLM의 뇌졸중 상지 재활 동작 이해도 및 임상 채점 능력 평가 | VLM이 전반적 동작은 설명하나, **세밀한 임상 점수 경계 채점에서는 심각한 오류 발생**을 최초로 실증. | VLM 단독 사용 시 정량적 센서 수치 보완 필요성 대두. |
| **Ahmed & Rikakis**<br>(2026) [11] | 뇌졸중 상지 다각도 비디오<br>(xAARA 딥러닝 융합) | 다중 시점 불확실성 인지 전문가 융합 및 저신뢰 예측 보류(Abstention) | 임상 신뢰도 확보를 위해 애매한 경계 사례를 인간 치료사에게 위임하는 보류 전략 도입. | 다중 카메라 환경 필요, 연산 복잡도 높음. |

---

### 6.2 선행 연구들로부터 도출된 핵심 교훈 및 연구 공백(Research Gap)

1. **"ARAT는 손상(FMA)이 아닌 활동(Activity)을 측정하므로, 운동학과 직접적으로 연결된다"**:
   * Alt Murphy(2012)가 증명했듯이 손 기능 운동학 지표를 FMA 총점에 매핑하면 상관이 떨어지지만, 물체를 다루는 ARAT에는 높은 상관을 보인다. 따라서 **동작 분석 및 자동화 모델의 참조 정답(Ground truth)으로 ARAT를 채택하는 것이 생체역학적으로 정당**하다.
2. **"완수 여부(0/1 vs 2/3)는 쉽지만, 질적 정상성(2 vs 3) 판별이 병목이다"**:
   * Unger et al. (2026)의 1,174회 trial 대규모 연구에서 확인된 바와 같이, 컴퓨터 비전이나 기계학습 모델은 물체를 선반에 올렸는지(성공) 여부는 거의 100%에 가깝게 분류하지만, **5초 초과 여부, 미세 떨림, 등받이 접촉 상실(체간 보상)으로 인한 2점 감점은 영상만으로 매우 분별하기 어렵다**.
3. **"VLM/AI 단독으로는 한계가 명확하며, 신뢰도 높은 정량 수치(Kinematics)의 주입이 필수적이다"**:
   * Li et al. (2026)의 연구는 생성형 VLM에게 영상만 보여주고 점수를 매기게 하면 심각한 환각과 일관성 결여가 나타남을 보였다.
   * 이를 해결하기 위해 최근 연구들은 **RGB-D 센서에서 추출한 체간 이동량(TD), 손끝 간격(Aperture), 움직임 평활도(SPARC) 등의 정량적 운동학 수치를 AI 모델에 직접 프롬프트로 제공하고, 품질이 검증된 수치만 선별하여 채점시키는 하이브리드 파이프라인**으로 진화하고 있다.

---

## 7. 비교 분석 매트릭스 및 종합 결론

### 7.1 표준 임상 상지 기능 평가 도구 간 비교

| 비교 항목 | ARAT (Action Research Arm Test) | FMA-UE (Fugl-Meyer Assessment) | BBT (Box and Block Test) | JTHFT (Jebsen-Taylor Hand Test) |
| :--- | :--- | :--- | :--- | :--- |
| **평가 층위 (ICF)** | **활동 제한 (Activity Capacity)** | 신체 기능 손상 (Body Impairment) | 손 기민성 (Manual Dexterity) | 일상 기능 속도 (Functional Dexterity) |
| **측정 대상** | 도달-파지-운반-해제 및 대동작 | 관절별 수의적 분리 운동 및 시너지 | 60초간 블록 이동 개수 | 7가지 일상 과제 완료 시간 (초) |
| **점수 척도** | 0~3점 순서척도 (총 57점 만점) | 0~2점 순서척도 (총 66점 만점) | 분당 개수 (연속 수치) | 각 과제 소요 시간 (초, 연속 수치) |
| **소요 시간** | 10~15분 (Guttman 단축 시) | 30~45분 (매우 길음) | 5~10분 (매우 짧음) | 15~25분 |
| **도구 키트** | 전용 19종 키트 및 2단 선반 | 반사망치, 캔, 공, 연필, 종이 | 칸막이 상자 및 2.5cm 블록 150개 | 숟가락, 카드, 체커말, 캔 등 |
| **체간 보상 고려** | **명시적 반영 (등받이 이탈 시 2점)** | 자세 보상에 대한 프로토콜 편차 심함 | 보상 억제 규정 없음 | 보상 억제 규정 미흡 |
| **운동학 상관성** | **매우 높음 ($r \approx 0.81$)** | 보통 ($r \approx 0.38 \sim 0.42$) | 중간 | 중간 |
| **주요 한계점** | 바닥/천장 효과, 키트 복잡성 | 임상 시간 과다 소모, 물체 조작 배제 | 질적 운동 패턴 미반영 (개수만 카운트) | 평가 도구 규격화 어려움 |

---

### 7.2 자동화 계측 기술별 장단점 비교

| 계측 기술 | 장점 (Strengths) | 한계점 (Limitations) | ARAT 적용 시 적합성 |
| :--- | :--- | :--- | :--- |
| **광학식 모션 캡처**<br>(Vicon, Qualisys) | 밀리미터 이하 초고정밀도, 100Hz+ 샘플링, 신뢰성 최고 | 고가(수천만~억 단위), 마커 부착 시간(20분+), 임상 도입 불가 | 연구실 골드 스탠다드 검증용 |
| **단일 RGB-D 카메라**<br>(Intel RealSense) | 저비용(수십만원), 마커리스, 깊이 맵 기반 3D 체간/손목 궤적 추정 가능 | 단일 시점 가림(Occlusion) 취약, 손가락 끝 키포인트 잡음 | **임상 현장 보급형 자동화에 최적** |
| **웨어러블 데이터 글러브**<br>(Data Gloves) | 손가락 관절 각도(ROM) 정밀 측정, 시각적 가림에 무관 | 센서 탈착 번거로움, 위생 문제, 환자 고유수용감각 방해 | 정밀 수지 생체역학 분석용 |
| **단순 2D 비디오 + VLM**<br>(Vision-Language Model) | 별도 센서 불필요, 자연어 임상 피드백 생성 가능 | 프레임 시간 해상도 부족, 미세 관절각 및 접촉력 인식 오류, 환각 | 고차원 정성 피드백 보조용 |
| **하이브리드 시스템**<br>**(RGB-D 운동학 + VLM)** | **정밀 시공간 수치(시간·체간·평활도)와 비전 문맥 이해의 상호 보완** | 운동학 지표 품질 선별(Gating) 및 전처리 파이프라인 설계 필요 | **차세대 AI 재활 평가의 핵심 지향점** |

---

### 7.3 종합 결론 및 향후 연구 설계에의 시사점

1. **표준 ARAT의 본질 이해**:
   ARAT는 단순한 손가락 움직임 검사가 아니라, **"중력에 대항하여 물체를 목표 위치까지 도달·조작·운반하고 안전하게 내려놓는 전체 상지의 기능적 활동 척도"**이다. 따라서 평가 시 손가락뿐만 아니라 **어깨, 팔꿈치, 그리고 등받이에 지지된 체간(Trunk)의 움직임을 반드시 함께 관찰**해야 한다.
2. **평가 기준의 다면적 구조**:
   점수를 결정하는 핵심 경계는 단순 성공 여부 외에 **(1) 5초 이내 완료 여부**, **(2) 지정된 손가락/패드 사용 여부**, **(3) 몸통의 등받이 접촉 유지 여부**이다. 임상 시험 및 자동화 시스템 구축 시 이 세 가지 요소가 분리되어 판정될 수 있도록 기준을 명문화해야 한다.
3. **공학적 자동화 연구의 올바른 방향**:
   * 전체 19개 항목을 일괄 자동화하려는 시도는 물체 가림과 키포인트 붕괴로 인해 실패하기 쉽다.
   * 대표적인 하위 영역(Grasp, Pinch, Gross movement)에서 비전 관측성이 높고 생체역학적 의미가 뚜렷한 **핵심 과제(예: 5cm 블록, 1.5cm 구슬, 머리 위 손 올리기)**를 선별하여 집중하는 것이 현실적이고 과학적인 접근이다.
   * 영상만을 사용하는 순수 AI 모델의 한계를 극복하기 위해서는 **카메라로부터 신뢰도 높은 운동학 수치(소요 시간, 체간 변위, 손목 평활도 등)를 추출하고, 품질이 검증된 수치만을 엄선하여 AI 추론에 보완 정보로 제공하는 '품질 기반 멀티모달 융합' 전략**이 필수적이다.

---

## 8. 참고문헌 (References)

1. **Lyle, R. C. (1981)**. A performance test for assessment of upper limb function in physical rehabilitation treatment and research. *International Journal of Rehabilitation Research*, 4(4), 483–492. DOI: [10.1097/00004356-198112000-00001](https://doi.org/10.1097/00004356-198112000-00001).
2. **van der Lee, J. H., De Groot, V., Beckerman, H., Wagenaar, R. C., Lankhorst, G. J., & Bouter, L. M. (2001)**. The intra- and interrater reliability of the action research arm test: a practical test of upper extremity function in patients with stroke. *Archives of Physical Medicine and Rehabilitation*, 82(1), 14–19. DOI: [10.1053/apmr.2001.18668](https://doi.org/10.1053/apmr.2001.18668).
3. **Yozbatiran, N., Der-Yeghiaian, L., & Cramer, S. C. (2008)**. A standardized approach to performing the Action Research Arm Test. *Neurorehabilitation and Neural Repair*, 22(1), 78–90. DOI: [10.1177/1545968307305353](https://doi.org/10.1177/1545968307305353).
4. **Lin, J. H., Hsu, M. J., Sheu, C. F., Wu, T. S., Lin, R. T., Chen, C. H., & Hsieh, C. L. (2009)**. Psychometric comparisons of 4 measures for assessing upper-extremity function in people with stroke. *Physical Therapy*, 89(8), 840–850. DOI: [10.2522/ptj.20080285](https://doi.org/10.2522/ptj.20080285).
5. **Alt Murphy, M., Willén, C., & Sunnerhagen, K. S. (2012)**. Movement kinematics during a drinking task are associated with the activity capacity level after stroke. *Neurorehabilitation and Neural Repair*, 26(9), 1106–1115. DOI: [10.1177/1545968312448234](https://doi.org/10.1177/1545968312448234).
6. **Kwakkel, G., Van Wegen, E., Burridge, J. H., Winstein, C. J., van Dokkum, L. E., Alt Murphy, M., ... & Krakauer, J. W. (2019)**. Standardized measurement of quality of upper limb movement after stroke: Consensus-based core recommendations from the Second Stroke Recovery and Rehabilitation Roundtable. *International Journal of Stroke*, 14(8), 783–791. DOI: [10.1177/1747493019873519](https://doi.org/10.1177/1747493019873519).
7. **Padilla-Magaña, J. F., Peña-Pitarch, E., Sánchez-Suarez, I., & Ticó-Falguera, N. (2022)**. Quantitative Assessment of Hand Function in Healthy Subjects and Post-Stroke Patients with the Action Research Arm Test. *Sensors*, 22(10), 3604. DOI: [10.3390/s22103604](https://doi.org/10.3390/s22103604).
8. **Faity, G., Mottet, D., & Froger, J. (2022)**. Validity and Reliability of Kinect v2 for Quantifying Upper Body Kinematics during Seated Reaching. *Sensors*, 22(7), 2735. DOI: [10.3390/s22072735](https://doi.org/10.3390/s22072735).
9. **Unger, T., Lambercy, O., Gassert, R., Luft, A. R., Cotton, R. J., & Easthope Awai, C. (2026)**. Markerless Motion Capture in Routine Clinical Upper Limb Assessments: Validity and Insights Beyond Ordinal Scoring. *arXiv preprint*, arXiv:2607.23608.
10. **Li, V., Kamalakannan, N., Parnandi, A., Schambra, H., & Fernandez-Granda, C. (2026)**. Vision-language models for human motion understanding: Lessons from stroke rehabilitation. *PLOS Digital Health*, 5(7), e0001506. DOI: [10.1371/journal.pdig.0001506](https://doi.org/10.1371/journal.pdig.0001506).
11. **Ahmed, T., & Rikakis, T. (2026)**. Enhancing Clinician Decision-Making via Uncertainty-Aware Multi-Expert Fusion for Stroke Rehabilitation (xAARA). *arXiv preprint*, arXiv:2606.24960.
12. **Kristersson, T., Persson, H. C., & Alt Murphy, M. (2019)**. Evaluation of a short assessment for upper extremity activity capacity early after stroke. *Journal of Rehabilitation Medicine*, 51(4), 257–263. DOI: [10.2340/16501977-2534](https://doi.org/10.2340/16501977-2534).
13. **Valladares, B., Kundert, R. G., Pohl, J., Held, J. P., Luft, A. R., Veerbeek, J. M., & Branscheidt, M. (2024)**. The association between dexterity and upper limb impairment during stroke recovery. *Frontiers in Neurology*, 15, 1429929. DOI: [10.3389/fneur.2024.1429929](https://doi.org/10.3389/fneur.2024.1429929).
14. **Collins, K. C., Kennedy, N. C., Clark, A., & Pomeroy, V. M. (2018)**. Getting a kinematic handle on reach-to-grasp: a meta-analysis. *Physiotherapy*, 104(2), 153–166. DOI: [10.1016/j.physio.2017.10.002](https://doi.org/10.1016/j.physio.2017.10.002).
15. **Lang, C. E., Edwards, D. F., Birkenmeier, R. L., & Dromerick, A. W. (2008)**. Estimating minimal clinically important differences of upper-extremity measures early after stroke. *Archives of Physical Medicine and Rehabilitation*, 89(9), 1693–1700. DOI: [10.1016/j.apmr.2008.02.022](https://doi.org/10.1016/j.apmr.2008.02.022).

# 뇌졸중 편마비 손 기능의 비전·센서 기반 평가 과제 선정

_근거 검토일: 2026-09-18_

## 요약 결론

1. 네 임상도구가 공통으로 포착하는 핵심은 **손 열기·파지 전 형상화 → 파지/집기 → 유지 → 들어 올리기·운반 → 능동적 놓기**이며, 여기에 속도·반복성·손가락 분리운동이 더해진다.
2. Brunnstrom 손 회복단계를 전 범위에서 가르는 단일 파지형은 없다. 단계 판별력은 파지 모양 자체보다 **능동적 손가락 폄과 놓기(release)**에서 더 크게 나온다. 하나의 경계표지자를 고르면 **측면 집기 후 엄지의 능동적 놓기**가 III→IV 전환을 가장 직접적으로 반영한다. V와 VI를 가르려면 원통/구형 파지와 끝 집기·손가락 분리운동을 추가해야 한다.
3. 단일 RGB-D 카메라용 핵심 과제는 **① 맨손 열기–쥐기–다시 열기, ② 측면 집기, ③ 원통형 파지 후 짧은 lift–place–release, ④ 큰 물체 끝 집기 후 이동·놓기**가 적합하다. 반복 속도가 필요하면 **⑤ 칸막이 없는 5-block transfer**를 선택 모듈로 둔다.
4. 현재의 구형 파지는 원통형 파지와 Brunnstrom V 수준에서 중복되고 손가락 가림이 커서 핵심 세트에서는 빼는 편이 낫다. FMA-UE와의 직접 대응이 연구목적이면 보조 모듈로 유지한다.
5. 정적 과제만으로는 임상적 손 기능을 충분히 평가할 수 없다. 다만 동적 과제만 사용하면 어깨·팔꿈치·몸통 보상이 손 기능과 섞인다. 따라서 **전완 지지 상태의 원위부 손상검사**와 **전완 비지지 상태의 reach–grasp–5 cm lift–transport–place–release**를 모두 포함해야 한다.
6. 5 cm lift가 중력·부하 하 수행을 드러내기는 하지만, 이것만으로 “굴곡 시너지”를 직접 측정했다고 말해서는 안 된다. 굴곡 시너지를 결과변수로 삼으려면 지지/비지지 조건을 비교하고 어깨 벌림–팔꿈치 굽힘–손목/손가락 굽힘의 비정상 결합을 함께 계측해야 한다.

---

## 1. 표준 임상 평가도구가 실제로 보는 손 동작

### 1.1 도구별 구성과 측정개념

| 평가도구 | 주된 ICF 구성개념 | 손 관련 과제 | 동적 요소와 점수의 성격 | 센서 시스템 설계에 주는 의미 |
|---|---|---|---|---|
| **FMA-UE Hand** | 신체기능/손상 | 전체 굽힘, 전체 폄, 고리 잡기, 엄지 모음(종이), 손끝 맞섬(연필), 원통형 파지(작은 캔), 구형 파지(테니스공) | 손 소계 14점. 물체를 운반하지 않고 자세 유지·검사자의 당김에 대한 저항을 0–2점으로 평가 | 원위부 선택운동과 파지형을 비교적 분리해 보지만 실제 활동 수행은 거의 반영하지 않음 |
| **ARAT** | 상지 활동 수행 | 크기가 다른 블록, 공, 숫돌의 grasp; 컵·튜브·와셔의 grip; 구슬·볼베어링의 여러 손가락 pinch; gross movement | 19문항/4개 하위영역. 물체를 잡고, 수직으로 들어 선반에 놓고, 능동적으로 놓아야 함. 정상·지연/어려움·부분·불가의 0–3점 | 성공/실패뿐 아니라 잘못된 파지, 비정상 팔 움직임, 몸통 보상, 소요시간을 함께 봐야 함 |
| **Box and Block Test** | 일측성 대동작 손기민성 | 2.5 cm 블록을 한 번에 하나씩 집기 | 60초 동안 칸막이를 넘어 운반한 블록 수 | 반복적 reach–grasp–lift–transport–release와 속도·지구력을 잘 포착하지만 손가락 정밀도는 제한적 |
| **Jebsen–Taylor Hand Function Test** | 모의 ADL 속도 | 문장 쓰기, 카드 뒤집기, 작은 일상물체 집기, 체커 쌓기, 모의 식사, 가벼운 캔과 1 lb 캔 옮기기 | 7개 과제의 완료시간. 질보다 속도를 평가 | 정밀·대동작·도구 사용·부하를 넓게 보지만 인지·학습·근위부 능력과 보상이 점수에 섞임 |

FMA-UE는 2026년 국제 합의 매뉴얼에서도 뇌졸중 운동기능의 핵심 임상 결과도구로 권고되며, 공식 설명상 ICF의 신체기능 수준을 평가한다. 손 항목의 정확한 자세와 물체는 [Gothenburg대 공식 페이지](https://www.gu.se/en/neuroscience-physiology/fugl-meyer-assessment), [공식 한글 FMA-UE 프로토콜](https://www.gu.se/sites/default/files/2021-05/the-korean-version-of-the-fma-upper-extremity-2021-04-30.pdf), [2026 국제 합의 매뉴얼](https://journals.sagepub.com/doi/10.1177/15459683251412300)에 제시돼 있다. ARAT의 표준화 매뉴얼은 단순히 팔을 움직이는 것만으로는 부분점수를 주지 않고, 손으로 물체를 유지하고 들어 올려야 하며, 정상적인 파지·팔 움직임·자세·시간을 함께 평가하도록 규정한다([Yozbatiran et al., 2008](https://journals.sagepub.com/doi/pdf/10.1177/1545968307305353)). BBT와 JTHFT의 표준 구성은 각각 [BBT RehabMeasures](https://www.sralab.org/rehabilitation-measures/box-and-block-test), [JTHFT RehabMeasures](https://www.sralab.org/rehabilitation-measures/jebsen-taylor-hand-function-test)에 정리돼 있다.

### 1.2 네 도구에서 반복되는 공통 동작 원소

| 동작 원소 | FMA-UE Hand | ARAT | BBT | JTHFT | 임상적 의미 |
|---|:---:|:---:|:---:|:---:|---|
| **능동적 손 열기·파지 전 형상화** | 직접 | 필수 | 필수 | 암묵적 | 굴곡 우세를 이겨 물체 크기에 맞춰 손을 여는 능력 |
| **대동작/파워 파지** | 고리·원통·구형 | 블록·공·컵 | 블록 집기 | 큰 캔 옮기기 | 다수 손가락의 협응과 엄지 맞섬 |
| **정밀 집기·엄지 맞섬** | 엄지 모음·손끝 집기 | 측면 집기와 여러 손가락 pinch | 작은 블록 획득에 필요 | 작은 물체·체커·필기 | 선택적 엄지–손가락 조절과 손가락 분리운동 |
| **유지와 부하 안정성** | 검사자의 당김에 저항 | 들어 올려 선반까지 유지 | 반복 운반 | 가벼운/무거운 캔 | 접촉만이 아니라 실제 물체 보유 능력 |
| **들어 올리기·운반·놓기** | 거의 없음 | 핵심 | 핵심 | 다수 과제의 핵심 | 활동 수준의 기능과 손–팔 통합 |
| **능동적 놓기** | 전체 폄에서 직접 확인 | 명시적 채점 요소 | 매 반복에 필요 | 암묵적 | Brunnstrom III 이후 회복, 다음 조작으로 전환하는 능력 |
| **속도·반복성** | Hand 소계에는 없음 | 시간 문턱을 포함한 서열점수 | 60초 개수 | 완료시간 | 기민성, 운동계획, 피로, 반복 간 변동성 |

따라서 네 척도의 공통분모를 한 문장으로 줄이면 **“필요한 만큼 손을 열고, 적절한 파지로 물체를 확보하여, 떨어뜨리지 않고 이동한 뒤, 의도적으로 놓는 능력”**이다. 단, FMA-UE는 이 연쇄를 손상 수준의 부분동작으로 나누고 ARAT·BBT·JTHFT는 활동 전체로 본다. 두 구성개념을 하나의 총점으로 바로 합치면 안 된다.

---

## 2. Brunnstrom 손 회복단계와 파지형의 판별력

### 2.1 단계별 대표 손 동작

| Brunnstrom Hand 단계 | 고전적 임상 특징 | 센서 과제에서 기대되는 관찰 |
|---|---|---|
| **I** | 이완성, 수의적 움직임 없음 | 움직임 개시 없음 또는 극미세 |
| **II** | 손가락 능동 굽힘이 거의 없거나 없음 | 약한 전체 굽힘 시도, 기능적 접촉/유지 불가 |
| **III** | 전체/고리 잡기 가능, 그러나 놓기와 수의적 손가락 폄이 없음 | 물체를 감싸거나 유지할 수 있으나 지시 후에도 손이 열리지 않음; 팔을 뒤로 빼 물체를 놓는 보상 가능 |
| **IV** | 측면 집기, 엄지 움직임으로 놓기; 작은 범위의 반수의적 손가락 폄 | 얇은 물체를 엄지–검지 측면으로 유지하고 엄지를 떼어 놓을 수 있음 |
| **V** | 손바닥 파지, 서툰 원통·구형 파지; 가변 범위의 전체 폄 | 원통/공의 크기에 맞춘 형상화와 물체 유지가 나타나지만 속도·부드러움·손가락 독립성은 제한 |
| **VI** | 모든 파지형을 조절, 전 범위 수의적 폄, 개별 손가락 움직임 | 끝 집기, 특정 손가락 맞섬, 빠른 전환과 정확한 놓기 가능 |

이 단계 기술은 동료심사 논문에 제시된 Brunnstrom 손 단계 정의와 일치한다([Ghaffari et al., 2019](https://link.springer.com/article/10.1016/j.jams.2019.04.004)). FMA-UE 문항난이도 연구에서도 손 문항은 한 난이도에 몰리지 않고 여러 수준에 걸쳐 있었다. 즉, 하나의 파지로 전체 중증도 범위를 재는 것은 구조적으로 불리하다([Hijikata et al., 2020](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2020.577855/full)).

### 2.2 “어떤 파지가 가장 잘 구별하는가?”에 대한 답

**엄밀한 답은 ‘단일 파지는 없다’이다.** Brunnstrom 단계는 다음처럼 서로 다른 동작의 출현으로 정의된다.

- III: 전체/고리 잡기는 되지만 **놓지 못함**
- IV: **측면 집기와 엄지 놓기** 출현
- V: 원통·구형의 손바닥 파지와 전체 폄 출현
- VI: 끝 집기를 포함한 모든 파지와 개별 손가락 조절

따라서 다음처럼 해석하는 것이 가장 타당하다.

- **하나의 단계 경계만 고르면:** 측면 집기 후 능동적 엄지 놓기가 III→IV를 가장 직접적으로 가른다.
- **혼합 중증도 집단을 한 과제로 넓게 선별하면:** 원통형 물체의 파지–유지–능동적 놓기가 시도 가능 범위가 넓지만, V–VI에서는 천장효과가 생긴다.
- **상위 단계 V→VI를 가르면:** 큰 물체의 끝 집기와 비과제 손가락의 독립성이 더 민감하지만 중증 환자에서는 바닥효과가 크다.

실제로 조기 **수의적 손가락 폄**은 이후 ARAT 기능 회복의 강한 예측인자였다. EPOS 코호트에서 뇌졸중 72시간 이내 손가락 폄과 어깨 벌림이 있던 환자는 6개월에 일부 기민성을 회복할 확률이 0.98이었고, 둘 다 없으면 0.25였다([Nijland et al., 2010](https://doi.org/10.1161/STROKEAHA.109.572065)). 따라서 알고리즘도 “물체를 잡았는가”보다 **지시에 따라 손을 다시 열었는가, 어느 손가락이 먼저/얼마나 폈는가, 물체를 팔의 후퇴로 빼낸 것은 아닌가**를 우선 측정해야 한다.

> **권장 최소 단계판별 조합:** 맨손 열기–쥐기–다시 열기 + 측면 집기/엄지 놓기 + 원통형 파지/놓기 + 끝 집기/손가락 분리운동.

Brunnstrom 단계는 임상적으로 유용한 서열범주이지만 모든 환자가 교과서적 순서를 동일하게 보이는 것은 아니다. 카메라의 한 과제로 정확한 단계를 자동 결정했다고 주장하기보다, 임상가가 판정한 Brunnstrom Hand와 FMA-UE Hand를 외부 준거로 두고 각 센서 지표의 판별타당도를 검증해야 한다.

---

## 3. 단일 RGB-D 카메라에 적합한 4개 핵심 과제와 선택 과제

### 3.1 권장 과제

| 우선순위 | 과제와 권장 물체 | 단일 카메라 가림 | 임상적으로 얻는 정보 | 핵심 정량지표 |
|---|---|---|---|---|
| **1** | **맨손 최대 열기 → 전체 쥐기 → 2초 유지 → 다시 열기**, 전완 지지 | 매우 낮음~낮음. 완전 주먹에서 손끝은 일부 가려짐 | 전체 굽힘/폄, 능동적 release, 굴곡 우세, 단계 II–III 포함 넓은 범위 | 최대 손 벌림, 손끝–손바닥 거리, MCP/PIP/DIP 폄 결손, 열기/닫기 시간, 손가락 간 동시성, jerk |
| **2** | **측면 집기 → 5 cm lift → place → 엄지로 능동적 release**. 무광 직육면체/판(대략 80×30×8–10 mm)을 세워 제공 | 낮음. 카메라를 엄지–검지 쪽에서 보면 접촉과 놓기가 잘 보임 | Brunnstrom IV 전환, 엄지 모음·벌림의 선택성, release latency | 엄지–검지 접촉형, 물체 이탈 시점, 엄지 벌림, release latency, slip/drop |
| **3** | **20 cm reach → 원통형 파지 → 5 cm lift → 10–15 cm transport → place → release**. 무광 원통(지름 약 45–60 mm) | 중간. 물체가 손바닥 면을 가리지만 손등 관절과 엄지/검지는 관찰 가능 | 파워 파지, V 단계 수준의 형상화, 부하 중 유지, 손–팔 통합 | MGA/tMGA, grasp/lift latency, 물체 z변위, 운반경로, slip/drop, release 성공, 손목 자세 |
| **4** | **큰 peg/2–2.5 cm cube의 엄지–검지 끝 집기 → lift/이동/놓기**, 물체를 낮은 받침대에 제공 | 낮음~중간. 6 mm 볼베어링보다 영상과 깊이에서 훨씬 안정적 | 엄지 맞섬, V–VI 상위기능, 손가락 분리와 정확도 | 손끝 간 거리, 맞섬 위치, 비과제 손가락 동반 굽힘, 집기 성공, 위치오차, release |
| **5 선택** | **칸막이 없는 5-block transfer** 또는 30초 반복. 두 개의 얕은 목표영역 사용 | 중간. 공식 BBT 칸막이와 블록 더미를 없애 가림 감소 | 반복 기민성, 속도–정확도, 피로와 반복 변동 | 성공 개수, cycle time, 반복 내 CV, drop, 시간에 따른 속도/가동범위 기울기 |

### 3.2 대상 중증도에 따른 분기

- **Brunnstrom I–III 또는 FMA-UE Hand가 매우 낮은 환자:** 4번 끝 집기와 5번 반복 이동은 바닥효과가 크다. 1번을 주평가로 하고, 3번 원통 대신 굵은 무광 손잡이의 전체/고리 잡기와 능동적 놓기 시도를 추가한다.
- **Brunnstrom IV–V:** 1–4번이 가장 많은 정보를 준다.
- **Brunnstrom VI 또는 경도 환자:** 4번과 5번의 속도·손가락 독립성·반복 변동성이 천장효과를 줄인다.

### 3.3 핵심 세트에서 제외하거나 보조 모듈로 둘 과제

- **구형 파지:** 원통형 파지와 단계 V에서 중복되고 공이 손가락의 상당 부분을 가린다. FMA-UE 문항 대응이 목적일 때만 보조로 둔다.
- **6 mm 볼베어링/작은 구슬:** 깊이 경계오차와 손톱·손끝 가림, 중증 환자의 바닥효과가 크다. 알고리즘 개발 단계에서는 20–25 mm 물체가 낫다.
- **공식 BBT 칸막이와 블록 더미:** 임상 BBT를 별도로 시행할 때는 표준을 그대로 지켜야 한다. 비전 과제에서는 칸막이와 더미가 가림을 키우므로 제거할 수 있지만, 이 경우 결과를 “BBT 점수”라고 부르면 안 된다.
- **필기·카드 뒤집기·숟가락 사용:** 기능적으로 중요하지만 아래팔 회전, 도구·손의 상호가림, 인지/학습/문화 영향이 커서 첫 비전 바이오마커 세트에는 비효율적이다.

### 3.4 촬영·센서 배치 원칙

- 카메라는 환측 손의 **손등–엄지 쪽 30–45° 사선**에 두고, 좌우 마비에 따라 세팅을 거울처럼 바꾼다. 엄지–검지 접촉과 손등 관절을 동시에 보이게 하는 것이 핵심이다.
- 물체는 무광, 피부·배경과 색 대비가 큰 재료를 쓰고 투명·검은색·광택 표면은 피한다.
- 측면 집기 물체와 peg는 낮은 받침대/슬롯에 세워 손가락이 테이블에 가리지 않게 한다.
- 시작·목표 받침대 아래에 소형 load cell/접촉센서를 두면 lift, place, release의 실제 사건시점을 자세추정과 독립적으로 얻을 수 있다. 물체 상단의 fiducial도 6-DoF 물체운동과 slip 판정에 유용하다.
- 성공과 질을 분리한다. **성공:** grasp–lift–transport–place–active release 완료, drop 없음. **질:** 관절각, aperture, 매끄러움, 비과제 손가락 동반운동, 손목/팔꿈치/몸통 보상.
- 수정 과제는 공식 ARAT·BBT·JTHFT의 대체검사가 아니다. 별도의 디지털 과제로 명명하고 임상척도와의 수렴타당도 및 알려진 집단 타당도를 검증해야 한다.

---

## 4. 정적 과제만으로 충분한가?

### 결론: 충분하지 않다. 다만 정적 과제도 반드시 남겨야 한다.

| 계층 | 권장 조건 | 측정하는 구성개념 | 빠지면 생기는 문제 |
|---|---|---|---|
| **원위부 손상 계층** | 전완 지지, 맨손 열기–쥐기–다시 열기; 필요 시 정적 측면/원통 유지 | 손가락 선택성, 관절가동범위, 능동적 폄/놓기 | 동적 과제만으로는 어깨·팔꿈치·몸통 보상을 손 기능으로 오인 |
| **기능 활동 계층** | 전완 비지지, reach–grasp–5 cm lift–transport–place–release | 중력 대항, 파지 안정성, 손–팔 통합, 실제 성공/실패 | 정적 과제만으로는 들어 올릴 때의 slip/drop, 운반 중 파지 붕괴, 놓기 실패를 놓침 |
| **시너지 도전 계층(선택)** | 같은 과제를 팔 지지 vs 비지지 조건에서 시행; 어깨·팔꿈치·손목·손가락 동시 기록 | 어깨 벌림 요구 증가에 따른 비정상 굴곡 결합 | 단순 lift의 저하를 근력·통증·운동실조와 구별하기 어려움 |

ARAT는 손으로 물체를 유지하고 실제로 들어 올려야 부분점수를 받을 수 있고, BBT와 JTHFT도 운반 또는 무게 조건을 내장한다. 따라서 활동 수준을 주장하려면 lift/transport가 필요하다. 반면 FMA-UE Hand는 팔꿉 지지를 허용하고 운반이 없으므로 깨끗한 원위부 손상 지표를 제공한다. 두 종류는 경쟁 관계가 아니라 상보적이다.

### 중력 대항과 굴곡 시너지의 구분

뇌졸중 후에는 어깨 벌림 요구가 커질수록 팔꿈치 굽힘과의 비정상 결합이 증가해 도달 작업공간이 줄어든다. Sukal 등의 실험에서 능동적 어깨 벌림 부하가 증가할수록 마비측 도달 작업공간과 팔꿈치 폄이 감소했다([Sukal et al., 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC2827935/)). 또한 굴곡 시너지는 어깨 벌림과 팔꿈치·손목·손가락 굽힘의 결합으로 표현되며, 손을 고립해 검사할 때보다 팔 활동이 포함될 때 더 문제가 된다([Lan et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4729670/)).

그러나 **물체를 5 cm 들었다는 사실만으로 굴곡 시너지를 직접 계측한 것은 아니다.** 다음 조건이 필요하다.

1. 전완이 테이블이나 장치에 닿지 않는 비지지 조건이어야 한다.
2. 어깨 벌림/굽힘, 팔꿈치 폄, 손목·손가락 굽힘을 같은 시간축에서 기록해야 한다.
3. 가능하면 동일 과제의 지지 조건과 비지지 조건 간 성능 저하를 비교한다.
4. 이 조건이 없으면 결과명을 “굴곡 시너지”가 아니라 **부하/중력 조건에서의 수행 저하**로 제한한다.

무거운 물체를 바로 도입하는 것은 권하지 않는다. 중증 환자에서 바닥효과와 낙상·통증 위험을 키우고, 손가락 운동조절보다 근력 요구를 과도하게 반영한다. 먼저 가벼운 표준 질량으로 안전성과 반복성을 확인하고, 부하 반응이 연구목적일 때만 두 번째 질량 조건을 추가하는 편이 낫다.

---

## 5. 현재 시스템에 대한 구체적 권고

현재의 **맨손 열기/닫기 + 원통/구형/측면 집기** 구성이라면 다음처럼 바꾸는 것이 가장 효율적이다.

1. **맨손 열기–닫기–2초 유지–다시 열기:** 유지. 특히 마지막 능동적 다시 열기를 별도 결과로 둔다.
2. **측면 집기:** 유지하되 정적 hold에서 끝내지 말고 5 cm lift–place–active release를 넣는다.
3. **원통형 파지:** 유지하고 20 cm reach 뒤 5 cm lift, 짧은 transport, place, release까지 수행한다.
4. **구형 파지:** 핵심 세트에서는 제거하고 **2–2.5 cm 큰 peg/cube 끝 집기**로 교체한다. FMA 직접 대응 분석이 필요하면 구형은 보조 세트로만 남긴다.
5. **선택:** 5회 block transfer를 추가해 속도·반복 변동·피로를 측정한다.

현재처럼 20 cm 수평 reach–grasp–2초 hold–return만 시행하면 MGA, tMGA, 접근/접촉/유지 단계는 잘 측정할 수 있지만, **물체가 바닥에서 떨어지는지, 운반 중 파지가 유지되는지, 능동적으로 목표에 놓을 수 있는지**는 검증하지 못한다. 적어도 원통형과 한 가지 정밀 집기 과제에는 수직 5 cm lift를 복원하는 것이 좋다.

각 과제는 1회 연습 후 3회 기록하고, 다음 사건을 공통 phase로 저장하는 것을 권한다.

`reach onset → preshape → contact → grasp stabilization → lift onset → transport → placement → active release`

임상가 라벨도 단일 총점보다 다음처럼 나누는 편이 알고리즘 검증에 유리하다.

- **과제 달성:** 접촉, 유지, lift, transport, place, 능동적 release의 단계별 성공
- **원위부 질:** 손가락 폄, 엄지 맞섬, aperture, 개별 손가락 선택성, slip
- **근위부/보상:** 어깨 벌림, 팔꿈치 굽힘, 손목 자세, 몸통 이동
- **시간·안정성:** phase별 시간, 매끄러움, 반복 간 변동, 피로 기울기

초기에는 이 지표들을 하나의 새 총점으로 합치지 말고 각각 보고해야 한다. 이후 충분한 뇌졸중 표본에서 임상척도와의 상관, 단계 간 판별, 검사–재검사 신뢰도, 최소검출변화가 확보된 뒤 가중 총점을 개발하는 것이 타당하다.

---

## 참고문헌·근거 링크

1. Hervé-Colas J, et al. [Standardized International Manual of the Fugl-Meyer Assessment of Motor Function After Stroke](https://journals.sagepub.com/doi/10.1177/15459683251412300). Neurorehabil Neural Repair. 2026.
2. University of Gothenburg. [Fugl-Meyer Assessment 공식 자료실](https://www.gu.se/en/neuroscience-physiology/fugl-meyer-assessment).
3. Kim TL, et al. [공식 한글판 FMA-UE 프로토콜](https://www.gu.se/sites/default/files/2021-05/the-korean-version-of-the-fma-upper-extremity-2021-04-30.pdf).
4. Yozbatiran N, et al. [A Standardized Approach to Performing the Action Research Arm Test](https://journals.sagepub.com/doi/pdf/10.1177/1545968307305353). Neurorehabil Neural Repair. 2008.
5. Shirley Ryan AbilityLab. [Box and Block Test](https://www.sralab.org/rehabilitation-measures/box-and-block-test).
6. Shirley Ryan AbilityLab. [Jebsen–Taylor Hand Function Test](https://www.sralab.org/rehabilitation-measures/jebsen-taylor-hand-function-test).
7. Ghaffari MS, et al. [Concurrent Effects of Dry Needling and Electrical Stimulation in the Management of Upper Extremity Hemiparesis](https://link.springer.com/article/10.1016/j.jams.2019.04.004). 2019.
8. Hijikata N, et al. [Item Difficulty of Fugl-Meyer Assessment for Upper Extremity in Persons With Chronic Stroke With Moderate-to-Severe Upper Limb Impairment](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2020.577855/full). Front Neurol. 2020.
9. Nijland RHM, et al. [Presence of Finger Extension and Shoulder Abduction Within 72 Hours After Stroke Predicts Functional Recovery](https://doi.org/10.1161/STROKEAHA.109.572065). Stroke. 2010.
10. Sukal TM, et al. [Shoulder abduction-induced reductions in reaching work area following hemiparetic stroke](https://pmc.ncbi.nlm.nih.gov/articles/PMC2827935/). Exp Brain Res. 2007.
11. Lan Y, et al. [Impact of Shoulder Abduction Loading on Brain-Machine Interface in Predicting Hand Opening and Grasping](https://pmc.ncbi.nlm.nih.gov/articles/PMC4729670/). Neurorehabil Neural Repair. 2015.


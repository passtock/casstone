# 문헌 인용 식별자 검증 보고서 (Citation Provenance Audit)

**작성일:** 2026-09-25
**작성자:** Feynman (자동 감사 + 수동 판정)
**범위:** 워크스페이스 내 Markdown 142개 파일 (`.git`, `open-science-seeds`, `.feynman` 캐시 제외)
**목적:** 문서에 적힌 PMID / PMCID / DOI / arXiv ID가 **실제로 존재하는 레코드**를 가리키는지, 그리고 그 레코드가 **문서가 주장하는 논문과 같은지** 확인하고 교정한다.

**재현 스크립트:** `experiments/provenance_audit.py`
**원자료:** `outputs/03-검증/provenance/verification-results.json`, `_unique_ids.json`, `_contexts.json`

---

## 0. 결론 (먼저)

| # | 질문 | 답 |
|---|---|---|
| 1 | **증거맵 2종(논문 40편·43편)의 인용이 깨져 있는가?** | **아니다. 0건.** PMID·DOI·arXiv ID 전부 실존하며 서지도 실제 레코드와 일치한다 |
| 2 | **정본 연구계획서(`research-plan-v6.md`, 출처 85개)는?** | **깨진 인용 0건.** 47 PMID + 32 DOI + 16 arXiv 전부 실존 |
| 3 | **워크스페이스 전체에서 깨진 인용은?** | **8개 파일에서 결함 25건** (교정 16 · 미검증 10 · 보완 2). **전부 `capstone/` 분석보고서와 `ARAT_논문조사_종합보고서.md`, 그리고 `systematic-search-novelty-audit.md`에 집중되어 있다** |
| 4 | **가장 심각한 유형은?** | **오귀속(misattribution)** — DOI가 존재하지만 **전혀 다른 논문**(토양 수분 측정기, 아테롬성 동맥경화, 두경부암 방사선량, 우울증 분류 등)을 가리킨다. 눈으로는 안 보인다 |

> **핵심 메시지:** 가장 최근에 만든 자료(증거맵·연구계획서)는 깨끗하다. 문제는 **중간 산출물인 `capstone/` 분석보고서**에 있다. 그 보고서들은 결론 자체가 아니라 **근거 목록에 가짜 문헌을 달고 있으므로**, 논문·보고서에 재인용하기 전에 반드시 원문을 다시 확인해야 한다.

---

## 1. 방법

### 1.1 검증 규칙

| 식별자 | 1차 출처 | 2차 확인 | "존재" 판정 기준 |
|---|---|---|---|
| **PMID** | PubMed E-utilities `esummary` | — | 레코드 반환 + `error` 필드 없음 |
| **PMCID** | PubMed E-utilities `db=pmc` | — | 동일 |
| **DOI** | Crossref `api.crossref.org/works/{doi}` | **doi.org handle API** (DataCite·중국 DOI기관 대응) | Crossref 200 **또는** handle `responseCode=1` |
| **arXiv** | arXiv export API `id_list` | — | `<entry>` 존재 |

**존재 판정 방법을 실측으로 교정한 기록:** 등록된 DOI(`10.1186/s12984-021-00895-3`)는 doi.org handle API가 **HTTP 200 / responseCode 1**을 반환하고, 미등록 DOI(`10.1186/s12984-023-01198-4`)는 **HTTP 404**를 반환함을 직접 확인했다. 즉 아래 "미등록" 판정은 API 장애가 아니라 실제 미등록이다.

### 1.2 귀속(attribution) 검증

존재 확인만으로는 부족하다. 문서가 말하는 논문과 실제 레코드가 같은지 보기 위해:

1. 문서의 참조 줄에서 저자·연도·제목·학술지를 정규식으로 파싱
2. 실제 레코드의 `title`과 정규화 후 `difflib.SequenceMatcher` 유사도 계산
3. **제목·저자·학술지·권·페이지 중 하나라도 불일치**하면 후보로 올리고, 제목으로 Crossref/PubMed 역검색해 "다른 DOI로 실존"인지 "논문 자체가 없음"인지 판정

### 1.3 커버리지

| 항목 | 값 |
|---|---|
| 스캔한 Markdown 파일 | **142** |
| 식별자를 1개 이상 포함한 파일 | **38** (주요 8개 파일로 결함 집중) |
| 고유 **DOI** | **202** |
| 고유 **PMID** | **47** |
| 고유 **PMCID** | **15** |
| 고유 **arXiv ID** | **66** |
| **PMID·PMCID·arXiv 미존재** | **0건** (128개 전부 실존) ✅ |

> **주목:** PMID·PMCID·arXiv는 **단 하나도 가짜가 없었다.** 결함은 **DOI에만** 집중됐다. DOI는 형식이 자유로워 그럴듯한 문자열을 만들기 쉽기 때문으로 보인다.

---

## 2. 교정한 결함 16건 (검증된 대체 레코드 존재)

각 항목은 **잘못된 DOI** → **실제 DOI**(제목·학술지·권·페이지까지 확인)로 교체했다. 문서에는 `⚠️ [PROV-AUDIT 2026-09-25]` 주석으로 교정 이력을 남겼다.

| # | 파일 | 문서가 주장한 논문 | 잘못된 DOI | **교정 DOI** | 실제 레코드 |
|---|---|---|---|---|---|
| 1 | `capstone/2-b` | Balasubramanian 2012 (SPARC) | `10.1109/TBME.2012.2198083` | **`10.1109/TBME.2011.2179545`** | IEEE TBME 59(8):2126-2136, PMID 22180502 |
| 2 | `capstone/2-a` | Dewald 2001 | `10.1310/TC87-8328-9844-4638` | **`10.1310/WA7K-NGDF-NHKK-JAGD`** | Top Stroke Rehabil 8(1):1-12, PMID 14523747 |
| 3 | `capstone/1-a` | Page 2012 (MCID) | `10.2522/ptj.20110008` | **`10.2522/ptj.20110009`** | Phys Ther 92(6):791-798, PMID 22282773 (제목도 "Fugl-Meyer **Scale** in people with minimal to moderate impairment"로 교정) |
| 4 | `ARAT_논문조사_종합보고서.md` | Weikert 2025 | `10.1109/ICORR60564.2025` | **`10.1109/ICORR66766.2025.11063162`** | ICORR 2025:1239-1244, PMID 40644012 |
| 5 | `capstone/2-b` | PrimSeq (Parnandi 2022) | `10.1109/TNSRE.2022.3213076` | **`10.1371/journal.pdig.0000044`** | **PLOS Digit Health 1(6):e0000044**, PMID 36420347 (학술지·권·페이지 전부 오류였음) |
| 6 | `capstone/2-b` | Qiu 2022 | `10.3389/fresc.2022.856012` | **`10.1109/EMBC48229.2022.9871891`** | **IEEE EMBC 2022:5107-5110**, PMID 36086392 (Frontiers는 오귀속) |
| 7 | `ARAT_논문조사_종합보고서.md` | "FOCUS" 편 | `10.1161/STROKEAHA.121.034537` | **`10.1161/STROKEAHA.121.035170`** | **Jordan HT, Che J, Byblow WD, Stinear CM (2022)** Stroke 53(2):578-585, PMID 34601902 (저자·연도·권·페이지 전부 오류) |
| 8 | `capstone/1-a` | Kurillo 2022 | `10.1109/TIM.2022.3168924` | **`10.3390/s22072469`** | Sensors 22(7):2469 "Evaluating the Accuracy of the Azure Kinect and Kinect v2" (저자 4인은 실존, 제목·학술지·DOI가 조작됨) |
| 9 | `capstone/1-a`, `1-b` | Amprimo 2024 | `10.1109/TNSRE.2024.3365821` | **`10.1016/j.bspc.2024.106508`** | Biomed Signal Process Control 96:106508 "Hand tracking for clinical applications: Validation of the Google MediaPipe Hand (GMH)…" |
| 10 | `capstone/1-a` | Albert 2020 | `10.3390/s20247175` → **「차량 탑재 토양 질감 측정기」** | **`10.3390/s20185104`** | Sensors 20(18):5104 |
| 11 | `capstone/1-a` | Whyte 2015 | `10.1016/j.compind.2014.12.007` → 「클라우드 프레임워크 검증」 | **`10.1109/ICSENS.2014.6985077`** | IEEE SENSORS 2014 (연도 2014로 교정) |
| 12 | `ARAT_논문조사_종합보고서.md` | "§2.2 Pérez-Pérez 2022" | `10.3390/s22228806` → **「다중위성 릴레이 트래픽 최적화」** | **`10.3390/s22239078`** | **Padilla-Magaña JF & Peña-Pitarch E** Sensors 22(23):9078, PMID 36501779 (저자 목록 자체가 조작됨) |
| 13 | `ARAT_논문조사_종합보고서.md` | Qiu 2022 EMBC | `…9871453` → 「양극성/우울증 분류」 | **`…9871891`** | 숫자 전위(transposition) 오타 |
| 14 | `capstone/2-a` | Lang 2009 | `10.1161/STROKEAHA.108.542944` → 「뇌졸중 사회경제적 격차」 | **`10.1016/j.apmr.2008.02.022`** | Arch Phys Med Rehabil 89(9):1693-1700, PMID 18760153 (연도 2008로 교정) |
| 15 | `capstone/2-a` | Stinear PREP2 | `10.1093/brain/awx224` → 「알츠하이머 뇌네트워크」 | **`10.1002/acn3.488`** | Ann Clin Transl Neurol 4(11):811-820, PMID 29159193 (저자 목록도 교정) |
| 16 | `capstone/2-b` | Balasubramanian 2015 | `10.3389/fnhum.2015.00112` → **「EEVEE: 공감 가상환경」** | **`10.1186/s12984-015-0090-9`** | J NeuroEng Rehabil 12:112, PMID 26651329 (Frontiers는 오귀속) |

**→ 16건 중 8건은 "DOI가 존재하지만 다른 논문"이었다.** 이 유형은 링크를 눌러도 열리기 때문에 자동 검사 없이는 발견되지 않는다.

---

## 3. 미검증 10건 (대응 레코드를 찾지 못함)

**이 항목들은 삭제하지 않았다.** 대신 `⚠️ [PROV-AUDIT 2026-09-25] 미검증` 주석을 달고 원문을 보존했다. **대체 출처를 임의로 만들어 넣는 것이 더 위험**하기 때문이다.

| # | 파일 | 문서가 주장한 논문 | 문제 | 판정 |
|---|---|---|---|---|
| 1 | `capstone/1-a` | Carfì, Motolese, Mastrogiovanni (2020) RealSense D415/D435 성능평가, Sensors 20(8):2445 | `10.3390/s20082445` **미등록** | 제목·저자 조합 레코드 없음 → **인용 철회 필요** |
| 2 | `capstone/1-a`, `1-b` | Smeraldi, D'Amico, Ronchetti (2023) JNER 20(1):84 | `10.1186/s12984-023-01198-4` **미등록**. PubMed 저자검색 0건 | **저자·논문 모두 실존 확인 불가** |
| 3 | `capstone/1-a`, `1-b` | Schoffelen, Visser, Kwakkel (2021) Clin Biomech 84:105322 | DOI가 **「비만/비만 아님에서의 soleus H-reflex」**를 가리킴 | 해당 논문 레코드 없음 |
| 4 | `capstone/1-a`, `1-b` | Metcalf 등 (2014) J Biomech 47(4):842-848 | DOI가 **「아테롬성 동맥경화 플라크 역학」**을 가리킴 | 해당 논문 레코드 없음 |
| 5 | `capstone/1-a` | Kobsar 등 (2020) Front Bioeng 8:567842 | DOI가 **「심장 패치용 나노섬유」**를 가리킴 | 해당 권고안 논문 레코드 없음 |
| 6 | `capstone/3-a`, `3-b` | Wang, Chen, Liu (2024) MedIA 92:103045 | DOI가 **「두경부암 방사선량 예측」**을 가리킴 | 해당 논문 레코드 없음 |
| 7 | `capstone/3-b` | Amjad, Khan, Rossi (2024) TNSRE 32:2145-2156 | `10.1109/TNSRE.2024.3412089` **미등록** | 저자검색 0건 |
| 8 | `capstone/1-a` | Reynolds 등 (2011) ICCV, flying pixels | **DOI 없음** | 확인 불가 |
| 9 | `capstone/3-a`, `3-b` | Tang, Zhang, Li (2025) TPAMI "Can VLMs accurately perceive fine-grained physical quantities?" | **DOI·PMID 없음** | 확인 불가 |
| 10 | `capstone/3-a`, `3-b` | Li, Wang, Zhou (2026) "…multi-center pilot study", JNER In Press | **DOI 없음**, 학술지 "A / B" 병기 | 확인 불가. **`Li V 등 2026 PLOS Digit Health 5(7):e0001506 (PMID 42406872)`로 교체 권장** |

### 3.1 철회 + 대체 문헌 적용 결과 (2026-09-25, 2차 조치)

미검증 10건을 **삭제하지 않고 철회 표시**하고, **레코드가 검증된 대체 문헌**을 붙였다. 파일별 결과:

| 파일 | 철회 | 대체 문헌 |
|---|---|---|
| `capstone/1-a` | 5 | Servi 2024 (IEEE Access) · Hesse 2024 (JTEHM) · Manzone 2026 (arXiv:2606.17427) · Wang Z 2024 (Clin Rehabil) · Scataglini 2024 (Sensors) |
| `capstone/1-b` | 3 | Hesse 2024 · Manzone 2026 · Wang Z 2024 |
| `capstone/3-a` | 3 | Golkar 2023 (arXiv:2310.02989, 후보) · Tang J 2025 (arXiv:2505.18412) · Li V 2026 (PLOS Digit Health, PMID 42406872) |
| `capstone/3-b` | 4 | Tang J 2025 · Li V 2026 · BiomechGPT (arXiv:2505.18465) · Golkar 2023 (후보) |
| **합계** | **15** | **13개 고유 식별자** (전부 Crossref/arXiv에서 레코드 존재 확인) |

**⚠️ 대체 문헌의 지위를 정직하게 밝힌다:** 대체 문헌은 **주제 근접도**로 선정했으며, **원래 주장을 직접 지지하는지는 내가 초록·본문을 읽고 확인하지 않았다.** 그래서 문서마다 "미확인" 경고를 달아 두었다. **지도교수에게 보내기 전에 각 대체 문헌의 초록을 확인해야 한다.**

### 3.2 🔴 가짜 인용이 본문 논증까지 오염시킨 사례 (발견)

단순한 참고문헌 목록 문제가 아니다. **본문이 가짜 문헌을 실험 근거로 인용하고 있었다.**

| 위치 | 내용 | 조치 |
|---|---|---|
| `capstone/1-b` §2.1 | 절 제목부터 `(Schoffelen et al., 2021; Smeraldi et al., 2023)` | 절 머리에 경고 블록 삽입 |
| `capstone/1-b` 실패모드 표 | `Landmark Collapse`, `High-freq Jitter` 등에 `10~20%`, `15~25%`, `30~50%` 수치를 가짜 논문의 "실험 데이터"로 귀속 | 출처 주석을 **"근거 없는 추정치"** 로 교체 |
| `capstone/1-b` §3 | `MCP 600~800°/s (Metcalf et al., 2014)` — 각속도 이상치 판정 임계값의 근거 | 인라인 경고 삽입 (임계값 재확보 필요) |
| `capstone/3-b` §2 표 | 4개 행 전부가 가짜 문헌이며 `+12.4%p`, `38% 감소`, `+31.8%p` 같은 **정량 효과**를 보고 | 표 직전에 **철회 경고** 삽입 |
| `capstone/3-a` §2 | `(Li et al., 2026 예비 결과 참조)` — 본문 제로샷 성능 추정치의 근거 | 인라인 경고 삽입 |

> **이 항목들이 가장 위험하다.** 참고문헌 목록은 독자가 대개 무시하지만, **본문의 숫자는 인용된다.** 위 5곳의 수치는 **출처가 없으므로 쓰면 안 된다.**

---

## 4. 보완 2건 (식별자가 `…`로 생략되어 있던 곳)

`outputs/03-검증/systematic-search-novelty-audit.md`의 표에 `doi 10.1109/…`, `doi 10.1016/j.…`로 **말줄임**만 남아 있던 항목을 실제 식별자로 복원했다.

| 위치 | 문서 표기 | 복원한 식별자 | 실제 레코드 |
|---|---|---|---|
| `systematic-search-novelty-audit.md` L96 | `doi 10.1109/…` | **`10.1109/MET59151.2023.00012`** | 2023 IEEE/ACM 8th Int. Workshop on Metamorphic Testing (arXiv:2303.04566과 동일 논문) |
| `systematic-search-novelty-audit.md` L119 | `doi 10.1016/j.…` | **`10.1016/j.ipemt.2022.100004`** | IPEM-Translation 2022. 정식 제목은 "…an **artificial intelligence**-enabled medical device" |

---

## 5. 수정하지 않은 것 / 수정한 것의 경계

| 구분 | 처리 |
|---|---|
| **DOI·서지 교정 16건** | 문서 본문에서 직접 교체 + 교정 이력 주석 |
| **미검증 10건** | 원문 유지 + 경고 주석. **삭제하지 않음** |
| **증거맵·연구계획서·프로토콜** | **변경 없음** (결함 0건이었으므로 건드리지 않음) |
| **`capstone/05`·`06`, 실제 데이터·코드** | **변경 없음** (인용 목록 없음) |
| **참고문헌 섹션 헤더 경고문** | 결함이 있는 6개 파일의 References 앞에 감사 결과 요약 삽입 |
| **사용자의 해설·주장 문장** | **변경하지 않음.** 단 `capstone/2-a` Lang 2009의 해설이 논문 내용과 다른 점은 주석으로만 표시 |

---

## 6. 재현 방법

```bash
cd "C:/Users/passp/OneDrive/바탕 화면/jeayong"

# 1) 식별자 + 문맥 추출
python experiments/provenance_audit.py extract

# 2) 외부 API 대조 (네트워크 필요, 약 2~4분)
python experiments/provenance_audit.py verify

# 3) 불일치 목록 출력
python experiments/provenance_audit.py report
```

산출물:

```
outputs/03-검증/provenance/
├── _extracted.json            파일별 식별자
├── _contexts.json             파일:줄:문맥 (원문 추적용)
├── _unique_ids.json           고유 식별자 4종
├── verification-results.json  식별자별 외부 레코드 (제목·연도·학술지·저자)
└── citation-verification-report.md   ← 이 문서
```

---

## 7. 한계 (정직하게)

1. **"실존"은 "내용이 옳다"가 아니다.** 이 감사는 식별자와 서지가 맞는지만 본다. 문서가 논문의 수치를 정확히 인용했는지는 **별도 감사 대상**이다.
2. **Crossref 미등록 ≠ 가짜.** 실제로 `10.3969/j.issn.0253-9802.2024.06.001`(중국 DOI기관)은 Crossref에 없지만 OpenAlex에서 실존이 확인됐다. 이런 건 "결함"으로 세지 않았다.
3. **DOI 귀속 검사는 제목 유사도 기반**이다. 문서가 제목을 의역한 경우 오탐이 생긴다(예: `research-plan-v6.md`의 Qiu 2022 항목은 정확한데 유사도가 낮게 나왔다). 그래서 **자동 플래그를 그대로 보고하지 않고 전부 수동 판정**했다.
4. **표본이 아니라 워크스페이스 전체를 스캔**했으나, 산문 안에 DOI 없이 저자·연도만 적힌 인용은 탐지 대상이 아니다. `capstone/03_연구계획_및_정리노트/*`의 여러 파일이 이 경우다.
5. **원문 PDF 대조는 하지 않았다.** 확보한 `capstone/01_참고자료_및_논문`의 PDF와 대조하면 더 강한 검증이 된다(미실시).

---

## 8. 권고 (우선순위)

| # | 조치 | 이유 |
|---|---|---|
| **1** | **`capstone/` 5개 분석보고서를 외부(지도교수·공저자)에게 보내지 말 것.** 미검증 10건의 인용을 철회하거나 실제 출처로 교체하기 전까지 근거 문서로 사용 금지 | 가짜 문헌에 기반한 설계 정당화가 섞여 있다 |
| **2** | **미검증 7건을 실제 문헌으로 대체하거나 삭제.** 특히 `Amprimo 2024`, `Metcalf 2014`, `Kobsar 2020`, `Schoffelen 2021`은 **1-a/1-b의 "무마커 신뢰도" 논증의 핵심 근거**였다 | 해당 논증의 실제 근거를 다시 세워야 한다 |
| **3** | **`3-a`/`3-b`의 3건(Tang 2025, Li 2026, Wang 2024)은 대체 가능** → Li V 등 2026(PLOS Digit Health, PMID 42406872), Tang J 등 2025(arXiv:2505.18412)로 교체 | 이미 증거맵에 검증된 동일 계열 문헌이 있다 |
| **4** | `ARAT_논문조사_종합보고서.md`의 "FOCUS" 편은 **저자가 van Hoonhorst → Jordan으로 바뀌므로**, §1.2~의 배경 서술이 Jordan 2022 원문과 맞는지 재확인 | 인용 대상 논문 자체가 교체됨 |
| **5** | **앞으로 문헌을 추가할 때는 `experiments/provenance_audit.py`를 돌릴 것** | 이번 결함은 전부 "그럴듯한 DOI 생성"에서 나왔다 |
| **6** | 인용 규칙을 **"DOI + PMID 병기"**로 고정 | DOI만 있으면 오귀속을 못 잡지만, PMID가 있으면 PubMed에서 바로 교차확인된다 |

---

## 9. 이번 감사에서 확인된 "정상" 자산 (변경 없음)

| 자산 | 규모 | 검증 결과 |
|---|---|---|
| `outputs/01-조사문헌/arat-fma-ue-evidence-map.md` | 논문 40편 | PMID 21 · DOI 37 · arXiv 5 — **전부 실존, 서지 일치** |
| `outputs/01-조사문헌/rgbd-grasp-vlm-protocol-analysis.md` | 논문 43편 | PMID 22 · PMCID 1 · DOI 39 · arXiv 7 — **전부 실존, 서지 일치** |
| `outputs/research-plan-v6.md` | 출처 85개 | PMID 32 · DOI 32 · arXiv 16 — **전부 실존** |
| `ARAT_논문조사_종합보고서.md` | 참조 17개 | 깨진 DOI 2건 + 오귀속 2건 → **교정 완료** (나머지 13건 정상) |

---

## Sources

**검증에 사용한 1차 데이터베이스·API**

- PubMed E-utilities (esummary / esearch) — https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- Crossref REST API — https://api.crossref.org/works
- arXiv API — https://export.arxiv.org/api/query
- OpenAlex API — https://api.openalex.org/works
- DOI Handle System API — https://doi.org/api/handles/

**교정에 사용한 실제 레코드 (DOI별)**

- `10.1109/TBME.2011.2179545` · `10.1310/WA7K-NGDF-NHKK-JAGD` · `10.2522/ptj.20110009`
- `10.1109/ICORR66766.2025.11063162` · `10.1371/journal.pdig.0000044` · `10.1109/EMBC48229.2022.9871891`
- `10.1161/STROKEAHA.121.035170` · `10.3390/s22072469` · `10.1016/j.bspc.2024.106508`
- `10.3390/s20185104` · `10.1109/ICSENS.2014.6985077` · `10.3390/s22239078`
- `10.1016/j.apmr.2008.02.022` · `10.1002/acn3.488` · `10.1186/s12984-015-0090-9`
- `10.1109/MET59151.2023.00012` · `10.1016/j.ipemt.2022.100004`

**연관 산출물**

- `outputs/03-검증/provenance/verification-results.json` (원자료)
- `experiments/provenance_audit.py` (재현 스크립트)

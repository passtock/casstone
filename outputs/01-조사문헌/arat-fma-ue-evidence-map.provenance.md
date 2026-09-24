# Provenance: ARAT 및 FMA-UE 상지기능 자동화 증거 맵

- **Date:** 2026-09-22
- **Version:** v2 상세 확장본 (방법·관찰·결과·해석·우리 연구 연관성 5단 구조)
- **Rounds:** 5 evidence-gathering rounds + 1 verification pass + 1 expansion pass
- **Sources consulted:** 90+ web pages, database records, abstracts, HTML full texts, publisher figures pages, and arXiv records across PubMed, Europe PMC, arXiv, MDPI, PLOS, Nature, Springer, Frontiers, and web search
- **Sources accepted:** 43 sources in the cited bibliography; 8 primary read/reproduce priorities
- **Sources added in v2:** Padilla-Magaña 2022 ×3 (ARAT 데이터장갑 / 다중센서 / 분류모델), Xing 2025 LLM-FMS, Tannús 2026 npj Digit Med, Li et al. 2026 PLOS Digital Health (동료심사본)
- **Sources rejected or downgraded:**
  - Unrelated TAPV search collisions (medical supplies/vehicle meanings)
  - PDF-only or JavaScript-blocked routes when equivalent metadata/HTML was available
  - Three-view ARAT preprint downgraded because it binarized scores 2 vs 3 and did not establish patient-disjoint splitting in accessible text
  - Exact per-metric Pearson r values for Qiu et al. 2022 omitted because official accessible HTML/metadata did not expose them
  - Li et al. VLM 연구의 arXiv판(대조군 29명, ±25%)과 동료심사 PLOS판(대조군 20명, ±30%) 수치 차이를 표로 병기하고, 인용 시 버전 명시를 요구
  - `kinematic blindness` treated as an interpretive label, not an established term
  - Six-dimensional GMM subtype/manifold percentile treated as a proposed method, not a reproduced clinical result
  - Ahmed & Rikakis 2025의 89%는 0/1점 환자를 배제한 이진분류 결과로 등급 하향 유지
- **Verification:** PASS WITH NOTES
- **Notes:** Delegation was disabled in the active Workbench session. Planned researcher/verifier/reviewer subagents could not be used; the lead completed direct evidence gathering, citation, and FATAL/MAJOR/MINOR review. PDF parsing was intentionally not attempted under the user’s workflow constraints. Several PMC pages could not be directly fetched because of JavaScript rendering, but their PubMed/PMC metadata and searchable indexed content were checked.
- **Plan:** `outputs/.plans/arat-fma-ue-evidence-map.md`
- **Research files:**
  - `outputs/.drafts/arat-fma-ue-evidence-map-research-direct.md`
  - `outputs/.drafts/arat-fma-ue-evidence-map-draft.md`
  - `outputs/.drafts/arat-fma-ue-evidence-map-cited.md`
  - `outputs/.drafts/arat-fma-ue-evidence-map-verification.md`
- **Final candidate:** `outputs/arat-fma-ue-evidence-map.md` (v2)
- **Related artifact (별도 요청):** `outputs/rgbd-grasp-vlm-protocol-analysis.md` — **v2 통합 정밀 프로토콜 아틀라스**. 조사한 **전체 문헌(47개 소스, 실험 40여 편 + 리뷰·메타·표준문서)** 을 대상자·행동/설계·획득·가공·검증 5항목 구조로 분석. ARAT 표준 물성표(Yozbatiran 2008: 항목 3 = 55 g, 항목 12 = 5.4 g, 선반 37 cm) 및 사양 미명시(Blocked) 목록 포함. **비전문가용 자료 2종 추가:** §0-3 전체 용어집(약 100항목) + **모든 논문(43편)에 `🔎 쉬운 설명` 6줄 블록**. 2026-09-22 확장.
- **Draft copies:**
  - `outputs/.drafts/arat-fma-ue-evidence-map-revised.md` (v2와 동일 내용)
  - `outputs/.drafts/arat-fma-ue-evidence-map-cited.md` (v1 요약 인용본)

## v2 추가 검증

- Padilla-Magaña 3편의 PMID/DOI/저자 목록을 PubMed에서 확인(PMID 35632013, 36501779, 35590966).

## 정정 기록 — v5 범위 초과 서술 (2026-09-22, 사용자 지적)

**지적:** “내가 손 궤적을 6개 쓸거라고 정했니? 데이터 보고 정하기로 한 거 아니야?”

**확인 결과: 지적이 맞다. 두 문서의 서술이 틀렸다.**

- v5 계획서 원문 확인:
  - §1: “건강인 군집화와 정상모형 개발은 이번 연구 범위에서 제외”
  - §5: “SPARC, 관절각 전종류, 정상 GMM, 완전 자동 접촉 분할은 이번 필수 목표에서 제외한다”
  - 후속 정상모형 연구에는 검증된 손 관절 계측, 연령·손 크기·과제 조건, 사람 단위 외부검증이 필요하다고 명시
- 즉 **“6차원 GMM”은 v5의 설계가 아니라 프로젝트 배경 설명문의 표현**이다. 문서가 이를 확정 사양처럼 서술한 것은 **범위 초과(over-scoping) 오류**다.
- **추가 발견(더 큰 문제):** 두 문서에 v5의 실제 입력 이름 **K1·K2·Q가 0건**이었다(grep 확인). 즉 두 문서의 “우리 연구” 줄은 v5가 아니라 배경 설명문 기준으로 쓰여 있었다.

**수정 내역 (verify: grep으로 잔여 0건 확인)**
- `6-component GMM` 잔여 → **0건** (양쪽 문서)
- `6차원 GMM` → `GMM 차원 선택` 등 중립 표현으로 교체
- 양쪽 문서 상단에 **v5 범위 주의문** + **표현 대응표** 삽입
- 문서 무결성: 아틀라스 43 블록 / 증거맵 40 블록 유지

**남은 미해결:** 두 문서에 “우리 연구” 줄이 **아틀라스 15곳 / 증거맵 9곳** 더 있으며, 이들은 여전히 배경 설명문 기준이다. v5 기준 재작성은 사용자 결정 대기.

**검증하지 못한 것:** 사전 명시 규칙(BIC·bootstrap)의 구체 임계값은 아직 정해지지 않았다. 문서는 “규칙이 필요하다”까지만 말하고 특정 K를 주장하지 않는다.

---

## 비전문가용 해설 추가 (2026-09-22, 2차)

**대상 1 — `outputs/rgbd-grasp-vlm-protocol-analysis.md`**
- §0-3 전체 용어집(7표, 약 100항목) 추가
- **논문 43편 전부에 `🔎 쉬운 설명` 6줄 블록** (묻는 것 / 어떻게 했나 / 핵심 숫자 / 의미 / 우리 연구 / ⚠️ 주의)
- §0-3-3에 **Vicon / Qualisys / OptiTrack** 항목 추가(정답 자 = 광학식 모션캡처, Vicon과 Qualisys는 별개 장비)
- 문서 상단에 `📖 초보자용 읽기 안내` 삽입
- **검증 명령 및 결과:** `grep -c "^#### "` = **43**, `grep -c "🔎 \*\*쉬운 설명\*\*"` = **43** → 헤딩 수와 블록 수 일치. 총 176,838 bytes.

**대상 2 — `outputs/arat-fma-ue-evidence-map.md`**
- **논문 40개 절 전부에 동일한 `🔎 쉬운 설명` 블록** (A-1~G-2의 43편 중 이 문서가 다루는 40편)
- 5-6 Padilla-Magaña 블록은 이 문서의 고유 내용(장갑 연구, SVM 97.8%, 나이 25년 차)으로 신규 작성
- 문서 상단에 `📖 초보자용 읽기 안내 (2026-09-22 추가)` 삽입
- **검증 명령 및 결과:** `grep -cE "^### [0-9]+-[0-9]+\."` = **45**(논문 40 + 비논문 5: 2-0·9-1~9-4), `grep -c "🔎 \*\*쉬운 설명\*\*"` = **40** → 논문 40개 절에 1:1 대응. 총 151,232 bytes.

**미해결/주의:** 두 문서에 동일 논문 블록이 중복 존재한다. 수치 수정 시 **양쪽을 함께 고쳐야 한다**.
- Xing 2025 LLM-FMS의 DOI 및 PubMed ID 확인(PMID 40067873), 1,812 keyframe/45명/accuracy 0.91 수치 확인.
- Tannús 2026 npj Digit Med의 R²=0.89 vs LOOCV R²=0.32–0.55 격차 및 hand aperture 핵심 특징 확인.
- Li et al.의 arXiv판과 PLOS판 수치 차이를 공식 페이지 2곳에서 대조 확인.
- 디스크에서 `outputs/arat-fma-ue-evidence-map.md`와 `outputs/.drafts/arat-fma-ue-evidence-map-revised.md` 존재 및 헤더 확인.

## Verification evidence

- PubMed metadata checks confirmed key DOI/PMID/author mappings for the clinical, kinematic, automated-scoring, and markerless papers.
- arXiv metadata checks confirmed IDs, titles, authors, dates, and abstracts for 2511.17727, 2505.18412, and 2505.01680.
- Targeted on-disk read confirmed corrected author names in the cited draft: Valladares, Herbst, Lafayette, Hamilton, and Zamin.
- Required quantitative claims are attached to inline DOI/arXiv/HTML URLs or explicitly marked unverified/omitted.

## Residual risks

1. Preprints arXiv:2511.17727 and arXiv:2505.01680 have not yet supplied the evidentiary stability of replicated peer-reviewed clinical validation.
2. Qiu et al. 2022 individual r values remain unverified; only significance and accessible model R² values are reported.
3. Markerless validity values are hardware-, task-, view-, and metric-specific and must not be treated as universal.
4. No experimental work was run in this research-only evidence map; the proposed architecture and evaluation plan remain recommendations.

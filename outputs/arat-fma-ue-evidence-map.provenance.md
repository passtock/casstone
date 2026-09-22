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
- **Related artifact (별도 요청):** `outputs/rgbd-grasp-vlm-protocol-analysis.md` — **v2 통합 정밀 프로토콜 아틀라스**. 조사한 **전체 문헌(47개 소스, 실험 40여 편 + 리뷰·메타·표준문서)** 을 대상자·행동/설계·획득·가공·검증 5항목 구조로 분석. ARAT 표준 물성표(Yozbatiran 2008: 항목 3 = 55 g, 항목 12 = 5.4 g, 선반 37 cm) 및 사양 미명시(Blocked) 목록 포함. 2026-09-22 확장.
- **Draft copies:**
  - `outputs/.drafts/arat-fma-ue-evidence-map-revised.md` (v2와 동일 내용)
  - `outputs/.drafts/arat-fma-ue-evidence-map-cited.md` (v1 요약 인용본)

## v2 추가 검증

- Padilla-Magaña 3편의 PMID/DOI/저자 목록을 PubMed에서 확인(PMID 35632013, 36501779, 35590966).
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

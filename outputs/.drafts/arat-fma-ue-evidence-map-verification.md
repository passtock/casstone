# Verification Report — ARAT·FMA-UE Evidence Map

**Candidate reviewed:** `outputs/.drafts/arat-fma-ue-evidence-map-cited.md`  
**Date:** 2026-09-22  
**Method:** direct lead verification; subagent delegation unavailable.

## Checks performed

1. Cross-checked key identifiers and author lists with PubMed/arXiv metadata for PMID 38693881, 39186425, 30776997, 39224885, 22647879, 20829411, 32640003, 39593603, 36616603 and arXiv IDs 2511.17727, 2505.18412, 2505.01680.
2. Checked key quantitative claims against searchable HTML/abstract content:
   - Hsueh floor/ceiling/ICC values.
   - Alt Murphy ARAT correlations and regression variance.
   - Bayle SPARC ICC/correlations.
   - Saes longitudinal coefficients.
   - VLM flatlining wording and cohort sizes.
   - Tang GPT-4o/LSTM/ST-GCN comparison table.
   - markerless ICC/error values.
3. Verified that every evidence-map row and critical numerical claim has an inline URL.
4. Checked that `flatlining` and `kinematic blindness` are not presented as established clinical terminology.
5. Checked that six-dimensional GMM subtyping is labeled a proposed method, not a reproduced literature result.
6. Performed on-disk read after citation edits; corrected author attributions are visible in the cited file.

## FATAL

- **None remaining.**

### Corrected during review

- Incorrect author shorthand was corrected on disk:
  - `Krebs` → `Valladares` for DOI 10.3389/fneur.2024.1429929.
  - `Bashford` → `Herbst` for DOI 10.1371/journal.pone.0234969.
  - `Jo` → `Lafayette` for DOI 10.3390/s23010003.
  - `Wade` → `Hamilton` for DOI 10.1016/j.jbmt.2024.04.033.
  - `Zhou` → `Zamin` for BIONICS DOI 10.1177/15459683231184186.
- Targeted read confirmed corrected names in both narrative and Sources section.

## MAJOR

1. **Qiu 2022 individual correlation coefficients unavailable.** Accessible official metadata/HTML confirms significance and exposes two-variable adjusted/predictive R², but not each Pearson r. The report explicitly states this and does not invent r values.
2. **Three-view ARAT evidence is preprint-level.** The 89% result uses only scores 2 vs 3 and describes a random segment split. Patient-disjoint independence is not demonstrated in the accessible text. Report downgraded to low evidence and flags leakage risk.
3. **VLM direct evidence remains a single preprint.** Flatlining is directly described in arXiv:2511.17727 but requires independent replication.
4. **Normative 6D GMM/manifold is not directly validated.** Report labels it a research hypothesis and requires comparison with simpler normative baselines.
5. **Markerless validation is dominated by healthy/simple-movement studies.** The report avoids applying one universal ICC/error to stroke ARAT tasks.

## MINOR

1. Several transfer-evidence source-list author entries (`Zhang et al.` for UbiPhysio; `Cotton et al.` for BiomechGPT) are abbreviated rather than fully enumerated, but arXiv identifiers and URLs are preserved.
2. Some terminology remains bilingual (e.g., `smoothness`, `trunk displacement`, `patient-disjoint`) to preserve technical precision.
3. No quantitative feedback-quality score exists for Tang et al.; the report correctly describes feedback evaluation as qualitative.

## Verification outcome

**PASS WITH NOTES**

The central claims and numbers are source-mapped. Remaining notes concern preprint status, unavailable Qiu per-metric r values, and lack of direct validation for the proposed GMM/VLM fusion—not citation fabrication or unresolved fatal errors.

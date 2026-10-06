# Review Plan: Harness Engineering (arXiv:2609.00006)

**Artifact**: `https://arxiv.org/abs/2609.00006` (`https://arxiv.org/pdf/2609.00006`)  
**Title**: *Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents — A Source-Code Study of Eleven Systems*  
**Authors**: Paul Barbaste, Tristan Darrigol, Germain Vu, Tom Wiltberger  
**Date**: September 2026 (Revision of April 2026 study)  
**Slug**: `harness-engineering-study`

---

## 1. Review Objectives
- Conduct a rigorous, comprehensive technical deep-dive into the first large-scale empirical source-code study of LLM coding agent runtimes (harnesses).
- Deconstruct the 7 canonical subsystems, 11 production harnesses (+ Omnigent meta-harness), 13 cross-cutting observations, and 29 architectural patterns.
- Analyze the "Twin Absences" (Zero agentic frameworks, Zero vector code RAG) and "The Platform Turn" (CLI as framework/platform).
- Extract and critique the 18 design recommendations and the 90-line Minimum Viable Harness (MVH).
- Assess empirical rigor, threats to validity, and practical takeaways for building production-grade coding agents.

## 2. Review Criteria
1. **Theoretical & Conceptual Rigor**: Clarity of the "Harness" definition, genealogy, and the 7-subsystem anatomical decomposition.
2. **Empirical Grounding**: Verification across ~4 million lines of Python, TypeScript, and Rust code from commercial and open-source systems.
3. **Architectural Value**: Depth of analysis across loop paradigms, prompt assembly, file editing, context compaction, multi-agent orchestration, sandboxing, and extensibility.
4. **Reproducibility & Practical Utility**: Actionability of the 18 recommendations, clarity of the 90-line MVH scaffold, and verification of claims.

## 3. Workflow Steps
1. Parse full text and 18 comparison tables from arXiv source HTML.
2. Write structured evidence notes to `outputs/.drafts/harness-engineering-study-review-evidence.md`.
3. Synthesize the final comprehensive review artifact in `outputs/harness-engineering-study-review.md`.
4. Provide a detailed, highly structured, and insightful Korean explanation directly answering the user's prompt.

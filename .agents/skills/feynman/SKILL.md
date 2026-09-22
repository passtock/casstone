---
name: feynman
description: >-
  Autonomous AI scientific and ML research agent workflow. Use when the user asks
  for deep literature research, academic paper analysis, arXiv exploration,
  ML training recipes, paper replication, code audits, automated experimentation loops (autoresearch),
  or citing and synthesizing research claims with provenance tracking.
---

# Feynman Research Agent Skill

This skill provides the core workflows, subagent patterns, and output standards of **Feynman — The Open Source AI Research Agent** for scientific investigation, machine learning experiments, and paper analysis.

---

## 1. Core Research Roles & Mindset

When operating in Feynman mode:
- **Source-Grounded**: Every factual claim must be backed by citations or experimental evidence.
- **Truth over Polishing**: Never hallucinate or smooth over missing checks. Explicitly label claims as `[verified]`, `[unverified]`, `[inferred]`, or `[blocked]`.
- **Slug-based Output Conventions**: Always assign a concise topic slug (lowercase, hyphens, ≤5 words, e.g. `multimodal-rag-evaluation`) to organize artifacts.

---

## 2. Research Workflows & Prompts

Refer to the prompt templates in [prompts/](./prompts/) for detailed execution instructions for each workflow:

| Workflow | Trigger / Goal | Reference Prompt |
| :--- | :--- | :--- |
| **Deep Research** | Comprehensive, multi-source literature investigation | [deepresearch.md](./prompts/deepresearch.md) |
| **Literature Review** | Systematic survey of prior work, methods, and benchmarks | [lit.md](./prompts/lit.md) |
| **Paper Review** | In-depth technical critique of an arXiv paper or PDF | [review.md](./prompts/review.md) |
| **ML Training Recipe** | Practical dataset, architecture, and hyperparameter guidance | [recipe.md](./prompts/recipe.md) |
| **Code & Paper Audit** | Auditing codebase against claims in a paper | [audit.md](./prompts/audit.md) |
| **Replication** | Assessing reproducibility and drafting replication steps | [replicate.md](./prompts/replicate.md) |
| **Autoresearch** | Iterative hypothesis-experiment-benchmark search loop | [autoresearch.md](./prompts/autoresearch.md) |
| **Source Comparison** | Comparing two or more competing papers or approaches | [compare.md](./prompts/compare.md) |
| **Draft Writing** | Structuring and drafting an academic paper or technical report | [draft.md](./prompts/draft.md) |
| **Paper Summarization** | Concise distillation of core contributions and limitations | [summarize.md](./prompts/summarize.md) |

---

## 3. Output Conventions & Directory Structure

Always follow Feynman file organization conventions:

- **Research Outputs**: `outputs/<slug>.md`
- **Drafts & Papers**: `papers/<slug>.md` or `outputs/.drafts/<slug>-draft.md`
- **Provenance Sidecars**: `<slug>.provenance.md` (recording all sources, search terms, and verification status)
- **Work Notes & Session Logs**: `notes/<slug>-notes.md`
- **Lab Notebook / Running Log**: `CHANGELOG.md` in workspace root (record milestones, tested hypotheses, failed directions)

---

## 4. Subagent Delegation Pipeline

For multi-step or deep investigations, adopt the four-stage specialist pipeline:
1. **Researcher**: Discovers papers via web search, AlphaXiv, arXiv, and Hugging Face; extracts key empirical metrics.
2. **Reviewer**: Evaluates theoretical rigor, experimental validity, and potential failure modes.
3. **Writer**: Synthesizes the structured draft with inline citations.
4. **Verifier**: Audits citations, checks claims against primary sources, and generates the `.provenance.md` record.

See [AGENTS.md](./AGENTS.md) for full delegation rules and workspace conventions.

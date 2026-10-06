# Evidence Notes: Harness Engineering (arXiv:2609.00006)

**Source**: `https://arxiv.org/html/2609.00006v1` (arXiv:2609.00006)  
**Corpus**: 11 production coding agent harnesses + Omnigent meta-harness (~4,000,000 LOC in Python, TypeScript, Rust)  
**Corpus Version Pins**: July 2026 releases (with longitudinal diff against April 2026 snapshots)

---

## 1. Key Empirical Facts & Numbers

| Fact / Metric | Exact Empirical Observation | Status |
| :--- | :--- | :--- |
| **Corpus Scale** | ~4,000,000 LOC across 11 systems (+ 1 meta-harness). Languages: Python, TypeScript, Rust. | `[verified]` |
| **Twin Absence 1 (Frameworks)** | **0 out of 11 systems** import LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, Pydantic AI, Genkit, ADK, or Semantic Kernel. | `[verified]` |
| **Twin Absence 2 (Code RAG)** | **0 out of 11 systems** use vector embeddings or vector databases for code retrieval. (Embeddings only appear for conversation history in OpenClaw). | `[verified]` |
| **Code Retrieval Reality** | 100% of systems rely on deterministic tools: ripgrep, glob, filesystem tree walks, tree-sitter AST, and LSP diagnostics. | `[verified]` |
| **Skills vs MCP Adoption** | **Skills (SKILL.md) lead MCP**: 9/11 systems support `SKILL.md` (only Aider & Mini-SWE-Agent omit it), while 8/11 support MCP. | `[verified]` |
| **ACP (Agent Client Protocol)** | Ships in 6 systems. Acquired a new 3rd role: **Harness Hosting** (OpenHands running Claude Code, Codex, Gemini CLI as interchangeable backends). | `[verified]` |
| **Multi-Agent Orchestration** | 9 out of 11 systems support multi-agent execution. 8 of the 9 keep sub-agents **in-process**. | `[verified]` |
| **The Minimalism Floor** | Mini-SWE-Agent implements all 7 subsystems in ~100 lines and achieves 74%+ on SWE-Bench Verified (self-reported), proving loop complexity does not predict task benchmark score. | `[verified]` |
| **The Platform Turn** | Coding agent harnesses completed the transition from CLI tools to extensible application platforms with SDKs, marketplaces, and meta-harnesses. | `[verified]` |

---

## 2. The Seven Canonical Subsystems (Table 1)

1. **Agent Loop (§6)**:
   - Alternates model inference with tool execution; manages stop guards and error loops.
   - *Minimal*: Mini-SWE-Agent (50-line linear while loop over bash).
   - *Maximal*: OpenHands (event-sourced conversation engine over persistent append-only event log with parallel tool batching); Codex (Tokio async state machine).
2. **LLM Integration (§7)**:
   - Handles provider protocols, streaming, prompt assembly, prompt cache boundaries, and reasoning effort.
   - *Minimal*: 1 LiteLLM call + 1 Jinja template.
   - *Maximal*: Hermes (5 owned transports, 29 provider profiles); Codex (remote server-delivered model catalog & instructions).
3. **Tools & Actions (§8)**:
   - Tool definition, schemas, parameter parsing, execution, and file editing.
   - *Minimal*: Bash only.
   - *Maximal*: Claude Code (43 typed tools with deferred loading via `ToolSearchTool`); Codex (V8-executed JavaScript code blocks as tool actions).
4. **Memory & Context Management (§9)**:
   - Context rationing, threshold compaction, session trees, persistent memory.
   - *Minimal*: Unbounded linear history.
   - *Maximal*: Codex (two-phase background sub-agent cross-session memory); Gemini CLI (graph-based multi-stage context distillation).
5. **Safety & Permissions (§10)**:
   - Approval modes, sandboxing, policy-as-code, audit logging.
   - *Minimal*: Step limits and token caps.
   - *Maximal*: Codex (Starlark execution policy + Guardian LLM approval reviewer + 3-platform native OS sandbox: Bubblewrap / Seatbelt / Windows tokens).
6. **Orchestration (§11)**:
   - Subagent spawning, context forking, inter-agent communication, coordinator-worker hierarchy.
   - *Minimal*: None (Aider is strictly single-agent).
   - *Maximal*: Claude Code (recursive composition & context forking); Omnigent (cross-vendor meta-orchestrator).
7. **Extensibility (§12)**:
   - Plugins, skills (`SKILL.md`), hooks, configuration, MCP servers.
   - *Minimal*: Python structural typing / protocols.
   - *Maximal*: Pi (everything-is-an-extension runtime); Codex (marketplace-distributed plugins).

---

## 3. The 11 Audited Systems Summary (Table 4)

1. **Claude Code** (Anthropic, TS, Large): Deferred tool loading; Blake2b prompt-cache boundary (`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`); 3-layer permissions; worktrees; context-forking subagents.
2. **Codex CLI** (OpenAI, Rust, Very Large): Native 3-OS sandboxing (vendored bubblewrap); Starlark policy; Guardian LLM reviewer; server-delivered model instructions; background memory agent.
3. **Gemini CLI** (Google, TS, Very Large): Native 3-OS sandbox; 4 approval modes (PLAN, DEFAULT, AUTO-EDIT, YOLO); A2A (Agent-to-Agent) server protocol; capability-gated prompt snippets.
4. **Mistral Vibe** (Mistral AI, Python, Small): Composable middleware pipeline loop; rewind over ACP; two-tier reactive compaction; per-agent markdown prompts.
5. **OpenHands** (Open Source, Python, Medium): Event-sourced engine; Docker/Apptainer sandbox; hosts rival harnesses via ACP; resource-locked parallel tool execution.
6. **Aider** (Open Source, Python, Small): 13 polymorphic edit formats; tree-sitter PageRank-style RepoMap; reflection loop with linter/test feedback; strictly single-agent.
7. **Mini-SWE-Agent** (Open Source, Python, Tiny): 100-line floor proof; single bash tool; linear loop; proves that task completion is model-bound, while production harness weight is for safety/UX/platform.
8. **Hermes** (Open Source, Python, Very Large): 69 tools; 5 owned transports; self-improving skill loop; lineage compaction (session rotation); verify-on-stop guard; YOLO policy floor.
9. **Pi** (Open Source, TS, Medium): 7 built-in tools; minimal core where safety, sandboxing, and sub-agents live on a runtime event bus; session-tree version control.
10. **OpenCode** (Open Source, TS, Large): Client/server architecture with OpenAPI & SDK; syntax-aware command permissions (tree-sitter); model-family prompt matrix (9 prompts); shadow git checkpoints.
11. **OpenClaw** (Open Source, TS, Large): Multi-channel gateway (28+ channels); 109+ tools; Active-Memory subagent before every response; hybrid sqlite-vec + FTS5 memory (non-code only).
*Contrast Point*: **Omnigent** (Databricks, Meta-harness): Imports `claude-agent-sdk` and `openai-agents` as dependencies; orchestrates 11 vendor harnesses behind one unified API.

---

## 4. The 29 Design Patterns & 18 Recommendations

- **13 Observations**: Span the decoupling of benchmark performance from loop complexity, prompt rhetoric convergence, file editing mechanics, sandboxing cost, and the platform turn.
- **29 Patterns**: Cataloged in Tables 11 & 12 (Event sourcing, Policy-as-code, Deferred loading, Threshold compaction, JIT repo context, Skills, Lineage compaction, Session trees, etc.).
- **18 Recommendations**: Provide a complete blueprint for building modern harnesses (Linear loop first -> Bash tool first -> Deferred loading >15 tools -> Exact substring replace for frontier models -> Context markdown auto-discovery -> NO Code RAG -> 3-mode safety -> Policy-as-code -> ACP server).
- **Listing 3 (90-line MVH)**: Concrete, working Python scaffold embodying the core principles.

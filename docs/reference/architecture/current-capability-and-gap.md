# Current Capability and Gap

## Purpose

This document answers three practical questions:
1. What Snowiki can actually do today
2. How mature those capabilities are
3. What is still missing before Snowiki can be considered fully functional for its intended role

This is a reality document, not a roadmap wishlist.

## Current capability level

Snowiki today is best described as a **usable Phase 1 backend and knowledge-compilation substrate**, not yet a finished end-to-end knowledge product.

It already has real, testable, installed runtime behavior. But it is still missing parts of the broader product/workflow/knowledge-quality story implied by the project vision.

This assessment is grounded in the shipped runtime and its tests, not in deferred workflow text. In particular, the current truth comes from the installed CLI surface, the read-only MCP surface, the benchmark harness, and the corresponding regression tests.

## What Snowiki can do today

### 1. Installable CLI runtime
Snowiki is packaged as an installable CLI under the `snowiki` command.

Current shipped CLI commands:
- `ingest`
- `rebuild`
- `query`
- `recall`
- `status`
- `lint`
- `export`
- `benchmark`
- `daemon`
- `mcp`

This means Snowiki is not merely a source-tree experiment; it is already usable as a packaged local CLI.

**Evidence:**
- `pyproject.toml` package metadata and CLI entrypoint
- `src/snowiki/cli/main.py`
- `README.md` Quick Start and current shipped CLI surface

**Why this is a strong claim:**
- the package is wired through `pyproject.toml`
- the runtime surface is assembled in `src/snowiki/cli/main.py`
- install/use contract drift is now guarded by `tests/governance/test_runtime_contract_docs.py`

### 2. Source/session ingest into normalized storage
Snowiki can ingest supported source material, especially Claude/OpenCode-like session exports, into normalized storage.

This is one of its strongest implemented capabilities.

**Evidence:**
- `src/snowiki/cli/commands/ingest.py`
- `tests/cli/test_ingest.py`
- `tests/adapters/test_opencode_adapter.py`
- `tests/privacy/test_redaction.py`

**Why this is solid:**
- ingest is a real shipped command
- it is covered through adapter and privacy/redaction tests

**What is still missing before this area feels broader than Phase 1:**
- more source types beyond the current session-heavy ingest focus
- richer ingest reporting and broader end-user source workflows

**Production-readiness caveat:**
- source coverage is still narrow; the runtime is strongest on session-like inputs rather than arbitrary raw project corpora.

### 3. Rebuild into compiled knowledge artifacts
Snowiki can rebuild compiled wiki-like pages from normalized records.

This supports the central “compilation, not storage” direction, even if the final artifact system is not yet as rich as the long-term vision.

**Evidence:**
- `src/snowiki/cli/commands/rebuild.py`
- `src/snowiki/compiler/engine.py`
- `tests/cli/test_rebuild.py`
- `tests/compiler/test_rebuild_determinism.py`

**Why this is solid:**
- rebuild is a real shipped command
- deterministic rebuild behavior is explicitly tested

**What is still missing:**
- richer compiled artifact semantics beyond the current Phase 1 page set
- broader productized authoring/maintenance flows around those artifacts

**Production-readiness caveat:**
- the rebuild path is real, but the higher-order artifact system (richer questions/comparisons/provenance quality guarantees) is still incomplete.

### 4. Lexical query and recall
Snowiki has a functioning lexical retrieval path for:
- query
- recall
- daemon-backed warm retrieval

This path is benchmarked and recently received a meaningful hot-path optimization.

**Evidence:**
- `src/snowiki/cli/commands/query.py`
- `src/snowiki/cli/commands/recall.py`
- `src/snowiki/search/indexer.py`
- `src/snowiki/search/workspace.py`
- `tests/cli/test_query.py`
- `tests/retrieval/test_mixed_language_queries_integration.py`

**Why this is solid:**
- query and recall are shipped CLI commands
- the lexical path is benchmarked and exercised in integration tests

**What is still missing:**
- mature Korean and mixed-language lexical policy
- semantic/hybrid/rerank as actual runtime behavior

**Production-readiness caveat:**
- this is a strong Phase 1 retrieval path, but semantic retrieval, reranking, and final multilingual lexical policy are still unresolved.

### 5. Read-only MCP surface
Snowiki exposes a read-only MCP surface suitable for agent/tool use.

That means the system already has a machine-facing interface beyond its CLI.

**Evidence:**
- `src/snowiki/cli/commands/mcp.py`
- `src/snowiki/mcp/server.py`
- `src/snowiki/mcp/tools/*`
- `src/snowiki/mcp/resources/*`
- `tests/mcp/test_search.py`
- `tests/mcp/test_readonly.py`

**Why this is only partial rather than fully solid:**
- the MCP surface is real and tested
- but it is intentionally read-only and still narrower than the larger product/workflow vision

**Production-readiness caveat:**
- MCP is real and useful, but still intentionally read-only and narrower than the eventual broader knowledge workflow surface.

### 6. Benchmark and evaluation discipline
Snowiki already has:
- deterministic benchmark presets
- retrieval quality thresholds
- latency thresholds
- structural gate semantics
- manual benchmark workflow support in GitHub Actions

This is unusually strong for a project at this stage and is one of the system’s real strengths.

**Evidence:**
- `src/snowiki/cli/commands/benchmark.py`
- `src/snowiki/bench/*`
- `benchmarks/README.md`
- `tests/cli/test_benchmark.py`
- `tests/bench/test_retrieval_benchmarks_integration.py`

**Why this is solid:**
- deterministic presets
- explicit thresholds
- structural + retrieval + performance gate model

**What is still missing:**
- broader answer-quality/provenance evaluation
- richer benchmark history/trend tooling
- broader workflow-level evaluation beyond Phase 1 backend focus

**Production-readiness caveat:**
- benchmark rigor is strong for Phase 1 backend evaluation, but it is not yet the same thing as a full product-quality or agent-authoring evaluation system. Benchmark outputs are evidence of engine capability, not the shipped runtime contract itself.

### 7. Unit/integration split and governance
The repo now has:
- a fast default unit loop
- explicit integration tests
- governance/path-contract discipline
- `src/snowiki/` layout

That means the engineering substrate is much healthier than earlier phases.

**Evidence:**
- `AGENTS.md`
- `tests/governance/*`
- current CI workflow

**Why this is solid:**
- the repo now has an actual discipline layer preventing drift in commands, paths, and surface contracts

## What is solid today

These are the strongest, most credible parts of the current system.

### Solid
- packaged CLI runtime
- lexical retrieval backbone
- rebuild/compile path
- deterministic benchmark harness
- MCP read surface
- governance and path discipline
- test taxonomy and fast local loop

These are the areas where Snowiki already behaves like a serious maintained engineering system rather than a prototype.

## What is partial today

These areas exist, but are not yet complete enough to be treated as “finished product behavior.”

### Partial
- broader wiki workflow beyond core CLI/retrieval
- cross-session install/use story beyond the newly aligned CLI-first contract
- deeper skill/runtime/agent contract design
- multilingual/Korean lexical strategy
- richer answer-quality and provenance quality evaluation

These are not hand-wavy aspirations; each has either partial shipped behavior or a clearly defined near-term hardening path, but none of them is complete enough to be sold as a finished product surface today.

## What is still mostly placeholder / deferred

These are real directions, but not current product truths.

### Deferred / placeholder
- semantic retrieval as an active runtime path
- reranking in the default path
- hybrid retrieval as a first-class shipped mode
- local model lifecycle management
- backend migration (SQLite FTS5/Tantivy/Qdrant/native)
- contradiction detection / richer semantic lint
- broad edit/sync/merge style product workflows as stable shipped behavior

These should be treated as explicit roadmap or research topics, not present-tense product truths.

These are important strategic directions, but they should not be described as things Snowiki already “does”.

## Main gaps before Snowiki “fully does the job”

If Snowiki is to fulfill its intended role as a provenance-aware, agent-friendly knowledge engine, the biggest remaining gaps are:

### 1. Canonical retrieval contract
The retrieval substrate must be canonical across CLI, daemon, MCP, and benchmark paths.

Without that, quality and performance work drift.

### 2. Better language strategy
Korean and mixed-language retrieval need benchmarked lexical decisions before semantic escalation.

### 3. Stronger knowledge-quality layer
Structural correctness is present, but richer knowledge-quality checks are not yet there:
- contradiction handling
- stale claim surfacing
- claim-level provenance quality
- broader semantic lint

### 4. Better skill/agent contract
The runtime is stronger than the current skill contract. That gap needs to be closed so agents can use Snowiki confidently without relying on legacy assumptions.

This is especially important because the current runtime already has real CLI JSON and MCP surfaces, so the remaining gap is more about contract clarity and workflow truth than about the total absence of agent interfaces.

### 5. Stronger productized ingest-to-wiki flow
Today the backend substrate is much stronger than the polished end-to-end “take a project/source and turn it into durable, queryable knowledge” workflow.

That means Snowiki can already support serious local knowledge work, but still needs a cleaner user/operator path before it fully feels like a finished knowledge product.

## Bottom line

Snowiki is already beyond a toy. It is a real CLI/MCP/benchmark-backed local knowledge substrate with a functioning lexical retrieval and compilation path.

But it is not yet a fully realized provenance-aware, agent-native knowledge product.

The next phase is not “start from scratch,” but **turn a strong backend/research substrate into a coherent, trustworthy knowledge system with better retrieval architecture, better language handling, better agent contracts, and stronger quality guarantees.**

# Current Retrieval Architecture

## Purpose

This document describes Snowiki’s current retrieval architecture as it exists in the shipped runtime.

The goal is to make future changes deliberate and comparable, rather than letting CLI, daemon, MCP, benchmark, and workflow surfaces drift apart.

## Active retrieval surfaces

Snowiki’s current retrieval stack shows up through four active runtime/evidence surfaces:

1. **CLI query/recall**
   - `src/snowiki/cli/commands/query.py`
   - `src/snowiki/cli/commands/recall.py`

2. **Daemon warm retrieval**
   - `src/snowiki/daemon/warm_index.py`
   - `src/snowiki/daemon/server.py`
   - `src/snowiki/daemon/cache.py`
   - `src/snowiki/daemon/invalidation.py`

3. **Read-only MCP retrieval**
   - `src/snowiki/mcp/server.py`
   - `src/snowiki/mcp/tools/*`
   - `src/snowiki/mcp/resources/*`

4. **Benchmark/evidence paths**
   - `src/snowiki/bench/*`
   - `benchmarks/README.md`

## The lexical backbone

The current active retrieval backbone is lexical and deterministic.

Primary modules:
- `src/snowiki/search/indexer.py`
- `src/snowiki/search/index_lexical.py`
- `src/snowiki/search/index_wiki.py`
- `src/snowiki/search/tokenizer.py`
- `src/snowiki/search/queries/*`

### What that means
- search is currently grounded in a lexical blended index
- current runtime does **not** use a semantic or reranked path as the default truth
- strategy differences are mostly routing/policy differences over the same lexical core

## Canonical retrieval seam

The current canonical seam is now centered on:
- `src/snowiki/search/workspace.py`

This file owns the shared retrieval assembly path and related service abstractions.

### Its role
- turn normalized records into search-ready structures
- turn compiled pages into search-ready structures
- build a blended retrieval snapshot
- provide the common retrieval contract used across multiple runtime surfaces

This is the most important architectural seam in the current codebase.

## Canonical retrieval contract

The canonical retrieval contract defines the normative behavior and shared expectations across all Snowiki retrieval surfaces.

### Source of truth
- **CLI recall** is the source-of-truth routing contract for the Snowiki system.
- Other surfaces (MCP, daemon) are **informative mirrors** or specialized optimizations of this authoritative contract.
- The behavior of the installed CLI defines the current system capabilities.

### Parity matrix
To prevent drift, retrieval surfaces are evaluated against these parity categories:

| Category | Definition |
| :--- | :--- |
| **Routing Parity** | Surfaces must use identical strategy layers (topical, temporal, known-item) for the same query intent. |
| **Metadata Parity** | Result structures must preserve provenance, score, and identity fields across all surfaces. |
| **Freshness Parity** | Surfaces must expose consistent generation identities (content-derived and process-local). |
| **Evaluation Boundary Parity** | Benchmark/runtime equivalence should never be assumed without explicit declaration. |

For the current shipped surfaces, that matrix means:

- **CLI `recall`** defines the authoritative auto-routing order: `date` → `temporal` → `known_item` → `topic`.
- **MCP `recall`** mirrors that routing contract and reports the chosen strategy, while **MCP `search`** intentionally remains a direct read-only search tool without recall auto-routing.
- **daemon `/query`** may keep explicit operation names for specialized callers, but `operation=recall` is the parity path that mirrors the CLI recall contract.

### Generation and identity
Retrieval state is identified by two distinct generation markers:
- **Content-derived freshness identity**: A hash or timestamp derived from the underlying source material.
- **Process-local runtime generation**: An opaque identifier naming the specific assembly or reload event in the current process.

For the current daemon surface, these identities should be exposed as separate diagnostic fields rather than collapsed into a single generic freshness label.

### Stale-state semantics
- Stale daemon state may exist until explicit invalidation or reload.
- This state must be surfaced explicitly to consumers; it must not be treated as authoritative when a newer generation is available.
- Cached retrieval state is valid only until explicit invalidation or TTL expiry.
- Health/status and query diagnostics should report both the snapshot identity being served and the current content-derived identity observed on disk so stale state is visible instead of implicit.

### Benchmark/runtime boundary
- Benchmark lexical paths are not always identical to shipped runtime query paths.
- This distinction is intentional but must be explicit.
- Benchmark evidence is used for evaluation, while CLI behavior remains the authoritative runtime contract.
- Benchmark outputs are evidence of engine capability, not the shipped runtime contract itself.
- Benchmark/runtime equivalence should never be assumed without saying so explicitly.

## Runtime Lexical-Policy Promotion Contract

This contract defines the formal requirements for promoting a new lexical retrieval policy to the Snowiki runtime default.

### Lexical-Policy Identifier
The authoritative identifier for the current promoted candidate is `korean-mixed-lexical`. This policy uses the Kiwi-backed morphology engine for improved Korean and mixed-language retrieval.

### Promotion Gates
Promotion from benchmark-only evidence to runtime truth requires passing two distinct gates. A benchmark PASS alone is insufficient for promotion.

1. **Benchmark Victory Gate**
   - The candidate must meet or exceed all Phase 1 thresholds: Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67.
   - It must demonstrate a clear improvement in topical or known-item metrics without regressing the overall system recall.
   - Benchmark outputs are treated as evidence of capability, not as the shipped runtime contract.

2. **Runtime Safety Gate**
   - The candidate must provide a runtime safety proof through a full green suite: `uv run ruff check`, `uv run ty check`, `uv run pytest`, and `uv run pytest -m integration`.
   - Implementation work must preserve the strict separation between benchmark baselines and runtime retrieval paths.
   - No candidate may introduce silent adaptation or hidden dependencies on benchmark-only assets.

### Mismatch and Failure Behavior
To prevent operational drift and index corruption, the runtime enforces strict policy alignment:
- **Explicit Rebuild**: Any change to the active runtime lexical policy requires an explicit `snowiki rebuild`.
- **Hard Fail on Mismatch**: If the runtime detects a mismatch between the active policy and the existing index/snapshot, it must hard-fail or trigger a mandatory rebuild. Silent adaptation to a mismatched index is forbidden.
- **No Auto-Promotion**: Benchmark victory does not trigger automatic runtime promotion. Promotion remains a deliberate architectural decision.

### Rollback and Recovery
Rollback of a promoted policy is an explicit operational action.
- A rollback requires reverting the runtime policy identifier and performing a full index rebuild.
- The system must maintain the ability to return to the legacy lexical default if the promoted candidate exhibits unforeseen runtime instability.

## Strategy layers

The retrieval policy wrappers currently live in:
- `src/snowiki/search/queries/known_item.py`
- `src/snowiki/search/queries/topical.py`
- `src/snowiki/search/queries/temporal.py`

These are not separate search engines. They are strategy layers over the same canonical retrieval substrate.

## Semantic and rerank status

These exist as extension seams, not active runtime layers.

### Semantic
- `src/snowiki/search/semantic_abstraction.py`
- currently a hook / abstraction point
- not the authoritative runtime retrieval path

### Rerank
- `src/snowiki/search/rerank.py`
- similarly a seam, not the main deployed path

## Benchmark comparison path

The benchmark system intentionally evaluates more than one retrieval mode.

Important files:
- `src/snowiki/bench/baselines.py`
- `src/snowiki/bench/report.py`
- `src/snowiki/bench/phase1_correctness.py`
- `src/snowiki/bench/phase1_latency.py`

Important nuance:
- benchmark evidence is strong and useful
- but benchmark baselines are not always identical to the exact runtime query path
- benchmark/runtime equivalence should never be assumed without saying so explicitly

## Daemon and cache semantics

Snowiki has more than one cache-like layer:

### Query-path cache
- cheap in-process reuse for repeated query calls
- exists to avoid rebuilding everything on every call

### Daemon warm snapshot
- long-lived prebuilt warm retrieval surface
- optimized for persistent serving and repeated reads

### TTL response cache
- request/response reuse for daemon-style serving

The architecture implication is important:
- cache ownership must remain explicit
- invalidation must be deliberate
- these cache layers should not silently redefine the retrieval contract
- daemon diagnostics should identify whether metadata belongs to the warm snapshot owner or the TTL response-cache owner

## Agent-facing retrieval surfaces

Snowiki must preserve agent usability.

That means retrieval architecture is constrained by:
- CLI JSON output
- MCP search/recall/page/link tools
- workflow/skill composability

This is why “just improve search” is not enough. Changes must preserve machine-facing contracts.

## Main current risk

The main current architecture risk is **drift**.

Not drift between “old and new algorithms,” but drift between surfaces that should all be speaking the same retrieval language:
- CLI
- daemon
- MCP
- benchmark/evidence
- skill/workflow expectations

Canonicalization of the retrieval contract is therefore more important, near term, than adding new retrieval machinery.

## Current direction implied by the codebase

The codebase currently points toward this order:

1. canonical retrieval contract
2. lexical quality and language strategy improvements
3. profiling and performance improvements
4. semantic / rerank / local model questions
5. backend evolution and native acceleration

That order should remain the default until evidence justifies changing it.

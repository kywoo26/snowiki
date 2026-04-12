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

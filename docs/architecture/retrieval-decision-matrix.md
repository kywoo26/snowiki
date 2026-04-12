# Retrieval Decision Matrix

## Purpose

This document states the current architecture decisions for Snowiki’s retrieval direction.

It is not a survey. It is a decision document.

## Framing

- **Now**: should be actively prioritized now
- **Later**: valid direction, but not yet
- **Reserved question**: explicit future design question with evidence needed before implementation

## Current decisions

| Axis | Now | Later | Reserved question |
|---|---|---|---|
| Lexical backbone | Keep as the active runtime backbone | Revisit only after contract hardening + lexical evaluation | Whether the current scorer should later be replaced or augmented |
| Canonical retrieval unit | Standardize one shared retrieval/corpus contract | Specialized corpus variants only later if needed | Whether normalized record, compiled page, or staged blend is the long-term canonical unit |
| Hybrid retrieval | Keep as deferred extension seam | Add only after lexical limits are proven | Which query classes really justify hybrid |
| Reranking | Keep out of the default path | Optional later quality layer | What candidate set rerank should operate on |
| Local models | Keep out of default runtime path | Add only with explicit CPU/GPU policy | Warm/cold lifecycle, fallback, and agent semantics |
| Backend evolution | Defer | Later architecture move | SQLite FTS5 vs Tantivy vs Qdrant vs native acceleration |
| Korean lexical strategy | Treat as lexical/tokenization problem first | Add selectable strategy later | Which tokenizer/morphology choice wins on Korean/mixed slices |
| Agent-facing constraints | Treat as non-negotiable now | Expand only if contracts remain stable | How much retrieval complexity can be exposed to agents |

## Stable modern patterns vs unsettled areas

### Stable enough to treat as current best practice
- lexical retrieval remains the safety net for exact identifiers, paths, literals, and provenance-bearing text
- hybrid retrieval is usually additive rather than a replacement for lexical retrieval
- reranking is a second-stage precision layer, not a substitute for poor first-stage candidate generation
- benchmarked retrieval quality and latency should be evaluated separately from answer-generation quality
- machine-readable agent-facing contracts should stay simpler than the full internal retrieval complexity

### Still unsettled enough to keep behind decision gates
- what the best default local multilingual / Korean retrieval stack is
- what local CPU/GPU model split is truly ergonomic for daily use
- when a backend swap becomes worth the operational/migration cost
- how much retrieval strategy complexity should be surfaced directly to agents

## What not to do yet

- semantic/vector runtime integration
- default rerank path
- backend swap
- local model lifecycle complexity in the mainline runtime
- pretending benchmark evidence alone decides product architecture

## Promotion gates

Deferred work should only move forward with evidence in one or more of:
- measured lexical limits
- benchmark quality deltas
- operational fit
- contract stability

## How to interpret those gates

### Measured lexical limits
Use this when the current lexical system fails even after:
- canonical corpus assembly
- tokenization cleanup
- query-routing cleanup

If the lexical path still misses relevant results in a repeatable way, later semantic/hybrid work becomes justified.

### Benchmark quality deltas
Use this when a candidate approach demonstrates consistent gains on:
- Recall@k
- MRR
- nDCG@k
across the relevant slices, without relying on one-off wins or hand-picked examples.

### Operational fit
Use this when a proposed later layer can state:
- acceptable latency
- acceptable memory use
- warm/cold behavior
- CPU-only fallback or GPU-optional semantics

If those aren’t explicit, the idea is not ready.

### Contract stability
Use this when a proposed change preserves:
- CLI JSON stability
- MCP/tool behavior
- deterministic enough retrieval for agent loops
- provenance and benchmark discipline

If a proposal cannot say which evidence bucket it satisfies, it is not ready.

## Current bottom line

The practical rule for Snowiki right now is:

1. **lexical backbone first**
2. **canonical retrieval contract before more sophistication**
3. **Korean/mixed-language lexical evaluation before semantic escalation**
4. **hybrid/rerank/local-model/backend work only when benchmark evidence and operational fit both justify it**

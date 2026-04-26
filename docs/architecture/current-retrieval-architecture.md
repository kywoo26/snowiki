# Current Retrieval Architecture

## Purpose

This document describes Snowiki’s current retrieval architecture.

The goal is to keep CLI, MCP, and bench aligned without turning any one of them into a separate contract universe.

## Active retrieval surfaces

Snowiki’s retrieval stack shows up through three surfaces:

1. CLI query and recall
2. Read only MCP retrieval
3. Bench evaluation runs

## The BM25 lexical backbone

The current active retrieval backbone is BM25 lexical candidate generation with deterministic result adaptation.

Primary modules:

- `src/snowiki/search/engine.py`
- `src/snowiki/search/protocols.py`
- `src/snowiki/search/bm25_index.py`
- `src/snowiki/search/corpus.py`
- `src/snowiki/search/indexer.py`
- `src/snowiki/search/tokenizer.py`
- `src/snowiki/search/queries/*`

## Canonical retrieval seam

The shared retrieval seam is centered on `src/snowiki/search/workspace.py`.

Its role is to:

1. turn normalized records into search ready structures
2. turn compiled pages into search ready structures
3. build a BM25 runtime retrieval snapshot
4. provide the common retrieval contract used across runtime surfaces

`RetrievalSnapshot.index` is the primary runtime search surface and implements
`RuntimeSearchIndex` through `BM25RuntimeIndex`.

## Canonical retrieval contract

The installed CLI defines the current runtime contract. Other surfaces mirror or specialize that contract.

### Retrieval surface parity

| Category | Meaning |
| :--- | :--- |
| Routing parity | Surfaces should use the same strategy layers for the same intent. |
| Metadata parity | Result structures should preserve identity, score, and provenance fields. |
| Freshness parity | Surfaces should expose consistent generation identities. |
| Evaluation boundary parity | Benchmark results should not be treated as the shipped runtime contract. |

## Bench as a thin runner

Bench is a thin retrieval evaluator, not a platform.

It accepts an `EvaluationMatrix`, sends execution through a `RetrievalTargetAdapter`, and returns a `BenchmarkRunResult`.

The bounded extension seams are:

1. dataset manifests
2. target registry
3. metric registry

These seams keep bench flexible without widening the runner model.

## Strategy layers

The retrieval policy wrappers currently live in:

- `src/snowiki/search/queries/known_item.py`
- `src/snowiki/search/queries/topical.py`
- `src/snowiki/search/queries/temporal.py`

These are strategy layers over the same BM25 runtime search substrate, not separate engines.

## Semantic and rerank status

These remain extension seams, not active runtime layers.

- `src/snowiki/search/semantic_abstraction.py`
- `src/snowiki/search/rerank.py`

## Main current risk

The main current architecture risk is drift between surfaces that should all be speaking the same retrieval language.

## Current direction implied by the codebase

The codebase currently points toward this order:

1. canonical retrieval contract
2. BM25 lexical quality and language strategy improvements
3. profiling and performance improvements
4. analyzer promotion gates
5. semantic, graph, and rerank questions

## BM25 runtime

The BM25 runtime is described in
[`bm25-retrieval-engine.md`](bm25-retrieval-engine.md).

The important distinction is that Snowiki should preserve external CLI, MCP,
provenance, and benchmark contracts while BM25 remains the primary retrieval
substrate.

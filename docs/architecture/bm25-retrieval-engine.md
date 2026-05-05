# BM25 Retrieval Engine

## Purpose

This document describes Snowiki's primary lexical retrieval engine.

Snowiki uses BM25 candidate generation for CLI query, CLI recall, read-only MCP
retrieval, and the runtime-shaped benchmark target while preserving the external
runtime contract.

## Decision

BM25 is the primary runtime retrieval substrate.

The compatibility seam is the external result contract, not an internal dual
engine path. CLI and MCP payloads continue to expose stable result fields:

- `id`
- `path`
- `title`
- `kind`
- `source_type`
- `score`
- `matched_terms`
- `summary`

## Runtime architecture

```text
CLI / MCP / benchmark
  -> query and recall orchestration
  -> query intent policy (SearchIntentPolicy preset)
    -> RuntimeSearchRequest
      -> RuntimeSearchIndex.search(request)
        -> BM25RuntimeIndex
          -> SearchDocument records/pages
          -> BM25SearchIndex candidate generation (policy-free raw BM25)
          -> RuntimeScoringPolicy (numeric scoring / ranking)
          -> SearchHit / SearchDocument result adapter
      -> optional post-scoring blend (topical policy, blend_hits_by_kind)
      -> final truncation to user-facing limit
  -> serializer (CLI JSON / MCP payload / benchmark hit)
```

The active implementation lives in:

- `src/snowiki/search/engine.py`
- `src/snowiki/search/protocols.py`
- `src/snowiki/search/bm25_index.py`
- `src/snowiki/search/corpus.py`
- `src/snowiki/search/requests.py`
- `src/snowiki/search/queries/policies.py`
- `src/snowiki/search/scoring.py`
- `src/snowiki/search/workspace.py`
- `src/snowiki/storage/index_manifest.py`

`BM25SearchIndex` is the raw backend. It handles persistence, cache artifacts,
and tokenizer diagnostics. It does not own scoring constants, query multipliers,
kind weights, or request routing. Those responsibilities sit in the policy and
scoring layers above it.

`storage/index_manifest.py` owns the typed manifest and freshness explanation
domain for retrieval identities. BM25 runtime code may consume those explanations,
but it should not parse legacy manifest shapes or infer identity from cache
artifacts. That compatibility boundary stays in storage, where legacy manifests
can be normalized once and explained consistently.

## Query and recall split

`query` and `recall` remain separate user intents.

- `query` is topical document retrieval.
- `recall` is memory reconstruction with time, session, source, and known-item
  clues.

Both use BM25 for candidate generation, while recall keeps first-class routing
for date, temporal, known-item, and topical strategies. All strategies now
construct a `RuntimeSearchRequest` through a `SearchIntentPolicy` preset before
calling the runtime index.

## Analyzer status

The default runtime tokenizer is `kiwi_morphology_v1`. It became the default
after passing Korean, mixed-language, path, code, CLI/tool, known-item,
session/history, latency, and packaging gates while preserving regex as a
supported benchmark and rollback lane.

Tokenizer identity is guarded at the manifest boundary, not by ad hoc runtime
checks. New tokenizer behavior should flow through the shared tokenizer helpers
and registry driven validation in `search/token_util.py`, so the stored index
identity and the active runtime tokenizer stay aligned.

## Deferred work

- Deterministic graph/taxonomy prefilters.
- Optional vector recall and Reciprocal Rank Fusion.
- Optional analyzer follow-ups for non-default lanes described in
  [`analyzer-promotion-gates.md`](analyzer-promotion-gates.md).

Hybrid/vector search and semantic reranking remain deferred non-goals for the
current shipped runtime.

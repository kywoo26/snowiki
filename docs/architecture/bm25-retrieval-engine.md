# BM25 Retrieval Engine

## Purpose

This document describes Snowiki's primary lexical retrieval engine.

Snowiki uses BM25 candidate generation for CLI query, CLI recall, read-only MCP
retrieval, and the runtime-shaped benchmark target while preserving the external
runtime contract.

## Decision

BM25 is the primary runtime retrieval substrate.

The shipped runtime remains BM25/Kiwi lexical retrieval. Snowiki does not ship
hybrid retrieval, vector retrieval, semantic reranking, or Reciprocal Rank
Fusion in the current runtime.

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
  -> canonical topical executor (execute_topical_search)
    -> query intent policy (SearchIntentPolicy preset)
    -> RuntimeSearchRequest
      -> RuntimeSearchIndex.size + search(request)
        -> BM25RuntimeIndex
          -> SearchDocument records/pages
          -> BM25SearchIndex candidate generation (policy-free raw BM25)
          -> HitScorer.rank_candidates()
          -> SearchHit result adapter
    -> optional post-scoring blend (topical policy)
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
kind weights, request routing, or any semantic fallback policy. Those
responsibilities sit in the policy and scoring layers above it.

`BM25RuntimeIndex` is the lexical runtime adapter. It keeps the protocol surface
minimal, forwards raw BM25 candidates into `HitScorer.rank_candidates()`, and
returns scored hits with deterministic ordering.

`RuntimeSearchIndex` exposes only `size` and `search(request)`. The tokenizer is
still available as a concrete backend diagnostic on `BM25SearchIndex`, but it is
not part of the runtime protocol.

The canonical topical lexical executor, `execute_topical_search()`, is shared by
CLI query, read-only MCP search, and the benchmark runtime so request assembly,
blending, and truncation stay aligned.

Phase 7 PR 1 preserved this runtime while tightening the corpus contract around
typed-only `SearchDocument` construction. The runtime no longer keeps mapping
compatibility builders or conversion branches alongside the active lexical path.

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

Topical query execution is centralized in `execute_topical_search()`, which is
the shared executor for CLI, MCP, and benchmark entry points. That executor owns
the request shape and final user-facing limit, while the backend stays policy
free.

## Analyzer status

The default runtime tokenizer is `kiwi_morphology_v1`. It became the default
after passing Korean, mixed-language, path, code, CLI/tool, known-item,
session/history, latency, and packaging gates while preserving regex as a
supported benchmark and rollback lane.

Tokenizer identity is guarded at the manifest boundary, not by ad hoc runtime
checks. New tokenizer behavior should flow through the shared tokenizer helpers
and registry driven validation in `search/token_util.py`, so the stored index
identity and the active runtime tokenizer stay aligned.

## PR 1 boundaries

Phase 7 PR 1 was a retrieval-contract cleanup, not a semantic retrieval launch.

Completed:

- canonical runtime corpus assembly now uses typed-only `SearchDocument`
  builders
- mapping compatibility paths were removed from the runtime retrieval seam
- BM25/Kiwi lexical candidate generation remained the shipped baseline

Deferred:

- semantic or vector retrieval execution
- ANN backend selection or embedding-model default selection
- Reciprocal Rank Fusion runtime behavior
- chunk-level fields added directly to `SearchDocument`
- the removed placeholder APIs, including `semantic_backend`, `NoOpReranker`,
  and the `Reranker` protocol

Any documentation that treats PR 1 as shipped hybrid search would therefore be
incorrect.

## Deferred work

- Deterministic graph/taxonomy prefilters.
- Scoring and query-policy extraction that keeps lexical scoring policy cleanly
  separable from future fusion policy.
- Manifest and vector identity design for future embedding-backed artifacts.
- Retrieval workspace split refinement for future lexical plus hybrid
  orchestration.
- Hybrid benchmark gates that must validate any future semantic or fusion lane
  against the lexical baseline before shipping.
- Optional analyzer follow-ups for non-default lanes described in
  [`analyzer-promotion-gates.md`](analyzer-promotion-gates.md).

Hybrid/vector search and semantic reranking remain deferred non-goals for the
current shipped runtime. Phase 7 PR3 and PR4 are the redesign boundary for any
future semantic or hybrid runtime, so no placeholder API should be treated as
shipped today.

Ordered top-N outputs are preserved, but exact score float values are not a
stability promise. Deterministic tie-breaking follows score descending, then
recency, then path, then id.

## Chunk identity guidance

Future semantic or chunked retrieval work should use a QMD-style chunk identity
pattern such as `(hash, seq, pos)` for stable chunk provenance and ordering.

That guidance is intentionally design-only here:

- do not add chunk or source-span fields to `SearchDocument` yet
- do not treat chunk identity as a settled part of the shipped lexical runtime
- do preserve a clean path for later mapping chunk evidence back to document and
  source provenance

# Current Retrieval Architecture

## Purpose

This document describes Snowiki's current retrieval architecture.

The goal is to keep CLI, MCP, and bench aligned without turning any one of them into a separate contract universe.

## Active retrieval surfaces

Snowiki's retrieval stack shows up through three surfaces:

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
- `src/snowiki/search/requests.py`
- `src/snowiki/search/scoring.py`
- `src/snowiki/search/tokenizer.py`
- `src/snowiki/storage/index_manifest.py`
- `src/snowiki/search/queries/*`

The legacy `src/snowiki/search/indexer.py` and its `InvertedIndex` implementation were removed during the runtime retrieval policy consolidation. All production callers now route through the request/policy boundary described below.

## Canonical retrieval seam

The shared retrieval seam is centered on `src/snowiki/search/workspace.py`.

Its role is to:

1. turn normalized records into search ready structures
2. turn compiled pages into search ready structures
3. build a BM25 runtime retrieval snapshot
4. provide the common retrieval contract used across runtime surfaces

`RetrievalSnapshot.index` is the primary runtime search surface and implements
`RuntimeSearchIndex` through `BM25RuntimeIndex`.

`src/snowiki/storage/index_manifest.py` owns the typed index manifest domain,
including `LayerIdentity`, `RetrievalIdentity`, `IndexIdentity`, `IndexManifest`,
`FreshnessReason`, and `FreshnessExplanation`. That module also owns manifest
path resolution, load and write helpers, identity comparison, and freshness
explanations. `search/workspace.py` stays a thin facade over those storage and
runtime seams.

The retrieval workspace split is:

- `src/snowiki/search/cache.py`, snapshot cache ownership
- `src/snowiki/search/runtime_service.py`, `RetrievalService` runtime orchestration
- `src/snowiki/search/workspace.py`, thin facade that bridges normalized data,
  compiled pages, cache state, and runtime snapshot construction

Legacy on-disk manifest shapes remain supported only through the compatibility
parser boundary in `storage/index_manifest.py`. `parse_index_manifest` and
`normalize_legacy_index_manifest` exist so older artifacts can be read and
explained, but they do not move manifest parsing responsibility back into
`workspace.py`, `status`, `lint`, or `rebuild`.

## Runtime retrieval policy boundary

The canonical retrieval flow now moves through an explicit request and policy boundary:

```text
query intent (known-item / topical / temporal / date)
  -> SearchIntentPolicy (candidate multiplier, kind weights, exact-path bias, blending flag)
    -> RuntimeSearchRequest (query, candidate_limit, filters, policy fields)
      -> BM25RuntimeIndex.search(request)
        -> BM25SearchIndex raw candidate generation (policy-free)
          -> RuntimeScoringPolicy (exact-path boost, path-phrase boost, kind-weight multiplication, recency tie-break)
            -> optional post-scoring blend (topical policy only)
              -> final truncation to user-facing limit
                -> serializer (CLI JSON / MCP payload / benchmark hit)
```

Boundary responsibilities:

| Layer | Module | Responsibility |
| :--- | :--- | :--- |
| Intent policy | `src/snowiki/search/queries/policies.py` | Named presets (`KNOWN_ITEM_POLICY`, `TOPICAL_POLICY`, `TEMPORAL_POLICY`), candidate-limit expansion, kind-weight defaults, exact-path bias, blending flags. |
| Request object | `src/snowiki/search/requests.py` | Frozen `RuntimeSearchRequest` with `query`, `candidate_limit`, temporal filters, `exact_path_bias`, `kind_weights`, and optional `scoring_policy`. |
| Protocol | `src/snowiki/search/protocols.py` | `RuntimeSearchIndex.search(request: RuntimeSearchRequest) -> Sequence[SearchHit]`. |
| Raw candidate generation | `src/snowiki/search/bm25_index.py` | Policy-free BM25 candidate retrieval. No scoring constants, multipliers, or blending logic lives here. |
| Runtime scoring | `src/snowiki/search/scoring.py` | `RuntimeScoringPolicy` owns matched-term derivation, zero-score rejection, exact-path/token boosts, kind-weight multiplication, recency tie-break, and deterministic sort key. |
| Runtime orchestration | `src/snowiki/search/engine.py` | `BM25RuntimeIndex` translates `RuntimeSearchRequest` into raw BM25 calls, applies `RuntimeScoringPolicy`, and returns scored `SearchHit`s. |
| Post-scoring blend | `src/snowiki/search/rerank.py` | `blend_hits_by_kind` is a query-policy-controlled topical behavior, not a numeric scoring layer. |
| Strategy wrappers | `src/snowiki/search/queries/known_item.py`, `topical.py`, `temporal.py` | Own final truncation, optional reranking, and routing to the runtime index via `RuntimeSearchRequest`. |
| Index manifest and freshness | `src/snowiki/storage/index_manifest.py` | Owns typed identity, manifest persistence, legacy normalization, current identity computation, comparison, and freshness explanations. |

Key invariants:

- `candidate_limit` is the pre-truncation candidate count requested from the runtime index. Final display limits stay in query-policy functions.
- `BM25SearchIndex` remains policy-free. It does not know about request objects, intent multipliers, kind weights, or scoring profiles.
- Scoring constants and policy literals live only in `scoring.py` and `queries/policies.py`, not in `engine.py` or individual query modules.
- CLI, MCP, and benchmark payloads remain stable; only internal routing changed.
- Manifest identity and freshness are storage concerns, not runtime query concerns. Runtime surfaces should consume the manifest explanation produced by `storage/index_manifest.py` instead of re-deriving identity from cache state or command-specific heuristics.

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

- `src/snowiki/search/queries/policies.py`
- `src/snowiki/search/queries/known_item.py`
- `src/snowiki/search/queries/topical.py`
- `src/snowiki/search/queries/temporal.py`

These are strategy layers over the same BM25 runtime search substrate, not separate engines. `queries/policies.py` centralizes the intent-specific constants that were previously embedded as literals in each query module.

## Semantic and rerank status

These remain extension seams, not active runtime layers.

- `src/snowiki/search/semantic_abstraction.py`
- `src/snowiki/search/rerank.py`

Hybrid/vector search and semantic reranking are deferred non-goals for the current runtime. See `bm25-retrieval-engine.md` for the deferred work list.

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

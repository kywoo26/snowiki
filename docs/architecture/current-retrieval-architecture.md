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

The shipped runtime remains lexical-only. Hybrid retrieval, vector retrieval,
semantic reranking, and Reciprocal Rank Fusion (RRF) are not active runtime
layers today.

The canonical topical lexical executor is `execute_topical_search()` in
`src/snowiki/search/queries/topical.py`. CLI query, read-only MCP search, and
the benchmark runtime all route through that executor so request construction,
candidate limits, blending, and final truncation stay in one place.

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

1. turn typed normalized records into `SearchDocument` values
2. turn typed compiled pages into `SearchDocument` values
3. build a BM25 runtime retrieval snapshot
4. provide the common retrieval contract used across runtime surfaces

PR 1 of Phase 7 narrowed this seam to a typed-only corpus contract. Runtime
corpus construction now flows through `search_document_from_normalized_record`,
`search_document_from_compiled_page`, and
`runtime_corpus_from_records_and_pages` in `src/snowiki/search/corpus.py`.
The older mapping-compatibility path was removed instead of being carried
forward as a second runtime contract.

`RetrievalSnapshot.index` is the primary runtime search surface and implements
`RuntimeSearchIndex` through `BM25RuntimeIndex`.

`RuntimeSearchIndex` exposes only `size` and `search(request)`. Tokenizer access
is a concrete backend diagnostic on `BM25SearchIndex`, not a protocol-level
requirement.

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

This means the current runtime no longer maintains a parallel dict or mapping
corpus builder inside the retrieval path. Typed schema objects are the only
supported inputs for runtime corpus assembly.

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
| Protocol | `src/snowiki/search/protocols.py` | `RuntimeSearchIndex` exposes `size` and `search(request: RuntimeSearchRequest) -> Sequence[SearchHit]`. |
| Raw candidate generation | `src/snowiki/search/bm25_index.py` | Policy-free BM25 candidate retrieval. No scoring constants, multipliers, or blending logic lives here. |
| Runtime scoring | `src/snowiki/search/scoring.py` | `HitScorer.rank_candidates()` owns matched-term derivation, zero-score rejection, exact-path/token boosts, kind-weight multiplication, recency tie-break, and deterministic sort key. |
| Runtime orchestration | `src/snowiki/search/engine.py` | `BM25RuntimeIndex` translates `RuntimeSearchRequest` into raw BM25 calls, then delegates ranking to `HitScorer`. |
| Canonical topical executor | `src/snowiki/search/queries/topical.py` | `execute_topical_search()` builds the request, applies topical policy, handles blending, and performs the final truncation used by CLI, MCP search, and benchmark. |
| Strategy wrappers | `src/snowiki/search/queries/known_item.py`, `topical.py`, `temporal.py` | Own final truncation, optional reranking, and routing to the runtime index via `RuntimeSearchRequest`. |
| Index manifest and freshness | `src/snowiki/storage/index_manifest.py` | Owns typed identity, manifest persistence, legacy normalization, current identity computation, comparison, and freshness explanations. |

Key invariants:

- `candidate_limit` is the pre-truncation candidate count requested from the runtime index. Final display limits stay in query-policy functions.
- `BM25SearchIndex` remains policy-free. It does not know about request objects, intent multipliers, kind weights, or scoring profiles.
- Scoring constants and policy literals live only in `scoring.py` and `queries/policies.py`, not in `engine.py` or individual query modules.
- `RuntimeSearchIndex` keeps a minimal contract, `size` plus `search(request)`, so backend diagnostics do not become required runtime behavior.
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

The active runtime no longer carries placeholder semantic APIs such as
`semantic_backend`, `NoOpReranker`, or a `Reranker` protocol. Phase 7 PR3 and
PR4 are the boundary for redesigning semantic and hybrid retrieval after the
current lexical consolidation lands.

Hybrid/vector search and semantic reranking are deferred non-goals for the
current runtime. See `bm25-retrieval-engine.md` for the deferred work list.

## Phase 7 PR 1 boundaries

Phase 7 PR 1 completed the contract cleanup required before any future
hybrid-search work can be evaluated safely.

Done in PR 1:

- runtime corpus construction is typed-only and produces `SearchDocument`
  directly
- mapping compatibility paths were deleted from the runtime retrieval seam
- ghost terminology from the old dual-contract model was removed from the
  active runtime description
- BM25 with the Kiwi lexical analyzer remained the shipped runtime baseline

Not done in PR 1:

- no semantic retrieval implementation
- no vector index, embedding pipeline, or ANN backend commitment
- no Reciprocal Rank Fusion runtime layer
- no chunk fields or vector identity fields added to `SearchDocument`

PR 1 should therefore be read as a boundary-cleanup change, not as a shipped
hybrid retrieval milestone.

## Hybrid-readiness roadmap

The next architecture steps remain explicitly deferred until follow-up PRs:

1. scoring and query-policy extraction so lexical ranking policy stays
   isolated from any later fusion policy
2. manifest and vector identity design so vector artifacts can be tracked
   without weakening the current typed manifest contract
3. retrieval workspace split refinement so corpus assembly, runtime search,
   and future hybrid orchestration can evolve independently
4. hybrid benchmark gates so any semantic or fusion experiment must earn its
   place against the lexical baseline before it can ship

None of those roadmap items change the current runtime claim: the shipped
engine is BM25/Kiwi lexical retrieval.

## Chunk And Source-Span Guidance

Future chunked or semantic retrieval work should follow the QMD-style identity
pattern of `(hash, seq, pos)` for chunk provenance and ordering.

The important current constraint is architectural, not schema-driven:

- keep `SearchDocument` as the current lexical runtime contract
- treat chunk identity and source-span metadata as a future companion layer,
  not as fields to add prematurely to `SearchDocument`
- preserve the ability to map chunk-level evidence back to stable document and
  source identities without making the lexical runtime depend on chunk-aware
  storage today

If chunk retrieval is introduced later, source-span design should preserve
stable document provenance first and treat chunk coordinates as an additional
indexing identity rather than as a replacement for the current document-level
contract.

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

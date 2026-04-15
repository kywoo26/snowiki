# Step 4 Analysis Notes

## Current internal seam posture

### What exists
- `src/snowiki/search/semantic_abstraction.py`
  - `SemanticBackend` protocol with `enabled: bool` and `search(query, documents, limit) -> list[SearchHit]`
  - `DisabledSemanticBackend` — frozen dataclass that returns `[]`
  - **No concrete vector backend, no embedding storage, no lifecycle hooks**
- `src/snowiki/search/rerank.py`
  - `Reranker` protocol
  - `NoOpReranker`
  - `blend_hits_by_kind(hits, limit)` — round-robin interleaving by `document.kind`
- `src/snowiki/search/workspace.py`
  - Builds runtime retrieval snapshot from compiler outputs
  - Current assembly: lexical + wiki + blended inverted index only
  - `content_freshness_identity()` and cache-key invalidation exist for snapshot lifecycle
- `src/snowiki/daemon/warm_index.py`
  - Warm snapshot reload and staleness tracking
  - Can be extended to vector index cache invalidation

### What does not exist
- No runtime vector pipeline.
- No embedding model lifecycle.
- No candidate fan-out or score fusion layer.
- `topical_recall()` assumes a single `InvertedIndex`; hybrid needs a higher-level search service or candidate-merge layer.
- `build_blended_index()` is currently document union only, not score fusion.

### Nearest chunking/integration points
- `CompilerEngine.build_pages()` and `CompiledPage.sections` / `PageSection` — natural chunk boundaries.
- `workspace.page_body()`, `compiled_page_to_search_mapping()`, `normalized_record_to_search_mapping()` — text materialization seam.
- `indexer.document_from_mapping()` — document conversion seam.
- `index_lexical.py` / `index_wiki.py` — adapter seams that could be duplicated for vector/chunk adapters.
- `bench/baselines.py` — already maps `SearchDocument` ↔ `BM25SearchDocument`, showing how a second backend adapter can sit alongside the inverted index.

## Required new components for hybrid

1. **Chunker** — slice `CompiledPage.sections` and `NormalizedRecord.content` into embeddable chunks with provenance.
2. **Embedder lifecycle** — model selection, lazy loading, CPU fallback, version tracking, cache invalidation.
3. **Vector store** — per-chunk embeddings with metadata linking back to source document/section.
4. **Candidate fan-out service** — run BM25 and vector queries in parallel (or sequentially with shortcut).
5. **Fusion layer** — RRF or weighted score fusion over candidate lists keyed by document identity.
6. **Strong-signal shortcut** — skip vector/fusion/rerank when BM25 signal is clearly dominant.
7. **Rerank cache** — optional cross-encoder rerank with query+doc cache keys.

## How the seams should evolve

```text
Current:
  compiler output
    -> workspace (lexical + wiki inverted indexes)
      -> topical_recall() on blended inverted index
        -> rerank/blend by kind

Future:
  compiler output
    -> workspace
      -> lexical inverted index (existing)
      -> BM25 index (from benchmark seam, promoted)
      -> vector index (new: chunk + embed + store)
    -> query fan-out
      -> BM25 probe
      -> strong-signal shortcut?
         yes -> return BM25 results early
         no  -> vector retrieval
    -> fusion (RRF or weighted)
    -> rerank (optional, cached)
    -> blend by kind / final truncation
```

## Key design decision: where does fusion live?

Option A — inside `workspace.py` / `RetrievalService`
- Pros: keeps all retrieval assembly in one place.
- Cons: `workspace.py` becomes a monolith; harder to unit-test fusion in isolation.

Option B — new `search/hybrid.py` module with a `HybridSearchService`
- Pros: fusion logic is testable independently; `workspace.py` only builds indexes.
- Cons: another abstraction layer to maintain.

**Current leaning: Option B.** `workspace.py` should remain an index builder; a new `HybridSearchService` should own fan-out, shortcut, fusion, and rerank orchestration.

## External reference — concrete parameters

### qmd (`tobi/qmd`)
- **RRF**: `k=60`, raw reciprocal-sum, **no normalization**, no position bonus.
  - `hybridQuery()` weights first 2 lists at `2.0`; `structuredSearch()` weights first list at `2.0`.
- **Strong-signal shortcut**: `topScore >= 0.85` AND `topScore - secondScore >= 0.15`; disabled when `intent` is provided.
- **Expansion modes**: typed `lex` (→ FTS), `vec/hyde` (→ vector); fallback on invalid output.
- **Rerank + cache**: reranks **after fusion** on best **chunks** (not full docs); cache key is `query + model + chunk`.
- **Candidate limit**: 40 before rerank; final dedup by **filepath** (no session cap).
- **Fallback**: if vectors table missing/embedding fails, vector returns `[]`; hybrid continues with FTS/lex paths.

### `vlwkaos/ir`
- **Score fusion** (before RRF): `combined = 0.80·vec_score + 0.20·bm25_score`.
  - Tuned on BEIR/NFCorpus plateau (α=0.70–0.95).
- **Strong-signal shortcut**:
  - Fused: `top >= 0.40` AND `top * gap >= 0.06`
  - BM25-only tier-0: `top >= 0.75` AND `gap >= 0.10`
- **RRF**: `k=60` with position bonuses: rank 0 → `+0.05`, ranks 1–2 → `+0.02`.
  - Weights: first list `1.0`, subsequent lists `0.8`.
- **Expansion**: runs **only if scorer exists**; typed `lex|vec|hyde`; invalid output falls back to `lex=query`, `vec=query`, `hyde="Information about {query}"`.
- **Rerank placement + cache**: reranks only **top 20** after fusion/expansion; cache key is `sha256(model_id + "\0" + query + "\0" + content_hash)`; prefix caching for shared prompt.
- **Diversity/caps**: no session cap; dedup by `(collection, path)`.
- **Fallback**: tier-1 daemon loads embedder only; tier-2 expander/reranker optional; on failure, CLI returns BM25 results.

### `seCall`
- **RRF**: `k=60`, `1/(k+rank+1)`, then **normalize to 0–1** by max score. No position bonus.
- **Strong-signal shortcut**: **none**; always runs BM25 + optional vector + fuse.
- **Expansion**: separate keyword append (not typed `lex/vec/hyde` in hybrid path); cache TTL **7 days**; on failure returns original query.
- **Rerank**: none in hybrid search.
- **Diversity/caps**: `diversify_by_session()` with default `max_per_session = 2`.
- **Fallback**: `create_vector_indexer()` returns `None` if all backends fail; then BM25-only. ANN falls back to BLOB cosine scan if stale.

## Synthesis for Snowiki

| Component | Recommended starting point | Rationale |
| :--- | :--- | :--- |
| **Fusion** | RRF (`k=60`) with **position bonus** (like `ir`) | Simple, well-tested, gives top ranks a slight edge. |
| **Score normalization** | Normalize by max (like `seCall`) or no normalization (like `qmd`/`ir`) | Try both; normalization makes thresholding easier. |
| **Strong-signal shortcut** | Adopt `ir`’s two-tier shortcut: BM25-only tier-0 + fused tier-1 | Saves latency on obvious matches without over-eager skipping. |
| **Expansion** | Deferred; only after reranker is proven | `ir` explicitly warns expansion without rerank is harmful. |
| **Rerank** | Optional top-20 chunk-level rerank with query+doc hash cache | Matches `ir`/`qmd` evidence; avoids full-document scoring trap. |
| **Diversity** | Optional session cap (default 2) | `seCall` shows this prevents one source from flooding results. |
| **Fallback** | BM25-only when vector/embedder unavailable | All three systems converge on this. |

## File references
- `src/snowiki/search/semantic_abstraction.py` — semantic backend protocol stub
- `src/snowiki/search/rerank.py` — rerank protocol and kind-blending
- `src/snowiki/search/workspace.py` — runtime snapshot assembly
- `src/snowiki/search/indexer.py` — core inverted index and document model
- `src/snowiki/compiler/taxonomy.py` — `CompiledPage`, `PageSection` chunking boundary
- `src/snowiki/daemon/warm_index.py` — snapshot lifecycle and cache invalidation
- `src/snowiki/bench/baselines.py` — BM25 adapter pattern that can be promoted to runtime

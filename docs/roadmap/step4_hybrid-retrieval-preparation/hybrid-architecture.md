# Hybrid Architecture Memo

## 1. Purpose

This document defines the target architecture for Snowiki’s hybrid retrieval layer. It specifies the seam design, component boundaries, fallback rules, and mode-gated API surface required to add BM25 + vector + fusion + rerank **without** making it the default runtime path prematurely.

The design draws directly from the qmd / `vlwkaos/ir` / `seCall` lineage, adapted to Snowiki’s existing lexical backbone and chunking model.

---

## 2. Design Principles

1. **Lexical-first default**: The CLI `query` and `recall` commands remain lexical-only by default. Hybrid is an opt-in mode (`--mode hybrid`) or benchmark slice.
2. **Fallback is not failure**: If the vector path is unavailable (model missing, CPU-only host, stale index), the system must return BM25 results cleanly and immediately.
3. **Shortcut saves latency**: When BM25 signal is already dominant, skip expensive dense retrieval, fusion, and rerank.
4. **Chunk-level provenance**: Every vector candidate must trace back to a specific document and, where applicable, a `PageSection` or record slice.
5. **No cloud dependency**: The primary embedding path is local CPU inference. GPU acceleration is optional; cloud APIs are out of scope for the canonical path.
6. **Evaluation gates promotion**: Hybrid does not become the default until benchmark evidence proves it improves semantic recall without regressing exact-match / known-item performance.

---

## 3. Component Architecture

### 3.1 High-level data flow

```
compiler output (pages + records)
    |
    v
workspace.py / RetrievalService
    |-- lexical inverted index  (existing)
    |-- BM25 index              (promote from bench seam)
    |-- vector index            (new: chunk + embed + store)
    |
    v
HybridSearchService  (new: src/snowiki/search/hybrid.py)
    |-- strong-signal shortcut?
    |       yes -> return BM25-only early
    |       no  -> proceed
    |-- candidate fan-out
    |       |-- BM25 probe
    |       +-- vector retrieval
    |-- fusion (RRF or weighted)
    |-- optional rerank (top-20 chunks)
    |-- diversity cap / dedup
    |-- kind-blend / final truncation
    |
    v
results
```

### 3.2 New components

| Component | File | Responsibility |
| :--- | :--- | :--- |
| **Chunker** | `src/snowiki/search/chunker.py` | Splits `CompiledPage.sections` and `NormalizedRecord.content` into embeddable chunks with `(doc_id, section_index, char_offset)` provenance. |
| **Embedder lifecycle** | `src/snowiki/search/embedder.py` | Model selection, lazy loading, CPU fallback, version tracking, cache invalidation. |
| **Vector store** | `src/snowiki/search/vector_store.py` | Per-chunk dense embeddings with metadata back-links. SQLite-backed with model-versioned tables. |
| **Hybrid search service** | `src/snowiki/search/hybrid.py` | Orchestrates fan-out, shortcut, fusion, rerank, and fallback. |
| **Fusion layer** | Inside `hybrid.py` | RRF and optional weighted score fusion over candidate lists keyed by `(collection, path)`. |
| **Rerank cache** | `src/snowiki/search/rerank_cache.py` | Query+chunk content-hash keyed cache for cross-encoder rerank scores. |

### 3.3 Existing components to extend

| Component | Extension |
| :--- | :--- |
| `workspace.py` / `RetrievalService` | Build and expose the vector index alongside the lexical index. Keep `workspace.py` as an index builder, not a fusion owner. |
| `daemon/warm_index.py` | Invalidate and warm-reload the vector index snapshot using the same content-derived identity used for lexical invalidation. |
| `bench/baselines.py` | Promote the BM25 adapter from benchmark-only to a runtime-ready seam. |
| `search/rerank.py` | Extend the `Reranker` protocol with a chunk-level signature: `rerank(query: str, chunks: list[ChunkCandidate]) -> list[ChunkCandidate]`. |

---

## 4. Fusion Design

### 4.1 Reciprocal Rank Fusion (RRF)

**Parameters** (synthesized from qmd / ir / seCall):
- `k = 60`
- **Position bonus** (from `ir`):
  - rank 0 → `+0.05`
  - ranks 1–2 → `+0.02`
- **List weights** (from `ir`):
  - first list (typically BM25) → `1.0`
  - subsequent lists (vector, expansion) → `0.8`
- **Score formula**:
  ```
  rrf_score = weight * (1 / (k + rank + 1) + position_bonus)
  ```
- **Normalization**: none at first (qmd/ir style). If threshold tuning proves difficult, add max-normalization (seCall style) as a later experiment.

### 4.2 Weighted score fusion (alternative)

If RRF alone underperforms on mixed-language queries, support an optional weighted fusion mode:
- `combined = 0.80 * vec_score + 0.20 * bm25_score`
- This matches `ir`’s BEIR/NFCorpus tuning. It requires both candidate lists to expose comparable normalized scores.

**Decision rule**: Start with RRF. Add weighted fusion only if benchmark evidence shows a consistent lift.

---

## 5. Strong-Signal Shortcut

To avoid paying vector + fusion + rerank latency on obvious matches, we adopt `ir`’s two-tier shortcut rule.

### 5.1 Tier-0: BM25-only shortcut

If the top BM25 result is already overwhelmingly strong, return BM25 results immediately.

```
if top_bm25_score >= 0.75 AND (top_bm25_score - second_bm25_score) >= 0.10:
    return bm25_results
```

### 5.2 Tier-1: Fused shortcut

After running both BM25 and vector retrieval (but before fusion/rerank), if the fused candidate list is already clearly dominant, shortcut early.

```
if top_fused_score >= 0.40 AND (top_fused_score * score_gap) >= 0.06:
    return fused_results_without_rerank
```

*Note*: `score_gap` is `(top - second) / top` or absolute difference, depending on the fusion mode. The exact gap metric should be validated against the benchmark corpus.

### 5.3 When shortcuts are disabled

- When the user explicitly requests `--mode hybrid` or `--no-shortcut`.
- When benchmark/evaluation mode is active (we need full-path measurements).

---

## 6. Expansion Policy

**Deferred until reranker is proven.**

The qmd lineage supports typed query expansion (`lex`, `vec`, `hyde`). However, `vlwkaos/ir` explicitly warns: **"Expansion without reranking is harmful."**

Therefore:
- Phase 1 (initial hybrid PoC): **no expansion**.
- Phase 2: After a chunk-level reranker is benchmarked and stabilized, add a simple `hyde`-style expansion behind a feature flag.

When expansion is eventually added:
- Fallback on invalid LLM output: `lex = original_query`, `vec = original_query`, `hyde = "Information about {original_query}"`.
- Cache expansion results with a query-hash keyed TTL (7 days, seCall style).

---

## 7. Rerank Design

### 7.1 Placement

Rerank operates **after fusion** on the **top-20 chunks** (not full documents). This matches both qmd and ir evidence.

### 7.2 Cache

Cache key: `sha256(model_id + "\0" + query + "\0" + chunk_content_hash)`

- Prefix caching for shared prompts is desirable but optional for the first implementation.
- TTL: 24 hours for in-process cache; persistent cache is unnecessary for the CLI default.

### 7.3 Model policy

- Primary: a small local cross-encoder (e.g., `BAAI/bge-reranker-base` or `jina-reranker-v1-tiny-en`).
- Fallback: if the reranker model is unavailable, return fused results unchanged.
- The reranker itself is optional; hybrid must work without it.

---

## 8. Diversity and Deduplication

### 8.1 Deduplication

Candidates are keyed by `(collection, path)`.
- BM25 and vector may return the same document with different chunk offsets.
- Collapse duplicate documents by keeping the highest-scoring chunk per document.

### 8.2 Session diversity cap

Following `seCall`, apply an optional `max_per_session` cap (default `2`) during final truncation.
- This prevents a single long session or source from flooding the result list.
- The cap is applied **after** fusion and **before** rerank, so the reranker still sees a diverse candidate set.
- Disable the cap in exact-match / known-item mode.

---

## 9. Chunking Boundary Policy

### 9.1 Source material

- `CompiledPage.sections` (`compiler/taxonomy.py`) — natural semantic boundaries.
- `NormalizedRecord.content` (`search/workspace.py`) — session or source text.

### 9.2 Chunk format

```python
@dataclass(frozen=True)
class Chunk:
    chunk_id: str               # hash or deterministic surrogate
    doc_path: str               # source document path
    section_index: int | None   # index within CompiledPage.sections
    char_offset: int
    text: str
```

### 9.3 Chunking strategy

- **Markdown pages**: split on `##` / `###` headers where possible; hard-limit to 512 tokens per chunk with 64-token overlap.
- **Plain records**: sentence-boundary chunking with the same token limit.
- **Code blocks**: keep intact if under the token limit; if oversized, split on blank lines.
- **Tables**: prefer to keep entire tables in one chunk; if oversized, row-group chunking.
- **Images / attachments**: excluded from embedding (text alt-text only).

### 9.4 Provenance rule

Every `Chunk` must embed back to its origin document. Every search hit derived from a chunk must expose `doc_path`, `section_index`, and `char_offset` so the agent can retrieve the exact source text.

---

## 10. Embedder Lifecycle

### 10.1 Model selection

| Tier | Model | Use case |
| :--- | :--- | :--- |
| Default | `BAAI/bge-small-en-v1.5` or `BAAI/bge-m3` | Local CPU, multilingual, good balance. |
| Fallback | `sentence-transformers/all-MiniLM-L6-v2` | Smaller download, faster inference, lower quality. |

**Decision rule**: `bge-m3` is preferred if Korean mixed-language performance is critical. `bge-small-en-v1.5` is acceptable if English dominates and Korean is handled primarily by the BM25 sparse branch.

*Open question* (to be resolved in Step 2 benchmark): final model choice depends on the mixed-language corpus evaluation.

### 10.2 Lazy loading

- The embedder is loaded only on the first hybrid/vector query or explicit `rebuild --vector` call.
- If the model is not present locally, the system attempts an **optional** download with user confirmation (CLI) or host pre-seeding (MCP/daemon).
- If loading fails, the embedder returns `None` and the system falls back to BM25-only.

### 10.3 Version tracking

The vector store schema includes a `model_version` column/table.
- When the configured model changes, existing vector tables are treated as stale.
- Rebuild triggers a full re-embedding.
- Daemon warm snapshots include `model_version` in their cache key.

---

## 11. Vector Store Design

### 11.1 Storage backend

SQLite, co-located with the lexical index database (per-collection or global, following existing storage patterns).

### 11.2 Schema

```sql
CREATE TABLE vector_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_path TEXT NOT NULL,
    section_index INTEGER,
    char_offset INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB NOT NULL,   -- f32 array
    model_version TEXT NOT NULL
);

CREATE INDEX idx_vector_doc ON vector_chunks(doc_path);
CREATE INDEX idx_vector_model ON vector_chunks(model_version);
```

### 11.3 Retrieval

- Exact cosine similarity scan for the PoC (collections are small enough that brute-force is acceptable).
- ANN (HNSW or similar) is deferred until brute-force latency is proven unacceptable.
- Following `seCall`, if an ANN index exists but is stale, fall back to the BLOB cosine scan.

---

## 12. Mode-Gated API Surface

### 12.1 CLI modes

| Mode | Behavior | Default? |
| :--- | :--- | :--- |
| `lexical` | BM25/inverted-index only. | **Yes** |
| `hybrid` | BM25 + vector + fusion + optional rerank + shortcut. | No |
| `vector` | Dense retrieval only (diagnostic / benchmark). | No |

Proposed CLI addition:
```bash
snowiki query "..." --mode hybrid
snowiki recall "..." --mode hybrid
snowiki benchmark --preset retrieval --mode hybrid
```

### 12.2 MCP policy

The MCP surface remains **read-only**. Hybrid search is exposed as an optional parameter on existing tools:
- `search` tool gains an optional `mode` argument (`lexical` | `hybrid` | `vector`).
- `recall` tool gains the same.
- Default is `lexical` to prevent silent latency changes for existing MCP consumers.

### 12.3 Daemon policy

The daemon warm snapshot builds all three indexes (lexical, BM25, vector) if the embedder is available. The query path respects the `mode` parameter without rebuilding the snapshot per request.

---

## 13. Fallback Rules

### 13.1 Embedding failure

If the embedder fails to load or the model is missing:
1. Log a warning.
2. Return BM25-only results.
3. Surface a diagnostic field in JSON output: `"fallback_reason": "embedder_unavailable"`.

### 13.2 Vector store missing/stale

If the vector store is missing or the model version mismatches:
1. Build BM25 results.
2. Skip vector retrieval and fusion.
3. Surface `"fallback_reason": "vector_store_stale"`.

### 13.3 Reranker failure

If the reranker model is missing:
1. Return fused results.
2. Surface `"fallback_reason": "reranker_unavailable"`.

### 13.4 Shortcut triggered

If a strong-signal shortcut fires:
1. Return the shortcut result.
2. Surface `"shortcut_applied": true` and `"shortcut_tier": "0"` or `"1"`.

---

## 14. Evaluation Gates (Promotion Criteria)

Hybrid retrieval may be promoted to the default runtime **only** when all of the following are true:

1. **Recall lift**: On a benchmark slice of semantic/paraphrase queries, hybrid achieves ≥ +10% recall@5 vs. lexical-only.
2. **Exact-match preservation**: On known-item and exact-match queries, hybrid shows no regression (> -2%) in top-1 accuracy vs. lexical-only.
3. **Latency envelope**: p95 query latency on a representative vault (≤ 500 pages) is ≤ 2× the lexical p95.
4. **Shortcut coverage**: The strong-signal shortcut fires on ≥ 30% of queries, saving measurable latency.
5. **Fallback reliability**: All integration tests pass with the embedder disabled (BM25-only fallback).
6. **Provenance integrity**: Every hybrid result hit includes `doc_path`, `section_index`, and `char_offset`.

Until these gates are met, `--mode hybrid` remains an opt-in flag and a benchmark slice.

---

## 15. Sequencing Within Step 4

The implementation of Step 4 should follow this order:

1. **Chunker + vector store schema** (no embedder yet).
2. **BM25 promotion** from `bench/` to runtime seam.
3. **Embedder lifecycle** with lazy loading and CPU fallback.
4. **HybridSearchService skeleton** with BM25-only fallback.
5. **RRF fusion** + strong-signal shortcut.
6. **Rerank hook** (optional, cached).
7. **Benchmark integration** and evaluation-gate measurement.
8. **Daemon/MCP mode parameter plumbing**.

---

## 16. Summary of Borrowed Parameters

| Parameter | Source | Snowiki Adaptation |
| :--- | :--- | :--- |
| RRF `k=60` | qmd, ir, seCall | Adopted directly. |
| RRF position bonus (+0.05 / +0.02) | ir | Adopted directly. |
| RRF list weights (1.0 / 0.8) | ir | Adopted directly. |
| Score fusion `0.8·vec + 0.2·bm25` | ir | Alternative mode, not default. |
| Shortcut tier-0: `top>=0.75, gap>=0.10` | ir | Adopted for BM25-only shortcut. |
| Shortcut tier-1: `top>=0.40, top*gap>=0.06` | ir | Adopted for fused shortcut. |
| Top-20 chunk rerank | qmd, ir | Adopted directly. |
| `max_per_session = 2` | seCall | Adopted as optional diversity cap. |
| BM25-only fallback | qmd, ir, seCall | Adopted as canonical fallback. |
| No expansion without rerank | ir | Expansion deferred until reranker is proven. |

This memo is the canonical architecture target for Snowiki’s hybrid retrieval preparation. Implementation details may evolve during the PoC, but any deviation from these parameters must be justified with benchmark evidence.

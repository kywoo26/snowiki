# seCall — Snowiki Analysis Notes

## Repository
- https://github.com/hang-in/seCall
- Local clone: `/home/k/local/seCall`

## What this is
Korean-aware local session search engine: vault as source of truth, BM25 + vector + RRF, deterministic graph build + optional LLM semantic enrichment.

## Key files to analyze for Snowiki

### Vault model
- `crates/secall-core/src/vault/mod.rs` — vault initialization and structure
- `crates/secall-core/src/vault/init.rs` — vault bootstrap
- `crates/secall-core/src/vault/index.rs` — index.md maintenance
- `crates/secall-core/src/vault/log.rs` — log.md maintenance

### Search / retrieval
- `crates/secall-core/src/search/bm25.rs` — BM25 query and result normalization
- `crates/secall-core/src/search/tokenizer.rs` — Lindera default, optional Kiwi, fallback logic
- `crates/secall-core/src/search/vector.rs` — vector path and BM25-only fallback
- `crates/secall-core/src/search/hybrid.rs` — RRF fusion and diversity cap
- `crates/secall-core/src/search/chunker.rs` — context-aware chunking
- `crates/secall-core/src/search/ann.rs` — HNSW / BLOB cosine fallback

### Graph extraction
- `crates/secall-core/src/graph/extract.rs` — deterministic frontmatter/rules-based edges
- `crates/secall-core/src/graph/build.rs` — graph construction and incremental rebuild
- `crates/secall-core/src/graph/semantic.rs` — optional LLM semantic edges with fallback

### Storage
- `crates/secall-core/src/store/schema.rs` — SQLite schema (FTS5, vectors)
- `crates/secall-core/src/store/session_repo.rs` — session read/write
- `crates/secall-core/src/store/search_repo.rs` — search query repository
- `crates/secall-core/src/store/graph_repo.rs` — graph-aware filtering

## Extracted findings

### Tokenizer fallback
- seCall uses **Lindera as default** and allows **Kiwi as an opt-in Korean tokenizer**.
- This is the strongest sibling reference for Snowiki's current Step 2 recommendation: Lindera-first default, Kiwi optional where supported.
- The important pattern is not merely tokenizer choice, but **fallback discipline**: the system remains operational even when the richer tokenizer path is unavailable.

### Hybrid fusion
- seCall uses **RRF `k=60`**.
- It normalizes the fused score range after RRF.
- It also applies a **session diversity cap** via `diversify_by_session()` with a default of **`max_per_session = 2`**.
- This is the best evidence source for Snowiki's optional diversity-capping behavior.

### BM25-only fallback
- seCall degrades to BM25-only when vector components are unavailable.
- It also keeps ANN and brute-force/vector fallback distinctions explicit.

### Vault and graph model
- seCall treats the vault as the source of truth and derives indexes/graph state from it.
- Deterministic graph extraction is primary; optional semantic enrichment is an add-on layer.
- This is directly relevant to Snowiki Step 3 because it reinforces that skill/workflow surfaces should wrap canonical file/vault truth, not replace it.

## Relevance to Snowiki steps
- Step 2: Korean tokenizer selection (Lindera default + Kiwi optional pattern)
- Step 3: Wiki skill design (vault model: raw/sessions + wiki/projects/topics/decisions)
- Step 4: Hybrid retrieval preparation (RRF, fallback, graph filtering)

## Concrete Snowiki takeaways

1. Lindera-first + Kiwi-opt-in is a proven Korean-aware local-first pattern.
2. Diversity capping is useful when one session/source can dominate the hit list.
3. BM25-only fallback should be an expected operational mode, not an error state.
4. Derived graph/search state should remain rebuildable from canonical vault files.

# vlwkaos/ir — Snowiki Analysis Notes

## Repository
- https://github.com/vlwkaos/ir
- Local clone: `/home/k/local/ir`

## What this is
Rust port of qmd with per-collection SQLite, tiered retrieval, CJK preprocessors, MCP integration.

## Key files to analyze for Snowiki

### Korean / CJK tokenization
- `preprocessors/ko/lindera-tokenize/src/main.rs` — Korean preprocessor executable
- `preprocessors/ja/lindera-tokenize/src/main.rs` — Japanese preprocessor
- `preprocessors/zh/bigram-tokenize/src/main.rs` — Chinese bigram preprocessor
- `src/preprocess.rs` — how preprocessors are wired into index/query pipeline

### Retrieval pipeline
- `src/search/hybrid.rs` — score fusion, RRF, shortcut logic
- `src/search/vector.rs` — vector retrieval path
- `src/search/rrf.rs` — RRF implementation details
- `src/search/fan_out.rs` — query expansion dispatch

### Indexing / chunking
- `src/index/chunker.rs` — structure-aware chunking with overlap
- `src/index/embed.rs` — embedding adapter and model switching
- `src/index/diff.rs` — incremental content-addressed indexing

### Storage
- `src/db/schema_base.sql` — per-collection SQLite schema
- `src/db/vectors.rs` — sqlite-vec integration

## Extracted findings

### Fusion parameters
- `ir` uses **RRF `k=60`** with **position bonuses**:
  - rank 0 → `+0.05`
  - ranks 1–2 → `+0.02`
- List weights follow a pragmatic asymmetry:
  - first list `1.0`
  - later lists `0.8`
- It also supports a weighted score-fusion phase with a tuned default of **`0.80 * vec + 0.20 * bm25`**.

### Strong-signal shortcut
- `ir` has the clearest two-tier shortcut design in the comparison set:
  - **BM25-only tier-0**: `top >= 0.75` and `gap >= 0.10`
  - **fused tier-1**: `top >= 0.40` and `top * gap >= 0.06`
- This is the strongest direct reference for Snowiki's Step 4 shortcut rule.

### Preprocessor protocol
- `ir` externalizes language preprocessing behind a command I/O protocol rather than hard-coding English-only tokenization.
- This keeps the retrieval core language-agnostic while still allowing high-quality Korean preprocessing.
- Errors in the preprocessor path are handled conservatively: the system degrades rather than treating preprocessing as mandatory runtime truth.

### Chunking strategy
- `ir` uses structure-aware chunking with overlap and content-addressed indexing.
- Chunking is treated as an index design concern, not only a search concern.

### Embedder posture
- `ir` explicitly acknowledges the operational cost of cold-loading hybrid components.
- Warm serving is relevant evidence for future dense-model work, but it is not part of Snowiki's current shipped runtime surface.

### Storage and collection model
- `ir`'s per-collection SQLite posture solves one of qmd's core operational pain points: a single global DB is awkward for concurrent multi-agent/project-local work.
- This is highly relevant to Snowiki if future indexing surfaces diversify by workspace or project scope.

## Relevance to Snowiki steps
- Step 2: Korean tokenizer selection (preprocessor pattern, Lindera vs Kiwi)
- Step 4: Hybrid retrieval preparation (fusion rules, shortcut behavior, rerank placement)
- Step 5: Rust core migration (modular Rust design, SQLite per-collection model)

## Concrete Snowiki takeaways

1. Keep Korean preprocessing behind a pluggable boundary.
2. Use `ir` as the primary evidence source for shortcut thresholds and RRF bonuses.
3. Treat warm serving as a future dense-model concern, not as a current runtime requirement.
4. Treat tokenizer/preprocessor configuration as collection/index metadata.

# qmd (tobi/qmd) — Snowiki Analysis Notes

## Repository
- https://github.com/tobi/qmd
- Local clone: `/home/k/local/qmd`

## What this is
Local-first hybrid retrieval engine: BM25/FTS5 + vector + typed expansion + RRF + rerank. The upstream lineage reference for Snowiki's retrieval target.

## Key files to analyze for Snowiki

### Retrieval pipeline
- `src/store.ts` — central store with BM25 probe, vector retrieval, RRF, rerank, strong-signal shortcut
- `test/eval.test.ts` — evaluation structure (BM25 baseline, vector, hybrid RRF)

### MCP / integration
- `src/mcp.ts` — MCP tool surface

### README / docs
- `README.md` — product definition: "Hybrid: FTS + Vector + Query Expansion + Re-ranking"

## Extracted findings

### Strong-signal shortcut
- qmd uses a strong-signal shortcut to skip more expensive hybrid work when lexical/BM25 evidence is already dominant.
- Extracted threshold: **top score `>= 0.85` AND top-second gap `>= 0.15`**.
- This is one of the clearest operational lessons Snowiki should inherit: hybrid should amplify lexical search, not blindly run on every query.

### RRF parameters
- qmd uses **RRF with `k=60`**.
- No normalization is required in the core formulation.
- qmd treats RRF as a late fusion layer after candidate generation rather than a replacement for individual modality scoring.

### Query expansion
- qmd supports typed query expansion modes such as **`lex`**, **`vec`**, and **`hyde`**.
- Expansion is a query-routing and candidate-broadening device, not the default starting point.
- The important lesson for Snowiki is architectural: expansion belongs **after** the sparse branch is already trustworthy and should be treated as a separately gated sophistication layer.

### Rerank placement
- qmd reranks **after fusion** and does so on **chunks**, not only on full documents.
- Candidate list sizes are intentionally capped before rerank to constrain latency.

### Fallback posture
- If vector state or embeddings are unavailable, qmd continues with lexical/FTS paths instead of failing the whole query.
- This matches Snowiki's desired fallback posture for Step 4.

## Relevance to Snowiki steps
- Step 4: Hybrid retrieval preparation (shortcut rules, RRF, rerank placement, expansion modes)

## Concrete Snowiki takeaways

1. Hybrid should be **mode-gated and shortcut-aware**, not always-on.
2. RRF `k=60` is a safe starting default.
3. Expansion should remain **deferred** until rerank quality is proven.
4. Chunk-level rerank is more credible than whole-document rerank for compiled knowledge pages.

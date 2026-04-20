# qmd (tobi/qmd) — Snowiki Analysis Notes

## Repository
- https://github.com/tobi/qmd
- Local clone: `/home/k/local/qmd`

## What this is
Local-first hybrid retrieval engine: BM25/FTS5 + vector + typed expansion + RRF + rerank. qmd is still the clearest upstream substrate reference for Snowiki's medium-term retrieval target, but it is a **retrieval system first**, not a provenance-aware knowledge engine.

## Why this matters to Snowiki
qmd is the strongest reference for **how** to build hybrid retrieval, especially around:
- strong lexical shortcuts
- chunk-aware reranking
- hybrid-vs-baseline evaluation
- graceful degradation when vector state is missing

It is a weaker reference for:
- knowledge maintenance workflow
- provenance contracts
- broad architecture governance across multiple runtime surfaces

## Key files to analyze for Snowiki

### Retrieval pipeline
- `src/store.ts` — central store with BM25 probe, vector retrieval, RRF, query expansion, rerank, and strong-signal shortcut
- `test/eval.test.ts` — evaluation structure (BM25 baseline, vector, hybrid RRF, fusion assertions)
- `docs/SYNTAX.md` — typed query grammar (`lex`, `vec`, `hyde`, `intent`) and MCP-facing semantics

### Runtime / hardware posture
- `src/llm.ts` — model lifecycle, llama.cpp integration, embedding/rerank contexts, CPU/GPU concurrency
- `src/db.ts` — sqlite-vec loading and runtime-specific SQLite caveats

### Chunking / document model
- `src/ast.ts` — AST-aware chunking for code files
- `src/collections.ts` — collection config and stable virtual path model

## Extracted findings

### 1. Strong-signal shortcut is part of the default design
- qmd uses a strong-signal shortcut to skip more expensive hybrid work when lexical/BM25 evidence is already dominant.
- Extracted threshold: **top score `>= 0.85` AND top-second gap `>= 0.15`**.
- This is one of qmd's clearest operational lessons: hybrid should **amplify lexical search**, not blindly run on every query.

### 2. Hybrid fusion is late-stage and modular
- qmd uses **RRF with `k=60`**.
- It treats RRF as a **late fusion layer after candidate generation**, not a replacement for modality-specific scoring.
- It also adds a top-rank bonus and weighted list treatment so the original lexical signal is not erased by later stages.

### 3. Reranking is chunk-scoped, not full-document-scoped
- qmd reranks **after fusion** and does so on **chunks**, not only on full documents.
- Candidate list sizes are intentionally capped before rerank to constrain latency.
- This is a strong fit for Snowiki because compiled pages and records already have natural section/chunk seams.

### 4. Query expansion is powerful but operationally heavy
- qmd supports typed query expansion modes such as **`lex`**, **`vec`**, and **`hyde`**.
- Expansion is not treated as a vague LLM add-on; it is a typed routing primitive.
- However, qmd's production-quality expansion depends on a **fine-tuned local model**, which makes expansion a separate product surface with real maintenance cost.

### 5. Graceful degradation is intentional
- If vector state or embeddings are unavailable, qmd continues with lexical/FTS paths instead of failing the whole query.
- sqlite-vec constraints are handled as implementation details rather than user-visible failures.
- This matches Snowiki's desired Step 4 posture exactly.

### 6. qmd is explicit about multilingual/CJK model tradeoffs
- The README documents that the default embedding path is English-leaning and that **Qwen3-Embedding** is the more CJK-friendly option.
- This matters for Snowiki because it reinforces the need to keep model policy tied to the Korean/mixed-language benchmark rather than picking a single dense model on reputation alone.

## Methodology patterns worth copying

### Benchmarkable hybrid design
- qmd's evaluation tests compare BM25, vector, hybrid, and fusion behavior directly.
- This makes hybrid quality claims falsifiable instead of anecdotal.
- For Snowiki, this is the main methodological upgrade over seCall's stronger workflow posture but weaker evaluation surface.

### Operational budgeting, not just algorithm choice
- qmd is careful about:
  - shortcutting expensive paths
  - reranking only the top chunk set
  - batching vector work where possible
  - keeping fallback behavior explicit
- Snowiki should absorb this as a planning principle, not merely as an implementation detail.

### Stable document identity
- qmd uses a virtual-path scheme and content-addressable storage so renames do not imply semantic identity changes.
- Snowiki should not copy the exact scheme blindly, but the identity discipline is relevant to chunk/vector invalidation design.

## Limitations and caveats for Snowiki

1. qmd is a stronger reference for retrieval machinery than for knowledge-system product identity.
2. Its query-expansion stack assumes a custom fine-tuned model; Snowiki should treat this as deferred, not baseline.
3. Some of qmd's runtime complexity comes from Node/sqlite-vec/llama.cpp constraints that Snowiki does not need to inherit literally.
4. qmd's default posture is closer to a hybrid-native product; Snowiki still needs `lexical` to remain the canonical shipped default.

## Relevance to Snowiki steps
- **Step 4**: Hybrid retrieval preparation (shortcut rules, RRF, chunk rerank, expansion policy, evaluation harness)
- **Step 2**: Mixed-language strategy, because qmd's multilingual story is only safe when tied to actual Korean/CJK evaluation

## Concrete Snowiki takeaways

1. Hybrid should be **mode-gated and shortcut-aware**, not always-on.
2. RRF `k=60` remains the safest default starting point.
3. Chunk-level rerank is much more credible than whole-document rerank for compiled knowledge pages.
4. Expansion should remain **deferred** until rerank quality is proven and benchmark infrastructure is mature.
5. qmd should be the primary external reference for **evaluation structure**, not only for retrieval algorithms.

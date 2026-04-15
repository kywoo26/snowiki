# Step 4: Hybrid Retrieval Preparation

## Purpose

Define seams, evaluation gates, and fallback rules for hybrid retrieval (lexical + vector + fusion + rerank) without shipping it as the default runtime path.

## Why now

Hybrid retrieval is the confirmed medium-term target for the retrieval core, aligned with the qmd / seCall / `vlwkaos/ir` lineage. We must prepare the architecture and evaluation framework before implementation, so that when the sparse branch is proven, the fusion layer can be added safely.

## Current reality

- `src/snowiki/search/semantic_abstraction.py` and `src/snowiki/search/rerank.py` exist as **extension seams**, not active runtime layers.
- The system has no dense vector lifecycle, embedding model policy, or fusion rule yet.
- The benchmark system currently evaluates lexical paths only.

## Scope

In scope:
- Define embedding insertion points and the chunking boundary policy.
- Design rerank and query-expansion hooks.
- Specify CPU-only fallback and GPU-optional acceleration policy.
- Define warm/cold model lifecycle and caching strategy.
- Design the **strong lexical shortcut** rule: when BM25 signal is dominant, skip expensive dense/rerank work.
- Create the evaluation plan and exact parity proof required for runtime promotion.

Out of scope:
- Making semantic retrieval the default runtime path prematurely.
- Swapping the backend engine by implication.
- Shipping a vector index without provenance-safe chunking.

## Non-goals

- Do not enable hybrid as the CLI default until strict parity/safety proof is complete.
- Do not integrate cloud-only embedding APIs as the primary path.
- Do not lose exact-match / known-item performance.

## Dependencies

- **Step 1** (stable lexical contract) and **Step 2** (proven sparse branch) must be complete.

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Hybrid becomes a permanent exploration with no promotion gate | Write the promotion criteria as pass/fail conditions before writing any hybrid code. |
| Model lifecycle burdens users with cold-start latency or large downloads | Design a CPU-only fallback and lazy model loading path. |
| Vector index drifts from lexical index without visibility | Couple invalidation semantics to the lexical rebuild path. |

## Deliverables

1. **Hybrid architecture memo** (`hybrid-architecture.md`) with seam design, fallback rules, and mode-gated API surface.
2. **Hybrid evaluation plan** (`hybrid-evaluation-plan.md`) with metrics, thresholds, and the required parity proof.
3. **Proof-of-concept fusion path** in the benchmark/evidence layer only.

## TDD and verification plan

1. Add evaluation/trigger tests and seam tests before any hybrid runtime implementation.
2. Benchmark must show that hybrid improves semantically relevant recall **without** regressing exact-match / known-item performance.
3. Verify with:
   - `uv run pytest tests/search/test_semantic_abstraction.py` (to be added)
   - `uv run snowiki benchmark --preset retrieval` — new hybrid slices pass threshold.
   - `uv run pytest -m integration` — fallback paths work when embeddings are unavailable.

## Promotion criteria to `.sisyphus/plans/`

This step graduates to execution when:
- The hybrid path demonstrates a clear quality lift on benchmark slices.
- Latency and memory envelopes are predictable and acceptable for a local CLI tool.
- Deterministic fallback to lexical-only works when models are unavailable or stale.
- The strong lexical shortcut rule is implemented and tested.

## Reference citations

- `tobi/qmd` — local-first hybrid retrieval substrate: BM25/FTS + vector + typed expansion (`lex`/`vec`/`hyde`) + RRF + chunk-level rerank + strong-signal shortcut. [README](https://github.com/tobi/qmd/blob/main/README.md) · [`src/store.ts`](https://github.com/tobi/qmd/blob/main/src/store.ts)
- `hang-in/seCall` — Korean-aware local session search with BM25 + vector + RRF (`k=60`), diversity cap, and deterministic fallback to BM25-only when vectors are unavailable. [`search/hybrid.rs`](https://github.com/hang-in/seCall/blob/main/crates/secall-core/src/search/hybrid.rs) · [`search/vector.rs`](https://github.com/hang-in/seCall/blob/main/crates/secall-core/src/search/vector.rs)
- `vlwkaos/ir` — Rust qmd port with tiered retrieval (BM25 probe → vector → score fusion `0.8·vec + 0.2·bm25` → strong-signal shortcut → optional expansion → RRF → top-20 rerank), per-collection SQLite, and MCP integration. [`src/search/hybrid.rs`](https://github.com/vlwkaos/ir/blob/main/src/search/hybrid.rs) · [`research/pipeline.md`](https://github.com/vlwkaos/ir/blob/main/research/pipeline.md)
- `docs/architecture/current-retrieval-architecture.md` — current runtime contract and extension seam status (semantic / rerank).
- `docs/reference/research/search-system-comparison-matrix.md` — comparative evidence for search system choices.
- `docs/reference/research/qmd-lineage-and-korean-strategy.md` — internal synthesis on when and why to escalate from lexical to hybrid.

## Open questions

- Which **embedding model family** do we standardize on for local CPU inference? (e.g., BGE-small-en-v1.5, multilingual-E5, BGE-M3)
- Should the vector cache live inside the same SQLite file as the lexical index, or in a separate file keyed by model version?
- How do we chunk **mixed-format pages** (markdown with code blocks, tables, images) without losing provenance?

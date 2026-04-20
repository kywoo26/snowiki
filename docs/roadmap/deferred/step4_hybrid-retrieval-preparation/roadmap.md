# Step 4: Hybrid Retrieval Preparation

## Purpose

Define seams, evaluation gates, and fallback rules for hybrid retrieval (lexical + vector + fusion + rerank) without shipping it as the default runtime path.

## Why now

Hybrid retrieval is the confirmed medium-term target for the retrieval core, aligned with the qmd / seCall / `vlwkaos/ir` lineage. We must prepare the architecture and evaluation framework before implementation, so that when the sparse branch is proven, the fusion layer can be added safely.

## Current reality

- `src/snowiki/search/semantic_abstraction.py` and `src/snowiki/search/rerank.py` exist as **extension seams**, not active runtime layers.
- The system has no dense vector lifecycle, embedding model policy, or fusion rule yet.
- The benchmark system currently evaluates lexical paths only.
- Step 2 closed as **benchmark-only / no runtime promotion**, so Step 4 must plan for a hybrid-ready future **without pretending the sparse branch is already proven**.

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

## Planning posture

Step 4 is allowed to do **deep design and execution-grade decomposition now**, but it is **not allowed to imply immediate runtime promotion**.

That means this step should produce:
- implementation-ready seams
- benchmark and test requirements
- model / hardware policy
- substep-level execution plans

But it should not claim that:
- hybrid is unblocked for default runtime promotion
- Step 2's sparse-branch uncertainty is resolved by dense retrieval
- benchmark evidence can be deferred until after implementation
- one dense model family is already frozen before the candidate matrix closes

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Hybrid becomes a permanent exploration with no promotion gate | Write the promotion criteria as pass/fail conditions before writing any hybrid code. |
| Model lifecycle burdens users with cold-start latency or large downloads | Design a CPU-only fallback and lazy model loading path. |
| Vector index drifts from lexical index without visibility | Couple invalidation semantics to the lexical rebuild path. |

## Deliverables

1. **Hybrid architecture memo** (`hybrid-architecture.md`) with seam design, fallback rules, and mode-gated API surface.
2. **Hybrid evaluation plan** (`hybrid-evaluation-plan.md`) with metrics, thresholds, and the required parity proof.
3. **Substep planning packet** (`01-04`) detailed enough to promote into `.sisyphus/plans/` once the sparse-branch gate is satisfied.
4. **External evidence notes** covering qmd, seCall, Damoang/seCall series, and embedding/hardware policy.
5. **Proof-of-concept fusion path** in the benchmark/evidence layer only.
6. **Substep execution protocol** (`substep-execution-protocol.md`) defining how each numbered unit becomes a reviewable deep-plan -> execution/research -> PR-ready artifact.

## TDD and verification plan

1. Add evaluation/trigger tests and seam tests before any hybrid runtime implementation.
2. Benchmark must show that hybrid improves semantically relevant recall **without** regressing exact-match / known-item performance.
3. Verify with:
   - `uv run pytest tests/search/test_semantic_abstraction.py` (to be added)
   - `uv run snowiki benchmark --preset retrieval` — new hybrid slices pass threshold.
   - `uv run pytest -m integration` — fallback paths work when embeddings are unavailable.

## Required substep closeout before `.sisyphus/plans/` promotion

The numbered substeps must each answer a different class of implementation question:

1. `01-chunker-vector-schema.md`
   - chunk identity
   - provenance preservation
   - vector-store schema and invalidation
2. `02-embedder-lifecycle-model-policy.md`
   - multilingual target model
   - CPU/GPU posture
   - fallback and versioning policy
3. `03-hybrid-fusion-shortcut-rerank.md`
   - fan-out owner
   - fusion math
   - shortcut thresholds
   - rerank placement and cache posture
4. `04-hybrid-evaluation-mode-plumbing.md`
   - benchmark slices
   - mode-gated CLI/MCP/daemon exposure
   - degraded-mode testing
5. `05-embedding-candidate-matrix.md`
   - closed candidate set for dense-model evaluation
   - promotion/reject thresholds
   - CPU-first measurement rules
6. `06-sparse-language-routing-policy.md`
   - Step 2 dependency posture
   - Korean/English/mixed-language slice policy
   - sparse-branch visibility during hybrid evaluation
7. `07-topology-cache-ann-mode-parity.md`
   - storage/snapshot topology
   - ANN transition gate
   - cache ownership
   - cross-surface mode parity

If any of the above remains narrative-only or ambiguous, Step 4 stays in roadmap mode.

## Promotion criteria to `.sisyphus/plans/`

This step graduates to execution when:
- The seven substeps and policy notes are detailed enough to decompose into atomic implementation plans.
- The hybrid path demonstrates a clear quality lift on benchmark slices.
- Latency and memory envelopes are predictable and acceptable for a local CLI tool.
- Deterministic fallback to lexical-only works when models are unavailable or stale.
- The strong lexical shortcut rule is implemented and tested.

## External evidence map

- `docs/roadmap/external/qmd-NOTES.md` — hybrid orchestration, shortcut, chunk rerank, evaluation structure
- `docs/roadmap/external/seCall-NOTES.md` — Korean fallback discipline, backend abstraction, vault-first methodology
- `docs/roadmap/external/damoang-secall-series-NOTES.md` — authorial sequencing logic behind seCall's evolution
- `docs/roadmap/external/embedding-hardware-NOTES.md` — multilingual model target, CPU/GPU posture, fallback philosophy

## Reference citations

- `tobi/qmd` — local-first hybrid retrieval substrate: BM25/FTS + vector + typed expansion (`lex`/`vec`/`hyde`) + RRF + chunk-level rerank + strong-signal shortcut. [README](https://github.com/tobi/qmd/blob/main/README.md) · [`src/store.ts`](https://github.com/tobi/qmd/blob/main/src/store.ts)
- `hang-in/seCall` — Korean-aware local session search with BM25 + vector + RRF (`k=60`), diversity cap, and deterministic fallback to BM25-only when vectors are unavailable. [`search/hybrid.rs`](https://github.com/hang-in/seCall/blob/main/crates/secall-core/src/search/hybrid.rs) · [`search/vector.rs`](https://github.com/hang-in/seCall/blob/main/crates/secall-core/src/search/vector.rs)
- `vlwkaos/ir` — Rust qmd port with tiered retrieval (BM25 probe → vector → score fusion `0.8·vec + 0.2·bm25` → strong-signal shortcut → optional expansion → RRF → top-20 rerank), per-collection SQLite, and MCP integration. [`src/search/hybrid.rs`](https://github.com/vlwkaos/ir/blob/main/src/search/hybrid.rs) · [`research/pipeline.md`](https://github.com/vlwkaos/ir/blob/main/research/pipeline.md)
- `docs/architecture/current-retrieval-architecture.md` — current runtime contract and extension seam status (semantic / rerank).
- `docs/reference/research/search-system-comparison-matrix.md` — comparative evidence for search system choices.
- `docs/reference/research/qmd-lineage-and-korean-strategy.md` — internal synthesis on when and why to escalate from lexical to hybrid.

## Open questions

- Which **embedding model family** wins the candidate matrix strongly enough to justify becoming the default?
- Should the vector cache live inside the same SQLite file as the lexical index, or in a separate file keyed by model version?
- How do we chunk **mixed-format pages** (markdown with code blocks, tables, images) without losing provenance?

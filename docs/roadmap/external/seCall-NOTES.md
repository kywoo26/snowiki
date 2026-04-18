# seCall — Snowiki Analysis Notes

## Repository
- https://github.com/hang-in/seCall
- Local clone: `/home/k/local/seCall`

## What this is
Korean-aware local session search engine: vault as source of truth, BM25 + vector + RRF, deterministic graph build + optional LLM semantic enrichment.

## Why this matters to Snowiki
seCall is Snowiki's closest sibling reference for:
- Korean-aware lexical/tokenizer discipline
- local-first embedding backends with fallback
- vault-first workflow and derived-cache philosophy
- planning methodology built around plan/task/review artifacts

It is a weaker reference for:
- search-quality benchmarks
- retrieval evaluation metrics
- benchmark-driven promotion gates

That gap is important because it highlights where Snowiki should differentiate on purpose.

## Key files to analyze for Snowiki

### Vault model
- `crates/secall-core/src/vault/mod.rs` — vault initialization and structure
- `crates/secall-core/src/vault/init.rs` — vault bootstrap
- `crates/secall-core/src/vault/index.rs` — index.md maintenance
- `crates/secall-core/src/vault/log.rs` — log.md maintenance
- `crates/secall-core/src/vault/config.rs` — config, classification rules, env override policy

### Search / retrieval
- `crates/secall-core/src/search/bm25.rs` — BM25 query and result normalization
- `crates/secall-core/src/search/tokenizer.rs` — Lindera default, optional Kiwi, fallback logic
- `crates/secall-core/src/search/vector.rs` — vector path and BM25-only fallback
- `crates/secall-core/src/search/hybrid.rs` — RRF fusion, diversity cap, graph-filter path
- `crates/secall-core/src/search/chunker.rs` — context-aware chunking
- `crates/secall-core/src/search/ann.rs` — HNSW / BLOB cosine fallback
- `crates/secall-core/src/search/embedding.rs` — Ollama / ORT / OpenAI / OpenVINO backends

### Graph extraction
- `crates/secall-core/src/graph/extract.rs` — deterministic frontmatter/rules-based edges
- `crates/secall-core/src/graph/build.rs` — graph construction and incremental rebuild
- `crates/secall-core/src/graph/semantic.rs` — optional LLM semantic edges with fallback

### Planning / methodology
- `docs/plans/index.md` — plan registry
- `docs/plans/secall-mvp.md` — canonical plan structure
- `docs/plans/*-task-*.md` — task decomposition pattern
- `docs/reference/adr-*.md` — ADR structure
- `docs/insight/latest-report.md` — auto-generated findings / testing debt surface

## Extracted findings

### 1. Tokenizer fallback is a first-class operational policy
- seCall uses **Lindera as default** and allows **Kiwi as an opt-in Korean tokenizer**.
- This is the strongest sibling reference for Snowiki's Step 2 posture: Lindera-first default, Kiwi optional where supported.
- The important pattern is not merely tokenizer choice, but **fallback discipline**: the system remains operational even when the richer tokenizer path is unavailable.

### 2. Hybrid fusion is pragmatic and conservative
- seCall uses **RRF `k=60`**.
- It normalizes the fused score range after RRF.
- It also applies a **session diversity cap** via `diversify_by_session()` with a default of **`max_per_session = 2`**.
- This is the best direct evidence source for Snowiki's optional diversity-capping behavior.

### 3. BM25-only fallback is normal, not exceptional
- seCall degrades to BM25-only when vector components are unavailable.
- It also keeps ANN and brute-force/vector fallback distinctions explicit.
- This is exactly the operational discipline Snowiki should keep even if it adopts more ambitious hybrid planning.

### 4. Embedding backends are abstracted behind a real interface
- seCall's `Embedder` trait supports multiple local and remote backends.
- ORT uses a session pool and OpenVINO is feature-gated for hardware acceleration.
- The design emphasizes **backend substitution and graceful startup failure**, not one canonical stack hardcoded everywhere.

### 5. Graph filtering is integrated into retrieval, not bolted on later
- seCall can resolve graph/topic/file filters into session allowlists before executing search.
- That makes graph-aware retrieval a routing/filtering concern rather than a second product.
- Snowiki should not copy this immediately, but it is relevant for future wiki/session cross-link retrieval design.

### 6. Vault-first design is one of seCall's strongest transferable ideas
- seCall treats the vault as the source of truth and derives indexes/graph state from it.
- Deterministic graph extraction is primary; optional semantic enrichment is an add-on layer.
- This is directly relevant to Snowiki Step 3 because it reinforces that skill/workflow surfaces should wrap canonical file/vault truth, not replace it.

## Methodology patterns worth copying

### Plan / task / review structure
- seCall's docs/plans surface is much more operationally mature than its evaluation harness.
- Each plan clearly decomposes into tasks with changed-files expectations, verification commands, scope boundaries, and risks.
- This is a strong planning-template reference for Snowiki's Step 4 substep docs and later `.sisyphus/plans/` promotion.

### ADRs and insight reports
- ADRs are used to freeze important operational decisions.
- The insight report exposes testing debt and architectural findings in one place.
- Snowiki should borrow the **discipline** here, but tie it to a stricter benchmark/evaluation loop than seCall currently has.

## Limitations and caveats for Snowiki

1. seCall has useful unit and smoke tests, but **no serious retrieval benchmark harness**.
2. It does not provide the kind of quality-evaluation surface Snowiki needs for hybrid promotion gates.
3. Some design choices are session/vault-shaped in ways Snowiki should adapt carefully rather than copy directly.
4. Its workflow/methodology maturity is ahead of its evaluation maturity; Snowiki should invert that weakness into a strength.

## Relevance to Snowiki steps
- **Step 2**: Korean tokenizer selection (Lindera default + Kiwi optional pattern)
- **Step 3**: Wiki skill design (vault model: raw/sessions + wiki/projects/topics/decisions)
- **Step 4**: Hybrid retrieval preparation (RRF, fallback, graph filtering, backend abstraction)

## Concrete Snowiki takeaways

1. Lindera-first + Kiwi-opt-in is a proven Korean-aware local-first pattern.
2. Diversity capping is useful when one session/source can dominate the hit list.
3. BM25-only fallback should be an expected operational mode, not an error state.
4. Derived graph/search state should remain rebuildable from canonical vault files.
5. Snowiki should deliberately surpass seCall by making **tests, evaluation, and benchmarks** first-class instead of mostly implicit.

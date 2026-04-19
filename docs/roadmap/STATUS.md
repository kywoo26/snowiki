# Roadmap Research Status

## Active tracks

- [x] **Benchmark Dataset Overhaul Program**
  - Status: Complete. All four authority tiers are implemented, documented, and wired into the benchmark CLI.
  - Deliverables:
    - Four-tier authority taxonomy defined and canonical in `benchmarks/README.md` and `benchmarks/AGENTS.md`: `regression`, `public_anchor`, `snowiki_shaped`, `hidden_holdout`.
    - 90-query set explicitly demoted to `regression` / candidate-screening only; it is no longer treated as the main truth source for release-quality claims.
    - Korean public anchors: MIRACL Korean (`miracl_ko`) and Mr. TyDi Korean (`mr_tydi_ko`) with stable IDs, inline qrels, and explicit provenance.
    - English public anchors: BEIR SciFact (`beir_scifact`) and BEIR NFCorpus (`beir_nfcorpus`) with compact deterministic samples and explicit provenance.
    - Snowiki-shaped suite (`snowiki_shaped`) with deterministic coverage quotas: 30% mixed-language, 25% code/doc, 30% topical, 10% temporal, 5% no-answer, 0% LLM-generated.
    - Hidden holdout review architecture (`hidden_holdout`) with synthetic workflow facsimile, sealed provenance, pooled-review disagreement handling, and audit sampling.
    - Tier-aware latency sampling: exhaustive for regression, stratified for large public/scripted tiers, fixed 20-query sample for hidden holdout.
    - No-answer scoring policy and generic qrel scoring layer to support abstention-aware evaluation across all tiers.
  - Maintenance posture:
    - New benchmark datasets must include `BenchmarkProvenance` with `visibility_tier` and `family_dedupe_key` to prevent cross-tier contamination.
    - The `beir_small` dataset is reserved but not yet wired; connect it when a compact BEIR multi-dataset manifest is ready.
    - Threshold calibration for public anchors and snowiki_shaped remains open; do not reuse regression-tier thresholds for release-quality claims.
    - The real hidden holdout (not the synthetic facsimile) must be established before any final-proof claim can be made.
  - Blocker: None

- [x] **Step 1: Lexical contract stabilization**
  - Status: Analysis complete. Ready for execution planning.
  - Next action: Recreate the execution plan locally (not in git) and execute parity tests, shared contract seam, rebuild hardening, and the promotion gate.
  - Blocker: None

- [x] **Step 2: Korean tokenizer deep-dive**
  - Status: Strengthened benchmark substrate showed no stable winner in the current lexical roster; the bounded HF/subword lane completed as a rejected benchmark-only comparison; the corrected Mecab lane using `mecab-python3` + `python-mecab-ko-dic` is now benchmarkable and also rejected on the blocking retrieval gate.
  - Next action: Close the final comparative proof/recommendation package with both external-family lanes recorded as benchmarkable but rejected.
  - Blocker: Step 2 sparse branch still not proven on mixed-language benchmark.

- [x] **Step 3: Wiki skill contract draft**
  - Status: Analysis complete. Decomposed into four sub-steps:
    - `01-wiki-route-contract.md`
    - `02-schema-and-provenance-contract.md`
    - `03-governance-and-mirror-alignment.md`
    - `04-maintenance-loop-and-deferred-workflows.md`
  - Next action: Close sub-steps before any `.sisyphus/plans/` promotion; Step 1 must complete first.
  - Blocker: Step 1 must complete first so the runtime contract is canonical.

- [x] **Step 4: Hybrid fusion deep-dive**
  - Status: Analysis complete. Expanded into seven planning sub-steps / policy notes:
    - `01-chunker-vector-schema.md`
    - `02-embedder-lifecycle-model-policy.md`
    - `03-hybrid-fusion-shortcut-rerank.md`
    - `04-hybrid-evaluation-mode-plumbing.md`
    - `05-embedding-candidate-matrix.md`
    - `06-sparse-language-routing-policy.md`
    - `07-topology-cache-ann-mode-parity.md`
  - Next action: Close the seven-document Step 4 planning packet before any execution-plan promotion; the candidate matrix and sparse/language policy are now explicit prerequisites.
  - Blocker: Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.

- [x] **Step 5: Rust core migration path**
  - Status: Analysis complete. Decomposed into three sub-steps:
    - `01-profiling-workload-matrix.md`
    - `02-rust-boundary-api-sketch.md`
    - `03-packaging-stub-fallback-policy.md`
  - Next action: Close sub-steps before any `.sisyphus/plans/` promotion; collect profiling evidence first.
  - Blocker: Profiling evidence has not yet been collected.

## Completed tracks

- [x] Initial roadmap structure and main-roadmap.md
- [x] 7 reference surface research and synthesis
- [x] External notes infrastructure setup (`docs/roadmap/external/`)
- [x] Step 1 lexical parity gap analysis; execution-planning-ready
- [x] Step 2 decomposed into sub-steps (corpus, registry, candidate matrix)
- [x] Step 2 gate audit / residual-program decision (`step2_korean-tokenizer-selection/04-gate-audit-and-residual-program.md`)
- [x] Step 2 gate reconciliation and fresh-evidence launch posture (`step2_korean-tokenizer-selection/04-gate-reconciliation-and-fresh-evidence-program.md`)
- [x] Step 2 runtime-promotion decision package (`step2_korean-tokenizer-selection/07-runtime-promotion-decision.md`)
- [x] Step 2 reopening runtime-promotion recommendation (`step2_korean-tokenizer-selection/11-runtime-promotion-recommendation.md`)
- [x] Step 2 reopening contract (`step2_korean-tokenizer-selection/08-reopening-contract.md`)
- [x] Step 3 wiki skill design analysis
- [x] Step 4 hybrid architecture memo (`hybrid-architecture.md`)
- [x] Step 4 hybrid evaluation plan (`hybrid-evaluation-plan.md`)
- [x] Step 4 decomposed into sub-steps (chunker, embedder, fusion, evaluation, candidate matrix, sparse/language policy, topology/cache parity)
- [x] Step 4 external note expansion (`qmd`, `seCall`, Damoang/seCall series, embedding/hardware policy)
- [x] Step 4 substep execution protocol (deep plan -> execution/research/decision -> PR-ready closeout)
- [x] Step 5 rust migration analysis (`step5_rust-core-migration-path/analysis.md`)
- [x] Step 5 decision/evidence scaffolding (`rust-migration-decision-record.md`, `profiling-baseline.md`)
- [x] Step 5 decomposed into sub-steps (profiling, boundary API, packaging)
- [x] External note expansion for Step 3 references (`karpathy-llm-wiki`, `farzapedia`, `personal-os-skills`, `artem-personal-os-pattern`)

## Canonical surface note

- `docs/roadmap/` is the canonical planning and analysis surface.
- `docs/architecture/` should contain only the small set of current contract/architecture owner docs.
- `docs/reference/` should be treated as supporting rationale, evidence, translations, and background context unless explicitly promoted.
- `docs/roadmap/external/` remains roadmap-owned supporting evidence, not a generic repo-wide reference bucket.
- `docs/roadmap/archive/follow-up-program.md` and `.ko.md` remain the clearest later deletion candidates once we decide the archive no longer adds value.

## Branch closure note

- Current branch policy: **classification over deletion**.
- Broad pruning of mirror/evidence/legacy docs is deferred until roadmap → execution-plan handoff is tighter and no operational document still depends on archived lineage.

## Docs structure note

- `docs/README.md` defines the durable key-path split between roadmap/contract docs and supporting/archive material.
- Branch-local control notes should not remain under `docs/`.

## Last updated

2026-04-20

# Roadmap Research Status

## Active tracks

- [x] **Step 1: Lexical contract stabilization**
  - Status: Analysis complete. Ready for execution planning.
  - Next action: Recreate the execution plan locally (not in git) and execute parity tests, shared contract seam, rebuild hardening, and the promotion gate.
  - Blocker: None

- [x] **Step 2: Korean tokenizer deep-dive**
  - Status: Benchmark proof failed to reach promotion threshold; local outcome is `benchmark-only/no runtime promotion`.
  - Next action: Closeout normalization / benchmark-surface hardening preparation.
  - Blocker: Step 2 sparse branch still not proven on mixed-language benchmark.

- [x] **Step 3: Wiki skill contract draft**
  - Status: Analysis complete. External concepts mapped onto Snowiki skill/ + mcp/ structure.
  - Next action: Promote to `.sisyphus/plans/` after Step 1 execution completes; create `skill/schemas/*.yaml` and `tests/governance/test_skill_contract_alignment.py`.
  - Blocker: Step 1 must complete first so the runtime contract is canonical.

- [x] **Step 4: Hybrid fusion deep-dive**
  - Status: Analysis complete. Decomposed into four sub-steps:
    - `01-chunker-vector-schema.md`
    - `02-embedder-lifecycle-model-policy.md`
    - `03-hybrid-fusion-shortcut-rerank.md`
    - `04-hybrid-evaluation-mode-plumbing.md`
  - Next action: Close sub-steps before any `.sisyphus/plans/` promotion; Step 2 must be proven first.
  - Blocker: (B) Step 2 still not proven, Step 4 remains blocked.

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
- [x] Step 3 wiki skill design analysis
- [x] Step 4 hybrid architecture memo (`hybrid-architecture.md`)
- [x] Step 4 hybrid evaluation plan (`hybrid-evaluation-plan.md`)
- [x] Step 4 decomposed into sub-steps (chunker, embedder, fusion, evaluation)
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

2026-04-18

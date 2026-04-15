# Roadmap Research Status

## Active tracks

- [x] **Step 1: Lexical contract stabilization**
  - Status: Analysis complete. Negative guards exist (`test_runtime_lexical_separation.py`); positive parity tests (CLI/MCP/daemon diff) are missing.
  - Next action: Implement `tests/governance/test_retrieval_surface_parity.py` and promotion-gate script.
  - Blocker: None

- [x] **Step 2: Korean tokenizer deep-dive**
  - Status: Analysis complete. Detailed comparison of ir (preprocessor executable), seCall (in-process Lindera-default + Kiwi opt-in), and Kiwi/kiwi-rs bindings written into `step2_korean-tokenizer-selection/analysis.md`.
  - Next action: Create benchmark corpus for true mixed-language tokenization; prototype tokenizer abstraction interface.
  - Blocker: None

- [x] **Step 3: Wiki skill contract draft**
  - Status: Analysis complete. External concepts (Farzapedia, Karpathy LLM Wiki, personal-os-skills, seCall) mapped onto Snowiki skill/ + mcp/ structure.
  - Status: External note layer now includes Karpathy, Farzapedia, personal-os-skills, and Artem personal-OS pattern notes under `docs/roadmap/external/`.
  - Next action: Create `skill/schemas/*.yaml` for current routes; add `tests/governance/test_skill_contract_alignment.py`.
  - Blocker: None

- [x] **Step 4: Hybrid fusion deep-dive**
  - Status: Analysis complete. Exact parameters extracted from qmd (shortcut 0.85/0.15, RRF k=60), ir (fusion α=0.80, shortcut 0.40/0.06 + tier-0 0.75/0.10, RRF bonuses), seCall (RRF normalize, diversify_by_session max=2).
  - Status: `hybrid-architecture.md` drafted with seam design, fallback rules, mode-gated API surface, and evaluation gates.
  - Status: `hybrid-evaluation-plan.md` drafted with benchmark slices, ablations, and promotion gates.
  - Next action: Begin chunker + vector store schema POC.
  - Blocker: Step 2 sparse branch proven on mixed-language benchmark.

- [x] **Step 5: Rust core migration path**
  - Status: Analysis complete. `analysis.md` now synthesizes `ir`, `tokenizers`, `tantivy-py`, and ParadeDB into candidate hot-path ranking, Python↔Rust boundary rules, wheel/stub policy, and fallback/debug requirements.
  - Status: `rust-migration-decision-record.md` and `profiling-baseline.md` now exist as roadmap-stage decision/evidence scaffolding.
  - Next action: Collect real hotspot evidence before any Rust spike.
  - Blocker: Profiling evidence has not yet been collected.

## Completed tracks

- [x] Initial roadmap structure and main-roadmap.md
- [x] 7 reference surface research and synthesis
- [x] external notes infrastructure setup (`docs/roadmap/external/`)
- [x] Step 1 lexical parity gap analysis
- [x] Step 3 wiki skill design analysis
- [x] Step 4 hybrid architecture memo (`hybrid-architecture.md`)
- [x] Step 4 hybrid evaluation plan (`hybrid-evaluation-plan.md`)
- [x] Step 5 rust migration analysis (`step5_rust-core-migration-path/analysis.md`)
- [x] Step 5 decision/evidence scaffolding (`rust-migration-decision-record.md`, `profiling-baseline.md`)
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

2026-04-16

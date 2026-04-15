# Snowiki Product Roadmap

## Purpose

This document is the canonical roadmap entrypoint for Snowiki. It defines the ordered sequence of strategic initiatives, explains dependencies between them, and specifies how each initiative graduates from analysis into execution.

The roadmap covers the medium-term transition from a lexical-first runtime to a hybrid-ready, agent-facing wiki engine, while keeping the current shipped contract stable.

## How to use this folder

- Start here (`main-roadmap.md`) for sequencing, dependencies, and status.
- Drill into each `stepN_*/roadmap.md` for initiative-level scope, non-goals, deliverables, and promotion criteria.
- Use `docs/architecture/` only for current contract owners, and `docs/reference/` for supporting rationale/evidence; do not treat roadmap documents as architecture truth.
- Execution-ready plans live in `.sisyphus/plans/*.md`. A step only graduates there when acceptance criteria and verification commands are stable.

## Current strategic posture

After the architecture discussion in [discussion #26](https://github.com/kywoo26/snowiki/discussions/26), the following posture is adopted:

1. **Current shipped truth remains lexical-first.** The CLI / MCP / daemon retrieval contract must stay canonical and drift-free.
2. **Retrieval-core target architecture is qmd / seCall / `vlwkaos/ir` lineage.** Hybrid retrieval (BM25 + vector + fusion + rerank) is a **medium-term** goal, not a long-term one. Once the lexical foundation is solid, hybrid preparation begins immediately.
3. **Kiwi / Kkma / Okt are not benchmark side quests.** They are the **future hybrid sparse branch candidates**. The current lexical benchmarking work is forward-compatible hardening.
4. **Agent-facing `/wiki` skill is a first-class design target.** Snowiki exists to let agents ingest, query, and maintain a local knowledge base on behalf of the user. This draws from Farzapedia, Karpathy’s LLM Wiki, and `ArtemXTech/personal-os-skills`.
5. **Rust core migration is extension-first (PyO3/maturin).** Only hot paths that are proven CPU-bound and stable in contract will move to Rust. Daemon/subprocess escalation is reserved for crash-isolation or multi-frontend sharing needs.

## Ordered roadmap steps

| Step | Directory | Focus | Horizon |
| :--- | :--- | :--- | :--- |
| 1 | `step1_lexical-foundation/` | Lock the lexical retrieval contract, eliminate drift, and make policy promotion safe. | Now |
| 2 | `step2_korean-tokenizer-selection/` | Benchmark and select the Korean / mixed-language lexical strategy. | Next |
| 3 | `step3_wiki-skill-design/` | Design the agent-facing `/wiki` skill contract, workflows, and maintenance loop. | Parallel with Step 2 |
| 4 | `step4_hybrid-retrieval-preparation/` | Define seams, evaluation gates, and fallback rules for hybrid retrieval without shipping it as default. | Medium-term |
| 5 | `step5_rust-core-migration-path/` | Define when and how to move hot paths to a Rust extension. | Long-term |

## Dependency chain

```text
Step 1: lexical contract stabilization
    |
    +--> Step 2: korean tokenizer selection (needs stable lexical substrate)
    |       |
    |       +--> Step 4: hybrid retrieval preparation (needs proven sparse branch)
    |
    +--> Step 3: wiki skill design (needs canonical runtime truth to build against)
    |
    +--> Step 5: rust migration path (needs stable boundaries before native acceleration)
```

- Step 3 can proceed in parallel with Step 2 because both depend on Step 1 but not on each other.
- Step 4 must wait for Step 2 because hybrid fusion is only meaningful when the sparse (lexical) branch is proven.
- Step 5 should be informed by Step 4’s boundary work, but it does not block Step 4.

## Promotion rules into `.sisyphus/plans/`

A step may be promoted from `docs/roadmap/` to `.sisyphus/plans/` when **all** of the following are true:

1. Scope is implementation-ready (no unresolved architecture questions).
2. Acceptance criteria are stable and pass/fail verifiable.
3. Verification commands are known and documented.
4. Dependencies are clear and already satisfied or concurrently planned.
5. The work can be split into atomic commits by concern.

If any of the above is missing, the step stays in `docs/roadmap/` until it hardens.

## Reference map

### External references reviewed for this roadmap

| Reference | What it contributes | Relevant steps |
| :--- | :--- | :--- |
| [`vlwkaos/ir`](https://github.com/vlwkaos/ir) | Rust port of qmd with per-collection SQLite, tiered retrieval (BM25 → vector → rerank), strong-signal shortcut, CJK preprocessors, MCP integration. | 2, 4 |
| [Hada.io topic 27239 / Artem Zhutov](https://news.hada.io/topic?id=27239) | Local-first personal OS pattern: Obsidian + Claude Code + QMD + skills, 3-layer memory, auto-dream cleanup, temporal/topic/graph recall. | 3 |
| [`bab2min/Kiwi`](https://github.com/bab2min/Kiwi) | C++ Korean morphological analyzer with multiple bindings and model families. Strong lexical foundation candidate, but corpus-sensitive in BM25. | 2 |
| [`ArtemXTech/personal-os-skills`](https://github.com/ArtemXTech/personal-os-skills) | Skill packaging patterns: `SKILL.md` frontmatter, schema files, route splitting (ingest/query/recall/sync), provenance preservation, human+agent outputs. | 3 |
| [Hada.io topic 28208 / Karpathy LLM Wiki](https://news.hada.io/topic?id=28208) | Local-first file-based knowledge system: raw → wiki → schema, ingest/query/lint operations, index-first navigation, compounding knowledge. | 3 |
| [FarzaTV / Farzapedia](https://x.com/FarzaTV/status/2040563939797504467) | Agent-owned wiki layer: `/wiki` skill commands (ingest, absorb, query, cleanup, breakdown, status), index-first retrieval, persistent synthesis. | 3 |
| [`hang-in/seCall`](https://github.com/hang-in/seCall) | Korean-aware local session search: vault as source of truth, BM25 + vector + RRF, deterministic graph build + optional LLM semantic enrichment, rebuildable derived caches. | 2, 3, 4 |

### Internal references that feed this roadmap

| Document | Role | Relevant steps |
| :--- | :--- | :--- |
| `docs/architecture/current-retrieval-architecture.md` | Canonical current-state retrieval contract and runtime boundaries. | 1, 2, 4, 5 |
| `docs/architecture/skill-and-agent-interface-contract.md` | Canonical agent/skill contract. | 3 |
| `docs/reference/architecture/retrieval-decision-matrix.md` | Decision framework for retrieval strategy choices. | 2, 4 |
| `docs/reference/architecture/rust-native-acceleration-roadmap.md` | Gating criteria and boundary guidance for Rust migration. | 5 |
| `docs/reference/research/qmd-lineage-and-korean-strategy.md` | Evidence synthesis for qmd lineage and Korean lexical-first strategy. | 2, 4 |
| `docs/reference/research/search-system-comparison-matrix.md` | Comparative evidence for search system choices. | 4 |
| `docs/reference/vision/snowiki-vision.md` | Long-term product identity and direction. | All |

## Deprecations and superseded docs

- `docs/roadmap/archive/follow-up-program.md` and its `.ko.md` mirror are **superseded** by this document and the step roadmaps below.
- The follow-up program correctly identified Korean lexical evaluation and skill contract design as next priorities. This roadmap preserves that sequencing while adding the wiki-skill and hybrid-preparation tracks explicitly.

---

*Last reviewed: 2026-04-14*

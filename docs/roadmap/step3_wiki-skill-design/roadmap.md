# Step 3: Wiki Skill Design

## Purpose

Design the agent-facing `/wiki` skill contract, workflows, and maintenance loop so that Snowiki becomes a first-class knowledge substrate for agents.

## Why now

Snowiki’s ultimate value proposition is letting agents ingest, query, and maintain a local knowledge base on behalf of the user. The skill layer has been treated as a workflow/reference surface, but it needs deliberate first-class design rather than patch-level cleanup. The architecture discussion confirmed that the `/wiki` skill should be a disciplined consumer of CLI/MCP truth, not a separate runtime.

## Current reality

- `skill/SKILL.md` and `skill/workflows/wiki.md` describe aspirational wiki workflows.
- The current shipped product truth is the Python `snowiki` CLI and its read-only MCP surface.
- The skill docs still contain legacy qmd-oriented guidance that is not the authoritative runtime contract.

## Scope

In scope:
- Define `/wiki` skill routes and their input/output schemas.
- Specify provenance rules: every wiki claim must trace to a source, and contradictions must be flagged.
- Design the maintenance loop: **ingest → absorb → lint/cleanup → query**.
- Keep the skill as a thin, deterministic wrapper over the canonical CLI/MCP contract.
- Define how the skill surfaces feedback to the agent (tables for humans, structured JSON for programmatic use).

Out of scope:
- Rewriting the whole product around skills.
- Reintroducing qmd-oriented runtime claims as present truth.
- Implementing a separate skill runtime backend.

## Non-goals

- Do not make the skill chatty or implicit.
- Do not allow the skill to bypass the CLI/MCP contract.
- Do not add agent write permissions without a review gate unless explicitly configured.

## Sub-steps

This initiative is decomposed into four concern-based sub-steps:

1. [01: Wiki Route Contract](01-wiki-route-contract.md) — Canonical route taxonomy and CLI/MCP mapping.
2. [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md) — Input/output schemas and traceability rules.
3. [03: Governance and Mirror Alignment](03-governance-and-mirror-alignment.md) — Drift prevention and automated alignment tests.
4. [04: Maintenance Loop and Deferred Workflows](04-maintenance-loop-and-deferred-workflows.md) — Knowledge lifecycle and future workflow boundaries.

## Future Planning Order

To ensure a stable foundation, future deep-planning for this step will follow the numbered sequence: **01 → 02 → 03 → 04**.

The **First Deep-Plan Target** is [01-wiki-route-contract.md](01-wiki-route-contract.md). All later Step 3 docs depend on a stable current-vs-deferred route map and canonical route ownership; deep-planning any later doc first would risk encoding unstable assumptions about what the `/wiki` skill actually wraps.

## Dependencies

- **Step 1** must be complete so that the runtime contract the skill wraps is stable and canonical.

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Skill surface becomes too implicit and drifts from user intent | Make the contract explicit through schema files and frontmatter. |
| Agent writes silently corrupt wiki pages | Add lint/cleanup as a mandatory step and support reviewable memory updates. |
| Skill becomes a second product identity | Keep it a wrapper; all heavy lifting stays in the CLI runtime. |

## Deliverables

1. **Skill contract document** (see [01-wiki-route-contract.md](01-wiki-route-contract.md)) defining each route, its arguments, and its output shape.
2. **Schema files** (see [02-schema-and-provenance-contract.md](02-schema-and-provenance-contract.md)) for inputs/outputs (YAML or JSON) that both humans and agents can validate against.
3. **Workflow map** (see [04-maintenance-loop-and-deferred-workflows.md](04-maintenance-loop-and-deferred-workflows.md)) showing how ingest, absorb, query, and lint interact.
4. **Governance tests** (see [03-governance-and-mirror-alignment.md](03-governance-and-mirror-alignment.md)) to prevent CLI/skill drift.

## TDD and verification plan

1. Write governance tests that fail if `skill/workflows/wiki.md` describes a command or behavior that does not exist in the CLI.
2. Verify that skill outputs match the schema.
3. Verify with:
   - `uv run pytest tests/governance/test_skill_contract_alignment.py` (to be added)
   - Manual QA: run the authoritative CLI surfaces (`snowiki ingest`, `snowiki query --output json`, `snowiki recall --output json`, `snowiki lint`, `snowiki status`) and confirm the skill documentation matches the shipped runtime contract.

## Promotion criteria to `.sisyphus/plans/`

This step graduates to execution when:
- The skill contract is complete enough to implement as a thin wrapper over CLI/MCP.
- No new runtime backend is required to fulfill the contract.
- Schema files are stable and versioned.

## Reference citations

- FarzaTV / Farzapedia — agent-owned wiki layer with `/wiki` skill commands (`ingest`, `absorb`, `query`, `cleanup`, `breakdown`, `status`). Emphasizes index-first retrieval and persistent synthesis. [LinkedIn mirror](https://www.linkedin.com/posts/farza-majeed-76685612a_this-is-farzapedia-i-had-an-llm-take-2500-activity-7446408553596166144-vwS2)
- Karpathy’s LLM Wiki gist — local-first file-based knowledge system with raw → wiki → schema layers, and operations: ingest, query, lint. [Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- `ArtemXTech/personal-os-skills` — packaged Claude Code skills demonstrating route splitting (`ingest`, `query`, `recall`, `sync`), explicit `SKILL.md` frontmatter, schema files, provenance preservation, and auto-sync hooks. [Repo](https://github.com/ArtemXTech/personal-os-skills)
- `hang-in/seCall` — vault model with immutable `raw/sessions`, derived `wiki/projects|topics|decisions`, `index.md`, and `log.md`. Demonstrates that the vault can be the canonical source of truth while derived indexes are rebuildable. [`vault/mod.rs`](https://github.com/hang-in/seCall/blob/main/crates/secall-core/src/vault/mod.rs)
- `docs/architecture/skill-and-agent-interface-contract.md` — canonical agent/skill contract inside Snowiki.
- `skill/SKILL.md` and `skill/workflows/wiki.md` — existing workflow/reference surfaces to be aligned.

## Open questions

- Should the skill support **reviewable memory updates** (agent proposes, user approves) by default, or direct writes with an opt-in flag?
- How should the skill handle **local image and attachment ingestion** without losing portability?
- What is the correct granularity for a lint report: per-page, per-source, or per-query?

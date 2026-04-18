# Step 3 Analysis: Wiki Skill Design

## Executive Summary

This document synthesizes external reference research (Farzapedia, Karpathy’s LLM Wiki, `personal-os-skills`, and `seCall`) and maps their patterns onto Snowiki’s current runtime. The conclusion is that Snowiki’s `/wiki` skill should be a **thin, schema-first wrapper over the existing CLI and read-only MCP surfaces**, not a separate runtime backend.

The current skill layer (`skill/SKILL.md`, `skill/workflows/wiki.md`) contains aspirational workflows that drift from the shipped CLI contract. This analysis is now a background synthesis surface: the numbered Step 3 documents own the route contract, schema/provenance contract, governance alignment, and maintenance/deferred workflow boundaries.

## Roadmap Decomposition

This analysis is further decomposed into four concern-based sub-steps that own the detailed contracts. Future deep-planning follows the sequence **01 → 02 → 03 → 04**, starting with the route contract as the primary dependency.

- [01: Wiki Route Contract](01-wiki-route-contract.md) — Taxonomy and CLI/MCP mapping. (**First Deep-Plan Target**)
- [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md) — I/O schemas and traceability.
- [03: Governance and Mirror Alignment](03-governance-and-mirror-alignment.md) — Drift prevention and testing.
- [04: Maintenance Loop and Deferred Workflows](04-maintenance-loop-and-deferred-workflows.md) — Lifecycle and future boundaries.

---

## 1. External Reference Synthesis

### 1.1 Farzapedia (FarzaTV)

**Core idea**: An agent-owned wiki layer where the LLM actively maintains persistent knowledge on behalf of the user.

**Relevant skill commands**:
- `ingest` — pull a source into the wiki
- `absorb` — summarize and file key takeaways
- `query` — retrieve synthesized knowledge
- `cleanup` — remove stale or low-value pages
- `breakdown` — decompose a large topic into sub-pages
- `status` — dashboard of wiki health and coverage

**What Snowiki should adopt**:
- The concept of an **agent maintenance loop** (ingest → absorb → cleanup → query).
- `status` as a first-class skill route that surfaces coverage gaps and health metrics.
- The posture that the wiki is **agent-maintained**, not just agent-queried.

**What Snowiki must reject**:
- Farzapedia’s implicit write model. Snowiki must keep mutations explicit and, by default, reviewable.

### 1.2 Karpathy’s LLM Wiki

**Core idea**: A local-first, file-based knowledge system with three layers: `raw/` → `wiki/` → `schema` (rules/conventions).

**Relevant operations**:
- `ingest` — compile raw sources into structured pages
- `query` — search the compiled wiki
- `lint` — enforce schema rules and structural health

**What Snowiki should adopt**:
- The **raw → wiki → schema** layering is already reflected in Snowiki’s `sources/`, `wiki/`, and `CLAUDE.md`.
- `lint` as a mandatory step in the maintenance loop. Karpathy treats lint as a first-class operation, not an afterthought.
- The idea that **schema evolution is human-curated** (`CLAUDE.md` is the schema owner).

**Alignment with Snowiki**:
- High. Snowiki’s existing three-layer model is structurally identical. The skill contract should make this layering explicit to agents.

### 1.3 `ArtemXTech/personal-os-skills`

**Core idea**: Packaged Claude Code skills with explicit frontmatter, schema files, and route splitting.

**Relevant patterns**:
- `SKILL.md` frontmatter defines name, description, argument-hint, and allowed-tools.
- Route splitting: `ingest`, `query`, `recall`, `sync` are separate, well-defined procedures.
- Schema files (YAML/JSON) for inputs and outputs that both humans and agents validate against.
- Provenance preservation: every skill output should trace back to source material.

**What Snowiki should adopt**:
- **Schema files** for skill routes. This is missing entirely from the current Snowiki skill package.
- **Explicit route definitions** with stable argument shapes.
- **Provenance rules** baked into the contract: every skill result must include source paths or session IDs.

### 1.4 `hang-in/seCall`

**Core idea**: A Korean-aware local session search system where the vault is the source of truth and derived indexes are rebuildable.

**Relevant patterns**:
- `raw/sessions` (immutable) + `wiki/projects|topics|decisions` (derived).
- `index.md` and `log.md` as navigational and audit layers.
- Derived caches (search indexes) are rebuildable; the vault files are canonical.

**What Snowiki should adopt**:
- The principle that **the file tree is the source of truth**; the skill must not treat derived indexes (lexical, vector, MCP snapshots) as durable memory.
- `log.md` as an audit trail for agent actions.
- The rebuildability posture: if an index is corrupted, the agent should know how to trigger `snowiki rebuild`.

---

## 2. Gap Analysis: Current Snowiki Skill State

### 2.1 What exists today

**CLI runtime (authoritative)**:
- `snowiki ingest` — `src/snowiki/cli/commands/ingest.py`
- `snowiki query` — `src/snowiki/cli/commands/query.py`
- `snowiki recall` — `src/snowiki/cli/commands/recall.py`
- `snowiki rebuild` — `src/snowiki/cli/commands/rebuild.py`
- `snowiki status` — `src/snowiki/cli/commands/status.py`
- `snowiki lint` — `src/snowiki/cli/commands/lint.py`
- `snowiki export` — `src/snowiki/cli/commands/export.py`
- `snowiki benchmark` — `src/snowiki/cli/commands/benchmark.py`
- `snowiki daemon` — `src/snowiki/cli/commands/daemon.py`
- `snowiki mcp` — `src/snowiki/cli/commands/mcp.py` (bridge to read-only MCP server)

**MCP runtime (read-only)**:
- Tools: `search`, `recall`, `get_page`, `resolve_links` — `src/snowiki/mcp/server.py`
- Resources: `graph://current`, `topic://<slug>`, `session://<session-id>` — `src/snowiki/mcp/server.py`

**Skill layer (informative)**:
- `skill/SKILL.md` — workflow frontmatter and aspirational commands
- `skill/workflows/wiki.md` — detailed step-by-step routing, mixing current and deferred workflows
- `skill/scripts/status.py`, `skill/scripts/lint.py` — helper scripts

### 2.2 Identified gaps

| Gap | Severity | Evidence |
| :--- | :--- | :--- |
| **No schema files** for skill I/O | High | `skill/` has no YAML/JSON schemas for route arguments or outputs. |
| **Skill workflows mix current and deferred commands without clear markers** | High | `skill/workflows/wiki.md` lists `sync`, `edit`, `merge` alongside `ingest`, `query` with only textual "Deferred" labels. |
| **No governance test enforcing CLI/skill alignment** | High | No test fails when `skill/workflows/wiki.md` describes a command that does not exist in `src/snowiki/cli/commands/`. |
| **MCP exposes read-only tools, but skill docs do not explain how an agent should request mutations** | Medium | The skill contract should route mutations through CLI and reads through MCP/CLI JSON. |
| **Missing maintenance loop specification** | Medium | No documented loop linking ingest → absorb → lint → query. |
| **Provenance is implicit in code but explicit in contract** | Medium | MCP `search`/`recall` return `source_type` and `path`, but the skill contract does not require agents to surface them. |

---

## 3. Skill Contract Synthesis

The high-level design principles and route definitions are summarized below. Detailed contract ownership is delegated to the numbered sub-steps.

### 3.1 Design principles

1. **Thin wrapper**: The skill is a consumer of the CLI/MCP contract, not a runtime owner.
2. **Deterministic routing**: Every `/wiki` command maps unambiguously to a CLI command, an MCP tool, or a deferred workflow.
3. **Explicit schema**: All skill routes have machine-readable input and output schemas.
4. **Read/write separation**: Reads may use CLI JSON or MCP. Mutations must flow through the CLI.
5. **Provenance-first**: Every query result must expose its source path or session ID.
6. **Reviewable mutations**: Write operations default to a propose-then-apply posture unless the host explicitly relaxes this.

### 3.2 Route contract implications

The authoritative mapping of skill routes to runtime commands is owned by the [Wiki Route Contract](01-wiki-route-contract.md). This analysis is intentionally subordinate to that contract and only summarizes the implementation consequences for Step 3 work.

- **Primary current `/wiki` routes** are owned by the canonical contract: `ingest`, `query`, `recall`, `status`, `lint`, `fileback preview`, and `fileback apply`.
- **Advanced passthrough surfaces** (`export`, `benchmark`, `daemon`, `mcp`) remain part of the shipped CLI surface, but the canonical contract decides how they are exposed through `/wiki`.
- **Shipped CLI support** such as `rebuild` remains runtime support, not a primary `/wiki` route.
- **Read-only MCP tools** such as `search`, `get_page`, `resolve_links`, and MCP-side recall support retrieval flows, but they are not standalone `/wiki` route definitions in this analysis.
- **Deferred workflows** (`sync`, `edit`, `merge`, and graph-oriented workflows) stay deferred until the later maintenance/deferred-workflow contract owns them.

### 3.3 Schema and provenance ownership handoff

This analysis no longer carries draft route schemas or duplicate provenance tables. The canonical owner for current `/wiki` route-adjacent schema, provenance, display, error-envelope, and reviewable-write truth is [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md).

Read that contract for the current CLI JSON minimums, MCP transport wrappers, fileback reviewed-write payload rules, provenance/display minimums, and failure semantics. Any future skill schema files should mirror that canonical contract instead of redefining it here.

### 3.4 Maintenance loop ownership handoff

This analysis intentionally does not finalize the agent maintenance loop or deferred workflow sequencing. That ownership belongs to [04: Maintenance Loop and Deferred Workflows](04-maintenance-loop-and-deferred-workflows.md).

For this analysis, the durable takeaway is only the boundary: reads may use CLI JSON or the read-only MCP surface, while reviewed writes remain CLI-mediated through `fileback preview` and `fileback apply`.

---

## 4. Implementation Mapping to Snowiki Codebase

This section maps the contract needs to the existing codebase. Detailed task ownership for these mappings is defined in the numbered sub-steps.

### 4.1 What already supports the contract

| Contract Need | Existing Code Location |
| :--- | :--- |
| Ingest command | `src/snowiki/cli/commands/ingest.py` |
| Query command | `src/snowiki/cli/commands/query.py` |
| Recall command (auto-routing) | `src/snowiki/cli/commands/recall.py` |
| Status command | `src/snowiki/cli/commands/status.py` |
| Lint command | `src/snowiki/cli/commands/lint.py` |
| Rebuild command | `src/snowiki/cli/commands/rebuild.py` |
| MCP search tool | `src/snowiki/mcp/tools/search.py` |
| MCP recall tool | `src/snowiki/mcp/tools/recall.py` |
| MCP get_page tool | `src/snowiki/mcp/tools/get_page.py` |
| MCP resolve_links tool | `src/snowiki/mcp/tools/resolve_links.py` |
| Read-only facade | `src/snowiki/mcp/server.py` (`SnowikiReadOnlyFacade`) |
| Skill frontmatter | `skill/SKILL.md` |
| Workflow descriptions | `skill/workflows/wiki.md` |

### 4.2 Ownership map for implementation follow-through

This analysis does not carry the implementation task list. Immediate follow-through belongs to the numbered Step 3 owners: route exposure in [01: Wiki Route Contract](01-wiki-route-contract.md), schema/provenance truth in [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md), governance/mirror alignment in [03: Governance and Mirror Alignment](03-governance-and-mirror-alignment.md), and maintenance/deferred workflow boundaries in [04: Maintenance Loop and Deferred Workflows](04-maintenance-loop-and-deferred-workflows.md).

### 4.3 No new runtime backend required

The skill contract can be fulfilled entirely with the existing CLI and MCP surfaces. This aligns with the roadmap constraint: **"Keep the skill as a thin, deterministic wrapper over the canonical CLI/MCP contract."**

---

## 5. Resolving Open Questions

The `step3_wiki-skill-design/roadmap.md` raised three open questions. This section proposes resolutions.

### 5.1 Reviewable memory updates vs. direct writes

**Resolution**: Default to **reviewable memory updates** (`Propose-Mutate` + `Required` approval) for all skill-mediated writes. Direct writes require an explicit host opt-in.

**Rationale**:
- The skill contract must not bypass CLI-level validations.
- `docs/architecture/skill-and-agent-interface-contract.md` already defines `Propose-Mutate` and `Required` approval semantics.
- In the current shipped contract, MCP is read-only and mutation flows through CLI. The skill should reinforce this boundary.

### 5.2 Local image and attachment ingestion

**Resolution**: Defer first-class image/attachment ingestion to a future step. Until then, the skill should **reject or warn** on image ingestion requests and suggest storing attachments as markdown-linked external files.

**Rationale**:
- The current CLI `ingest` surface is text-oriented.
- Adding multimodal ingestion requires changes to the compiler, indexer, and page schema.
- This is out of scope for the medium-term hybrid-ready transition.

### 5.3 Granularity of lint reports

**Resolution**: The skill should surface lint reports at **three granularities simultaneously**:
- **Per-page**: which pages have errors/warnings.
- **Per-source**: which sources lack summaries or have broken provenance.
- **Per-query**: when a query result points to a page with known lint issues, surface a warning.

**Rationale**:
- `snowiki lint` already operates over the entire vault and can emit structured JSON.
- Presenting all three granularities gives the agent enough context to fix issues or warn the user.

---

## 6. Reference fit: Snowiki vs. external patterns

These external patterns remain background inputs, not current ownership surfaces:

- **Farzapedia** contributed the maintenance-loop framing, but current loop ownership now lives in [04: Maintenance Loop and Deferred Workflows](04-maintenance-loop-and-deferred-workflows.md).
- **Karpathy's LLM Wiki** reinforced the raw-to-derived layering already present in Snowiki's runtime and documentation.
- **personal-os-skills** informed the schema-first skill packaging direction, while current schema/provenance truth now lives in [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md).
- **seCall** reinforced the file-tree-as-truth posture and rebuildability boundary for derived indexes.
- **qmd lineage** remains reference lineage only, not current Snowiki runtime contract.

---

## 7. How to use this analysis now

Use this document as background synthesis for why Step 3 was split into numbered owners. For current contract truth and follow-through:

- use [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md) for schema/provenance, display, error-envelope, and reviewable-write truth
- use [04: Maintenance Loop and Deferred Workflows](04-maintenance-loop-and-deferred-workflows.md) for maintenance-loop and deferred workflow ownership
- use the numbered Step 3 documents and their deep plans, not this analysis, for execution-ready tasks and promotion criteria

### Conclusion

Step 3 does not require deep architectural invention. It requires **contract discipline**: defining exactly what the `/wiki` skill promises, how it maps to the existing CLI/MCP runtime, and how it prevents drift. The external references (Farzapedia, Karpathy, personal-os-skills, seCall) provide the UX patterns and organizational principles, but the runtime truth remains Snowiki’s Python CLI. The skill should be a transparent, schema-first wrapper around that truth.

The lasting value of this analysis is the synthesis behind the numbered Step 3 documents, not ownership of the current contract or near-term action plan.

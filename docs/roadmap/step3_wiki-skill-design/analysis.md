# Step 3 Analysis: Wiki Skill Design

## Executive Summary

This document synthesizes external reference research (Farzapedia, Karpathy’s LLM Wiki, `personal-os-skills`, and `seCall`) and maps their patterns onto Snowiki’s current runtime. The conclusion is that Snowiki’s `/wiki` skill should be a **thin, schema-first wrapper over the existing CLI and read-only MCP surfaces**, not a separate runtime backend.

The current skill layer (`skill/SKILL.md`, `skill/workflows/wiki.md`) contains aspirational workflows that drift from the shipped CLI contract. The goal of this step is to define a deterministic skill contract that agents can rely on, with explicit input/output schemas, a clear maintenance loop, and governance tests that fail when the skill description diverges from the CLI.

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

### 3.3 Input/output schema drafts

#### `wiki ingest`

```yaml
# skill/schemas/ingest-input.yaml
name: ingest-input
type: object
required:
  - source
properties:
  source:
    type: string
    description: URL, file path, or inline text to ingest
  source_type:
    type: string
    enum: [auto, article, session, note]
    default: auto
  tags:
    type: array
    items:
      type: string
```

```yaml
# skill/schemas/ingest-output.yaml
name: ingest-output
type: object
required:
  - ok
  - source_path
  - pages_created
  - pages_updated
properties:
  ok:
    type: boolean
  source_path:
    type: string
  pages_created:
    type: array
    items:
      type: string
  pages_updated:
    type: array
    items:
      type: string
  errors:
    type: array
    items:
      type: string
```

#### `wiki query`

```yaml
# skill/schemas/query-input.yaml
name: query-input
type: object
required:
  - question
properties:
  question:
    type: string
  output:
    type: string
    enum: [json, markdown, text]
    default: json
  limit:
    type: integer
    default: 5
```

```yaml
# skill/schemas/query-output.yaml
name: query-output
type: object
required:
  - ok
  - command
  - result
properties:
  ok:
    type: boolean
  command:
    type: string
  result:
    type: object
    properties:
      hits:
        type: array
        items:
          type: object
          properties:
            path:
              type: string
            title:
              type: string
            score:
              type: number
            source_type:
              type: string
            summary:
              type: string
```

#### `wiki recall`

```yaml
# skill/schemas/recall-input.yaml
name: recall-input
type: object
required:
  - target
properties:
  target:
    type: string
    description: Date expression, topic, or session identifier
  mode:
    type: string
    enum: [auto, date, temporal, known_item, topic]
    default: auto
  limit:
    type: integer
    default: 5
```

```yaml
# skill/schemas/recall-output.yaml
name: recall-output
type: object
required:
  - ok
  - command
  - result
properties:
  ok:
    type: boolean
  command:
    type: string
  result:
    type: object
    properties:
      strategy:
        type: string
      hits:
        type: array
        items:
          type: object
          properties:
            path:
              type: string
            title:
              type: string
            recorded_at:
              type: string
            source_type:
              type: string
      one_thing:
        type: string
        description: Synthesized highest-leverage next action
```

#### `wiki status`

```yaml
# skill/schemas/status-output.yaml
name: status-output
type: object
required:
  - ok
  - pages
  - sources
  - health
properties:
  ok:
    type: boolean
  pages:
    type: object
    properties:
      total:
        type: integer
      summaries:
        type: integer
      concepts:
        type: integer
      entities:
        type: integer
      topics:
        type: integer
      comparisons:
        type: integer
      questions:
        type: integer
  sources:
    type: object
    properties:
      total:
        type: integer
      articles:
        type: integer
      sessions:
        type: integer
      notes:
        type: integer
  health:
    type: object
    properties:
      errors:
        type: integer
      warnings:
        type: integer
```

### 3.4 Maintenance loop design

The agent-facing wiki workflow should follow this loop:

```
Ingest  ->  Absorb  ->  Lint/Cleanup  ->  Query  ->  (File Back)
   ^                                            |
   +--------------------------------------------+
```

**Ingest**: Acquire source (URL, file, text, session) and compile it into `sources/` and `wiki/summaries/`.

**Absorb**: Post-ingest synthesis. The agent reads the summary and updates concept, entity, topic, comparison, and overview pages. This is currently agent-driven (via LLM reasoning), not a CLI command.

**Lint/Cleanup**: Run `snowiki lint` to detect structural errors, broken links, orphan pages, and stale content. Propose cleanup actions (e.g., merge overlapping pages, remove stale questions).

**Query**: Use `snowiki query` or MCP `search`/`recall` to answer user questions from the compiled wiki.

**File Back** (optional): If an answer is valuable, the agent may propose creating a `wiki/questions/` page. This remains a propose-then-apply step.

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

### 4.2 What needs to be added or modified

| Task | Priority | Rationale |
| :--- | :--- | :--- |
| Create `skill/schemas/*.yaml` for all current routes | High | Schema files are the missing layer between agent and runtime. |
| Add governance test `tests/governance/test_skill_contract_alignment.py` | High | Ensures `skill/workflows/wiki.md` never describes a non-existent CLI command. |
| Update `skill/SKILL.md` argument-hint to match current CLI only | Medium | Remove deferred commands from the primary hint or mark them explicitly. |
| Add `one_thing` synthesis guidance to `skill/workflows/wiki.md` | Medium | Formalize the "One Thing" pattern already practiced in recall workflows. |
| Define `absorb` and `cleanup` as agent-level wrappers (not CLI commands) | Low | These are orchestration patterns, not runtime mutations. They belong in the skill workflow, not the CLI. |

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

## 6. Synthesis: Snowiki vs. External Patterns

| Pattern Source | Key Idea | Snowiki Adoption | Snowiki Adaptation |
| :--- | :--- | :--- | :--- |
| **Farzapedia** | Agent-owned wiki with maintenance loop | Maintenance loop (`ingest → absorb → lint → query`) | Require explicit approval for writes |
| **Karpathy LLM Wiki** | Raw → wiki → schema layering | Reinforce `sources/`, `wiki/`, `CLAUDE.md` layering | Add lint as a mandatory loop step |
| **personal-os-skills** | SKILL.md frontmatter + schema files | Add `skill/schemas/*.yaml` for all routes | Keep schemas versioned with the CLI |
| **seCall** | Vault = source of truth; indexes are rebuildable | Agent should prefer file reads over derived indexes | Document `rebuild` as the index recovery path |
| **qmd lineage** | Hybrid retrieval, MCP integration, session recall | Future design target for Steps 4–5 | Keep as reference, not current runtime contract |

---

## 7. Recommendations and Next Actions

### Immediate next actions (before promoting to `.sisyphus/plans/`)

1. **Create schema files** (`skill/schemas/`) for `ingest`, `query`, `recall`, `status`, and `lint` routes.
2. **Write the governance test** `tests/governance/test_skill_contract_alignment.py` that parses `skill/workflows/wiki.md` and verifies every "Current" route exists in `src/snowiki/cli/commands/`.
3. **Update `skill/SKILL.md`** to reflect the current CLI-only posture and remove deferred commands from the primary argument hint.
4. **Add a maintenance-loop diagram** to `skill/workflows/wiki.md` clarifying which steps are CLI calls, which are agent reasoning, and which are deferred.

### Promotion criteria checklist

- [x] Scope is implementation-ready (schemas and governance tests are concrete).
- [x] No new runtime backend is required.
- [ ] Acceptance criteria are documented (this analysis provides them).
- [ ] Verification commands are known (`pytest tests/governance/test_skill_contract_alignment.py`).
- [ ] Dependencies (Step 1 lexical contract stabilization) are satisfied.

### Conclusion

Step 3 does not require deep architectural invention. It requires **contract discipline**: defining exactly what the `/wiki` skill promises, how it maps to the existing CLI/MCP runtime, and how it prevents drift. The external references (Farzapedia, Karpathy, personal-os-skills, seCall) provide the UX patterns and organizational principles, but the runtime truth remains Snowiki’s Python CLI. The skill should be a transparent, schema-first wrapper around that truth.

Once the schema files and governance test are implemented, Step 3 is ready for promotion to `.sisyphus/plans/`.

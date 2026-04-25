# CLI Command Taxonomy

## Purpose

This document classifies Snowiki's shipped CLI commands by product role.

The `src/snowiki/cli/commands/` modules are runtime adapters for parsing and dispatching CLI subcommands. They are not themselves the philosophical list of LLM wiki workflow intents. A command may be important runtime infrastructure without being an everyday `/wiki` skill action.

## Command classes

| Class | Commands | Role |
| :--- | :--- | :--- |
| Knowledge flow | `ingest`, `query`, `recall` | Primary knowledge loop: accept durable material, answer from memory/evidence, and recover temporal/topic context. |
| Lifecycle and health | `status`, `lint`, `fileback` | Keep source freshness, structure, and reviewable writeback visible and safe. |
| Maintenance and rebuild | `rebuild`, `prune` | Recompute derived state or remove stale accepted records through explicit maintenance paths. |
| Runtime/control plane | `daemon` | Runtime optimization/control-plane surface. It must not redefine CLI truth. |
| Transport bridge | `mcp` | Read-only MCP bridge for tools/resources. It is a transport surface, not a mutation or workflow command family. |
| Support/debug/export | `export` | Portability, inspection, migration, and snapshot/debug support. Not a primary wiki flow. |
| Development/evaluation | `benchmark`, `benchmark-fetch` | Retrieval and benchmark development support. Not a user memory workflow. |

## Command package layout

Command adapter files live flat under `src/snowiki/cli/commands/` with one module per shipped top-level command. Each adapter should stay small and delegate quickly to domain modules.

The role taxonomy below is the conceptual ownership map, not a directory tree. This keeps CLI import paths short while preserving the product-role distinction in architecture docs and review checklists.

Current layout:

```text
src/snowiki/cli/commands/
  ingest.py
  query.py
  recall.py
  status.py
  lint.py
  fileback.py
  rebuild.py
  prune.py
  daemon.py
  mcp.py
  export.py
  benchmark.py
  benchmark_fetch.py
```

Grouping criteria:

| Criterion | Meaning | Example |
| :--- | :--- | :--- |
| Product role | What part of the wiki lifecycle the command represents. | `ingest` belongs to the knowledge flow; `prune` belongs to maintenance. |
| Primary consumer | Who normally invokes or depends on it. | Agents use `query`; benchmark maintainers use `benchmark`. |
| Mutation posture | Whether the command reads, proposes, applies, or deletes durable state. | `mcp` is read-only; `fileback` proposes/applies; `prune` deletes only through explicit maintenance. |
| Contract status | Whether the command is everyday runtime truth, support/debug, transport, or dev/eval. | `export` is support/debug; `benchmark-fetch` is dev/eval. |

Avoid grouping by vague nouns such as `utils`, by output format, or by whether a command happens to share a helper today. CLI adapters should stay thin; shared behavior should move into domain modules only when there is a real domain boundary.

Do not add directory depth as a cosmetic refactor. A subpackage becomes worthwhile only when multiple commands share enough implementation or ownership to reduce review load. The taxonomy should remain the conceptual source of truth when the physical package stays flat.

Implementation sequencing for this taxonomy lives in `docs/architecture/cli-command-implementation-plan.md`.

## Primary wiki loop

The smallest user-facing LLM wiki loop is:

1. `snowiki ingest <path> [options]`
2. `snowiki query <question>` or `snowiki recall <time-or-topic>`
3. `snowiki status` / `snowiki lint` when freshness or structure is uncertain
4. `snowiki fileback ...` when an accepted answer should become a reviewable durable edit

Skill workflows should expand short `/wiki` intents into these CLI commands instead of inventing shadow commands.

## Command role details

### `ingest`

`ingest` is the entry path for durable source material. For broad directories plus a user goal, agent workflows should inspect evidence, write one focused Markdown note when appropriate, and ingest that durable note rather than bulk-ingesting operational files by accident.

### `query`

`query` is the authoritative CLI retrieval command for knowledge questions. It may surface compiled pages, normalized records, and provenance metadata, but it should preserve the difference between derived memory and source evidence.

### `recall`

`recall` is the temporal/topic continuity surface. It overlaps conceptually with query, but its product role is context recovery rather than general question answering.

### `status` and `lint`

`status` reports freshness and indexed state. `lint` reports structural and source-health issues. They are lifecycle commands, not optional polish, because a compiled wiki must remain inspectable and maintainable.

### `fileback`

`fileback` is the reviewable writeback path. Preview and queue outputs are proposals, not accepted source truth. Durable changes enter the wiki only after an approved CLI apply path succeeds.

### `rebuild` and `prune`

`rebuild` recomputes derived state from accepted memory. `prune` removes stale accepted source records only through narrow, explicit, dry-run-first maintenance flows. Neither should be presented as everyday knowledge authoring.

### `daemon`

`daemon` may improve performance or long-running runtime behavior, but it is not a second product contract. Skill and agent instructions should continue to call documented `snowiki ... --output json` commands instead of implementing daemon-specific fallback logic.

### `mcp`

`mcp` is a read-only bridge. The shipped shape is `snowiki mcp serve --stdio`. MCP tools/resources expose read-only retrieval semantics and must not be treated as write-capable equivalents of CLI commands.

### `export`

`export` is a support/debug surface.

Useful cases include:

- backup or migration snapshots
- inspection of normalized records or compiled pages
- test fixtures and reproducibility checks
- integration with external tooling that expects bulk files or JSON

It should not be promoted as a core `/wiki` workflow while the source/vault model remains filesystem-first and the runtime already exposes direct source roots plus generated compiled pages. If the maintenance cost grows faster than these use cases, `export` should be treated as a deprecation candidate rather than a primary command.

### `benchmark` and `benchmark-fetch`

Benchmark commands belong to retrieval development and evaluation. They should inform runtime quality gates, but benchmark behavior is not the shipped wiki memory contract.

## Skill mapping rule

Claude/OpenCode skills should map user intent to command classes:

- everyday knowledge work: `ingest`, `query`, `recall`
- health and cleanup: `status`, `lint`, `prune` dry-run before delete
- reviewed durable writes: `fileback`
- runtime optimization: `daemon` only when explicitly needed by the runtime setup
- transport: `mcp` only for read-only tool/resource exposure
- support: `export` only when the user asks for backup, migration, inspection, or external integration

This prevents command names from becoming product promises that the runtime does not actually make.

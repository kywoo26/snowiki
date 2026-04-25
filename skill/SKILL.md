---
name: wiki
description: "Snowiki — CLI-first workflow skill. Use the installed snowiki runtime for ingest, query, recall, status, lint, dry-run-first source prune, and reviewable fileback/queue flows. The skill mirrors current CLI truth, prefers daemon-backed reads only as an optimization, and keeps sync/standalone edit/standalone merge/graph workflows deferred unless a future runtime spec explicitly ships them."
argument-hint: [ingest SOURCE|query QUESTION|recall TARGET|status|lint|prune sources|fileback preview QUESTION|fileback preview --queue QUESTION|fileback queue list|fileback apply|export|benchmark PRESET|daemon|mcp]
allowed-tools: Bash(python3:*), Read, Write, Edit, Glob, Grep, WebFetch
---

# Snowiki — CLI-First Wiki Workflow Skill

A persistent wiki that compounds knowledge like a snowball.

The authoritative runtime contract is the installed `snowiki` CLI.

This skill is an informative reference layer for orchestrating the shipped CLI. It projects the canonical artifact model (Commands, Skills, Memory) defined in `docs/architecture/skill-and-agent-interface-contract.md`. For the authoritative mapping of skill routes to runtime commands, see the [Wiki Route Contract](../docs/roadmap/step3_wiki-skill-design/01-wiki-route-contract.md).

## Current shipped commands

Atomic units of execution provided by the `snowiki` CLI:

### Primary Current Routes
- `snowiki ingest`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki prune`
- `snowiki fileback`

### Advanced Passthrough
- `snowiki export`
- `snowiki benchmark`
- `snowiki benchmark-fetch`
- `snowiki daemon`
- `snowiki mcp`

### Shipped CLI Support
- `snowiki rebuild` (not a primary `/wiki` route)

## Skill role

This skill is orchestration and reference text around the shipped CLI. It must not silently redefine runtime capabilities.

Use it when the user asks for:

- wiki ingest
- wiki query
- wiki recall
- wiki status
- wiki lint
- wiki start / progress / finish / health
- reviewable file-back of a useful answer
- what do I know about X
- what did we work on yesterday / last week

Lifecycle route names such as `/wiki-start`, `/wiki-progress`, `/wiki-finish`, and `/wiki-health` are skill workflows, not `snowiki` subcommands. They expand to the installed CLI: status/recall/query for start, status/lint for progress and health, and session Markdown plus ingest/fileback for finish. See `workflows/wiki.md` for the detailed routing.

Runtime validation:
- installed runtime: `snowiki --help`
- development checkout: `uv run snowiki --help`
- Claude Code skill package location: `~/.claude/skills/wiki/`

## Current Runtime Truth

Use the installed `snowiki` command as the primary interface.

Machine-usable interfaces today:
- CLI with `--output json` where supported
- read-only MCP via `snowiki mcp`

Read optimization:
- daemon-backed reads for `query` and `recall` are preferred only when a daemon is already reachable
- CLI fallback remains canonical and supported

Write posture:
- `fileback` is current shipped behavior
- `fileback preview` is non-mutating and reviewable
- `fileback preview --queue` persists a pending proposal under the active Snowiki root without applying it
- `fileback preview --queue --auto-apply-low-risk` may apply only when runtime policy proves the proposal low-risk
- `fileback queue list`, `queue show`, `queue apply`, `queue reject`, and `queue prune` manage CLI queue lifecycle state
- `fileback apply` requires a reviewed proposal file
- `prune sources --dry-run` previews missing-source cleanup candidates; destructive cleanup requires `prune sources --delete --yes --all-candidates`
- MCP write support is not shipped

## Current Commands vs Deferred Workflow Ideas

### Current shipped commands

#### `ingest`
Ingest a supported source into Snowiki storage.

Claude/OpenCode session exports should be summarized into durable Markdown notes before ingest. Do not treat raw session exports as the primary `snowiki ingest PATH` workflow.

#### `query`
Search compiled knowledge through the current lexical retrieval runtime.

#### `recall`
Recall against current stored knowledge/session-derived material through the shipped Snowiki runtime.

#### `status`, `lint`, `prune`, `export`, `benchmark`, `benchmark-fetch`, `daemon`, `mcp`
These are all part of the current shipped CLI surface and should be invoked through `snowiki ...`.

Use `status` and `lint` before source gardening. `status` gives source freshness summary counts, while `lint --output json` gives actionable `source.modified`, `source.missing`, `source.untracked`, and `source.rename_candidate` findings. Use `prune sources --dry-run` before any destructive source cleanup, and inspect rename candidates before pruning missing-source records.

#### `fileback`
Use `snowiki fileback preview` to produce a reviewed proposal, `snowiki fileback preview --queue` to persist a non-blocking pending proposal, `snowiki fileback queue list/show/apply/reject/prune` to manage queue lifecycle state, `snowiki fileback preview --queue --auto-apply-low-risk` only for runtime-proven low-risk proposals, and `snowiki fileback apply` to persist a reviewed proposal file through the canonical CLI path.

### Deferred / broader workflow ideas

The following remain workflow or roadmap concepts rather than guaranteed shipped commands in the current runtime:
- sync
- standalone edit
- standalone merge
- graph-oriented recall workflows
- qmd-backed hybrid/vector routing as a default runtime path

Treat them as future-facing workflow concepts unless the runtime explicitly exposes them. Claude/OpenCode/OMO agents should orchestrate current CLI truth without claiming those standalone commands ship.

## Search Strategy

Current shipped runtime posture:
- lexical-first retrieval
- deterministic benchmarked backend
- semantic/hybrid/rerank remain deferred architecture work

qmd remains lineage/reference material, not the current canonical runtime search engine.

## Workflow

See `workflows/wiki.md` for the current workflow interpretation of the shipped CLI plus clearly marked deferred ideas.

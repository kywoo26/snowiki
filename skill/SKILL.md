---
name: wiki
description: "Snowiki — CLI-first workflow skill. Use the installed snowiki runtime for ingest, query, recall, status, lint, and reviewable fileback flows. The skill mirrors current CLI truth, prefers daemon-backed reads only as an optimization, and keeps sync/edit/merge/graph workflows deferred."
argument-hint: [ingest SOURCE|query QUESTION|recall TARGET|status|lint|fileback preview QUESTION|fileback apply|export|benchmark PRESET|daemon|mcp]
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
- `snowiki fileback`

### Advanced Passthrough
- `snowiki export`
- `snowiki benchmark`
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
- reviewable file-back of a useful answer
- what do I know about X
- what did we work on yesterday / last week

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
- `fileback apply` requires a reviewed proposal file
- MCP write support is not shipped

## Current Commands vs Deferred Workflow Ideas

### Current shipped commands

#### `ingest`
Ingest a supported source into Snowiki storage.

#### `query`
Search compiled knowledge through the current lexical retrieval runtime.

#### `recall`
Recall against current stored knowledge/session-derived material through the shipped Snowiki runtime.

#### `status`, `lint`, `export`, `benchmark`, `daemon`, `mcp`
These are all part of the current shipped CLI surface and should be invoked through `snowiki ...`.

#### `fileback`
Use `snowiki fileback preview` to produce a reviewed proposal and `snowiki fileback apply` to persist that reviewed proposal through the canonical CLI path.

### Deferred / broader workflow ideas

The following remain workflow or roadmap concepts rather than guaranteed shipped commands in the current runtime:
- sync
- edit
- merge
- graph-oriented recall workflows
- qmd-backed hybrid/vector routing as a default runtime path

Treat them as future-facing workflow concepts unless the runtime explicitly exposes them.

## Search Strategy

Current shipped runtime posture:
- lexical-first retrieval
- deterministic benchmarked backend
- semantic/hybrid/rerank remain deferred architecture work

qmd remains lineage/reference material, not the current canonical runtime search engine.

## Workflow

See `workflows/wiki.md` for the current workflow interpretation of the shipped CLI plus clearly marked deferred ideas.

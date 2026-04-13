---
name: wiki
description: "Snowiki — CLI-first workflow skill. Ingest sources, query compiled knowledge, and recall session history. Commands (ingest, query, recall, status, lint) are authoritative runtime surfaces. Skills (wiki, recall) are reusable procedures. Memory (sources/, wiki/, sessions/) is the ground truth. Use when user says: wiki ingest, wiki query, wiki lint, wiki status, wiki recall, what do I know about, recall, what did we work on, load context, yesterday, last week, session history. Note: sync, edit, merge, and graph flows are deferred reference workflows."
argument-hint: [ingest SOURCE|query QUESTION|recall TARGET|status|lint|export|benchmark PRESET|daemon|mcp]
allowed-tools: Bash(python3:*), Read, Write, Edit, Glob, Grep, WebFetch
---

# Snowiki — CLI-First Wiki Workflow Skill

A persistent wiki that compounds knowledge like a snowball.

The authoritative runtime contract is the installed `snowiki` CLI.

This skill is an informative reference layer for orchestrating the shipped CLI. It projects the canonical artifact model (Commands, Skills, Memory) defined in `docs/architecture/skill-and-agent-interface-contract.md`.

## Artifact Classes

### Commands (Invocation Surface)
Atomic units of execution provided by the `snowiki` CLI.
- `snowiki ingest`, `rebuild`, `query`, `recall`, `status`, `lint`, `export`, `benchmark`, `daemon`, `mcp`.

### Skills (Reusable Procedures)
Higher-level orchestration logic for agents.
- `wiki` skill: General wiki management and compilation.
- `recall` skill: Temporal and topic-based context loading.

### Memory (Ground Truth)
Persistent state of the Snowiki system.
- `sources/`: Immutable raw documents.
- `wiki/`: LLM-compiled knowledge.
- `sessions/`: Active or frozen session logs.

## Current Runtime Truth

Use the installed `snowiki` command as the primary interface.

Machine-usable interfaces today:
- CLI with `--output json` where supported
- read-only MCP via `snowiki mcp`

## Workflow Context (Informative)

```
Source in -> LLM compiles -> Wiki grows -> Query draws from wiki -> Good answers filed back -> Snowball
Sessions -> Recall loads context -> future sync/edit/merge flows may compound back into the wiki
```

**Human** curates sources, asks questions, thinks.
**LLM** summarizes, cross-references, files, maintains consistency, and recalls context.

> **Note**: Broader sync, edit, merge, and graph-oriented flows are deferred reference workflows, not shipped runtime behavior.

## Architecture Context

Three layers:
1. **sources/** — immutable raw material (articles, notes). Never modified.
2. **sessions/** — cc session exports (live while active, frozen after). Separate from sources/.
3. **wiki/** — LLM-owned compiled knowledge (summaries, concepts, entities, topics, comparisons, questions, overview).
4. **CLAUDE.md** — rules for structure, conventions, workflows.

Read `CLAUDE.md` when operating inside a Snowiki-style vault workflow.

## Page Types

| Type | Directory | Purpose | Example |
|------|-----------|---------|---------|
| summary | `wiki/summaries/` | 1:1 with source. The compilation step. | `karpathy-llm-wiki.md` |
| concept | `wiki/concepts/` | Single idea. "What is X?" | `rag.md`, `bm25.md` |
| entity | `wiki/entities/` | Person, tool, org, project. | `qmd.md`, `karpathy.md` |
| topic | `wiki/topics/` | Cross-cutting theme. | `korean-nlp.md` |
| comparison | `wiki/comparisons/` | Side-by-side with table. | `rag-vs-wiki.md` |
| question | `wiki/questions/` | Filed query answer. | `2026-04-07-why-wiki-beats-rag.md` |
| overview | `wiki/overview.md` | Evolving synthesis. Singleton. | -- |

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

## Obsidian Graph Integration

All cross-references use `[[wikilinks]]` for Obsidian graph connectivity:
- Every page has `related:` array in frontmatter, rendered as backlinks
- Inline `[[wiki/concepts/bm25]]` links within body text
- Entity pages become hub nodes (many inbound links)
- Topic pages bridge concept clusters
- Session pages link to artifacts they created/modified
- The graph should show natural knowledge clusters, not a flat list

## Environment

Scripts reference these paths and variables:
- `VAULT_DIR` — root of the Obsidian vault (detect via `git rev-parse --show-toplevel` or fallback to cwd)
- `TZ` — timezone for temporal queries (default: system timezone)
- `~/.claude/skills/wiki/scripts/` — skill scripts (recall-day.py, session-graph.py, lint.py, status.py)
- `~/.claude/projects/` — Claude Code JSONL session files (for recall)

## Workflow

See `workflows/wiki.md` for the current workflow interpretation of the shipped CLI plus clearly marked deferred ideas.

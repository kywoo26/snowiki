# snowiki ❄️

A personal wiki that compounds knowledge like a snowball.

Instead of re-deriving knowledge on every query, the LLM incrementally builds and maintains a persistent, interlinked wiki. Every source ingested makes it richer. Knowledge compounds.

## Three Layers

```
sources/        → immutable raw documents (articles, notes)
sessions/       → cc session exports (live while active, frozen after)
wiki/           → LLM-compiled knowledge (summaries, concepts, entities, topics)
CLAUDE.md       → the schema (rules, conventions, workflows)
```

**You** curate sources, ask questions, think.
**LLM** summarizes, cross-references, files, maintains — all the bookkeeping humans abandon.

## Quick Start

Snowiki’s current shipped runtime is **CLI-first**.

The authoritative runtime contract is the installed `snowiki` command, not the older qmd-oriented `/wiki` workflow text. This README is an **informative mirror** of the canonical contract at `docs/architecture/skill-and-agent-interface-contract.md`.

```bash
# 1. Install Snowiki from a checkout
uv tool install --from . snowiki

# 2. Inspect the shipped command surface
snowiki --help

# 3. Use the current runtime directly
snowiki ingest /path/to/claude-export.jsonl --source claude
snowiki rebuild
snowiki query "What do I know about X?" --output json
snowiki recall yesterday --output json
snowiki lint
snowiki status
```

If you are working from a development checkout instead of a tool install, the equivalent commands are available via `uv run snowiki ...`.

## Current shipped CLI surface

The current runtime exposes these commands:

- `snowiki ingest`
- `snowiki rebuild`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki export`
- `snowiki benchmark`
- `snowiki daemon`
- `snowiki mcp`

## Workflow skill status

The `skill/` package is currently best understood as a **workflow/reference layer**, not the canonical runtime contract.

- It still contains legacy qmd-oriented guidance and broader aspirational wiki workflows.
- The current shipped product truth is the Python `snowiki` CLI and its read-only MCP surface.
- If you want a reliable machine-usable interface today, prefer `snowiki ... --output json` and `snowiki mcp`.

## Historical workflow surface (Lineage)

Earlier Snowiki workflow docs described a broader `/wiki` interface. This workflow remains useful as **lineage and future design context**, but it is **not** the authoritative runtime contract for the current shipped CLI.

| Command | What it does |
|---------|-------------|
| `/wiki ingest <source>` | Compile source → 5-15 wiki pages |
| `/wiki query <question>` | Search wiki → synthesize → file back |
| `/wiki recall <date/topic>` | Session history (temporal, topic, graph) |
| `/wiki sync` | Export sessions to Obsidian markdown |
| `/wiki edit <page>` | Lightweight page modification |
| `/wiki merge <p1> <p2>` | Consolidate overlapping pages |
| `/wiki lint` | Structural + semantic health check |
| `/wiki status` | Dashboard: pages, sources, health |

The current runtime truth is defined by the `snowiki` CLI and its read-only MCP surface.

## Obsidian Integration

- `[[wikilinks]]` everywhere for graph connectivity
- Entity pages = hub nodes (many inbound links)
- Topic pages = bridges between concept clusters
- overview.md = central synthesis node
- Graph view reveals natural knowledge structure

## Lint Codes

| Code | Severity | Check |
|------|----------|-------|
| L001 | ERROR | Missing/incomplete frontmatter |
| L002 | ERROR | Broken wikilinks |
| L003 | WARN | Orphan pages (no inbound links) |
| L004 | WARN | Source without summary page |
| L005 | ERROR | Page missing from index.md |
| L006 | INFO | Stale pages (30+ days) |

## Design Principles

1. **Compilation, not storage** — sources are compiled into structured, interlinked wiki pages
2. **Epistemic integrity** — every claim traces to a source, contradictions flagged not smoothed
3. **Graph-first** — every design decision considers Obsidian graph view
4. **Search-strategic** — lexical-first retrieval now, with semantic/hybrid layers deferred until evidence promotes them
5. **Progressive growth** — start simple, structure emerges from content
6. **Human insight preserved** — `[!insight]` callouts never modified by LLM

## Related

- [qmd-system](https://github.com/kywoo26/qmd-system) — infrastructure setup (qmd + Claude Code + Obsidian)
- [qmd](https://github.com/tobi/qmd) — retrieval lineage reference, not the current Snowiki runtime. Snowiki uses a lexical-first retrieval strategy in its current shipped CLI.

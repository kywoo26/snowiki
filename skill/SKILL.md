---
name: wiki
description: "Snowiki — unified LLM wiki with recall and sync. Ingest sources into structured wiki pages. Query compiled knowledge. Recall sessions by date, topic, or graph. Sync sessions to Obsidian. Edit pages. Merge overlapping pages. Lint for health. Use when user says: wiki ingest, wiki query, wiki lint, wiki status, wiki recall, wiki sync, wiki edit, wiki merge, add to wiki, file this, search wiki, what do I know about, recall, what did we work on, load context, yesterday, last week, session history, recall graph, sync sessions, export sessions, log session."
argument-hint: [ingest SOURCE|query QUESTION|recall DATE_OR_TOPIC|sync|edit PAGE|merge PAGE1 PAGE2|lint|status]
allowed-tools: Bash(python3:*), Bash(qmd:*), Read, Write, Edit, Glob, Grep, WebFetch, mcp__plugin_qmd_qmd__query, mcp__plugin_qmd_qmd__get
---

# Snowiki — Unified LLM Wiki Skill

A persistent wiki that compounds knowledge like a snowball, with integrated recall and session sync.

## Core Loop

```
Source in -> LLM compiles -> Wiki grows -> Query draws from wiki -> Good answers filed back -> Snowball
Sessions -> Recall loads context -> Sync exports to Obsidian -> Sessions become sources -> Snowball
```

**Human** curates sources, asks questions, thinks.
**LLM** summarizes, cross-references, files, maintains consistency, recalls context, syncs sessions.

## Architecture

Three layers:
1. **sources/** — immutable raw material (articles, notes). Never modified.
2. **sessions/** — cc session exports (live while active, frozen after). Separate from sources/.
3. **wiki/** — LLM-owned compiled knowledge (summaries, concepts, entities, topics, comparisons, questions, overview).
4. **CLAUDE.md** — rules for structure, conventions, workflows.

Read `CLAUDE.md` at the start of every ingest or lint operation.

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

## Modes (8 total)

### /wiki ingest <source>
Process a source and compile it into the wiki. One source should touch 5-15 pages.

### /wiki query <question>
Search wiki, synthesize answer, offer to file back as a question page.

### /wiki recall <date_or_topic>
Load context from vault memory. Temporal queries (yesterday, last week) use native JSONL timeline. Topic queries use QMD BM25 search. Graph mode generates interactive visualization. Every recall ends with "One Thing" -- the single highest-leverage next action.

### /wiki sync
Export Claude Code sessions to Obsidian markdown. Batch export, resume, annotate, close sessions.

### /wiki edit <page>
Lightweight page modification. Read page, apply change, update frontmatter timestamps, done.

### /wiki merge <page1> <page2>
Consolidate overlapping pages. Combine content, redirect links, update index.

### /wiki lint
Health-check: orphans, broken links, stale pages, missing summaries, overlapping pages.

### /wiki status
Overview: page counts, source counts, last activity, session stats.

## Search Strategy

Use qmd strategically based on context:

| Situation | Strategy | Why |
|-----------|----------|-----|
| Quick keyword lookup | `lex` only, `rerank: false` | Instant, no model loading, zero tokens |
| Semantic meaning search | `lex` + `vec`, `rerank: false` | Good recall, ~3s with GPU |
| Best quality (GPU available) | `lex` + `vec`, `rerank: true` | Full hybrid, ~5s with GPU |
| CPU-only environment | `lex` only, `rerank: false` | vec/rerank too slow without GPU |
| Finding related pages for ingest | `lex` + `vec` across wiki collection | Need broad coverage |
| Verifying contradiction | `lex` exact phrase search | Precise matching |
| Recall topic search | BM25 `lex` across all collections | 53x faster than hybrid |

Always specify `collections: ["wiki"]` for wiki queries, `collections: ["sources"]` for source lookups, `collections: ["sessions"]` for recall.

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

See `workflows/wiki.md` for detailed step-by-step routing across all 8 modes.

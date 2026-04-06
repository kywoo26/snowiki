---
name: wiki
description: "Snowiki — LLM-maintained wiki that compounds knowledge like a snowball. Ingest sources into structured, interlinked wiki pages. Query compiled knowledge with strategic search. Lint for health. Every source touches 5-15 pages. Use when user says: wiki ingest, wiki query, wiki lint, wiki status, add to wiki, file this, search wiki, what do I know about."
argument-hint: [ingest SOURCE|query QUESTION|lint|status]
allowed-tools: Bash(python3:*), Bash(qmd:*), Read, Write, Edit, Glob, Grep, WebFetch, mcp__plugin_qmd_qmd__query, mcp__plugin_qmd_qmd__get
---

# Snowiki — LLM Wiki Skill

A persistent wiki that compounds knowledge like a snowball. Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Core Loop

```
Source in → LLM compiles → Wiki grows → Query draws from wiki → Good answers filed back → Snowball
```

**Human** curates sources, asks questions, thinks.
**LLM** summarizes, cross-references, files, maintains consistency — the bookkeeping humans abandon.

## Architecture

Three layers:
1. **sources/** — immutable raw material (articles, sessions, notes). Never modified.
2. **wiki/** — LLM-owned compiled knowledge (summaries, concepts, entities, topics, comparisons, questions, overview).
3. **SCHEMA.md** — rules for structure, conventions, workflows.

Read `SCHEMA.md` at the start of every ingest or lint operation.

## Page Types

| Type | Directory | Purpose | Example |
|------|-----------|---------|---------|
| summary | `wiki/summaries/` | 1:1 with source. The compilation step. | `karpathy-llm-wiki.md` |
| concept | `wiki/concepts/` | Single idea. "What is X?" | `rag.md`, `bm25.md` |
| entity | `wiki/entities/` | Person, tool, org, project. | `qmd.md`, `karpathy.md` |
| topic | `wiki/topics/` | Cross-cutting theme. | `korean-nlp.md` |
| comparison | `wiki/comparisons/` | Side-by-side with table. | `rag-vs-wiki.md` |
| question | `wiki/questions/` | Filed query answer. | `2026-04-07-why-wiki-beats-rag.md` |
| overview | `wiki/overview.md` | Evolving synthesis. Singleton. | — |

## Modes

### /wiki ingest <source>
Process a source and compile it into the wiki. One source should touch 5-15 pages.

### /wiki query <question>
Search wiki → synthesize answer → offer to file back as a question page.

### /wiki lint
Health-check: orphans, broken links, stale pages, missing summaries.

### /wiki status
Overview: page counts, source counts, last activity.

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

Always specify `collections: ["wiki"]` for wiki queries, `collections: ["sources"]` for source lookups.

## Obsidian Graph Integration

All cross-references use `[[wikilinks]]` for Obsidian graph connectivity:
- Every page has `related:` array in frontmatter → rendered as backlinks
- Inline `[[wiki/concepts/bm25]]` links within body text
- Entity pages become hub nodes (many inbound links)
- Topic pages bridge concept clusters
- The graph should show natural knowledge clusters, not a flat list

## Workflow

See `workflows/wiki.md` for detailed step-by-step routing.

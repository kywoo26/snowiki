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

```bash
# 1. Copy vault template
cp -r vault-template/ ~/vault/
# (or merge CLAUDE.md + directories into existing vault)

# 2. Install the wiki skill
mkdir -p ~/.claude/skills
cp -r skill/ ~/.claude/skills/wiki/

# 3. Set up qmd for search
bun install -g @tobilu/qmd
qmd collection add ~/vault/wiki --name wiki
qmd collection add ~/vault/sources --name sources
qmd collection add ~/vault/sessions --name sessions
qmd update && qmd embed

# 4. Start using
/wiki ingest https://example.com/article
/wiki query "What do I know about X?"
/wiki recall yesterday
/wiki lint
```

## Unified Skill — 8 Modes

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

## Search Strategy (qmd)

| Need | Strategy |
|------|----------|
| Quick lookup | `lex` only, `rerank: false` — instant |
| Broad search | `lex` + `vec`, `rerank: false` — ~3s (GPU) |
| Best quality | `lex` + `vec`, `rerank: true` — ~5s (GPU) |
| CPU-only | `lex` only — vec/rerank too slow |

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
4. **Search-strategic** — context-aware qmd usage (lex for speed, vec for depth)
5. **Progressive growth** — start simple, structure emerges from content
6. **Human insight preserved** — `[!insight]` callouts never modified by LLM

## Related

- [qmd-system](https://github.com/kywoo26/qmd-system) — infrastructure setup (qmd + Claude Code + Obsidian)
- [qmd](https://github.com/tobi/qmd) — local markdown search engine

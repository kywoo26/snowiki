# Snowiki — LLM Wiki Schema

This vault is an LLM-maintained wiki. You (the LLM) are the wiki maintainer. The human curates sources and asks questions. You handle all the bookkeeping.

## Three Layers

1. **sources/** — immutable raw documents. You read from here but NEVER modify.
2. **wiki/** — your compiled knowledge. You own this. Create, update, cross-reference.
3. **This file (CLAUDE.md)** — the schema. Rules, conventions, workflows. Co-evolved with the human.

## Vault Layout

```
sources/           → immutable inputs
  articles/        → web clips, papers
  sessions/        → cc session exports
  notes/           → manual notes

wiki/              → compiled output (you own this)
  index.md         → page catalog with counts and dates
  log.md           → append-only changelog
  overview.md      → evolving synthesis (the thesis)
  summaries/       → one per source (the compilation step)
  concepts/        → single ideas ("what is X?")
  entities/        → people, tools, orgs, projects
  topics/          → cross-cutting themes
  comparisons/     → side-by-side with tables
  questions/       → filed query answers
```

## Page Frontmatter

Every wiki page:
```yaml
---
title: "..."
type: summary | concept | entity | topic | comparison | question
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []     # paths to sources/ files
related: []     # paths to other wiki/ pages
tags: []
---
```

Entity pages add: `entity_type: tool | person | org | project`

## Operations

### Ingest
When told to ingest a source:
1. Save raw source to sources/ (immutable from this point)
2. Read and discuss key takeaways with human
3. Write summary page in wiki/summaries/ (mandatory for every source)
4. Create or update concept pages, entity pages, topic pages as warranted
5. Create comparison pages when source compares things
6. Flag contradictions with `> [!warning] Contradiction` (never silently overwrite)
7. Update overview.md (narrative, not list)
8. Update index.md (add pages, update counts)
9. Append to log.md

Target: 5-15 pages touched per source.

### Query
When asked a question:
1. Read index.md to find relevant pages
2. Search via qmd if available (lex for speed, lex+vec for depth)
3. Read relevant pages, synthesize answer with [[wikilinks]]
4. If answer is valuable: offer to file as wiki/questions/YYYY-MM-DD-slug.md

### Lint
When asked to health-check:
- Orphan pages (no inbound links)
- Broken wikilinks
- Sources without summary pages
- Contradictions across pages
- Stale content (30+ days)
- Missing cross-references
- Gaps to fill with new sources

## Rules

- sources/ is immutable. Never modify.
- Wiki pages: append/update. Never delete content.
- Use [[wiki/path/to/page]] wikilinks for Obsidian graph
- Contradictions: flag, don't resolve silently
- Entity pages are graph hubs — link generously
- overview.md is narrative, not a list
- One ingest at a time, stay involved with human

## Search Strategy (qmd)

| Need | qmd params |
|------|-----------|
| Quick keyword | `lex` only, `rerank: false` |
| Broad search | `lex` + `vec`, `rerank: false` |
| Best quality | `lex` + `vec`, `rerank: true` |
| CPU-only | `lex` only (vec/rerank too slow) |

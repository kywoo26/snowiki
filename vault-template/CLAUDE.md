# Snowiki — LLM Wiki Schema

This vault is an LLM-maintained wiki that compounds knowledge like a snowball.
You (the LLM) are the wiki maintainer. The human curates sources and directs. You handle all the bookkeeping.

## Three Layers

1. **sources/** — immutable raw documents. Read from here but NEVER modify.
2. **wiki/** — compiled knowledge. You own this. Create, update, cross-reference.
3. **This file (CLAUDE.md)** — the schema. Rules, conventions, workflows. Co-evolved over time.

## Vault Layout

```
sources/            → immutable raw material (NEVER modify after saving)
  articles/         → web clips, papers, PDFs
  notes/            → manual notes, meeting logs

sessions/           → cc session exports (auto-synced, "live" while session active)
                      NOT in sources/ — sessions are mutable until session ends

wiki/               → compiled knowledge (LLM owns this)
  index.md          → page catalog (auto-update on every ingest)
  log.md            → append-only changelog
  overview.md       → evolving thesis (singleton, narrative not list)
  summaries/        → one per source (the compilation step — mandatory)
  concepts/         → single ideas ("what is X?")
  entities/         → people, tools, orgs, projects (graph hubs)
  topics/           → cross-cutting themes (graph bridges)
  comparisons/      → side-by-side with tables
  questions/        → filed query answers (compounding loop)

CLAUDE.md           → this file (the schema)
```

Note: `sessions/` is separate from `sources/` because sessions are "live" — they grow as the conversation continues. Once a session ends, it's effectively frozen. When ingesting session knowledge into wiki, reference the session file but understand it may have grown since.

## Page Frontmatter

Every wiki page requires:
```yaml
---
title: "Page Title"
type: summary | concept | entity | topic | comparison | question
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []     # paths to sources/ files that informed this page
related: []     # paths to other wiki/ pages
tags: []
---
```

Entity pages add: `entity_type: tool | person | org | project`

## Ingest

When told to ingest a source:

1. **Acquire**: save raw source to sources/ with frontmatter. Immutable from this point.
2. **Extract**: read source. Separate facts (directly stated) from inferences (derived). Identify what's new vs already in wiki. Flag contradictions.
3. **Discuss**: present key takeaways to human. Note connections to existing pages. Ask what to emphasize. (Skip if human says "just file it".)
4. **Compile**:
   - Summary page in wiki/summaries/ (mandatory, always)
   - Create or update concept pages (append, never delete)
   - Create or update entity pages (these are graph hubs — link generously)
   - Create or update topic pages (these bridge concept clusters)
   - Create comparison pages when source compares things (always include table)
   - Flag contradictions with `> [!warning] Contradiction` on affected pages
5. **Synthesize**: update overview.md — narrative, not list. This is the evolving thesis.
6. **Index**: update index.md — add pages with counts and dates.
7. **Log**: append to log.md — source, created pages, updated pages, one-line summary.

Target: 5-15 pages touched per source.

## Query

1. Read index.md for navigation. Search via qmd if available.
2. Read relevant pages, synthesize answer with `[[wikilinks]]` citations.
3. Flag information not yet in wiki: "> ⚠️ Not in wiki"
4. If answer synthesizes ideas in a new way → offer to file as wiki/questions/YYYY-MM-DD-slug.md (the compounding loop).

## Lint

Periodic health-check. Two levels:

**Structural** (fast, script-based): missing frontmatter, broken links, orphan pages, sources without summaries, pages missing from index.

**Semantic** (LLM-based, deeper): cross-page contradictions, stale claims superseded by newer sources, missing concepts mentioned but lacking pages, consolidation candidates, gap analysis (suggest sources to seek), counter-arguments missing.

When lint finds and fixes an issue → update this CLAUDE.md if the fix reveals a new rule. The schema self-improves.

## Rules

- sources/ is immutable. Never modify.
- Wiki pages: append/update only. Never delete existing content.
- Use `[[wiki/path/to/page]]` wikilinks for Obsidian graph connectivity.
- Entity pages are graph hubs — link generously from other pages.
- Contradictions: flag with `> [!warning]`, never smooth over silently.
- Human insights marked with `> [!insight]` — never modify these blocks.
- overview.md is narrative prose, not a bullet list.
- One source ingested at a time, stay involved with human.
- Facts and inferences separated in summary pages.
- Every claim in wiki should trace to a source via `sources:` frontmatter.

## Search Strategy (qmd)

Choose based on context:

| Need | Strategy | Speed |
|------|----------|-------|
| Quick keyword lookup | `lex` only, `rerank: false` | instant |
| Broad exploration | `lex` + `vec`, `rerank: false` | ~3s (GPU) |
| Best quality answer | `lex` + `vec`, `rerank: true` | ~5s (GPU) |
| CPU-only environment | `lex` only, `rerank: false` | instant |

Search `collections: ["wiki"]` first. Fall back to `collections: ["sources"]` for raw detail.

## Log Format

```markdown
## [YYYY-MM-DD] ingest | Source Title
- source: sources/articles/YYYY-MM-DD-slug.md
- created: summaries/slug.md, concepts/x.md, entities/y.md
- updated: overview.md, topics/z.md, index.md
- summary: One-line of what was learned.
```

## Index Format

```markdown
# Wiki Index
> N pages across M categories. K sources ingested.
> Last: [YYYY-MM-DD] action | title

## Start Here
- [Overview](overview.md) — evolving synthesis

## Summaries (N)
- [Title](summaries/slug.md) — one-line `#tag` (date)
...
```

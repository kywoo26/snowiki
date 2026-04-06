# snowiki ❄️

A personal wiki that compounds knowledge like a snowball.

Inspired by [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Instead of re-deriving knowledge on every query (RAG), the LLM incrementally builds and maintains a persistent, interlinked wiki. Knowledge compounds.

## Three Layers

```
sources/        → immutable raw documents (articles, sessions, notes)
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

# 3. Start using
/wiki ingest https://example.com/article
/wiki query "What do I know about X?"
/wiki lint
/wiki status
```

## How Ingest Works

```
You drop a source
    ↓
LLM reads it, discusses key takeaways
    ↓
Creates summary page (wiki/summaries/)
Updates concept pages, entity pages, topic pages
Flags contradictions, adds cross-references
Updates overview.md (the evolving thesis)
Updates index.md, appends to log.md
    ↓
5-15 pages touched per source
    ↓
Snowball grows
```

## Search Strategy (with qmd)

| Need | Strategy |
|------|----------|
| Quick lookup | `lex` only, `rerank: false` — instant |
| Broad search | `lex` + `vec`, `rerank: false` — ~3s (GPU) |
| Best quality | `lex` + `vec`, `rerank: true` — ~5s (GPU) |
| CPU-only | `lex` only — vec/rerank too slow |

## Obsidian Integration

- All cross-references use `[[wikilinks]]` for graph connectivity
- Entity pages become hub nodes with many inbound links
- Topic pages bridge concept clusters
- overview.md is the central synthesis node
- Graph view reveals knowledge structure

## Related

- [Karpathy's LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [qmd-system](https://github.com/kywoo26/qmd-system) — infrastructure (qmd + Claude Code + Obsidian setup)
- [qmd](https://github.com/tobi/qmd) — local markdown search engine

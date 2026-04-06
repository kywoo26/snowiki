# snowiki ❄️

A personal wiki that compounds knowledge like a snowball.

Inspired by [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — instead of re-deriving knowledge on every query (RAG), the LLM incrementally builds and maintains a persistent, interlinked wiki. Every source makes it richer. Knowledge compounds.

## How It Works

```
You drop a source → LLM reads, extracts, integrates → Wiki grows
You ask a question → LLM searches wiki, synthesizes → Answer filed back
You run lint → Orphans, contradictions, stale pages caught → Wiki stays healthy
```

**You** curate sources, ask questions, direct analysis, think.
**LLM** summarizes, cross-references, files, maintains consistency — all the bookkeeping humans abandon.

## Architecture

```
vault/
├── sources/           ← Immutable raw material (never modified)
│   ├── articles/      ← Web clippings, PDFs
│   ├── sessions/      ← Claude Code session exports
│   └── notes/         ← Manual notes, meeting logs
│
├── wiki/              ← LLM-owned compiled knowledge
│   ├── index.md       ← Auto-maintained catalog
│   ├── log.md         ← Append-only timeline
│   ├── concepts/      ← Single-concept deep pages
│   ├── topics/        ← Cross-cutting themes
│   ├── decisions/     ← "Why A over B" records
│   ├── tools/         ← Tool usage & config
│   └── setup/         ← System setup guides
│
├── SCHEMA.md          ← Rules for how the LLM maintains the wiki
└── .obsidian/         ← Obsidian config
```

## Quick Start

### 1. Install the skill

```bash
mkdir -p ~/.claude/skills
cp -r skill/ ~/.claude/skills/wiki/
```

### 2. Initialize your vault

```bash
cp -r vault-template/ ~/vault/
# Or merge into existing vault
```

### 3. Set up qmd (optional but recommended)

```bash
bun install -g @tobilu/qmd
qmd collection add ~/vault/wiki --name wiki
qmd collection add ~/vault/sources --name sources
qmd update && qmd embed
```

### 4. Use it

```
/wiki ingest https://example.com/article    # Ingest a URL
/wiki ingest path/to/file.md                # Ingest a file
/wiki query "How does BM25 handle Korean?"  # Query the wiki
/wiki lint                                   # Health check
/wiki status                                 # Overview
```

## The `/wiki` Skill

| Command | What it does |
|---------|-------------|
| `/wiki ingest <source>` | Read source → discuss with user → update wiki pages → update index → log |
| `/wiki query <question>` | Search wiki via qmd → synthesize answer → optionally file back |
| `/wiki lint` | Check: orphans, broken links, missing frontmatter, contradictions, stale pages |
| `/wiki status` | Page counts, source counts, last activity, qmd state |

## Lint Codes

| Code | Severity | Check |
|------|----------|-------|
| S001 | WARN | Orphan pages (no inbound links) |
| S002 | INFO | Sources not referenced by any wiki page |
| S003 | ERROR | Incomplete frontmatter |
| S004 | ERROR | Broken wikilinks |
| S005 | WARN | Excessive contradiction markers (3+) |
| S006 | INFO | Stale pages (30+ days without update) |

## Stack

- **Obsidian** — visual interface, graph view
- **qmd** — local markdown search (BM25 + vector + LLM reranking)
- **Claude Code** — the LLM agent that maintains the wiki
- **SCHEMA.md** — the rulebook, co-evolved by human and LLM

## Philosophy

> "The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping."
> — Andrej Karpathy

The wiki is a **persistent, compounding artifact**. Not chat history. Not a pile of raw documents. A living knowledge base where cross-references are already there, contradictions are already flagged, and the synthesis already reflects everything you've read.

## Related

- [Karpathy's LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [qmd](https://github.com/tobi/qmd) — local markdown search engine
- [qmd-system](https://github.com/kywoo26/qmd-system) — infrastructure setup (qmd + cc + Obsidian)

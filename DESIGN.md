# Snowiki Design Document

Comprehensive design synthesized from:
- Karpathy's LLM Wiki gist + 217 community comments
- seCall (hang-in/seCall) — 2-layer vault, lint, Korean NLP, meta-agent
- atomic (kenforthewin/atomic) — semantic connections, 765 stars
- Farzapedia — 2500 sources → 400 pages, production proof
- Palinode, Freelance, sage-wiki — provenance, typed entities, self-learning
- HN thread #47640875 — error accumulation debate, scaling strategies
- Our qmd-system experience — search strategies, GPU/CPU, hooks, session sync

## Core Insight

> "The tedious part is not the reading or the thinking — it's the bookkeeping."
> — Karpathy

But the community adds crucial nuance:

> "Epistemic integrity, not organization, is the real product problem."
> — laphilosophia (gist comment)

> "When an LLM writes my summaries, I get a well-organized information store. What I don't get is the understanding."
> — pssah4 (gist comment)

Snowiki must balance: LLM handles bookkeeping, but human insight is preserved and elevated.

## Design Principles

### 1. Compilation, Not Storage
Raw sources are compiled into wiki pages — like source code → binary. The compilation step (ingest) creates value by extracting, structuring, cross-referencing, and flagging contradictions.

### 2. Epistemic Integrity
Every claim traces to a source. Contradictions are flagged, not smoothed over. Facts and inferences are separated. The wiki is a derived artifact — sources/ is truth.

Inspired by: laphilosophia's 5 constraints, Palinode's git-blame-per-fact, Freelance's content-hash provenance.

### 3. Progressive Snowball
Start simple. Grow organically. Every source, every query, every lint pass makes the wiki richer. No need for perfect structure on day one.

### 4. Graph-First (Obsidian)
Every design decision considers "how does this look in the graph?" Entity pages are hubs. Topic pages bridge clusters. Overview.md is the central node. [[wikilinks]] everywhere.

### 5. Search-Strategic (qmd)
Not just "search the wiki" but context-aware strategy:
- lex-only when speed matters (instant, zero tokens)
- lex+vec when depth matters (~3s GPU)
- CPU fallback is always lex-only
- Token budget awareness: retrieve snippets, not full pages, unless needed

### 6. Session-to-Wiki Pipeline
Daily cc work → auto-sync to sources/sessions/ → user triggers `/wiki ingest` → session knowledge compiled into wiki pages. The bridge between ephemeral work and permanent knowledge.

### 7. Dual-Mode Compilation (from seCall)
- **Batch**: Full wiki generation/major restructure. Weekly or on-demand. Higher quality.
- **Incremental**: Per-source update. Fast, add-only. After each ingest.

### 8. Human Insight Layer
LLM handles bookkeeping. But human insights get special treatment:
- `> [!insight]` callout for human-originated ideas
- LLM never modifies these blocks
- In graph: human insights are first-class nodes

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  ~/vault/                                           │
│                                                     │
│  CLAUDE.md ← schema (rules, conventions, workflows) │
│                                                     │
│  sources/ ← immutable raw material                  │
│  ├── articles/    (web clips, papers)               │
│  ├── sessions/    (cc session exports, auto-synced)  │
│  └── notes/       (manual notes, voice memos)       │
│                                                     │
│  wiki/ ← LLM-owned compiled knowledge               │
│  ├── index.md     (catalog, auto-generated)         │
│  ├── log.md       (append-only changelog)           │
│  ├── overview.md  (evolving thesis, singleton)      │
│  ├── summaries/   (1:1 with sources)                │
│  ├── concepts/    (atomic ideas)                    │
│  ├── entities/    (people, tools, orgs — graph hubs)│
│  ├── topics/      (cross-cutting — graph bridges)   │
│  ├── comparisons/ (side-by-side with tables)        │
│  └── questions/   (filed query answers)             │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
     ┌─────▼─────┐            ┌──────▼──────┐
     │   qmd     │            │  Obsidian   │
     │           │            │             │
     │ wiki    collection     │ Graph view  │
     │ sources collection     │ Backlinks   │
     │                        │ Dataview    │
     │ Strategy:              │             │
     │  lex → instant         │             │
     │  lex+vec → 3s (GPU)    │             │
     │  lex+vec+rerank → 5s   │             │
     └─────▲─────┘            └─────────────┘
           │
  ┌────────┴──────────────────────────────────┐
  │  Claude Code                               │
  │                                            │
  │  Skills:                                   │
  │  ├── /wiki ingest   → compile source       │
  │  ├── /wiki query    → search + synthesize  │
  │  ├── /wiki lint     → structural+semantic  │
  │  └── /wiki status   → dashboard            │
  │                                            │
  │  Hooks:                                    │
  │  ├── Stop → sync session to sources/       │
  │  └── (on-demand) → incremental compile     │
  │                                            │
  │  Scripts:                                  │
  │  ├── lint.py     → structural checks       │
  │  ├── status.py   → vault overview          │
  │  └── index-gen.py→ auto-generate index.md  │
  └────────────────────────────────────────────┘
```

## Ingest Workflow (detailed)

The ingest is where all the magic happens. One source → 5-15 pages.

### Phase 1: Acquire
- Save raw source to sources/ with frontmatter
- Source is immutable from this point

### Phase 2: Extract (not "summarize")
Following laphilosophia's constraint: separate facts from inferences.

```markdown
## Facts (directly stated in source)
- BM25 uses term frequency and inverse document frequency
- qmd supports hybrid BM25 + vector search

## Inferences (derived from source)
- Hybrid search is likely better for multilingual content

## New vs Known
- New: qmd has LLM re-ranking on top of hybrid search
- Already in wiki: BM25 concept ([[wiki/concepts/bm25]])

## Contradictions
- Source says "embedding dimension is 768" but [[wiki/entities/qmd]] says "1024 with Qwen3"
```

### Phase 3: Discuss
Present extraction to user. Ask what to emphasize. User may add `[!insight]` blocks.

### Phase 4: Compile
- **Summary page** (mandatory): facts + inferences + contradictions
- **Concept pages**: create or append. Link with [[wikilinks]]
- **Entity pages**: create or append. These are graph hubs — link generously
- **Topic pages**: update if source touches cross-cutting theme
- **Comparison pages**: when source compares things (always include table)
- **Contradiction callouts**: on affected pages with both claims and sources

### Phase 5: Bookkeeping
- Update overview.md (narrative, not list)
- Update index.md (auto-generate from frontmatter)
- Append to log.md
- qmd update && qmd embed

### Phase 6: Verify
- Quick lint (structural only) on touched pages
- Confirm no broken links created

## Query Workflow (the compounding loop)

### Search Strategy Selection
```
if user_wants_speed or cpu_only:
    qmd lex-only, rerank: false     # instant
elif user_exploring:
    qmd lex+vec, rerank: false      # 3s GPU
elif complex_question:
    qmd lex+vec, rerank: true       # 5s GPU
```

### The Filing Step (critical for compounding)
After answering, assess:
- Is this synthesis new? (not just repeating one page)
- Would finding this again be valuable?
- Did it connect ideas that weren't explicitly linked?

If yes → create questions/ page → the snowball grows from queries too.

## Lint Workflow (structural + semantic)

### Structural (lint.py, fast, no LLM)
| Code | Check |
|------|-------|
| L001 | Missing/incomplete frontmatter |
| L002 | Broken links (wikilinks + markdown links) |
| L003 | Orphan pages (no inbound links) |
| L004 | Source without summary page |
| L005 | Page missing from index.md |
| L006 | related: references nonexistent page |

### Semantic (LLM-based, slower, deeper)
| Check | Method |
|-------|--------|
| Cross-page contradictions | Read pages with overlapping tags, compare claims |
| Stale content | Compare page dates with source dates |
| Missing concepts | Grep for terms mentioned 3+ times without own page |
| Consolidation candidates | Find pages with >70% topic overlap |
| Gap analysis | What's mentioned but never sourced? |
| Counter-arguments | Does any concept page lack opposing views? (from localwolfpackai) |

### The Self-Learning Loop (from sage-wiki)
When lint finds and fixes an issue:
1. The correction is stored (log.md)
2. Next ingest, the same pattern is checked
3. CLAUDE.md is updated with the new rule
4. Schema co-evolves from corrections

## Hooks & Automation

### Current
```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "session sync", "timeout": 10}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "session sync", "timeout": 10}]}]
  }
}
```

### Future (when wiki is mature)
- **Stop**: sync session + trigger incremental compile if session was substantive
- The compile decision: only if session had >10 user messages and touched files (not just chat)

## Scripts

### lint.py
Structural checks. Fast. No LLM needed.
- Fix: proper YAML parsing (not naive string split)
- Fix: case-insensitive wikilink matching
- Fix: relative path resolution from page directory
- Add: L004 (source without summary), L005 (missing from index), L006 (broken related:)

### status.py
Vault overview dashboard.
- Fix: robust qmd status parsing
- Add: page count by type from frontmatter
- Add: health summary (last lint result)

### index-gen.py (NEW)
Auto-generate index.md from frontmatter.
- Scan all wiki/*.md pages
- Read frontmatter (title, type, tags, sources, updated)
- Group by type
- Output formatted index with counts, dates, source counts
- Prevents index drift from reality

### compile.py (NEW)
Compilation prompt generator.
- Input: source file path + mode (batch|incremental)
- Output: prompt for Claude Code
- Batch: full wiki analysis
- Incremental: single source → pages

## What Makes Snowiki Unique

| Feature | Source of Inspiration | Our Implementation |
|---------|----------------------|-------------------|
| qmd strategic search | Our benchmarks (lex: instant, vec: 3s, query: 5s) | Context-aware strategy selection in CLAUDE.md |
| Session-to-wiki pipeline | seCall hooks + our sync skill | auto-sync → sources/ → user-triggered ingest |
| Obsidian graph-first | Karpathy ("graph view is the best way to see shape") | Entity=hub, Topic=bridge, wikilinks everywhere |
| Epistemic integrity | laphilosophia, Palinode, Freelance | facts/inferences separated, source links required |
| Dual environment (GPU/CPU) | Our CUDA benchmarks | Search strategy adapts to hardware |
| Human insight preservation | pssah4, arturseo-geo | `[!insight]` callouts, LLM never modifies |
| Self-learning schema | sage-wiki (xoai) | Lint corrections → CLAUDE.md updates |
| Contradiction tracking | frosk1, localwolfpackai | Flag, don't smooth. Counter-arguments section. |
| Progressive growth | Karpathy ("intentionally abstract") | Start simple, structure emerges from content |

## Migration from Current State

Current wiki pages (tools/fzf.md, wsl/setup.md, etc.) become:
- `wiki/entities/fzf.md` (entity_type: tool)
- `wiki/topics/wsl2-dev-environment.md` (topic merging wsl/setup + claude/setup)
- `wiki/entities/qmd.md` (entity, consolidating qmd-reference + architecture)

But: don't restructure now. Let future ingests create the proper pages. Old pages stay until naturally superseded. No big-bang migration.

## What NOT to Build

- Custom UI (Obsidian is the UI)
- Custom vector DB (qmd handles this)
- Custom embedding pipeline (qmd handles this)
- Custom git sync (plain git is enough)
- Custom graph visualization (Obsidian graph view)
- Automatic compilation without user involvement (user stays in the loop per Karpathy)

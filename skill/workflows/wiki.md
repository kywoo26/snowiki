# Snowiki Workflow

## Step 0: Bootstrap

On first use or when entering a new vault:
1. Read `SCHEMA.md` — understand structure and rules
2. Check if `wiki/overview.md`, `wiki/index.md`, `wiki/log.md` exist — create if missing
3. Verify directories: `wiki/{summaries,concepts,entities,topics,comparisons,questions}`, `sources/{articles,sessions,notes}`

## Step 1: Classify Command

Parse input after `/wiki`:

| Input | Route |
|-------|-------|
| `ingest <URL/path/text>` | Step 2 |
| `query <question>` | Step 3 |
| `lint` | Step 4 |
| `status` | Step 5 |

## Step 2: Ingest

One source → 5-15 wiki pages touched. This is the core compilation step.

### 2.1: Acquire Source

| Input | Action |
|-------|--------|
| URL | WebFetch → save to `sources/articles/YYYY-MM-DD-slug.md` |
| File path | Read file. If not in sources/, copy it there |
| Inline text | Save to `sources/notes/YYYY-MM-DD-slug.md` |
| "yesterday's session about X" | Use recall or ls sources/sessions/ to find, confirm with user |

Add frontmatter to source:
```yaml
---
type: source
source_type: article | session | note
title: "Source Title"
url: "https://..." # if applicable
ingested: YYYY-MM-DD
---
```

Source is now immutable. Never modify it again.

### 2.2: Discuss

Read the source. Present to user:
- 3-5 key takeaways
- Connections to existing wiki pages (search via qmd `lex`)
- New concepts/entities that warrant pages
- Potential contradictions with existing knowledge

If user says "just file it" — skip to 2.3 with reasonable defaults.

### 2.3: Compile (the core step)

Read SCHEMA.md for rules. Then:

**A. Create summary page** (mandatory, always):
- `wiki/summaries/<slug>.md`
- Key Claims, Notable Details, Open Questions
- Link to all concept/entity pages this source informed

**B. Create or update concept pages**:
- For each significant concept: check if `wiki/concepts/<name>.md` exists
  - Exists → append new information. Never delete existing content.
  - New → create with Definition, How It Works, Strengths, Limitations
- Use `[[wiki/concepts/<name>]]` wikilinks in body text

**C. Create or update entity pages**:
- For people, tools, orgs, projects mentioned substantively
- `wiki/entities/<name>.md` with `entity_type: tool | person | org | project`
- Entity pages become graph hubs — link generously

**D. Create or update topic pages**:
- If source contributes to a cross-cutting theme
- `wiki/topics/<theme>.md` — links to relevant concepts and entities

**E. Create comparison pages** (when applicable):
- If source explicitly compares things, or new info makes comparison useful
- `wiki/comparisons/<a>-vs-<b>.md` — always include a markdown table

**F. Flag contradictions**:
- If new info contradicts existing wiki content:
  ```markdown
  > [!warning] Contradiction
  > This page says X (from source A), but [[wiki/concepts/Y]] says Z (from source B).
  > Needs resolution.
  ```
- Never silently overwrite — always flag.

**G. Update overview.md**:
- Add or revise the relevant section
- Should read as coherent narrative, not a list
- This is the "evolving thesis"

**H. Update index.md**:
- Add new pages to correct category
- Include counts, dates, source counts
- Maintain "Start Here → overview.md"

**I. Append to log.md**:
```markdown
## [YYYY-MM-DD] ingest | Source Title
- source: sources/articles/YYYY-MM-DD-slug.md
- created: summaries/slug.md, concepts/x.md, entities/y.md
- updated: overview.md, topics/z.md, index.md
- summary: One-line of what was learned.
```

### 2.4: Report

```
✅ Ingested: "Source Title"
   Created: 4 pages (summaries/slug.md, concepts/x.md, entities/y.md, comparisons/a-vs-b.md)
   Updated: 3 pages (overview.md, topics/z.md, index.md)
   Total pages touched: 7
```

### 2.5: Post-ingest

Run `qmd update && qmd embed` to index new/updated pages for future queries.

## Step 3: Query

Search the wiki, synthesize an answer. Good answers compound back into the wiki.

### 3.1: Search Strategy

Choose strategy based on context:

**Quick lookup** (user knows the term):
```
qmd query: [{type: "lex", query: "exact term"}], rerank: false
```

**Broad search** (user exploring):
```
qmd query: [{type: "lex", query: "keywords"}, {type: "vec", query: "natural language question"}], rerank: false
```

**Deep search** (complex question, GPU available):
```
qmd query: [{type: "lex", query: "keywords"}, {type: "vec", query: "question"}], rerank: true
```

Always search `collections: ["wiki"]` first. Fall back to `collections: ["sources"]` for raw detail.

If qmd unavailable: read `wiki/index.md`, identify relevant pages by scanning, read them directly.

### 3.2: Synthesize

- Read top 3-5 matching pages in full via `qmd get`
- Generate answer with inline `[[wikilinks]]`
- Flag gaps: "> ⚠️ Not in wiki — consider ingesting a source about X"

### 3.3: File Back (the compounding step)

After answering, assess:
- Is this answer valuable beyond this conversation?
- Does it synthesize multiple pages in a new way?
- Would it be useful to find again?

If yes: "This answer could become `wiki/questions/YYYY-MM-DD-slug.md`. File it?"

On approval:
1. Create question page with frontmatter (sources consulted, related pages)
2. Update related pages' `related:` arrays
3. Update index.md under Questions
4. Append to log.md
5. Run qmd update

## Step 4: Lint

Health-check per SCHEMA.md rules.

### 4.1: Structural Checks (script-based)

Run `python3 ~/.claude/skills/wiki/scripts/lint.py --vault $VAULT_DIR`

Catches: L001-L009 (missing frontmatter, broken links, orphans, missing summaries, stale pages).

### 4.2: Semantic Checks (LLM-based)

After structural lint, the LLM reads flagged pages and checks:
- Cross-page contradictions (claims that conflict between pages)
- Overlapping pages that should be merged
- Concepts mentioned but lacking their own page
- Stale claims superseded by newer sources
- Missing connections that should be linked

### 4.3: Gap Analysis

Suggest new sources to seek:
- "No wiki pages about X, but it's mentioned in 3 places — consider ingesting a source"
- "Topic Y has only 1 source — more depth needed"

### 4.4: Report and Fix

Present findings. For auto-fixable issues (missing from index, stale overview), offer to fix.
For semantic issues, present the contradiction and let user decide.

Append to log.md:
```markdown
## [YYYY-MM-DD] lint | Health check
- errors: N, warnings: N
- actions: description of fixes applied
```

## Step 5: Status

Quick overview. Run `python3 ~/.claude/skills/wiki/scripts/status.py --vault $VAULT_DIR`

Or manually:
```
📊 Snowiki Status

Pages:     42 (summaries: 12, concepts: 8, entities: 10, topics: 5, comparisons: 3, questions: 4)
Sources:   28 (articles: 12, sessions: 14, notes: 2)
Overview:  Last updated 2026-04-07
Last:      [2026-04-07] ingest | Karpathy LLM Wiki
Health:    0 errors, 2 warnings
qmd:       42 docs indexed, 28 embedded, GPU: cuda
```

## Notes

- One source at a time for ingest (quality > speed)
- Always discuss before writing (unless user says "just file it")
- sources/ is immutable — never modify
- Wiki pages: append/update only — never delete content
- Contradictions: flag, don't resolve silently
- Good query answers → file back → snowball compounds
- Use `[[wikilinks]]` everywhere for Obsidian graph connectivity
- Entity pages are graph hubs — they should have many inbound links
- The overview.md is the thesis — keep it narrative, not a list

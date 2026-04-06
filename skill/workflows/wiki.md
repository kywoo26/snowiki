# Snowiki Workflow

## Step 1: Classify Command

Parse input after `/wiki`:

- **ingest** → Step 2A
- **query** → Step 2B
- **lint** → Step 2C
- **status** → Step 2D

## Step 2A: Ingest

Read a source and integrate it into the wiki.

### 2A.1: Acquire Source

| Input | Action |
|-------|--------|
| URL | WebFetch content. Save to `sources/articles/YYYY-MM-DD-title.md` |
| File path | Read file. If already in sources/, use as-is |
| Inline text | Save to `sources/notes/YYYY-MM-DD-topic.md` |
| Session ref | Reference existing `sources/sessions/*.md` |

Source file frontmatter:
```yaml
---
type: source
source_type: article | session | note
title: "Source Title"
url: "https://..."
ingested: 2026-04-07
---
```

### 2A.2: Discuss with User

Present key takeaways from the source:
- "3 key points from this source: ..."
- "Related to existing wiki page X"
- "New concept Y — should I create a page?"

Proceed after user feedback.

### 2A.3: Update Wiki

1. **Read SCHEMA.md** — review rules
2. **Search related pages via qmd** — find connection points
3. **Create/update pages**:
   - New concept → `wiki/concepts/`
   - Related to existing → append to that page (never delete)
   - Decision recorded → `wiki/decisions/YYYY-MM-DD-topic.md`
4. **Add cross-references** — `[[wiki/concepts/topic]]` wikilinks
5. **Update index.md** — add new pages, update summaries
6. **Append to log.md** — date, source, pages created/modified

### 2A.4: Report

```
✅ Ingested: "Source Title"
   Created: concepts/bm25.md, topics/korean-search.md
   Updated: tools/qmd.md, index.md
   Log: [2026-04-07] ingest | Source Title
```

## Step 2B: Query

Search the wiki and synthesize an answer.

### 2B.1: Search

1. qmd MCP: `type:'lex'` + `type:'vec'` across wiki collection
2. Get top 3-5 relevant pages in full
3. Supplementary search in sources/ collection

### 2B.2: Synthesize

- Generate answer based on wiki pages
- Cite sources with `[[page]]` wikilinks
- Flag information not yet in wiki: "⚠️ Not in wiki"

### 2B.3: Feedback Loop

If the answer is valuable, suggest:
- "File this as wiki/topics/X.md?"
- On approval → run 2A.3~2A.4

## Step 2C: Lint

Health-check per SCHEMA.md lint rules.

### 2C.1: Checks

| Code | Severity | Check |
|------|----------|-------|
| S001 | WARN | Orphan pages (no inbound links) |
| S002 | INFO | Sources not referenced by any wiki page |
| S003 | ERROR | Incomplete frontmatter (missing required fields) |
| S004 | ERROR | Broken wikilinks |
| S005 | WARN | Excessive contradictions (3+ per page) |
| S006 | INFO | Stale pages (not updated in 30+ days) |

Run via script: `python3 ~/.claude/skills/wiki/scripts/lint.py`

### 2C.2: Report Format

```
🔍 Snowiki Lint Report

S001 ⚠️  Orphan page: no inbound links
       → wiki/concepts/orphan.md

S003 ❌  Missing frontmatter: title, type
       → wiki/tools/fzf.md

Summary: 1 error, 1 warning, 0 info
```

### 2C.3: Auto-fix Suggestions

Suggest fixes for each finding. Apply on user approval only.

## Step 2D: Status

Wiki overview at a glance.

```
📊 Snowiki Status

Pages:     42 (concepts: 15, topics: 8, decisions: 5, tools: 10, guides: 4)
Sources:   28 (articles: 12, sessions: 14, notes: 2)
Last:      [2026-04-07] ingest | CUDA Toolkit Setup
Health:    ✅ 0 errors, 2 warnings (run /wiki lint)
qmd:       12 docs indexed, last embed 2h ago
```

## Notes

- Ingest one source at a time (quality over speed)
- Always discuss with user before wiki updates (no silent writes)
- sources/ is immutable — never modify
- On contradiction: mark with `> ⚠️ Contradiction:` callout, don't delete
- Good query answers should be filed back into wiki (compound effect)

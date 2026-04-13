# Snowiki Workflow

## Important

This file is a workflow guide around the current Snowiki CLI.

The authoritative shipped runtime contract is the installed `snowiki` command, not the older qmd-centric workflow assumptions. Do not assume a qmd update/embed loop is the current shipped behavior.

Use this file to guide how an agent should orchestrate the shipped CLI, and treat any broader wiki workflow notes as deferred ideas unless the runtime explicitly exposes them.

Current shipped CLI surface:
- `snowiki ingest`
- `snowiki rebuild`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki export`
- `snowiki benchmark`
- `snowiki daemon`
- `snowiki mcp`

## Step 0: Bootstrap

On first use or when entering a new vault:
1. Read `CLAUDE.md` — understand structure and rules.
2. Verify directories: `wiki/`, `sources/`, `sessions/`.
3. Detect environment: `VAULT_DIR` and `TZ`.

## Step 1: Classify Command

Parse input after `/wiki`:

| Input | Route | Status |
|-------|-------|--------|
| `ingest <URL/path/text>` | Step 2: Ingest | Current |
| `query <question>` | Step 3: Query | Current |
| `recall <date_or_topic>` | Step 4: Recall | Current |
| `sync` | Step 5: Sync | **Deferred** |
| `edit <page>` | Step 6: Edit | **Deferred** |
| `merge <p1> <p2>` | Step 7: Merge | **Deferred** |
| `lint` | Step 8: Lint | Current |
| `status` | Step 9: Status | Current |

Implicit routing (no explicit mode keyword):
- Temporal words ("yesterday", "last week", "what was I doing") -> Step 4: Recall
- "what do I know about X" -> Step 3: Query
- "add to wiki", "file this" -> Step 2: Ingest

---

## Step 2: Ingest

One source -> 5-15 wiki pages touched. This is the core compilation step.

### 2.1: Acquire Source

| Input | Action |
|-------|--------|
| URL | WebFetch -> save to `sources/articles/YYYY-MM-DD-slug.md` |
| File path | Read file. If not in `sources/`, copy it there |
| Inline text | Save to `sources/notes/YYYY-MM-DD-slug.md` |
| "yesterday's session about X" | Use `recall` to find session |

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

Read the source and current local Snowiki outputs. Use the shipped retrieval surfaces where possible.

### 2.3: Compile (the core step)

Read `CLAUDE.md` for rules. Then:

**A. Create summary page** (mandatory, always):
- `wiki/summaries/<slug>.md`
- Key Claims, Notable Details, Open Questions.
- Link to all concept/entity pages this source informed.

**B. Create or update concept pages**:
- For each significant concept: check if `wiki/concepts/<name>.md` exists.
  - Exists -> append new information. Never delete existing content.
  - New -> create with Definition, How It Works, Strengths, Limitations.
- Use `[[wiki/concepts/<name>]]` wikilinks in body text.

**C. Create or update entity pages**:
- For people, tools, orgs, projects mentioned substantively.
- `wiki/entities/<name>.md` with `entity_type: tool | person | org | project`.

**D. Create or update topic pages**:
- If source contributes to a cross-cutting theme.
- `wiki/topics/<theme>.md` — links to relevant concepts and entities.

**E. Create comparison pages** (when applicable):
- If source explicitly compares things, or new info makes comparison useful.
- `wiki/comparisons/<a>-vs-<b>.md` — always include a markdown table.

**F. Flag contradictions**:
- If new info contradicts existing wiki content:
  ```markdown
  > [!warning] Contradiction
  > This page says X (from source A), but [[wiki/concepts/Y]] says Z (from source B).
  > Needs resolution.
  ```
- Never silently overwrite — always flag.

**G. Update overview.md**:
- Add or revise the relevant section.
- Should read as coherent narrative, not a list.

**H. Update index.md**:
- Add new pages to correct category.

**I. Append to log.md**:
```markdown
## [YYYY-MM-DD] ingest | Source Title
- source: sources/articles/YYYY-MM-DD-slug.md
- created: summaries/slug.md, concepts/x.md, entities/y.md
- updated: overview.md, topics/z.md, index.md
```

### 2.4: Report

```
Ingested: "Source Title"
   Created: 4 pages (summaries/slug.md, concepts/x.md, entities/y.md, comparisons/a-vs-b.md)
   Updated: 3 pages (overview.md, topics/z.md, index.md)
   Total pages touched: 7
```

### 2.5: Post-ingest

If the runtime later exposes additional indexing/maintenance helpers, use those.

---

## Step 3: Query

Search the wiki, synthesize an answer. Good answers compound back into the wiki.

### 3.1: Search Strategy

Use the shipped `snowiki query` runtime first.

Current truth:
- Lexical retrieval is the shipped runtime path.
- Semantic/hybrid/rerank remain deferred reference workflows.

### 3.2: Synthesize

- Read top 3-5 matching pages in full via `Read` tool
- Generate answer with inline `[[wikilinks]]`
- Flag gaps: "Not in wiki — consider ingesting a source about X"

### 3.3: File Back (Deferred Workflow)

The following compounding step is a deferred workflow idea, not a shipped runtime command.

If an answer is valuable beyond the conversation:
1. Propose creating `wiki/questions/YYYY-MM-DD-slug.md`.
2. On approval, create the page and update related arrays.
3. Update `index.md` and `log.md`.

---

## Step 4: Recall

Load context from vault memory.

### 4.1: Temporal Recall

Use the shipped `snowiki recall` command for temporal context.

### 4.2: Synthesize "One Thing"

After presenting recall results, synthesize the single highest-leverage next action.

**How to pick the One Thing:**
1. Look at what has momentum — sessions with recent activity.
2. Look at what is blocked — removing a blocker unlocks downstream work.
3. Look at what is closest to done — finishing > starting.

**Format:** Bold line at the end of results:

> **One Thing: [specific, concrete action]**

### 4.3: Topic Recall (Deferred Workflow)

Use the shipped `snowiki recall` behavior first. Broader hybrid recall and topic expansion remain deferred reference workflows.

If the runtime later exposes broader topic recall:
1. Expand query into phrasings.
2. Run variants across collections.
3. Deduplicate and present top results.

### 4.4: Graph Visualization (Deferred Workflow)

Graph-oriented recall workflows are deferred reference ideas. If the runtime later exposes graph visualization:
1. Run the `session-graph.py` script.
2. Present interactive HTML to the user.


### 4.3: Fallback — No Results

```
No results found for "QUERY". Try:
- Different search terms
- Broader keywords / different date range
```

---

## Step 5: Sync (Deferred Workflow)

Exporting Claude Code sessions to Obsidian markdown is a deferred reference workflow. If the runtime later exposes a `sync` command:
1. Detect `VAULT_DIR` and `TZ`.
2. Run the sync/export logic.
3. Preserve `## My Notes` and specific frontmatter fields.

---

## Step 6: Edit (Deferred Workflow)

Lightweight page modification is a deferred reference workflow. If the runtime later exposes an `edit` command:
1. Identify target page.
2. Read current content.
3. Apply surgical modifications via `Edit` tool.
4. Update metadata and cross-references.

---

## Step 7: Merge (Deferred Workflow)

Consolidating overlapping pages is a deferred reference workflow. If the runtime later exposes a `merge` command:
1. Identify pages to merge.
2. Analyze overlap and contradictions.
3. Combine content into a primary page.
4. Redirect links and update index.


---

## Step 8: Lint

Health-check per `CLAUDE.md` rules.

### 8.1: Structural Checks

Run `snowiki lint` for the authoritative runtime linting.

### 8.2: Semantic Checks (Informative)

The LLM may check for:
- Cross-page contradictions.
- Overlapping pages that should be merged.
- Concepts mentioned but lacking their own page.
- Stale claims superseded by newer sources.

### 8.3: Gap Analysis (Informative)

Suggest new sources to seek:
- "No wiki pages about X, but it's mentioned in 3 places — consider ingesting a source."
- "Topic Y has only 1 source — more depth needed."

### 8.4: Report and Fix

Present findings. For auto-fixable issues, offer to fix.
For semantic issues, present the contradiction and let user decide.

---

## Step 9: Status

Quick overview of the entire system.

Run `snowiki status` for the authoritative runtime status.

Informative status may include:
```
Snowiki Status

Pages:     42 (summaries: 12, concepts: 8, entities: 10, topics: 5, comparisons: 3, questions: 4)
Sources:   28 (articles: 12, sessions: 14, notes: 2)
Overview:  Last updated 2026-04-07
Health:    0 errors, 2 warnings
```

---

## Notes

- One source at a time for ingest (quality > speed)
- Always discuss before writing (unless user says "just file it")
- `sources/` is immutable — never modify
- `sessions/` are "live" while active, frozen after session ends
- Wiki pages: append/update only — never delete content
- Contradictions: flag, do not resolve silently
- Use `[[wikilinks]]` everywhere for Obsidian graph connectivity
- Entity pages are graph hubs — they should have many inbound links
- The `overview.md` is the thesis — keep it narrative, not a list
- Every claim traces to source
- For recall/sync: always resolve `VAULT_DIR` and `TZ` before running scripts
- Search strategy: lexical-first retrieval is the current runtime truth

# Snowiki Workflow

## Important

This file is a workflow guide around the current Snowiki CLI.

The authoritative shipped runtime contract is the installed `snowiki` command, not the older qmd-centric workflow assumptions.

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
1. Read `CLAUDE.md` — understand structure and rules
2. Check if `wiki/overview.md`, `wiki/index.md`, `wiki/log.md` exist — create if missing
3. Verify directories: `wiki/{summaries,concepts,entities,topics,comparisons,questions}`, `sources/{articles,notes}`, `sessions/`
4. Detect environment:
   - `VAULT_DIR`: `git rev-parse --show-toplevel 2>/dev/null || pwd`
   - `TZ`: system timezone via `date +%Z` (used for temporal recall and sync timestamps)

## Step 1: Classify Command

Parse input after `/wiki`:

| Input | Route |
|-------|-------|
| `ingest <URL/path/text>` | Step 2: Ingest |
| `query <question>` | Step 3: Query |
| `recall <date_or_topic>` | Step 4: Recall |
| `export` | Step 5: Export |
| `benchmark [preset]` | Step 6: Benchmark |
| `daemon` | Step 7: Daemon |
| `mcp` | Step 8: MCP |
| `lint` | Step 8: Lint |
| `status` | Step 9: Status |

Implicit routing (no explicit mode keyword):
- Temporal words ("yesterday", "last week", "what was I doing") -> Step 4: Recall
- "what do I know about X" -> Step 3: Query
- "add to wiki", "file this" -> Step 2: Ingest
- "export sessions" -> Step 5: Export

---

## Step 2: Ingest

One source -> 5-15 wiki pages touched. This is the core compilation step.

### 2.1: Acquire Source

| Input | Action |
|-------|--------|
| URL | WebFetch -> save to `sources/articles/YYYY-MM-DD-slug.md` |
| File path | Read file. If not in sources/, copy it there |
| Inline text | Save to `sources/notes/YYYY-MM-DD-slug.md` |
| "yesterday's session about X" | Use recall (Step 4) to find session, confirm with user |

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

Read the source and current local Snowiki outputs. Use the shipped retrieval surfaces where possible. Do not assume qmd is available or canonical.

### 2.3: Compile (the core step)

Read CLAUDE.md for rules. Then:

**A. Create summary page** (mandatory, always):
- `wiki/summaries/<slug>.md`
- Key Claims, Notable Details, Open Questions
- Link to all concept/entity pages this source informed

**B. Create or update concept pages**:
- For each significant concept: check if `wiki/concepts/<name>.md` exists
  - Exists -> append new information. Never delete existing content.
  - New -> create with Definition, How It Works, Strengths, Limitations
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
- Maintain "Start Here -> overview.md"

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
Ingested: "Source Title"
   Created: 4 pages (summaries/slug.md, concepts/x.md, entities/y.md, comparisons/a-vs-b.md)
   Updated: 3 pages (overview.md, topics/z.md, index.md)
   Total pages touched: 7
```

### 2.5: Post-ingest

If the runtime later exposes additional indexing/maintenance helpers, use those. Do not assume a qmd update/embed loop is the current shipped behavior.

---

## Step 3: Query

Search the wiki, synthesize an answer. Good answers compound back into the wiki.

### 3.1: Search Strategy

Use the shipped `snowiki query` runtime first.

Current truth:
- lexical runtime is shipped
- semantic/hybrid/rerank are not yet shipped as the canonical runtime path

So this workflow should assume `snowiki query` first, and only treat qmd-like hybrid flows as lineage or future-facing ideas.

### 3.2: Synthesize

- Read top 3-5 matching pages in full via `qmd get`
- Generate answer with inline `[[wikilinks]]`
- Flag gaps: "Not in wiki — consider ingesting a source about X"

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

---

## Step 4: Recall

Load context from vault memory. Three sub-modes: temporal, topic, graph.

### 4.0: Environment Setup

```bash
VAULT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
TZ=$(date +%Z)
```

Scripts live at `~/.claude/skills/wiki/scripts/`. The recall scripts (`recall-day.py`, `session-graph.py`) are reused from the original recall skill — they stay in the scripts directory, integrated here.

### 4.1: Classify Recall Query

Parse the input after `recall`:

- **Graph** — starts with "graph": "graph last week", "graph yesterday"
  -> Go to Step 4.4
- **Temporal** — mentions time: "yesterday", "today", "last week", "this week", a date, "what was I doing", "session history"
  -> Go to Step 4.2
- **Topic** — mentions a subject: "QMD video", "authentication", "lab content"
  -> Go to Step 4.3
- **Both** — temporal + topic: "what did I do with QMD yesterday"
  -> Go to Step 4.2 first, then scan results for the topic

### 4.2: Temporal Recall (JSONL Timeline)

Run the recall-day script:

```bash
python3 ~/.claude/skills/wiki/scripts/recall-day.py list DATE_EXPR
```

Replace `DATE_EXPR` with the parsed date expression. Supported:
- `yesterday`, `today`
- `YYYY-MM-DD`
- `last monday` .. `last sunday`
- `this week`, `last week`
- `N days ago`, `last N days`

Options:
- `--min-msgs N` — filter noise (default: 3)
- `--all-projects` — scan all projects, not just current vault

Present the table to the user. If they pick a session to expand:

```bash
python3 ~/.claude/skills/wiki/scripts/recall-day.py expand SESSION_ID
```

This shows the conversation flow (user messages, assistant first lines, tool calls).

### 4.3: Topic Recall

Use the shipped `snowiki recall` behavior first. Topic expansion and broader hybrid recall remain possible future enhancements, but should not be assumed as current built-in runtime behavior.

**Step 4.3.1: Expand query into variants.** Generate 3-4 alternative phrasings that someone might use for the same topic. Think: what other words describe this? Example:
- User says "disk clean up" -> variants: `"disk cleanup free space"`, `"large files storage"`, `"delete cache bloat GB"`, `"free up computer space"`

**Step 4.3.2: Run ALL variants across ALL collections in parallel** (fast, ~0.3s each):

```bash
qmd search "VARIANT_1" -c sessions -n 5
qmd search "VARIANT_2" -c sessions -n 5
qmd search "VARIANT_3" -c sessions -n 5
qmd search "VARIANT_1" -c sources -n 5
qmd search "VARIANT_2" -c sources -n 5
qmd search "VARIANT_1" -c sessions -n 3
```

Run sessions variants in parallel. Sources/sessions can use fewer variants (prioritize sessions for recall).

**Step 4.3.3: Deduplicate results** by document path. If same doc appears in multiple searches, keep the highest score. Present top 5 unique results.

### 4.4: Graph Visualization

Strip "graph" prefix from query to get the date expression. Run:

```bash
python3 ~/.claude/skills/wiki/scripts/session-graph.py DATE_EXPR
```

Options:
- `--min-files N` — only show sessions touching N+ files (default: 2, use 5+ for cleaner graphs)
- `--min-msgs N` — filter noise (default: 3)
- `--all-projects` — scan all projects
- `-o PATH` — custom output path (default: /tmp/session-graph.html)
- `--no-open` — don't auto-open browser

Opens interactive HTML in browser. Session nodes colored by day, file nodes colored by folder.
Tell the user the node/edge counts and what to look for (clusters, shared files).

### 4.5: Fetch Full Documents (topic path only)

For the top 3 most relevant results across all collections, get the full document:

```bash
qmd get "qmd://collection/path/to/file.md" -l 50
```

Use the paths returned from Step 4.3 searches. The `-l 50` flag limits to 50 lines (adjust if needed for very large files).

### 4.6: Present Structured Summary

**For temporal queries:** Present the session table and offer to expand any session.

**For topic queries:** Organize results by collection type:

**Sessions**
- What was worked on related to this topic
- Key dates and decisions
- Current status or next steps

**Sources**
- Relevant research findings
- Plans or proposals

Keep this concise — it is context loading, not a full report.

### 4.7: Synthesize "One Thing"

After presenting recall results (temporal, topic, or graph), synthesize the single highest-leverage next action.

**How to pick the One Thing:**
1. Look at what has momentum — sessions with recent activity, things mid-flow
2. Look at what is blocked — removing a blocker unlocks downstream work
3. Look at what is closest to done — finishing > starting
4. Weigh urgency signals: deadlines in session titles, "blocked" status, time-sensitive content

**Format:** Bold line at the end of results:

> **One Thing: [specific, concrete action]**

**Good examples:**
- **One Thing: Finish the QMD video outline — sections 3-5 are drafted, just needs the closing CTA**
- **One Thing: Unblock the lab deploy — the DNS config is the only remaining blocker**

**Bad examples (too generic):**
- "Continue working on the video"
- "Pick up where you left off"

If the recall results do not have enough signal to pick a clear One Thing, skip it and ask "What would you like to work on from here?" instead.

### 4.8: Fallback — No Results

```
No results found for "QUERY". Try:
- Different search terms
- Broader keywords / different date range
- --min-msgs 1 to include short sessions
```

---

## Step 5: Sync

Export Claude Code sessions to Obsidian markdown for observability and analysis.

### 5.0: Environment Setup

```bash
VAULT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
TZ=$(date +%Z)
```

Session script lives at `~/.claude/skills/wiki/scripts/claude-sessions`.

### 5.1: Classify Sync Subcommand

| Input | Action |
|-------|--------|
| `sync` (no args) | Sync current session (hook or explicit) |
| `sync export --today` | Batch export today's sessions |
| `sync export --all` | Export all sessions |
| `sync export <file>` | Export specific session file |
| `sync resume --pick` | Interactive resume (pick from list) |
| `sync resume --active` | Resume most recent active session |
| `sync note "text"` | Add timestamped comment to current session |
| `sync close "text"` | Mark session done + optional comment |
| `sync list` | List active sessions |
| `sync list --all` | List all sessions |
| `sync log "title, status, tags, rating"` | Log/annotate current session |

### 5.2: Sync/Export Flow

```bash
python3 ~/.claude/skills/wiki/scripts/claude-sessions sync
python3 ~/.claude/skills/wiki/scripts/claude-sessions export --today
python3 ~/.claude/skills/wiki/scripts/claude-sessions list --all
```

Sessions exported to `Claude-Sessions/` directory with:
- Frontmatter: `type`, `date`, `session_id`, `title`, `summary`, `skills`, `messages`, `status`, `tags`, `rating`, `comments`
- Content: Summary, Skills Used (linked), Artifacts (wiki-linked), My Notes, Conversation

### 5.3: Log/Annotate Flow

When user says "log session" or provides metadata like title, tags, status, rating:

1. Parse intent from natural language:
   - **Title:** after "title:" or first quoted phrase
   - **Status:** done, active, blocked, handoff
   - **Rating:** number 1-10
   - **Tags:** match against `schema/tags.yaml`
   - **Comment:** everything else, or auto-generate from context
2. Read `schema/tags.yaml` to validate tags
3. Generate summary (2-3 lines from conversation analysis)
4. Update session file frontmatter

### 5.4: Preserved on Sync

These fields are never overwritten on re-sync:
- `## My Notes` section in body
- Frontmatter: `comments`, `related`, `status`, `tags`, `rating`

### 5.5: Finding Current Session

```bash
echo $CLAUDE_SESSION_ID
# Session file pattern: Claude-Sessions/YYYY-MM-DD-{session_id[:8]}.md
```

### 5.6: Report

```
Synced: 3 sessions exported to Claude-Sessions/
  - 2026-04-07-a1b2c3d4.md (active, 42 messages)
  - 2026-04-07-e5f6g7h8.md (done, 18 messages)
  - 2026-04-06-i9j0k1l2.md (done, 65 messages)
```

---

## Step 6: Edit

Lightweight page modification. For small changes that do not warrant a full ingest cycle.

### 6.1: Identify Target Page

Parse `<page>` from input. Accept:
- Full path: `wiki/concepts/bm25.md`
- Short name: `bm25` — search for matching page via Glob or index.md
- Wikilink: `[[wiki/concepts/bm25]]`

If ambiguous (multiple matches), present options and let user choose.

### 6.2: Read Current Page

Read the target page in full. Present current content to user if they have not specified the exact change.

### 6.3: Apply Change

Use the Edit tool for surgical modifications. Types of edits:
- **Add section:** append new section to body
- **Update claim:** modify existing text (flag if contradicts prior source)
- **Add link:** insert `[[wikilink]]` to related page
- **Update frontmatter:** add/modify metadata fields
- **Fix formatting:** correct markdown issues

Rules:
- Never delete existing content — append or update only
- If changing a factual claim, add a contradiction flag if old claim came from a different source
- Always preserve existing wikilinks

### 6.4: Update Metadata

Update the page's frontmatter:
```yaml
updated: YYYY-MM-DD
```

If the edit adds a new related page, update the `related:` array.

### 6.5: Update Cross-References

If the edit affects other pages (new links, changed entity info):
- Update the linked pages' `related:` arrays to include backlinks
- Update index.md if page category or title changed

### 6.6: Log and Index

Append to log.md:
```markdown
## [YYYY-MM-DD] edit | Page Title
- page: wiki/concepts/bm25.md
- change: Brief description of what changed
```

Run `qmd update` to re-index the modified page.

### 6.7: Report

```
Edited: wiki/concepts/bm25.md
  Change: Added "Okapi BM25 variant" section with formula
  Updated: frontmatter timestamp, related array
```

---

## Step 7: Merge

Consolidate overlapping pages into one authoritative page.

### 7.1: Identify Pages to Merge

Parse `<page1>` and `<page2>` from input. Accept same formats as edit (full path, short name, wikilink).

If user says "merge" without specifying pages, check lint results or search for candidates:
- Pages with similar titles
- Pages with high content overlap (same sources cited)
- Pages in same directory covering same concept

### 7.2: Read Both Pages

Read both pages in full. Analyze:
- Which page is more comprehensive (this becomes the **primary**)
- Which has more inbound links (prefer keeping this one)
- Unique content in each
- Contradictions between them
- Overlapping claims (same info stated differently)

Present analysis to user:
```
Merge candidates:
  Primary (keep): wiki/concepts/bm25.md (8 inbound links, 3 sources)
  Secondary (absorb): wiki/concepts/okapi-bm25.md (2 inbound links, 1 source)
  Overlap: 60% content similarity
  Unique to secondary: Okapi variant formula, parameter tuning section
  Contradictions: none
```

### 7.3: Combine Content

Using the primary page as the base:
1. Append unique content from secondary page into appropriate sections
2. Preserve all source attributions from both pages
3. Merge `related:` arrays (deduplicate)
4. Merge `sources:` arrays
5. Update frontmatter: `updated: YYYY-MM-DD`
6. Add note about merge:
   ```markdown
   > [!note] Merged
   > This page absorbed content from [[wiki/concepts/okapi-bm25]] on YYYY-MM-DD.
   ```

### 7.4: Redirect Links

Find all pages that link to the secondary (absorbed) page:

```bash
grep -r "okapi-bm25" wiki/ --include="*.md" -l
```

For each linking page:
- Replace `[[wiki/concepts/okapi-bm25]]` with `[[wiki/concepts/bm25]]`
- Update their `related:` arrays

### 7.5: Handle Secondary Page

Do NOT delete the secondary page (wiki pages: never delete). Instead, replace its content with a redirect:

```markdown
---
type: concept
title: "Okapi BM25"
redirect: "[[wiki/concepts/bm25]]"
merged_into: wiki/concepts/bm25.md
merged_date: YYYY-MM-DD
---

This page has been merged into [[wiki/concepts/bm25]].
```

### 7.6: Update Index

- Remove secondary page from index.md listing (or mark as redirect)
- Update page counts
- Update any category counts affected

### 7.7: Log and Index

Append to log.md:
```markdown
## [YYYY-MM-DD] merge | Page1 + Page2
- primary: wiki/concepts/bm25.md
- absorbed: wiki/concepts/okapi-bm25.md
- links redirected: 4 pages updated
- summary: Consolidated BM25 variants into single authoritative page.
```

Run `qmd update` to re-index.

### 7.8: Report

```
Merged: wiki/concepts/okapi-bm25.md -> wiki/concepts/bm25.md
  Added: Okapi variant formula, parameter tuning section
  Redirected: 4 pages updated with new links
  Secondary: converted to redirect stub
```

---

## Step 8: Lint

Health-check per CLAUDE.md rules.

### 8.1: Structural Checks (script-based)

Run `python3 ~/.claude/skills/wiki/scripts/lint.py --vault $VAULT_DIR`

Catches: L001-L006 (L001=Missing frontmatter ERROR, L002=Broken links ERROR, L003=Orphan pages WARN, L004=Source without summary WARN, L005=Page missing from index ERROR, L006=Stale pages 30+ days INFO).

### 8.2: Semantic Checks (LLM-based)

After structural lint, the LLM reads flagged pages and checks:
- Cross-page contradictions (claims that conflict between pages)
- Overlapping pages that should be merged (candidates for Step 7)
- Concepts mentioned but lacking their own page
- Stale claims superseded by newer sources
- Missing connections that should be linked

### 8.3: Gap Analysis

Suggest new sources to seek:
- "No wiki pages about X, but it's mentioned in 3 places — consider ingesting a source"
- "Topic Y has only 1 source — more depth needed"

### 8.4: Report and Fix

Present findings. For auto-fixable issues (missing from index, stale overview), offer to fix.
For semantic issues, present the contradiction and let user decide.
For merge candidates, offer to run Step 7.

Append to log.md:
```markdown
## [YYYY-MM-DD] lint | Health check
- errors: N, warnings: N
- merge candidates: N pairs
- actions: description of fixes applied
```

---

## Step 9: Status

Quick overview of the entire system.

Run `python3 ~/.claude/skills/wiki/scripts/status.py --vault $VAULT_DIR`

Or manually:
```
Snowiki Status

Pages:     42 (summaries: 12, concepts: 8, entities: 10, topics: 5, comparisons: 3, questions: 4)
Sources:   28 (articles: 12, sessions: 14, notes: 2)
Overview:  Last updated 2026-04-07
Last:      [2026-04-07] ingest | Source Title
Health:    0 errors, 2 warnings
Sessions:  6 active, 142 total (Claude-Sessions/)
qmd:       42 docs indexed, 28 embedded, GPU: cuda
```

Include session stats (from Claude-Sessions/) in the status output to reflect the unified scope.

---

## Notes

- One source at a time for ingest (quality > speed)
- Always discuss before writing (unless user says "just file it")
- sources/ is immutable — never modify
- sessions/ are "live" while active, frozen after session ends
- Wiki pages: append/update only — never delete content
- Contradictions: flag, do not resolve silently
- Good query answers -> file back -> snowball compounds
- Use `[[wikilinks]]` everywhere for Obsidian graph connectivity
- Entity pages are graph hubs — they should have many inbound links
- The overview.md is the thesis — keep it narrative, not a list
- Every claim traces to source
- Recall scripts (recall-day.py, session-graph.py) live in the skill's scripts/ directory
- Sync script (claude-sessions) lives in the skill's scripts/ directory
- For recall/sync: always resolve VAULT_DIR and TZ before running scripts
- Search strategy: lex for speed, lex+vec for depth, context-aware selection

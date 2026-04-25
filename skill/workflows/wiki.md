# Snowiki Workflow

## Important

This file is a workflow guide around the current Snowiki CLI. For the authoritative mapping of skill routes to runtime commands, see the [Wiki Route Contract](../../docs/roadmap/step3_wiki-skill-design/01-wiki-route-contract.md).

The authoritative shipped runtime contract is the installed `snowiki` command, not the older qmd-centric workflow assumptions. Do not assume a qmd update/embed loop is the current shipped behavior.

Use this file to guide how an agent should orchestrate the shipped CLI, and treat any broader wiki workflow notes as deferred ideas unless the runtime explicitly exposes them.

Current shipped CLI surface:

### Primary Current Routes
- `snowiki ingest`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki prune`
- `snowiki fileback`

### Advanced Passthrough
- `snowiki export`
- `snowiki benchmark`
- `snowiki benchmark-fetch`
- `snowiki daemon`
- `snowiki mcp`

### Shipped CLI Support
- `snowiki rebuild` (not a primary `/wiki` route)

## Step 0: Bootstrap

On first use:
1. Confirm the installed runtime with `snowiki --help`.
2. Prefer `snowiki ... --output json` for machine-readable results.
3. If faster repeated reads are useful, optionally start `snowiki daemon`; treat it as an optimization, not a separate contract.

## Step 1: Classify Command

Parse input after `/wiki`:

| Input | Route | Status |
|-------|-------|--------|
| `ingest <URL/path/text>` | Step 2: Ingest | Current |
| `query <question>` | Step 3: Query | Current |
| `recall <date_or_topic>` | Step 4: Recall | Current |
| `fileback preview <question>` | Step 5: Fileback Preview | Current |
| `fileback preview --queue <question>` | Step 5: Fileback Preview | Current |
| `fileback queue list` | Step 5: Fileback Preview | Current |
| `fileback apply` | Step 6: Fileback Apply | Current |
| `prune sources` | Step 12: Source Prune | Current |
| `sync` | Step 7: Sync | **Deferred** |
| `edit <page>` | Step 8: Edit | **Deferred** |
| `merge <p1> <p2>` | Step 9: Merge | **Deferred** |

Standalone sync/edit/merge/graph workflows remain deferred. Phase 5 planning may introduce narrow edit/merge behavior only inside reviewed source-gardening proposals.
| `lint` | Step 10: Lint | Current |
| `status` | Step 11: Status | Current |

Implicit routing (no explicit mode keyword):
- Temporal words ("yesterday", "last week", "what was I doing") -> Step 4: Recall
- "what do I know about X" -> Step 3: Query
- "add to wiki", "file this" -> Step 2: Ingest

---

## Step 2: Ingest

Use `snowiki ingest` on Markdown files or directories, then rebuild if needed.

Typical current flow:

```bash
snowiki ingest /path/to/source.md --output json
snowiki ingest /path/to/docs/ --rebuild --output json
snowiki rebuild
```

For Claude/OpenCode sessions, first summarize or export the durable knowledge into a Markdown note, then ingest that note. Do not present direct session-export ingest as the primary shipped workflow.

Do not describe older `sources/` or `wiki/` hand-edited layouts as the shipped contract.

---

## Step 3: Query

Search compiled knowledge and synthesize an answer.

### 3.1: Search Strategy

Use the shipped `snowiki query` runtime first.

Current truth:
- Lexical retrieval is the shipped runtime path.
- Semantic/hybrid/rerank remain deferred reference workflows.
- When a daemon is already reachable, daemon-backed reads may be preferred as a warm-read optimization.
- If the daemon is unavailable, fall back to the canonical CLI path without changing result shape.

### 3.2: Synthesize

- Read the returned results.
- Answer from current compiled knowledge.
- If the answer should become durable knowledge, use the current `fileback` flow instead of claiming ad-hoc page writes.

---

## Step 4: Recall

Load context from current stored knowledge/session-derived material.

### 4.1: Temporal Recall

Use the shipped `snowiki recall` command for temporal context.

If a daemon is already reachable, daemon-backed recall may be preferred as a warm-read optimization. CLI fallback remains canonical.

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


### 4.5: Fallback — No Results

```
No results found for "QUERY". Try:
- Different search terms
- Broader keywords / different date range
```

---

## Step 5: Fileback Preview

Current shipped write posture is reviewable and CLI-only.

Use `snowiki fileback preview` to produce a non-mutating proposal that includes:
- the target compiled question path
- reviewed draft content
- supporting evidence paths
- the apply plan for the eventual reviewed write

Do not treat preview as an applied write.

For autonomous work that should not stop for immediate apply, use `snowiki fileback preview --queue` to persist the proposal under the active Snowiki root as control-plane state. Queued proposals are non-blocking and pending; they are not source truth or compiler input.

Use `snowiki fileback queue list --output json` to inspect pending proposals. Use `--status pending|applied|rejected|failed|all` when terminal queue artifacts are relevant.

Use `snowiki fileback queue show <proposal-id> --output json` to inspect queue metadata without exposing full raw/normalized payloads. Add `--verbose` only when full proposal/apply payload details are needed.

Use `snowiki fileback queue apply <proposal-id> --output json` to apply a pending queue entry through the canonical reviewed fileback apply path. Successful applies archive the queue envelope to `queue/proposals/applied/`; runtime failures archive it to `queue/proposals/failed/` with safe error metadata.

Use `snowiki fileback queue reject <proposal-id> --reason "..." --output json` when a human/runtime declines a proposal. Rejected envelopes move to `queue/proposals/rejected/`.

Use `snowiki fileback queue prune --status applied|rejected|failed|all --keep 50 --output json` for dry-run terminal cleanup. Actual deletion requires `--delete --yes`; pending proposals are not pruned by the default retention policy.

Use `snowiki fileback preview --queue --auto-apply-low-risk` only when the runtime should apply a proposal if, and only if, deterministic low-risk policy checks pass. Agent-provided labels are not trusted.

---

## Step 6: Fileback Apply

Use `snowiki fileback apply --proposal-file ...` only with a reviewed preview payload.

Current truth:
- this is shipped behavior
- it is derived and reviewable
- it writes through the canonical CLI path
- compiled question pages remain rebuild-generated artifacts
- pending queue proposals are not applied writes until this apply path or a documented runtime policy succeeds

Do not claim direct MCP writes or direct compiled-file editing.

---

## Step 7: Sync (Deferred Workflow)

This is not part of Phase 3 queue hardening and has no scheduled implementation in the current runtime.

Exporting Claude Code sessions to Obsidian markdown is a deferred reference workflow. If the runtime later exposes a `sync` command:
1. Detect `VAULT_DIR` and `TZ`.
2. Run the sync/export logic.
3. Preserve `## My Notes` and specific frontmatter fields.

---

## Step 8: Edit (Deferred Workflow)

This is not part of the current shipped runtime as a standalone workflow. Phase 5 planning may introduce narrow edit semantics only inside reviewed source-gardening proposals.

Lightweight page modification is a deferred reference workflow. If the runtime later exposes an `edit` command:
1. Identify target page.
2. Read current content.
3. Apply surgical modifications via `Edit` tool.
4. Update metadata and cross-references.

---

## Step 9: Merge (Deferred Workflow)

This is not part of the current shipped runtime as a standalone workflow. Phase 5 planning may introduce narrow merge semantics only inside reviewed source-gardening proposals.

Consolidating overlapping pages is a deferred reference workflow. If the runtime later exposes a `merge` command:
1. Identify pages to merge.
2. Analyze overlap and contradictions.
3. Combine content into a primary page.
4. Redirect links and update index.


---

## Step 10: Lint

Health-check per `CLAUDE.md` rules.

### 10.1: Structural Checks

Run `snowiki lint` for the authoritative runtime linting. Source freshness findings are runtime-owned:

- `source.modified`: reingest the changed source before relying on compiled state.
- `source.missing`: inspect with `snowiki prune sources --dry-run` before cleanup.
- `source.rename_candidate`: review the exact-hash missing/untracked evidence before pruning; usually reingest the untracked source first, then review prune candidates again.
- `source.untracked`: ingest the source root if the file should become durable knowledge.

### 10.2: Semantic Checks (Informative)

The LLM may check for:
- Cross-page contradictions.
- Overlapping pages that should be merged.
- Concepts mentioned but lacking their own page.
- Stale claims superseded by newer sources.

### 10.3: Gap Analysis (Informative)

Suggest new sources to seek:
- "No wiki pages about X, but it's mentioned in 3 places — consider ingesting a source."
- "Topic Y has only 1 source — more depth needed."

### 10.4: Report and Fix

Present findings. For auto-fixable issues, offer to fix.
For semantic issues, present the contradiction and let user decide.

---

## Step 11: Status

Quick overview of the entire system.

Run `snowiki status` for the authoritative runtime status. Treat `sources.freshness` as the summary surface; use `snowiki lint` for detailed paths and recommended actions.

Informative status may include:
```
Snowiki Status

Pages:     42 (summaries: 12, concepts: 8, entities: 10, topics: 5, comparisons: 3, questions: 4)
Sources:   28 (articles: 12, sessions: 14, notes: 2)
Overview:  Last updated 2026-04-07
Health:    0 errors, 2 warnings
```

---

## Step 12: Source Prune

Source prune is current but destructive only with explicit confirmation.

Safe flow:

```bash
snowiki status --output json
snowiki lint --output json
snowiki prune sources --dry-run --output json
```

Only after reviewing candidates, include explicit all-candidate confirmation:

```bash
snowiki prune sources --delete --yes --all-candidates --output json
```

Current prune scope is intentionally narrow: missing-source normalized Markdown records and raw snapshots that become unreferenced. It rebuilds generated artifacts after deletion. Do not claim multi-source cascade cleanup, source rename repair, or dead-wikilink gardening as shipped behavior yet.

---

## Notes

- One source at a time for ingest (quality > speed)
- Prefer the installed CLI as runtime truth
- Use daemon-backed reads only when already available
- `fileback` is current and reviewable; preview before apply
- `prune sources` is dry-run-first; delete only with `--delete --yes --all-candidates`
- Do not claim MCP write support
- Deferred flows stay clearly marked deferred
- Search strategy: lexical-first retrieval is the current runtime truth

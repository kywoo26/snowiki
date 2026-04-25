# Snowiki Workflow Reference

Read this only when the main `SKILL.md` is not enough to choose a safe intent expansion. The installed `snowiki` CLI is runtime truth; this reference explains common orchestration patterns.

## Operating Style

- Observe before asking: check status, lint, recall, query, or relevant files when available.
- Hypothesize before asking: prefer “I think X because Y; confirm?” over broad discovery questions.
- Propose concrete writes before executing session filing or fileback apply flows.
- Ask only targeted questions for lifecycle workflows; trivial ingest/query should not trigger interviews.
- Use progressive disclosure: status/query summaries -> compiled paths -> evidence/source paths -> raw source files only when needed.

## Lifecycle Intents

Claude Code loads one skill named `wiki`, invoked directly as `/wiki`. These are phase arguments or intent labels after `/wiki`, not separate slash commands defined by the skill.

| Intent | Agent expansion |
| --- | --- |
| `/wiki start ...` | Run status, then relevant recall/query, then propose one next action. |
| `/wiki ingest <path> [goal]` | Resolve the first existing path as source. If it is a durable Markdown source, ingest it; if it is a broad scope plus a goal, inspect relevant evidence, write one derived Markdown note, ingest that note with `--rebuild`, then validate with status/lint/query. Do not bulk-ingest broad directories unless explicitly requested. |
| `/wiki progress` | Run status and lint to detect drift, stale sources, and pending cleanup risks. |
| `/wiki finish` | Write a durable Markdown session note, ingest it, verify retrieval, and optionally queue fileback. |
| `/wiki health` | Run lint plus targeted review; surface issues without silently applying semantic fixes. |

## Intent Selection

| User intent | Use |
| --- | --- |
| “ingest this”, “add to wiki”, “file this source” | `snowiki ingest` |
| “what do I know about X?” | `snowiki query` |
| “what did we work on yesterday/last week?” | `snowiki recall` |
| “save this answer” | `snowiki fileback preview`, queue/apply only after review |
| “is the wiki healthy?” | `snowiki status`, then `snowiki lint` |
| “clean missing sources” | `snowiki prune sources --dry-run`, then explicit delete only after review |

## Session-to-Markdown Filing

For Claude/OpenCode sessions:

1. Extract durable decisions, facts, evidence links, open questions, and follow-ups into a human-readable Markdown note.
2. Add only user-authored/session metadata in frontmatter; do not claim Snowiki-generated fields.
3. Ingest that Markdown note.
4. Verify the content can be found through query or recall.

## Query and Recall

- Use `snowiki query` for knowledge questions.
- Use `snowiki recall` for temporal or topic recall supported by the runtime.
- Call shipped CLI JSON commands; daemon behavior is runtime-owned and must not be reimplemented in the skill package.
- If recall is used for work continuation, end with `**One Thing: [specific, concrete action]**`.
- If an answer should become durable, use fileback instead of direct page edits.

## Fileback

1. Preview first; preview output is a proposal, not an applied write.
2. Queue when autonomous work should continue without immediate apply.
3. Apply only through documented fileback apply or queue apply paths after review.
4. Rebuild or validate after successful apply when needed.
5. Trust runtime low-risk policy, not agent labels, for any auto-apply behavior.

## Status, Lint, and Source Prune

Source freshness handling:

- `source.modified`: reingest before relying on compiled state.
- `source.untracked`: ingest if it should become durable knowledge.
- `source.rename_candidate`: usually reingest the untracked path before pruning the old missing record.
- `source.missing`: review prune dry-run candidates before deletion.

Source prune is narrow: missing-source normalized Markdown records and raw snapshots that become unreferenced. Do not claim multi-source cascade cleanup, rename repair, or dead-wikilink gardening as shipped behavior.

Any fix must use current CLI-mediated paths such as reingest, dry-run-first prune, or reviewable fileback. Standalone edit/merge-style fixes remain deferred unless a future runtime spec ships them.

## Deferred Reference Workflows

The following are not current runtime commands:

- standalone sync
- standalone edit
- standalone merge
- graph-oriented recall or visualization
- topic expansion beyond shipped recall behavior
- semantic, hybrid, vector, or rerank retrieval as the default runtime path
- MCP write/delete

If a future runtime exposes one of these, update `SKILL.md`, this reference, and the architecture contract together.

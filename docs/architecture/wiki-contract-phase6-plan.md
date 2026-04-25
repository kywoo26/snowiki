# Phase 6 Agent Workflow Plan

Status: **planning wave**. This document is the executable Phase 6 plan. Durable outcomes should be folded into `docs/architecture/skill-and-agent-interface-contract.md` and `docs/architecture/refactoring-operating-principles.md` as implementation decisions land.

## Goal

Phase 6 turns Snowiki from a set of correct CLI primitives into a disciplined **agent-operated LLM wiki workflow** for Claude Code, OpenCode/OMO, and similar coding agents.

Snowiki still follows Karpathy's LLM Wiki premise:

- humans curate sources, ask questions, and review durable mutations;
- agents summarize, file, query, lint, and maintain the wiki;
- the installed `snowiki` CLI and its JSON output remain runtime truth;
- skills and workflow docs orchestrate the CLI, but must not invent a parallel backend.

The phase should make it obvious how an agent uses Snowiki during real work without expanding the runtime command surface by default.

## Scope

### In Scope

- Claude Code `wiki` skill and OpenCode/OMO-style workflow guidance over current CLI primitives.
- Natural-language intent mapping for common journeys:
  - ingest this file or directory;
  - summarize this session or conversation into a Markdown note and ingest it;
  - rebuild and verify the wiki;
  - query or recall from compiled knowledge;
  - file a durable answer through reviewable `fileback` flows;
  - run `status`/`lint` before continuing work;
  - review source freshness, rename candidates, and prune candidates safely.
- Session-to-Markdown workflow design that keeps direct Claude/OpenCode export ingest out of `snowiki ingest PATH`.
- Skill documentation that uses progressive disclosure: concise discovery metadata, detailed workflow docs, and explicit deferred modes.
- Agent-readable examples that prioritize `--output json` and stable runtime contracts over prose scraping.
- OMO/OpenCode and Claude Code integration notes that explain how agents should trigger Snowiki workflows without broadening core runtime behavior.

### Out of Scope

- New standalone runtime commands for `sync`, `edit`, `merge`, or graph workflows.
- Direct Claude/OpenCode export ingest in the primary `snowiki ingest` CLI.
- MCP write/delete support.
- Semantic/vector/hybrid retrieval expansion.
- Full append-only event sourcing.
- Persistent policy config.
- Projection backfill/migration or normalized storage write-contract redesign.

## Reference Evidence

Local and external references point to these design constraints:

1. **Karpathy LLM Wiki** keeps the workflow surface small (`ingest`, `query`, `lint`) while the LLM performs summarization, filing, cross-linking, and maintenance.
2. **Agent skill implementations** such as `llm-wiki-agent`, `agent-wiki`, and Claude skills examples favor natural-language triggers, `AGENTS.md`/`CLAUDE.md` schemas, and workflow packaging over large CLI surfaces.
3. **Snowiki's own contract** makes CLI JSON output normative and skill docs informative mirrors; skills cannot silently redefine capabilities or bypass CLI-level validation.
4. **Claude Skills guidance** favors progressive disclosure: concise skill discovery metadata, linked workflow/supporting docs, and command examples that expose current runtime truth instead of freezing stale copies.
5. **OpenCode/OMO-style orchestration** favors role-based agents and MCP/CLI tool use, which maps to Snowiki as an orchestration layer over CLI primitives rather than a second runtime.
6. **Local-first wiki implementations** such as `llm-wiki-compiler`, `obsidian-llm-wiki-local`, and seCall-like vault workflows reinforce source traceability, status-first operation, review queues, and rebuildable derived artifacts.

The reference research pass for Phase 6 should specifically compare:

- Claude Code skill packaging and progressive disclosure;
- OpenCode/OMO workflow invocation patterns;
- Karpathy-derived LLM wiki implementations' README/SKILL/AGENTS guidance;
- local `llm-wiki-references` examples for how agents map `ingest`, `query`, `lint`, `file/absorb`, and `cleanup` workflows to tool/CLI calls.

Reference implications for this plan:

- Keep the shipped workflow vocabulary close to Karpathy's small loop, then let agents do synthesis and filing work above it.
- Borrow `agent-wiki`'s session lifecycle vocabulary (`start`, `ingest`, `progress`, `finish`, `health`) as `wiki` skill intents, not runtime commands.
- Treat Farzapedia-style `absorb`, `cleanup`, `breakdown`, and `reorganize` as useful workflow names, not new commands, unless a later CLI spec accepts them.
- Preserve the skill split: `SKILL.md` for discovery and runtime truth, `skill/references/wiki-workflow.md` for on-demand workflow detail.
- Prefer status/lint before mutation-like work so agents see stale, missing, untracked, and rename-candidate source facts before pruning or filing.
- Use reviewable fileback and queue flows for durable writes; never teach agents to edit compiled wiki artifacts directly.
- Teach agent behavior, not only commands: observe first, hypothesize before asking, propose concrete writes before executing, ask a small number of targeted questions, and continue softly if Snowiki is unavailable.

## Agent Workflow Contracts

Phase 6 documents five canonical journeys. Each journey must name the CLI command an agent consumes and whether the result is read-only, proposal-only, or applied state.

| Journey | CLI contract | Skill intent | State posture |
| --- | --- | --- | --- |
| Ingest file or directory | `snowiki ingest <path> --output json` | Step 2 | Applies through runtime storage |
| File session as knowledge | Markdown note -> `snowiki ingest <note> --rebuild --output json` | Step 2 | Applies after agent-created note is ingested |
| Query or recall | `snowiki query` / `snowiki recall --output json` | Steps 3-4 | Read-only |
| File durable answer | `fileback preview` -> queue/apply | Steps 5-6 | Proposal first, applied only through CLI |
| Review freshness | `status` -> `lint` -> `prune sources --dry-run` | Steps 10-12 | Read-only until explicit prune delete |

### Session Lifecycle Skill Intents

Phase 6 may name lifecycle intents for agent ergonomics. Claude Code loads one skill named `wiki`, so these are arguments to `/wiki`; they must expand to shipped CLI primitives and must not imply independent hyphenated slash commands.

| Skill intent | Expansion over current CLI truth | Purpose |
| --- | --- | --- |
| `/wiki start ...` | `status --output json` + relevant `recall`/`query` | Brief current context, detect stale sources, propose a plan |
| `/wiki ingest <path>` | `ingest <path> --output json` + optional `rebuild` + `status` | Make source material durable |
| `/wiki progress` | `status --output json` + `lint --output json` | Mid-session checkpoint and scope-drift check |
| `/wiki finish` | session Markdown note + `ingest <note> --rebuild --output json` + optional `fileback preview --queue` | Capture durable outcomes before context is lost |
| `/wiki health` | `lint --output json` + targeted human-readable review | Deeper maintenance/audit without new mutation commands |

Agents may expose these as natural-language triggers or host-level wrappers outside the skill package, but docs must explain the underlying CLI sequence so the intent cannot drift from runtime truth.

### 1. Ingest a file or directory

Agent flow:

1. Confirm the source is Markdown or a directory of Markdown files.
2. Run `snowiki ingest <path> --output json` or `snowiki ingest <path> --rebuild --output json`.
3. Read `documents_stale`, `rebuild_required`, and document paths from JSON output.
4. If needed, run `snowiki rebuild --output json`.
5. Run `snowiki status --output json` or `snowiki lint --output json` before claiming the wiki is healthy.

Natural-language triggers include “ingest this,” “add this to the wiki,” “file this source,” and “make this source durable.”

### 2. File this session as durable knowledge

Agent flow:

1. Summarize durable decisions, open questions, and follow-up actions into a Markdown note.
2. Add source/session metadata in frontmatter without claiming Snowiki-generated fields unless runtime-owned.
3. Save the note in the user's chosen source/vault location.
4. Run `snowiki ingest <note> --rebuild --output json`.
5. Verify recall/query can find the filed content.

This is a workflow, not direct session-export ingest. Raw Claude/OpenCode logs remain outside the primary `snowiki ingest PATH` contract unless converted to Markdown first.

The note should preserve human reviewability: durable decisions, facts, evidence links, open questions, and follow-up actions should be visible in Markdown rather than buried in agent memory.

### 3. Query or recall the wiki

Agent flow:

1. Prefer `snowiki query <question> --output json` for current knowledge questions.
2. Prefer `snowiki recall <target> --output json` for temporal/topic recall already shipped by the CLI.
3. Use shipped CLI JSON output as the skill contract; daemon optimizations must stay behind runtime-owned commands rather than skill-side fallback logic.
4. Synthesize an answer from returned compiled knowledge and cite relevant paths when useful.
5. If the answer should become durable, use fileback preview/queue rather than writing compiled files directly.

Recall responses should end with a single “One Thing” action when used for work continuation, mirroring the existing skill workflow pattern.

### 4. File a durable answer

Agent flow:

1. Run `snowiki fileback preview <question> --output json` or `snowiki fileback preview --queue <question> --output json`.
2. Treat preview output as a proposal, not an applied write.
3. Use queue commands for non-blocking review flows.
4. Apply only through `snowiki fileback queue apply` or `snowiki fileback apply --proposal-file ...` after review.
5. Rebuild/verify after successful apply.

### 5. Review freshness before continuing work

Agent flow:

1. Run `snowiki status --output json` for dashboard counts.
2. Run `snowiki lint --output json` for actionable path-level findings.
3. For `source.modified`, reingest before relying on compiled state.
4. For `source.rename_candidate`, reingest the untracked source before pruning old missing records.
5. For `source.missing`, run `snowiki prune sources --dry-run --output json` and review candidates before deletion.
6. Destructive prune remains explicit: `snowiki prune sources --delete --yes --all-candidates --output json`.

This journey is the Phase 6 replacement for broad “garden” wording: agents read source-freshness facts from existing JSON contracts and choose explicit reingest/prune/fileback steps instead of invoking a new maintenance command.

## Skill Packaging Plan

- Keep `skill/SKILL.md` short and discoverable; avoid embedding long runbooks there.
- Keep detailed intent mapping in `skill/references/wiki-workflow.md` so Claude Code, OpenCode/OMO, and similar agents can load only the depth they need.
- Keep `skill/AGENTS.md` as package governance for deferred workflows and preservation rules.
- Keep `skill/scripts/` empty unless a future skill-specific helper is justified by Claude Skills guidance; do not place Snowiki runtime behavior, CLI wrappers, daemon fallback, or Markdown note drafting there.
- Keep any future `CLAUDE.md` or concise agent entrypoint minimal: point to the installed CLI, `skill/SKILL.md`, and the canonical architecture contract instead of duplicating long workflow text.
- Document install/validation around the installed `snowiki` binary; if a checkout is used, examples should say `uv run snowiki ...`.
- Future dynamic command discovery may be added only if it reflects installed CLI help/status without changing behavior.
- Any plan artifact guidance should remain optional workflow discipline above the runtime, useful for multi-step wiki maintenance but not required for simple ingest/query flows.

## Agent Behavior Rules

Agent-facing workflow docs should encode behavior rules learned from local references:

- Observe before asking; inspect status, lint, recall, or relevant files when available.
- Hypothesize before asking; prefer “I think X because Y; confirm?” over broad discovery questions.
- Propose concrete writes before executing them, especially for session filing and fileback flows.
- Ask only a small set of targeted questions during lifecycle intents; trivial ingest/query should not trigger interviews.
- Use progressive disclosure for retrieval: start from status/index-like summaries, then compiled answers, then evidence/source paths, then raw source files only when needed.
- Continue softly when optional optimizations are unavailable: daemon/MCP absence must not block canonical CLI use.

## Use-Case Examples

These examples define expected skill/workflow behavior. They are not new `snowiki` subcommands.

### UC1: Start work with wiki context

```text
User: /wiki start phase 6 문서 작업 이어가자
Agent:
  1. Runs `snowiki status --output json`.
  2. Runs `snowiki recall "phase 6" --output json`.
  3. Runs `snowiki query "Phase 6 agent workflows" --output json` if more current knowledge is needed.
  4. Reports stale sources, pending proposals, or lint risks before doing new work.
  5. Ends with one concrete next action.
```

### UC2: File a session as durable knowledge

```text
User: 이 세션 wiki에 남겨
Agent:
  1. Summarizes durable decisions, open questions, and follow-ups into a Markdown note.
  2. Adds human-readable frontmatter such as date, tags, session metadata, and confidence.
  3. Runs `snowiki ingest <note> --rebuild --output json`.
  4. Verifies the note can be found with `snowiki query` or `snowiki recall`.
  5. Uses `snowiki fileback preview --queue ... --output json` only when a durable answer proposal needs review.
```

Raw Claude/OpenCode session exports are not ingested directly in this flow; the agent converts durable knowledge to Markdown first.

### UC3: Check progress or health before continuing

```text
Agent:
  1. Runs `snowiki status --output json`.
  2. Runs `snowiki lint --output json`.
  3. Reingests `source.modified` paths before relying on compiled state.
  4. For `source.rename_candidate`, reingests the untracked path before reviewing old missing records.
  5. For `source.missing`, runs `snowiki prune sources --dry-run --output json` before any deletion.
```

This is the safe replacement for broad maintenance verbs: the agent composes current JSON contracts instead of invoking a new garden/sync/cleanup command.

## Distribution Model

- Runtime distribution remains the Python CLI: install with `uv tool install --from . snowiki` from a checkout or an equivalent package distribution, then inspect `snowiki --help`.
- Development checkout examples should use `uv run snowiki ...` so docs and verification stay repo-local.
- Claude Code skill distribution is the `skill/` package copied or symlinked to `~/.claude/skills/wiki/`, where `SKILL.md` is the discovery entrypoint and `references/wiki-workflow.md` is the detailed intent guide.
- OpenCode/OMO integration uses the same workflow text through project instructions or agent skill packaging; it should call the installed `snowiki` CLI and parse JSON output rather than embedding runtime logic.
- `snowiki mcp` may be used as a read-only retrieval surface. MCP write/delete support is not part of Phase 6 distribution.

## Deferred Workflow Policy

- `sync` may be described as a session-to-Markdown workflow concept, but not as a shipped standalone runtime command.
- Standalone `edit` and `merge` remain deferred until Snowiki has explicit write contracts beyond fileback and gardening proposals.
- Graph-oriented workflows remain deferred to the retrieval/graph roadmap unless they are purely informative over existing read-only outputs.
- MCP remains read-only.
- Skills may describe future concepts only in clearly marked deferred sections.

## Acceptance Criteria

- Phase 6 plan exists and replaces Phase 5 as the active executable plan.
- Phase 5 shipped outcomes and remaining carry-forward items are recorded in the durable architecture ledger.
- Skill docs explain Claude/OpenCode/OMO usage as workflows over CLI truth, not alternate runtime behavior.
- Lifecycle intents such as `/wiki start`, `/wiki progress`, `/wiki finish`, and `/wiki health` are documented only as arguments to the single `wiki` skill command, not shipped `snowiki` subcommands or independent slash commands.
- Session-to-Markdown filing is specified without reintroducing direct session-export ingest into `snowiki ingest PATH`.
- README and quickstart stay aligned with the shipped CLI surface and deferred workflow policy.
- Standalone `sync`, standalone `edit`, standalone `merge`, and graph-oriented workflows remain clearly deferred unless a later runtime spec accepts them.
- MCP remains read-only; write/delete support is not documented as shipped behavior.
- No runtime implementation is added until a workflow contract names the exact CLI JSON payloads agents consume.

## Migration from Phase 5 Plan

This document absorbs carry-forward items from the deleted Phase 5 executable plan:

- standalone `sync`, `edit`, `merge`, and graph workflow concepts;
- the requirement to keep mutation CLI-mediated and reviewable;
- the boundary that skills/workflows mirror CLI truth and do not add hidden runtime behavior;
- post-Phase 5 deferrals for semantic/vector retrieval, MCP writes, event journal, policy config, projection migration, and storage redesign.

The Phase 5 executable plan has been removed; this document is now the active executable plan.

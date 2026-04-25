---
name: wiki
description: "Snowiki CLI-first wiki workflow. Use when the user asks to ingest notes, query or recall wiki knowledge, check wiki status/lint, prune missing sources safely, file a durable answer, or invoke /wiki with start/progress/finish/health-style arguments."
when_to_use: "Use for phrases like /wiki ingest, /wiki query, /wiki recall, /wiki start, /wiki progress, /wiki finish, /wiki health, add this to the wiki, what do I know about, what did we work on, file this session, save this answer, wiki status, wiki lint, and prune missing sources. Do not use for general coding tasks unless the user asks to consult or update Snowiki."
argument-hint: "[ingest SOURCE|query QUESTION|recall TARGET|status|lint|prune sources|fileback preview QUESTION|fileback apply|start TOPIC|progress|finish|health]"
---

# Snowiki Wiki Skill

Snowiki is a CLI-first, agent-operated wiki. The installed `snowiki` command and its JSON output are runtime truth; this skill only teaches Claude when to use that runtime.

Claude Code exposes this skill as one command named `/wiki`. Treat text after `/wiki` as arguments that describe the user's wiki intent; do not invent hyphenated sibling commands.

## Start Here

1. Confirm the runtime when needed: `snowiki --help`.
2. In a development checkout, use `uv run snowiki ...`.
3. Prefer `snowiki ... --output json` when supported.
4. Read `references/wiki-workflow.md` only when lifecycle intent mapping, write-safety details, or deferred workflow boundaries are needed.

This skill ships no scripts by default. Use Claude's normal file/tools for Markdown reading or note drafting, and use the installed `snowiki` CLI for runtime behavior.

## Current CLI Primitives

Use these shipped commands as atomic building blocks:

- `snowiki ingest`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki prune`
- `snowiki fileback`

Support and advanced commands also exist: `export` is for backup/migration/inspection, `benchmark` and `benchmark-fetch` are development/evaluation surfaces, `daemon` is runtime optimization, and `mcp` is a read-only transport bridge. `snowiki rebuild` is shipped support, not a primary wiki skill primitive.

## Common `/wiki` Arguments

Claude Code loads this as one skill named `wiki`; it does not define independent slash commands. Treat text after `/wiki` as an argument that describes the user's intent.

- `start`, `ingest`, `query`, `recall`, `progress`, `finish`, and `health` are common argument patterns.
- For exact intent-to-CLI mapping, read `references/wiki-workflow.md`.

Let Claude choose the exact CLI sequence from the user's goal and current state, while respecting the boundaries below.

## Critical Boundaries

- Do not redefine runtime capabilities or invent `snowiki` subcommands.
- Do not ingest raw Claude/OpenCode session exports as the primary workflow; summarize durable knowledge into Markdown first.
- For `/wiki ingest <path> [goal]`, treat `<path>` as an evidence scope, not a request to persist every file under it. Persist only durable Markdown knowledge: a user-intended Markdown source or one derived Markdown note created from inspected evidence. Read non-Markdown or operational files only as evidence unless the user explicitly asks to preserve those exact files.
- Do not edit compiled wiki artifacts directly.
- Do not add or rely on skill scripts for Snowiki runtime behavior.
- File tools may be used for user-authored Markdown notes or reviewed source material when the user intent requires it; durable Snowiki storage changes still go through the CLI.
- Use `fileback preview` before any durable answer write; apply only through reviewed fileback paths.
- Use `prune sources --dry-run` before destructive source cleanup; deletion requires explicit delete confirmation flags.
- Do not implement daemon fallback, payload normalization, or command behavior in this skill; call the shipped CLI instead.
- If `snowiki` is unavailable or returns an error, report that failure rather than emulating runtime behavior.
- Do not claim MCP write/delete support.

## Deferred Workflow Ideas

These are not current runtime commands unless a future runtime explicitly ships them:

- standalone sync
- standalone edit
- standalone merge
- graph-oriented recall or visualization
- semantic, hybrid, vector, or rerank retrieval as the default runtime path

## Reference

For detailed intent mapping, read `references/wiki-workflow.md`.

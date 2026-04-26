---
name: wiki
description: "Snowiki CLI-first wiki workflow for ingest, query/recall, status/lint, safe prune, fileback, and /wiki lifecycle intents."
when_to_use: "Use when the user asks to consult or update Snowiki/wiki knowledge, including /wiki ..., add/save/file this to the wiki, what do I know about, what did we work on, wiki health, or prune missing sources."
argument-hint: "[ingest SOURCE|query QUESTION|recall TARGET|status|lint|prune sources|fileback preview QUESTION|fileback apply|start TOPIC|progress|finish|health]"
---

# Snowiki Wiki Skill

Snowiki is CLI-first. The installed `snowiki` command is runtime truth; this skill only maps `/wiki ...` intents to safe CLI use.

## Start Here

1. Confirm the runtime when needed: `snowiki --version` or `snowiki --help`.
2. In a development checkout, use `uv run snowiki ...`.
3. Prefer `snowiki ... --output json` for automation.
4. Read `references/wiki-workflow.md` only when lifecycle intent mapping, write-safety details, or deferred workflow boundaries are needed.

Use normal file tools for Markdown reading/drafting. Durable Snowiki changes still go through the CLI.

## Optional CLI Invocation Defaults

These are installed CLI defaults, not skill configuration. Snowiki works without them. Use `SNOWIKI_ROOT` only to pin a non-default wiki root and `SNOWIKI_OUTPUT=json` only to avoid repeating `--output json`.

JSON success is normally `{"ok": true, "command": "...", "result": {...}}`; runtime failures use `{"ok": false, "error": {...}}`; semantic failures such as lint errors may return `{"ok": false, "command": "lint", "result": {...}}`.

## Current CLI Primitives

Use these shipped commands as atomic building blocks:

- `snowiki ingest`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki prune`
- `snowiki fileback`

Support commands exist (`export`, `rebuild`, read-only `mcp`, benchmarks), but they are not primary `/wiki` primitives.

## Common `/wiki` Arguments

- `start`, `ingest`, `query`, `recall`, `progress`, `finish`, and `health` are common argument patterns.
- For exact intent-to-CLI mapping, read `references/wiki-workflow.md`.

## Critical Boundaries

- Do not redefine runtime capabilities or invent `snowiki` subcommands.
- Do not ingest raw Claude/OpenCode session exports as the primary workflow; summarize durable knowledge into Markdown first.
- For `/wiki ingest <path> [goal]`, treat `<path>` as an evidence scope, not a request to persist every file under it. Persist only durable Markdown knowledge: a user-intended Markdown source or one derived Markdown note created from inspected evidence. Read non-Markdown or operational files only as evidence unless the user explicitly asks to preserve those exact files.
- Do not edit compiled wiki artifacts directly.
- Use `fileback preview` before any durable answer write; apply only through reviewed fileback paths.
- Use `prune sources --dry-run` before destructive source cleanup; deletion requires `prune sources --delete --yes --all-candidates`.
- Use `fileback queue prune` as a dry-run-first cleanup surface; deletion requires `fileback queue prune --delete --yes`.
- Do not implement payload normalization or command behavior in this skill; call the shipped CLI instead.
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

# snowiki ❄️

A personal wiki that compounds knowledge like a snowball.

Snowiki’s current shipped runtime is **CLI-first**. The installed `snowiki` command is the authoritative runtime contract; the Claude Code `wiki` skill is a workflow layer that should mirror the CLI rather than redefine it.

## Quick Start

This README is an **informative mirror** of the canonical contract at `docs/architecture/skill-and-agent-interface-contract.md` and the packaged wiki skill at `skill/SKILL.md`.

```bash
# 1. Install Snowiki from a checkout
uv tool install --from . snowiki

# 2. Inspect the shipped command surface
snowiki --help
snowiki -h
snowiki --version

# 3. Use the current runtime directly
snowiki ingest /path/to/README.md --output json
snowiki ingest /path/to/docs/ --output json
snowiki ingest /path/to/docs/ --rebuild --output json
snowiki rebuild
snowiki query "What do I know about X?" --output json
snowiki recall yesterday --output json
snowiki status --output json
snowiki lint --output json
snowiki prune sources --dry-run --output json
```

Markdown files and directories are the primary ingest surface. Claude/OpenCode session exports should be converted into Markdown notes by an agent or skill workflow, then ingested with `snowiki ingest <note-or-directory>`.

For the Claude Code `wiki` skill workflow, use this README as the short entrypoint and follow the dedicated guide at [`docs/reference/claude-code-wiki-quickstart.md`](docs/reference/claude-code-wiki-quickstart.md). It covers install-from-checkout, optional daemon startup for faster reads, and the current `fileback preview/queue/apply` flow.

If you are working from a development checkout instead of a tool install, run the same commands as `uv run snowiki ...`.

## CLI affordances for agents

- Help and discovery: every command supports `-h` and `--help`; the top-level command also supports `--version`.
- Shared configuration: set `SNOWIKI_ROOT` to choose the storage root and `SNOWIKI_OUTPUT=json` to make supported commands emit machine-readable output without repeating `--output json`.
- Daemon configuration: `snowiki daemon` also respects `SNOWIKI_DAEMON_HOST`, `SNOWIKI_DAEMON_PORT`, and `SNOWIKI_DAEMON_CACHE_TTL`.
- Shell completion: Click completion scripts are available for Bash, Zsh, and Fish; for Bash use `eval "$(_SNOWIKI_COMPLETE=bash_source snowiki)"`.
- JSON envelope: successful JSON commands emit `{"ok": true, "command": "...", "result": {...}}`; runtime failures emit `{"ok": false, "error": {...}}`; semantic failures such as lint errors may emit `{"ok": false, "command": "lint", "result": {...}}`.

## Current shipped CLI surface

The current runtime exposes these top-level commands. For the detailed role taxonomy, see `docs/architecture/cli-command-taxonomy.md`.

### Primary Current Commands
- `snowiki ingest`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki prune`
- `snowiki fileback`

### Support / Advanced / Evaluation
- `snowiki export`
- `snowiki benchmark`
- `snowiki benchmark-fetch`
- `snowiki daemon`
- `snowiki mcp`

### Shipped CLI Support
- `snowiki rebuild` (support command, not a primary everyday wiki skill intent)

## Claude Code `wiki` skill status

The `wiki` skill should currently mirror this shipped surface for everyday use:

- current: `ingest`, `query`, `recall`, `status`, `lint`, `prune sources --dry-run`, `prune sources --delete --yes --all-candidates`, `fileback preview`, `fileback preview --queue`, `fileback preview --queue --auto-apply-low-risk`, `fileback queue list`, `fileback queue show`, `fileback queue apply`, `fileback queue reject`, `fileback queue prune`, `fileback apply`
- optimization, not skill logic: `snowiki daemon` remains a runtime CLI feature, but the `wiki` skill should call documented `snowiki ... --output json` commands rather than implementing daemon fallback itself
- agent workflows: Claude Code exposes one `/wiki` skill command; phase arguments such as `/wiki start`, `/wiki progress`, `/wiki finish`, and `/wiki health` expand to current CLI sequences rather than new runtime commands
- deferred unless explicitly accepted by runtime spec: standalone `sync`, standalone `edit`, standalone `merge`, graph-oriented workflows

Do not treat daemon internals, qmd lineage, or older vault-layout docs as a separate product contract.

`export` is a support/debug surface for backup, migration, inspection, fixtures, and external integration. It is not a primary everyday `/wiki` flow.

## Machine-usable surfaces today

- CLI JSON output via `snowiki ... --output json`
- read-only MCP via `snowiki mcp`

Mutation remains CLI-mediated. MCP write support is not shipped. Source cleanup is report-first through `status`/`lint` and dry-run-first through `snowiki prune sources`; destructive source pruning requires `--delete --yes --all-candidates`. `lint --output json` may include agent-readable source gardening diagnostics such as exact-hash rename candidates before a missing source is pruned. Autonomous writeback queues are control-plane proposal artifacts until applied through a documented CLI path. The CLI queue lifecycle supports pending/applied/rejected/failed proposal states, dry-run-first terminal pruning, and runtime-owned low-risk auto-apply policy before any broader mutation surface is considered.

## Design Principles

1. **CLI truth first** — docs and skills mirror the installed runtime instead of inventing a parallel wiki backend
2. **Compilation, not ad-hoc mutation** — durable knowledge flows through Snowiki storage and rebuild paths
3. **Reviewable writes** — `fileback apply` requires a reviewed proposal from `fileback preview`
4. **Search-strategic** — lexical-first retrieval is shipped now; hybrid/semantic work remains deferred
5. **Performance where it matters** — runtime optimizations belong behind shipped `snowiki` commands, not in the skill package

## Related

- `docs/architecture/skill-and-agent-interface-contract.md` — canonical agent/runtime contract
- `docs/architecture/source-vault-compiled-taxonomy.md` — source, raw, normalized, compiled, and vault layer taxonomy
- `docs/architecture/cli-command-taxonomy.md` — command classes and primary/support surface boundaries
- `docs/reference/claude-code-wiki-quickstart.md` — step-by-step Claude Code `wiki` skill adoption guide
- [qmd](https://github.com/tobi/qmd) — lineage/reference material, not the current Snowiki runtime

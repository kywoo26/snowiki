# Skill Governance Delta

Root `AGENTS.md` is inherited; this file defines local deltas only.

## Scope

This directory governs the distributable skill package and its associated workflows. It defines how the LLM interacts with the Snowiki vault.

## Environment & Footprint

- `VAULT_DIR`: Root of the Obsidian vault (detected via git or cwd).
- `TZ`: Timezone for temporal queries and sync timestamps.
- Footprint: `~/.claude/skills/wiki/` for scripts and `~/.claude/projects/` for session logs.

## Workflow & Logic

- `skill/SKILL.md` defines the tool surface and core architecture.
- `skill/workflows/wiki.md` contains the detailed step-by-step routing for current and deferred modes.
- Logic changes in `skill/scripts/` must preserve the "One Thing" synthesis principle in recall.
- Lifecycle route names are skill workflows, not `snowiki` subcommands. Keep `/wiki-start`, `/wiki-progress`, `/wiki-finish`, and `/wiki-health` mapped to current CLI sequences in `skill/workflows/wiki.md`.
- Session filing must convert durable Claude/OpenCode knowledge into Markdown before ingest; do not teach raw session-export ingest as the shipped workflow.

## Write Safety

- Mutation must stay CLI-mediated.
- `fileback preview` is non-mutating; `fileback apply` or queue apply is the reviewed write path.
- `prune sources --dry-run` is required before destructive source cleanup.
- Destructive prune requires `prune sources --delete --yes --all-candidates`.
- MCP write/delete support is not shipped.

## Deferred Workflow Policy

- `sync`, standalone `edit`, standalone `merge`, and graph-oriented flows are deferred reference workflows.
- Agent workflows orchestrate current CLI truth without claiming standalone sync/edit/merge/graph commands ship.
- If implemented, `sync` operations must preserve `## My Notes` and specific frontmatter fields (`comments`, `related`, `status`, `tags`, `rating`).
- Exported sessions live in `Claude-Sessions/` within the vault.

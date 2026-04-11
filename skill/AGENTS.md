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
- `skill/workflows/wiki.md` contains the detailed step-by-step routing for all 8 modes.
- Logic changes in `skill/scripts/` must preserve the "One Thing" synthesis principle in recall.

## Sync Policy

- `sync` operations must preserve `## My Notes` and specific frontmatter fields (`comments`, `related`, `status`, `tags`, `rating`).
- Exported sessions live in `Claude-Sessions/` within the vault.

## Workflow

Detailed tool definitions and mode-specific logic live in `skill/SKILL.md` and `skill/workflows/wiki.md`.

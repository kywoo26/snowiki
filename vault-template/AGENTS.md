# Vault Template Governance Delta

Root `AGENTS.md` is inherited; this file defines local deltas only.

## Scope

This directory governs the distributable vault schema and template layout. It ensures the integrity of the "Snowball" knowledge compounding loop.

## Schema Integrity

- `vault-template/CLAUDE.md` is the canonical schema documentation.
- `sources/` is strictly immutable. Never modify or delete files once ingested.
- `wiki/` pages follow an append/update-only policy. Never delete existing content.
- Maintain `[[wikilinks]]` for Obsidian graph connectivity.

## Evolution & Caution

- Schema changes (directory structure, frontmatter requirements) are high-impact.
- Consult `vault-template/CLAUDE.md` before proposing layout modifications.
- Ensure any schema evolution is reflected in the `skill/` package.

## Workflow

Detailed schema rules, ingest/query workflows, and lint codes live in `vault-template/CLAUDE.md`.

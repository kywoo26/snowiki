# Source, Vault, and Compiled Taxonomy

## Purpose

This document defines Snowiki's durable knowledge layers before retrieval work expands the runtime surface.

The goal is to keep source handling, raw provenance, normalized records, compiled pages, and Obsidian-style vault usage distinct. These layers are related, but they are not interchangeable.

## Core rule

Snowiki treats sources as evidence and compiled pages as derived memory.

Users, agents, and external tools may author or collect source material. Snowiki may snapshot, normalize, index, compile, lint, and query that material. Generated compiled pages must remain rebuildable from accepted source/provenance state.

## Runtime layers

| Layer | Current runtime shape | Owner | Mutability | Role |
| :--- | :--- | :--- | :--- | :--- |
| Source root | External filesystem path recorded as `source_root` plus `source_path` | User, agent, or upstream tool | Editable outside Snowiki | Durable evidence or authoring location. |
| Raw snapshot | `$SNOWIKI_ROOT/raw/` | Snowiki runtime | Runtime-managed | Provenance-preserving copy of accepted source content. |
| Normalized record | `$SNOWIKI_ROOT/normalized/` | Snowiki runtime | Runtime-managed | Typed/indexable representation used by search, status, lint, and rebuild. |
| Compiled page | `$SNOWIKI_ROOT/compiled/` | Snowiki compiler/runtime | Generated; do not hand-edit as truth | Queryable wiki memory derived from normalized records. |
| Index state | `$SNOWIKI_ROOT/index/` | Snowiki runtime | Rebuildable cache | Retrieval acceleration and lookup state. |
| Control-plane queue | `$SNOWIKI_ROOT/queue/` | Snowiki runtime | Proposal lifecycle only | Pending mutation intent; not source truth until applied through CLI. |

## Source is a role, not an author type

`source` does not mean only user-authored notes.

A source is any durable evidence/document artifact that Snowiki may ingest or use to support compiled knowledge. Valid source roles include:

- `user_note` — human-authored Markdown, including Obsidian notes
- `project_doc` — repository docs, READMEs, architecture notes, specs, plans
- `session_note` — durable summary extracted from Claude/OpenCode/agent sessions
- `research_note` — web, code-search, or external-reference research captured as Markdown
- `imported_doc` — converted PDF, HTML, DOCX, API export, or other durable document
- `generated_note` — LLM-created Markdown that has been reviewed or accepted as durable evidence
- `fileback_answer` — an answer or synthesis accepted through a reviewable fileback path

The author may be a human, an LLM, an external system, or a conversion tool. The requirement is durability plus provenance, not human authorship.

## Obsidian and vault usage

Obsidian is best treated as one possible source authoring surface and/or a read-only viewer for generated compiled pages.

Recommended usage:

1. Keep human-editable notes in an external source root, such as an Obsidian vault or project documentation directory.
2. Ingest selected Markdown files or scoped directories with `snowiki ingest`.
3. Treat `$SNOWIKI_ROOT/compiled/` as generated wiki memory. It may be viewed, but manual edits there are not canonical because rebuilds may overwrite them.
4. Use `fileback` or a reviewed source-note edit when compiled knowledge should feed back into durable editable material.

Snowiki does not currently require a root-internal `sources/` authoring zone. Existing references to a `sources/` zone should be read as conceptual shorthand for external source roots plus runtime provenance, not as a shipped storage directory contract.

## Relationship to LLM wiki references

Most Karpathy-style LLM wiki implementations use a three-layer pattern:

1. raw/source material
2. generated wiki pages
3. rules, schemas, lint, or review policy

Snowiki maps that pattern to the current shipped runtime as:

1. external `source_root`/`source_path` plus `$SNOWIKI_ROOT/raw/`
2. `$SNOWIKI_ROOT/normalized/` and `$SNOWIKI_ROOT/compiled/`
3. architecture contracts, CLI JSON, lint/status/fileback policy, and skill workflow guidance

This keeps Snowiki compatible with the LLM wiki lineage without pretending that the runtime already ships the exact `raw/` + `wiki/` vault layout used by other projects.

## Query-time implication

Retrieval should preserve layer identity.

- Hits from compiled pages answer from derived wiki memory.
- Hits from normalized/raw provenance answer from source evidence.
- Status and lint results describe freshness or structural health, not knowledge synthesis.
- Fileback proposals are pending edits, not accepted source truth.

Keeping these identities separate prevents retrieval improvements from collapsing evidence, synthesis, cache, and pending mutation into one ambiguous bucket.

# Wiki Route Contract

## Purpose

Define the canonical `/wiki` route taxonomy and the mapping between skill routes and the underlying CLI/MCP runtime to ensure deterministic agent behavior. This document is the **canonical owner** of the route taxonomy and route-to-runtime map.

## Canonical Route Matrix

The following matrix defines the authoritative mapping between `/wiki` skill routes and the Snowiki runtime.

| Skill Route | Runtime Mapping | Bucket | Description |
| :--- | :--- | :--- | :--- |
| `ingest` | `snowiki ingest` | Primary Current | Ingests a supported source into Snowiki storage. |
| `query` | `snowiki query --output json` | Primary Current | Searches compiled knowledge using the current lexical retrieval runtime. |
| `recall` | `snowiki recall --output json` | Primary Current | Recalls temporal or topical knowledge from stored sessions and pages. |
| `status` | `snowiki status --output json` | Primary Current | Displays the current health, coverage, and system status. |
| `lint` | `snowiki lint --output json` | Primary Current | Runs authoritative health checks and schema validation. |
| `fileback preview` | `snowiki fileback preview` | Primary Current | Generates a reviewable proposal for filing back an answer. |
| `fileback apply` | `snowiki fileback apply` | Primary Current | Persists a reviewed proposal through the canonical CLI path. |
| `export` | `snowiki export` | Advanced Passthrough | Exports Snowiki data to external formats. |
| `benchmark` | `snowiki benchmark` | Advanced Passthrough | Runs performance benchmarks on the retrieval engine. |
| `daemon` | `snowiki daemon` | Advanced Passthrough | Manages the background daemon for warm-read optimizations. |
| `mcp` | `snowiki mcp` | Advanced Passthrough | Starts the read-only MCP server bridge. |
| `rebuild` | `snowiki rebuild` | Shipped CLI Support | Rebuilds search indexes and compiled artifacts (not a primary `/wiki` route). |
| `sync` | N/A | Deferred | Synchronizes sessions to an external vault. (Unavailable today) |
| `edit` | N/A | Deferred | Performs surgical edits on compiled pages. (Unavailable today) |
| `merge` | N/A | Deferred | Consolidates overlapping compiled pages. (Unavailable today) |

## Route Families

- **Knowledge Acquisition**: `ingest`
- **Retrieval & Reasoning**: `query`, `recall`
- **Health & Governance**: `status`, `lint`
- **Durable Memory (Write)**: `fileback preview`, `fileback apply`
- **System & Performance**: `export`, `benchmark`, `daemon`, `mcp`, `rebuild`

## Naming and Description Rules

- **Third-Person Singular**: All route descriptions must use third-person singular verbs (e.g., "Ingests", "Searches") to align with official skill metadata guidance.
- **Discovery-Friendly**: Descriptions must be specific enough to trigger Level 2 loading only when the wiki domain is actually required.
- **Gerund/Noun-Phrase**: Follow gerund (e.g., `ingesting-sources`) or noun-phrase conventions for internal naming where discovery is the primary goal.

## Current vs Deferred Contract

- **Unsupported Means Unavailable**: Deferred workflows (`sync`, `edit`, `merge`, and graph-oriented workflows) are **unavailable today**. They are roadmap concepts, not soft promises.
- **No Implicit Capability**: The skill must not imply that deferred routes are functional.
- **Read-Only MCP**: The MCP surface is strictly read-only. The route taxonomy must not imply write-capable MCP behavior. All mutations must flow through the CLI.

## Mirror Update Requirements

This document is the canonical owner. Any change to the route taxonomy or mapping must be mirrored in the following surfaces in the same change set:

- `skill/SKILL.md`
- `skill/workflows/wiki.md`
- `README.md`
- `docs/reference/claude-code-wiki-quickstart.md`
- `docs/roadmap/step3_wiki-skill-design/analysis.md`

Mirrors must point back to `01-wiki-route-contract.md` as the authoritative source of truth.

## In Scope

- Canonical `/wiki` route taxonomy and naming conventions.
- Current vs. deferred route split (what is supported now vs. later).
- Route-to-CLI/MCP mapping (which skill route triggers which runtime command).
- Argument mapping and basic routing logic.

## Out of Scope

- Detailed input/output schema definitions (owned by `02`).
- benchmark methodology, tokenizer selection, or retrieval quality metrics.
- Maintenance-loop sequencing details beyond route boundaries (owned by `04`).
- runtime promotion or sparse-branch proof.
- schema package details.

## Owns

- Canonical `/wiki` route taxonomy.
- Current vs. deferred route split.
- Route-to-CLI/MCP mapping.

## Does Not Own

- Schema definitions.
- Governance implementation.
- maintenance loop design.

## Related Documents

- [Step 3 Roadmap](roadmap.md)
- [Step 3 Analysis](analysis.md)

## Reference Reading

- **Progressive Disclosure**: See `docs/reference/research/claude-skill-authoring-guide.md` for how Level 1 (Metadata) and Level 2 (Instructions) affect route discovery.
- **Routing Patterns**: Review `skill/workflows/wiki.md` (Step 1: Classify Command) for the current mapping of user intent to CLI routes.
- **Discovery Model**: See `docs/roadmap/external/claude-skills/official-guidance-notes.md` for location priority and live detection rules.

## Helper Questions for Future Deep Planning

- Does the route taxonomy follow the gerund or noun-phrase naming convention suggested in official guidance?
- How does the current vs. deferred split align with the "Unsupported Means Unavailable" policy in the interface contract?
- Are route descriptions specific enough to trigger Level 2 loading only when the wiki domain is actually required?

## Deferred / Open Questions

- Should the skill support custom route aliases for specific agent personas?
- How should the skill handle route-level versioning if the CLI surface changes?

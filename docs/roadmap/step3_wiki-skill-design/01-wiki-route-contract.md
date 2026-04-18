# Sub-step A: Wiki Route Contract

## Purpose

Define the canonical `/wiki` route taxonomy and the mapping between skill routes and the underlying CLI/MCP runtime to ensure deterministic agent behavior.

## In Scope

- Canonical `/wiki` route taxonomy and naming conventions.
- Current vs. deferred route split (what is supported now vs. later).
- Route-to-CLI/MCP mapping (which skill route triggers which runtime command).
- Argument mapping and basic routing logic.

## Out of Scope

- Detailed input/output schema definitions (owned by `02`).
- Benchmark claims or retrieval quality metrics.
- Maintenance-loop sequencing details beyond route boundaries (owned by `04`).
- Tokenizer selection, benchmark methodology, or runtime promotion.

## Owns

- Canonical `/wiki` route taxonomy.
- Current vs. deferred route split.
- Route-to-CLI/MCP mapping.

## Does Not Own

- Schema definitions.
- Governance implementation.
- Maintenance loop design.

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

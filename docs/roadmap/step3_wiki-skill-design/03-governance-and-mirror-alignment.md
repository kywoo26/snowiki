# Sub-step C: Governance and Mirror Alignment

## Purpose

Define the rules for preventing drift between the skill, CLI, and MCP surfaces, and specify the governance test surface to maintain a single source of truth.

## In Scope

- Skill/CLI/MCP drift-prevention rules and alignment policies.
- Governance test surface: automated checks that fail when skill docs diverge from the CLI.
- Mirror-sync ownership: ensuring `README.md` and other mirrors reflect the canonical contract.
- Versioning alignment between the skill package and the core runtime.

## Out of Scope

- Benchmark-side validation or quality gates.
- Maintenance-loop design (owned by `04`).
- Tokenizer selection, benchmark methodology, or runtime promotion.
- Implementation of the actual CLI commands.

## Owns

- Skill/CLI/MCP drift-prevention rules.
- Governance test surface and mirror-sync ownership.

## Does Not Own

- Route taxonomy.
- Schema definitions.
- Maintenance loop design.

## Related Documents

- [Step 3 Roadmap](roadmap.md)
- [Step 3 Analysis](analysis.md)

## Reference Reading

- **Normative vs. Informative**: Review `docs/architecture/skill-and-agent-interface-contract.md` for the governance rule on updating mirrors in the same PR as normative changes.
- **Drift Prevention**: See `docs/architecture/current-retrieval-architecture.md` for the parity matrix (Routing, Metadata, Freshness, Evaluation).
- **Authoring Discipline**: Review `docs/roadmap/external/claude-skills/official-guidance-notes.md` for conciseness rules and the "Assume Claude is already smart" principle.

## Helper Questions for Future Deep Planning

- How will automated governance tests verify that the `skill/SKILL.md` mirror remains aligned with the `snowiki --help` output?
- Does the versioning alignment strategy account for the "Version match required" rule in the resumable state contract?
- What mechanism will ensure that `README.md` remains a faithful informative mirror of the canonical interface contract?

## Deferred / Open Questions

- Should governance tests run as part of every CI build or only on PRs touching the skill?
- How should we handle "soft" drift where the command exists but the behavior has subtly changed?

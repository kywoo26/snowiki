# Sub-step B: Schema and Provenance Contract

## Purpose

Define the input/output schema package for current routes and the provenance/display rules for route results to ensure structured, traceable knowledge exchange.

## In Scope

- Input/output schema package for current `/wiki` routes (YAML/JSON).
- Provenance rules: every wiki claim must trace back to a source path or session ID.
- Display contract: how results are formatted for both human review and agent consumption.
- Error schema and failure mode reporting.

## Out of Scope

- Benchmark metadata or tokenizer-specific metadata.
- Governance implementation details (owned by `03`).
- Workflow/deferred behavior design (owned by `04`).
- Tokenizer selection, benchmark methodology, or runtime promotion.

## Owns

- Input/output schema package for current routes.
- Provenance/display rules for route results.

## Does Not Own

- Route taxonomy.
- Governance rules.
- Maintenance loop design.

## Related Documents

- [Step 3 Roadmap](roadmap.md)
- [Step 3 Analysis](analysis.md)

## Reference Reading

- **Schema-First Design**: Review `docs/roadmap/external/claude-skills/reference-implementations-notes.md` (personal-os-skills) for patterns using machine-readable YAML/JSON for I/O validation.
- **Metadata Parity**: See `docs/architecture/current-retrieval-architecture.md` for the requirement to preserve provenance and score fields across all surfaces.
- **Visibility States**: Review `docs/architecture/skill-and-agent-interface-contract.md` for the definitions of Metadata-Only and Read visibility.

## Helper Questions for Future Deep Planning

- Do the input schemas account for the "Progressive Disclosure" model to avoid context bloat during large retrieval tasks?
- How will the provenance contract represent "Content-derived freshness identity" vs. "Process-local runtime generation"?
- Does the display contract ensure that "Reviewable Writes" (preview/apply) have sufficient evidence for human approval?

## Deferred / Open Questions

- Should schemas include optional fields for multimodal attachments in the future?
- How should the provenance contract handle multi-hop synthesis where one page derives from another?

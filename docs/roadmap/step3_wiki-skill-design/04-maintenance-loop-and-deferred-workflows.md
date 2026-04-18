# Sub-step D: Maintenance Loop and Deferred Workflows

## Purpose

Define the agent maintenance loop and the boundaries for deferred workflows and reviewable mutations to establish a sustainable knowledge lifecycle.

## In Scope

- The maintenance loop: Ingest → Absorb → Lint/Cleanup → Query.
- Deferred workflow boundaries: defining what `sync`, `edit`, and `merge` will eventually do.
- Reviewable mutation posture: the "propose-then-apply" contract for all wiki writes.
- Heuristics for agent-driven cleanup and synthesis.

## Out of Scope

- Runtime backend redesign or new storage engines.
- Benchmark hardening or tokenizer evaluation.
- Tokenizer selection, benchmark methodology, or runtime promotion.
- Implementation of the `fileback` or `lint` logic.

## Owns

- Ingest → absorb → lint/cleanup → query loop.
- Deferred workflow boundaries and reviewable mutation posture.

## Does Not Own

- Route taxonomy.
- Schema definitions.
- Governance rules.

## Related Documents

- [Step 3 Roadmap](roadmap.md)
- [Step 3 Analysis](analysis.md)

## Reference Reading

- **Maintenance Loop**: Review `docs/reference/research/claude-skill-authoring-guide.md` and the Farzapedia pattern in `reference-implementations-notes.md` for the ingest-absorb-cleanup-query cycle.
- **Reviewable Writes**: See `skill/workflows/wiki.md` (Steps 5 and 6) for the current `fileback preview/apply` implementation.
- **Approval Semantics**: Review `docs/architecture/skill-and-agent-interface-contract.md` for the definitions of Propose-Mutate and Required approval.

## Helper Questions for Future Deep Planning

- How does the "Absorb" step map to the "Propose-Mutate" visibility state to ensure no silent writes occur?
- Are the deferred workflow boundaries (sync, edit, merge) clearly marked as "Unsupported" to prevent agent hallucination of capabilities?
- Does the maintenance loop synthesis follow the "One Thing" principle defined in the recall workflow?

## Deferred / Open Questions

- Should the "Absorb" step be automated via a CLI command or remain an agent-orchestrated pattern?
- What is the threshold for a "stale" page in the cleanup loop?

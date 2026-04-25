# Phase 5 Wiki Gardening Proposal Plan

Status: **planning wave**. This document is the executable Phase 5 plan. Durable outcomes should be folded into `docs/architecture/llm-wiki-ingest-redesign.md` and `docs/architecture/refactoring-operating-principles.md` as implementation decisions land.

## Goal

Phase 5 turns the Phase 4 source-freshness primitives into reviewable gardening workflows. The runtime should propose safe cleanup and repair actions, not hide mutation inside `ingest`, `rebuild`, `status`, or `lint`.

The first Phase 5 implementation should make it possible for an agent or user to answer:

- Which source changes need reingest, prune, rename repair, or link cleanup?
- Which cleanup actions are safe enough to propose for review?
- Which actions must remain manual because they touch shared generated pages, source identity, or semantic content?

## Scope

### In Scope

- Reviewable gardening proposal model over Phase 4 source state.
- Source move/rename assistance that starts from `missing` + `untracked` evidence and proposes a reconciliation path.
- Multi-source cascade cleanup proposals that are structural and reviewable, not automatic substring edits.
- Dead wikilink discovery and cleanup proposals using structural wikilink parsing.
- Agent/skill workflow guidance for when to run `status`, `lint`, `ingest`, `prune sources`, and future gardening proposal commands.
- Merge/edit behavior only when it is directly required by a gardening proposal review/apply flow.

### Out of Scope

- Silent cleanup during `ingest` or `rebuild`.
- Direct destructive cascade deletion without a proposal review step.
- Broad `sync`, `edit`, `merge`, or graph workflows unrelated to source gardening.
- MCP write/delete support.
- Semantic/vector/hybrid retrieval expansion.
- Full append-only event sourcing.
- Normalized storage write-contract redesign or projection backfill.

## Candidate CLI Shape

The exact names may change during implementation, but Phase 5 should keep the CLI dry-run/review-first:

```text
snowiki garden sources --dry-run --output json
snowiki garden sources --queue --output json
snowiki garden queue list --output json
snowiki garden queue show <proposal-id> --output json
snowiki garden queue apply <proposal-id> --yes --output json
snowiki garden queue reject <proposal-id> --reason "..." --output json
```

Design bias:

- `prune sources` remains the narrow explicit deletion command from Phase 4.
- `garden sources` proposes broader repairs and cleanup where a direct prune would be too blunt.
- Queue semantics should reuse fileback concepts where practical, but not couple source gardening to question-answer writeback internals.

## Proposal Types

| Proposal type | Evidence | Default action | Apply behavior |
| :--- | :--- | :--- | :--- |
| `source_rename_candidate` | One `missing` record plus one similar `untracked` Markdown source. | Review proposed source identity reconciliation. | Reingest new source, mark old missing source for prune review, preserve provenance. |
| `dead_wikilink_candidate` | Structural wikilink parser finds links to missing generated/source pages. | Review link removal or replacement candidates. | Edit source Markdown only through a reviewed proposal path. |
| `cascade_source_cleanup_candidate` | A removed/pruned source identity appears inside multi-source generated provenance. | Review structural removal from affected source references. | Apply only through deterministic source/provenance update logic; never substring replace compiled artifacts. |
| `manual_gardening_required` | Ambiguous or high-risk source state. | Explain why automation is unsafe. | No automatic apply path. |

## Safety Rules

- Report-first remains mandatory: proposal generation must be safe to run repeatedly.
- Applying a proposal must require explicit confirmation and durable audit output.
- Generated compiled pages are rebuild artifacts; Phase 5 must not hand-edit compiled Markdown as source of truth.
- Source edits must target source Markdown files, not normalized JSON, unless the proposal is specifically a storage/provenance maintenance proposal.
- Multi-source cleanup must be structural and test-backed before any apply command ships.
- Proposal queues must use stable JSON payloads and deterministic IDs so agents can review them reliably.

## Agent Workflow Contract

Agents should use Phase 5 in this order:

1. Run `snowiki status --output json` and `snowiki lint --output json` before mutation.
2. Reingest modified sources before proposing cleanup.
3. Use `snowiki prune sources --dry-run` only for narrow missing-source deletion candidates.
4. Use Phase 5 gardening proposal commands for rename, dead-link, and cascade cleanup candidates.
5. Apply only reviewed proposals with explicit confirmation.
6. Rebuild and verify query/recall after successful apply.

## Open Questions for Implementation

- Should source rename assistance be represented as reingest plus prune, or should it update durable source identity directly?
- Should gardening queues share the fileback queue storage surface, or use a dedicated `garden/queue` namespace?
- What similarity threshold is acceptable for rename candidates before a proposal becomes manual-only?
- What wikilink parser is sufficient for Snowiki Markdown without introducing a heavyweight parser dependency?
- Which proposal types can be low-risk auto-queue candidates, and which must always remain manual review?

## Post-Phase 5 Ledger

These items must remain visible after Phase 5 planning but should not be smuggled into the first gardening proposal implementation:

| Deferred item | Target track | Why not Phase 5 |
| :--- | :--- | :--- |
| Standalone `sync` workflow | Phase 6 agent workflow | Sync needs session-to-Markdown export semantics and vault preservation rules beyond source cleanup. |
| Standalone `edit` workflow | Phase 6 agent workflow | Phase 5 may edit source Markdown only through reviewed gardening proposals; general editing needs its own write contract. |
| Standalone `merge` workflow | Phase 6 agent workflow | Phase 5 may include merge-like cleanup only for source gardening; broad page consolidation needs contradiction/link semantics. |
| Graph-oriented recall/workflows | Phase 6 or retrieval roadmap | Source gardening may parse wikilinks, but graph UX and recall are broader read workflows. |
| Semantic/vector/hybrid retrieval | Retrieval roadmap | Phase 5 is maintenance/gardening over deterministic source state, not retrieval expansion. |
| MCP write/delete support | Post-CLI write-contract phase | Mutation remains CLI-mediated until proposal apply contracts are stable. |
| Full append-only event journal | Event-log design | Phase 4 `log.md` is generated; a real event store needs ordering, retention, replay, and corruption semantics. |
| Persistent freshness/prune/garden policy config | Config design | Defaults and CLI flags need to stabilize before durable policy config ships. |
| Projection backfill/migration | Migration spec | Old projection-less records should be handled by an explicit operator command, not hidden compatibility. |
| Normalized storage write-contract redesign | Storage spec | Gardening proposals can use current records; storage layout changes deserve a separate spec and migration plan. |

## Acceptance Criteria

- The first implementation PR preserves Phase 4's report-first and dry-run-first guarantees.
- Gardening proposal generation has unit and integration coverage for rename, dead-wikilink, and ambiguous/manual cases.
- Any apply path is reviewed, explicit, audited, and followed by rebuild verification.
- Skill and quickstart docs explain the difference between `prune sources` and broader gardening proposals.
- Deferred `sync`, `edit`, `merge`, and graph workflows remain clearly marked unless directly implemented for gardening proposal review.

## Migration from Phase 4 Plan

This document absorbs the Phase 4 carry-forward items previously listed in `docs/architecture/wiki-contract-phase4-plan.md`:

- source move/rename workflow;
- multi-source cascade cleanup;
- dead wikilink cleanup;
- reviewable cleanup proposals;
- keeping broader sync/edit/merge/graph work outside the Phase 4 runtime contract.

The Phase 4 executable plan can be removed once this plan and the durable architecture ledger are updated.

# Phase 5 Wiki Gardening Proposal Plan

Status: **planning wave**. This document is the executable Phase 5 plan. Durable outcomes should be folded into `docs/architecture/llm-wiki-ingest-redesign.md` and `docs/architecture/refactoring-operating-principles.md` as implementation decisions land.

## Goal

Snowiki starts from Karpathy's LLM Wiki pattern: a persistent Markdown wiki maintained primarily by agents, with humans curating sources and reviewing durable mutations. Phase 5 must therefore improve the **agent-readable maintenance contract**, not grow a human-operated CLI surface by default.

Phase 5 turns the Phase 4 source-freshness primitives into reviewable gardening workflows. The runtime should expose stable machine-readable evidence for safe cleanup and repair decisions, not hide mutation inside `ingest`, `rebuild`, `status`, or `lint`.

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
- Agent/skill workflow guidance for when to run `status`, `lint`, `ingest`, `prune sources`, and the accepted future proposal surface.
- Merge/edit behavior only when it is directly required by a gardening proposal review/apply flow.

### Out of Scope

- Silent cleanup during `ingest` or `rebuild`.
- Direct destructive cascade deletion without a proposal review step.
- Broad `sync`, `edit`, `merge`, or graph workflows unrelated to source gardening.
- MCP write/delete support.
- Semantic/vector/hybrid retrieval expansion.
- Full append-only event sourcing.
- Normalized storage write-contract redesign or projection backfill.

## Use Cases Before Runtime Surface

Phase 5 must derive any CLI/API exposure from agent use cases and durable decisions, not from the existence of an internal proposal engine. Human-readable output is useful for review, but the primary contract is structured data that an agent can inspect, cite, queue, and act on through approved runtime paths.

| Use case | User decision | Existing surface fit | Phase 5 decision |
| :--- | :--- | :--- | :--- |
| Review a missing source before deletion | Is this source truly gone, or was it renamed/moved? | `prune sources` shows delete candidates, but should not decide rename semantics. `lint` already reports actionable source findings. | Keep `prune sources` narrow. Expose exact-hash rename evidence through `lint --output json`. |
| Review modified sources | Should changed source files be reingested before answering or pruning? | `lint` already emits `source.modified`; `status` summarizes freshness. | Prefer lint detail + status summary, not a new command. |
| Review untracked files | Should this source be ingested, ignored, or paired with a missing record as a rename? | `lint` reports `source.untracked`; Phase 5 can enrich the reason. | Exact one-to-one same-hash rename candidates are emitted as lint proposal diagnostics; ambiguous cases stay manual through existing source findings. |
| Review dead wikilinks | Should a link be fixed, removed, or left because the target is generated? | Existing lint has link diagnostics; source edits need a review/apply contract. | Future lint/proposal work only; no apply path until structural parser tests exist. |
| Review cascade cleanup | Should shared provenance/source references be cleaned after prune? | Neither `prune` nor `rebuild` should silently cascade. | Future reviewable proposal work; no first-slice implementation. |

Surface decision rules:

- `status` remains the dashboard/count surface.
- `lint --output json` is the accepted first user/agent-facing surface for actionable gardening diagnostics because it already reports path-level findings.
- `prune sources` remains the explicit narrow delete candidate/deletion command and should not grow broad rename/link/cascade decision semantics.
- A new top-level command is rejected for the first slice and should be reconsidered only if lint/status/prune cannot express the accepted user journey.
- Any accepted surface must prioritize JSON contracts and deterministic identifiers over additional human-facing flags.
- Queue semantics should reuse fileback concepts where practical, but not couple source gardening to question-answer writeback internals.

First implementation boundary:

- domain proposal generation feeds enriched lint diagnostics;
- no new CLI options or commands in the foundation slice;
- no queue, apply, source edits, or compiled edits;
- any additional user-facing exposure requires a separate UC-specific spec update plus integration tests.

## Proposal Types

| Proposal type | Evidence | Default action | Apply behavior |
| :--- | :--- | :--- | :--- |
| `source_rename_candidate` | One `missing` record plus one same-root exact-hash `untracked` Markdown source. | Review proposed source identity reconciliation. | Reingest new source, mark old missing source for prune review, preserve provenance. |
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
4. Read `source.rename_candidate` lint diagnostics before pruning missing-source candidates.
5. Treat dead-link and cascade cleanup candidates as future lint/proposal work until structural parser and source-of-truth tests exist.
6. Apply only reviewed proposals with explicit confirmation.
7. Rebuild and verify query/recall after successful apply.

The agent contract is intentionally stronger than the human CLI contract: an agent must be able to decide whether to reingest, prune, defer, or request review from structured evidence without scraping prose or relying on hidden compatibility behavior.

## Open Questions for Implementation

- Should source rename assistance be represented as reingest plus prune, or should it update durable source identity directly?
- Should gardening queues share the fileback queue storage surface, or use a dedicated `garden/queue` namespace?
- What similarity threshold is acceptable for rename candidates before a proposal becomes manual-only?
- What wikilink parser is sufficient for Snowiki Markdown without introducing a heavyweight parser dependency?
- Which proposal types can be low-risk auto-queue candidates, and which must always remain manual review?
- If source gardening reaches users, should it appear first as enriched lint issues rather than new CLI options?

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
- The foundation slice exposes exact-hash rename candidates through existing `lint --output json`, with no new CLI options or commands.
- User-facing exposure must add integration coverage for the accepted lint surface in the same PR that exposes it.
- Rename proposal generation has unit coverage for exact-hash candidates and ambiguous/manual cases before any runtime surface is exposed.
- Dead-wikilink and cascade proposal generation must not ship apply behavior until structural parsing and source-of-truth tests exist.
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

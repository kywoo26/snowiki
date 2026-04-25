# Autonomous Writeback Queue Plan

This plan captures the Phase 2 closing writeback decision before implementation. It extends the reviewed `fileback preview` -> `fileback apply` path into an autonomous-friendly, non-blocking proposal queue while preserving Snowiki's CLI-first and read-only MCP contracts.

Status: **implemented as the queue MVP**. This document remains the executable spec for the shipped queue behavior and the deferred auto-apply/state-transition work.

## Summary

Autonomous agents should be able to finish their primary task without stopping for synchronous human review every time they discover durable knowledge worth filing back into Snowiki.

The writeback path therefore becomes a side stream:

```text
agent work loop
  -> snowiki query / recall / status / lint reads
  -> fileback proposal creation
  -> policy decision
      -> low-risk apply path, when explicitly supported by runtime policy
      -> queued pending proposal for high-impact or uncertain writes
  -> primary task continues
```

The queue is not a second knowledge store. It is a control-plane artifact for pending mutation intent. Durable knowledge only enters the raw -> normalized -> compiled -> index pipeline after an approved CLI apply path succeeds.

## User Decisions Captured

- The queue must be designed from the perspective of real Snowiki CLI usage, not from the development repository checkout.
- Queue paths resolve under the active Snowiki storage root: explicit `--root`, `SNOWIKI_ROOT`, or the default `~/.snowiki`.
- Human review must not interrupt autonomous task completion. Review-required writes should become queued proposals, not blocking prompts.
- Prior reference synthesis stands: proposal-backed writeback, provenance-first evidence, CLI-mediated mutation, and no MCP writes.
- Implementation should follow this updated spec/plan rather than jumping straight from discussion to code.

## Storage Contract

Pending proposals live under a Snowiki-root control-plane queue:

```text
$SNOWIKI_ROOT/
  raw/
  normalized/
  compiled/
  index/
  queue/
    proposals/
      pending/
      applied/
      rejected/
      failed/
```

The Phase 2 closing MVP implements `queue/proposals/pending/`. The other state directories are reserved vocabulary for later lifecycle transitions.

### Why not `raw/proposals`?

`raw/` is source/provenance material. A pending agent proposal is not accepted source truth. Applied fileback raw notes may still be written under the existing reviewed raw path after apply.

### Why not `normalized/pending`?

`normalized/` is compiler input. Pending proposals there would force rebuild, query, lint, and future compiler paths to learn an ignore-pending rule. That weakens the strict Phase 2 projection boundary.

### Why not development workspace files?

The source checkout is not the user's Snowiki runtime. Queue paths must resolve from the runtime root exactly like ingest, rebuild, query, and fileback apply do.

## Proposal Envelope

A queued proposal should wrap the existing fileback proposal with runtime policy metadata. Minimum fields:

- `queue_version`
- `proposal_id`
- `queued_at`
- `root`
- `status`: `pending`, `applied`, `rejected`, or `failed`
- `decision`: `queued`, `auto_apply_allowed`, `applied`, `rejected`, or `failed`
- `impact`: `low`, `medium`, or `high`
- `requires_human_review`
- `reasons`: machine-readable reason strings
- `proposal`: the existing `FilebackProposal` payload

The existing proposal root-mismatch validation remains required. A queued proposal created for one Snowiki root must not be applied against another root.

## Policy Decision Rules

The runtime, not the agent, decides whether a proposal is low-risk. Agents may suggest context, but self-declared impact is advisory only.

### Low-risk candidate

A proposal may be considered low-risk only when all conditions hold:

- It creates a new Snowiki-owned manual question record.
- It is append-only: no overwrite, delete, merge, source-file edit, or broad multi-record rewrite.
- Evidence paths resolve inside the active Snowiki root.
- The apply plan is deterministic and matches the proposal payload.
- Target raw and normalized paths do not collide with existing files unless the apply path explicitly proves idempotency.
- Rebuild can run through the existing integrity path.

### Queue-required candidate

A proposal must be queued rather than auto-applied when any condition holds:

- delete, prune, overwrite, rename, merge, or source-file edit
- contradiction or conflict with existing durable knowledge
- weak, missing, or out-of-root provenance
- policy, preference, or long-term operating-rule changes
- config, schema, storage-layout, or MCP/CLI capability changes
- broad multi-record rewrites
- target collisions or non-idempotent write plans

Queue-required does **not** mean stop the autonomous task. It means the CLI returns a successful non-blocking queued outcome with a proposal path and reasons.

## CLI Contract

The current shipped behavior remains:

```bash
snowiki fileback preview ... --output json
snowiki fileback apply --proposal-file reviewed.json --output json
```

Phase 2 closing additions:

```bash
snowiki fileback preview ... --queue --output json
snowiki fileback queue list --output json
```

JSON outcomes:

- `fileback preview` without `--queue`: non-mutating proposal payload, unchanged from current shipped behavior.
- `fileback preview --queue`: writes a pending proposal envelope under `$SNOWIKI_ROOT/queue/proposals/pending/` and returns `result.queue.decision: "queued"`, `result.queue.proposal_id`, and `result.queue.proposal_path`.
- `fileback queue list`: lists pending proposal metadata without reading from or mutating compiled truth.
- `fileback apply --proposal-file`: remains the mutating reviewed apply path and rebuilds through the existing integrity flow.

Auto-apply is intentionally not part of the minimum queue MVP unless the implementation adds runtime policy validation and tests for every low-risk condition above.

## Implementation Seams

- `src/snowiki/storage/zones.py`: owns `queue` and `queue_proposals` path helpers under the resolved Snowiki root.
- `src/snowiki/markdown/discovery.py`: skips `queue` defensively, so a vault ingest does not ingest queue artifacts as Markdown sources.
- `src/snowiki/fileback/queue.py`: owns pending proposal envelope construction, atomic persistence, and list metadata.
- `src/snowiki/cli/commands/fileback.py`: exposes `preview --queue` and `queue list` while preserving the current preview/apply JSON envelopes.
- `tests/integration/cli/test_fileback.py`: covers `preview --queue`, non-application, and `queue list` behavior with `SNOWIKI_ROOT`.

## Acceptance Criteria

- Preview remains non-mutating unless `--queue` is explicitly requested.
- Queued proposals are written under the resolved Snowiki root, never the development checkout.
- Queued proposals do not affect `raw/`, `normalized/`, `compiled/`, `index/`, rebuild, or query until applied.
- Queue write uses atomic file writes and safe path construction.
- CLI JSON output includes enough metadata for an autonomous agent to continue without asking the user.
- MCP remains read-only and exposes no writeback or queue mutation path.
- Docs and skill mirrors distinguish shipped behavior from planned queue behavior.

## Verification Plan

Before implementation PR:

```bash
uv run ruff check src/snowiki tests
uv run ty check
uv run pytest
uv run pytest -m integration
```

Target tests:

- unit tests for queue path construction and proposal envelope shape
- integration test that `fileback preview --queue` writes only under `queue/proposals/pending/`
- integration test that queued proposals are listed by `fileback queue list`
- regression test that plain `fileback preview` remains non-mutating
- regression test that `fileback apply --proposal-file` still rejects root mismatch and malformed proposals

## Deferred Beyond Queue MVP

- automatic low-risk apply
- queue state transitions for applied/rejected/failed proposals
- queue pruning or retention policy
- broad edit/merge/sync workflows
- MCP write or queue mutation surface

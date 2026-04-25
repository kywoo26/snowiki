# Autonomous Writeback Phase 3 Plan: CLI Queue Hardening

This plan injects Phase 3 into the current Snowiki roadmap as a CLI-only autonomous writeback queue hardening phase. It supersedes the completed queue MVP plan and keeps the remaining work in one live executable plan.

Status: **implemented in the Phase 3 branch; pending final verification and PR review**. The reference-cache and count-based retention decisions below are accepted and reflected in the runtime work.

## Summary

Phase 3 should make the shipped fileback queue operationally useful without widening Snowiki's mutation surface beyond the CLI.

The current queue MVP can persist and list pending proposals:

```text
snowiki fileback preview ... --queue --output json
snowiki fileback queue list --output json
```

MVP queue behavior already established:

- `fileback preview` without `--queue` is non-mutating.
- `fileback preview --queue` writes a pending proposal envelope under `$SNOWIKI_ROOT/queue/proposals/pending/` and returns `result.queue.decision`, `result.queue.proposal_id`, and `result.queue.proposal_path`.
- `fileback queue list` lists pending proposal metadata without reading from or mutating compiled truth.
- Queue artifacts are control-plane state, not source truth, normalized compiler input, compiled output, or index content.
- MCP remains read-only and exposes no queue mutation surface.

Phase 3 extends that into a reviewed queue lifecycle:

```text
pending proposal
  -> inspect/show
  -> apply through existing fileback apply path
      -> applied archive on success
      -> failed archive on runtime failure
  -> reject explicitly when a human/runtime declines it
  -> prune old terminal queue artifacts by policy
```

Automatic low-risk apply is a policy layer on top of this lifecycle. It must not be implemented as an agent-trusted shortcut.

## Phase 3 Scope

### In Scope

1. **Queue lifecycle states**
   - Materialize `queue/proposals/{pending,applied,rejected,failed}/`.
   - Move queue envelopes atomically between state directories.
   - Preserve proposal IDs and audit metadata across transitions.
   - Keep terminal state artifacts outside `raw/`, `normalized/`, `compiled/`, and `index/`.

2. **Queue inspect/apply/reject UX**
   - `snowiki fileback queue show <proposal-id> --output json`
   - `snowiki fileback queue apply <proposal-id> --output json`
   - `snowiki fileback queue reject <proposal-id> --reason ... --output json`
   - Extend `snowiki fileback queue list` with `--status pending|applied|rejected|failed|all`.
   - Queue apply must delegate to the existing reviewed fileback apply path instead of duplicating raw/normalized/rebuild logic.

3. **Low-risk auto-apply policy**
   - Add runtime-owned policy classification for fileback proposals.
   - Allow automatic apply only when every low-risk condition in this plan is verified by code.
   - Return queued outcome when any condition is uncertain, high-impact, unsupported, or conflicting.
   - Make the policy decision visible in CLI JSON: `decision`, `impact`, `requires_human_review`, and `reasons`.

4. **Queue retention and pruning**
   - Define bounded retention for terminal states (`applied`, `rejected`, `failed`).
   - Provide dry-run-first pruning before deleting queue artifacts.
   - Keep default behavior non-destructive unless the operator explicitly requests deletion.
   - Use count-based terminal retention by default, with explicit age filters available for operators.

5. **Documentation and skill sync**
   - Update architecture docs first.
   - Update README/skill mirrors only after runtime behavior exists.
   - Preserve the read-only MCP contract.

### Explicitly Out of Scope

- MCP write support.
- MCP queue mutation tools.
- Broad `edit`, `merge`, or `sync` commands.
- Direct edits to compiled pages.
- Direct edits to user-authored source files.
- General review queues unrelated to fileback proposals.
- Normalized storage write-contract redesign.
- Projection backfill/migration.

These are separate architecture decisions. Phase 3 must not quietly introduce them while hardening the fileback queue.

## CLI Contract

Current shipped commands remain valid:

```bash
snowiki fileback preview ... --output json
snowiki fileback preview ... --queue --output json
snowiki fileback queue list --output json
snowiki fileback apply --proposal-file reviewed.json --output json
```

Phase 3 additions:

```bash
snowiki fileback queue list --status pending --output json
snowiki fileback queue show <proposal-id> --output json
snowiki fileback queue apply <proposal-id> --output json
snowiki fileback queue reject <proposal-id> --reason "..." --output json
snowiki fileback queue prune --status applied --keep 50 --dry-run --output json
snowiki fileback queue prune --status applied --older-than 30d --delete --yes --output json
```

Phase 3 auto-apply entrypoint:

```bash
snowiki fileback preview ... --queue --auto-apply-low-risk --output json
```

`--auto-apply-low-risk` must mean “runtime may apply if policy validation passes,” not “the agent says this is safe.”

## Storage Contract

Phase 3 keeps queue state under the active Snowiki root:

```text
$SNOWIKI_ROOT/queue/proposals/
  pending/<proposal_id>.json
  applied/<proposal_id>.json
  rejected/<proposal_id>.json
  failed/<proposal_id>.json
```

Terminal envelopes should include transition metadata:

- `transitioned_at`
- `transition_reason`
- `previous_status`
- `result` for apply success/failure details when safe to expose

Queue artifacts remain control-plane state. They do not become source truth, normalized input, compiled pages, or index documents.

## Phase 3 Requirements Decisions

These decisions came from the initial requirements interview:

- Successful `queue apply` archives the envelope to `applied/` by default instead of deleting it immediately.
- Failed `queue apply` moves the envelope to `failed/` immediately with safe error metadata.
- `queue reject` requires a human-readable `--reason`.
- `queue list` defaults to `pending` only; other states require `--status` or `--status all`.
- `queue show` defaults to metadata, summary, target, evidence refs, status, decision, reasons, and transition metadata. Full proposed raw/normalized payloads require `--verbose`.
- Low-risk auto-apply is in Phase 3 scope and must be implemented in this phase, not deferred again.
- Terminal queue artifacts must be prunable so the hot queue store does not grow forever.
- Low-risk auto-apply is exposed only as explicit `--auto-apply-low-risk`; no shorter alias is added in Phase 3.
- Terminal retention defaults remain CLI-only in Phase 3; persistent local config is deferred until a broader config design exists.
- `queue requeue <proposal-id>` is deferred until after lifecycle/apply/reject/prune behavior ships and has real usage feedback.

## Policy Contract

The runtime may auto-apply only if all low-risk requirements are proven:

- proposal creates a new Snowiki-owned manual question record
- no overwrite/delete/merge/source-file edit
- evidence paths resolve inside the active Snowiki root
- apply plan validates against deterministic proposal reconstruction
- raw and normalized target paths are non-colliding or explicitly idempotent
- rebuild integrity can run through the existing checked path

Everything else stays queued.

Queue-required conditions include:

- delete, prune, overwrite, rename, merge, or source-file edit
- contradiction or conflict with existing durable knowledge
- weak, missing, or out-of-root provenance
- policy, preference, or long-term operating-rule changes
- config, schema, storage-layout, or MCP/CLI capability changes
- broad multi-record rewrites
- target collisions or non-idempotent write plans

## Retention Policy

Local reference implementations do not support the earlier `30/90/180 day` default matrix for queue/review/draft deletion. The closest reference pattern is `llm-wiki`'s count-based terminal job pruning (`keep=50`), while other references archive, resolve, or flag review artifacts by state rather than deleting by age.

Phase 3 therefore uses a count-first terminal retention policy:

| State | Default full-envelope retention | Rationale |
| :--- | :--- | :--- |
| `applied` | keep latest 50 | Durable knowledge has already moved through raw/normalized/rebuild provenance; the queue envelope is operational audit context. |
| `rejected` | keep latest 50 | Rejections may need human review and policy tuning, but should not accumulate indefinitely in the hot queue store. |
| `failed` | keep latest 50 | Failures need troubleshooting context, but bounded recent history is enough for the Phase 3 CLI queue. |

Age pruning remains available only when the operator asks for it explicitly, for example `--older-than 30d`. A 30-day value is supported as a user-provided filter, not as a hidden default; no reference supports 90- or 180-day queue retention defaults.

Pruning rules:

- `queue prune` is dry-run by default.
- Terminal count pruning defaults to `--keep 50` when no `--keep` or `--older-than` is supplied.
- Deletion requires explicit `--delete --yes`.
- Pruning targets terminal states only; `pending` is never deleted by default retention.
- Prune output must report candidate count, deleted count, retained count, bytes considered, and bytes deleted.
- Future cold-archive support may preserve compact audit manifests longer than full envelopes, but Phase 3 should not invent a second archive store unless implementation proves it is required.

## Reference Research Protocol

When Phase 3 needs external implementation references, use the local cache first:

1. Search `/home/k/local/llm-wiki-references` before web or GitHub network lookups.
2. Prefer local clones already indexed by `docs/reference/llm-wiki-implementation-survey.md`.
3. Only use web/GitHub documentation after local references are insufficient or stale.
4. If a new reference repo becomes necessary, clone it into `/home/k/local/llm-wiki-references` and update the survey rather than repeatedly fetching it ad hoc.

Current local cache includes `agent-wiki`, `llm-wiki`, `llm-wiki-agent`, `llm-wiki-compiler`, `nashsu-llm_wiki`, and `obsidian-llm-wiki-local`.

## Acceptance Criteria

- Existing queue MVP behavior remains backward-compatible.
- Queue lifecycle transitions are atomic and stay within the Snowiki root.
- Queue apply reuses existing reviewed apply validation and rebuild integrity checks.
- Auto-apply cannot be triggered solely by agent-provided impact labels.
- Queue pruning is dry-run-first; terminal deletion requires explicit operator intent.
- MCP remains read-only in docs and code.
- README and skill docs are updated only for shipped CLI behavior.

## Verification Plan

Before any implementation PR:

```bash
uv run ruff check src/snowiki tests
uv run ty check
uv run pytest
uv run pytest -m integration
```

Target tests:

- unit tests for state path construction and transition envelope validation
- integration tests for `queue show`, `queue apply`, `queue reject`, and `queue list --status`
- regression tests for root mismatch and proposal tampering
- tests proving queue artifacts do not affect rebuild/query until applied
- tests proving unsupported/high-impact proposals remain queued under auto-apply policy

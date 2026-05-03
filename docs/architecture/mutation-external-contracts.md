# Phase 6 Mutation External Contract Ledger

## Purpose

Phase 6 may aggressively redesign Snowiki's mutation domain internals. This ledger records the external contracts that must remain stable while that redesign happens.

Only user- and agent-visible behavior is preserved here: CLI commands and options, JSON envelopes, exit behavior, stdout/stderr posture, durable storage effects, destructive safety confirmations, and reviewed fileback writes. Function names, helper locations, call graphs, and legacy module boundaries are intentionally not part of this contract.

## Contract scope

Preserved external surfaces:

- CLI command names, subcommands, required arguments, and documented safety options.
- Machine-readable JSON envelope shapes emitted by `--output json` or `SNOWIKI_OUTPUT=json`.
- Successful mutation results on stdout with exit code `0`.
- Runtime failures as JSON errors on stdout for JSON mode, with non-zero exit codes.
- Human-mode runtime failures on stderr.
- Durable storage compatibility for accepted Snowiki zones: `raw/`, `normalized/`, `compiled/`, `index/`, and `queue/`.
- Fail-closed destructive deletion and reviewed-write gates.

Non-contract surfaces:

- Python function signatures, imports, class names, helper names, and module ownership.
- Exact private implementation sequencing except where an externally visible write, rebuild, queue transition, or safety gate depends on it.
- Legacy unit tests that assert internal structure rather than runtime behavior.

## Shared CLI JSON envelope

Mutation commands that support JSON output use the standard Snowiki envelope family:

| Outcome | Envelope | Exit behavior | Stream |
| :--- | :--- | :--- | :--- |
| Successful command | `{"ok": true, "command": string, "result": object}` | `0` | stdout |
| Runtime failure | `{"ok": false, "error": {"code": string, "message": string, "details"?: object}}` | non-zero | stdout in JSON mode |

Rationale: agents and scripts need one stable machine contract across mutation commands. Command-specific result payloads may evolve, but the envelope must remain predictable.

## Ingest contracts

### `snowiki ingest <path>`

Preserved behavior:

- Accepts a Markdown file or directory path.
- Supports `--source-root`, `--rebuild`, `--root`, and `--output [human|json]`.
- Honors `SNOWIKI_ROOT` for runtime storage and `SNOWIKI_OUTPUT=json` for machine output.
- On success with JSON output, emits `command: "ingest"` and `ok: true`.
- Records accepted Markdown into Snowiki-managed `raw/markdown/` and `normalized/markdown/` storage.
- Reports document counts, per-document paths, source identity, stale-document count, and whether rebuild remains required.
- Without `--rebuild`, accepted documents make `rebuild_required` true when documents were seen.
- With `--rebuild`, derived `compiled/` and `index/manifest.json` state is refreshed and `rebuild_required` becomes false.
- Missing, non-Markdown, or privacy-blocked inputs fail with `ok: false` and a non-zero exit code.

Rationale: ingest is the durable entry path for external evidence. Phase 6 may move orchestration behind a mutation service, but the CLI and storage result must remain stable for users, skills, and downstream tooling.

## Fileback contracts

### `snowiki fileback preview <question>`

Preserved behavior:

- Supports `--answer-markdown`, `--summary`, repeated `--evidence-path`, optional `--queue`, `--root`, and `--output [human|json]`.
- Emits `command: "fileback preview"` and `ok: true` on success.
- Produces a reviewable proposal with a stable proposal version, draft, target compiled path, evidence resolution, derivation metadata, and apply plan.
- Exposes the proposed raw-note body and normalized-record payload without applying them.
- Preview without `--queue` is non-mutating: it must not create raw, normalized, compiled, index, or queue artifacts.
- Preview with `--queue` persists only pending proposal control-plane state under `queue/proposals/pending/`; queued proposals are not accepted memory and do not affect rebuild/query results until applied.

Rationale: fileback must remain proposal-first so agents can prepare durable knowledge edits without silently mutating accepted memory.

### `snowiki fileback queue ...`

Preserved behavior:

- `snowiki fileback queue list` supports `--root` and `--output [human|json]`, emits `command: "fileback queue list"`, and reports pending proposal metadata without applying or rejecting anything.
- `snowiki fileback queue show <proposal-id>` supports `--verbose`, `--root`, and `--output [human|json]`; the default output reports metadata, while `--verbose` includes the reviewed proposal payload for inspection.
- `snowiki fileback queue apply <proposal-id>` applies a pending reviewed proposal through the same reviewed-write safety path as `fileback apply`, rebuilds accepted state on success, and deletes the pending queue artifact only after the apply succeeds.
- `snowiki fileback queue reject <proposal-id> --reason <text>` deletes the pending queue artifact with a human-readable rejection reason and does not write accepted raw, normalized, compiled, or index state.
- Queue command failures use JSON error envelopes in JSON mode with fileback-queue-specific error codes and non-zero exits.

Rationale: queued fileback proposals are external control-plane state. Agents rely on queue list/show/apply/reject to separate pending intent from accepted memory and to avoid losing pending proposals before a successful write.

### `snowiki fileback apply --proposal-file <json>`

Preserved behavior:

- Requires a reviewed preview payload or direct proposal JSON file.
- Fails closed with `ok: false`, code `fileback_apply_failed`, and non-zero exit when the payload is malformed, for the wrong command, for the wrong root, unsupported, replayed, or tampered.
- Does not write raw or normalized fileback artifacts when validation fails.
- On success, writes the proposed raw note and normalized question record, rebuilds compiled/index state, and emits `command: "fileback apply"`.

Rationale: reviewed-write safety is a core external guarantee. Internal validation may move, but unsafe or unreviewed fileback writes must not become durable memory.

## Prune contracts

### `snowiki prune sources --dry-run`

Preserved behavior:

- Supports `--dry-run`, `--delete`, `--yes`, `--all-candidates`, `--root`, and `--output [human|json]`.
- Emits `command: "prune sources"` and `ok: true` on success.
- Reports missing-source candidates and candidate counts.
- Is non-destructive: `deleted_count` remains `0`, no tombstone is written, and candidate `raw/` and `normalized/` files remain on disk.

Rationale: source cleanup must be inspectable before deletion because it removes accepted runtime artifacts.

### `snowiki prune sources --delete`

Preserved behavior:

- `--delete` is fail-closed unless both `--yes` and `--all-candidates` are supplied.
- Missing confirmation flags fail with `ok: false`, code `prune_confirmation_required`, and non-zero exit.
- Failed confirmation does not initialize or delete Snowiki storage artifacts.
- Confirmed deletion removes reported candidates, writes `index/source-prune-tombstones.json`, and rebuilds derived state when anything was deleted.

Rationale: destructive maintenance must require explicit intent and leave an auditable tombstone when deletion succeeds.

## Rebuild contracts

### `snowiki rebuild`

Preserved behavior:

- Supports `--root` and `--output [human|json]`.
- Emits `command: "rebuild"` and `ok: true` on success.
- Recomputes compiled pages from accepted normalized memory.
- Writes a consistent `index/manifest.json` whose content identity matches the current runtime state.
- Refreshes runtime-visible search state so queries after a rebuild observe newly accepted content rather than stale pre-rebuild content.
- Fails closed with `ok: false`, code `rebuild_failed`, and non-zero exit if freshness changes before integrity can be confirmed.

Rationale: rebuild is the authoritative path for derived wiki memory. Phase 6 may re-home finalization, cache clearing, and manifest writing, but callers must still observe one coherent rebuilt state.

## Storage compatibility contracts

Mutation commands may reorganize implementation code, but accepted storage remains externally meaningful by zone:

- `raw/`: provenance-preserving snapshots and reviewed fileback raw notes.
- `normalized/`: typed accepted records consumed by rebuild, status, lint, query, and recall.
- `compiled/`: generated wiki pages; rebuildable and not source truth.
- `index/`: rebuildable retrieval and manifest state, including prune tombstones when deletion succeeds.
- `queue/`: pending control-plane proposals, not accepted memory.

Any future storage schema change requires an explicit migration contract rather than an incidental Phase 6 refactor side effect.

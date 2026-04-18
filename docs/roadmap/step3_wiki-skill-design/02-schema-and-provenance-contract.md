# Sub-step B: Schema and Provenance Contract

## Purpose

This document is the canonical owner of the current `/wiki` route-adjacent schema, provenance, display, error-envelope, and reviewable-write contract.

It sits directly on top of `01-wiki-route-contract.md`, which remains the canonical owner of the route taxonomy, route names, and current-vs-deferred status. This document treats that route taxonomy as fixed input and defines only the machine-readable contract and display/provenance rules for the currently shipped routes.

This document does **not** own route taxonomy, governance implementation, maintenance loop design, benchmark methodology, tokenizer selection, sparse-branch proof, or runtime promotion.

## In Scope

- Machine-readable contract truth for the current `/wiki` routes already fixed in `01-wiki-route-contract.md`.
- Shared semantics that must stay aligned across CLI JSON, read-only MCP, and fileback proposal/apply artifacts.
- Provenance and display minimums for current retrieval, ingest, health, and reviewed-write surfaces.
- Error and failure envelope boundaries for CLI JSON, MCP tool/resource responses, and reviewed-write validation.

## Out of Scope

- Changing route names, buckets, or current-vs-deferred status.
- Designing governance implementation or a broader governance suite.
- Defining maintenance loop design or workflow sequencing.
- Reopening benchmark methodology, tokenizer selection, sparse-branch proof, or runtime promotion.

## Owns

- The canonical interpretation of schema/provenance truth across the current CLI, MCP, and fileback surfaces.
- Route-level input/output minimums for the current shipped routes.
- Transport-specific wrapper distinctions where multiple surfaces express overlapping semantics.

## Does Not Own

- Route taxonomy or route naming.
- Host-specific governance workflows.
- Mutation orchestration beyond the reviewed-write payload contract.

## Contract Truth Surfaces

This document is the canonical owner of the contract interpretation below, but the shipped runtime files named here remain the authoritative implementation surfaces that the contract must describe accurately.

| Surface | Canonical runtime owner | Contract role |
| :--- | :--- | :--- |
| Current `/wiki` route set and current-vs-deferred split | `docs/roadmap/step3_wiki-skill-design/01-wiki-route-contract.md` | Fixed route taxonomy input for this document. |
| CLI JSON success/error envelope | `src/snowiki/cli/output.py` | Owns the top-level CLI `ok`/`command`/`result` success wrapper and `ok`/`error` failure wrapper. |
| CLI command payload exemplars | `src/snowiki/cli/commands/query.py`, `recall.py`, `status.py`, `lint.py`, `ingest.py`, `fileback.py` | Own the current route-level result payload shapes. |
| Read-only MCP tool/resource transport | `src/snowiki/mcp/server.py` | Owns the MCP `structuredContent`, text `content`, resource `contents`, and MCP JSON-RPC error framing. |
| Reviewed-write proposal/apply payload contract | `src/snowiki/fileback.py` | Owns the fileback proposal object, apply invariants, evidence resolution, and derived-write payload semantics. |
| Retrieval parity and freshness vocabulary | `docs/architecture/current-retrieval-architecture.md` | Defines metadata parity, freshness identity, and evaluation-boundary vocabulary that this contract must preserve. |
| CLI-first / read-only-MCP policy vocabulary | `docs/architecture/skill-and-agent-interface-contract.md` | Defines the policy boundary that mutation stays CLI-mediated and MCP remains read-only. |

Normative interpretation rule: when these sources differ in transport shape, this document treats the semantic concept as shared only when the runtime actually shares it. It does not collapse unlike wrappers into a single fake schema.

## Shared Semantics vs Transport Wrappers

Shared semantics are the stable facts a caller may rely on across surfaces. Transport wrappers are the delivery-specific envelopes that carry those facts.

**CLI JSON and MCP payloads are not identical.** Current parity is semantic where the runtime overlaps, not structural parity at the outer envelope level.

| Semantic unit | Shared meaning | CLI JSON wrapper | MCP tool wrapper | MCP resource wrapper | Fileback reviewed-write artifact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Command success | The operation succeeded and returned a result payload. | `{"ok": true, "command": <name>, "result": <payload>}` | `{"structuredContent": <payload>, "content": [{"type": "text", "text": <json>}]} ` | Not used; resources return `contents`. | Preview may be wrapped in the CLI success envelope; apply consumes either that reviewed preview payload or a direct proposal object. |
| Read result payload | The route-specific machine-readable result. | Lives inside `result`. | Lives inside `structuredContent`; the text `content` is a JSON rendering of the same structured payload. | Lives as JSON text inside `contents[].text` with `mimeType` and `uri`. | Lives as the direct proposal object or as the `result.proposal` member of the preview envelope. |
| Retrieval hit | A search/recall item naming the underlying record/page plus display metadata. | Query/recall hits are route-specific lists inside `result.hits`. | Search/recall hits live inside `structuredContent.hits`. | Resource reads do not use hit arrays; they return graph/topic/session objects. | Evidence records supporting write review are named separately, not as retrieval hits. |
| Provenance-bearing evidence | The source path/identity chain supporting a result or proposed write. | Ingest returns `raw_ref`; status returns freshness identities; fileback preview/apply return evidence and raw refs. | MCP search/recall hits include path, metadata, recorded time, and source type when available. | Session/topic/graph resources preserve the resource `uri` and JSON payload. | Proposal/apply payloads preserve requested evidence paths, resolved paths, supporting record ids, supporting raw refs, derivation, and apply-plan invariants. |
| Failure | The request was rejected, invalid, or unsupported. | Usually `{"ok": false, "error": {...}}`; `lint` is the shipped exception described below. | Tool errors return `isError: true`, a text message, and `structuredContent.error`. | Resource errors return a `contents` JSON text payload containing `error` and `uri`. | Preview/apply validation failures are reported through the CLI error envelope, not by mutating the proposal schema. |

Progressive disclosure rule: human-readable renderers and text mirrors are support surfaces for review and host compatibility. The machine-readable payload is the contract truth for automation.

## Current Route-Level Input and Output Contract

The current route set is owned by `01-wiki-route-contract.md`. The tables below define the schema minimums for those already-approved current routes without reopening route status or route naming.

### Current CLI route payload minimums

| Current route | Machine-readable input minimum | Machine-readable success output minimum |
| :--- | :--- | :--- |
| `ingest` | Positional source file `path`; required `--source` of `claude` or `opencode`; optional `--root`; optional `--output json`. | CLI success envelope with `command: "ingest"` and `result` containing `source`, `root`, `session_id`, `raw_ref`, `records_written`, and `written_paths`. `raw_ref` must carry `sha256`, `path`, `size`, and `mtime`. |
| `query` | Positional query string; optional `--mode` (`lexical` or compatibility `hybrid`); optional `--top-k`; optional `--root`; optional `--output json`. | CLI success envelope with `command: "query"` and `result` containing `query`, `mode`, `semantic_backend`, `records_indexed`, `pages_indexed`, and `hits`. Each hit currently includes `id`, `path`, `title`, `kind`, `source_type`, `score`, `matched_terms`, and `summary`. |
| `recall` | Positional target string; optional `--root`; optional `--output json`. | CLI success envelope with `command: "recall"` and `result` containing `target`, `strategy`, and `hits`. Each hit currently includes `id`, `path`, `title`, `kind`, `score`, and `summary`. The current CLI recall payload does not claim full query-hit parity and does not currently emit `source_type`. |
| `status` | Optional `--root`; optional `--output json`. | CLI success envelope with `command: "status"` and `result` containing `root`, `pages`, `sources`, `lint`, `freshness`, `manifest`, and `candidate_matrix`. `freshness` is a contract-bearing diagnostics object, not display-only text. |
| `lint` | Optional `--root`; optional `--output json`. | On healthy runs, CLI success envelope with `command: "lint"` and `result` containing `root`, `summary`, `issues`, and `error_count` through the lint result payload. On validation failures, see the failure rules below; the route still returns a route-shaped payload rather than the generic CLI `error` object. |
| `fileback preview` | Positional `question`; required `--answer-markdown`; required `--summary`; one or more `--evidence-path`; optional `--root`; optional `--output json`. | CLI success envelope with `command: "fileback preview"` and `result` containing `root`, `proposal`, and `proposed_write`. `proposal` must contain `proposal_id`, `proposal_version`, `created_at`, `target`, `draft`, `evidence`, `derivation`, and `apply_plan`. `proposed_write` must expose `raw_note_body` and `normalized_record_payload` for review. |
| `fileback apply` | Required `--proposal-file`; optional `--root`; optional `--output json`. The proposal file may be either a successful preview envelope or a direct proposal object. | CLI success envelope with `command: "fileback apply"` and `result` containing `root`, `applied_at`, `proposal_id`, `proposal_version`, `raw_ref`, `supporting_raw_ref_count`, `normalized_path`, `compiled_path`, and `rebuild`. |

### Current read-only MCP transport minimums

The current MCP surface is a read-only transport wrapper. It overlaps semantically with some CLI read routes, but it is not the owner of route taxonomy and it is not a write path.

| MCP surface | Current contract minimum |
| :--- | :--- |
| Tools | The server exposes only `search`, `recall`, `get_page`, and `resolve_links`. Successful tool calls return `structuredContent` plus a JSON text mirror in `content`. `search` and `recall` hits currently include `id`, `kind`, `matched_terms`, `metadata`, `path`, `recorded_at`, `score`, `source_type`, `summary`, and `title`. |
| Resources | The server exposes only `graph://current`, `topic://<slug>`, and `session://<session-id>`. Successful resource reads return `contents` entries with `mimeType: "application/json"`, JSON text, and the originating `uri`. Topic resources currently expose `path`, `slug`, `summary`, and `title`; session resources return the normalized session payload; graph resources return `nodes` and `edges`. |
| Capability boundary | Write-oriented names such as `edit`, `ingest`, `merge`, `status`, `sync`, and `write` are rejected as read-only violations rather than approximated. Bridge startup and transport hydration do not imply CLI-root loading or mutation capability. |

## Provenance and Display Rules

### Provenance minimums

The current contract requires route outputs to preserve provenance-bearing minimums appropriate to what the route actually does.

- **Ingest** must identify the ingested source via `source`, `session_id` when available, `written_paths`, and a `raw_ref` carrying at least `sha256`, `path`, `size`, and `mtime`.
- **Query** must expose retrieval identity and display minimums per hit: `id`, `path`, `title`, `kind`, `source_type`, `score`, `matched_terms`, and `summary`.
- **Recall** must expose `strategy` plus hit identity/display minimums: `id`, `path`, `title`, `kind`, `score`, and `summary`. The current CLI recall contract does not claim the full query hit shape; when another transport includes extra provenance-bearing fields such as `source_type`, `metadata`, or `recorded_at`, those are additive transport facts, not proof that all transports are identical.
- **Status** must surface freshness identity explicitly rather than hiding it in prose. At minimum, `freshness` must expose `status`, `manifest_content_identity`, `current_content_identity`, `latest_normalized_recorded_at`, and `latest_compiled_update`.
- **Lint** issues must remain attributable. Current issue payloads must include at least `code`, `message`, `path`, and `severity` inside the lint result payload.
- **Fileback preview** must preserve evidence provenance through `requested_paths`, `resolved_paths`, `supporting_record_ids`, `supporting_raw_refs`, and a `derivation` object that states the write is synthesized and reviewed rather than raw-authored.
- **Fileback apply** must preserve the resulting manual raw note as `raw_ref` and report the scope of inherited evidence via `supporting_raw_ref_count`, `normalized_path`, `compiled_path`, and `rebuild` output.

### Display rules

- Machine-readable JSON is authoritative for automation; human renderers are informative display layers.
- Human-readable output may summarize or reorder for readability, but it must not invent fields or silently widen capability claims.
- CLI JSON output is intentionally stable and sorted at serialization time.
- MCP tool responses intentionally duplicate structured JSON as text content for host compatibility and review, but `structuredContent` remains the machine-facing truth.
- MCP resources intentionally expose JSON text inside `contents`; callers must not assume a CLI-style `result` envelope is present.
- Fileback preview intentionally includes both the canonical proposal object and the proposed raw/normalized write bodies so a reviewer can inspect the exact reviewed-write payload before apply.

## Error and Failure Envelope Rules

Failure handling is transport-specific and must remain explicit.

### CLI failures

- The generic CLI failure envelope is `{"ok": false, "error": {"code": <string>, "message": <string>, "details"?: <object>}}`.
- `query`, `recall`, `status`, `ingest`, `fileback preview`, and `fileback apply` currently use this error envelope for operational failure.
- Current route-specific error codes include `query_failed`, `recall_failed`, `status_failed`, `ingest_failed`, `privacy_blocked`, `unexpected_error`, `fileback_preview_failed`, and `fileback_apply_failed`.
- `details` are route-specific and additive. For example, `query` and `ingest` currently attach request context such as the input query/path/source.

### CLI validation-failure exception: `lint`

`lint` is the current shipped exception to the generic failure envelope. When lint finds issues, it emits a route-shaped payload `{"ok": false, "command": "lint", "result": ...}` and exits non-zero. This means:

- `ok: false` does not always imply the presence of a top-level `error` object.
- Domain validation failure may still be expressed as a normal route result payload.
- Callers must distinguish transport failure from a successful lint execution that found actionable issues.

### MCP failures

- MCP tool-level semantic failures return `isError: true`, a text message in `content`, and `structuredContent` containing `{"error": <message>}`.
- MCP resource failures return `contents` with a JSON text payload containing `error` and `uri`.
- MCP protocol/request failures use the outer JSON-RPC `error` object with numeric codes such as invalid request, invalid params, or method not found.
- Unsupported write-oriented MCP tool names must fail closed as read-only violations; they must not fall through to CLI mutation behavior.

### Reviewed-write failures

- Preview/apply schema validation failures are surfaced through the CLI error envelope, not by writing partial artifacts.
- Apply must fail if the reviewed payload root does not match the apply root, if `proposal_version` is unsupported, if the target derived from the reviewed question no longer matches, or if the reviewed `apply_plan` no longer matches the recomputed proposed write set.
- Evidence paths must fail closed when they leave the workspace root, do not exist, are not files, or are not under `raw/`, `normalized/`, or `compiled/`.

## Reviewable Write Contract

The current reviewed-write contract is the CLI-mediated `fileback` surface. This section defines payload boundaries, not workflow sequencing.

- **Only current write path**: reviewed durable writes flow through `fileback preview` and `fileback apply`. Mutation does not flow through MCP.
- **Preview is non-mutating**: `build_fileback_proposal()` constructs a review object without mutating workspace state.
- **Direct proposal vs reviewed preview envelope**: `apply` accepts either a direct `FilebackProposal` object or a successful preview envelope whose `result.proposal` contains that same object. The underlying proposal schema is the same either way.
- **Proposal identity**: a proposal must carry `proposal_id`, `proposal_version`, and `created_at`. The current shipped `proposal_version` is `1`.
- **Target contract**: `target` must carry `title`, `slug`, and `compiled_path`. `apply` recomputes this target from the reviewed question and rejects drift.
- **Draft contract**: `draft` must carry non-empty `question`, `answer_markdown`, and `summary`.
- **Evidence contract**: `evidence` must carry the originally `requested_paths`, the resolved per-zone path lists, `supporting_record_ids`, and `supporting_raw_refs`. Evidence paths are constrained to existing files under the workspace `raw/`, `normalized/`, and `compiled/` zones.
- **Derivation contract**: the proposal and normalized record must declare the write as derived/synthesized, preserve the reviewed-proposal identity, and keep supporting sources as evidence rather than as claimed direct raw authorship.
- **Apply-plan contract**: `apply_plan` must name `source_type`, `record_type`, `record_id`, `raw_note_path`, `normalized_path`, `proposed_raw_note_body`, `proposed_normalized_record_payload`, and `rebuild_required`. `apply` validates this object for exact equality against the recomputed write set.
- **Apply result contract**: a successful apply must report the created manual raw-note `raw_ref`, the resulting `normalized_path`, the target `compiled_path`, and rebuild output. This is the current durable confirmation surface for reviewed writes.

Contract boundary: this document defines the current reviewed-write payload semantics and invariants. It does not define approval UX, governance implementation, or maintenance-loop choreography.

## Related Documents

- [Wiki Route Contract](01-wiki-route-contract.md)
- [Skill and Agent Interface Contract](../../architecture/skill-and-agent-interface-contract.md)
- [Current Retrieval Architecture](../../architecture/current-retrieval-architecture.md)

## Reference Reading

- `docs/reference/research/claude-skill-authoring-guide.md` for schema-first packaging, progressive disclosure, and reviewable-write posture.
- `docs/roadmap/external/claude-skills/official-guidance-notes.md` for the authoritative progressive-disclosure and supporting-file model.

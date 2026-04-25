# Wiki Contract Phase 4 Plan: Source Freshness, Navigation Artifacts, and Prune

Status: **active implementation plan for `feat/phase4-wiki-contract`**. This is the first executable plan for Phase 4 and should be updated until the implementation PR merges. After merge, durable outcomes should be folded back into `docs/architecture/llm-wiki-ingest-redesign.md` and this plan should be removed.

## Summary

Phase 4 turns Snowiki from a Markdown-first ingest/rebuild runtime into a maintainable compiled wiki. The goal is not just to detect stale sources. The goal is to make Snowiki's generated knowledge artifact inspectable, navigable, and safely gardenable by humans and agents.

Karpathy-style LLM wiki references use a small, durable loop:

```text
raw sources -> compiled wiki pages -> index/log/schema -> lint/status/gardening
```

Snowiki should preserve that shape while keeping its stronger CLI/runtime boundaries:

- raw/normalized records remain source truth and provenance truth;
- compiled Markdown remains derived and reproducible;
- `index.md`, `log.md`, and `overview.md` become generated navigation/control artifacts;
- stale/missing source state is reported before any cleanup;
- cleanup is explicit, dry-run-first, and auditable;
- MCP remains read-only and mutation remains CLI-mediated.

## References Checked

Local references were preferred before web research:

- `docs/reference/external/karpathy-llm-wiki-NOTES.md`
- `docs/reference/llm-wiki-implementation-survey.md`
- `docs/reference/external/seCall-NOTES.md`
- `/home/k/local/seCall/crates/secall-core/src/vault/index.rs`
- `/home/k/local/seCall/crates/secall-core/src/vault/log.rs`
- `/home/k/local/seCall/crates/secall-core/src/ingest/lint.rs`
- `/home/k/local/seCall/crates/secall/src/commands/status.rs`
- `/home/k/local/llm-wiki-references/nashsu-llm_wiki/llm-wiki.md`
- `/home/k/local/llm-wiki-references/llm-wiki/src/llm_wiki/templates/index.md`
- `/home/k/local/llm-wiki-references/llm-wiki/src/llm_wiki/templates/log.md`

Transferable patterns:

- Karpathy-style wikis keep `index.md` as navigation, `log.md` as chronological operations, and `overview.md` as living synthesis.
- seCall's vault model creates `index.md`, `log.md`, `SCHEMA.md`, and `wiki/overview.md` idempotently, and uses structured lint codes for bidirectional vault/DB consistency.
- nashsu-style references emphasize SHA/content-hash identity, source traceability, structural wikilink cleanup, and explicit cascade cleanup.
- dbt/MkDocs/Terraform/Git-style maintenance workflows report first and keep destructive cleanup explicit.

Patterns to avoid:

- Do not update `index.md` by brittle string insertion. Use deterministic template regeneration or structural section replacement.
- Do not let `log.md` become an opaque event store in Phase 4. Generate a parseable operation summary from durable runtime state first.
- Do not infer deletion from a missing live source file alone.
- Do not collapse status, lint, generation, and deletion into one opaque command.

## Final Phase 4 Decisions

### Scope

Phase 4 includes:

1. source freshness report for Markdown source records;
2. status summary and lint issues for source freshness;
3. generated `compiled/index.md`, `compiled/log.md`, and strengthened `compiled/overview.md` contract;
4. explicit source prune/cleanup dry-run and delete path;
5. architecture docs and tests for the above.

Phase 4 excludes:

- MCP write/delete;
- semantic/vector/hybrid retrieval expansion;
- `sync`, `edit`, and `merge` workflows;
- legacy Claude/OpenCode direct ingest restoration;
- automatic cascade deletion during ingest or rebuild;
- full append-only event sourcing.

### Explicit Carry-Forward Items

The following items are intentionally **not** part of Phase 4 implementation. They must stay visible here and in the long-running architecture ledger so that they are not lost when this executable plan is removed after merge.

| Future item | Target phase / track | Why not Phase 4 |
| :--- | :--- | :--- |
| Full append-only runtime event journal | Later event-log design | Phase 4 `log.md` is generated from durable state; a true event store needs ordering, retention, replay, and corruption semantics. |
| Source move/rename workflow | Phase 5 gardening workflow | Requires identity reconciliation and review UX beyond modified/missing/untracked detection. |
| Multi-source cascade cleanup | Phase 5 gardening workflow | Safe removal from shared generated pages requires structural source-reference editing and stronger tests. |
| Dead wikilink cleanup | Phase 5 gardening workflow | Must use structural wikilink parsing; should not be bolted onto source freshness. |
| Reviewable cleanup proposals | Phase 5 or writeback extension | Cleanup can use fileback-like review semantics later; Phase 4 only ships explicit CLI prune. |
| Persistent freshness/prune policy config | Later config design | Existing config policy is not broad enough; keep Phase 4 defaults explicit and CLI-owned. |
| Projection backfill/migration | Separate migration spec | Old projection-less records must not regain hidden compatibility through Phase 4. |
| Normalized storage write-contract redesign | Separate storage spec | Phase 4 reads existing normalized records and adds reporting/prune; it should not redesign storage layout. |
| `sync`, `edit`, `merge` commands | Agent/workflow phases | These are higher-level workflows over stable CLI primitives, not Phase 4 runtime truth. |
| MCP write/delete | Post-CLI-write-contract phase | Mutation stays CLI-mediated until write contracts prove stable. |
| Semantic/vector/hybrid retrieval expansion | Retrieval roadmap | Phase 4 is wiki maintenance/gardening, not retrieval expansion. |

Implementation PRs for Phase 4 must preserve these boundaries. If any item becomes required during implementation, update this table and the affected architecture ledger before broadening scope.

### Source Freshness States

Snowiki runtime, not an agent, owns source freshness classification.

| State | Meaning | Default severity | Recommended action |
| :--- | :--- | :--- | :--- |
| `current` | Source file exists and current content hash matches normalized record. | none | `none` |
| `modified` | Source file exists but current content hash differs from normalized record. | warning | `reingest` |
| `missing` | Normalized Markdown record points at a source path that no longer exists. | warning | `review_prune` |
| `untracked` | Source root contains a Markdown file with no normalized record. | info | `ingest` |

`content_hash` is the authoritative correctness signal. `mtime` and file size may be used later as cache hints, but they must not be the durable truth. This follows standard cache invalidation practice: cheap metadata can identify candidates, but hash comparison determines freshness.

### Source Freshness Report Schema

The shared report item shape should be stable across `status`, `lint`, and future prune flows:

```json
{
  "state": "modified",
  "severity": "warning",
  "recommended_action": "reingest",
  "record_id": "markdown-document-...",
  "source_root": "/abs/source/root",
  "relative_path": "notes/topic.md",
  "source_path": "/abs/source/root/notes/topic.md",
  "normalized_path": "normalized/markdown/documents/....json",
  "compiled_paths": ["compiled/summaries/topic.md"],
  "stored_content_hash": "...",
  "current_content_hash": "..."
}
```

Rules:

- `current_content_hash` is omitted or `null` for `missing`.
- `record_id` and `normalized_path` are omitted or `null` for `untracked`.
- Paths in JSON output remain POSIX-style strings.
- The schema should be generated by a shared domain module, not hand-built separately in Click callbacks.

### CLI Surface

Status should provide a dashboard summary:

```json
{
  "sources": {
    "total": 120,
    "by_type": {"markdown": 120},
    "freshness": {
      "current": 113,
      "modified": 4,
      "missing": 2,
      "untracked": 1
    }
  }
}
```

Lint should provide actionable issues:

```json
{
  "code": "source.modified",
  "check": "source.freshness",
  "severity": "warning",
  "path": "notes/topic.md",
  "message": "source file has changed since ingest",
  "target": "/abs/source/root/notes/topic.md"
}
```

Ingest may continue reporting `documents_stale`, but `status`/`lint` own the canonical cross-run freshness report. `documents_stale` should count stale records only within the scope of the source roots involved in the current ingest operation.

### Prune / Cleanup Surface

The Phase 4 prune command should be explicit and dry-run-first:

```text
snowiki prune sources --dry-run --output json
snowiki prune sources --delete --yes --output json
```

Decision: use **`snowiki prune sources`** rather than `cleanup sources` because it matches the existing `fileback queue prune` safety vocabulary.

Prune scope:

- produce candidates for missing-source normalized Markdown records;
- produce candidates for compiled pages that are single-source and derive only from pruned identities;
- produce candidates for raw snapshots no longer referenced by any normalized provenance;
- update generated navigation artifacts after deletion;
- preserve audit evidence through tombstone or archive records.

Safety rules:

- dry-run is the default;
- deletion requires `--delete --yes`;
- pruning requires explicit source identity selection or an explicit all-candidates confirmation;
- rebuild/ingest must not silently cascade delete;
- multi-source generated pages must not be deleted until tests prove source removal can update `sources[]` structurally;
- cleanup must be structural, not substring-based.

### Navigation Artifact Contracts

#### `compiled/index.md`

Role: generated catalog and navigation entrypoint.

Content:

- total compiled pages;
- page counts by type;
- links grouped by page type;
- source freshness summary;
- pointers to `overview.md`, `log.md`, and key generated pages.

Contract:

- deterministic regeneration on rebuild;
- no long-form synthesis;
- generated frontmatter marks it as Snowiki-managed.

#### `compiled/log.md`

Role: generated chronological operation summary, not a full event-sourcing store.

Initial data source:

- normalized record `recorded_at` values;
- fileback result metadata when available;
- rebuild manifest metadata when available.

Format:

```markdown
## [YYYY-MM-DD] ingest | notes/topic.md
- record_id: markdown-document-...
- source: notes/topic.md
- action: inserted|updated|unchanged|modified|missing|pruned
```

Contract:

- parseable `## [` headings;
- deterministic ordering;
- no hidden append-only runtime log requirement in Phase 4.

#### `compiled/overview.md`

Role: living synthesis / dashboard of the current compiled wiki state.

Phase 4 changes:

- retain existing overview generation;
- document generated frontmatter expectations;
- include source freshness summary when available;
- do not make overview the source of truth for stale state.

### Frontmatter Contract

User-authored Markdown source frontmatter:

- preserve safe fields already recognized by ingest;
- reserved Snowiki fields must not override runtime provenance;
- malformed or unsupported frontmatter must fail deterministically rather than silently redefining source identity.

Snowiki-managed compiled frontmatter:

- must include generated-page identity (`title`, `type`, `created`, `updated`, `summary`, `sources`, `related`, `tags`, `record_ids` where applicable);
- must distinguish generated catalog/log/overview pages from source-derived summary pages;
- must retain provenance links to normalized records and raw/source identities where possible.

## Implementation Plan

### Step 1: Source Freshness Domain Module

Add a domain module, likely `src/snowiki/source_freshness.py` or `src/snowiki/sources/freshness.py`, that:

- loads normalized Markdown document records;
- extracts `source_root`, `relative_path`, `source_path`, `content_hash`, and record paths;
- hashes live source files for known `source_path` values;
- optionally scans known source roots for untracked Markdown files;
- returns typed report items using the shared schema.

Tests:

- current source;
- modified source;
- missing source;
- untracked source under a known source root;
- out-of-root or malformed source metadata is reported, not trusted.

### Step 2: Status and Lint Wiring

Status:

- extend `src/snowiki/cli/commands/status.py` source summary with freshness counts;
- keep existing manifest freshness unchanged as search/index freshness.

Lint:

- add source freshness issues to `src/snowiki/lint/runtime.py`;
- introduce check code family such as `source.freshness` with issue codes:
  - `source.modified`;
  - `source.missing`;
  - `source.untracked`.

Tests:

- `tests/integration/cli/test_status.py`;
- `tests/integration/cli/test_lint.py`;
- unit tests for the freshness collector.

### Step 3: Ingest Stale Aggregate

Update `src/snowiki/markdown/ingest.py` so `documents_stale` is no longer hardcoded.

Rules:

- count stale/missing records within the source roots involved in the current ingest;
- do not prune or mutate stale records during ingest;
- keep per-document result status limited to current ingest inputs (`inserted`, `updated`, `unchanged`).

### Step 4: Navigation Generators

Add compiler generators for `index.md` and `log.md`, and strengthen the overview contract.

Likely files:

- `src/snowiki/compiler/generators/index.py`
- `src/snowiki/compiler/generators/log.py`
- `src/snowiki/compiler/generators/overview.py`
- `src/snowiki/compiler/engine.py`
- `src/snowiki/compiler/taxonomy.py`
- `src/snowiki/compiler/paths.py`

Tests:

- rebuild determinism includes `compiled/index.md` and `compiled/log.md`;
- generated frontmatter passes lint;
- no brittle string insertion.

### Step 5: `snowiki prune sources`

Add source prune planning and explicit deletion.

Likely files:

- `src/snowiki/prune.py` or `src/snowiki/sources/prune.py`
- `src/snowiki/cli/commands/prune.py`
- `src/snowiki/cli/main.py`

Behavior:

- dry-run default;
- `--delete --yes` required for deletion;
- JSON reports candidates and deleted paths;
- preserve tombstones or archives for pruned normalized records;
- do not delete multi-source generated pages in the first implementation unless source reference removal is structurally safe and tested.

Tests:

- dry-run does not delete;
- delete requires `--yes`;
- missing source candidate selection;
- raw snapshot reference safety;
- compiled single-source page cleanup;
- generated navigation artifacts regenerate after prune.

### Step 6: Docs and Skill Sync After Runtime Truth

After behavior ships:

- update `README.md` with new `status`/`lint` freshness and `prune sources` examples;
- update `skill/SKILL.md` and `skill/workflows/wiki.md` so agents read status/lint before gardening;
- update quickstart with source freshness and prune dry-run examples;
- fold final plan outcomes into `llm-wiki-ingest-redesign.md` and remove this executable plan.

### Step 7: Carry-Forward Ledger Sync

Before the Phase 4 PR opens:

- confirm every carry-forward item above appears in `docs/architecture/llm-wiki-ingest-redesign.md` under the correct future phase or open question;
- keep Phase 5 focused on gardening workflows over Phase 4 primitives, not raw implementation spillover;
- keep retrieval/MCP/storage migration items in their own tracks;
- remove or archive this executable plan only after the durable ledger has absorbed both shipped outcomes and deferred items.

## Acceptance Criteria

- `snowiki status --output json` exposes source freshness counts.
- `snowiki lint --output json` emits detailed source freshness issues.
- `documents_stale` is no longer a hardcoded zero.
- `compiled/index.md`, `compiled/log.md`, and `compiled/overview.md` have explicit, tested contracts.
- `snowiki prune sources` is dry-run-first and requires `--delete --yes` for deletion.
- Missing live source files never trigger implicit deletion during ingest or rebuild.
- Source freshness uses content hash as authoritative truth.
- Tests cover current/modified/missing/untracked source states.
- Tests cover navigation artifact generation determinism.
- Tests cover prune dry-run and destructive guards.
- Carry-forward items are explicitly preserved in the architecture ledger before this executable plan is removed.
- `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest` passes.
- `uv run pytest -m integration` passes before PR.

## Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Source-root scans become expensive. | Hash known source paths first; add untracked scans only for known source roots and keep results bounded. |
| Missing files cause accidental data loss. | Report missing first; require explicit prune source identity and `--delete --yes`. |
| `log.md` implies audit guarantees Snowiki cannot yet meet. | Treat Phase 4 `log.md` as generated operation summary, not durable event store. |
| `index.md` becomes stale or hand-edited. | Regenerate deterministically on rebuild and mark as Snowiki-managed. |
| Multi-source page cleanup deletes shared knowledge. | Do not delete multi-source pages until structural source-reference removal is implemented and tested. |

# Markdown Ingest Phase 1 Implementation Plan

This plan turns `docs/architecture/llm-wiki-ingest-redesign.md` into an executable PR scope. Keep that architecture ledger synchronized whenever implementation discovers a new decision, deferred item, or compatibility constraint.

## Summary

Phase 1 makes `snowiki ingest PATH` Markdown-first. The PR should replace the primary Claude/OpenCode ingest UX with deterministic Markdown file/directory ingest, copy source bytes into Snowiki raw storage, write latest-only normalized Markdown document records, rebuild summary pages when requested, and keep legacy normalized records readable by rebuild/query where feasible.

## In Scope

- `snowiki ingest <file-or-directory> [--source-root PATH] [--rebuild] [--output json]`.
- Markdown discovery for `.md` and `.markdown` files.
- Recursive directory ingest without following symlinks.
- Skipping hidden/internal directories including `.git`, `.venv`, `node_modules`, `raw`, `normalized`, `compiled`, and `index`.
- SHA-256 content hashing over copied Markdown bytes.
- Copy + provenance raw source storage under `raw/markdown/...`.
- Latest-only normalized records for `source_type: "markdown"`, `record_type: "document"`.
- Frontmatter preservation, safe promotion, and reserved field blocking.
- Summary-only compiled output for Markdown document records.
- Bounded summary slugs/paths for long Markdown titles or body-derived fallback titles.
- JSON output with aggregate counts and enough per-document detail for tests/callers.
- Compatibility: existing normalized Claude/OpenCode records remain readable by rebuild/query.
- Legacy Claude/OpenCode normalized records remain readable, but direct session-export write paths are removed from `snowiki ingest`.

## Out of Scope

- Automatic prune of removed source files.
- Cascade cleanup of compiled pages, indexes, or wikilinks.
- Concept/entity/topic/graph generation from Markdown documents.
- LLM summarization inside ingest or rebuild.
- Vector indexing, review queues, daemon behavior, or MCP writes.
- Visible or hidden CLI writes for Claude/OpenCode session exports through `snowiki ingest`.

## Implementation Waves

### Wave 1: Markdown Source Helpers

Files:

- `src/snowiki/markdown/__init__.py`
- `src/snowiki/markdown/frontmatter.py`
- `src/snowiki/markdown/discovery.py`
- tests under `tests/unit/markdown/`

Deliverables:

- Parse frontmatter/body deterministically.
- Preserve all parsed frontmatter.
- Split safe promoted fields from reserved blocked fields.
- Discover Markdown files with the Phase 1 safety policy.

Acceptance criteria:

- `.md` and `.markdown` are discovered.
- Non-Markdown files in directories are skipped.
- Symlink files/directories are skipped.
- Hidden/internal directories are skipped.
- Reserved frontmatter cannot override runtime fields.

### Wave 2: Raw and Normalized Storage

Files:

- `src/snowiki/storage/raw.py`
- `src/snowiki/storage/normalized.py`
- `src/snowiki/storage/provenance.py` if provenance metadata needs helper support
- tests under `tests/unit/storage/`

Deliverables:

- Store Markdown bytes through existing SHA-addressed raw storage with `source_type="markdown"`.
- Add latest-only Markdown document pathing that does not disturb legacy date-bucketed records.
- Create deterministic Markdown document IDs from canonical `source_root + relative_path`.
- Store normalized payload fields defined in the architecture ledger.

Acceptance criteria:

- First ingest reports inserted.
- Same hash reports unchanged.
- Changed content reports updated.
- Legacy `store_record()` date-bucketed behavior remains unchanged.

### Wave 3: CLI Contract

Files:

- `src/snowiki/cli/commands/ingest.py`
- `src/snowiki/cli/commands/rebuild.py` only if reusable helper extraction is needed
- `tests/integration/cli/test_ingest.py`

Deliverables:

- Make `path` accept files and directories.
- Remove required `--source` from the primary ingest path.
- Add `--source-root`.
- Add `--rebuild`.
- Emit the Phase 1 JSON result shape.
- Clear search caches after successful ingest/rebuild-impacting changes.

Acceptance criteria:

- `snowiki ingest note.md --output json` succeeds.
- `snowiki ingest docs/ --output json` succeeds recursively.
- `snowiki ingest docs/ --source-root docs --output json` uses stable relative paths.
- Missing paths and invalid single-file extensions fail with JSON errors.
- Claude/OpenCode session writes are no longer `snowiki ingest --source ...` behavior.

### Wave 4: Compiler Summary Projection

Files:

- `src/snowiki/compiler/paths.py`
- `src/snowiki/compiler/generators/summary.py`
- `src/snowiki/compiler/taxonomy.py` if helper extraction is needed
- compiler tests under `tests/unit/compiler/`

Deliverables:

- Markdown document records compile into summary pages.
- Summary pages include body/provenance/source identity without LLM summarization.
- Slugs are bounded to avoid filesystem filename limits.
- Existing legacy normalized records still compile.

Acceptance criteria:

- Long Markdown title/body fallback cannot create an overlong filename.
- Markdown summary page contains document body text and source provenance.
- Existing rebuild determinism tests still pass.

### Wave 5: Documentation and Verification

Files:

- `docs/architecture/llm-wiki-ingest-redesign.md`
- `docs/architecture/markdown-ingest-phase1-plan.md`
- `README.md` and skill-facing docs only after runtime behavior matches the new contract

Verification commands:

```bash
uv run ruff check src/snowiki tests
uv run ty check
uv run pytest
uv run pytest -m integration
```

PR readiness requires all commands above to pass, with integration tests run before opening the PR.

### Wave 6: Phase-End Consistency and Cleanup

Run this after functional implementation and before PR:

- Compare `llm-wiki-ingest-redesign.md`, this plan, implementation, and tests.
- Fix contract mismatches rather than deferring them silently.
- Add missing acceptance tests for help output, `--source-root`, non-Markdown errors, symlink safety, removed legacy source behavior, and Markdown summary semantics.
- Keep cleanup bounded to the Phase 1 boundary: module seams, naming, duplicated summary/body behavior, and legacy compatibility isolation.
- Record larger follow-up refactors in the deferred ledger instead of expanding this PR.
- Re-run lint, typecheck, default tests, and integration tests after the cleanup pass.

## Deferred Ledger

Keep these visible in `llm-wiki-ingest-redesign.md` until implemented:

- Phase 2: status/lint stale source report schema and source manifest comparison.
- Phase 2: generated-page frontmatter conventions for `index.md`, `log.md`, `overview.md`, and summary pages.
- Phase 3: explicit dry-run-first `--prune` or `snowiki prune`.
- Phase 3: pruning audit trail through tombstones or archive records.
- Phase 3+: cascade cleanup of generated pages, indexes, and dead wikilinks.
- Phase 4: Claude/OpenCode skills convert sessions to Markdown before ingest.
- Follow-up: if direct session-export writes are needed again, add explicit compatibility tooling outside the primary `snowiki ingest PATH` contract.
- Phase 5: graph/vector/MCP write extensions.
- Long-term: preserve CLI/JSON, normalized JSON, raw storage, and compiled Markdown as language-agnostic boundaries so performance-sensitive engine pieces can move to Rust later without changing ingest semantics.

## Commit Strategy

Recommended atomic commits:

1. `docs(ingest): finalize markdown phase 1 plan`
2. `feat(ingest): add markdown source parsing and discovery`
3. `feat(storage): add markdown document upsert path`
4. `feat(cli): make ingest markdown first`
5. `fix(compiler): bound summary slugs for markdown records`
6. `test(ingest): cover markdown first ingest contract`

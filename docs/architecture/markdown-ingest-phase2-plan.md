# Markdown Ingest Phase 2 Plan: Compiler Projection Boundary

This plan turns the post-Phase-1 refactor ledger into an executable Phase 2 scope. It supersedes the completed Phase 1 implementation plan and keeps `docs/architecture/llm-wiki-ingest-redesign.md` synchronized as the canonical architecture ledger.

## Summary

Phase 2 makes the compiler operate on a stable normalized projection contract instead of branching on source-specific record shapes.

Phase 1 made Markdown ingest primary and Phase 1 refactor extracted the Markdown ingest application seam. The remaining compiler debt is concentrated in `src/snowiki/compiler/generators/summary.py`, where Markdown document records get special inline handling for summary text, promoted tags, source identity, and document body sections.

The Phase 2 goal is to redesign that boundary so ingest/normalization owns source-specific interpretation and the compiler consumes a source-agnostic projection.

## User Decisions Captured

- Phase 2 target: **compiler boundary**.
- Phase 2 may remove or redesign legacy paths when they no longer fit Snowiki's Markdown-first direction.
- Behavior compatibility is not absolute. If better wiki output requires a deliberate compiled-output contract change, document it and test it.
- Use external references for ideas, especially Karpathy-style LLM wiki philosophy and seCall-style normalization, but do not copy any one project's taxonomy or UI assumptions.
- Follow the Phase 1 documentation workflow: keep a dedicated plan file, sync the architecture redesign ledger, and remove completed stale plan files when they stop adding live guidance.

## Reference Synthesis

The reference direction is: **normalize once, compile many**.

Relevant ideas:

- seCall parses multiple input sources into one normalized session/action model, then renders Markdown/frontmatter from that model. Later graph passes consume normalized Markdown/frontmatter rather than parser-specific branches.
- LLM wiki references generally use a two-stage pipeline: analyze/normalize first, generate pages second.
- Compiled wiki pages should be projections, not source-of-truth. Raw sources and normalized records remain auditable durable layers.
- Traceability should be first-class: generated pages need source/provenance links that explain where claims came from.
- Review queues, graph extraction, semantic retrieval, and UI-heavy workflows are later concerns unless Phase 2 needs a specific seam for them.

Snowiki should use these as design pressure, not requirements. Phase 2 should not inherit external taxonomies wholesale.

## Current Problem

`src/snowiki/compiler/generators/summary.py` currently has three Markdown-specific branches:

1. Override generic `record_summary(record)` for `source_type == "markdown"` and `record_type == "document"`.
2. Pull tags from `payload["promoted_frontmatter"]["tags"]` into summary page tags.
3. Add Markdown-only `Source Identity` and `Document` sections.

Related weaker seams:

- `src/snowiki/compiler/taxonomy.py::record_title()` and `record_summary()` use fallback chains that re-derive fields the ingest layer already knows.
- `extract_compiler_bucket()` depends on a loose `payload["compiler"]` convention with no schema owner.
- `taxonomy_items_for_record()` hardcodes session-era buckets (`concepts`, `entities`, `topics`, `questions`, `projects`, `decisions`).
- `NormalizedStorage` still supports legacy date-bucketed records while Markdown documents use latest-only records. Phase 2 should not expand the legacy write model.

## In Scope

- Define a source-agnostic compiler projection contract for normalized records.
- Populate that projection for Markdown document records during ingest.
- Refactor summary page generation to consume the projection instead of checking `source_type == "markdown"`.
- Preserve source/provenance traceability in generated pages.
- Decide which legacy compiler fallback paths are retained for read compatibility and which are removed.
- Add compiler-seam tests before changing projection behavior.
- Update architecture docs to make compiled pages explicitly derived artifacts.

## Out of Scope

- New frontmatter/YAML/Markdown parser dependencies.
- Storage layout redesign or pruning semantics.
- Stale source reports, source manifests, or destructive cleanup.
- Graph/community detection, vector search, review queues, and UI flows.
- LLM summarization inside deterministic rebuild.
- MCP writes or daemon behavior changes.

## Proposed Projection Contract

Add an explicit compiler projection shape inside normalized payloads. The exact field name should be short and stable; recommended key:

```json
"projection": {
  "title": "Guide",
  "summary": "Short description",
  "body": "# Guide\n\nBody text",
  "tags": ["docs", "reference"],
  "source_identity": {
    "source_root": "/repo/docs",
    "relative_path": "guide.md",
    "content_hash": "..."
  },
  "sections": [
    {"title": "Document", "body": "# Guide\n\nBody text"}
  ],
  "taxonomy": {
    "concepts": [],
    "entities": [],
    "topics": [],
    "questions": [],
    "projects": [],
    "decisions": []
  }
}
```

Implementation may use a Python `TypedDict` rather than runtime validation. The durable contract is the JSON shape written to normalized records.

### Contract Rules

- Ingest adapters own source-specific interpretation.
- Compiler generators consume `projection` fields first.
- Legacy records without `projection` may use compatibility fallback helpers.
- New source types must not add branches to summary generators; they must write the projection contract.
- Compiled pages must retain provenance through raw refs and source identity.

## Implementation Decisions

These Phase 2 decisions are now part of the implementation contract:

1. The normalized compiler projection key is `projection`.
   - Reason: `compiler` already has loose legacy meaning.
2. Projection keeps both `body` and `sections`.
   - `sections` is compiler-facing.
   - `body` preserves source text for search/future consumers.
3. Markdown tags are duplicated intentionally.
   - Source frontmatter remains preserved under `promoted_frontmatter`.
   - Compiler-facing tags are copied into `projection.tags`.
4. Existing normalized Markdown records are not migrated in Phase 2.
   - Re-ingest writes the new shape.
   - Compiler fallback handles existing records until pruning/migration is explicit.

## Implementation Waves

### Wave 1: Projection schema and tests

Files:

- `src/snowiki/compiler/taxonomy.py` or new `src/snowiki/compiler/projection.py`
- `tests/unit/compiler/`

Deliverables:

- Define `CompilerProjection`, `ProjectionSection`, and `SourceIdentity` typed contracts.
- Add helpers for extracting title, summary, tags, sections, source identity, and taxonomy buckets from either projection or legacy fallback.
- Add unit tests for projection-first extraction and legacy fallback.
- Keep legacy taxonomy fallback behavior available through projection helpers rather than expanding generator-level branching.

Acceptance criteria:

- A record with `payload["projection"]` compiles without checking source type.
- A legacy record without projection still compiles if compatibility is intentionally retained.
- Tests lock the fallback behavior that remains.

### Wave 2: Markdown ingest writes projection

Files:

- `src/snowiki/markdown/ingest.py`
- `tests/unit/markdown/test_ingest.py`

Deliverables:

- Extend `build_markdown_payload()` to write the projection contract.
- Map Markdown title/summary/body/tags/source identity into projection fields.
- Keep original frontmatter fields preserved separately.
- Keep CLI ingest output stable; the projection is a normalized payload addition, not a CLI response field.

Acceptance criteria:

- Markdown ingest unit tests assert the projection shape.
- Existing CLI ingest JSON output remains stable unless explicitly changed.

### Wave 3: Summary generator consumes projection

Files:

- `src/snowiki/compiler/generators/summary.py`
- `src/snowiki/compiler/taxonomy.py` or `src/snowiki/compiler/projection.py`
- `tests/unit/compiler/test_markdown_summary.py`

Deliverables:

- Remove inline `source_type == "markdown"` branches from `generate_summary_pages()`.
- Build title, summary, tags, source identity, and document sections through projection helpers.
- Keep record/provenance sections deterministic.
- Use the same projection helpers from concept/question generators where taxonomy/title/summary data is needed.

Acceptance criteria:

- Summary generator has no Markdown-specific source-type branch.
- Markdown document summary output remains intentionally tested.
- If output changes, tests and architecture docs describe the new contract.

### Wave 4: Legacy cleanup decision

Files:

- `src/snowiki/compiler/taxonomy.py`
- compiler tests

Deliverables:

- Decide whether to delete or retain:
  - `extract_compiler_bucket()` loose `payload["compiler"]` convention,
  - title/summary fallback chains,
  - session-era taxonomy bucket assumptions.
- Keep compatibility only where tests prove it is still a supported read path.

Acceptance criteria:

- Removed legacy paths have replacement behavior or explicit documentation that they are no longer supported.
- Retained fallback paths have tests and comments explaining why they remain.

### Wave 5: Documentation sync and verification

Files:

- `docs/architecture/llm-wiki-ingest-redesign.md`
- `docs/architecture/refactoring-operating-principles.md`
- this plan

Verification commands:

```bash
uv run ruff check src/snowiki tests
uv run ty check
uv run pytest
uv run pytest -m integration
```

PR readiness requires all commands above to pass.

## Deferred Ledger

Keep these out of Phase 2 unless implementation proves they are required:

- Source manifest and stale source report schema.
- Normalized storage write-contract split.
- Explicit prune/cascade cleanup.
- Graph/vector extraction and semantic retrieval.
- Review queues or approval workflows.
- Parser dependency changes.

## Commit Strategy

Recommended atomic commits:

1. `docs(compiler): define phase 2 projection plan`
2. `refactor(compiler): add projection contract helpers`
3. `refactor(markdown): write compiler projection payloads`
4. `refactor(compiler): consume projection summaries`
5. `test(compiler): cover projection compatibility`
6. `docs(architecture): sync compiler projection contract`

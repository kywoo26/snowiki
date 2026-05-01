# Refactoring Operating Principles

This document defines Snowiki's persistent refactoring contract. It turns recurring cleanup concerns into repeatable engineering practice for humans and agents.

It complements, but does not replace, root repository rules in `AGENTS.md`, architecture contracts in `docs/architecture/`, and tool configuration in `pyproject.toml`.

## North Star

Refactoring should make Snowiki easier to change without changing verified behavior.

Good refactoring in this repo improves at least one of:

- maintainability,
- reuse through clear domain boundaries,
- testability,
- agent readability,
- runtime contract stability,
- future engine portability.

Refactoring is not aesthetic churn. It must preserve CLI JSON contracts, storage artifacts, and documented behavior unless the PR explicitly changes those contracts.

## Non-Negotiable Repository Rules

These rules come from `AGENTS.md` and CI configuration:

- Use Python 3.14+ and run tools through `uv run`.
- Use explicit type hints on all function signatures.
- Keep `ruff`, `ty`, and `pytest` green.
- Use `pytest` fixtures such as `tmp_path`, `monkeypatch`, and `pytest-mock`; avoid new `unittest.mock`-driven patterns.
- Unit tests must stay deterministic: no sleeps, network, heavy datasets, or real external services.
- Use `logging` or `click.echo`; never use `print()` for runtime logging.
- Access repo assets through approved helpers such as `src/snowiki/config.py` and storage path helpers; avoid raw `cwd` coupling.

## Refactor Workflow

Every significant phase or feature should end with a bounded refactor pass before PR:

1. Re-check spec -> plan -> implementation alignment.
2. Identify behavior-preserving cleanup required for the next phase.
3. Fix contract mismatches immediately.
4. Add acceptance tests for safety, help output, compatibility, and error behavior.
5. Record larger refactors in the relevant architecture ledger instead of expanding the PR.
6. Re-run required verification.

Refactor PRs should be smaller than feature PRs. If a refactor changes behavior, rename it: it is a feature or fix, not a pure refactor.

## Agent-Readable Code

Snowiki is maintained by humans and agents. Code should be readable to both.

Prefer:

- explicit names over clever abbreviations,
- small pure functions with typed inputs and outputs,
- dataclasses or typed dicts for boundary objects,
- simple dependency flow over hidden global state,
- file and module names that describe their domain.

Avoid:

- action-at-a-distance decorators,
- generic `utils.py` dumping grounds,
- stringly typed payloads without a schema owner,
- broad `except Exception` blocks that hide the actual failure mode,
- mixing CLI parsing, file I/O, domain transformation, and storage writes in one function.

Agent-readable code is not merely "human readable." It should make the next safe edit obvious from local context and tests.

## Module Boundaries and Layering

Snowiki should keep dependency direction explicit:

```text
CLI / skill workflow
  -> application orchestration
  -> domain adapters / parsers
  -> storage and compiler contracts
  -> search / query surfaces
```

### CLI modules

CLI command modules should translate arguments, call domain/application functions, and format output. They should not own parsing policy, normalized payload schemas, or compiler behavior.

### Domain modules

Domain modules own meaning. For example, Markdown title extraction, frontmatter promotion, and reserved-field policy belong under `snowiki.markdown`, not `snowiki.cli.commands.ingest`.

### Storage modules

Storage modules own artifact layout, atomic writes, provenance attachment, and stable read/write contracts. They should avoid embedding CLI assumptions.

### Compiler modules

Compiler modules should operate on normalized records, not raw source formats. Source-specific transformation belongs at ingest/normalization time unless explicitly documented as compiler policy.

### Tests

Test helpers should target the narrowest API needed by the test:

- parser tests call parser functions,
- storage tests write storage records directly,
- compiler tests seed normalized records,
- CLI tests use `CliRunner`,
- integration tests exercise real CLI/runtime boundaries.

## Reuse Without `utils.py`

Python does not require Java-style helper classes or global utility buckets.

When code is duplicated:

1. If it belongs to one domain, colocate it in that domain module.
2. If it crosses domains, name the shared module after the concept, not `utils`.
3. If it defines a boundary, consider a `Protocol` or typed facade.
4. If it is test-only, place it under `tests/helpers/` or the nearest `conftest.py`.

Examples:

- Good: `snowiki.markdown.discovery`, `snowiki.compiler.paths`, `snowiki.cli.output`.
- Acceptable: `tests/helpers/markdown_ingest.py` for test-only fixture creation.
- Avoid: `snowiki/utils.py`, classes containing only static helper methods, or shared modules named by convenience rather than domain.

## Design Patterns

Design patterns are vocabulary, not goals.

Use patterns when they reduce coupling or make extension safer:

- **Adapter**: for external source formats such as Markdown, Claude, OpenCode, future GitHub/Notion sources.
- **Facade**: for stable entrypoints over storage, rebuild, or search orchestration.
- **Strategy**: for tokenizer/search/ranking variants and source-type-specific transformations.
- **Protocol**: for structural interfaces where inheritance is unnecessary.
- **Value object**: for immutable boundary data, usually `@dataclass(frozen=True, slots=True)`.

Do not add pattern ceremony when a typed function is clearer. In Python, a module with pure functions is often the best abstraction.

## Modern Python Baseline

Snowiki targets Python 3.14+. Prefer modern Python idioms that improve clarity and type checking:

- builtin generics: `list[str]`, `dict[str, object]`, `tuple[str, ...]`,
- `type` aliases for repeated contracts,
- `@dataclass(frozen=True, slots=True)` for immutable value objects,
- `TypedDict` for JSON-like contract shapes,
- `Protocol` for behavior seams,
- `pathlib.Path` for paths,
- `contextlib`, `functools`, `itertools`, `tempfile`, and `subprocess.run(..., check=True, timeout=...)` from stdlib where appropriate.

Continue using `from __future__ import annotations` while the repo standard requires it, even though Python 3.14 improves deferred annotation behavior.

Avoid outdated patterns:

- `typing.List` / `typing.Dict` in new code,
- mutable defaults,
- untyped function signatures,
- manual path string manipulation where `Path` works,
- manual retry loops around transient I/O.

## Dependency and Library Policy

Use stdlib first, but do not reinvent mature infrastructure.

Add or expand dependencies only when they clearly improve correctness, safety, or maintenance and are acceptable for a CLI/runtime package. Do not treat example libraries as a roadmap. A dependency is justified by a current Snowiki requirement, not by general popularity.

Evaluate candidates by domain and need:

- CLI: keep `click` unless a concrete runtime or ergonomics problem requires a change.
- Runtime validation/schema: continue using `pydantic` where Snowiki already needs validated schema objects.
- YAML/frontmatter: consider a YAML library only if the current deterministic parser cannot support documented frontmatter requirements safely.
- Retry: use a maintained retry library only around real transient I/O boundaries; do not add retry machinery for pure local transforms.
- Async I/O and HTTP: add async or HTTP dependencies only when Snowiki ships a real network/runtime integration that needs them.
- Structured logging: consider a structured logging dependency only when runtime workflows need cross-component correlation IDs or machine-ingested logs.

Dependency rules:

- Do not add a library for a one-line convenience.
- Do not add a dependency that weakens Rust/engine portability unless the boundary remains file/JSON based.
- Wrap third-party libraries behind domain modules so replacement is possible.
- Validate human-authored config after parsing; parsing alone is not validation.

## Testing Levels

Snowiki uses five test levels:

- `tests/unit/`: deterministic, fast, patched boundaries.
- `tests/integration/`: real CLI/runtime boundaries.
- `tests/smoke/`: fast end-to-end product contract checks that run in the smoke workflow.
- `tests/bench/`: actual benchmark validation, dataset-heavy benchmark checks, and benchmark-result guardrails.
- `tests/perf/`: latency/performance assertions.

Tests for the benchmark implementation itself still belong at the narrowest normal
test level. For example, pure helpers in `benchmarks/` should have unit tests in
`tests/unit/`, and CLI/runtime integration around `snowiki benchmark` should live
in `tests/integration/`. Do not put ordinary unit coverage under `tests/bench/`
just because the code under test is in the `benchmarks/` package.

Smoke tests are useful when they lock a top-level product path with minimal cost. In Snowiki, smoke tests should be reserved for committed, fast, end-to-end product contracts that should block PRs independently from broader integration coverage. Examples include:

- `snowiki ingest <markdown> --output json`,
- `snowiki rebuild --output json`,
- `snowiki query ... --output json`,
- `snowiki benchmark --matrix benchmarks/contracts/snowiki_regression_matrix.yaml ...`,
- status/lint happy paths.

Use `tests/smoke/` only for smoke contracts selected by `pytest -m smoke`; keep ordinary CLI/runtime integration coverage under `tests/integration/`.

Refactors should preserve or improve tests at the same level as the changed seam. If a refactor extracts a pure function, add or move unit tests to that pure seam.

## Observability and Errors

Use clear error types and output contracts:

- CLI errors should use `emit_error` and stable machine-readable codes.
- Validation failures should usually raise `ValueError` with actionable messages.
- Runtime logs should use `logging`; CLI user output should use `click.echo` through existing output helpers.
- Do not log secrets, raw credentials, or private source content.

Structured logging may become appropriate when runtime workflows need request IDs, source IDs, or operation IDs across multiple components.

## Engine Portability

Future Rust engine work should remain possible.

Stable boundaries are:

- CLI arguments,
- CLI JSON output,
- raw storage layout,
- normalized JSON records,
- compiled Markdown artifacts,
- search/index manifests.

Avoid making Python-only objects, decorators, or Click internals durable contracts. Refactors should move toward deterministic file/JSON boundaries when code may later be ported to Rust.

## Recurring Refactor Smells

Treat these as prompts for a refactor plan:

- one function performs CLI parsing, I/O, transformation, and storage,
- source-type checks appear in compiler/search code,
- a field is interpreted differently by two modules,
- test helpers call a broader layer than the system under test requires,
- two model types represent the same abstraction level,
- a shared helper cannot be named without using `utils`,
- string rendering grows conditionals for structured output,
- compatibility bridges remain after tests can use the new contract.

## Refactor Decision Checklist

Use this checklist before changing structure or moving code:

1. **Name the seam.** Identify the boundary being clarified, such as CLI adapter, Markdown ingest, storage provenance, compiler projection, fileback queue, retrieval workspace, or benchmark adapter.
2. **Prove behavior preservation.** State which CLI JSON output, storage artifact, compiled page, or test contract must remain unchanged.
3. **Choose the narrowest layer.** Move logic only to the layer that owns its meaning; do not centralize unrelated helpers for convenience.
4. **Pair tests with the seam.** Extracted pure logic needs unit tests; CLI wiring and runtime paths need integration tests.
5. **Keep generated artifacts generated.** Do not turn compiled Markdown, index state, queues, or benchmark reports into hand-edited source truth.
6. **Record durable rules.** If the refactor changes a lasting architecture decision, update the relevant architecture contract in the same PR.

## Current Refactor Boundaries

These boundaries are current architecture guidance, not historical phase plans.

### Ingest and Markdown

- `src/snowiki/cli/commands/ingest.py` should stay a Click/output/error wrapper.
- Markdown ingest orchestration belongs behind `src/snowiki/markdown/ingest.py` or a future dedicated application package if ingest grows beyond Markdown-specific orchestration.
- Source discovery, frontmatter handling, title/summary derivation, privacy gating, and projection construction should stay in Markdown/domain modules rather than CLI callbacks.
- Non-Markdown conversion belongs before Markdown ingest; Snowiki-owned DTOs should feed title resolution, projection sections, links, wikilinks, and source gardening.

### Compiler and projection

- `src/snowiki/compiler/projection.py` owns the source-agnostic compiler projection contract.
- Compiler generators should consume projection helpers for title, summary, sections, source identity, and taxonomy buckets.
- Missing projection is a lint/status diagnostic for old records, not an invitation to reintroduce hidden fallback chains.
- Projection backfill, if needed, should be an explicit operator workflow with tests and docs.

### Storage and provenance

- Storage modules own artifact layout, atomic writes, provenance attachment, and stable read/write contracts.
- `content_hash` is the authoritative freshness signal; mtime and size are cache hints.
- Ingest and rebuild must not silently delete normalized, raw, compiled, or index artifacts.
- Source roots and raw provenance snapshots are evidence layers; compiled pages are derived wiki memory.

### Status, lint, prune, and gardening

- Keep Markdown source freshness classification and prune planning in domain modules such as `snowiki.markdown.source_state` and `snowiki.markdown.source_prune`, not Click callbacks.
- Keep `status` as a summary surface and `lint` as an actionable diagnostic surface.
- Keep `prune sources` narrow, dry-run-first, and destructive only through explicit `--delete --yes --all-candidates` style confirmation.
- Model source rename, dead-wikilink, and cascade cleanup as reviewable proposals before any apply path mutates files.

### Fileback and queues

- Keep fileback preview output as proposal state until an approved CLI apply path succeeds.
- Keep queued fileback proposals as a pending inbox, not a terminal archive manager.
- Queue apply must delete pending proposals only after the reviewed raw/normalized/rebuild path succeeds.
- Queue reject should delete the pending proposal with an explicit reason.

### CLI commands and agent workflows

- CLI command modules translate arguments, call domain/application functions, and format output.
- Skills orchestrate the installed CLI; they must not redefine runtime behavior.
- Natural-language `/wiki` lifecycle intents are skill arguments over current CLI truth, not shipped `snowiki` subcommands.
- Mutation remains CLI-mediated and reviewable through shipped paths such as `fileback` and explicit prune.
- Standalone sync/edit/merge/graph commands remain deferred unless a later runtime spec accepts them.

### Retrieval and evaluation

- Retrieval surfaces should preserve parity across CLI query/recall, MCP read-only retrieval, and benchmark runs.
- `src/snowiki/storage/index_manifest.py` owns typed retrieval identity, manifest freshness, and legacy compatibility parsing. `search/workspace.py` should stay a thin facade over that storage contract, while `status`, `lint`, and `rebuild` consume freshness explanations instead of parsing manifests themselves.
- Phase 3 completed the workspace split and the typed index manifest groundwork needed for future semantic, vector, and fusion identity work. It does not ship hybrid or vector retrieval, and it does not turn semantic reranking into a current runtime layer.
- Semantic/vector/rerank work should stay behind explicit extension seams until benchmark evidence justifies promotion.
- Benchmark commands inform retrieval quality gates, but benchmark behavior is not the shipped wiki memory contract.

## Refactor Backlog

Keep future cleanup scoped to one durable concern at a time:

1. **Clarify normalized storage write contracts**
   - Separate latest-only document storage from legacy date-bucketed record storage, or extract shared record-writing mechanics.
2. **Narrow test helper layers**
   - Use parser/storage/compiler seams directly in unit tests.
   - Reserve CLI helpers for integration tests.
3. **Specify explicit projection backfill/migration**
   - Old projection-less normalized records should not regain rebuild/query compatibility through hidden fallback.
   - If needed, add an explicit operator command with tests and docs for projection backfill.
4. **Keep command adapters thin**
   - If `src/snowiki/cli/commands/` grows, split by command role and primary consumer as described in `docs/architecture/cli-command-taxonomy.md`.

Each refactor PR should update this document or the relevant architecture contract when it changes a durable principle.

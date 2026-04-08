# AGENTS.md

## Project overview

Snowiki V2 is a CLI-first Python project for ingesting sources, compiling wiki knowledge, querying indexed content, and exposing MCP resources for search and recall workflows.

## Directory structure

- `snowiki/` — application package
  - `cli/` — Click entrypoints and command wiring
  - `adapters/` — Claude and OpenCode ingestion adapters
  - `compiler/` — wiki compilation and link generation
  - `search/` — indexing, tokenization, retrieval, reranking
  - `storage/` — raw, normalized, compiled, provenance, dedupe layers
  - `mcp/` — MCP server, tools, and resources
  - `daemon/`, `lint/`, `privacy/`, `rebuild/`, `schema/` — supporting subsystems
- `tests/` — pytest suite, generally mirroring package areas
- `fixtures/` — test fixtures and sample inputs
- `vault-template/` — starter vault layout for downstream wiki usage
- `benchmarks/` — benchmark data and judgments

## Code style

- Use Python 3.12+ syntax.
- Keep imports sorted and grouped consistently with Ruff.
- Ruff lint rules enabled: `E`, `F`, `I`, `N`, `W`, `UP`, `B`, `C4`, `SIM`.
- Ruff formatting is the canonical formatter.
- Target line length is 88.
- Prefer explicit types and straightforward control flow; simplify branches when possible to satisfy `SIM` and related rules.
- Docstring convention is Google style when docstrings are added.

## Type checking requirements

- Basedpyright runs in `strict` mode.
- New or modified code in `snowiki/` must type check without errors.
- Avoid untyped helpers, implicit `Any`, and ambiguous return paths.
- Use project-local imports that resolve from the repository root or `snowiki/` package root.

## Testing requirements

- Use `pytest` for all tests.
- Add or update tests in `tests/` alongside the affected subsystem.
- Default pytest configuration runs coverage for `snowiki`.
- Before finishing work, run targeted tests when possible and at least the repo-standard verification commands.

## Pre-commit hooks

Pre-commit runs the following checks before commit:

1. `ruff check --fix`
2. `ruff format`
3. `basedpyright snowiki/`
4. branch protection against direct commits to `main`

Install hooks with:

```bash
uv run pre-commit install
```

Run all hooks manually with:

```bash
uv run pre-commit run --all-files
```

## Common commands

```bash
uv sync --group dev
uv run snowiki --help
uv run ruff check snowiki tests
uv run ruff format snowiki tests
uv run basedpyright snowiki/
uv run pytest
uv run pytest tests/cli/test_query.py
python -m compileall snowiki/
```

## CI expectations

- CI installs dependencies with `uv`.
- CI must pass Ruff, basedpyright, and pytest with coverage.
- Keep local commands aligned with CI commands to avoid drift.

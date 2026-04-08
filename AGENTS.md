# AGENTS.md

## Project overview

Snowiki V2 is a CLI-first Python project for ingesting LLM session logs (Claude Code, OMO/OpenCode), compiling personal wiki knowledge, and exposing query interfaces (CLI, MCP, optional daemon).

**Key Philosophy (Karpathy-style)**:
- Centralized storage at `~/.snowiki` - ALL sessions across ALL projects compound in one place
- 3-layer architecture: raw → normalized → compiled
- Rebuildable from raw sources at any time
- Bilingual lexical-first retrieval (Korean + English)

## Storage

Snowiki uses centralized storage at `~/.snowiki` (configurable via `SNOWIKI_ROOT` environment variable).

Directory structure:
- `~/.snowiki/raw/` — immutable raw sources (Claude JSONL, OMO SQLite)
- `~/.snowiki/normalized/` — canonical records (sessions, events, messages, parts)
- `~/.snowiki/compiled/` — generated wiki pages (markdown)
- `~/.snowiki/index/` — search indexes
- `~/.snowiki/quarantine/` — corrupted/blocked sources

Override locations:
- Environment: `export SNOWIKI_ROOT=/custom/path`
- CLI flag: `snowiki --root /custom/path ingest ...`

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

- Use Python 3.14+ syntax.
- Keep imports sorted and grouped consistently with Ruff.
- Ruff lint rules enabled: `E`, `F`, `I`, `N`, `W`, `UP`, `B`, `C4`, `SIM`.
- Ruff formatting is the canonical formatter.
- Target line length is 88.
- Prefer explicit types and straightforward control flow; simplify branches when possible to satisfy `SIM` and related rules.
- Docstring convention is Google style when docstrings are added.

## Type checking requirements

- **ty** (Astral): Primary type checker - extremely fast Rust-based checker
  - Run: `uv run ty check`
  - Configuration: `[tool.ty]` in pyproject.toml
  - Currently in beta but actively developed
  
- **basedpyright** (fallback): Strict mode type checking
  - Run: `uv run basedpyright snowiki/`
  - Configuration: `[tool.basedpyright]` in pyproject.toml
  
- Both must pass for CI. Prefer ty for local development speed.
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
3. `ty check` (Astral - fast Rust-based type checker)
4. `basedpyright snowiki/` (fallback strict check)
5. branch protection against direct commits to `main`

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
# Sync dependencies
uv sync --group dev

# Run CLI
uv run snowiki --help

# Code quality
uv run ruff check snowiki tests
uv run ruff format snowiki tests

# Type checking (both)
uv run ty check
uv run basedpyright snowiki/

# Testing
uv run pytest
uv run pytest tests/cli/test_query.py

# Verification
python -m compileall snowiki/
```

## CI expectations

- CI installs dependencies with `uv`.
- CI must pass Ruff, ty, basedpyright, and pytest with coverage.
- Keep local commands aligned with CI commands to avoid drift.

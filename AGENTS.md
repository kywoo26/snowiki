# Snowiki Agent Contract

## Commands

```bash
# Setup & Dependencies
uv sync --group dev
uv run pre-commit install

# Quality Control
uv run ruff check snowiki tests
uv run ruff format snowiki tests
uv run ty check

# Testing
uv run pytest
uv run pytest tests/cli/test_query.py -v

# Verification
uv run python -m compileall snowiki/
```

## Toolchain

- **Runtime**: Python 3.14+ managed by `uv`
- **Type System**: `ty` (primary type checker)
- **Lint/Format**: `ruff` (E, F, I, N, W, UP, B, C4, SIM rules)
- **Test Runner**: `pytest` with `pytest-cov`
- **Repo Map**:
  - `snowiki/` - Core implementation (CLI, storage, adapters)
  - `tests/` - Unit and integration tests
  - `pyproject.toml` - Centralized tool configuration

## Always

- Execute all tools via `uv run`.
- Run `ruff check` and `ty check` before every commit.
- Use explicit type hints for all function signatures.
- Maintain 90%+ test coverage target for new logic.
- Follow Google style docstrings.
- Use `tmp_path` fixture for all tests that write to the filesystem.

## Ask First

- Adding or updating dependencies in `pyproject.toml`.
- Modifying core storage interfaces, Pydantic models, or `SchemaVersion` (schema/versioning change boundary).
- Changing CLI command signatures or arguments.
- Updating `fixtures/` or `benchmarks/` (inventory sensitive).

## Never

- Commit secrets, credentials, or `.env` files.
- Use `print()` for logging (use `logging` or `click.echo`).
- Skip verification steps (tests, lint, type check).
- Modify raw source files in `SNOWIKI_ROOT/raw/` (runtime storage, not the repo).
- Manually modify or delete files in `SNOWIKI_ROOT/quarantine/` (runtime storage zone).
- Manually edit generated artifacts in `compiled/` or `index/` zones.

## Verification Matrix

| Scope | Verification Command |
| :--- | :--- |
| **Docs Only** | `uv run ruff check snowiki tests` |
| **CLI / Help** | `uv run snowiki --help && uv run ruff check snowiki tests && uv run ty check` |
| **Search / Compiler** | `uv run python -m compileall snowiki/ && uv run pytest tests/cli/test_query.py` |
| **Storage / Schema / Config** | `uv run pytest && uv run ty check && uv run ruff check snowiki tests` |
| **Tests / Fixtures** | `uv run pytest && uv run ruff check snowiki tests` |
| **Perf Sensitive** | `uv run snowiki benchmark --help` (See benchmarks/README.md) |

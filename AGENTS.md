# Root AGENTS.md

This is the root AGENTS file for Snowiki. It defines repo-wide rules. Child `AGENTS.md` files inherit these rules and define local deltas only.

## Commands

```bash
# Setup & Dependencies
uv sync --group dev
uv run pre-commit install

# Quality Control
uv run ruff check src/snowiki tests
uv run ruff format src/snowiki tests
uv run ty check

# Testing
uv run pytest
uv run pytest -m integration
uv run pytest --cov=snowiki --cov-report=term-missing --cov-report=xml
uv run pytest tests/cli/test_query.py -v
uv run pytest --durations=10

# Verification
uv run python -m compileall src/snowiki/
uv run snowiki benchmark --preset retrieval --output reports/retrieval.json
```

## Toolchain

- **Runtime**: Python 3.14+ managed by `uv`
- **Type System**: `ty` (primary type checker)
- **Lint/Format**: `ruff` (E, F, I, N, W, UP, B, C4, SIM rules)
- **Test Runner**: `pytest` (`pytest-cov` for CI and explicit coverage runs)

## Always

- Execute all tools via `uv run`.
- Run `ruff check` and `ty check` before every commit.
- Use explicit type hints for all function signatures.
- Maintain 90%+ test coverage target for new logic.
- Keep default local test loops fast; use explicit coverage runs locally or rely on CI coverage reporting.
- Treat `uv run pytest` as the fast unit-test loop; run integration tests explicitly before opening a PR.
- Use integration tests for real heavy engines, subprocess/thread/server lifecycle, benchmark-sized fixtures, real DB/index builds, or timing-sensitive behavior.
- Follow Google style docstrings.
- Use `tmp_path` fixture for all tests that write to the filesystem.
- Ensure child AGENTS are delta-only and inherit root policy.

## Ask First

- Adding or updating dependencies in `pyproject.toml`.
- Modifying core storage interfaces, Pydantic models, or `SchemaVersion`.
- Changing CLI command signatures or arguments.
- Updating `fixtures/` or `benchmarks/` (inventory sensitive).

## Never

- Commit secrets, credentials, or `.env` files.
- Use `print()` for logging (use `logging` or `click.echo`).
- Skip verification steps (tests, lint, type check).
- Modify raw source files in `SNOWIKI_ROOT/raw/`.
- Manually modify or delete files in `SNOWIKI_ROOT/quarantine/`.
- Manually edit generated artifacts in `compiled/` or `index/` zones.

## Verification Matrix

| Scope | Verification Command |
| :--- | :--- |
| **Docs Only** | `uv run ruff check src/snowiki tests` |
| **CLI / Help** | `uv run snowiki --help && uv run ruff check src/snowiki tests && uv run ty check` |
| **Search / Compiler** | `uv run python -m compileall src/snowiki/ && uv run pytest tests/cli/test_query.py` |
| **Storage / Schema / Config** | `uv run pytest && uv run ty check && uv run ruff check src/snowiki tests` |
| **Tests / Fixtures** | `uv run pytest && uv run ruff check src/snowiki tests` |
| **PR Preflight** | `uv run pytest && uv run pytest -m integration && uv run pytest --cov=snowiki --cov-report=term-missing --cov-report=xml` |
| **Coverage Check** | `uv run pytest --cov=snowiki --cov-report=term-missing --cov-report=xml` |
| **Integration Check** | `uv run pytest -m integration` |
| **Slow Test Diagnosis** | `uv run pytest --durations=10` |
| **Perf Sensitive** | `uv run snowiki benchmark --preset retrieval --output reports/retrieval.json` |

## Ownership

| Path | Role | Governance Owner |
| :--- | :--- | :--- |
| `src/snowiki/` | Runtime code | Root `AGENTS.md` |
| `docs/architecture/skill-and-agent-interface-contract.md` | Skill/Agent Contract | `docs/architecture/skill-and-agent-interface-contract.md` |
| `tests/` | Verification | Root `AGENTS.md` |
| `scripts/` | Repo automation | Root `AGENTS.md` |
| `docs/architecture/skill-and-agent-interface-contract.md` | Canonical agent interface contract | Root `AGENTS.md` |
| `benchmarks/` | Benchmark assets/reports/docs | `benchmarks/AGENTS.md` |
| `vault-template/` | Distributable vault schema | `vault-template/AGENTS.md` |
| `skill/` | Distributable skill package | `skill/AGENTS.md` |
| `fixtures/` | Shared asset surface | Root `AGENTS.md` |

## Path Contract

- Access to repository assets (benchmarks, fixtures) must flow through approved helpers in `src/snowiki/config.py` and `src/snowiki/storage/zones.py`.
- Avoid direct repo-root derivations or raw `cwd` coupling in production code.

## PR Discipline

- One canonical owner per fact; mirrors must be updated in the same PR.
- Root AGENTS changes must be intentional; do not silently rewrite child AGENTS.
- Maintain atomic commits by concern.

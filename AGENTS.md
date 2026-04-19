# Root AGENTS.md

This is the root AGENTS file for Snowiki. It defines repo-wide rules. Child `AGENTS.md` files inherit these rules and define local deltas only.

## Toolchain

- **Runtime**: Python 3.14+ managed by `uv`
- **Type System**: `ty` (primary type checker)
- **Lint/Format**: `ruff` (E, F, I, N, W, UP, B, C4, SIM rules)
- **Test Runner**: `pytest` (`pytest-cov` for CI and explicit coverage runs)

## Always

- Execute all tools via `uv run`.
- Run `uv run ruff check src/snowiki tests && uv run ty check` before every commit.
- Use explicit type hints for all function signatures.
- Maintain 90%+ test coverage target for new logic.
- Treat `uv run pytest` as the fast unit-test loop; run `uv run pytest -m integration` before opening a PR.
- Follow Google style docstrings.
- Use `tmp_path` fixture for all tests that write to the filesystem.
- Ensure child AGENTS are delta-only and inherit root policy.

## Never

- Commit secrets, credentials, or `.env` files.
- Use `print()` for logging (use `logging` or `click.echo`).
- Skip verification steps (tests, lint, type check).
- Modify raw source files in `SNOWIKI_ROOT/raw/`.
- Manually modify or delete files in `SNOWIKI_ROOT/quarantine/`.
- Manually edit generated artifacts in `compiled/` or `index/` zones.
- Add agent co-author markers (e.g., `Co-authored-by:`, `Ultraworked with`) to commits.
- Force-add or commit ignored internal artifacts (for example `.sisyphus/`, `.cache/`, or transient `reports/` content) unless an explicit tracked exception is already whitelisted by repo policy.


## PR Discipline

- Use `.github/pull_request_template.md` as lightweight guidance, not as a hard gate.
- Use `.github/commit-message-rules.md` as lightweight guidance for clear conventional commit subjects.
- Maintain atomic commits by concern when practical.

## Verification Matrix

| Scope | Verification Command |
| :--- | :--- |
| **Docs Only** | `uv run ruff check src/snowiki tests` |
| **CLI / Help** | `uv run snowiki --help && uv run ruff check src/snowiki tests && uv run ty check` |
| **Search / Compiler** | `uv run python -m compileall src/snowiki/ && uv run pytest tests/search/ tests/retrieval/ tests/compiler/` |
| **Storage / Schema / Config** | `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest` |
| **Tests / Fixtures** | `uv run ruff check src/snowiki tests && uv run pytest` |
| **PR Preflight** | `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest && uv run pytest -m integration` |
| **Coverage Check** | `uv run pytest --cov=snowiki --cov-report=term-missing --cov-report=xml` |
| **Integration Check** | `uv run pytest -m integration` |
| **Slow Test Diagnosis** | `uv run pytest --durations=10` |
| **Perf Sensitive** | `uv run snowiki benchmark --preset retrieval --output reports/retrieval.json` |

## Ownership

| Path | Role | Governance Owner |
| :--- | :--- | :--- |
| `src/snowiki/` | Runtime code | Root `AGENTS.md` |
| `tests/` | Verification | Root `AGENTS.md` |
| `scripts/` | Repo automation | Root `AGENTS.md` |
| `docs/architecture/` | Contract layer (runtime truth, stable interfaces) | Root `AGENTS.md` |
| `docs/reference/` | Supporting architecture rationale and research | Root `AGENTS.md` |
| `docs/roadmap/` | Canonical planning and analysis surface | Root `AGENTS.md` |
| `docs/archive/` | Historical non-roadmap lineage | Root `AGENTS.md` |
| `benchmarks/` | Benchmark assets/reports/docs | `benchmarks/AGENTS.md` |
| `vault-template/` | Distributable vault schema | `vault-template/AGENTS.md` |
| `skill/` | Distributable skill package | `skill/AGENTS.md` |
| `fixtures/` | Shared asset surface | Root `AGENTS.md` |

## Path Contract

- Access to repository assets (benchmarks, fixtures) must flow through approved helpers in `src/snowiki/config.py` and `src/snowiki/storage/zones.py`.
- Avoid direct repo-root derivations or raw `cwd` coupling in production code.


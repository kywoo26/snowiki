# Root AGENTS.md

This is the root AGENTS file for Snowiki. It defines repo-wide rules. Child `AGENTS.md` files inherit these rules and define local deltas only.

## Toolchain

- **Runtime**: Python 3.14+ managed by `uv`
- **Type System**: `ty` (primary type checker)
- **Lint/Format**: `ruff` (E, F, I, N, W, UP, B, C4, SIM rules)
- **Test Runner**: `pytest` (`pytest-cov` for CI and explicit coverage runs)

## Always

- Execute all tools via `uv run`.
- Run `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest` before every commit.
- Run `uv run pytest -m integration` before opening a PR.
- Follow `.github/pull_request_template.md` when opening a PR.
- Use explicit type hints for all function signatures.
- Follow `.github/commit-message-rules.md` for all commits.
- Preserve the PR number suffix in squash-merge commit subjects, following `.github/commit-message-rules.md`.
- Maintain atomic commits by concern.
- Use `pytest-mock`'s `mocker` fixture or pytest's `monkeypatch` for unit-test patching; avoid new `unittest.mock`-driven test patterns.
- Use `tmp_path` fixture for all tests that write to the filesystem.

## Never

- Commit secrets, credentials, or `.env` files.
- Use `print()` for logging (use `logging` or `click.echo`).
- Skip verification steps (tests, lint, type check).
- Let unit tests sleep, hit network, spawn long-lived background workers, or load heavy public datasets; patch those boundaries and move that coverage to `integration`, `bench`, or `perf`.
- Add agent co-author markers (e.g., `Co-authored-by:`, `Ultraworked with`) to commits.
- Force-add or commit ignored internal artifacts (for example `.sisyphus/`, `.cache/`, or transient `reports/` content) unless an explicit tracked exception is already whitelisted by repo policy.


## Verification Commands

| Purpose | Command |
| :--- | :--- |
| **Fast check** | `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest` |
| **Full check** | `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest && uv run pytest -m integration` |
| **Coverage** | `uv run pytest --cov=snowiki --cov-report=term-missing` |
| **Benchmark** | `uv run snowiki benchmark --preset retrieval` |

## Test Levels

- `tests/unit/` is the default fast loop. Keep tests deterministic and patch external boundaries.
- `tests/integration/` exercises real CLI/runtime boundaries and runs with `pytest -m integration`.
- `tests/smoke/` is for fast end-to-end product contract smoke tests and runs with `pytest -m smoke`.
- `tests/bench/` is for benchmark-domain and dataset-heavy validation; it is excluded from the default unit loop.
- `tests/perf/` is for latency/performance assertions and is excluded from the default unit loop.
- Keep shared fixtures in the nearest `conftest.py`; do not dynamically import another test directory's `conftest.py`.

## Ownership

| Path | Role | Governance Owner |
| :--- | :--- | :--- |
| `src/snowiki/` | Runtime code | Root `AGENTS.md` |
| `tests/` | Verification | Root `AGENTS.md` |
| `docs/architecture/` | Contract layer (runtime truth, stable interfaces) | Root `AGENTS.md` |
| `docs/reference/` | Supporting architecture rationale and research | Root `AGENTS.md` |
| `benchmarks/` | Benchmark assets/reports/docs | `benchmarks/AGENTS.md` |
| `skill/` | Distributable skill package | `skill/AGENTS.md` |
| `fixtures/` | Shared asset surface | Root `AGENTS.md` |

## Path Contract

- Access to repository assets (benchmarks, fixtures) must flow through approved helpers in `src/snowiki/config.py` and `src/snowiki/storage/zones.py`.
- Avoid direct repo-root derivations or raw `cwd` coupling in production code.

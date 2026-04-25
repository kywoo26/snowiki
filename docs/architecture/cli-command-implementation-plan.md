# CLI Command Implementation Plan

## Purpose

This plan turns `docs/architecture/cli-command-taxonomy.md` into implementation work without making a cosmetic directory move.

The command taxonomy is now the product-role spec. Implementation should proceed only when it improves test coverage, import stability, or command ownership clarity.

## Current command map

All command adapters currently live flat under `src/snowiki/cli/commands/` and are registered explicitly in `src/snowiki/cli/main.py`.

| Class | Commands | Current files |
| :--- | :--- | :--- |
| Wiki flow | `ingest`, `query`, `recall` | `ingest.py`, `query.py`, `recall.py` |
| Lifecycle | `status`, `lint`, `fileback` | `status.py`, `lint.py`, `fileback.py` |
| Maintenance | `rebuild`, `prune` | `rebuild.py`, `prune.py` |
| Runtime | `daemon` | `daemon.py` |
| Transport | `mcp` | `mcp.py` |
| Support | `export` | `export.py` |
| Evaluation | `benchmark`, `benchmark-fetch` | `benchmark.py`, `benchmark_fetch.py` |

## Implementation gates

Do not split `src/snowiki/cli/commands/` into role-based subpackages until these gates are satisfied:

1. **Untested command gaps are closed**
   - `export` has integration coverage.
   - `mcp serve --stdio` has CLI surface coverage.
   - `snowiki.cli.output` has direct unit coverage.
2. **Direct imports are known and intentional**
   - `tests/integration/cli/test_query.py`
   - `tests/integration/cli/test_rebuild.py`
   - `tests/integration/cli/test_daemon.py`
   - `tests/unit/mcp/test_search.py`
3. **Monkeypatch string paths are migrated in the same commit as any module move**
   - `snowiki.cli.commands.query.*`
   - `snowiki.cli.commands.recall.*`
   - `snowiki.cli.commands.benchmark.run_matrix_with_exit_code`
4. **Compatibility is deliberate**
   - Either preserve temporary re-exports from `snowiki.cli.commands`, or update all imports and tests in one atomic commit.
   - Do not leave both old and new command paths as permanent public contracts unless the architecture contract explicitly accepts that compatibility burden.

## Safe work order

### Step 1: Test command gaps

Add tests before moving modules:

- `tests/integration/cli/test_export.py`
- `tests/integration/cli/test_mcp.py`
- `tests/unit/cli/test_output.py`

This makes the support/debug, transport, and shared output surfaces visible before command files are reorganized.

### Step 2: Reduce import fragility

Prefer command tests through `snowiki.cli.main.app` where possible. Keep direct imports only when a test intentionally targets a non-Click helper such as `run_query`, `run_rebuild`, `run_recall`, or daemon parser/command internals.

If direct imports remain, list them in this plan before a move.

### Step 3: Move command adapters only when useful

Move files into role-based subpackages only if doing so reduces ownership drift or review load:

```text
src/snowiki/cli/commands/
  wiki_flow/       ingest.py, query.py, recall.py
  lifecycle/       status.py, lint.py, fileback.py
  maintenance/     rebuild.py, prune.py
  runtime/         daemon.py
  transport/       mcp.py
  support/         export.py
  evaluation/      benchmark.py, benchmark_fetch.py
```

The move must update:

- `src/snowiki/cli/main.py`
- direct test imports
- monkeypatch string paths
- any compatibility re-export strategy

### Step 4: Verify full runtime parity

After any command-path move, run:

```bash
uv run ruff check src/snowiki tests
uv run ty check
uv run pytest
uv run pytest -m integration
```

## Non-goals

- Do not change command behavior as part of directory reshuffling.
- Do not add new runtime commands because a taxonomy class exists.
- Do not promote `export` into a primary `/wiki` flow.
- Do not widen MCP beyond read-only transport.
- Do not convert benchmark commands into user memory workflows.

## Current next slice

The current implementation slice is **test-first command stabilization**:

1. add `export` CLI integration coverage;
2. add `mcp` CLI surface coverage;
3. add `cli/output.py` unit coverage;
4. keep command files flat until this safety net is green.

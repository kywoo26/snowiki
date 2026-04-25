# CLI Command Implementation Plan

## Purpose

This plan records how `docs/architecture/cli-command-taxonomy.md` guides command implementation work without requiring the physical package layout to mirror every conceptual role.

The command taxonomy is now the product-role spec. Implementation should proceed only when it improves test coverage, import stability, or command ownership clarity.

## Current command map

Command adapters live flat under `src/snowiki/cli/commands/` and are registered explicitly in `src/snowiki/cli/main.py`.

| Class | Commands | Current files |
| :--- | :--- | :--- |
| Knowledge flow | `ingest`, `query`, `recall` | `ingest.py`, `query.py`, `recall.py` |
| Lifecycle / health | `status`, `lint`, `fileback` | `status.py`, `lint.py`, `fileback.py` |
| Maintenance | `rebuild`, `prune` | `rebuild.py`, `prune.py` |
| Runtime | `daemon` | `daemon.py` |
| Transport | `mcp` | `mcp.py` |
| Support | `export` | `export.py` |
| Evaluation | `benchmark`, `benchmark-fetch` | `benchmark.py`, `benchmark_fetch.py` |

## Implementation gates

The flat layout is acceptable only while these gates remain satisfied:

1. **Untested command gaps are closed**
    - `export` has integration coverage.
    - `mcp serve --stdio` has CLI surface coverage.
    - `snowiki.cli.output` has direct unit coverage.
    - reusable Click option decorators have direct unit coverage.
    - storage export bundle assembly has direct unit coverage.
2. **Direct imports are known and intentional**
    - `tests/integration/cli/test_rebuild.py`
    - `tests/integration/cli/test_daemon.py`
    - `tests/integration/cli/test_mcp.py`
    - `tests/integration/cli/test_query.py` imports search-domain `run_query` and `run_recall`, not CLI adapter internals.
    - `tests/unit/mcp/test_search.py`
3. **Monkeypatch string paths target canonical command modules**
    - `snowiki.search.queries.runtime.*` for query/recall domain behavior
    - `snowiki.cli.commands.benchmark.run_matrix_with_exit_code`
4. **Compatibility is deliberate**
   - `snowiki.cli.commands` intentionally re-exports command modules for package-level consumers such as tests targeting command internals.
   - Flat module paths such as `snowiki.cli.commands.query` are the canonical internal CLI adapter paths.

## Safe work order

### Step 1: Test command gaps — complete

The following tests protect command surfaces before and after module movement:

- `tests/integration/cli/test_export.py`
- `tests/integration/cli/test_mcp.py`
- `tests/unit/cli/test_output.py`

This makes the support/debug, transport, and shared output surfaces visible before command files are reorganized.

### Step 2: Reduce import fragility — complete

Command tests use `snowiki.cli.main.app` where possible. Direct imports remain only when a test intentionally targets a non-Click helper such as `run_rebuild`, `mcp.run`, or daemon parser/command internals. Query and recall helper tests target `snowiki.search.queries` domain entry points instead of CLI command modules.

If new direct imports are added later, list them in this plan before another package move.

### Step 3: Evaluate command adapter grouping — complete

Internal and external review found that mapping every conceptual role to a directory over-fragments a 13-command CLI surface. Mature Python CLIs commonly keep small-to-medium command packages flat and use docs/registries for conceptual grouping. Snowiki therefore keeps one module per command:

```text
src/snowiki/cli/commands/
  ingest.py
  query.py
  recall.py
  status.py
  lint.py
  fileback.py
  rebuild.py
  prune.py
  daemon.py
  mcp.py
  export.py
  benchmark.py
  benchmark_fetch.py
```

Any future subpackage split must update:

- `src/snowiki/cli/main.py`
- direct test imports
- monkeypatch string paths
- package-level compatibility re-exports from `snowiki.cli.commands`

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

The current implementation slice is **command-adapter thinning**:

1. keep CLI modules as argument/output adapters;
2. move domain logic out of command modules only when a seam is large enough to justify it;
3. place storage export bundle assembly in `snowiki.storage.export_bundle`, not a top-level `snowiki.export` module that can be confused with the CLI command;
4. place status aggregation in `snowiki.status` so `cli/commands/status.py` only renders and maps errors;
5. place query/recall runtime helpers in `snowiki.search.queries` so CLI command modules do not own search orchestration;
6. share repeated Click option declarations through `snowiki.cli.decorators` and output mode normalization through `snowiki.cli.output`;
7. keep package-level command re-exports intentional and tested indirectly through existing command-internal tests;
8. do not add compatibility flat modules unless an external consumer requires them.

## Click contract guidance

Snowiki treats Click as the agent-facing runtime contract layer, not only as a
decorator convenience. Command adapters should use Click features when they make
the installed `snowiki` command easier for humans and agents to inspect, invoke,
and test.

- Use `ctx.obj` via `snowiki.cli.context.SnowikiCliContext` for shared adapter
  state such as parsed output mode and root path.
- Keep option callbacks side-effect free. Parsing may normalize values, but
  storage initialization belongs in command execution paths that actually need a
  prepared Snowiki root.
- Prefer typed Click parameters (`Choice`, `IntRange`, `FloatRange`, `Path`, and
  project `ParamType` instances) over command-local string parsing.
- Expose stable environment variables in help with `show_envvar=True` for common
  agent configuration (`SNOWIKI_ROOT`, `SNOWIKI_OUTPUT`, daemon settings).
- Add explicit `short_help` and `no_args_is_help=True` for groups so `--help`
  remains a compact command index.
- Keep destructive commands dry-run-first and flag-confirmed (`--delete --yes`),
  rather than using interactive prompts that can hang automated agents.
- Validate Click shell completion with a smoke test. Users can enable Bash
  completion with:

```bash
eval "$(_SNOWIKI_COMPLETE=bash_source snowiki)"
```

# Benchmark & Quality Playbook

This playbook guides performance-sensitive changes and search quality verification in Snowiki. Use it when modifying search algorithms, indexing logic, or when `AGENTS.md` routes you here for performance verification.

## Benchmark Assets

The following files define the canonical quality dataset:

- `benchmarks/queries.json`: Bilingual query set (Korean, English, Mixed) covering known-item, topical, and temporal retrieval.
- `benchmarks/judgments.json`: Gold relevance judgments for the query set.

## Execution

Run benchmarks using the `snowiki benchmark` command. Always use `uv run` to ensure the correct environment.

### Presets

| Preset | Description |
| :--- | :--- |
| `core` | Fast regression check using known-item queries. |
| `retrieval` | Broader check including known-item and topical queries. |
| `full` | Complete coverage including temporal queries and optional semantic slots. |

### Example Commands

```bash
# Fast regression check
uv run snowiki benchmark --preset core --output reports/core.json

# Retrieval quality check
uv run snowiki benchmark --preset retrieval --output reports/retrieval.json

# Full benchmark run
uv run snowiki benchmark --preset full --output reports/full.json
```

## Routing from AGENTS.md

The root `AGENTS.md` file routes performance-sensitive work to this playbook. If your changes affect search latency or retrieval precision, you should run the `full` preset to capture current performance metrics. 

> **Note**: Automated regression testing against a "blessed baseline" and specific metric thresholds (e.g., `Precision@K`, `P99` latency, `memory usage`) are planned for future implementation. For now, use the benchmark output for manual comparison and verification.

## Verification

- Ensure `uv run pytest` passes for all benchmark-related tests.
- Verify that machine-readable JSON reports are generated in the specified output path.
- Review the generated report for any obvious performance or quality regressions.

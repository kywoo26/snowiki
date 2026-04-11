# Benchmark & Quality Playbook

This playbook guides performance-sensitive changes and search quality verification in Snowiki. Use it when modifying search algorithms, indexing logic, or when `AGENTS.md` routes you here for performance verification.

## Phase 1: Headless Backend Benchmark

The current benchmark suite (Phase 1) is a **deterministic, headless backend benchmark**. It verifies the core retrieval and performance characteristics of the Snowiki engine.

It is **not** a full agent-authoring loop. It focuses on the `ingest -> rebuild -> query -> status/lint` flow using local, deterministic components.

### Phase 1 Scope
- **Flow**: `ingest` (normalization) -> `rebuild` (compilation) -> `query` (retrieval) -> `status/lint` (structural integrity).
- **Execution**: Local and deterministic. No LLM calls or agentic loops are exercised in this phase.

### Phase 2 Exclusions (Future Work)
The following items are explicitly excluded from Phase 1 and are planned for Phase 2:
- `sync` and `edit` command benchmarking.
- Semantic linting and contradiction detection.
- Claim-level citations and epistemic integrity checks.
- P99 latency metrics (Phase 1 uses P50 and P95).
- Precision@K metrics (Phase 1 uses Recall@K, MRR, and nDCG@K).
- Memory usage metrics.

## Benchmark Assets

The following files define the canonical quality dataset:

- `benchmarks/queries.json`: Bilingual query set (Korean, English, Mixed) covering known-item, topical, and temporal retrieval.
- `benchmarks/judgments.json`: Gold relevance judgments for the query set.

## Execution

Run benchmarks using the `snowiki benchmark` command. Always use `uv run` to ensure the correct environment.

When `--root` is omitted, the benchmark runs inside an isolated temporary Snowiki root that is seeded with the canonical Phase 1 fixtures. This prevents Phase 1 verification from reading or mutating the user's real `~/.snowiki` runtime tree.

### Presets

| Preset | Description |
| :--- | :--- |
| `core` | Fast regression check using known-item queries. |
| `retrieval` | Broader check including known-item and topical queries. |
| `full` | Complete coverage including temporal queries. |

### Example Commands

```bash
# Fast regression check
uv run snowiki benchmark --preset core --output reports/core.json

# Retrieval quality check
uv run snowiki benchmark --preset retrieval --output reports/retrieval.json

# Full benchmark run
uv run snowiki benchmark --preset full --output reports/full.json
```

## Pass/Fail Semantics

The benchmark command evaluates three primary gates. A failure in any blocking gate results in a non-zero exit code.

1.  **Structural Gate (Blocking)**: Verifies workspace integrity and lint health. Any `ERROR` level issue fails this gate.
2.  **Retrieval Gate (Blocking)**: Compares retrieval metrics against frozen Phase 1 thresholds.
    -   **Overall Thresholds**: Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67.
    -   **Slice Thresholds**: Specific targets for `known-item`, `topical`, and `temporal` slices.
3.  **Performance Gate (Blocking)**: Verifies latency for `ingest`, `rebuild`, and `query`.
    -   **Thresholds**: P50 <= 5950ms, P95 <= 6300ms.

### Unified Verdict
The final line of the benchmark output provides a unified verdict:
`Unified benchmark verdict: PASS/FAIL (blocking_stage=..., exit_code=...)`

## Report Output

The benchmark produces two types of output:
1.  **Human-readable summary**: Printed to stdout, including per-baseline metrics, threshold deltas, and the unified verdict.
2.  **Machine-readable JSON**: Written to the path specified by `--output`. This report includes detailed metrics, threshold policies, and structural validation results.

The stdout summary is intended to be concise and benchmark-focused. Backend library progress bars should not obscure the final structural, performance, retrieval, and unified verdict sections.

## Verification

- Ensure `uv run pytest` passes for all benchmark-related tests.
- Verify that machine-readable JSON reports are generated in the specified output path.
- Review the `Unified benchmark verdict` for a `PASS` status.

# Benchmarks Governance Delta

Root `AGENTS.md` is inherited; this file defines local deltas only.

## Scope

This directory governs benchmark assets, canonical corpora, and quality reports. Performance sensitive changes must be verified with the benchmark levels, targets, and metric slices defined here and in `benchmarks/README.md`. Numeric promotion thresholds are intentionally not defined in this file.

The governed benchmark asset surface lives in `benchmarks/`. Runtime benchmark implementation code under `src/snowiki/bench/` remains governed by the root contract for `src/snowiki/` and should use this file only for asset and report policy, thresholds, and benchmark specific workflow boundaries.

## Module Boundaries

The benchmark runtime in `src/snowiki/bench/` is organized into seven flat modules. When modifying benchmark code, respect these boundaries:

### `specs.py` — Dataclasses
- Owns `EvaluationMatrix`, `DatasetManifest`, and related data structures.
- Must not import from any other bench module.
- Changes here affect all downstream modules and must be accompanied by test updates.

### `datasets.py` — YAML Contract Loading
- Owns evaluation matrix loading, asset resolution, and dataset manifest handling.
- May import from `specs.py` only.
- Public dataset payloads stay out of git; all fetch results go through the HF cache.

### `targets.py` — Target Registry
- Owns the target registry with built-in retrieval target specs.
- May import from `specs.py` and `datasets.py`.
- Maps a dataset or runtime target to an adapter.

### `metrics.py` — Metric Compute Functions
- Owns metric computation functions (Recall@k, MRR, nDCG@k, latency percentiles).
- May import from `specs.py` only.
- Does not load datasets or execute targets; pure compute only.

### `runner.py` — Matrix Execution
- Owns evaluation matrix execution, cell evaluation, and qrel loading.
- May import from `specs.py`, `datasets.py`, `targets.py`, and `metrics.py`.
- The main orchestration entrypoint that drives a benchmark run.

### `report.py` — Lean JSON Rendering
- Owns lean JSON report rendering and summary output.
- May import from `specs.py` and `runner.py`.
- Does not compute metrics; formats and writes results.

### `__init__.py` — Public API Exports
- Re-exports the public benchmark API surface.
- May import from all other modules.
- Keep the export surface minimal and stable.

## Workflow

Detailed benchmark playbooks and execution steps live in `benchmarks/README.md`.

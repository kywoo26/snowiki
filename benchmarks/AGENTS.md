# Benchmarks Governance Delta

Root `AGENTS.md` is inherited; this file defines local deltas only.

## Scope

This directory governs benchmark assets, canonical corpora, and quality reports. Performance-sensitive changes must be verified against the thresholds defined here and in `benchmarks/README.md`.

The governed benchmark asset surface lives in `benchmarks/`. Runtime benchmark implementation code under `src/snowiki/bench/` remains governed by the root contract for `src/snowiki/` and should use this file only for asset/report policy, thresholds, and benchmark-specific workflow boundaries.

## Assets & Provenance

- `benchmarks/queries.json` and `benchmarks/judgments.json` are the canonical Phase 1 quality dataset.
- Benchmark asset updates are allowed only when they are part of an explicitly bounded benchmark program with canonical docs/tests updated in the same PR.
- Benchmark reports in `reports/` are transient artifacts and should not be committed unless specifically requested for evidence.

## Execution & Isolation

- Always run benchmarks via `uv run snowiki benchmark`.
- Default execution uses an isolated temporary root seeded with Phase 1 fixtures.
- Avoid using `--root` in automated verification to prevent mutation of the user's real vault.

## Threshold Sensitivity

- Retrieval Gate: Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67.
- Performance Gate: P50 <= 5950ms, P95 <= 6300ms.
- Any regression below these thresholds requires architectural justification or optimization.

## Workflow

Detailed benchmark playbooks and execution steps live in `benchmarks/README.md`.

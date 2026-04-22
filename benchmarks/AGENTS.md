# Benchmarks Governance Delta

Root `AGENTS.md` is inherited; this file defines local deltas only.

## Scope

This directory governs benchmark assets, canonical corpora, and quality reports. Performance sensitive changes must be verified against the thresholds defined here and in `benchmarks/README.md`.

The governed benchmark asset surface lives in `benchmarks/`. Runtime benchmark implementation code under `src/snowiki/bench/` remains governed by the root contract for `src/snowiki/` and should use this file only for asset and report policy, thresholds, and benchmark specific workflow boundaries.

## Benchmark Authority Tiers

Benchmarks are classified into two authority tiers.

- **`official_suite`**: The fixed 6 dataset ko/en benchmark suite. Governs release quality claims.
- **`regression_harness`**: Fast, deterministic internal checks visible during development. Governs candidate screening only.

A pass in the `regression_harness` is necessary but not sufficient for release quality claims.

## Assets & Provenance

- `benchmarks/queries.json` and `benchmarks/judgments.json` are the internal regression harness quality dataset, a 90 query set.
- They are not the official suite. They are visible during development and tuned against, so they support candidate screening only.
- The 90 query set must never be treated as the main truth source for release quality claims. Regression harness results are necessary but not sufficient for any claim beyond candidate screening.
- Benchmark asset updates are allowed only when they are part of an explicitly bounded benchmark program with canonical docs and tests updated in the same PR.
- Benchmark reports in `reports/` are transient artifacts and should not be committed unless specifically requested for evidence.

## Execution & Isolation

- Always run benchmarks via `uv run snowiki benchmark`.
- Default execution uses an isolated local root under the benchmark output directory, seeded with Phase 1 fixtures.
- Avoid using `--root` in automated verification to prevent mutation of the user's real vault.

## Threshold Sensitivity

- Retrieval Gate: Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67.
- Performance Gate: P50 <= 5950ms, P95 <= 6300ms.
- Any regression below these official suite thresholds requires architectural justification or optimization.

## Tier Aware Latency Sampling

Latency sampling defaults keep the internal regression harness exhaustive while preserving comparable official suite reports.

- `regression_harness`: exhaustive, all queries.
- `official_suite`: layer declared volume, quick or standard.

The exact policy is recorded in every report under `protocol.sampling_policy`. Official suite reports cap per query detail to 20 entries in JSON reports.

## Workflow

Detailed benchmark playbooks and execution steps live in `benchmarks/README.md`.

# Benchmarks Governance Delta

Root `AGENTS.md` is inherited; this file defines local deltas only.

## Scope

This directory governs benchmark assets, canonical corpora, and quality reports. Performance-sensitive changes must be verified against the thresholds defined here and in `benchmarks/README.md`.

The governed benchmark asset surface lives in `benchmarks/`. Runtime benchmark implementation code under `src/snowiki/bench/` remains governed by the root contract for `src/snowiki/` and should use this file only for asset/report policy, thresholds, and benchmark-specific workflow boundaries.

## Benchmark Authority Tiers

Benchmarks are classified into four authority tiers. Each tier governs a specific decision gate.

- **`regression`**: Fast, deterministic checks visible during development. Govern the **candidate-screening gate** only.
- **`public_anchor`**: Public, reproducible datasets with external provenance. Govern **release-quality claims**.
- **`snowiki_shaped`**: Internally curated datasets reflecting real user queries and content shapes. Govern **release-quality claims**.
- **`hidden_holdout`**: Held-out queries and judgments not visible during development. Govern **final proof**.

A pass in the `regression` tier is necessary but not sufficient for release-quality or final-proof claims.

## Assets & Provenance

- `benchmarks/queries.json` and `benchmarks/judgments.json` are the **regression / candidate-screening** quality dataset (90-query set).
- They are **not** a public anchor, shaped dataset, or hidden holdout. They are visible during development and tuned against, so they support candidate-screening only.
- **The 90-query set must never be treated as the main truth source for release-quality or final-proof claims.** Regression-tier results are necessary but not sufficient for any claim beyond candidate screening.
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

## Tier-Aware Latency Sampling

Latency sampling defaults differ by tier to keep run times bounded while preserving representativeness:

- `regression`: exhaustive (all queries).
- `public_anchor` / `snowiki_shaped`: stratified sampling when query count exceeds 50.
- `hidden_holdout`: fixed 20-query sample.

The exact policy is recorded in every report under `protocol.sampling_policy`. Large non-regression tiers also cap per-query detail to 20 entries in JSON reports.

## Workflow

Detailed benchmark playbooks and execution steps live in `benchmarks/README.md`.

# Benchmark & Quality Playbook

This playbook guides performance-sensitive changes and search quality verification in Snowiki. Use it when modifying search algorithms, indexing logic, or when `AGENTS.md` routes you here for performance verification.

## Benchmark Authority Model

Benchmarks in Snowiki are organized into execution layers and evidence authority classes. Execution layers define when a benchmark runs; authority classes define what claims the results can support.

### Execution Layers

| Layer | Trigger | Datasets | Metrics | Blocking |
| :--- | :--- | :--- | :--- | :--- |
| `pr_official_quick` | PRs touching benchmark-relevant paths | Same 6 official ko/en datasets, quick volume (150-query cap) | nDCG@10, Recall@100, MRR@10, P95 latency | Yes |
| `scheduled_official_standard` | Weekday-nightly cron + manual | Same 6 official ko/en datasets, standard volume (500-query cap) | nDCG@10, Recall@100, MRR@10, P95 latency | No |
| `release_proof` | Manual only (disabled by default) | Holdout set (not configured) | Full scorecard | Yes |

### Authority Classes

| Class | Scope | Gating Power |
| :--- | :--- | :--- |
| `official_suite` | The fixed 6 dataset ko/en benchmark suite: MS MARCO, TREC DL, MIRACL, and BEIR | Release quality claims. Results can be cited in release notes and compared externally. |
| `regression_harness` | Internal deterministic harness that exercises the local 90 query fixture set | Candidate screening only. It is useful for iteration, but it is not release quality evidence. |

### Official Balanced-Core Backbone

The official benchmark backbone consists of exactly these 6 datasets:

| Dataset | Language | Source |
| :--- | :--- | :--- |
| `ms_marco_passage` | en | Microsoft MSMARCO |
| `trec_dl_2020_passage` | en | NIST TREC DL 2020 |
| `miracl_ko` | ko | MIRACL Korean |
| `miracl_en` | en | MIRACL English |
| `beir_nq` | en | BEIR Natural Questions |
| `beir_scifact` | en | BEIR SciFact |

The `regression` fixture set stays internal and deterministic. It is excluded from official scorecards and release claims.

### The Regression Harness

The `regression` harness is a deterministic, headless backend benchmark that verifies core retrieval and performance characteristics on a fixed 90 query set. It focuses on the `ingest -> rebuild -> query -> status/lint` flow using local, deterministic components. No LLM calls or agentic loops are exercised.

Because the 90 query set is visible and tuned against during development, it is explicitly classified as an internal regression harness. It cannot support release quality or final proof claims on its own.

### Future Work Exclusions

The following items are explicitly excluded from the current benchmark system and are planned for future tiers:
- `sync` and `edit` command benchmarking.
- Semantic linting and contradiction detection.
- Claim level citations and epistemic integrity checks.
- P99 latency metrics; the current system uses P50 and P95.
- Precision@K metrics; the current system uses Recall@K, MRR, and nDCG@K.

Tokenizer promotion operational evidence, memory and disk, is measured separately from the benchmark pass or fail gate.

### Tier Aware Execution and Latency Sampling

Latency measurement adapts by surface so that the regression harness stays deterministic and the official suite stays comparable across runs:

| Surface | Default Sampling Mode | Rationale |
| :--- | :--- | :--- |
| `regression_harness` | Exhaustive, all queries | Small, fixed 90 query set, every query matters for deterministic screening. |
| `official_suite` | Layer dependent, quick or standard | The official 6 should use the layer's declared volume so reports stay comparable. |

Sampling policy is recorded in every report under `protocol.sampling_policy` so the exact population versus sampled counts are auditable. Report detail for the official suite is capped to 20 per query entries so JSON outputs stay inspectable without dropping aggregate metrics.

## Benchmark Module Architecture

The benchmark runtime lives in `src/snowiki/bench/` and is organized into six subpackages. Each subpackage has a single responsibility and a well-defined boundary:

| Subpackage | Responsibility | Key Exports |
| :--- | :--- | :--- |
| `contract/` | Frozen thresholds, scoring semantics, presets, and policy contracts. | `MetricThreshold`, `ReportEntry`, `NoAnswerScoringPolicy`, `BenchmarkPreset`, `get_benchmark_contract()` |
| `datasets/` | Dataset registry, fetch logic, caching, and materialization for public corpora. | `BenchmarkDatasetId`, `fetch_benchmark_dataset()`, `resolve_cached_benchmark_dataset()` |
| `evaluation/` | Retrieval evaluation: qrel loading, baseline comparison, candidate matrix assembly, and quality scoring. | `run_baseline_comparison()`, `CANDIDATE_MATRIX`, `evaluate_quality()`, `load_qrels()` |
| `validation/` | Pre-flight correctness checks and latency benchmarking. | `run_correctness_flow()`, `run_latency_evaluation()`, `validate_workspace()` |
| `reporting/` | Report generation, rendering, verdict computation, and baseline modeling. | `generate_report()`, `benchmark_verdict()`, `render_report_text()` |
| `runtime/` | Execution context, corpus manifest handling, catalog of official datasets, and operational measurement. | `BenchmarkCorpusManifest`, `ExecutionLayer`, `official_suite_dataset_ids()`, `seed_canonical_benchmark_root()` |

### Design Principles

- **Contract first**: `contract/` owns all frozen values. Nothing outside `contract/` hard-codes thresholds or preset definitions.
- **Dataset boundaries split**: Public dataset fetch/cache logic lives in `datasets/`. Evaluation logic consumes materialized corpora through `runtime/corpus.py` and does not reach into fetch internals.
- **Baselines decomposed**: Baseline comparison (`evaluation/baselines.py`) assembles candidates from `evaluation/candidates.py`, runs against qrels via `evaluation/index.py`, and delegates scoring to `evaluation/scoring.py`.
- **Validation separate from evaluation**: `validation/` handles workspace correctness and latency measurement. It does not compute retrieval metrics.
- **Reporting consumes evaluation**: `reporting/report.py` orchestrates the full benchmark flow by calling into `validation/`, `evaluation/`, and `runtime/`, then produces the final report and verdict.
- **Public API surface minimal**: `snowiki.bench` exports only the symbols in `__all__`. Subpackages are not re-exported at the package root.

### Cross-Package Import Rules

- `contract/` may not import from any other bench subpackage.
- `datasets/` may import from `contract/` and `runtime/` only.
- `evaluation/` may import from `contract/` and `runtime/` only.
- `validation/` may import from `contract/`, `runtime/`, and `datasets/`.
- `reporting/` may import from all other subpackages.
- `runtime/` may import from `contract/` only.

## Benchmark Assets

The following files define the internal regression harness quality dataset:

- `benchmarks/queries.json`: Bilingual query set, Korean and English, covering known item, topical, and temporal retrieval, with machine checkable `tags` and optional `no_answer` flags.
- `benchmarks/judgments.json`: Gold relevance judgments for the query set; no answer queries are represented as queries with no relevant documents.

`benchmarks/*.json` files are benchmark maintenance assets for the internal regression harness only. They must not be promoted into the official suite.

## Real Public Dataset Management

Real public benchmark payloads stay out of git. Use the dedicated benchmark fetch cache instead of copying corpora or qrels into `benchmarks/`.

- Default benchmark data root: `SNOWIKI_ROOT/benchmarks`
- Override env var: `SNOWIKI_BENCHMARK_DATA_ROOT`
- Benchmark owned Hugging Face cache: `<benchmark_data_root>/hf`
- Local lock metadata: `<benchmark_data_root>/locks/<dataset_id>.json`

If you point `--data-root` at the repo local `benchmarks/` directory for experiments, both payload caches and generated lock files remain local only and should stay out of git.

Use the flat CLI entrypoint:

```bash
# Fetch an official dataset into the benchmark owned HF cache
uv run snowiki benchmark-fetch --dataset miracl_ko

# Force refresh a repo local benchmark cache root for local experiments
uv run snowiki benchmark-fetch --dataset beir_scifact --data-root benchmarks --refresh force

# Reuse only locally cached files, no network
uv run snowiki benchmark-fetch --dataset beir_nq --offline
```

The fetch command stores dataset payloads in the benchmark data root / HF cache and writes small local lock metadata describing every resolved source snapshot, revision, provenance metadata, and allow listed file scope. Corpora and qrels remain outside git managed benchmark assets.

## Execution

Run benchmarks using the `snowiki benchmark` command. Always use `uv run` to ensure the correct environment.

When `--root` is omitted, the benchmark runs inside an isolated local Snowiki root created under the JSON output directory and seeded with the regression harness fixtures. This keeps the run isolated from the user's real `~/.snowiki` runtime tree while leaving benchmark local artifacts durable for inspection.

The default dataset remains `regression`. Official datasets are opt in via `--dataset` so release quality runs stay clearly separated from the internal regression harness.

### Presets

| Preset | Description |
| :--- | :--- |
| `core` | Fast regression check using known item queries. |
| `retrieval` | Broader check including known item and topical queries. |
| `full` | Complete coverage including temporal queries. |

### Example Commands

```bash
# Fast regression harness check
uv run snowiki benchmark --preset core --output reports/core.json

# Official PR quick suite (with layer annotation)
uv run snowiki benchmark-fetch --dataset ms_marco_passage
uv run snowiki benchmark --preset retrieval --dataset ms_marco_passage   --sample-mode quick --layer pr_official_quick --output reports/ms_marco.json

# Official scheduled standard suite (with layer annotation)
uv run snowiki benchmark-fetch --dataset miracl_ko
uv run snowiki benchmark --preset retrieval --dataset miracl_ko   --sample-mode standard --layer scheduled_official_standard --output reports/miracl_ko.json

# Internal regression harness run
uv run snowiki benchmark --preset retrieval --dataset regression   --output reports/regression.json
```

### Dataset Selection

`snowiki benchmark` accepts `--dataset` with the following options:

**Official Standard Datasets:**
- `ms_marco_passage`, `trec_dl_2020_passage`
- `miracl_ko`, `miracl_en`
- `beir_nq`, `beir_scifact`

**Internal Regression Harness:**
- `regression`

- `regression` uses the deterministic local fixtures.
- `miracl_ko` loads a compact deterministic sample built from the real cached MIRACL Korean parquet assets. Query IDs, document IDs, and qrels come from the public dataset; run `benchmark-fetch` first.
- `beir_scifact` loads a compact deterministic sample built from the real cached BEIR SciFact corpus and queries repo plus the separate SciFact qrels repo. Query IDs, document IDs, and qrels come from the public dataset; run `benchmark-fetch` first.

To keep runs isolated, manifest backed datasets are seeded only into empty isolated benchmark roots. They do not reuse or silently mix with the regression fixtures.

## Review & Audit Workflow

Authoritative benchmark maintenance uses pooled review rather than single system qrels alone.

- **Multi system pooling**: candidate documents are pooled from multiple retrieval systems so adjudication does not inherit a single ranker's blind spots.
- **Blind human adjudication**: reviewers judge pooled candidates without seeing which system retrieved them.
- **Disagreement handling**: when pooled judgments conflict, the query is escalated to adjudication and the benchmark status reports disagreement counts rather than silently collapsing them.
- **Audit sampling**: a quota controlled sample of adjudicated queries is re reviewed to estimate ground truth error and report provenance coverage across source class, authoring method, authority class, and execution layer.

This means the internal regression harness is useful for iteration, while the official suite provides the release quality evidence.

### GitHub Manual Workflow

For shared, reproducible benchmark runs without turning benchmarks into a default PR hard gate, use the GitHub Actions workflow:

- Workflow: `benchmark-manual`
- Trigger: `workflow_dispatch`
- Inputs: `preset` (`core`, `retrieval`, `full`)

The workflow uploads the generated JSON report as an artifact so the result can be reviewed without relying on a local machine.

## Pass/Fail Semantics

The benchmark command evaluates three primary gates. A failure in any blocking gate results in a non zero exit code.

1.  **Structural Gate (Blocking)**: Verifies workspace integrity and lint health. Any `ERROR` level issue fails this gate.
2.  **Retrieval Gate (Blocking)**: Compares retrieval metrics against frozen official suite thresholds.
    -   **Overall Thresholds**: Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67.
    -   **Slice Thresholds**: Specific targets for `known-item`, `topical`, and `temporal` slices.
3.  **Performance Gate (Blocking)**: Verifies latency for `ingest`, `rebuild`, and `query`.
    -   **Thresholds**: P50 <= 5950ms, P95 <= 6300ms.

### Unified Verdict
The final line of the benchmark output provides a unified verdict:
`Unified benchmark verdict: PASS/FAIL (blocking_stage=..., exit_code=...)`

## Report Output

The benchmark produces two types of output:
1.  **Human readable summary**: Printed to stdout, including per baseline metrics, threshold deltas, and the unified verdict.
2.  **Machine readable JSON**: Written to the path specified by `--output`. This report includes detailed metrics, threshold policies, structural validation results, multi k metric maps, and subset slices when available.

The stdout summary is intended to be concise and benchmark focused. Backend library progress bars should not obscure the final structural, performance, retrieval, and unified verdict sections.

## GitHub Actions Workflows

Three workflows support the official benchmark system:

| Workflow | Trigger | Purpose |
| :--- | :--- | :--- |
| `benchmark-official-pr` | PR paths + manual | Runs the fixed 6 dataset ko/en official suite at quick volume (150 query cap) |
| `benchmark-official-scheduled` | Weekday nightly cron + manual | Runs the same 6 dataset ko/en official suite at standard volume (500 query cap) |
| `benchmark-manual` | Manual only | Ad hoc benchmark runs for any preset |

All workflows support offline preflight. If a dataset is not cached, the run is recorded as `infra_skipped` and the workflow continues.

## Dashboard Decision Matrix

The following directions were evaluated for richer benchmark visualization:

| Direction | Mainstream Adoption | Production Fit | Maintenance Cost | Integration Complexity | Score |
| :--- | :--- | :--- | :--- | :--- |
| Richer static pipeline | Medium | High | Low | Low | **Recommended for next step** |
| Interactive portal | High | Medium | High | High | Deferred |
| Report store integration | Medium | High | Medium | Medium | Deferred |

**Decision**: Ship artifact first tables and static plots now. Evaluate interactive portal options after the official benchmark system is stable.

## Next Steps

1. **Threshold calibration for official datasets**: Layer specific thresholds need calibration against external baselines.
2. **Official suite proof path**: Keep the six dataset official suite aligned with release notes and workflow output.
3. **Interactive dashboard**: Evaluate portal options after benchmark system stabilizes.
4. **Benchmark asset update policy**: Define PR checklist for adding or modifying datasets.

## Verification

- Ensure `uv run pytest` passes for all benchmark related tests.
- Verify that machine readable JSON reports are generated in the specified output path.
- Review the `Unified benchmark verdict` for a `PASS` status.

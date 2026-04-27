# Benchmark README

This bench is a local-first retrieval evaluator. It helps compare retrieval behavior on fixed datasets and fixed levels, using the shipped CLI as the entry point.

## Mission

Bench measures retrieval quality and runtime behavior for local runs. It is a thin evaluator, not a release evidence platform, and it stays separate from governance policy.

## Official datasets

These are the four fixed dataset IDs used by bench:

| Dataset ID | Language |
| :--- | :--- |
| `beir_nq` | en |
| `beir_scifact` | en |
| `trec_dl_2020_passage` | en |
| `miracl_ko` | ko |

## Levels

| Level ID | Query count | Corpus scope |
| :--- | :--- | :--- |
| `quick` | 150 | Up to 50,000 docs |
| `standard` | 500 | Up to 200,000 docs |

Quick and standard levels materialize bounded working sets for local benchmarking. Sampling always keeps all judged documents for the selected queries first, then fills any remaining budget with a deterministic random sample so metrics stay valid while index build time stays practical. Full-corpus benchmarks are intentionally outside the official local surface until streaming/chunked materialization exists.

## Core contracts

| Contract | Role |
| :--- | :--- |
| `EvaluationMatrix` | Input that describes the retrieval matrix to score. |
| `RetrievalTargetAdapter` | Execution seam that adapts a target into the bench runner. |
| `BenchmarkRunResult` | Output that carries the result of one benchmark run. |

## Command reference

Run bench with the shipped CLI:

```bash
# Run with the default official matrix
uv run snowiki benchmark --matrix benchmarks/contracts/official_matrix.yaml --target bm25_regex_v1 --report report.json

# Run a single dataset at quick level
uv run snowiki benchmark --matrix benchmarks/contracts/official_matrix.yaml --target bm25_regex_v1 --report report.json --dataset beir_scifact --level quick
```

The `snowiki benchmark` command is the supported surface for local evaluation runs.

Materialize datasets before benchmarking:

```bash
# Fetch the official benchmark datasets into benchmarks/materialized/
uv run snowiki benchmark-fetch --level quick
```

For CI smoke runs, `bm25_regex_v1` is the only target executed on pull requests and `main`. Keep tokenizer-variant BM25 targets plus `snowiki_query_runtime_v1` in the manual or local comparison lane before semantic or hybrid work.

Useful top-k metrics for CLI query baselines are available as `recall_at_1`, `recall_at_3`, `recall_at_5`, `recall_at_10`, `hit_rate_at_1`, `hit_rate_at_3`, `hit_rate_at_5`, and `hit_rate_at_10`. `recall_at_5` and `hit_rate_at_5` are the most relevant defaults when evaluating whether a human or agent can find a useful candidate from the first screen of results.

## Manual BM25 comparison recipe

Use this manual recipe when comparing the six built-in runtime and BM25 targets across the official core datasets:

```bash
# 1. Materialize the official core datasets once.
uv run snowiki benchmark-fetch \
  --level standard \
  --dataset beir_nq \
  --dataset beir_scifact \
  --dataset trec_dl_2020_passage \
  --dataset miracl_ko

# 2. Run the official runtime and BM25 target comparison manually.
uv run snowiki benchmark \
  --matrix benchmarks/contracts/official_matrix.yaml \
  --level standard \
  --dataset beir_nq \
  --dataset beir_scifact \
  --dataset trec_dl_2020_passage \
  --dataset miracl_ko \
  --target snowiki_query_runtime_v1 \
  --target bm25_regex_v1 \
  --target bm25_kiwi_morphology_v1 \
  --target bm25_kiwi_nouns_v1 \
  --target bm25_mecab_morphology_v1 \
  --target bm25_hf_wordpiece_v1 \
  --report reports/benchmark-lexical-baselines.json
```

## Runner shape

Bench is intentionally thin. Its job is to assemble the input matrix, hand execution to a retrieval target adapter, and return a run result.

The bounded extension seams are:

1. dataset manifests, which describe the fixed datasets
2. target registry, which maps a dataset or runtime target to an adapter
3. metric registry, which defines the metrics bench can score

## Analyzer promotion gates

Analyzer candidates are evaluated with the gate contract at
`benchmarks/contracts/analyzer_promotion_gates.yaml` and the architecture guide at
`docs/architecture/analyzer-promotion-gates.md`. Benchmark reports include
slice-level metrics when queries expose `group`, `kind`, or `tags` metadata.

Use `snowiki benchmark-gate` to evaluate an existing benchmark report without
rerunning the matrix:

```bash
uv run snowiki benchmark-gate \
  --report reports/benchmark-lexical-baselines.json \
  --gate benchmarks/contracts/analyzer_promotion_gates.yaml \
  --gate-report reports/analyzer-gate.json
```

This support command is a report post-processor for CI and manual promotion
checks; it does not change runtime analyzer defaults. A complete analyzer
promotion report must include both the public matrix cells and the Snowiki-owned
slice/golden-query evidence named by the gate contract; missing Snowiki evidence
is an intentional gate failure, not an implicit pass. Use the Snowiki-owned
regression matrix below to generate the product slice/golden-query evidence
required by the gate before considering any runtime default analyzer change.

## Snowiki regression evidence

The Snowiki-owned regression matrix is a small product contract, not a public
benchmark replacement. It exists to catch regressions that public datasets do not
cover: CLI/tool queries, source provenance, temporal/session recall, mixed
Korean-English phrasing, path/API-symbol lookup, and hard negatives.

```bash
uv run snowiki benchmark \
  --matrix benchmarks/contracts/snowiki_regression_matrix.yaml \
  --level regression \
  --target bm25_regex_v1 \
  --target bm25_kiwi_morphology_v1 \
  --report reports/snowiki-regression-analyzers.json
```

The regression assets live under `benchmarks/regression/snowiki_retrieval/` and
are deliberately reviewable JSON. They are anchored in existing Snowiki fixture
and architecture contracts, include distractor documents, and avoid using only
path-title exact matches as evidence.

## Scope

Bench stays lean and only covers the local evaluation runner.

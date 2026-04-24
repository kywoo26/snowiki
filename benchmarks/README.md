# Benchmark README

This bench is a local-first retrieval evaluator. It helps compare retrieval behavior on fixed datasets and fixed levels, using the shipped CLI as the entry point.

## Mission

Bench measures retrieval quality and runtime behavior for local runs. It is a thin evaluator, not a release evidence platform, and it stays separate from governance policy.

## Official datasets

These are the six fixed dataset IDs used by bench:

| Dataset ID | Language |
| :--- | :--- |
| `ms_marco_passage` | en |
| `trec_dl_2020_passage` | en |
| `miracl_ko` | ko |
| `miracl_en` | en |
| `beir_nq` | en |
| `beir_scifact` | en |

## Levels

| Level ID | Query count | Corpus scope |
| :--- | :--- | :--- |
| `quick` | 150 | Up to 50,000 docs |
| `standard` | 500 | Up to 200,000 docs |
| `full` | min all, 1000 | All docs |

Quick and standard levels may sample the corpus for large datasets. Sampling always keeps all judged documents first, then fills any remaining budget with a deterministic random sample so metrics stay valid while index build time stays practical.

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
uv run snowiki benchmark --matrix benchmarks/contracts/official_matrix.yaml --output report.json

# Run a single dataset at quick level
uv run snowiki benchmark --matrix benchmarks/contracts/official_matrix.yaml --output report.json --dataset ms_marco_passage --level quick
```

The `snowiki benchmark` command is the supported surface for local evaluation runs.

Materialize datasets before benchmarking:

```bash
# Fetch the official benchmark datasets into benchmarks/materialized/
uv run snowiki benchmark-fetch
```

For CI smoke runs, `bm25_regex_v1` is the only target executed on pull requests and `main`. Keep tokenizer-variant BM25 targets plus `lexical_regex_v1` in the manual or local comparison lane while choosing the lexical baseline before semantic or hybrid work.

## Manual lexical comparison recipe

Use this manual recipe when comparing the six built-in lexical and BM25 targets across the official six datasets:

```bash
# 1. Materialize the official six datasets once.
uv run snowiki benchmark-fetch \
  --dataset ms_marco_passage \
  --dataset trec_dl_2020_passage \
  --dataset miracl_ko \
  --dataset miracl_en \
  --dataset beir_nq \
  --dataset beir_scifact

# 2. Run the official six-by-six lexical baseline comparison manually.
uv run snowiki benchmark \
  --matrix benchmarks/contracts/official_matrix.yaml \
  --level standard \
  --dataset ms_marco_passage \
  --dataset trec_dl_2020_passage \
  --dataset miracl_ko \
  --dataset miracl_en \
  --dataset beir_nq \
  --dataset beir_scifact \
  --target lexical_regex_v1 \
  --target bm25_regex_v1 \
  --target bm25_kiwi_morphology_v1 \
  --target bm25_kiwi_nouns_v1 \
  --target bm25_mecab_morphology_v1 \
  --target bm25_hf_wordpiece_v1 \
  --output reports/benchmark-lexical-baselines.json
```

## Runner shape

Bench is intentionally thin. Its job is to assemble the input matrix, hand execution to a retrieval target adapter, and return a run result.

The bounded extension seams are:

1. dataset manifests, which describe the fixed datasets
2. target registry, which maps a dataset or runtime target to an adapter
3. metric registry, which defines the metrics bench can score

## Scope

Bench stays lean and only covers the local evaluation runner.

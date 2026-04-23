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

| Level ID | Query count |
| :--- | :--- |
| `quick` | 150 |
| `standard` | 500 |
| `full` | min all, 1000 |

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

## Runner shape

Bench is intentionally thin. Its job is to assemble the input matrix, hand execution to a retrieval target adapter, and return a run result.

The bounded extension seams are:

1. dataset manifests, which describe the fixed datasets
2. target registry, which maps a dataset or runtime target to an adapter
3. metric registry, which defines the metrics bench can score

## Scope

Bench stays lean and only covers the local evaluation runner.

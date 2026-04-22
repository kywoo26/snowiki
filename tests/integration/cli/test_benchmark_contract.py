from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from click.testing import CliRunner

from snowiki.cli.commands import benchmark as benchmark_command
from snowiki.cli.main import app

_TERMINAL_WIDTH = 80
_EXPECTED_BENCHMARK_HELP_LINES = (
    "Usage: snowiki benchmark [OPTIONS]",
    "",
    "Options:",
    "  --preset [core|full|retrieval]  [required]",
    "  --output FILE                   Path to write the machine-readable benchmark",
    "                                  JSON report.  [required]",
    "  --root DIRECTORY                Snowiki storage root (defaults to an isolated",
    "                                  temporary benchmark root)",
    "  --dataset [regression|ms_marco_passage|trec_dl_2020_passage|miracl_ko|miracl_en|beir_nq|beir_scifact]",
    "                                  Benchmark dataset to evaluate. Supported",
    "                                  values are regression plus the official six-",
    "                                  dataset suite.  [default: regression]",
    "  --sample-mode [quick|standard|full]",
    "                                  Official benchmark sample mode (quick=150,",
    "                                  standard=500, full=min(all,1000)). Ignored for",
    "                                  regression.  [default: standard]",
    "  --latency-sample [exhaustive|stratified|fixed_sample]",
    "                                  Override the tier-aware latency sampling",
    "                                  policy for benchmark query timing.",
    "  --layer [pr_official_quick|scheduled_official_standard|release_proof|scheduled_official_broad]",
    "                                  Execution layer for official benchmark runs.",
    "  -h, --help                      Show this message and exit.",
)
_EXPECTED_BENCHMARK_DATASETS = (
    "regression",
    "ms_marco_passage",
    "trec_dl_2020_passage",
    "miracl_ko",
    "miracl_en",
    "beir_nq",
    "beir_scifact",
)


def _successful_benchmark_report() -> dict[str, object]:
    return {
        "benchmark_verdict": {
            "blocking_stage": None,
            "exit_code": 0,
            "order": [
                "structural",
                "retrieval_thresholds",
                "performance_thresholds",
                "informational",
            ],
            "stages": [
                {
                    "blocking": True,
                    "failure_count": 0,
                    "name": "structural",
                    "verdict": "PASS",
                    "warning_count": 0,
                },
                {
                    "blocking": False,
                    "failure_count": 0,
                    "name": "retrieval_thresholds",
                    "verdict": "PASS",
                },
                {
                    "blocking": True,
                    "failure_count": 0,
                    "name": "performance_thresholds",
                    "verdict": "PASS",
                },
                {
                    "blocking": False,
                    "name": "informational",
                    "verdict": "PASS",
                    "warning_count": 0,
                },
            ],
            "verdict": "PASS",
        },
        "corpus": {
            "dataset": "regression",
            "fixtures": [{"path": "fixtures/claude/basic.jsonl", "source": "claude"}],
            "fixtures_indexed": 1,
            "judgments_path": "benchmarks/judgments.json",
            "queries_available": 1,
            "queries_evaluated": 1,
            "queries_path": "benchmarks/queries.json",
            "tier": "regression",
        },
        "dataset": {
            "description": "Deterministic local regression fixtures used for contract tests.",
            "id": "regression",
            "name": "Phase 1 regression fixtures",
            "tier": "regression",
        },
        "generated_at": "2026-04-23T00:00:00Z",
        "metadata": {
            "dataset_id": "regression",
            "dataset_name": "Phase 1 regression fixtures",
            "dataset_tier": "regression",
            "latency_sampling_policy": {
                "mode": "exhaustive",
                "population_query_count": 1,
                "sampled": False,
                "sampled_query_count": 1,
            },
            "report_limits": {
                "applied": False,
                "baselines_truncated": [],
                "entries_removed": 0,
                "per_query_detail_limit": None,
            },
        },
        "performance": {
            "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
            "query": {"p50_ms": 6.0, "p95_ms": 9.0},
            "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
        },
        "performance_threshold_policy": [
            {"metric": "p50_ms", "operator": "<=", "value": 5950.0},
            {"metric": "p95_ms", "operator": "<=", "value": 6300.0},
        ],
        "performance_thresholds": [
            {
                "delta": 5938.0,
                "gate": "ingest",
                "metric": "p50_ms",
                "threshold": 5950.0,
                "value": 12.0,
                "verdict": "PASS",
                "warnings": [],
            },
            {
                "delta": 6282.0,
                "gate": "ingest",
                "metric": "p95_ms",
                "threshold": 6300.0,
                "value": 18.0,
                "verdict": "PASS",
                "warnings": [],
            },
            {
                "delta": 5920.0,
                "gate": "rebuild",
                "metric": "p50_ms",
                "threshold": 5950.0,
                "value": 30.0,
                "verdict": "PASS",
                "warnings": [],
            },
            {
                "delta": 6255.0,
                "gate": "rebuild",
                "metric": "p95_ms",
                "threshold": 6300.0,
                "value": 45.0,
                "verdict": "PASS",
                "warnings": [],
            },
            {
                "delta": 5944.0,
                "gate": "query",
                "metric": "p50_ms",
                "threshold": 5950.0,
                "value": 6.0,
                "verdict": "PASS",
                "warnings": [],
            },
            {
                "delta": 6291.0,
                "gate": "query",
                "metric": "p95_ms",
                "threshold": 6300.0,
                "value": 9.0,
                "verdict": "PASS",
                "warnings": [],
            },
        ],
        "preset": {
            "description": "Known-item benchmark slice for fast regression checks.",
            "name": "core",
            "query_kinds": ["known-item"],
            "top_k": 5,
            "top_ks": [1, 3, 5, 10, 20],
        },
        "protocol": {
            "isolated_root": True,
            "query_mode": "lexical",
            "repetitions": 5,
            "top_k": 5,
            "top_ks": [1, 3, 5, 10, 20],
            "warmups": 1,
        },
        "report_version": "1.3",
        "retrieval": {
            "baselines": {
                "lexical": {
                    "latency": {
                        "max_ms": 1.0,
                        "mean_ms": 1.0,
                        "min_ms": 1.0,
                        "p50_ms": 1.0,
                        "p95_ms": 1.0,
                    },
                    "name": "lexical",
                    "queries": [],
                    "quality": {
                        "overall": {
                            "mrr": 0.79,
                            "ndcg_at_k": 0.81,
                            "recall_at_k": 0.88,
                        },
                        "thresholds": [
                            {
                                "delta": 0.16,
                                "gate": "overall",
                                "metric": "recall_at_k",
                                "threshold": 0.72,
                                "value": 0.88,
                                "verdict": "PASS",
                                "warnings": [],
                            },
                            {
                                "delta": 0.09,
                                "gate": "overall",
                                "metric": "mrr",
                                "threshold": 0.7,
                                "value": 0.79,
                                "verdict": "PASS",
                                "warnings": [],
                            },
                            {
                                "delta": 0.14,
                                "gate": "overall",
                                "metric": "ndcg_at_k",
                                "threshold": 0.67,
                                "value": 0.81,
                                "verdict": "PASS",
                                "warnings": [],
                            },
                        ],
                    },
                    "tokenizer_name": "regex_v1",
                }
            },
            "candidate_matrix": {
                "candidates": [
                    {
                        "admission_status": "admitted",
                        "candidate_name": "regex_v1",
                        "evidence_baseline": "lexical",
                        "role": "control",
                    }
                ],
                "decisions": [
                    {
                        "candidate_name": "regex_v1",
                        "disposition": "promote",
                        "reasons": ["contract_freeze"],
                    }
                ],
            },
            "corpus": {
                "blended_documents": 1,
                "pages_indexed": 1,
                "queries_evaluated": 1,
                "raw_documents": 1,
                "records_indexed": 1,
            },
            "preset": {
                "baselines": ["lexical"],
                "description": "Known-item benchmark slice for fast regression checks.",
                "name": "core",
                "query_kinds": ["known-item"],
                "top_k": 5,
            },
            "threshold_policy": {
                "overall": [
                    {"metric": "recall_at_k", "operator": ">=", "value": 0.72},
                    {"metric": "mrr", "operator": ">=", "value": 0.7},
                    {"metric": "ndcg_at_k", "operator": ">=", "value": 0.67},
                ],
                "slices": {
                    "known-item": [
                        {"metric": "recall_at_k", "operator": ">=", "value": 0.7},
                        {"metric": "mrr", "operator": ">=", "value": 0.6},
                    ],
                    "temporal": [
                        {"metric": "recall_at_k", "operator": ">=", "value": 0.47}
                    ],
                    "topical": [
                        {"metric": "recall_at_k", "operator": ">=", "value": 0.49},
                        {"metric": "ndcg_at_k", "operator": ">=", "value": 0.5},
                    ],
                },
            },
        },
        "structural": {"failures": [], "warnings": []},
    }


def _noop_seed_canonical_benchmark_root(root: Path) -> list[object]:
    del root
    return []


def _generate_successful_benchmark_report(*args: object, **kwargs: object) -> dict[str, object]:
    del args, kwargs
    return _successful_benchmark_report()


def test_benchmark_help_text_matches_frozen_contract() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["benchmark", "--help"], terminal_width=_TERMINAL_WIDTH)

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == list(_EXPECTED_BENCHMARK_HELP_LINES)


def test_benchmark_supported_dataset_choices_match_frozen_contract() -> None:
    assert benchmark_command.PRESET_NAMES == ("core", "full", "retrieval")
    assert benchmark_command.DATASET_NAMES == _EXPECTED_BENCHMARK_DATASETS
    assert benchmark_command.LAYER_NAMES == (
        "pr_official_quick",
        "scheduled_official_standard",
        "release_proof",
        "scheduled_official_broad",
    )


def test_benchmark_invalid_preset_uses_click_usage_exit_code() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["benchmark", "--preset", "invalid_preset"],
        terminal_width=_TERMINAL_WIDTH,
    )

    assert result.exit_code == 2, result.output
    assert result.output.splitlines() == [
        "Usage: snowiki benchmark [OPTIONS]",
        "Try 'snowiki benchmark -h' for help.",
        "",
        "Error: Invalid value for '--preset': 'invalid_preset' is not one of 'core', 'full', 'retrieval'.",
    ]


def test_benchmark_success_contract_writes_expected_report_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        _noop_seed_canonical_benchmark_root,
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        _generate_successful_benchmark_report,
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "core", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert "Unified benchmark verdict: PASS (blocking_stage=None, exit_code=0)" in result.output
    assert f"JSON report written to {report_path}" in result.output

    payload = cast(dict[str, object], json.loads(report_path.read_text(encoding="utf-8")))
    benchmark_verdict = cast(dict[str, object], payload["benchmark_verdict"])
    dataset = cast(dict[str, object], payload["dataset"])
    metadata = cast(dict[str, object], payload["metadata"])
    performance = cast(dict[str, object], payload["performance"])
    protocol = cast(dict[str, object], payload["protocol"])
    retrieval = cast(dict[str, object], payload["retrieval"])
    candidate_matrix = cast(dict[str, object], retrieval["candidate_matrix"])

    assert sorted(payload) == [
        "benchmark_verdict",
        "corpus",
        "dataset",
        "generated_at",
        "metadata",
        "performance",
        "performance_threshold_policy",
        "performance_thresholds",
        "preset",
        "protocol",
        "report_version",
        "retrieval",
        "structural",
    ]
    assert sorted(benchmark_verdict) == [
        "blocking_stage",
        "exit_code",
        "order",
        "stages",
        "verdict",
    ]
    assert sorted(dataset) == ["description", "id", "name", "tier"]
    assert sorted(metadata) == [
        "dataset_id",
        "dataset_name",
        "dataset_tier",
        "latency_sampling_policy",
        "report_limits",
    ]
    assert sorted(performance) == ["ingest", "query", "rebuild"]
    assert sorted(protocol) == [
        "isolated_root",
        "query_mode",
        "repetitions",
        "top_k",
        "top_ks",
        "warmups",
    ]
    assert sorted(retrieval) == [
        "baselines",
        "candidate_matrix",
        "corpus",
        "preset",
        "threshold_policy",
    ]
    assert sorted(candidate_matrix) == ["candidates", "decisions"]
    assert benchmark_verdict["exit_code"] == 0
    assert benchmark_verdict["verdict"] == "PASS"
    assert dataset["id"] == "regression"
    assert payload["report_version"] == "1.3"

    artifact_path = report_path.parent / ".cache" / "tokenizer_comparison.md"
    assert artifact_path.exists()
    assert f"Tokenizer comparison written to {artifact_path}" in result.output
    assert artifact_path.read_text(encoding="utf-8").splitlines() == [
        "Tokenizer comparison:",
        "| Baseline | Tokenizer | Recall@k | MRR  | nDCG@k |",
        "| -------- | --------- | -------- | ---- | ------ |",
        "| lexical  | regex_v1  | 0.88     | 0.79 | 0.81   |",
    ]

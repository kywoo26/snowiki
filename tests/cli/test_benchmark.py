from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from snowiki.cli.commands import benchmark as benchmark_command
from snowiki.cli.main import app


def _fake_report(
    *,
    structural_fail: bool = False,
    retrieval_fail: bool = False,
    performance_fail: bool = False,
    warning_only: bool = False,
) -> dict[str, object]:
    warning_count = 1 if warning_only else 0
    structural_failures = (
        [
            {
                "stage": "lint",
                "code": "L001",
                "path": "normalized/bad.json",
                "message": "missing required key: id",
            }
        ]
        if structural_fail
        else []
    )
    structural_warnings = (
        [
            {
                "stage": "integrity",
                "code": "L003",
                "severity": "warning",
                "path": "compiled/orphan.md",
                "message": "orphan page",
            }
        ]
        if warning_only
        else []
    )
    performance_thresholds = [
        {
            "gate": "ingest",
            "metric": "p50_ms",
            "value": 12.0,
            "delta": 5938.0,
            "verdict": "PASS",
            "threshold": 5950.0,
            "warnings": [],
        },
        {
            "gate": "ingest",
            "metric": "p95_ms",
            "value": 18.0,
            "delta": 6282.0,
            "verdict": "PASS",
            "threshold": 6300.0,
            "warnings": [],
        },
        {
            "gate": "rebuild",
            "metric": "p50_ms",
            "value": 30.0,
            "delta": 5920.0,
            "verdict": "PASS",
            "threshold": 5950.0,
            "warnings": [],
        },
        {
            "gate": "rebuild",
            "metric": "p95_ms",
            "value": 45.0,
            "delta": 6255.0,
            "verdict": "PASS",
            "threshold": 6300.0,
            "warnings": [],
        },
        {
            "gate": "query",
            "metric": "p50_ms",
            "value": 6.0,
            "delta": 5944.0,
            "verdict": "PASS",
            "threshold": 5950.0,
            "warnings": [],
        },
        {
            "gate": "query",
            "metric": "p95_ms",
            "value": 6400.0 if performance_fail else 9.0,
            "delta": 100.0 if performance_fail else 6291.0,
            "verdict": "FAIL" if performance_fail else "PASS",
            "threshold": 6300.0,
            "warnings": [],
        },
    ]
    return {
        "generated_at": "2026-04-10T00:00:00Z",
        "report_version": "1.2",
        "preset": {
            "name": "retrieval",
            "description": "Known-item and topical retrieval benchmark coverage.",
            "query_kinds": ["known-item", "topical"],
            "top_k": 5,
        },
        "structural": {
            "ok": not structural_fail,
            "error_count": len(structural_failures),
            "warning_count": warning_count,
            "failures": structural_failures,
            "warnings": structural_warnings,
        },
        "corpus": {
            "queries_path": "benchmarks/queries.json",
            "judgments_path": "benchmarks/judgments.json",
            "fixtures": [],
            "fixtures_indexed": 12,
            "queries_evaluated": 18,
        },
        "protocol": {
            "isolated_root": True,
            "warmups": 1,
            "repetitions": 5,
            "query_mode": "lexical",
            "top_k": 5,
        },
        "performance": {
            "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
            "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
            "query": {"p50_ms": 6.0, "p95_ms": 6400.0 if performance_fail else 9.0},
        },
        "performance_threshold_policy": [
            {"metric": "p50_ms", "value": 5950.0, "operator": "<="},
            {"metric": "p95_ms", "value": 6300.0, "operator": "<="},
        ],
        "performance_thresholds": performance_thresholds,
        "retrieval": {
            "threshold_policy": {
                "overall": [
                    {"metric": "recall_at_k", "value": 0.72, "operator": ">="},
                    {"metric": "mrr", "value": 0.7, "operator": ">="},
                    {"metric": "ndcg_at_k", "value": 0.67, "operator": ">="},
                ],
                "slices": {
                    "known-item": [
                        {"metric": "recall_at_k", "value": 0.7, "operator": ">="},
                        {"metric": "mrr", "value": 0.6, "operator": ">="},
                    ],
                    "topical": [
                        {"metric": "recall_at_k", "value": 0.49, "operator": ">="},
                        {"metric": "ndcg_at_k", "value": 0.5, "operator": ">="},
                    ],
                    "temporal": [
                        {"metric": "recall_at_k", "value": 0.47, "operator": ">="}
                    ],
                },
            },
            "preset": {
                "name": "retrieval",
                "description": "Known-item and topical retrieval benchmark coverage.",
                "query_kinds": ["known-item", "topical"],
                "top_k": 5,
                "baselines": ["lexical", "bm25s"],
            },
            "corpus": {
                "records_indexed": 12,
                "pages_indexed": 8,
                "raw_documents": 14,
                "blended_documents": 16,
                "queries_evaluated": 18,
            },
            "baselines": {
                "lexical": {
                    "quality": {
                        "thresholds": [
                            {
                                "gate": "overall",
                                "metric": "recall_at_k",
                                "value": 0.82,
                                "delta": 0.1,
                                "verdict": "PASS",
                                "threshold": 0.72,
                                "warnings": [],
                            }
                        ]
                    }
                },
                "bm25s": {
                    "quality": {
                        "thresholds": [
                            {
                                "gate": "overall",
                                "metric": "mrr",
                                "value": 0.68,
                                "delta": 0.02,
                                "verdict": "FAIL" if retrieval_fail else "PASS",
                                "threshold": 0.7,
                                "warnings": [],
                            }
                        ]
                    }
                },
            },
        },
        "benchmark_verdict": {
            "verdict": (
                "FAIL"
                if structural_fail or retrieval_fail or performance_fail
                else "PASS"
            ),
            "exit_code": 1
            if structural_fail or retrieval_fail or performance_fail
            else 0,
            "blocking_stage": (
                "structural"
                if structural_fail
                else "phase1_thresholds"
                if retrieval_fail or performance_fail
                else None
            ),
            "order": [
                "structural",
                "retrieval_thresholds",
                "performance_thresholds",
                "informational",
            ],
            "stages": [
                {
                    "name": "structural",
                    "verdict": "FAIL" if structural_fail else "PASS",
                    "blocking": True,
                    "failure_count": len(structural_failures),
                    "warning_count": warning_count,
                },
                {
                    "name": "retrieval_thresholds",
                    "verdict": "FAIL" if retrieval_fail else "PASS",
                    "blocking": True,
                    "failure_count": 1 if retrieval_fail else 0,
                },
                {
                    "name": "performance_thresholds",
                    "verdict": "FAIL" if performance_fail else "PASS",
                    "blocking": True,
                    "failure_count": 1 if performance_fail else 0,
                },
                {
                    "name": "informational",
                    "verdict": "WARN" if warning_only else "PASS",
                    "blocking": False,
                    "warning_count": warning_count,
                },
            ],
        },
    }


def test_benchmark_writes_json_report_and_renders_unified_phase1_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    fake_report = _fake_report(warning_only=True)
    seeded_roots: list[Path] = []
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: seeded_roots.append(root) or [],
    )
    monkeypatch.setattr(
        benchmark_command, "generate_report", lambda *args, **kwargs: fake_report
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "core", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert len(seeded_roots) == 1
    assert seeded_roots[0] != tmp_path / "root"
    assert seeded_roots[0].name.startswith("snowiki-benchmark-root-")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    retrieval = payload["retrieval"]
    assert "semantic_slots" not in payload
    assert "semantic_slots" not in retrieval
    assert "token_reduction" not in retrieval
    assert payload["performance"]["ingest"] == {"p50_ms": 12.0, "p95_ms": 18.0}
    assert payload["performance_threshold_policy"] == [
        {"metric": "p50_ms", "value": 5950.0, "operator": "<="},
        {"metric": "p95_ms", "value": 6300.0, "operator": "<="},
    ]
    assert retrieval["threshold_policy"]["overall"] == [
        {"metric": "recall_at_k", "value": 0.72, "operator": ">="},
        {"metric": "mrr", "value": 0.7, "operator": ">="},
        {"metric": "ndcg_at_k", "value": 0.67, "operator": ">="},
    ]
    assert retrieval["threshold_policy"]["slices"] == {
        "known-item": [
            {"metric": "recall_at_k", "value": 0.7, "operator": ">="},
            {"metric": "mrr", "value": 0.6, "operator": ">="},
        ],
        "topical": [
            {"metric": "recall_at_k", "value": 0.49, "operator": ">="},
            {"metric": "ndcg_at_k", "value": 0.5, "operator": ">="},
        ],
        "temporal": [{"metric": "recall_at_k", "value": 0.47, "operator": ">="}],
    }
    assert payload["performance_thresholds"][-1]["verdict"] == "PASS"
    assert payload["benchmark_verdict"]["exit_code"] == 0
    assert "Structural verdict: PASS (0 failures, 1 warnings)" in result.output
    assert "Informational warnings:" in result.output
    assert "Performance threshold policy:" in result.output
    assert "Performance threshold verdict: PASS (0 failures)" in result.output
    assert "Retrieval threshold policy:" in result.output
    assert "Retrieval threshold verdict: PASS (0 failures)" in result.output
    assert (
        "Unified benchmark verdict: PASS (blocking_stage=None, exit_code=0)"
        in result.output
    )


def test_benchmark_preserves_explicit_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    explicit_root = tmp_path / "explicit-root"
    seeded_roots: list[Path] = []
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: seeded_roots.append(root) or [],
    )
    monkeypatch.setattr(
        benchmark_command, "generate_report", lambda *args, **kwargs: _fake_report()
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "core",
            "--output",
            str(report_path),
            "--root",
            str(explicit_root),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "ignored-root")},
    )

    assert result.exit_code == 0, result.output
    assert seeded_roots == [explicit_root]


def test_benchmark_returns_non_zero_when_performance_threshold_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: [],
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(performance_fail=True),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "retrieval", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 1, result.output
    assert "Performance threshold failures:" in result.output
    assert "Performance threshold verdict: FAIL (1 failures)" in result.output
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=phase1_thresholds, exit_code=1)"
        in result.output
    )
    assert report_path.exists()


def test_benchmark_structural_failures_take_precedence_over_threshold_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: [],
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(
            structural_fail=True, retrieval_fail=True, performance_fail=True
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "retrieval", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 1, result.output
    assert "Structural failures:" in result.output
    assert "Retrieval threshold failures:" in result.output
    assert "Performance threshold failures:" in result.output
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=structural, exit_code=1)"
        in result.output
    )


def test_benchmark_help_mentions_isolated_temp_root() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["benchmark", "--help"])

    assert result.exit_code == 0, result.output
    assert "defaults to an isolated" in result.output
    assert "temporary benchmark root" in result.output

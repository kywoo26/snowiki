from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Any, cast


def _load_report_symbols(repo_root: Path) -> tuple[Any, Any]:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    report = import_module("snowiki.bench.report")
    benchmark_report = import_module("snowiki.bench.models").BenchmarkReport
    return report, benchmark_report


def test_generate_report_exposes_unified_benchmark_gate(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, benchmark_report = _load_report_symbols(repo_root)
    generate_report = report_module.generate_report
    render_report_text = report_module.render_report_text
    monkeypatch.setattr(
        report_module,
        "validate_phase1_workspace",
        lambda root: {
            "ok": True,
            "status": {"root": root.as_posix(), "zones": {}, "index_manifest": None},
            "lint": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "integrity": {
                "root": root.as_posix(),
                "issues": [
                    {
                        "code": "L003",
                        "severity": "warning",
                        "path": "compiled/orphan.md",
                        "message": "orphan page",
                    }
                ],
                "error_count": 0,
            },
            "failures": [],
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_phase1_latency_evaluation",
        lambda root, preset: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 6400.0},
            },
            "corpus": {"fixtures_indexed": 12, "queries_evaluated": 18},
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": 5,
            },
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_baseline_comparison",
        lambda root, preset: benchmark_report.model_validate(
            {
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
                    "bm25s": {
                        "name": "bm25s",
                        "latency": {
                            "p50_ms": 1.0,
                            "p95_ms": 2.0,
                            "mean_ms": 1.5,
                            "min_ms": 1.0,
                            "max_ms": 2.0,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.82,
                                "mrr": 0.68,
                                "ndcg_at_k": 0.75,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [
                                {
                                    "gate": "overall",
                                    "metric": "mrr",
                                    "value": 0.68,
                                    "delta": 0.02,
                                    "verdict": "FAIL",
                                    "threshold": 0.7,
                                    "warnings": [],
                                }
                            ],
                        },
                        "queries": [],
                    }
                },
            }
        ),
    )

    report = cast(dict[str, Any], generate_report(tmp_path, preset_name="retrieval"))
    retrieval = cast(dict[str, Any], report["retrieval"])
    threshold_policy = cast(dict[str, Any], retrieval["threshold_policy"])
    performance_policy = cast(
        list[dict[str, Any]], report["performance_threshold_policy"]
    )
    performance_thresholds = cast(
        list[dict[str, Any]], report["performance_thresholds"]
    )
    verdict = cast(dict[str, Any], report["benchmark_verdict"])

    assert threshold_policy["overall"][0] == {
        "metric": "recall_at_k",
        "value": 0.72,
        "operator": ">=",
    }
    assert {entry["metric"] for entry in threshold_policy["overall"]} == {
        "recall_at_k",
        "mrr",
        "ndcg_at_k",
    }
    assert threshold_policy["slices"] == {
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
    assert performance_policy == [
        {"metric": "p50_ms", "value": 5950.0, "operator": "<="},
        {"metric": "p95_ms", "value": 6300.0, "operator": "<="},
    ]
    assert report["structural"]["warning_count"] == 1
    assert report["structural"]["error_count"] == 0
    assert "semantic_slots" not in report
    assert "semantic_slots" not in retrieval
    assert "token_reduction" not in retrieval
    assert performance_thresholds[-1] == {
        "gate": "query",
        "metric": "p95_ms",
        "value": 6400.0,
        "delta": 100.0,
        "verdict": "FAIL",
        "threshold": 6300.0,
        "warnings": [],
    }
    assert verdict["blocking_stage"] == "phase1_thresholds"
    assert verdict["exit_code"] == 1
    assert verdict["order"] == [
        "structural",
        "retrieval_thresholds",
        "performance_thresholds",
        "informational",
    ]

    rendered = render_report_text(report)
    assert "Structural verdict: PASS (0 failures, 1 warnings)" in rendered
    assert "Informational warnings:" in rendered
    assert "Performance threshold policy:" in rendered
    assert "Performance threshold failures:" in rendered
    assert "Performance threshold verdict: FAIL (1 failures)" in rendered
    assert "Retrieval threshold failures:" in rendered
    assert "Retrieval threshold verdict: FAIL (1 failures)" in rendered
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=phase1_thresholds, exit_code=1)"
        in rendered
    )


def test_generate_report_structural_failures_block_before_thresholds(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, _ = _load_report_symbols(repo_root)
    generate_report = report_module.generate_report
    render_report_text = report_module.render_report_text
    monkeypatch.setattr(
        report_module,
        "validate_phase1_workspace",
        lambda root: {
            "ok": False,
            "status": {"root": root.as_posix(), "zones": {}, "index_manifest": None},
            "lint": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "integrity": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "failures": [
                {
                    "stage": "lint",
                    "code": "L001",
                    "path": "normalized/bad.json",
                    "message": "missing required key: id",
                }
            ],
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_phase1_latency_evaluation",
        lambda root, preset: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 6400.0},
            },
            "corpus": {"fixtures_indexed": 12, "queries_evaluated": 18},
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": 5,
            },
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_baseline_comparison",
        lambda root, preset: {
            "preset": {},
            "corpus": {},
            "baselines": {
                "bm25s": {
                    "quality": {
                        "thresholds": [
                            {
                                "gate": "overall",
                                "metric": "mrr",
                                "value": 0.68,
                                "delta": 0.02,
                                "verdict": "FAIL",
                                "threshold": 0.7,
                                "warnings": [],
                            }
                        ]
                    }
                }
            },
        },
    )

    report = cast(dict[str, Any], generate_report(tmp_path, preset_name="retrieval"))

    assert "semantic_slots" not in report
    assert "semantic_slots" not in cast(dict[str, Any], report["retrieval"])
    assert "token_reduction" not in cast(dict[str, Any], report["retrieval"])

    assert report["benchmark_verdict"] == {
        "verdict": "FAIL",
        "exit_code": 1,
        "blocking_stage": "structural",
        "order": [
            "structural",
            "retrieval_thresholds",
            "performance_thresholds",
            "informational",
        ],
        "stages": [
            {
                "name": "structural",
                "verdict": "FAIL",
                "blocking": True,
                "failure_count": 1,
                "warning_count": 0,
            },
            {
                "name": "retrieval_thresholds",
                "verdict": "FAIL",
                "blocking": True,
                "failure_count": 1,
            },
            {
                "name": "performance_thresholds",
                "verdict": "FAIL",
                "blocking": True,
                "failure_count": 1,
            },
            {
                "name": "informational",
                "verdict": "PASS",
                "blocking": False,
                "warning_count": 0,
            },
        ],
    }
    rendered = render_report_text(report)
    assert "Structural failures:" in rendered
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=structural, exit_code=1)"
        in rendered
    )

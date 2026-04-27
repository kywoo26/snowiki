from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from snowiki.benchmark_gates import (
    evaluate_analyzer_promotion_gate,
    load_analyzer_promotion_gate,
    render_gate_json,
    render_gate_summary,
)


def _write_gate(path: Path) -> None:
    _ = path.write_text(
        """\
        gate_id: korean_analyzer_promotion_v1
        baseline_target: bm25_regex_v1
        candidate_targets:
          - bm25_kiwi_morphology_v1
        public_matrix:
          matrix: benchmarks/contracts/official_matrix.yaml
          required_dataset_ids:
            - miracl_ko
            - beir_nq
          required_level_ids:
            - standard
        snowiki_slices:
          required_slice_ids:
            - group:ko
            - group:en
            - group:mixed
            - kind:temporal
            - tag:identifier-path-code-heavy
          required_golden_query_ids:
            - cli_tool_command
        thresholds:
          public_korean:
            dataset_id: miracl_ko
            slice_id: all
            must_improve_metrics:
              ndcg_at_10:
                min_relative_delta: 0.03
              recall_at_100:
                min_relative_delta: 0.03
          snowiki_korean:
            slice_id: group:ko
            must_improve_metrics:
              hit_rate_at_5:
                min_relative_delta: 0.03
              mrr_at_10:
                min_relative_delta: 0.03
          mixed_and_identifier_regression:
            slice_ids:
              - group:mixed
              - tag:identifier-path-code-heavy
            max_allowed_absolute_regression: 0.0
            metrics:
              - hit_rate_at_5
              - mrr_at_10
          temporal_regression:
            slice_id: kind:temporal
            max_allowed_absolute_regression: 0.0
            metrics:
              - hit_rate_at_5
              - mrr_at_10
          golden_query_regression:
            fixture: fixtures/retrieval/golden_queries.json
            required_query_ids:
              - cli_tool_command
            max_allowed_top5_regressions: 0
          public_english_regression:
            dataset_ids:
              - beir_nq
            slice_id: all
            max_allowed_absolute_regression: 0.005
            max_allowed_relative_regression: 0.01
            metrics:
              - ndcg_at_10
              - mrr_at_10
              - hit_rate_at_5
          english_regression:
            slice_id: group:en
            max_allowed_absolute_regression: 0.005
            max_allowed_relative_regression: 0.01
            metrics:
              - ndcg_at_10
              - mrr_at_10
              - hit_rate_at_5
          latency:
            max_p95_multiplier_vs_baseline: 1.5
        """,
        encoding="utf-8",
    )


def _cell(
    dataset_id: str,
    target_id: str,
    *,
    ndcg: float,
    recall100: float,
    hit5: float,
    mrr10: float,
    p95: float,
    include_slices: bool = False,
) -> dict[str, object]:
    slices: dict[str, object] = {}
    if include_slices:
        slices = {
            "all": {
                "query_count": 3,
                "metrics": {
                    "ndcg_at_10": ndcg,
                    "recall_at_100": recall100,
                    "hit_rate_at_5": hit5,
                    "mrr_at_10": mrr10,
                },
                "evaluated_queries": {},
            },
            "group:ko": {
                "query_count": 1,
                "metrics": {"hit_rate_at_5": hit5, "mrr_at_10": mrr10},
                "evaluated_queries": {},
            },
            "group:en": {
                "query_count": 1,
                "metrics": {
                    "ndcg_at_10": ndcg,
                    "mrr_at_10": mrr10,
                    "hit_rate_at_5": hit5,
                },
                "evaluated_queries": {},
            },
            "group:mixed": {
                "query_count": 1,
                "metrics": {"hit_rate_at_5": hit5, "mrr_at_10": mrr10},
                "evaluated_queries": {},
            },
            "kind:temporal": {
                "query_count": 1,
                "metrics": {"hit_rate_at_5": hit5, "mrr_at_10": mrr10},
                "evaluated_queries": {},
            },
            "tag:identifier-path-code-heavy": {
                "query_count": 1,
                "metrics": {"hit_rate_at_5": hit5, "mrr_at_10": mrr10},
                "evaluated_queries": {},
            },
        }
    return {
        "dataset_id": dataset_id,
        "level_id": "standard",
        "target_id": target_id,
        "status": "success",
        "metrics": [
            {"metric_id": "ndcg_at_10", "value": ndcg},
            {"metric_id": "recall_at_100", "value": recall100},
            {"metric_id": "hit_rate_at_5", "value": hit5},
            {"metric_id": "mrr_at_10", "value": mrr10},
        ],
        "latency": {"p50": p95 / 2.0, "p95": p95},
        "per_query": {
            "cli_tool_command": {
                "ranked_doc_ids": ["doc-cli"],
                "relevant_doc_ids": ["doc-cli"],
                "latency_ms": 1.0,
                "metrics": {"hit_rate_at_5": hit5},
            }
        },
        "slices": slices,
        "error": None,
    }


def test_analyzer_gate_evaluator_reports_public_and_missing_slice_failures(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "gate.yaml"
    _write_gate(gate_path)
    gate = load_analyzer_promotion_gate(gate_path)
    report: dict[str, object] = {
        "cells": [
            _cell("miracl_ko", "bm25_regex_v1", ndcg=0.35, recall100=0.72, hit5=0.49, mrr10=0.39, p95=5.0),
            _cell("miracl_ko", "bm25_kiwi_morphology_v1", ndcg=0.41, recall100=0.75, hit5=0.57, mrr10=0.44, p95=5.0),
            _cell("beir_nq", "bm25_regex_v1", ndcg=0.38, recall100=0.70, hit5=0.458, mrr10=0.349, p95=1.0),
            _cell("beir_nq", "bm25_kiwi_morphology_v1", ndcg=0.375, recall100=0.71, hit5=0.46, mrr10=0.344, p95=1.1),
        ]
    }

    result = evaluate_analyzer_promotion_gate(gate=gate, report=report)

    assert result.status == "fail"
    assert render_gate_summary(result) == (
        "gate=korean_analyzer_promotion_v1 candidates=1 status=fail failures=14"
    )
    check_statuses = {
        check.check_id: check.status
        for candidate in result.candidates
        for check in candidate.checks
    }
    assert check_statuses["public_korean:ndcg_at_10"] == "pass"
    assert check_statuses["public_korean:recall_at_100"] == "pass"
    assert check_statuses["public_english:beir_nq:mrr_at_10"] == "fail"
    assert check_statuses["required_snowiki_slices"] == "fail"
    payload = render_gate_json(result)
    assert payload["status"] == "fail"
    assert payload["summary"] == {
        "candidate_count": 1,
        "pass_count": 0,
        "fail_count": 1,
        "failure_count": 14,
    }


def test_analyzer_gate_evaluator_passes_when_all_evidence_clears_gate(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "gate.yaml"
    _write_gate(gate_path)
    gate = load_analyzer_promotion_gate(gate_path)
    report: dict[str, object] = {
        "cells": [
            _cell("miracl_ko", "bm25_regex_v1", ndcg=0.35, recall100=0.72, hit5=0.50, mrr10=0.40, p95=5.0, include_slices=True),
            _cell("miracl_ko", "bm25_kiwi_morphology_v1", ndcg=0.41, recall100=0.75, hit5=0.55, mrr10=0.43, p95=5.2, include_slices=True),
            _cell("beir_nq", "bm25_regex_v1", ndcg=0.38, recall100=0.70, hit5=0.45, mrr10=0.35, p95=1.0, include_slices=True),
            _cell("beir_nq", "bm25_kiwi_morphology_v1", ndcg=0.38, recall100=0.70, hit5=0.47, mrr10=0.37, p95=1.1, include_slices=True),
        ]
    }

    result = evaluate_analyzer_promotion_gate(gate=gate, report=report)

    assert result.status == "pass"
    assert result.failures == ()
    assert result.candidates[0].status == "pass"


def test_load_analyzer_gate_rejects_missing_contract(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _ = load_analyzer_promotion_gate(tmp_path / "missing.yaml")


def test_load_analyzer_gate_rejects_malformed_contract(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    _ = gate_path.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected analyzer gate mapping"):
        _ = load_analyzer_promotion_gate(gate_path)


def test_render_gate_json_is_serializable(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    _write_gate(gate_path)
    gate = load_analyzer_promotion_gate(gate_path)
    report: dict[str, object] = {
        "cells": [
            _cell("miracl_ko", "bm25_regex_v1", ndcg=0.35, recall100=0.72, hit5=0.50, mrr10=0.40, p95=5.0),
        ]
    }

    payload = render_gate_json(evaluate_analyzer_promotion_gate(gate=gate, report=report))

    _ = json.dumps(payload)
    assert set(payload) == {
        "generated_at",
        "gate_id",
        "baseline_target",
        "summary",
        "status",
        "candidates",
        "failures",
    }


def test_slice_regression_checks_all_scoped_pairs(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    _write_gate(gate_path)
    gate = load_analyzer_promotion_gate(gate_path)
    report: dict[str, object] = {
        "cells": [
            _cell("miracl_ko", "bm25_regex_v1", ndcg=0.35, recall100=0.72, hit5=0.50, mrr10=0.40, p95=5.0, include_slices=True),
            _cell("miracl_ko", "bm25_kiwi_morphology_v1", ndcg=0.41, recall100=0.75, hit5=0.55, mrr10=0.43, p95=5.2, include_slices=True),
            _cell("beir_nq", "bm25_regex_v1", ndcg=0.38, recall100=0.70, hit5=0.80, mrr10=0.80, p95=1.0, include_slices=True),
            _cell("beir_nq", "bm25_kiwi_morphology_v1", ndcg=0.38, recall100=0.70, hit5=0.10, mrr10=0.10, p95=1.1, include_slices=True),
        ]
    }

    result = evaluate_analyzer_promotion_gate(gate=gate, report=report)

    check = next(
        check
        for candidate in result.candidates
        for check in candidate.checks
        if check.check_id == "mixed_and_identifier_regression:group:mixed:hit_rate_at_5"
    )
    assert check.status == "fail"
    assert check.details["comparison_count"] == 2


def test_required_slice_check_requires_candidate_for_each_baseline_pair(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    _write_gate(gate_path)
    gate = load_analyzer_promotion_gate(gate_path)
    report: dict[str, object] = {
        "cells": [
            _cell("miracl_ko", "bm25_regex_v1", ndcg=0.35, recall100=0.72, hit5=0.50, mrr10=0.40, p95=5.0, include_slices=True),
            _cell("miracl_ko", "bm25_kiwi_morphology_v1", ndcg=0.41, recall100=0.75, hit5=0.55, mrr10=0.43, p95=5.2, include_slices=True),
            _cell("beir_nq", "bm25_regex_v1", ndcg=0.38, recall100=0.70, hit5=0.45, mrr10=0.35, p95=1.0, include_slices=True),
            _cell("beir_nq", "bm25_kiwi_morphology_v1", ndcg=0.38, recall100=0.70, hit5=0.47, mrr10=0.37, p95=1.1),
        ]
    }

    result = evaluate_analyzer_promotion_gate(gate=gate, report=report)

    check = next(
        check
        for candidate in result.candidates
        for check in candidate.checks
        if check.check_id == "required_snowiki_slices"
    )
    assert check.status == "fail"
    missing_slices = check.details["missing_slices"]
    assert isinstance(missing_slices, list)
    assert {
        "slice_id": "group:ko",
        "dataset_id": "beir_nq",
        "level_id": "standard",
        "reason": "missing_candidate_slice",
    } in missing_slices


def test_golden_query_regression_checks_each_dataset_level_pair(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    _write_gate(gate_path)
    gate = load_analyzer_promotion_gate(gate_path)
    report: dict[str, object] = {
        "cells": [
            _cell("miracl_ko", "bm25_regex_v1", ndcg=0.35, recall100=0.72, hit5=1.0, mrr10=0.40, p95=5.0, include_slices=True),
            _cell("miracl_ko", "bm25_kiwi_morphology_v1", ndcg=0.41, recall100=0.75, hit5=1.0, mrr10=0.43, p95=5.2, include_slices=True),
            _cell("beir_nq", "bm25_regex_v1", ndcg=0.38, recall100=0.70, hit5=1.0, mrr10=0.35, p95=1.0, include_slices=True),
            _cell("beir_nq", "bm25_kiwi_morphology_v1", ndcg=0.38, recall100=0.70, hit5=0.0, mrr10=0.35, p95=1.1, include_slices=True),
        ]
    }

    result = evaluate_analyzer_promotion_gate(gate=gate, report=report)

    check = next(
        check
        for candidate in result.candidates
        for check in candidate.checks
        if check.check_id == "golden_query_regression"
    )
    assert check.status == "fail"
    regressions = check.details["regressions"]
    assert isinstance(regressions, list)
    assert len(regressions) == 1
    first_regression = regressions[0]
    assert isinstance(first_regression, dict)
    first_regression = cast(dict[str, object], first_regression)
    assert first_regression["dataset_id"] == "beir_nq"

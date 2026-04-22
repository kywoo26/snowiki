from __future__ import annotations

from importlib import import_module
from typing import Any, cast


def _load_report_symbols() -> tuple[Any, Any]:
    report = import_module("snowiki.bench.reporting.report")
    benchmark_report = import_module("snowiki.bench.reporting.models").BenchmarkReport
    return report, benchmark_report



def test_report_internal_helpers_cover_coercion_bounding_and_empty_audit() -> None:
    report_module, benchmark_report = _load_report_symbols()

    assert report_module._coerce_int(True) == 1
    assert report_module._coerce_int(7) == 7
    assert report_module._coerce_int(7.9) == 7
    assert report_module._coerce_int("8") == 8
    assert report_module._coerce_int("bad", default=9) == 9
    assert report_module._coerce_int(object(), default=9) == 9

    bounded = report_module._bound_retrieval_payload(
        {
            "baselines": {
                "lexical": {
                    "queries": {"q1": [{"id": "doc-1"}]},
                    "quality": {
                        "overall": {"per_query": [{"query_id": "q1"}]},
                        "slices": {
                            "group": {"hidden": {"per_query": [{"query_id": "q1"}]}},
                            "kind": {"raw": "keep"},
                            "subset": {"hidden": {"per_query": [{"query_id": "q1"}]}},
                        },
                    },
                },
                "raw": "keep-me",
            }
        },
        query_count=21,
        tier="official_suite",
    )

    assert bounded == {
        "applied": False,
        "per_query_detail_limit": None,
        "entries_removed": 0,
        "baselines_truncated": [],
    }

    assert report_module.generate_audit_report(benchmark_report.model_validate({})) == {}


def test_dataset_payload_from_manifest_covers_regression_and_official_paths() -> None:
    from snowiki.bench.datasets.anchors.korean import load_miracl_ko_sample

    report_module, _ = _load_report_symbols()

    regression_payload = report_module._dataset_payload_from_manifest(
        None,
        dataset_name="regression",
    )
    assert regression_payload == {
        "id": "regression",
        "name": "Phase 1 regression fixtures",
        "tier": "regression_harness",
        "description": (
            "Deterministic local regression fixtures used for "
            "candidate-screening benchmark runs."
        ),
    }

    visible_payload = report_module._dataset_payload_from_manifest(
        load_miracl_ko_sample(size=2),
        dataset_name="miracl_ko",
    )
    assert visible_payload["tier"] == "official_suite"
    assert cast(dict[str, object], visible_payload["metadata"])["sample_size"] == 2
    assert "provenance" in visible_payload


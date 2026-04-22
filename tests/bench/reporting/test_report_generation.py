from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, cast

from snowiki.bench.evaluation.candidates import CANDIDATE_MATRIX

_EXPANDED_BASELINES = [
    "lexical",
    "bm25s",
    "bm25s_kiwi_nouns",
    "bm25s_kiwi_full",
    "bm25s_mecab_full",
    "bm25s_hf_wordpiece",
]


def _provenance_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_class": "human_curated",
        "authoring_method": "human_only",
        "license": "CC-BY-4.0",
        "collection_method": "manual_entry",
        "visibility_tier": "public",
        "contamination_status": "clean",
        "family_dedupe_key": "family-report",
        "authority_tier": "official_suite",
    }
    payload.update(overrides)
    return payload


def _asset_manifest_payload(
    asset_id: str, path: str, **provenance_overrides: object
) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "path": path,
        "provenance": _provenance_payload(**provenance_overrides),
    }


def _load_report_symbols() -> tuple[Any, Any]:
    report = import_module("snowiki.bench.reporting.report")
    benchmark_report = import_module("snowiki.bench.reporting.models").BenchmarkReport
    return report, benchmark_report


def test_generate_report_exposes_unified_benchmark_gate(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, benchmark_report = _load_report_symbols()
    generate_report = report_module.generate_report
    render_report_text = report_module.render_report_text
    monkeypatch.setattr(
        report_module,
        "validate_workspace",
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
        "run_latency_evaluation",
        lambda root, preset, **kwargs: {
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
                "sampling_policy": {
                    "mode": "exhaustive",
                    "population_query_count": 18,
                    "sampled_query_count": 18,
                    "sampled": False,
                },
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
                    "baselines": _EXPANDED_BASELINES,
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
                        "name": "lexical",
                        "latency": {
                            "p50_ms": 1.1,
                            "p95_ms": 2.1,
                            "mean_ms": 1.6,
                            "min_ms": 1.1,
                            "max_ms": 2.1,
                        },
                        "quality": {
                            "tokenizer_name": "regex_v1",
                            "overall": {
                                "recall_at_k": 0.83,
                                "mrr": 0.71,
                                "ndcg_at_k": 0.76,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    },
                    "bm25s": {
                        "name": "bm25s",
                        "tokenizer_name": "kiwi_morphology_v1",
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
                    },
                    "bm25s_kiwi_nouns": {
                        "name": "bm25s_kiwi_nouns",
                        "tokenizer_name": "kiwi_nouns_v1",
                        "latency": {
                            "p50_ms": 1.2,
                            "p95_ms": 2.2,
                            "mean_ms": 1.7,
                            "min_ms": 1.2,
                            "max_ms": 2.2,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.81,
                                "mrr": 0.7,
                                "ndcg_at_k": 0.74,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    },
                    "bm25s_kiwi_full": {
                        "name": "bm25s_kiwi_full",
                        "latency": {
                            "p50_ms": 1.3,
                            "p95_ms": 2.3,
                            "mean_ms": 1.8,
                            "min_ms": 1.3,
                            "max_ms": 2.3,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.84,
                                "mrr": 0.72,
                                "ndcg_at_k": 0.77,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    },
                    "bm25s_mecab_full": {
                        "name": "bm25s_mecab_full",
                        "latency": {
                            "p50_ms": 1.35,
                            "p95_ms": 2.35,
                            "mean_ms": 1.85,
                            "min_ms": 1.35,
                            "max_ms": 2.35,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.78,
                                "mrr": 0.67,
                                "ndcg_at_k": 0.72,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    },
                    "bm25s_hf_wordpiece": {
                        "name": "bm25s_hf_wordpiece",
                        "latency": {
                            "p50_ms": 1.25,
                            "p95_ms": 2.25,
                            "mean_ms": 1.75,
                            "min_ms": 1.25,
                            "max_ms": 2.25,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.79,
                                "mrr": 0.69,
                                "ndcg_at_k": 0.73,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    },
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
    metadata = cast(dict[str, Any], report["metadata"])
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
    assert report["report_version"] == "1.4"
    assert cast(dict[str, Any], report["preset"])["top_ks"] == [1, 3, 5, 10, 20]
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
    assert metadata["dataset_tier"] == "regression_harness"
    assert metadata["authority_class"] == "regression_harness"
    assert metadata["latency_sampling_policy"] == {
        "mode": "exhaustive",
        "population_query_count": 18,
        "sampled_query_count": 18,
        "sampled": False,
    }
    assert report["structural"]["warning_count"] == 1
    assert report["structural"]["error_count"] == 0
    assert "semantic_slots" not in report
    assert "semantic_slots" not in retrieval
    assert "token_reduction" not in retrieval
    assert "runtime_generation" not in report
    candidate_matrix = cast(dict[str, Any], retrieval["candidate_matrix"])
    assert candidate_matrix == {
        "candidates": [
            candidate.model_dump(mode="json") for candidate in CANDIDATE_MATRIX
        ]
    }
    assert "benchmark_verdict" not in retrieval
    assert retrieval["preset"]["baselines"] == _EXPANDED_BASELINES
    assert performance_thresholds[-1] == {
        "gate": "query",
        "metric": "p95_ms",
        "value": 6400.0,
        "delta": 100.0,
        "verdict": "FAIL",
        "threshold": 6300.0,
        "warnings": [],
    }
    assert verdict["blocking_stage"] == "performance_thresholds"
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
    assert "Latency sampling: mode=exhaustive, queries=18/18" in rendered
    assert "Performance threshold failures:" in rendered
    assert "Performance threshold verdict: FAIL (1 failures)" in rendered
    assert "Retrieval threshold failures:" in rendered
    assert "Retrieval threshold verdict: FAIL (1 failures)" in rendered
    assert "Tokenizer comparison:" in rendered
    assert "| Baseline" in rendered
    assert "| bm25s_kiwi_nouns" in rendered
    assert "| bm25s" in rendered
    assert "| kiwi_morphology_v1" in rendered
    assert "top_ks=[1, 3, 5, 10, 20]" in rendered
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=performance_thresholds, exit_code=1)"
        in rendered
    )


def test_generate_report_structural_failures_block_before_thresholds(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, _ = _load_report_symbols()
    generate_report = report_module.generate_report
    render_report_text = report_module.render_report_text
    monkeypatch.setattr(
        report_module,
        "validate_workspace",
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
        "run_latency_evaluation",
        lambda root, preset, **kwargs: {
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
                "sampling_policy": {
                    "mode": "exhaustive",
                    "population_query_count": 18,
                    "sampled_query_count": 18,
                    "sampled": False,
                },
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
    assert cast(dict[str, Any], report["retrieval"])["candidate_matrix"] == {
        "candidates": [
            candidate.model_dump(mode="json") for candidate in CANDIDATE_MATRIX
        ]
    }
    assert (
        cast(dict[str, Any], report["benchmark_verdict"])["blocking_stage"]
        == "structural"
    )

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


def test_generate_report_official_suite_retrieval_failures_are_informational(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    from snowiki.bench.runtime.corpus import BenchmarkCorpusManifest

    report_module, benchmark_report = _load_report_symbols()
    generate_report = report_module.generate_report
    render_report_text = report_module.render_report_text
    manifest = BenchmarkCorpusManifest(
        tier="official_suite",
        documents=[{"id": "doc-1", "content": "Official suite corpus note."}],
        queries=[
            {
                "id": "q-1",
                "text": "official suite corpus note",
                "group": "mixed_ko_en",
                "kind": "known-item",
            }
        ],
        judgments={
            "q-1": [
                {"query_id": "q-1", "doc_id": "doc-1", "relevance": 1}
            ]
        },
        dataset_id="miracl_ko",
        dataset_name="MIRACL Korean",
        dataset_description="Official benchmark manifest sample.",
    )
    monkeypatch.setattr(
        report_module,
        "validate_workspace",
        lambda root: {
            "ok": True,
            "status": {"root": root.as_posix(), "zones": {}, "index_manifest": None},
            "lint": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "integrity": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "failures": [],
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 12.0},
            },
            "corpus": {
                "dataset": "miracl_ko",
                "tier": "official_suite",
                "queries_available": 1,
                "queries_evaluated": 1,
            },
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": 5,
                "dataset_mode": "manifest",
                "sampling_policy": {
                    "mode": "stratified",
                    "population_query_count": 1,
                    "sampled_query_count": 1,
                    "sampled": False,
                    "strata": ["mixed_ko_en"],
                },
            },
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_baseline_comparison",
        lambda root, preset, **kwargs: benchmark_report.model_validate(
            {
                "preset": {
                    "name": preset.name,
                    "description": preset.description,
                    "query_kinds": list(preset.query_kinds),
                    "top_k": preset.top_k,
                    "top_ks": list(preset.top_ks),
                    "baselines": ["lexical"],
                },
                "corpus": {
                    "records_indexed": 1,
                    "pages_indexed": 1,
                    "raw_documents": 1,
                    "blended_documents": 1,
                    "queries_evaluated": 1,
                },
                "baselines": {
                    "lexical": {
                        "name": "lexical",
                        "latency": {
                            "p50_ms": 1.0,
                            "p95_ms": 2.0,
                            "mean_ms": 1.5,
                            "min_ms": 1.0,
                            "max_ms": 2.0,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.8,
                                "mrr": 0.4,
                                "ndcg_at_k": 0.45,
                                "top_k": 5,
                                "queries_evaluated": 1,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [
                                {
                                    "gate": "overall",
                                    "metric": "mrr",
                                    "value": 0.4,
                                    "delta": -0.3,
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

    report = cast(
        dict[str, Any],
        generate_report(
            tmp_path,
            preset_name="retrieval",
            manifest=manifest,
            dataset_name="miracl_ko",
        ),
    )
    verdict = cast(dict[str, Any], report["benchmark_verdict"])
    stages = cast(list[dict[str, Any]], verdict["stages"])

    assert verdict["verdict"] == "PASS"
    assert verdict["exit_code"] == 0
    assert verdict["blocking_stage"] is None
    metadata = cast(dict[str, Any], report["metadata"])
    assert stages[1] == {
        "name": "retrieval_thresholds",
        "verdict": "FAIL",
        "blocking": False,
        "failure_count": 1,
    }
    assert "sample_mode" not in metadata
    assert "queries_available" not in metadata
    assert "sample_size" not in metadata
    rendered = render_report_text(report)
    assert "Retrieval threshold failures:" in rendered
    assert "Dataset sample mode:" not in rendered
    assert (
        "Unified benchmark verdict: PASS (blocking_stage=None, exit_code=0)"
        in rendered
    )


def test_generate_report_includes_provenance_metadata_when_present(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, benchmark_report = _load_report_symbols()
    generate_report = report_module.generate_report
    monkeypatch.setattr(
        report_module,
        "validate_workspace",
        lambda root: {
            "ok": True,
            "status": {"root": root.as_posix(), "zones": {}, "index_manifest": None},
            "lint": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "integrity": {"root": root.as_posix(), "issues": [], "error_count": 0},
            "failures": [],
        },
    )
    monkeypatch.setattr(
        report_module,
        "run_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 6200.0},
            },
            "corpus": {"fixtures_indexed": 12, "queries_evaluated": 18},
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": 5,
                "sampling_policy": {
                    "mode": "exhaustive",
                    "population_query_count": 18,
                    "sampled_query_count": 18,
                    "sampled": False,
                },
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
                    "baselines": ["lexical"],
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
                        "name": "lexical",
                        "tokenizer_name": "regex_v1",
                        "latency": {
                            "p50_ms": 1.1,
                            "p95_ms": 2.1,
                            "mean_ms": 1.6,
                            "min_ms": 1.1,
                            "max_ms": 2.1,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.83,
                                "mrr": 0.71,
                                "ndcg_at_k": 0.76,
                                "top_k": 5,
                                "queries_evaluated": 18,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    }
                },
                "corpus_assets": [
                    _asset_manifest_payload(
                        "doc-1", "benchmarks/corpus/doc-1.json", source_class="public_dataset"
                    )
                ],
                "query_assets": [
                    _asset_manifest_payload(
                        "query-1",
                        "benchmarks/queries/query-1.json",
                        source_class="human_curated",
                        collection_method="manual_entry",
                        authority_tier="official_suite",
                    )
                ],
                "judgment_assets": [
                    _asset_manifest_payload(
                        "judgment-1",
                        "benchmarks/judgments/judgment-1.json",
                        source_class="mixed",
                        authoring_method="human_reviewed",
                        collection_method="manual_entry",
                        authority_tier="official_suite",
                    )
                ],
            }
        ),
    )

    report = cast(dict[str, Any], generate_report(tmp_path, preset_name="retrieval"))
    retrieval = cast(dict[str, Any], report["retrieval"])

    assert retrieval["corpus_assets"] == [
        _asset_manifest_payload(
            "doc-1", "benchmarks/corpus/doc-1.json", source_class="public_dataset"
        )
    ]
    assert retrieval["query_assets"][0]["provenance"]["authority_tier"] == "official_suite"
    assert retrieval["judgment_assets"][0]["provenance"]["authoring_method"] == "human_reviewed"


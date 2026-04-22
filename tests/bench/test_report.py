from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from snowiki.bench.matrix import CANDIDATE_MATRIX

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
    report = import_module("snowiki.bench.report")
    benchmark_report = import_module("snowiki.bench.models").BenchmarkReport
    return report, benchmark_report


def test_generate_report_exposes_unified_benchmark_gate(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, benchmark_report = _load_report_symbols()
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
        "Unified benchmark verdict: FAIL (blocking_stage=phase1_thresholds, exit_code=1)"
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
    from snowiki.bench.corpus import BenchmarkCorpusManifest

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
        "validate_phase1_workspace",
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
        "run_phase1_latency_evaluation",
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
        "validate_phase1_workspace",
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
        "run_phase1_latency_evaluation",
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


def test_tier_aware_latency_policy_is_applied() -> None:
    from snowiki.bench.phase1_latency import get_latency_policy

    regression_policy = get_latency_policy("regression_harness", 90)
    official_large_policy = get_latency_policy("official_suite", 100)
    official_small_policy = get_latency_policy("official_suite", 20)

    assert regression_policy.mode == "exhaustive"
    assert regression_policy.sample_size is None
    assert official_large_policy.mode == "stratified"
    assert official_small_policy.mode == "exhaustive"


def test_stratified_sampling_works_for_large_tiers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snowiki.bench import phase1_latency
    from snowiki.bench.anchors.korean import load_miracl_ko_sample
    from snowiki.bench.presets import get_preset

    fixture_path = tmp_path / "fixture.jsonl"
    _ = fixture_path.write_text("{}\n", encoding="utf-8")
    manifest = load_miracl_ko_sample(size=100)

    monkeypatch.setattr(phase1_latency, "PHASE_1_WARMUPS", 0)
    monkeypatch.setattr(phase1_latency, "PHASE_1_REPETITIONS", 1)
    monkeypatch.setattr(
        phase1_latency,
        "_canonical_fixtures",
        lambda: ({"source": "claude", "path": fixture_path},),
    )
    monkeypatch.setattr(
        phase1_latency,
        "run_ingest",
        lambda path, *, source, root: {"path": path.as_posix(), "source": source},
    )
    monkeypatch.setattr(
        phase1_latency,
        "run_rebuild",
        lambda root: {"root": root.as_posix()},
    )

    query_calls: list[str] = []

    def fake_query(root: Path, query: str, *, mode: str, top_k: int) -> dict[str, object]:
        query_calls.append(query)
        return {"query": query, "mode": mode, "top_k": top_k}

    monkeypatch.setattr(phase1_latency, "run_query", fake_query)
    ticks = iter([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    monkeypatch.setattr("time.perf_counter", lambda: next(ticks))

    report = phase1_latency.run_phase1_latency_evaluation(
        tmp_path / "requested-root",
        preset=get_preset("retrieval"),
        manifest=manifest,
        dataset_name="miracl_ko",
    )
    protocol = cast(dict[str, Any], report["protocol"])
    sampling_policy = cast(dict[str, Any], protocol["sampling_policy"])
    corpus = cast(dict[str, Any], report["corpus"])

    assert sampling_policy["mode"] == "stratified"
    assert sampling_policy["sampled"] is True
    assert cast(list[str], sampling_policy["strata"]) == ["known-item", "topical"]
    assert corpus["queries_available"] == 100
    assert corpus["queries_evaluated"] == 20
    assert len(query_calls) == 20


def test_report_includes_sampling_policy_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snowiki.bench.anchors.korean import load_miracl_ko_sample

    report_module, benchmark_report = _load_report_symbols()
    manifest = load_miracl_ko_sample(size=60)
    monkeypatch.setattr(
        report_module,
        "validate_phase1_workspace",
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
        "run_phase1_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 12.0},
            },
            "corpus": {
                "dataset": "miracl_ko",
                "tier": "official_suite",
                "queries_available": 60,
                "queries_evaluated": 20,
            },
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": 5,
                "top_ks": [1, 3, 5, 10, 20],
                "dataset_mode": "manifest",
                "sampling_policy": {
                    "mode": "stratified",
                    "population_query_count": 60,
                    "sampled_query_count": 20,
                    "sampled": True,
                    "strata": ["known-item", "topical"],
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
                    "records_indexed": 60,
                    "pages_indexed": 60,
                    "raw_documents": 60,
                    "blended_documents": 60,
                    "queries_evaluated": 60,
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
                                "mrr": 0.7,
                                "ndcg_at_k": 0.75,
                                "top_k": 5,
                                "queries_evaluated": 60,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    }
                },
            }
        ),
    )

    report = cast(
        dict[str, Any],
        report_module.generate_report(
            tmp_path,
            preset_name="retrieval",
            manifest=manifest,
            dataset_name="miracl_ko",
        ),
    )
    metadata = cast(dict[str, Any], report["metadata"])
    rendered = report_module.render_report_text(report)

    assert metadata["dataset_name"] == manifest.dataset_name
    assert metadata["dataset_tier"] == "official_suite"
    assert metadata["authority_class"] == "official_suite"
    assert metadata["latency_sampling_policy"]["mode"] == "stratified"
    assert metadata["latency_sampling_policy"]["sampled_query_count"] == 20
    assert report["performance_threshold_policy"] == []
    assert "Latency sampling: mode=stratified, queries=20/60" in rendered


def test_report_includes_dataset_sample_metadata_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snowiki.bench.corpus import BenchmarkCorpusManifest

    report_module, benchmark_report = _load_report_symbols()
    manifest = BenchmarkCorpusManifest(
        tier="official_suite",
        documents=[{"id": "doc-1", "content": "Official suite document."}],
        queries=[
            {
                "id": "q-1",
                "text": "official suite query",
                "group": "ko",
                "kind": "known-item",
            }
        ],
        judgments={
            "q-1": [{"query_id": "q-1", "doc_id": "doc-1", "relevance": 1}]
        },
        dataset_id="miracl_ko",
        dataset_name="MIRACL Korean",
        dataset_description="Deterministic manifest sampled from cached public assets.",
        dataset_metadata={
            "sample_mode": "quick",
            "queries_available": 812,
            "sample_size": 150,
            "sampling_strategy": "deterministic_qrels_bounded_mode",
            "synthetic_sample": False,
        },
    )
    monkeypatch.setattr(
        report_module,
        "validate_phase1_workspace",
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
        "run_phase1_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 12.0},
            },
            "corpus": {
                "dataset": "miracl_ko",
                "tier": "official_suite",
                "queries_available": 200,
                "queries_evaluated": 20,
            },
                "protocol": {
                    "isolated_root": True,
                    "warmups": 1,
                    "repetitions": 5,
                    "query_mode": "lexical",
                    "top_k": 5,
                    "top_ks": [1, 3, 5, 10, 20],
                    "dataset_mode": "manifest",
                    "sampling_policy": {
                        "mode": "stratified",
                        "population_query_count": 150,
                        "sampled_query_count": 20,
                        "sampled": True,
                        "strata": ["known-item"],
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
                                "mrr": 0.7,
                                "ndcg_at_k": 0.75,
                                "top_k": 5,
                                "queries_evaluated": 1,
                                "per_query": [],
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": [],
                    }
                },
            }
        ),
    )

    report = cast(
        dict[str, Any],
        report_module.generate_report(
            tmp_path,
            preset_name="retrieval",
            manifest=manifest,
            dataset_name="miracl_ko",
        ),
    )
    metadata = cast(dict[str, Any], report["metadata"])
    dataset_metadata = cast(dict[str, Any], cast(dict[str, Any], report["dataset"])["metadata"])
    rendered = report_module.render_report_text(report)

    assert dataset_metadata["sample_mode"] == "quick"
    assert dataset_metadata["queries_available"] == 812
    assert dataset_metadata["sample_size"] == 150
    assert metadata["sample_mode"] == "quick"
    assert metadata["queries_available"] == 812
    assert metadata["sample_size"] == 150
    assert "sampling_strategy" not in metadata
    assert metadata["latency_sampling_policy"] == {
        "mode": "stratified",
        "population_query_count": 150,
        "sampled_query_count": 20,
        "sampled": True,
        "strata": ["known-item"],
    }
    assert "Dataset sample mode: quick (150/812 queries)" in rendered


def test_report_size_is_bounded_for_large_tiers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snowiki.bench.anchors.korean import load_miracl_ko_sample

    report_module, benchmark_report = _load_report_symbols()
    manifest = load_miracl_ko_sample(size=60)
    monkeypatch.setattr(
        report_module,
        "validate_phase1_workspace",
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
        "run_phase1_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 12.0},
            },
            "corpus": {
                "dataset": "miracl_ko",
                "tier": "official_suite",
                "queries_available": 60,
                "queries_evaluated": 20,
            },
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": 5,
                "top_ks": [1, 3, 5, 10, 20],
                "dataset_mode": "manifest",
                "sampling_policy": {
                    "mode": "stratified",
                    "population_query_count": 60,
                    "sampled_query_count": 20,
                    "sampled": True,
                    "strata": ["known-item", "topical"],
                },
            },
        },
    )

    per_query = [
        {
            "query_id": f"q-{index:03d}",
            "ranked_ids": [f"doc-{index:03d}"],
            "relevant_ids": [f"doc-{index:03d}"],
            "tags": ["ko"],
            "recall_at_k": 1.0,
            "reciprocal_rank": 1.0,
            "ndcg_at_k": 1.0,
        }
        for index in range(60)
    ]
    baseline_queries = [
        {
            "query_id": f"q-{index:03d}",
            "hits": [
                {
                    "id": f"doc-{index:03d}",
                    "path": f"normalized/doc-{index:03d}.json",
                    "score": 1.0,
                }
            ],
        }
        for index in range(60)
    ]
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
                    "records_indexed": 60,
                    "pages_indexed": 60,
                    "raw_documents": 60,
                    "blended_documents": 60,
                    "queries_evaluated": 60,
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
                                "mrr": 0.7,
                                "ndcg_at_k": 0.75,
                                "top_k": 5,
                                "queries_evaluated": 60,
                                "per_query": per_query,
                            },
                            "slices": {"group": {}, "kind": {}},
                            "thresholds": [],
                        },
                        "queries": baseline_queries,
                    }
                },
            }
        ),
    )

    report = cast(
        dict[str, Any],
        report_module.generate_report(
            tmp_path,
            preset_name="retrieval",
            manifest=manifest,
            dataset_name="miracl_ko",
        ),
    )
    metadata = cast(dict[str, Any], report["metadata"])
    lexical = cast(dict[str, Any], cast(dict[str, Any], report["retrieval"])["baselines"])[
        "lexical"
    ]

    assert metadata["report_limits"]["applied"] is True
    assert metadata["report_limits"]["per_query_detail_limit"] == 20
    assert len(lexical["queries"]) == 20
    assert len(lexical["quality"]["overall"]["per_query"]) == 20


def test_generate_report_rejects_authoritative_assets_without_required_provenance(
    tmp_path: Path, monkeypatch, repo_root: Path
) -> None:
    report_module, _ = _load_report_symbols()
    generate_report = report_module.generate_report
    monkeypatch.setattr(
        report_module,
        "validate_phase1_workspace",
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
        "run_phase1_latency_evaluation",
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
        lambda root, preset: {
            "preset": {},
            "corpus": {},
            "baselines": {},
            "corpus_assets": [
                {
                    "asset_id": "doc-1",
                    "path": "benchmarks/corpus/doc-1.json",
                    "provenance": {
                        "source_class": "public_dataset",
                        "authoring_method": "human_only",
                        "license": "CC-BY-4.0",
                        "collection_method": "manual_entry",
                        "contamination_status": "clean",
                        "authority_tier": "official_suite",
                    },
                }
            ],
        },
    )

    with pytest.raises(ValidationError):
        _ = generate_report(tmp_path, preset_name="retrieval")


def _baseline_payload_for_verdict(
    *,
    name: str,
    mixed_value: float = 0.9,
    ko_value: float = 0.9,
    en_value: float = 0.9,
    p95_ms: float = 10.0,
    overall_fail: bool = False,
    include_overall_threshold: bool = True,
) -> dict[str, object]:
    thresholds: list[dict[str, object]] = []
    if include_overall_threshold:
        thresholds.append(
            {
                "gate": "overall",
                "metric": "mrr",
                "value": mixed_value,
                "delta": mixed_value - 0.7,
                "verdict": "FAIL" if overall_fail else "PASS",
                "threshold": 0.7,
                "warnings": [],
            }
        )

    def _group_payload(value: float) -> dict[str, object]:
        return {
            "recall_at_k": value,
            "mrr": value,
            "ndcg_at_k": value,
            "top_k": 5,
            "queries_evaluated": 1,
            "per_query": [],
        }

    return {
        "name": name,
        "latency": {
            "p50_ms": min(p95_ms, 5.0),
            "p95_ms": p95_ms,
            "mean_ms": p95_ms,
            "min_ms": min(p95_ms, 5.0),
            "max_ms": p95_ms,
        },
        "quality": {
            "overall": {
                "recall_at_k": mixed_value,
                "mrr": mixed_value,
                "ndcg_at_k": mixed_value,
                "top_k": 5,
                "queries_evaluated": 1,
                "per_query": [],
            },
            "slices": {
                "group": {
                    "mixed": _group_payload(mixed_value),
                    "ko": _group_payload(ko_value),
                    "en": _group_payload(en_value),
                },
                "kind": {},
            },
            "thresholds": thresholds,
        },
        "queries": [],
    }


def _operational_evidence_payload(*, measured: bool) -> dict[str, object]:
    status = "measured" if measured else "not_measured"
    return {
        "memory_peak_rss_mb": 1.0 if measured else None,
        "memory_evidence_status": status,
        "disk_size_mb": 1.0 if measured else None,
        "disk_size_evidence_status": status,
        "platform_support": {
            "macos": "supported",
            "linux_x86_64": "supported",
            "linux_aarch64": "supported",
            "windows": "supported",
            "fallback_behavior": "none",
        },
        "install_ergonomics": {
            "prebuilt_available": True,
            "build_from_source_required": False,
            "hidden_bootstrap_steps": False,
            "operational_complexity": "low",
        },
        "zero_cost_admission": True,
        "admission_reason": "test",
    }


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
    from snowiki.bench.anchors.korean import load_miracl_ko_sample

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


def test_baselines_parsing_helpers_cover_error_and_path_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    baselines = import_module("snowiki.bench.baselines")

    absolute_path = tmp_path / "absolute.json"
    absolute_path.write_text("{}", encoding="utf-8")
    resolved_path, label = baselines._resolve_benchmark_asset_path(
        tmp_path,
        absolute_path,
        default_relative_path="ignored.json",
    )
    assert resolved_path == absolute_path
    assert label == absolute_path.as_posix()

    root_relative = tmp_path / "queries.json"
    root_relative.write_text("{}", encoding="utf-8")
    resolved_path, label = baselines._resolve_benchmark_asset_path(
        tmp_path,
        "queries.json",
        default_relative_path="ignored.json",
    )
    assert resolved_path == root_relative
    assert label == root_relative.as_posix()

    repo_fallback = tmp_path / "repo-queries.json"
    repo_fallback.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(baselines, "resolve_repo_asset_path", lambda relative: repo_fallback)
    resolved_path, label = baselines._resolve_benchmark_asset_path(
        tmp_path,
        None,
        default_relative_path="benchmarks/queries.json",
    )
    assert resolved_path == repo_fallback
    assert label == "benchmarks/queries.json"

    assert baselines._parse_qrel_entry("q1", "doc-1", label="qrels").doc_id == "doc-1"
    assert baselines._parse_qrel_entry(
        "q1",
        {"query_id": "q1", "doc_id": "doc-2", "relevance": "2"},
        label="qrels",
    ).relevance == 2

    with pytest.raises(ValueError):
        _ = baselines._require_mapping_rows("bad", label="rows")
    with pytest.raises(ValueError):
        _ = baselines._require_mapping_rows(["bad"], label="rows")
    with pytest.raises(ValueError):
        _ = baselines._string_list("bad", label="strings")
    with pytest.raises(ValueError):
        _ = baselines._parse_qrel_entry(
            "q1",
            {"query_id": "other", "doc_id": "doc-1"},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = baselines._parse_qrel_entry(
            "q1",
            {"query_id": "q1", "doc_id": "", "relevance": 1},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = baselines._parse_qrel_entry(
            "q1",
            {"query_id": "q1", "doc_id": "doc-1", "relevance": "bad"},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = baselines._parse_qrel_entry(
            "q1",
            {"query_id": "q1", "doc_id": "doc-1", "relevance": 1.5},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = baselines._parse_qrel_entries("q1", "bad", label="qrels")

    judgments_path = tmp_path / "judgments.json"
    judgments_path.write_text(
        json.dumps(
            {
                "judgments": [
                    {"query_id": "q1", "doc_id": "doc-1", "relevance": 1},
                    {
                        "query_id": "q2",
                        "qrels": [
                            {"query_id": "q2", "doc_id": "doc-2", "relevance": 2}
                        ],
                    },
                    {"query_id": "q3", "relevant_paths": ["doc-3", "doc-4"]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    qrels = baselines.load_qrels(judgments_path)
    assert [entry.doc_id for entry in qrels["q3"]] == ["doc-3", "doc-4"]
    assert qrels["q2"][0].relevance == 2

    monkeypatch.setattr(
        baselines,
        "load_qrels",
        lambda path: (_ for _ in ()).throw(ValueError("bad qrels")),
    )
    with pytest.raises(ValueError, match="must contain a 'judgments' mapping or list rows"):
        _ = baselines._load_judgments(tmp_path, judgments_path)


def test_baselines_lookup_tokenizer_and_operational_helpers_cover_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baselines = import_module("snowiki.bench.baselines")
    from snowiki.search.indexer import SearchDocument, SearchHit

    path_hit = SearchHit(
        document=SearchDocument(
            id="",
            path="compiled/path-doc.md",
            kind="page",
            title="Path Doc",
            content="content",
        ),
        score=1.0,
        matched_terms=(),
    )
    assert baselines._hit_identifier(path_hit) == "compiled/path-doc.md"
    assert baselines._match_benchmark_hit(
        path_hit,
        [baselines.QrelEntry(query_id="q1", doc_id="fixture-a")],
        {"compiled/path-doc.md": "fixture-a"},
    ) == "fixture-a"

    duplicate_ids = baselines._ranked_doc_ids(
        [path_hit, path_hit],
        [baselines.QrelEntry(query_id="q1", doc_id="fixture-a")],
        hit_lookup={"compiled/path-doc.md": "fixture-a"},
    )
    assert duplicate_ids == ["fixture-a"]

    monkeypatch.setattr(baselines, "resolve_legacy_tokenizer", lambda **kwargs: None)
    with pytest.raises(ValueError, match="could not resolve tokenizer"):
        _ = baselines._tokenizer_name_for_baseline("bm25s")
    with pytest.raises(ValueError, match="unsupported baseline"):
        _ = baselines._tokenizer_name_for_baseline("bm25s_kiwi_full")
    with pytest.raises(ValueError, match="unsupported baseline"):
        _ = baselines._tokenizer_name_for_baseline("bogus")

    monkeypatch.setattr(
        baselines,
        "measure_regex_candidate_build",
        lambda *, records: (1.0, 2.0),
    )
    monkeypatch.setattr(
        baselines,
        "measure_bm25_candidate_build",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected bm25 measurement")),
    )
    evidence = baselines._measure_operational_evidence(
        records=[],
        bm25_indexes={"not-a-bm25-index": object()},
    )
    assert evidence["regex_v1"].disk_size_mb == 2.0


def test_phase1_latency_helper_branches_are_covered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    phase1_latency = import_module("snowiki.bench.phase1_latency")
    presets = import_module("snowiki.bench.presets")
    preset = presets.get_preset("retrieval")

    rows: list[dict[str, object]] = [
        {
            "id": "q1",
            "text": "alpha",
            "kind": "known-item",
            "group": "ko",
            "tags": ["keep", ""],
        },
        {"id": "q2", "text": " ", "kind": "known-item"},
        {"id": "q3", "text": "skip", "kind": "temporal"},
    ]
    query_specs = phase1_latency._query_specs_from_rows(rows, preset=preset)
    assert query_specs == ({"text": "alpha", "kind": "known-item", "id": "q1", "group": "ko", "tags": ["keep"]},)

    payload_path = tmp_path / "queries.json"
    payload_path.write_text('{"queries": []}', encoding="utf-8")
    assert phase1_latency._load_json(payload_path) == {"queries": []}

    monkeypatch.setattr(phase1_latency, "_load_json", lambda path: {"queries": rows})
    loaded_specs = phase1_latency._load_query_specs_for_preset(preset)
    assert loaded_specs == query_specs

    assert phase1_latency._requested_latency_policy(
        "official_suite",
        query_count=60,
        latency_sample="fixed_sample",
    ).mode == "fixed_sample"
    assert phase1_latency._requested_latency_policy(
        "official_suite",
        query_count=60,
        latency_sample="stratified",
    ).mode == "stratified"
    assert phase1_latency._requested_latency_policy(
        "official_suite",
        query_count=60,
        latency_sample="exhaustive",
    ).mode == "exhaustive"

    assert phase1_latency._derive_latency_strata(
        (
            {"text": "alpha", "kind": "known-item", "group": "shared"},
            {"text": "beta", "kind": "topical", "group": "shared"},
        )
    ) == ["known-item", "topical"]
    assert phase1_latency._derive_latency_strata(
        ({"text": "alpha", "kind": "", "group": ""},)
    ) == ["all"]

    materialized = phase1_latency._materialize_latency_policy(
        phase1_latency.LatencySamplingPolicy(mode="stratified"),
        queries=(
            {"text": "alpha", "kind": "known-item", "group": "shared"},
            {"text": "beta", "kind": "topical", "group": "shared"},
        ),
    )
    assert materialized.strata == ["known-item", "topical"]
    assert phase1_latency._materialize_latency_policy(
        phase1_latency.LatencySamplingPolicy(mode="stratified", strata=["preset"]),
        queries=query_specs,
    ).strata == ["preset"]

    assert phase1_latency._evenly_spaced_positions(0, 3) == []
    assert phase1_latency._evenly_spaced_positions(3, 5) == [0, 1, 2]
    assert phase1_latency._fixed_sample_query_positions(3, 5) == [0, 1, 2]
    assert phase1_latency._stratified_sample_query_positions((), strata=["ko"]) == []
    assert phase1_latency._stratified_sample_query_positions(query_specs, strata=[]) == [0]
    assert phase1_latency._stratified_sample_query_positions(
        query_specs,
        strata=["missing"],
    ) == [0]

    mixed_queries = cast(
        tuple[object, ...],
        tuple(
            {
                "text": f"q{index}",
                "kind": "known-item",
                "group": "ko" if index == 0 else "other",
            }
            for index in range(5)
        ),
    )
    assert phase1_latency._stratified_sample_query_positions(
        cast(Any, mixed_queries),
        strata=["ko"],
    ) == [0, 1, 2, 3, 4]


def test_verdict_internal_helpers_cover_edge_cases() -> None:
    verdict = import_module("snowiki.bench.verdict")
    models = import_module("snowiki.bench.models")

    assert verdict._report_tier({"metadata": {"dataset_tier": "official_suite"}}) == "official_suite"
    assert verdict._report_tier({"dataset": {"tier": "official_suite"}}) == "official_suite"
    assert verdict._report_tier({}) == "regression_harness"

    assert verdict.performance_threshold_failure_count({"performance_thresholds": "bad"}) == 0
    assert verdict.retrieval_threshold_failure_count({"retrieval": {"baselines": "bad"}}) == 0
    assert verdict.benchmark_exit_code({"benchmark_verdict": {"exit_code": True}}) == 1
    assert verdict.benchmark_exit_code({"benchmark_verdict": {"exit_code": 2}}) == 2
    assert verdict.benchmark_exit_code({}) == 0

    missing_control = verdict._control_decision(None)
    assert missing_control.reasons == ["missing_control_evidence"]

    control_without_measurements = verdict._control_decision(
        models.CandidateMatrixEntry.model_validate(
            {
                "candidate_name": "regex_v1",
                "evidence_baseline": "lexical",
                "role": "control",
                "admission_status": "admitted",
                "control": True,
                "operational_evidence": _operational_evidence_payload(measured=False),
                "baseline": _baseline_payload_for_verdict(name="lexical"),
            }
        )
    )
    assert control_without_measurements.disposition == "benchmark_only"
    assert control_without_measurements.reasons == ["missing_operational_evidence"]

    control_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "regex_v1",
            "evidence_baseline": "lexical",
            "role": "control",
            "admission_status": "admitted",
            "control": True,
            "operational_evidence": _operational_evidence_payload(measured=True),
            "baseline": _baseline_payload_for_verdict(
                name="lexical",
                mixed_value=0.80,
                ko_value=0.80,
                en_value=0.80,
                p95_ms=10.0,
            ),
        }
    )

    assert verdict._candidate_decision(
        None,
        control_entry,
        verdict.STEP_03_CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    ).reasons == ["missing_benchmark_evidence"]

    overall_fail_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "kiwi_morphology_v1",
            "evidence_baseline": "bm25s_kiwi_full",
            "role": "candidate",
            "admission_status": "admitted",
            "control": False,
            "operational_evidence": _operational_evidence_payload(measured=True),
            "baseline": _baseline_payload_for_verdict(
                name="bm25s_kiwi_full",
                mixed_value=0.85,
                ko_value=0.85,
                en_value=0.85,
                p95_ms=11.0,
                overall_fail=True,
            ),
        }
    )
    assert verdict._candidate_decision(
        overall_fail_entry,
        control_entry,
        verdict.STEP_03_CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    ).reasons == ["overall_quality_gate_failed"]

    no_improvement_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "kiwi_morphology_v1",
            "evidence_baseline": "bm25s_kiwi_full",
            "role": "candidate",
            "admission_status": "admitted",
            "control": False,
            "operational_evidence": _operational_evidence_payload(measured=True),
            "baseline": _baseline_payload_for_verdict(
                name="bm25s_kiwi_full",
                mixed_value=0.80,
                ko_value=0.80,
                en_value=0.80,
                p95_ms=10.0,
            ),
        }
    )
    assert verdict._candidate_decision(
        no_improvement_entry,
        control_entry,
        verdict.STEP_03_CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    ).reasons == ["no_material_mixed_improvement"]

    benchmark_only_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "kiwi_morphology_v1",
            "evidence_baseline": "bm25s_kiwi_full",
            "role": "candidate",
            "admission_status": "admitted",
            "control": False,
            "operational_evidence": _operational_evidence_payload(measured=False),
            "baseline": _baseline_payload_for_verdict(
                name="bm25s_kiwi_full",
                mixed_value=0.81,
                ko_value=0.78,
                en_value=0.78,
                p95_ms=15.0,
            ),
        }
    )
    benchmark_only = verdict._candidate_decision(
        benchmark_only_entry,
        control_entry,
        verdict.STEP_03_CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    )
    assert benchmark_only.disposition == "benchmark_only"
    assert benchmark_only.reasons == [
        "mixed_delta_below_promotion_threshold",
        "slice_recall_non_regression_failed",
        "latency_ratio_guard_failed",
        "missing_operational_evidence",
    ]

    baseline_without_overall = models.BaselineResult.model_validate(
        _baseline_payload_for_verdict(
            name="lexical",
            include_overall_threshold=False,
        )
    )
    assert verdict._passes_overall_quality_gates(baseline_without_overall) is False
    assert verdict._group_metric(baseline_without_overall, "missing", "mrr") == 0.0
    assert verdict._latency_ratio(
        models.BaselineResult.model_validate(
            _baseline_payload_for_verdict(name="candidate", p95_ms=5.0)
        ),
        models.BaselineResult.model_validate(
            _baseline_payload_for_verdict(name="control", p95_ms=0.0)
        ),
    ) == float("inf")
    assert verdict._baseline_p95(
        models.BaselineResult.model_validate({"name": "empty", "queries": []})
    ) == 0.0

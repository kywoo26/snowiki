from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

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



def test_tier_aware_latency_policy_is_applied() -> None:
    from snowiki.bench.validation.latency import get_latency_policy

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
    from snowiki.bench.contract.presets import get_preset
    from snowiki.bench.datasets.anchors.korean import load_miracl_ko_sample
    from snowiki.bench.validation import latency as latency_module

    fixture_path = tmp_path / "fixture.jsonl"
    _ = fixture_path.write_text("{}\n", encoding="utf-8")
    manifest = load_miracl_ko_sample(size=100)

    monkeypatch.setattr(latency_module, "BENCHMARK_WARMUPS", 0)
    monkeypatch.setattr(latency_module, "BENCHMARK_REPETITIONS", 1)
    monkeypatch.setattr(
        latency_module,
        "_canonical_fixtures",
        lambda: ({"source": "claude", "path": fixture_path},),
    )
    monkeypatch.setattr(
        latency_module,
        "run_ingest",
        lambda path, *, source, root: {"path": path.as_posix(), "source": source},
    )
    monkeypatch.setattr(
        latency_module,
        "run_rebuild",
        lambda root: {"root": root.as_posix()},
    )

    query_calls: list[str] = []

    def fake_query(root: Path, query: str, *, mode: str, top_k: int) -> dict[str, object]:
        query_calls.append(query)
        return {"query": query, "mode": mode, "top_k": top_k}

    monkeypatch.setattr(latency_module, "run_query", fake_query)
    ticks = iter([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    monkeypatch.setattr("time.perf_counter", lambda: next(ticks))

    report = latency_module.run_latency_evaluation(
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
    from snowiki.bench.datasets.anchors.korean import load_miracl_ko_sample

    report_module, benchmark_report = _load_report_symbols()
    manifest = load_miracl_ko_sample(size=60)
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
    from snowiki.bench.runtime.corpus import BenchmarkCorpusManifest

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
    from snowiki.bench.datasets.anchors.korean import load_miracl_ko_sample

    report_module, benchmark_report = _load_report_symbols()
    manifest = load_miracl_ko_sample(size=60)
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


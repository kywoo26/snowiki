from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from snowiki.bench.models import (
    BENCHMARK_ASSET_MANIFEST_LIST_ADAPTER,
    PAGE_LIST_ADAPTER,
    RECORD_LIST_ADAPTER,
    BenchmarkAssetManifest,
    BenchmarkProvenance,
    BenchmarkReport,
    CandidateMatrixReport,
    validate_baseline_result,
    validate_page_dict,
    validate_record_dict,
)


def _baseline_payload() -> dict[str, object]:
    return {
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
                "recall_at_k": 1.0,
                "mrr": 0.75,
                "ndcg_at_k": 0.88,
                "top_k": 5,
                "queries_evaluated": 1,
                "per_query": [
                    {
                        "query_id": "q1",
                        "ranked_ids": ["fixture-a"],
                        "relevant_ids": ["fixture-a"],
                        "recall_at_k": 1.0,
                        "reciprocal_rank": 1.0,
                        "ndcg_at_k": 1.0,
                    }
                ],
            },
            "slices": {
                "group": {},
                "kind": {},
            },
            "thresholds": [
                {
                    "gate": "overall",
                    "metric": "mrr",
                    "value": 0.75,
                    "delta": 0.05,
                    "verdict": "PASS",
                    "threshold": 0.7,
                    "warnings": [],
                }
            ],
        },
        "queries": {
            "q1": [
                {
                    "id": "fixture-a",
                    "path": "fixtures/a.jsonl",
                    "title": "Fixture A",
                    "score": 3.5,
                }
            ]
        },
    }


def _provenance_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_class": "public_dataset",
        "authoring_method": "human_only",
        "license": "CC-BY-4.0",
        "collection_method": "miracl_official",
        "visibility_tier": "public",
        "contamination_status": "clean",
        "family_dedupe_key": "family-a",
        "authority_tier": "public_anchor",
    }
    payload.update(overrides)
    return payload


def _asset_manifest_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "asset_id": "asset-1",
        "path": "benchmarks/corpus/doc-1.json",
        "provenance": _provenance_payload(),
    }
    payload.update(overrides)
    return payload


def test_record_model_accepts_text_alias_and_is_frozen() -> None:
    record = validate_record_dict(
        {
            "id": "record-1",
            "path": "normalized/record-1.json",
            "text": "hello world",
            "title": "Example",
            "metadata": {"source_path": "fixtures/a.jsonl"},
        }
    )

    assert record.content == "hello world"
    assert record.model_dump(mode="json")["title"] == "Example"

    with pytest.raises(ValidationError):
        record.content = "changed"


def test_page_model_forbids_unexpected_fields() -> None:
    page = validate_page_dict(
        {
            "id": "page-1",
            "path": "compiled/example.md",
            "title": "Example",
            "body": "Rendered body",
            "record_ids": ["record-1"],
        }
    )

    assert page.record_ids == ["record-1"]

    with pytest.raises(ValidationError):
        _ = validate_page_dict(
            {
                "id": "page-1",
                "path": "compiled/example.md",
                "title": "Example",
                "body": "Rendered body",
                "aliases": ["unexpected"],
            }
        )


def test_baseline_result_legacy_queries_round_trip() -> None:
    payload = _baseline_payload()

    result = validate_baseline_result(payload)

    assert result.queries[0].query_id == "q1"
    assert result.to_legacy_dict() == payload


def test_baseline_result_preserves_canonical_tokenizer_name_in_legacy_dict() -> None:
    payload = _baseline_payload()
    payload["tokenizer_name"] = "kiwi_morphology_v1"

    result = validate_baseline_result(payload)

    assert result.tokenizer_name == "kiwi_morphology_v1"
    assert result.to_legacy_dict()["tokenizer_name"] == "kiwi_morphology_v1"
    assert result.to_legacy_dict() == payload


def test_benchmark_report_legacy_serializer_preserves_shape() -> None:
    report = BenchmarkReport.model_validate(
        {
            "preset": {
                "name": "core",
                "description": "Core benchmark preset.",
                "query_kinds": ["known-item"],
                "top_k": 5,
                "baselines": ["lexical"],
            },
            "corpus": {
                "records_indexed": 1,
                "pages_indexed": 1,
                "raw_documents": 1,
                "blended_documents": 2,
                "queries_evaluated": 1,
            },
            "baselines": {"lexical": _baseline_payload()},
            "corpus_assets": [_asset_manifest_payload()],
            "candidate_matrix": {
                "candidates": [
                    {
                        "candidate_name": "regex_v1",
                        "evidence_baseline": "lexical",
                        "role": "control",
                        "admission_status": "admitted",
                        "control": True,
                    }
                ]
            },
        }
    )

    legacy = report.to_legacy_dict()
    preset = cast(dict[str, object], legacy["preset"])
    corpus = cast(dict[str, object], legacy["corpus"])
    baselines = cast(dict[str, object], legacy["baselines"])
    lexical = cast(dict[str, object], baselines["lexical"])
    queries = cast(dict[str, object], lexical["queries"])
    q1_hits = cast(list[dict[str, object]], queries["q1"])
    assert preset["name"] == "core"
    assert corpus["records_indexed"] == 1
    assert q1_hits[0]["score"] == 3.5
    assert report.candidate_matrix == CandidateMatrixReport.model_validate(
        {
            "candidates": [
                {
                    "candidate_name": "regex_v1",
                    "evidence_baseline": "lexical",
                    "role": "control",
                    "admission_status": "admitted",
                    "control": True,
                }
            ]
        }
    )
    assert report.corpus_assets == [
        BenchmarkAssetManifest.model_validate(_asset_manifest_payload())
    ]
    assert "candidate_matrix" not in legacy
    assert "corpus_assets" not in legacy


def test_benchmark_provenance_accepts_valid_authoritative_payload() -> None:
    manifest = BenchmarkAssetManifest.model_validate(_asset_manifest_payload())

    assert manifest.provenance == BenchmarkProvenance.model_validate(_provenance_payload())
    assert manifest.to_report_dict()["provenance"] == _provenance_payload()


def test_assistant_generated_assets_cannot_be_authoritative() -> None:
    payloads = (
        _provenance_payload(
            authoring_method="assistant_generated",
            authority_tier="public_anchor",
        ),
        _provenance_payload(
            authoring_method="assistant_generated",
            authority_tier="snowiki_shaped",
            visibility_tier="developer_visible",
        ),
        _provenance_payload(
            authoring_method="assistant_generated",
            authority_tier="hidden_holdout",
            visibility_tier="hidden_holdout",
        ),
    )

    for provenance in payloads:
        with pytest.raises(ValidationError):
            _ = BenchmarkAssetManifest.model_validate(
                _asset_manifest_payload(provenance=provenance)
            )


def test_hidden_holdout_requires_clean_contamination_status() -> None:
    with pytest.raises(ValidationError):
        _ = BenchmarkAssetManifest.model_validate(
            _asset_manifest_payload(
                provenance=_provenance_payload(
                    visibility_tier="hidden_holdout",
                    contamination_status="suspected",
                    authority_tier="hidden_holdout",
                )
            )
        )


def test_authoritative_assets_fail_closed_when_provenance_fields_are_missing() -> None:
    payload = _asset_manifest_payload(
        provenance={
            "source_class": "public_dataset",
            "authoring_method": "human_only",
            "license": "CC-BY-4.0",
            "collection_method": "miracl_official",
            "contamination_status": "clean",
            "authority_tier": "public_anchor",
        }
    )

    with pytest.raises(ValidationError):
        _ = BenchmarkAssetManifest.model_validate(payload)

    with pytest.raises(ValidationError):
        _ = BENCHMARK_ASSET_MANIFEST_LIST_ADAPTER.validate_python([payload])


def test_record_list_adapter_rejects_malformed_record_metadata() -> None:
    with pytest.raises(ValidationError):
        _ = RECORD_LIST_ADAPTER.validate_python(
            [
                {
                    "id": "record-1",
                    "text": "hello world",
                    "metadata": ["not-a-mapping"],
                }
            ]
        )


def test_page_list_adapter_rejects_wrong_record_id_container_type() -> None:
    with pytest.raises(ValidationError):
        _ = PAGE_LIST_ADAPTER.validate_python(
            [
                {
                    "id": "page-1",
                    "path": "compiled/example.md",
                    "title": "Example",
                    "body": "Rendered body",
                    "record_ids": "record-1",
                }
            ]
        )

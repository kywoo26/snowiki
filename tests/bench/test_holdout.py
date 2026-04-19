from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import cast

import pytest

from snowiki.bench.anchors.hidden_holdout import (
    is_hidden_holdout,
    load_hidden_holdout_suite,
)
from snowiki.bench.models import BenchmarkReport, PooledReview
from snowiki.bench.report import generate_audit_report, generate_report


def test_hidden_holdout_manifest_has_correct_visibility_tier() -> None:
    manifest = load_hidden_holdout_suite(size=6)

    assert manifest.tier == "hidden_holdout"
    assert is_hidden_holdout(manifest) is True
    assert manifest.corpus_assets[0].provenance.visibility_tier == "hidden_holdout"
    assert (
        manifest.corpus_assets[0].provenance.family_dedupe_key
        == "hidden-holdout:v1:corpus"
    )


def test_hidden_holdout_is_excluded_from_dev_reporting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = load_hidden_holdout_suite(size=6)
    report_module = import_module("snowiki.bench.report")

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
        "run_baseline_comparison",
        lambda root, preset, **kwargs: BenchmarkReport.model_validate(
            {
                "preset": {
                    "name": preset.name,
                    "description": preset.description,
                    "query_kinds": list(preset.query_kinds),
                    "top_k": preset.top_k,
                    "top_ks": list(preset.top_ks),
                    "baselines": [],
                },
                "corpus": {
                    "records_indexed": 6,
                    "pages_indexed": 6,
                    "raw_documents": 6,
                    "blended_documents": 6,
                    "queries_evaluated": 6,
                },
                "baselines": {
                    "lexical": {
                        "name": "lexical",
                        "queries": [
                            {
                                "query_id": "holdout-q-001",
                                "hits": [
                                    {
                                        "id": "holdout-doc-001",
                                        "path": "compiled/holdout-doc-001.md",
                                        "title": "Hidden holdout case 001",
                                        "score": 1.0,
                                    }
                                ],
                            }
                        ],
                        "quality": {
                            "overall": {
                                "recall_at_k": 1.0,
                                "mrr": 1.0,
                                "ndcg_at_k": 1.0,
                                "top_k": 5,
                                "queries_evaluated": 1,
                                "per_query": [
                                    {
                                        "query_id": "holdout-q-001",
                                        "ranked_ids": ["holdout-doc-001"],
                                        "relevant_ids": ["holdout-doc-001"],
                                        "tags": ["holdout"],
                                        "recall_at_k": 1.0,
                                        "reciprocal_rank": 1.0,
                                        "ndcg_at_k": 1.0,
                                    }
                                ],
                            },
                            "slices": {
                                "group": {
                                    "hidden_holdout": {
                                        "recall_at_k": 1.0,
                                        "mrr": 1.0,
                                        "ndcg_at_k": 1.0,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [
                                            {
                                                "query_id": "holdout-q-001",
                                                "ranked_ids": ["holdout-doc-001"],
                                                "relevant_ids": ["holdout-doc-001"],
                                                "recall_at_k": 1.0,
                                                "reciprocal_rank": 1.0,
                                                "ndcg_at_k": 1.0,
                                            }
                                        ],
                                    }
                                },
                                "kind": {},
                            },
                            "thresholds": [],
                        },
                    }
                },
            }
        ),
    )

    report = generate_report(
        tmp_path,
        preset_name="retrieval",
        manifest=manifest,
        dataset_name="hidden_holdout",
        isolated_root=True,
    )
    retrieval = cast(dict[str, object], report["retrieval"])
    dataset = cast(dict[str, object], report["dataset"])
    audit = cast(dict[str, object], report["audit"])
    baselines = cast(dict[str, object], retrieval["baselines"])
    lexical = cast(dict[str, object], baselines["lexical"])
    quality = cast(dict[str, object], lexical["quality"])
    overall = cast(dict[str, object], quality["overall"])

    assert "corpus_assets" not in retrieval
    assert "query_assets" not in retrieval
    assert "judgment_assets" not in retrieval
    assert retrieval["sealed_holdout"] is True
    assert "provenance" not in dataset
    assert cast(dict[str, object], dataset["provenance_status"])["sealed"] is True
    assert lexical["queries"] == {}
    assert overall["per_query"] == []
    provenance_quota = cast(dict[str, object], audit["provenance_quota"])
    visibility_tiers = cast(dict[str, int], provenance_quota["by_visibility_tier"])
    assert visibility_tiers["hidden_holdout"] == 3

    serialized_report = repr(report)
    assert "holdout-q-001" not in serialized_report
    assert "holdout-doc-001" not in serialized_report


def test_audit_sampling_policy_exists() -> None:
    manifest = load_hidden_holdout_suite(size=10)
    report = BenchmarkReport.model_validate(
        {
            "audit_samples": [sample.model_dump(mode="json") for sample in manifest.audit_samples],
            "pooled_reviews": [review.model_dump(mode="json") for review in manifest.pooled_reviews],
            "corpus_assets": [asset.model_dump(mode="json") for asset in manifest.corpus_assets],
            "query_assets": [asset.model_dump(mode="json") for asset in manifest.query_assets],
            "judgment_assets": [asset.model_dump(mode="json") for asset in manifest.judgment_assets],
            "audit_policy": manifest.audit_policy,
            "review_policy": manifest.review_policy,
        }
    )

    audit = generate_audit_report(report)
    provenance_quota = cast(dict[str, object], audit["provenance_quota"])

    assert cast(dict[str, object], audit["policy"])["ground_truth_error_estimation"] is True
    assert "visibility_tier" in cast(
        list[str], provenance_quota["quota_dimensions"]
    )
    assert cast(dict[str, object], audit["pooled_review"])["blind_human_adjudication"] is True
    assert cast(dict[str, int], provenance_quota["by_authoring_method"])["human_reviewed"] == 2
    assert cast(dict[str, int], provenance_quota["by_authority_tier"])["hidden_holdout"] == 3


def test_pooled_review_model_validates() -> None:
    pooled_review = PooledReview.model_validate(
        {
            "query_id": "holdout-q-001",
            "judgments_from_systems": {
                "lexical": {"holdout-doc-001": 1},
                "bm25s": {"holdout-doc-002": 1},
            },
            "final_adjudication": {"holdout-doc-001": 1},
            "disagreement_flag": True,
        }
    )

    assert pooled_review.disagreement_flag is True
    assert pooled_review.final_adjudication == {"holdout-doc-001": 1}


def test_hidden_holdout_small_sizes_do_not_create_dangling_references() -> None:
    for size in (1, 2, 3):
        manifest = load_hidden_holdout_suite(size=size)
        query_ids = {str(query["id"]) for query in manifest.queries or []}
        document_ids = {str(document["id"]) for document in manifest.documents}

        assert all(sample.query_id in query_ids for sample in manifest.audit_samples)
        assert all(review.query_id in query_ids for review in manifest.pooled_reviews)
        assert all(
            doc_id in document_ids
            for review in manifest.pooled_reviews
            for judgments in review.judgments_from_systems.values()
            for doc_id in judgments
        )
        assert all(
            doc_id in document_ids for review in manifest.pooled_reviews for doc_id in review.final_adjudication
        )

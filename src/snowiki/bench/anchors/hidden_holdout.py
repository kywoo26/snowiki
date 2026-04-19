from __future__ import annotations

from snowiki.bench.corpus import BenchmarkCorpusManifest
from snowiki.bench.models import (
    AuditSample,
    BenchmarkAssetManifest,
    BenchmarkProvenance,
    PooledReview,
)

HIDDEN_HOLDOUT_METADATA: dict[str, str] = {
    "name": "Hidden Holdout Workflow Facsimile",
    "description": (
        "Deterministic synthetic hidden-holdout benchmark facsimile used to verify "
        "sealing, pooled review, adjudication, and audit-report handling without "
        "exposing release holdout assets during development."
    ),
    "tier": "hidden_holdout",
}

_POOLING_SYSTEMS: tuple[str, ...] = (
    "lexical",
    "bm25s",
    "bm25s_kiwi_full",
)


def _asset_provenance(asset_kind: str) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        source_class="synthetic",
        authoring_method="human_reviewed" if asset_kind != "corpus" else "automated",
        license="proprietary",
        collection_method="sealed_holdout_simulation",
        visibility_tier="hidden_holdout",
        contamination_status="clean",
        family_dedupe_key=f"hidden-holdout:v1:{asset_kind}",
        authority_tier="hidden_holdout",
    )


def _documents(size: int) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    for index in range(1, size + 1):
        family_key = f"hidden-holdout:v1:family:{index:03d}"
        documents.append(
            {
                "id": f"holdout-doc-{index:03d}",
                "content": (
                    f"Hidden holdout document {index:03d} captures a sealed retrieval scenario with "
                    "developer-invisible phrasing, release-only adjudication notes, and mixed Korean-English "
                    "entity wording for contamination-resistant benchmark verification."
                ),
                "metadata": {
                    "title": f"Hidden holdout case {index:03d}",
                    "summary": "Synthetic sealed document for hidden holdout workflow verification.",
                    "recorded_at": f"2026-04-{((index - 1) % 28) + 1:02d}T00:00:00Z",
                    "language": "ko+en",
                    "family_dedupe_key": family_key,
                    "visibility_tier": "hidden_holdout",
                },
            }
        )
    return documents


def _queries(size: int) -> list[dict[str, object]]:
    queries: list[dict[str, object]] = []
    for index in range(1, size + 1):
        queries.append(
            {
                "id": f"holdout-q-{index:03d}",
                "text": f"sealed holdout retrieval question {index:03d}",
                "group": "hidden_holdout",
                "kind": "known-item" if index % 3 else "topical",
                "tags": ["holdout", "sealed", "blind-review"],
                "family_dedupe_key": f"hidden-holdout:v1:query:{index:03d}",
            }
        )
    return queries


def _judgments(size: int) -> dict[str, list[dict[str, object]]]:
    judgments: dict[str, list[dict[str, object]]] = {}
    for index in range(1, size + 1):
        judgments[f"holdout-q-{index:03d}"] = [
            {
                "query_id": f"holdout-q-{index:03d}",
                "doc_id": f"holdout-doc-{index:03d}",
                "relevance": 2 if index % 5 == 0 else 1,
            }
        ]
    return judgments


def _pooled_reviews(size: int) -> tuple[PooledReview, ...]:
    review_count = min(size, max(1, min(max(size // 10, 3), 6)))
    reviews: list[PooledReview] = []
    for index in range(1, review_count + 1):
        query_id = f"holdout-q-{index:03d}"
        target_doc = f"holdout-doc-{index:03d}"
        alternate_doc = f"holdout-doc-{(index % max(size, 1)) + 1:03d}"
        disagreement = index % 2 == 0
        reviews.append(
            PooledReview(
                query_id=query_id,
                judgments_from_systems={
                    "lexical": {target_doc: 1},
                    "bm25s": {target_doc: 1},
                    "bm25s_kiwi_full": (
                        {alternate_doc: 1} if disagreement else {target_doc: 1}
                    ),
                },
                final_adjudication={target_doc: 1},
                disagreement_flag=disagreement,
            )
        )
    return tuple(reviews)


def _audit_samples(size: int) -> tuple[AuditSample, ...]:
    sample_count = min(size, max(1, min(max(size // 8, 4), 8)))
    samples: list[AuditSample] = []
    for index in range(1, sample_count + 1):
        samples.append(
            AuditSample(
                query_id=f"holdout-q-{index:03d}",
                adjudicated_relevance=1,
                reviewer_count=3,
                agreement_score=0.67 if index % 2 == 0 else 1.0,
            )
        )
    return tuple(samples)


def load_hidden_holdout_suite(size: int = 50) -> BenchmarkCorpusManifest:
    if size < 1:
        raise ValueError("hidden holdout suite size must be at least 1")

    return BenchmarkCorpusManifest(
        tier="hidden_holdout",
        documents=_documents(size),
        queries=_queries(size),
        judgments=_judgments(size),
        dataset_id="hidden_holdout",
        dataset_name=HIDDEN_HOLDOUT_METADATA["name"],
        dataset_description=HIDDEN_HOLDOUT_METADATA["description"],
        dataset_metadata={
            "language": "ko+en",
            "development_only": True,
            "release_use": "sealed_final_proof_only",
            "sealing_policy": {
                "visibility_tier": "hidden_holdout",
                "dev_reporting_excludes_assets": True,
                "release_reporting_requires_separate_channel": True,
            },
        },
        corpus_assets=(
            BenchmarkAssetManifest(
                asset_id="hidden_holdout_corpus",
                provenance=_asset_provenance("corpus"),
            ),
        ),
        query_assets=(
            BenchmarkAssetManifest(
                asset_id="hidden_holdout_queries",
                provenance=_asset_provenance("queries"),
            ),
        ),
        judgment_assets=(
            BenchmarkAssetManifest(
                asset_id="hidden_holdout_judgments",
                provenance=_asset_provenance("judgments"),
            ),
        ),
        pooled_reviews=_pooled_reviews(size),
        audit_samples=_audit_samples(size),
        review_policy={
            "pooled_review": True,
            "blind_human_adjudication": True,
            "systems": list(_POOLING_SYSTEMS),
            "disagreement_policy": "escalate_to_lead_adjudicator_when_systems_diverge",
        },
        audit_policy={
            "ground_truth_error_estimation": True,
            "sample_rate_pct": 12.0,
            "minimum_queries": 6,
            "provenance_quota_dimensions": [
                "source_class",
                "authoring_method",
                "visibility_tier",
                "authority_tier",
            ],
        },
    )


def is_hidden_holdout(manifest: BenchmarkCorpusManifest) -> bool:
    return manifest.tier == "hidden_holdout" or any(
        asset.provenance.visibility_tier == "hidden_holdout"
        for asset in (
            *manifest.corpus_assets,
            *manifest.query_assets,
            *manifest.judgment_assets,
        )
    )


__all__ = [
    "HIDDEN_HOLDOUT_METADATA",
    "is_hidden_holdout",
    "load_hidden_holdout_suite",
]

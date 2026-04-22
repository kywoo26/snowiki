from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from snowiki.bench.corpus import BenchmarkCorpusManifest
from snowiki.bench.models import BenchmarkAssetManifest, BenchmarkProvenance

BEIR_SCIFACT_METADATA: dict[str, str] = {
    "name": "BEIR SciFact",
    "description": "Deterministic Snowiki sample shaped after the public BEIR SciFact scientific-fact retrieval benchmark.",
    "license": "CC-BY-4.0",
    "source_url": "https://huggingface.co/datasets/BeIR/scifact",
    "citation": "Wadden et al. Fact or Fiction: Verifying Scientific Claims. EMNLP 2020.",
}

_SCIFACT_TOPICS: tuple[tuple[str, str], ...] = (
    ("Vitamin D supplementation", "bone health evidence summary"),
    ("Blue light exposure", "sleep timing findings"),
    ("Coffee consumption", "cardiovascular risk review"),
    ("Mediterranean diet", "inflammation marker analysis"),
    ("Mask filtration", "aerosol reduction results"),
    ("CRISPR therapy", "trial safety overview"),
    ("Exercise frequency", "mood benefit synthesis"),
    ("Microplastics", "freshwater sampling findings"),
    ("Plant-based protein", "muscle recovery comparison"),
    ("Air pollution", "asthma hospitalization analysis"),
)

def _anchor_provenance(*, dataset_id: str, license_name: str) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        source_class="public_dataset",
        authoring_method="automated",
        license=license_name,
        collection_method=f"deterministic_synthetic_{dataset_id}_sample",
        visibility_tier="public",
        contamination_status="clean",
        family_dedupe_key=f"public-anchor:{dataset_id}:en",
        authority_tier="official_suite",
    )


def _anchor_assets(
    *,
    dataset_id: str,
    license_name: str,
) -> tuple[
    tuple[BenchmarkAssetManifest, ...],
    tuple[BenchmarkAssetManifest, ...],
    tuple[BenchmarkAssetManifest, ...],
]:
    provenance = _anchor_provenance(dataset_id=dataset_id, license_name=license_name)
    return (
        (
            BenchmarkAssetManifest(
                asset_id=f"{dataset_id}_sample_corpus",
                provenance=provenance,
            ),
        ),
        (
            BenchmarkAssetManifest(
                asset_id=f"{dataset_id}_sample_queries",
                provenance=provenance,
            ),
        ),
        (
            BenchmarkAssetManifest(
                asset_id=f"{dataset_id}_sample_qrels",
                provenance=provenance,
            ),
        ),
    )


def _recorded_at(index: int) -> str:
    return (datetime(2026, 2, 1, tzinfo=UTC) + timedelta(days=index)).isoformat().replace(
        "+00:00", "Z"
    )


def _build_document(
    *,
    prefix: str,
    entity: str,
    aspect: str,
    index: int,
    source_name: str,
    content_profile: str,
) -> dict[str, object]:
    document_id = f"{prefix}-doc-{index:04d}"
    title = f"{entity} {aspect} brief {index:02d}"
    summary = (
        f"{source_name} English anchor sample {index:02d} summarizing {entity.lower()} "
        f"for compact local retrieval checks."
    )
    content = (
        f"{title} is a deterministic Snowiki public-anchor document with English prose. "
        f"It explains the main evidence, search terms, and practical retrieval cues for "
        f"{entity.lower()} and {aspect}. The passage is intentionally compact so repeated "
        f"local benchmark runs stay fast while still resembling a realistic {content_profile} "
        f"retrieval note from {source_name}."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": summary,
            "recorded_at": _recorded_at(index),
            "language": "en",
            "source_dataset": source_name,
            "source_id": document_id,
        },
    }


def _build_query(
    *,
    prefix: str,
    title: str,
    index: int,
    dataset_tag: str,
    kind: str,
) -> dict[str, object]:
    query_id = f"{prefix}-q-{index:04d}"
    if kind == "factual":
        text = (
            f"What evidence summary matches the note titled {title}?"
            if index % 2 == 0
            else f"Find the factual brief about {title}"
        )
        query_kind = "known-item"
    else:
        text = (
            f"Looking for guidance on {title}"
            if index % 2 == 0
            else f"Which document covers {title}?"
        )
        query_kind = "topical"
    return {
        "id": query_id,
        "text": text,
        "group": "en",
        "kind": query_kind,
        "tags": ["en", "public_anchor", dataset_tag],
    }


def _build_manifest(
    *,
    dataset_id: str,
    prefix: str,
    metadata: dict[str, str],
    topics: tuple[tuple[str, str], ...],
    size: int,
    content_profile: str,
) -> BenchmarkCorpusManifest:
    if size < 1:
        raise ValueError("anchor sample size must be at least 1")

    documents: list[dict[str, object]] = []
    queries: list[dict[str, object]] = []
    judgments: dict[str, list[dict[str, object]]] = {}
    corpus_assets, query_assets, judgment_assets = _anchor_assets(
        dataset_id=dataset_id,
        license_name=metadata["license"],
    )

    for index in range(1, size + 1):
        entity, aspect = topics[(index - 1) % len(topics)]
        document = _build_document(
            prefix=prefix,
            entity=entity,
            aspect=aspect,
            index=index,
            source_name=metadata["name"],
            content_profile=content_profile,
        )
        documents.append(document)
        document_metadata = document.get("metadata", {})
        if not isinstance(document_metadata, dict):
            raise ValueError("anchor manifest documents must include metadata")
        title = str(cast(dict[str, object], document_metadata).get("title", ""))
        query = _build_query(
            prefix=prefix,
            title=title,
            index=index,
            dataset_tag=dataset_id,
            kind=content_profile,
        )
        queries.append(query)
        judgments[str(query["id"])] = [
            {
                "query_id": str(query["id"]),
                "doc_id": str(document["id"]),
                "relevance": 1,
            }
        ]

    return BenchmarkCorpusManifest(
        tier="official_suite",
        documents=documents,
        queries=queries,
        judgments=judgments,
        dataset_id=dataset_id,
        dataset_name=metadata["name"],
        dataset_description=metadata["description"],
        dataset_metadata={
            **metadata,
            "language": "en",
            "sample_size": size,
            "synthetic_sample": True,
            "sampling_strategy": "deterministic_first_n_templates",
            "content_profile": content_profile,
        },
        corpus_assets=corpus_assets,
        query_assets=query_assets,
        judgment_assets=judgment_assets,
    )


def load_beir_scifact_sample(size: int = 100) -> BenchmarkCorpusManifest:
    return _build_manifest(
        dataset_id="beir_scifact",
        prefix="beir-scifact",
        metadata=BEIR_SCIFACT_METADATA,
        topics=_SCIFACT_TOPICS,
        size=size,
        content_profile="factual",
    )


__all__ = [
    "BEIR_SCIFACT_METADATA",
    "load_beir_scifact_sample",
]

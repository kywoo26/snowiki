from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from snowiki.bench.corpus import BenchmarkCorpusManifest
from snowiki.bench.models import BenchmarkAssetManifest, BenchmarkProvenance

MIRACL_KO_METADATA: dict[str, str] = {
    "name": "MIRACL Korean",
    "description": "Deterministic Snowiki sample shaped after the public MIRACL Korean retrieval benchmark.",
    "license": "Apache-2.0",
    "source_url": "https://github.com/project-miracl/miracl",
    "citation": "Zhang et al. MIRACL: A Multilingual Retrieval Dataset Covering 18 Diverse Languages.",
}

_MIRACL_TOPICS: tuple[tuple[str, str], ...] = (
    ("서울 공공도서관", "디지털 아카이브 안내"),
    ("제주 올레길", "7코스 여행 정보"),
    ("경복궁", "야간 개장 운영 요약"),
    ("한강공원", "자전거 대여 절차"),
    ("부산 국제영화제", "상영관 이용 안내"),
    ("국립중앙박물관", "특별전 해설"),
    ("한국어 형태소 분석", "기초 개념 정리"),
    ("태백산 국립공원", "등산 코스 설명"),
    ("광주 비엔날레", "전시 구성 소개"),
    ("판소리", "대표 작품 해설"),
)

def _anchor_provenance(*, dataset_id: str, license_name: str) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        source_class="mixed",
        authoring_method="automated",
        license=license_name,
        collection_method=f"deterministic_synthetic_{dataset_id}_sample",
        visibility_tier="public",
        contamination_status="clean",
        family_dedupe_key=f"public-anchor:{dataset_id}:ko",
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
    return (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)).isoformat().replace(
        "+00:00", "Z"
    )


def _build_document(
    *,
    prefix: str,
    entity: str,
    aspect: str,
    index: int,
    source_name: str,
) -> dict[str, object]:
    document_id = f"{prefix}-doc-{index:04d}"
    title = f"{entity} {aspect} {index:02d}"
    summary = f"{source_name} 한국어 앵커 샘플 {index:02d}의 핵심 내용을 요약한 문서입니다."
    content = (
        f"{title} 문서는 Snowiki 공개 앵커 벤치마크용 한국어 샘플입니다. "
        f"이 문서는 {entity}와 {aspect}에 관한 핵심 배경, 이용 팁, 검색 키워드를 함께 정리합니다. "
        f"검색 질의가 '{title}' 또는 '{entity} {aspect}' 형태로 들어오면 관련 문서를 안정적으로 찾을 수 있도록 설계했습니다."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": summary,
            "recorded_at": _recorded_at(index),
            "language": "ko",
            "source_dataset": source_name,
            "source_id": document_id,
        },
    }


def _build_query(*, prefix: str, title: str, index: int) -> dict[str, object]:
    query_id = f"{prefix}-q-{index:04d}"
    if index % 2 == 0:
        text = f"{title} 관련 핵심 정보를 알려줘"
        kind = "topical"
    else:
        text = f"{title} 문서의 핵심 내용은 무엇이야"
        kind = "known-item"
    return {
        "id": query_id,
        "text": text,
        "group": "ko",
        "kind": kind,
        "tags": ["ko", "public_anchor", prefix],
    }


def _build_manifest(
    *,
    dataset_id: str,
    prefix: str,
    metadata: dict[str, str],
    topics: tuple[tuple[str, str], ...],
    size: int,
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
        )
        documents.append(document)
        document_metadata = document.get("metadata", {})
        if not isinstance(document_metadata, dict):
            raise ValueError("anchor manifest documents must include metadata")
        title = str(cast(dict[str, object], document_metadata).get("title", ""))
        query = _build_query(prefix=prefix, title=title, index=index)
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
            "language": "ko",
            "sample_size": size,
            "synthetic_sample": True,
            "sampling_strategy": "deterministic_first_n_templates",
        },
        corpus_assets=corpus_assets,
        query_assets=query_assets,
        judgment_assets=judgment_assets,
    )


def load_miracl_ko_sample(size: int = 100) -> BenchmarkCorpusManifest:
    return _build_manifest(
        dataset_id="miracl_ko",
        prefix="miracl-ko",
        metadata=MIRACL_KO_METADATA,
        topics=_MIRACL_TOPICS,
        size=size,
    )


__all__ = [
    "MIRACL_KO_METADATA",
    "load_miracl_ko_sample",
]

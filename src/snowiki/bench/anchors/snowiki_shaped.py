from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from typing import Literal

from snowiki.bench.corpus import BenchmarkCorpusManifest
from snowiki.bench.models import BenchmarkAssetManifest, BenchmarkProvenance

SNOWIKI_SHAPED_METADATA: dict[str, str] = {
    "name": "Snowiki Shaped Scripted Crawl",
    "description": (
        "Deterministic scripted-crawl manifest simulating an internal corpus with mixed "
        "Korean+English technical notes, code/doc references, topical knowledge pages, "
        "temporal coverage, and explicit abstention cases."
    ),
    "tier": "snowiki_shaped",
}

MIXED_LANGUAGE_QUOTA: float = 30.0
CODE_DOC_QUOTA: float = 25.0
TOPICAL_QUOTA: float = 30.0
TEMPORAL_QUOTA: float = 10.0
NO_ANSWER_QUOTA: float = 5.0
LLM_GENERATED_QUOTA: float = 0.0


@dataclass(frozen=True)
class _FamilyTemplate:
    family_key: str
    label: str
    subtitle: str
    focus: str


_MIXED_LANGUAGE_FAMILIES: tuple[_FamilyTemplate, ...] = (
    _FamilyTemplate(
        "hybrid_search_playbook",
        "하이브리드 검색 playbook",
        "fallback tuning",
        "mixed ko+en search debugging",
    ),
    _FamilyTemplate(
        "release_incident_digest",
        "릴리스 incident digest",
        "rollback timeline",
        "developer-visible service note",
    ),
    _FamilyTemplate(
        "wiki_import_runbook",
        "위키 import runbook",
        "attachment parsing notes",
        "pipeline operator guidance",
    ),
    _FamilyTemplate(
        "search_support_sheet",
        "검색 support sheet",
        "incident keyword map",
        "search issue triage",
    ),
    _FamilyTemplate(
        "api_glossary_bridge",
        "API glossary bridge",
        "query normalization",
        "Korean operator wording with English technical nouns",
    ),
)

_CODE_DOC_FAMILIES: tuple[_FamilyTemplate, ...] = (
    _FamilyTemplate(
        "cli_reference",
        "database query CLI",
        "search flag reference",
        "command help and examples",
    ),
    _FamilyTemplate(
        "python_api_notes",
        "data service API",
        "constructor contract",
        "typed Python integration note",
    ),
    _FamilyTemplate(
        "storage_schema",
        "storage zone schema",
        "normalized record layout",
        "filesystem-backed storage documentation",
    ),
    _FamilyTemplate(
        "config_loader",
        "config resolver",
        "repo asset path helper",
        "configuration helper reference",
    ),
    _FamilyTemplate(
        "quality_scoring",
        "quality reference guide",
        "no-answer semantics",
        "interface contract excerpt",
    ),
)

_TOPICAL_FAMILIES: tuple[_FamilyTemplate, ...] = (
    _FamilyTemplate(
        "han_river_history",
        "Han River bridges",
        "urban development overview",
        "general topical city note",
    ),
    _FamilyTemplate(
        "jeju_climate",
        "Jeju wind patterns",
        "seasonal tourism context",
        "regional climate explainer",
    ),
    _FamilyTemplate(
        "kimchi_fermentation",
        "kimchi fermentation",
        "salt and temperature factors",
        "food science summary",
    ),
    _FamilyTemplate(
        "seoul_library",
        "Seoul public libraries",
        "digital archive services",
        "civic knowledge page",
    ),
    _FamilyTemplate(
        "lunar_new_year",
        "Lunar New Year customs",
        "travel and family traditions",
        "cultural overview",
    ),
)

_TEMPORAL_FAMILIES: tuple[_FamilyTemplate, ...] = (
    _FamilyTemplate(
        "release_calendar",
        "release calendar",
        "quarterly maintenance window",
        "dated program schedule",
    ),
    _FamilyTemplate(
        "policy_rollout",
        "policy rollout",
        "crawl provenance enforcement",
        "time-sensitive governance memo",
    ),
    _FamilyTemplate(
        "conference_watch",
        "conference watch",
        "documentation refresh window",
        "dated event summary",
    ),
    _FamilyTemplate(
        "service_status",
        "service status",
        "incident remediation milestones",
        "time-bound update log",
    ),
)

_NO_ANSWER_FAMILIES: tuple[_FamilyTemplate, ...] = (
    _FamilyTemplate(
        "phantom_memo",
        "ZXQ-731 phantom memo",
        "nonexistent archive request",
        "query should abstain",
    ),
    _FamilyTemplate(
        "ghost_dataset",
        "AURORA-19 ghost dataset",
        "missing crawl snapshot",
        "query should abstain",
    ),
    _FamilyTemplate(
        "sealed_appendix",
        "KITE-204 sealed appendix",
        "unpublished field packet",
        "query should abstain",
    ),
)

_QUOTA_ORDER: tuple[str, ...] = (
    "mixed_language",
    "code_doc",
    "topical",
    "temporal",
    "no_answer",
)


def get_coverage_quotas() -> dict[str, float]:
    return {
        "mixed_language": MIXED_LANGUAGE_QUOTA,
        "code_doc": CODE_DOC_QUOTA,
        "topical": TOPICAL_QUOTA,
        "temporal": TEMPORAL_QUOTA,
        "no_answer": NO_ANSWER_QUOTA,
    }


def _asset_provenance(
    *,
    asset_kind: str,
    authoring_method: Literal["automated", "human_reviewed"],
) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        source_class="scripted_crawl",
        authoring_method=authoring_method,
        license="proprietary",
        collection_method="scripted_crawl",
        visibility_tier="developer_visible",
        contamination_status="clean",
        family_dedupe_key=f"snowiki-shaped:v1:{asset_kind}",
        authority_tier="snowiki_shaped",
    )


def _assets() -> tuple[
    tuple[BenchmarkAssetManifest, ...],
    tuple[BenchmarkAssetManifest, ...],
    tuple[BenchmarkAssetManifest, ...],
]:
    corpus_provenance = _asset_provenance(
        asset_kind="corpus",
        authoring_method="automated",
    )
    reviewed_provenance = _asset_provenance(
        asset_kind="queries",
        authoring_method="human_reviewed",
    )
    judgment_provenance = _asset_provenance(
        asset_kind="judgments",
        authoring_method="human_reviewed",
    )
    return (
        (
            BenchmarkAssetManifest(
                asset_id="snowiki_shaped_scripted_crawl_corpus",
                provenance=corpus_provenance,
            ),
        ),
        (
            BenchmarkAssetManifest(
                asset_id="snowiki_shaped_scripted_crawl_queries",
                provenance=reviewed_provenance,
            ),
        ),
        (
            BenchmarkAssetManifest(
                asset_id="snowiki_shaped_scripted_crawl_judgments",
                provenance=judgment_provenance,
            ),
        ),
    )


def _recorded_at(index: int) -> str:
    return (
        (datetime(2026, 3, 1, tzinfo=UTC) + timedelta(days=index - 1))
        .isoformat()
        .replace("+00:00", "Z")
    )


def _family_dedupe_key(bucket: str, family_key: str) -> str:
    return f"snowiki-shaped:v1:{bucket}:{family_key}"


def _allocate_counts(size: int) -> dict[str, int]:
    quotas = get_coverage_quotas()
    raw_counts = {bucket: size * (quota / 100.0) for bucket, quota in quotas.items()}
    counts = {bucket: floor(value) for bucket, value in raw_counts.items()}
    remaining = size - sum(counts.values())
    ranked_buckets = sorted(
        _QUOTA_ORDER,
        key=lambda bucket: (
            raw_counts[bucket] - counts[bucket],
            -_QUOTA_ORDER.index(bucket),
        ),
        reverse=True,
    )
    for bucket in ranked_buckets[:remaining]:
        counts[bucket] += 1
    return counts


def _build_mixed_language_document(
    *,
    document_id: str,
    family: _FamilyTemplate,
    ordinal: int,
    recorded_at: str,
    dedupe_key: str,
) -> dict[str, object]:
    title = f"{family.label} {family.subtitle} {ordinal:02d}"
    content = (
        f"{title} 문서는 scripted crawl로 수집된 internal developer note를 모사합니다. "
        f"Korean 운영 설명과 English technical vocabulary가 함께 나타나며, {family.focus}를 중심으로 "
        "related examples, operator notes, and an evidence trail을 정리합니다. "
        "운영자는 mixed-language note를 읽을 때 title keyword와 body의 API noun을 함께 활용해 관련 내용을 파악할 수 있습니다."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": "Mixed Korean+English scripted-crawl digest for bilingual reference work.",
            "recorded_at": recorded_at,
            "language": "ko+en",
            "coverage_bucket": "mixed_language",
            "source_dataset": SNOWIKI_SHAPED_METADATA["name"],
            "family_dedupe_key": dedupe_key,
            "scripted_source": "internal_crawl_digest",
        },
    }


def _build_code_doc_document(
    *,
    document_id: str,
    family: _FamilyTemplate,
    ordinal: int,
    recorded_at: str,
    dedupe_key: str,
) -> dict[str, object]:
    title = f"{family.label} {family.subtitle} {ordinal:02d}"
    content = (
        f"{title} is a scripted crawl excerpt from technical documentation. "
        f"It explains {family.focus} and includes a compact code sample:\n"
        "```python\n"
        "note = {\n"
        "    \"title\": \"Bridge maintenance note\",\n"
        "    \"status\": \"active\",\n"
        "}\n"
        "print(note[\"title\"])\n"
        "```\n"
        "The note highlights interface fields, API signatures, and implementation constraints for code/document system integration."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": "Code and technical documentation snippet for general system integration.",
            "recorded_at": recorded_at,
            "language": "en",
            "coverage_bucket": "code_doc",
            "source_dataset": SNOWIKI_SHAPED_METADATA["name"],
            "family_dedupe_key": dedupe_key,
            "scripted_source": "technical_docs_crawl",
        },
    }


def _build_topical_document(
    *,
    document_id: str,
    family: _FamilyTemplate,
    ordinal: int,
    recorded_at: str,
    dedupe_key: str,
) -> dict[str, object]:
    title = f"{family.label} {family.subtitle} {ordinal:02d}"
    content = (
        f"{title} is a general-knowledge topical page shaped after scripted crawl outputs. "
        f"It summarizes {family.focus} with concise factual prose, definitions, notable examples, and common reference terms. "
        "The page is intentionally compact so system operations stay lightweight while still resembling a realistic knowledge article."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": "General topical page for broad subject coverage.",
            "recorded_at": recorded_at,
            "language": "en",
            "coverage_bucket": "topical",
            "source_dataset": SNOWIKI_SHAPED_METADATA["name"],
            "family_dedupe_key": dedupe_key,
            "scripted_source": "topical_crawl_page",
        },
    }


def _build_temporal_document(
    *,
    document_id: str,
    family: _FamilyTemplate,
    ordinal: int,
    recorded_at: str,
    dedupe_key: str,
) -> dict[str, object]:
    year = 2026 + ((ordinal - 1) % 2)
    month = 4 + ((ordinal - 1) % 6)
    title = f"{family.label} {family.subtitle} {ordinal:02d}"
    content = (
        f"{title} captures a dated update window. On {year}-{month:02d}-15 the team published a refresh covering {family.focus}. "
        f"A follow-up checkpoint on {year}-{month:02d}-28 confirmed which reference materials changed and what operators should revisit next."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": "Time-sensitive operational update for data verification.",
            "recorded_at": recorded_at,
            "language": "en",
            "coverage_bucket": "temporal",
            "source_dataset": SNOWIKI_SHAPED_METADATA["name"],
            "family_dedupe_key": dedupe_key,
            "effective_date": f"{year}-{month:02d}-15",
            "scripted_source": "dated_ops_feed",
        },
    }


def _build_no_answer_document(
    *,
    document_id: str,
    family: _FamilyTemplate,
    ordinal: int,
    recorded_at: str,
    dedupe_key: str,
) -> dict[str, object]:
    title = f"Archive operations digest {ordinal:02d}"
    content = (
        "This archive digest describes ordinary maintenance, checksum review, and storage rotation. "
        f"It is intentionally unrelated to {family.label} so the paired query should abstain instead of matching a near duplicate."
    )
    return {
        "id": document_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": "Unrelated archive digest paired with a no-answer query family.",
            "recorded_at": recorded_at,
            "language": "en",
            "coverage_bucket": "no_answer",
            "source_dataset": SNOWIKI_SHAPED_METADATA["name"],
            "family_dedupe_key": dedupe_key,
            "scripted_source": "maintenance_crawl_digest",
        },
    }


def _build_query(
    *,
    query_id: str,
    bucket: str,
    family: _FamilyTemplate,
    ordinal: int,
    dedupe_key: str,
) -> dict[str, object]:
    if bucket == "mixed_language":
        text = f"{family.label}에서 {family.subtitle} 관련 English search hint 정리된 문서 찾아줘"
        kind = "topical" if ordinal % 2 == 0 else "known-item"
        group = "mixed_ko_en"
    elif bucket == "code_doc":
        text = (
            f"Which technical note documents {family.label} and the {family.subtitle}?"
        )
        kind = "known-item"
        group = "code_doc"
    elif bucket == "topical":
        text = (
            f"Looking for the topical page about {family.label} and {family.subtitle}"
        )
        kind = "topical"
        group = "topical"
    elif bucket == "temporal":
        text = f"What changed in the dated update for {family.label} {family.subtitle}?"
        kind = "temporal"
        group = "temporal"
    else:
        text = f"Find the source document for {family.label} {family.subtitle}"
        kind = "known-item" if ordinal % 2 == 0 else "topical"
        group = "no_answer"

    query: dict[str, object] = {
        "id": query_id,
        "text": text,
        "group": group,
        "kind": kind,
        "tags": ["snowiki_shaped", bucket, family.family_key],
        "family_dedupe_key": dedupe_key,
    }
    if bucket == "no_answer":
        query["no_answer"] = True
    return query


def _build_bucket_entries(
    *,
    bucket: str,
    count: int,
    start_index: int,
) -> tuple[
    list[dict[str, object]], list[dict[str, object]], dict[str, list[dict[str, object]]]
]:
    if count <= 0:
        return [], [], {}

    if bucket == "mixed_language":
        families = _MIXED_LANGUAGE_FAMILIES
        document_builder = _build_mixed_language_document
    elif bucket == "code_doc":
        families = _CODE_DOC_FAMILIES
        document_builder = _build_code_doc_document
    elif bucket == "topical":
        families = _TOPICAL_FAMILIES
        document_builder = _build_topical_document
    elif bucket == "temporal":
        families = _TEMPORAL_FAMILIES
        document_builder = _build_temporal_document
    else:
        families = _NO_ANSWER_FAMILIES
        document_builder = _build_no_answer_document

    documents: list[dict[str, object]] = []
    queries: list[dict[str, object]] = []
    judgments: dict[str, list[dict[str, object]]] = {}

    for offset in range(count):
        index = start_index + offset
        family = families[offset % len(families)]
        dedupe_key = _family_dedupe_key(bucket, family.family_key)
        document_id = f"snowiki-shaped-doc-{index:04d}"
        query_id = f"snowiki-shaped-q-{index:04d}"
        recorded_at = _recorded_at(index)
        documents.append(
            document_builder(
                document_id=document_id,
                family=family,
                ordinal=index,
                recorded_at=recorded_at,
                dedupe_key=dedupe_key,
            )
        )
        queries.append(
            _build_query(
                query_id=query_id,
                bucket=bucket,
                family=family,
                ordinal=index,
                dedupe_key=dedupe_key,
            )
        )
        if bucket != "no_answer":
            judgments[query_id] = [
                {
                    "query_id": query_id,
                    "doc_id": document_id,
                    "relevance": 1,
                }
            ]

    return documents, queries, judgments


def load_snowiki_shaped_suite(size: int = 100) -> BenchmarkCorpusManifest:
    if size < 1:
        raise ValueError("snowiki_shaped sample size must be at least 1")

    counts = _allocate_counts(size)
    corpus_assets, query_assets, judgment_assets = _assets()
    documents: list[dict[str, object]] = []
    queries: list[dict[str, object]] = []
    judgments: dict[str, list[dict[str, object]]] = {}

    next_index = 1
    for bucket in _QUOTA_ORDER:
        bucket_documents, bucket_queries, bucket_judgments = _build_bucket_entries(
            bucket=bucket,
            count=counts[bucket],
            start_index=next_index,
        )
        documents.extend(bucket_documents)
        queries.extend(bucket_queries)
        judgments.update(bucket_judgments)
        next_index += counts[bucket]

    return BenchmarkCorpusManifest(
        tier="snowiki_shaped",
        documents=documents,
        queries=queries,
        judgments=judgments,
        dataset_id="snowiki_shaped",
        dataset_name=SNOWIKI_SHAPED_METADATA["name"],
        dataset_description=SNOWIKI_SHAPED_METADATA["description"],
        dataset_metadata={
            **SNOWIKI_SHAPED_METADATA,
            "sample_size": size,
            "synthetic_sample": True,
            "source_model": "deterministic_scripted_crawl_facsimile",
            "coverage_quotas_pct": get_coverage_quotas(),
            "coverage_counts": counts,
            "language_profile": "mixed_ko_en_internal",
            "provenance_policy": "scripted crawl corpus with human-reviewed queries and judgments",
            "llm_generated_share_pct": LLM_GENERATED_QUOTA,
            "llm_generated_used": False,
            "llm_generated_role": "auxiliary_only",
            "authoritative_source": "scripted_crawl",
        },
        corpus_assets=corpus_assets,
        query_assets=query_assets,
        judgment_assets=judgment_assets,
    )


__all__ = [
    "CODE_DOC_QUOTA",
    "LLM_GENERATED_QUOTA",
    "MIXED_LANGUAGE_QUOTA",
    "NO_ANSWER_QUOTA",
    "SNOWIKI_SHAPED_METADATA",
    "TEMPORAL_QUOTA",
    "TOPICAL_QUOTA",
    "get_coverage_quotas",
    "load_snowiki_shaped_suite",
]

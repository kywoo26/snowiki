from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar, Literal, cast

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    model_validator,
)

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class RecordModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)

    id: str
    path: str | None = None
    content: str = Field(validation_alias=AliasChoices("content", "text"))
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    raw_ref: dict[str, JsonValue] | None = None


class PageModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    id: str
    path: str
    title: str
    summary: str | None = None
    body: str
    tags: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    record_ids: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class BenchmarkHit(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    id: str
    path: str
    title: str | None = None
    score: float


class QueryResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    query_id: str
    hits: list[BenchmarkHit] = Field(default_factory=list)

    def to_legacy_dict(self) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in self.hits]


class PerQueryQuality(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    query_id: str
    ranked_ids: list[str] = Field(default_factory=list)
    relevant_ids: list[str] = Field(default_factory=list)
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


class QualityMetrics(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    top_k: int
    queries_evaluated: int
    per_query: list[PerQueryQuality] = Field(default_factory=list)

    def to_legacy_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class QualitySlices(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    group: dict[str, QualityMetrics] = Field(default_factory=dict)
    kind: dict[str, QualityMetrics] = Field(default_factory=dict)

    def to_legacy_dict(self) -> dict[str, dict[str, dict[str, object]]]:
        return {
            "group": {
                name: metrics.to_legacy_dict() for name, metrics in self.group.items()
            },
            "kind": {
                name: metrics.to_legacy_dict() for name, metrics in self.kind.items()
            },
        }


class ThresholdResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    gate: str
    metric: str
    value: float | str | None
    delta: float | None
    verdict: Literal["PASS", "FAIL", "WARN"]
    threshold: float | str | None
    warnings: list[str] = Field(default_factory=list)

    def to_legacy_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class QualityReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    overall: QualityMetrics
    slices: QualitySlices
    thresholds: list[ThresholdResult] = Field(default_factory=list)

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall.to_legacy_dict(),
            "slices": self.slices.to_legacy_dict(),
            "thresholds": [entry.to_legacy_dict() for entry in self.thresholds],
        }


class LatencyMetrics(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    p50_ms: float
    p95_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float

    def to_legacy_dict(self) -> dict[str, float]:
        return self.model_dump(mode="json")


class PresetSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    query_kinds: list[str] = Field(default_factory=list)
    top_k: int
    baselines: list[str] = Field(default_factory=list)

    def to_legacy_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class CorpusSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    records_indexed: int
    pages_indexed: int
    raw_documents: int
    blended_documents: int
    queries_evaluated: int

    def to_legacy_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class BaselineResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    name: str
    latency: LatencyMetrics
    quality: QualityReport
    queries: list[QueryResult] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_queries(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(cast(Mapping[object, object], value))
        queries = payload.get("queries")
        if isinstance(queries, Mapping):
            query_items = list(queries.items())
            payload["queries"] = [
                {"query_id": query_id, "hits": hits} for query_id, hits in query_items
            ]
        return payload

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "latency": self.latency.to_legacy_dict(),
            "quality": self.quality.to_legacy_dict(),
            "queries": {
                query.query_id: query.to_legacy_dict() for query in self.queries
            },
        }


class BenchmarkReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    preset: PresetSummary
    corpus: CorpusSummary
    baselines: dict[str, BaselineResult]

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset.to_legacy_dict(),
            "corpus": self.corpus.to_legacy_dict(),
            "baselines": {
                name: result.to_legacy_dict() for name, result in self.baselines.items()
            },
        }


RECORD_LIST_ADAPTER = TypeAdapter(list[RecordModel])
PAGE_LIST_ADAPTER = TypeAdapter(list[PageModel])
QUERY_RESULT_LIST_ADAPTER = TypeAdapter(list[QueryResult])


def validate_record_dict(payload: object) -> RecordModel:
    return RecordModel.model_validate(payload)


def validate_page_dict(payload: object) -> PageModel:
    return PageModel.model_validate(payload)


def validate_baseline_result(payload: object) -> BaselineResult:
    return BaselineResult.model_validate(payload)


__all__ = [
    "BaselineResult",
    "BenchmarkHit",
    "BenchmarkReport",
    "CorpusSummary",
    "JsonScalar",
    "JsonValue",
    "LatencyMetrics",
    "PAGE_LIST_ADAPTER",
    "PageModel",
    "PerQueryQuality",
    "PresetSummary",
    "QUERY_RESULT_LIST_ADAPTER",
    "QualityMetrics",
    "QualityReport",
    "QualitySlices",
    "QueryResult",
    "RECORD_LIST_ADAPTER",
    "RecordModel",
    "ThresholdResult",
    "validate_baseline_result",
    "validate_page_dict",
    "validate_record_dict",
]

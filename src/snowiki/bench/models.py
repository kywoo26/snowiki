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

from snowiki.search.registry import all_candidates, resolve_legacy_tokenizer

from .presets import normalize_benchmark_baseline, normalize_benchmark_baselines

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


class BenchmarkQueryMetadata(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    tags: list[str] = Field(default_factory=list)
    no_answer: bool = False


class QueryResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    query_id: str
    metadata: BenchmarkQueryMetadata = Field(default_factory=BenchmarkQueryMetadata)
    hits: list[BenchmarkHit] = Field(default_factory=list)

    def to_legacy_dict(self) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in self.hits]


class PerQueryQuality(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    query_id: str
    ranked_ids: list[str] = Field(default_factory=list)
    relevant_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    no_answer: bool = False
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


class QualityMetrics(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    top_k: int
    top_ks: list[int] = Field(default_factory=list)
    metrics_by_k: dict[str, dict[str, float]] = Field(default_factory=dict)
    queries_evaluated: int
    per_query: list[PerQueryQuality] = Field(default_factory=list)

    def to_legacy_dict(self) -> dict[str, object]:
        payload = self.model_dump(mode="json")
        if not self.top_ks:
            payload.pop("top_ks", None)
        if not self.metrics_by_k:
            payload.pop("metrics_by_k", None)
        per_query = []
        for item in payload.get("per_query", []):
            if not item.get("tags"):
                item.pop("tags", None)
            if item.get("no_answer") is False:
                item.pop("no_answer", None)
            per_query.append(item)
        payload["per_query"] = per_query
        return payload


class QualitySlices(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    group: dict[str, QualityMetrics] = Field(default_factory=dict)
    kind: dict[str, QualityMetrics] = Field(default_factory=dict)
    subset: dict[str, QualityMetrics] = Field(default_factory=dict)

    def to_legacy_dict(self) -> dict[str, dict[str, dict[str, object]]]:
        payload = {
            "group": {
                name: metrics.to_legacy_dict() for name, metrics in self.group.items()
            },
            "kind": {
                name: metrics.to_legacy_dict() for name, metrics in self.kind.items()
            },
        }
        if self.subset:
            payload["subset"] = {
                name: metrics.to_legacy_dict() for name, metrics in self.subset.items()
            }
        return payload


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
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)

    overall: QualityMetrics | None = None
    slices: QualitySlices | None = None
    thresholds: list[ThresholdResult] = Field(default_factory=list)

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall.to_legacy_dict() if self.overall else {},
            "slices": self.slices.to_legacy_dict() if self.slices else {},
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
    top_ks: list[int] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_baselines(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(cast(Mapping[object, object], value))
        baselines = payload.get("baselines")
        if isinstance(baselines, list):
            payload["baselines"] = list(
                normalize_benchmark_baselines(str(item) for item in baselines)
            )
        return payload

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
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)

    name: str
    tokenizer_name: str | None = None
    latency: LatencyMetrics | None = None
    quality: QualityReport | None = None
    queries: list[QueryResult] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_queries(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(cast(Mapping[object, object], value))
        name = payload.get("name")
        if isinstance(name, str):
            payload["name"] = normalize_benchmark_baseline(name)

        tokenizer_name = payload.get("tokenizer_name")
        if isinstance(tokenizer_name, str) and tokenizer_name.strip():
            name = tokenizer_name.strip()
            canonical_names = {spec.name for spec in all_candidates()}
            if name in canonical_names:
                payload["tokenizer_name"] = name
            else:
                payload["tokenizer_name"] = resolve_legacy_tokenizer(
                    benchmark_alias=name
                )

        queries = payload.get("queries")
        if isinstance(queries, Mapping):
            query_items = list(queries.items())
            payload["queries"] = [
                {"query_id": query_id, "hits": hits} for query_id, hits in query_items
            ]
        return payload

    def to_legacy_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "latency": self.latency.to_legacy_dict() if self.latency else {},
            "quality": self.quality.to_legacy_dict() if self.quality else {},
            "queries": {
                query.query_id: query.to_legacy_dict() for query in self.queries
            },
        }
        if self.tokenizer_name is not None:
            payload["tokenizer_name"] = self.tokenizer_name
        return payload


class PlatformSupportEvidence(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    macos: Literal["supported", "unsupported", "unknown"]
    linux_x86_64: Literal["supported", "unsupported", "unknown"]
    linux_aarch64: Literal["supported", "unsupported", "unknown"]
    windows: Literal["supported", "unsupported", "unknown"]
    fallback_behavior: Literal[
        "none", "fail_closed", "fail_open", "requires_fallback", "unknown"
    ]


class InstallErgonomicsEvidence(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    prebuilt_available: bool | None = None
    build_from_source_required: bool | None = None
    hidden_bootstrap_steps: bool | None = None
    operational_complexity: Literal["low", "medium", "high", "unknown"]


class CandidateOperationalEvidence(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    memory_peak_rss_mb: float | None = None
    memory_evidence_status: Literal["measured", "not_measured"]
    disk_size_mb: float | None = None
    disk_size_evidence_status: Literal["measured", "not_measured"]
    platform_support: PlatformSupportEvidence
    install_ergonomics: InstallErgonomicsEvidence
    zero_cost_admission: bool
    admission_reason: str


class CandidateMatrixEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    candidate_name: str
    evidence_baseline: str | None = None
    role: Literal["control", "candidate"]
    admission_status: Literal["admitted", "not_admitted"]
    control: bool
    operational_evidence: CandidateOperationalEvidence | None = None
    baseline: BaselineResult | None = None

    def to_report_dict(self) -> dict[str, object]:
        payload = self.model_dump(mode="json")
        if self.baseline is None:
            payload.pop("baseline", None)
        if self.operational_evidence is None:
            payload.pop("operational_evidence", None)
        return payload


class CandidateDecision(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    candidate_name: str
    evidence_baseline: str | None = None
    disposition: Literal["promote", "benchmark_only", "reject"]
    overall_quality_gate_passed: bool
    operational_evidence_present: bool
    mixed_deltas: dict[str, float] = Field(default_factory=dict)
    ko_recall_delta: float | None = None
    en_recall_delta: float | None = None
    latency_p95_ratio: float | None = None
    reasons: list[str] = Field(default_factory=list)

    def to_report_dict(self) -> dict[str, object]:
        payload = self.model_dump(mode="json")
        if self.evidence_baseline is None:
            payload.pop("evidence_baseline", None)
        if self.ko_recall_delta is None:
            payload.pop("ko_recall_delta", None)
        if self.en_recall_delta is None:
            payload.pop("en_recall_delta", None)
        if self.latency_p95_ratio is None:
            payload.pop("latency_p95_ratio", None)
        return payload


class CandidateMatrixReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    candidates: list[CandidateMatrixEntry] = Field(default_factory=list)
    decisions: list[CandidateDecision] = Field(default_factory=list)

    def to_report_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "candidates": [candidate.to_report_dict() for candidate in self.candidates]
        }
        if self.decisions:
            payload["decisions"] = [
                decision.to_report_dict() for decision in self.decisions
            ]
        return payload


class BenchmarkReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)

    preset: PresetSummary | None = None
    corpus: CorpusSummary | None = None
    baselines: dict[str, BaselineResult] = Field(default_factory=dict)
    candidate_matrix: CandidateMatrixReport | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_baseline_keys(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(cast(Mapping[object, object], value))
        baselines = payload.get("baselines")
        if not isinstance(baselines, Mapping):
            return payload

        normalized: dict[str, object] = {}
        for key, baseline_payload in cast(Mapping[object, object], baselines).items():
            normalized_key = normalize_benchmark_baseline(str(key))
            normalized[normalized_key] = baseline_payload
        payload["baselines"] = normalized
        return payload

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset.to_legacy_dict() if self.preset else {},
            "corpus": self.corpus.to_legacy_dict() if self.corpus else {},
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
    "BenchmarkQueryMetadata",
    "BenchmarkReport",
    "CandidateOperationalEvidence",
    "CandidateDecision",
    "CandidateMatrixEntry",
    "CandidateMatrixReport",
    "CorpusSummary",
    "InstallErgonomicsEvidence",
    "JsonScalar",
    "JsonValue",
    "LatencyMetrics",
    "PAGE_LIST_ADAPTER",
    "PageModel",
    "PerQueryQuality",
    "PresetSummary",
    "PlatformSupportEvidence",
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

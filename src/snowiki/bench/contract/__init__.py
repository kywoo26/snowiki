"""Benchmark contract definitions and scoring semantics.

Benchmark semantics:
- Retrieval unit: a single query-document pair scored by the retrieval engine.
- Relevance unit: a binary judgment of whether a document is relevant to a query.
- Reporting unit: a query together with its full ranked result set and aggregated
  metrics.
- No-answer semantics: a no-answer query is one where the correct engine behavior
  is to return no relevant documents. The engine should abstain or reject; any
  returned document is a false positive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass(frozen=True)
class MetricThreshold:
    metric: str
    value: float
    operator: Literal[">=", "<="] = ">="


@dataclass(frozen=True)
class ReportEntry:
    gate: str
    metric: str
    value: float | str
    delta: float | None
    verdict: Literal["PASS", "FAIL", "WARN"]
    threshold: float | str | None
    warnings: list[str]


@dataclass(frozen=True)
class NoAnswerScoringPolicy:
    """Controls how no-answer benchmark queries contribute to quality metrics."""

    mode: Literal["ignore", "penalize_false_positives", "require_abstention"]
    false_positive_penalty: float = 1.0
    abstention_bonus: float | None = None


class CorpusContract(TypedDict):
    queries: str
    judgments: str


class ThresholdsContract(TypedDict):
    overall: list[MetricThreshold]
    slices: dict[str, list[MetricThreshold]]


class ReportSchemaContract(TypedDict):
    fields: list[str]
    entry_type: type[ReportEntry]


@dataclass(frozen=True)
class CandidatePolicyThresholds:
    mixed_delta_min: float
    slice_recall_non_regression_floor: float
    latency_p95_ratio_max: float


class MetadataContract(TypedDict):
    phase: int
    status: str
    flow: list[str]
    exclusions: list[str]


class BenchmarkContract(TypedDict):
    corpus: CorpusContract
    thresholds: ThresholdsContract
    report_schema: ReportSchemaContract
    metadata: MetadataContract


class CandidatePolicyContract(TypedDict):
    control_candidate_name: str
    control_decision_baseline: str
    mixed_delta_metrics: list[str]
    thresholds: CandidatePolicyThresholds


BENCHMARK_CORPUS: CorpusContract = {
    "queries": "benchmarks/queries.json",
    "judgments": "benchmarks/judgments.json",
}

BENCHMARK_THRESHOLDS: ThresholdsContract = {
    "overall": [
        MetricThreshold("recall_at_k", 0.72),
        MetricThreshold("mrr", 0.70),
        MetricThreshold("ndcg_at_k", 0.67),
        MetricThreshold("p50_ms", 5950.0, "<="),
        MetricThreshold("p95_ms", 6300.0, "<="),
    ],
    "slices": {
        "known-item": [
            MetricThreshold("recall_at_k", 0.70),
            MetricThreshold("mrr", 0.60),
        ],
        "topical": [
            MetricThreshold("recall_at_k", 0.49),
            MetricThreshold("ndcg_at_k", 0.50),
        ],
        "temporal": [
            MetricThreshold("recall_at_k", 0.47),
        ],
    },
}

CANDIDATE_POLICY: CandidatePolicyContract = {
    "control_candidate_name": "regex_v1",
    "control_decision_baseline": "lexical",
    "mixed_delta_metrics": ["recall_at_k", "mrr", "ndcg_at_k"],
    "thresholds": CandidatePolicyThresholds(
        mixed_delta_min=0.03,
        slice_recall_non_regression_floor=-0.01,
        latency_p95_ratio_max=1.25,
    ),
}

DEFAULT_NO_ANSWER_SCORING_POLICY = NoAnswerScoringPolicy(
    mode="penalize_false_positives"
)


def get_benchmark_contract() -> BenchmarkContract:
    """Returns the frozen benchmark contract."""
    return {
        "corpus": BENCHMARK_CORPUS,
        "thresholds": BENCHMARK_THRESHOLDS,
        "report_schema": {
            "fields": [
                "gate",
                "metric",
                "value",
                "delta",
                "verdict",
                "threshold",
                "warnings",
            ],
            "entry_type": ReportEntry,
        },
        "metadata": {
            "phase": 1,
            "status": "frozen",
            "flow": ["ingest", "rebuild", "query", "status", "lint"],
            "exclusions": ["sync", "edit"],
        },
    }

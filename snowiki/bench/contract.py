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


class CorpusContract(TypedDict):
    queries: str
    judgments: str


class ThresholdsContract(TypedDict):
    overall: list[MetricThreshold]
    slices: dict[str, list[MetricThreshold]]


class ReportSchemaContract(TypedDict):
    fields: list[str]
    entry_type: type[ReportEntry]


class MetadataContract(TypedDict):
    phase: int
    status: str
    flow: list[str]
    exclusions: list[str]


class Phase1Contract(TypedDict):
    corpus: CorpusContract
    thresholds: ThresholdsContract
    report_schema: ReportSchemaContract
    metadata: MetadataContract


PHASE_1_CORPUS: CorpusContract = {
    "queries": "benchmarks/queries.json",
    "judgments": "benchmarks/judgments.json",
}

PHASE_1_THRESHOLDS: ThresholdsContract = {
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


def get_phase_1_contract() -> Phase1Contract:
    """Returns the frozen phase-1 benchmark contract."""
    return {
        "corpus": PHASE_1_CORPUS,
        "thresholds": PHASE_1_THRESHOLDS,
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

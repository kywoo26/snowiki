from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

from .contract import (
    PHASE_1_CORPUS,
    PHASE_1_THRESHOLDS,
    MetricThreshold,
    ReportEntry,
    get_phase_1_contract,
)
from .corpus import (
    CANONICAL_BENCHMARK_FIXTURE_PATHS,
    BenchmarkFixture,
    canonical_benchmark_fixtures,
    seed_canonical_benchmark_root,
)
from .latency import LatencySummary, measure_latency
from .phase1_correctness import run_phase1_correctness_flow, validate_phase1_workspace
from .phase1_latency import run_phase1_latency_evaluation
from .presets import BenchmarkPreset, get_preset, list_presets
from .quality import QualitySummary, evaluate_quality

_RENDER = import_module("snowiki.bench.render")
_REPORT = import_module("snowiki.bench.report")
_VERDICT = import_module("snowiki.bench.verdict")


class _RenderReportText(Protocol):
    def __call__(self, report: dict[str, object]) -> str: ...


class _GenerateReport(Protocol):
    def __call__(self, root: Path, *, preset_name: str) -> dict[str, object]: ...


class _ReportToInt(Protocol):
    def __call__(self, report: dict[str, object]) -> int: ...


class _ReportToDict(Protocol):
    def __call__(self, report: dict[str, object]) -> dict[str, object]: ...


render_report_text = cast(_RenderReportText, _RENDER.render_report_text)
generate_report = cast(_GenerateReport, _REPORT.generate_report)
benchmark_exit_code = cast(_ReportToInt, _VERDICT.benchmark_exit_code)
benchmark_verdict = cast(_ReportToDict, _VERDICT.benchmark_verdict)
informational_warning_count = cast(_ReportToInt, _VERDICT.informational_warning_count)
performance_threshold_failure_count = cast(
    _ReportToInt, _VERDICT.performance_threshold_failure_count
)
retrieval_threshold_failure_count = cast(
    _ReportToInt, _VERDICT.retrieval_threshold_failure_count
)
structural_failure_count = cast(_ReportToInt, _VERDICT.structural_failure_count)

__all__ = [
    "BenchmarkFixture",
    "BenchmarkPreset",
    "CANONICAL_BENCHMARK_FIXTURE_PATHS",
    "canonical_benchmark_fixtures",
    "LatencySummary",
    "MetricThreshold",
    "PHASE_1_CORPUS",
    "PHASE_1_THRESHOLDS",
    "QualitySummary",
    "ReportEntry",
    "benchmark_exit_code",
    "seed_canonical_benchmark_root",
    "benchmark_verdict",
    "evaluate_quality",
    "generate_report",
    "get_phase_1_contract",
    "get_preset",
    "informational_warning_count",
    "list_presets",
    "measure_latency",
    "performance_threshold_failure_count",
    "run_phase1_latency_evaluation",
    "render_report_text",
    "retrieval_threshold_failure_count",
    "run_phase1_correctness_flow",
    "structural_failure_count",
    "validate_phase1_workspace",
]

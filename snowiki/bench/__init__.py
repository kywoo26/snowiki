from __future__ import annotations

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
from .report import (
    benchmark_exit_code,
    benchmark_verdict,
    generate_report,
    informational_warning_count,
    performance_threshold_failure_count,
    render_report_text,
    retrieval_threshold_failure_count,
    structural_failure_count,
)
from .semantic_slots import SemanticSlotsConfig
from .token_reduction import TokenReductionSummary, compare_token_usage

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
    "SemanticSlotsConfig",
    "TokenReductionSummary",
    "compare_token_usage",
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

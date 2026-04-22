"""Architecture guard tests for the reorganized benchmark package."""

from __future__ import annotations

import pkgutil
from importlib import import_module
from pathlib import Path

import pytest

import snowiki.bench as bench

pytestmark = pytest.mark.bench

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_ROOT = REPO_ROOT / "src" / "snowiki" / "bench"
BENCH_SUBPACKAGES: tuple[str, ...] = (
    "contract",
    "datasets",
    "evaluation",
    "validation",
    "reporting",
    "runtime",
)
EXPECTED_PUBLIC_API: tuple[str, ...] = (
    "BENCHMARK_CORPUS",
    "BENCHMARK_THRESHOLDS",
    "BenchmarkCorpusManifest",
    "BenchmarkPreset",
    "DEFAULT_NO_ANSWER_SCORING_POLICY",
    "MetricThreshold",
    "NoAnswerScoringPolicy",
    "ReportEntry",
    "benchmark_exit_code",
    "benchmark_verdict",
    "generate_report",
    "get_benchmark_contract",
    "get_preset",
    "list_presets",
    "render_report_text",
    "seed_canonical_benchmark_root",
    "write_tokenizer_comparison_artifact",
)
KEY_SYMBOL_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("snowiki.bench.contract", "get_benchmark_contract"),
    ("snowiki.bench.contract.presets", "BenchmarkPreset"),
    ("snowiki.bench.datasets", "BenchmarkDatasetId"),
    ("snowiki.bench.evaluation", "run_baseline_comparison"),
    ("snowiki.bench.evaluation.index", "CorpusBundle"),
    ("snowiki.bench.validation", "run_correctness_flow"),
    ("snowiki.bench.reporting.report", "generate_report"),
    ("snowiki.bench.reporting.verdict", "benchmark_verdict"),
    ("snowiki.bench.runtime", "BenchmarkCorpusManifest"),
)
ALL_BENCH_MODULES: tuple[str, ...] = tuple(
    sorted(
        module_info.name
        for module_info in pkgutil.walk_packages(bench.__path__, prefix=f"{bench.__name__}.")
    )
)


def test_bench_subpackages_exist_on_disk() -> None:
    for subpackage in BENCH_SUBPACKAGES:
        subpackage_root = BENCH_ROOT / subpackage
        assert subpackage_root.is_dir(), f"missing bench subpackage directory: {subpackage_root}"
        assert (subpackage_root / "__init__.py").is_file(), (
            f"missing package marker for bench subpackage: {subpackage_root / '__init__.py'}"
        )


def test_no_legacy_flat_file_modules_remain_at_bench_root() -> None:
    legacy_flat_modules = tuple(
        sorted(path.name for path in BENCH_ROOT.glob("*.py") if path.name != "__init__.py")
    )
    assert legacy_flat_modules == ()


def test_bench_public_api_surface_is_minimal_and_intentional() -> None:
    assert tuple(bench.__all__) == EXPECTED_PUBLIC_API
    assert set(bench.__all__).isdisjoint(BENCH_SUBPACKAGES)
    for public_name in bench.__all__:
        assert hasattr(bench, public_name), f"bench is missing public export: {public_name}"


@pytest.mark.parametrize(("module_path", "symbol_name"), KEY_SYMBOL_LOCATIONS)
def test_key_symbols_are_importable_from_new_locations(
    module_path: str, symbol_name: str
) -> None:
    module = import_module(module_path)
    assert getattr(module, symbol_name) is not None


def test_all_bench_modules_import_without_circular_import_failures() -> None:
    imported_modules = {
        module_name: import_module(module_name) for module_name in ALL_BENCH_MODULES
    }
    assert tuple(sorted(imported_modules)) == ALL_BENCH_MODULES

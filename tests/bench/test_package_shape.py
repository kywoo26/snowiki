from __future__ import annotations

from pathlib import Path

import snowiki.bench as bench

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_ROOT = REPO_ROOT / "src" / "snowiki" / "bench"
EXPECTED_FILES: tuple[str, ...] = (
    "__init__.py",
    "cache.py",
    "datasets.py",
    "metrics.py",
    "normalization.py",
    "report.py",
    "runner.py",
    "specs.py",
    "targets.py",
)
EXPECTED_EXPORTS: tuple[str, ...] = (
    "EvaluationMatrix",
    "DatasetManifest",
    "LevelConfig",
    "BenchmarkTargetSpec",
    "BenchmarkRunResult",
    "CellResult",
    "MetricResult",
    "load_matrix",
    "TargetRegistry",
    "MetricRegistry",
    "run_matrix",
    "render_json",
)
LEGACY_EXPORTS: tuple[str, ...] = (
    "_".join(("benchmark", "verdict")),
    "generate_report",
    "seed_canonical_benchmark_root",
)


def test_bench_root_contains_only_lean_python_modules() -> None:
    assert tuple(sorted(path.name for path in BENCH_ROOT.glob("*.py"))) == EXPECTED_FILES
    assert tuple(
        sorted(
            path.name
            for path in BENCH_ROOT.iterdir()
            if path.is_dir() and path.name != "__pycache__"
        )
    ) == ()


def test_bench_public_exports_match_lean_surface() -> None:
    assert tuple(bench.__all__) == EXPECTED_EXPORTS
    for public_name in EXPECTED_EXPORTS:
        assert hasattr(bench, public_name)


def test_legacy_exports_are_gone() -> None:
    for legacy_name in LEGACY_EXPORTS:
        assert not hasattr(bench, legacy_name)

"""Import consistency tests for the reorganized benchmark package."""

from __future__ import annotations

import pkgutil
from importlib import import_module

import pytest

import snowiki.bench as bench

pytestmark = pytest.mark.bench

BENCH_PACKAGE_NAMES: tuple[str, ...] = tuple(
    sorted(
        module_info.name
        for module_info in pkgutil.walk_packages(bench.__path__, prefix=f"{bench.__name__}.")
        if module_info.ispkg
    )
)


@pytest.mark.parametrize("package_name", BENCH_PACKAGE_NAMES)
def test_all_bench_subpackages_import_cleanly(package_name: str) -> None:
    package = import_module(package_name)
    assert package.__name__ == package_name


def test_cross_subpackage_imports_resolve_shared_symbols() -> None:
    contract = import_module("snowiki.bench.contract")
    evaluation = import_module("snowiki.bench.evaluation")
    evaluation_candidates = import_module("snowiki.bench.evaluation.candidates")
    reporting_models = import_module("snowiki.bench.reporting.models")
    reporting_report = import_module("snowiki.bench.reporting.report")
    reporting_render = import_module("snowiki.bench.reporting.render")
    reporting_verdict = import_module("snowiki.bench.reporting.verdict")
    runtime_corpus = import_module("snowiki.bench.runtime.corpus")
    runtime_quality = import_module("snowiki.bench.runtime.quality")
    validation_latency = import_module("snowiki.bench.validation.latency")

    assert reporting_report.CANDIDATE_MATRIX is evaluation.CANDIDATE_MATRIX
    assert reporting_report.BenchmarkCorpusManifest is runtime_corpus.BenchmarkCorpusManifest
    assert reporting_report.render_report_text is reporting_render.render_report_text
    assert reporting_verdict.CANDIDATE_MATRIX is evaluation_candidates.CANDIDATE_MATRIX
    assert runtime_quality.ReportEntry is contract.ReportEntry
    assert runtime_corpus.BenchmarkAssetManifest is reporting_models.BenchmarkAssetManifest
    assert validation_latency.BenchmarkCorpusManifest is runtime_corpus.BenchmarkCorpusManifest

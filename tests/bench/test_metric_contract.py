"""Tests for layer-specific metric contract and report schema."""

from __future__ import annotations

from snowiki.bench.policy import (
    get_layer_policy,
    get_quick_pr_suite,
    get_scheduled_suite,
)
from snowiki.bench.verdict import _evaluate_policy_stages


class TestLayerMetricContract:
    """Tests for layer-specific metric policies."""

    def test_pr_quick_metrics(self) -> None:
        policy = get_layer_policy("pr_official_quick")
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is True
        assert policy["sample_mode"] == "quick"

    def test_scheduled_broad_metrics(self) -> None:
        policy = get_layer_policy("scheduled_official_broad")
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is False
        assert policy["sample_mode"] == "standard"

    def test_release_proof_metrics(self) -> None:
        policy = get_layer_policy("release_proof")
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is True
        assert policy["enabled_by_default"] is False


class TestVerdictLayerSemantics:
    """Tests for layer-aware verdict computation."""

    def test_official_layer_retrieval_is_blocking(self) -> None:
        stages = _evaluate_policy_stages(
            structural_failures=0,
            retrieval_failures=1,
            performance_failures=0,
            warnings=0,
            tier="public_anchor",
            layer="pr_official_quick",
        )
        retrieval_stage = next(s for s in stages if s["name"] == "retrieval_thresholds")
        assert retrieval_stage["blocking"] is True

    def test_non_official_layer_retrieval_not_blocking(self) -> None:
        stages = _evaluate_policy_stages(
            structural_failures=0,
            retrieval_failures=1,
            performance_failures=0,
            warnings=0,
            tier="public_anchor",
            layer=None,
        )
        retrieval_stage = next(s for s in stages if s["name"] == "retrieval_thresholds")
        assert retrieval_stage["blocking"] is False

    def test_regression_retrieval_is_blocking(self) -> None:
        stages = _evaluate_policy_stages(
            structural_failures=0,
            retrieval_failures=1,
            performance_failures=0,
            warnings=0,
            tier="regression",
            layer=None,
        )
        retrieval_stage = next(s for s in stages if s["name"] == "retrieval_thresholds")
        assert retrieval_stage["blocking"] is True


class TestSuiteDefinitions:
    """Tests for official suite definitions."""

    def test_quick_pr_suite_has_six_datasets(self) -> None:
        suite = get_quick_pr_suite()
        assert len(suite) == 6
        assert suite[0] == "ms_marco_passage"
        assert "trec_dl_2020_passage" in suite
        assert "miracl_ko" in suite
        assert "miracl_en" in suite
        assert "beir_nq" in suite
        assert "beir_scifact" in suite

    def test_scheduled_suite_has_six_datasets(self) -> None:
        suite = get_scheduled_suite()
        assert len(suite) == 6
        assert "ms_marco_passage" in suite
        assert "trec_dl_2020_passage" in suite
        assert "miracl_ko" in suite
        assert "miracl_en" in suite
        assert "beir_nq" in suite
        assert "beir_scifact" in suite

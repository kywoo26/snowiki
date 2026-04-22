from __future__ import annotations

import pytest

from snowiki.bench.evaluation.candidates import (
    CANDIDATE_MATRIX,
    admitted_candidates,
    assemble_candidate_matrix,
    get_candidate,
)
from snowiki.bench.reporting.models import (
    BaselineResult,
    BenchmarkReport,
    CandidateDecision,
    CandidateMatrixReport,
    CandidateOperationalEvidence,
    InstallErgonomicsEvidence,
    PlatformSupportEvidence,
)
from snowiki.bench.reporting.verdict import evaluate_candidate_policy


def test_candidate_matrix_roster() -> None:
    names = {c.candidate_name for c in CANDIDATE_MATRIX}
    assert "regex_v1" in names
    assert "kiwi_morphology_v1" in names
    assert "kiwi_nouns_v1" in names
    assert "mecab_morphology_v1" in names
    assert "hf_wordpiece_v1" in names
    assert len(CANDIDATE_MATRIX) == 5


def test_regex_v1_is_control() -> None:
    regex = get_candidate("regex_v1")
    assert regex.role == "control"
    assert regex.control is True
    assert regex.admission_status == "admitted"
    assert regex.operational_evidence.zero_cost_admission is True
    assert regex.operational_evidence.admission_reason == "current_runtime_default"


def test_kiwi_variants_are_admitted() -> None:
    morphology = get_candidate("kiwi_morphology_v1")
    assert morphology.role == "candidate"
    assert morphology.control is False
    assert morphology.admission_status == "admitted"
    assert (
        morphology.operational_evidence.install_ergonomics.operational_complexity
        == "medium"
    )

    nouns = get_candidate("kiwi_nouns_v1")
    assert nouns.role == "candidate"
    assert nouns.control is False
    assert nouns.admission_status == "admitted"
    assert nouns.operational_evidence.platform_support.windows == "unknown"


def test_candidate_matrix_contains_only_supported_benchmark_candidates() -> None:
    assert all(candidate.evidence_baseline is not None for candidate in CANDIDATE_MATRIX)


def test_admitted_candidates_filter() -> None:
    admitted = admitted_candidates()
    names = {c.candidate_name for c in admitted}
    assert names == {
        "regex_v1",
        "kiwi_morphology_v1",
        "kiwi_nouns_v1",
        "mecab_morphology_v1",
        "hf_wordpiece_v1",
    }


def test_get_candidate_raises_on_unknown() -> None:
    with pytest.raises(KeyError, match="Unknown candidate: unknown"):
        _ = get_candidate("unknown")


def test_candidate_matrix_report_preserves_dual_identity_additively() -> None:
    report = BenchmarkReport.model_validate(
        {
            "baselines": {},
            "candidate_matrix": {
                "candidates": [
                    {
                        "candidate_name": "regex_v1",
                        "evidence_baseline": "lexical",
                        "role": "control",
                        "admission_status": "admitted",
                        "control": True,
                        "operational_evidence": {
                            "memory_peak_rss_mb": None,
                            "memory_evidence_status": "not_measured",
                            "disk_size_mb": None,
                            "disk_size_evidence_status": "not_measured",
                            "platform_support": {
                                "macos": "supported",
                                "linux_x86_64": "supported",
                                "linux_aarch64": "supported",
                                "windows": "supported",
                                "fallback_behavior": "none",
                            },
                            "install_ergonomics": {
                                "prebuilt_available": True,
                                "build_from_source_required": False,
                                "hidden_bootstrap_steps": False,
                                "operational_complexity": "low",
                            },
                            "zero_cost_admission": True,
                            "admission_reason": "current_runtime_default",
                        },
                    },
                    {
                        "candidate_name": "mecab_morphology_v1",
                        "evidence_baseline": "bm25s_mecab_full",
                        "role": "candidate",
                        "admission_status": "admitted",
                        "control": False,
                        "operational_evidence": {
                            "memory_peak_rss_mb": None,
                            "memory_evidence_status": "not_measured",
                            "disk_size_mb": None,
                            "disk_size_evidence_status": "not_measured",
                            "platform_support": {
                                "macos": "unknown",
                                "linux_x86_64": "supported",
                                "linux_aarch64": "unknown",
                                "windows": "unknown",
                                "fallback_behavior": "unknown",
                            },
                            "install_ergonomics": {
                                "prebuilt_available": True,
                                "build_from_source_required": False,
                                "hidden_bootstrap_steps": False,
                                "operational_complexity": "medium",
                            },
                            "zero_cost_admission": True,
                            "admission_reason": "admitted_mecab_candidate",
                        },
                    },
                ]
            },
        }
    )

    assert report.candidate_matrix == CandidateMatrixReport.model_validate(
        {
            "candidates": [
                {
                    "candidate_name": "regex_v1",
                    "evidence_baseline": "lexical",
                    "role": "control",
                    "admission_status": "admitted",
                    "control": True,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "supported",
                            "fallback_behavior": "none",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "low",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "current_runtime_default",
                    },
                },
                {
                    "candidate_name": "mecab_morphology_v1",
                    "evidence_baseline": "bm25s_mecab_full",
                    "role": "candidate",
                    "admission_status": "admitted",
                    "control": False,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "unknown",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "unknown",
                            "windows": "unknown",
                            "fallback_behavior": "unknown",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "medium",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "admitted_mecab_candidate",
                    },
                },
            ]
        }
    )
    assert report.candidate_matrix is not None
    assert report.candidate_matrix.candidates[0].candidate_name == "regex_v1"
    assert report.candidate_matrix.candidates[0].evidence_baseline == "lexical"
    assert report.to_legacy_dict() == {"preset": {}, "corpus": {}, "baselines": {}}


def test_assemble_candidate_matrix_groups_baselines_by_canonical_candidate() -> None:
    matrix = assemble_candidate_matrix(
        {
            "lexical": BaselineResult.model_validate(
                {"name": "lexical", "queries": []}
            ),
            "bm25s": BaselineResult.model_validate(
                {
                    "name": "bm25s",
                    "tokenizer_name": "regex_v1",
                    "queries": [],
                }
            ),
            "bm25s_kiwi_full": BaselineResult.model_validate(
                {
                    "name": "bm25s_kiwi_full",
                    "tokenizer_name": "kiwi_morphology_v1",
                    "queries": [],
                }
            ),
            "bm25s_kiwi_nouns": BaselineResult.model_validate(
                {
                    "name": "bm25s_kiwi_nouns",
                    "tokenizer_name": "kiwi_nouns_v1",
                    "queries": [],
                }
            ),
            "bm25s_hf_wordpiece": BaselineResult.model_validate(
                {
                    "name": "bm25s_hf_wordpiece",
                    "tokenizer_name": "hf_wordpiece_v1",
                    "queries": [],
                }
            ),
            "bm25s_mecab_full": BaselineResult.model_validate(
                {
                    "name": "bm25s_mecab_full",
                    "tokenizer_name": "mecab_morphology_v1",
                    "queries": [],
                }
            ),
        }
    )

    assert [entry.candidate_name for entry in matrix.candidates] == [
        "regex_v1",
        "regex_v1",
        "kiwi_morphology_v1",
        "kiwi_nouns_v1",
        "hf_wordpiece_v1",
        "mecab_morphology_v1",
    ]
    assert [entry.evidence_baseline for entry in matrix.candidates] == [
        "lexical",
        "bm25s",
        "bm25s_kiwi_full",
        "bm25s_kiwi_nouns",
        "bm25s_hf_wordpiece",
        "bm25s_mecab_full",
    ]
    assert matrix.candidates[0].control is True
    assert matrix.candidates[1].control is True
    assert matrix.candidates[0].operational_evidence == CandidateOperationalEvidence(
        memory_peak_rss_mb=None,
        memory_evidence_status="not_measured",
        disk_size_mb=None,
        disk_size_evidence_status="not_measured",
        platform_support=PlatformSupportEvidence(
            macos="supported",
            linux_x86_64="supported",
            linux_aarch64="supported",
            windows="supported",
            fallback_behavior="none",
        ),
        install_ergonomics=InstallErgonomicsEvidence(
            prebuilt_available=True,
            build_from_source_required=False,
            hidden_bootstrap_steps=False,
            operational_complexity="low",
        ),
        zero_cost_admission=True,
        admission_reason="current_runtime_default",
    )
    assert matrix.candidates[1].operational_evidence is not None
    assert matrix.candidates[1].operational_evidence.zero_cost_admission is True
    assert matrix.candidates[1].candidate_name == "regex_v1"
    assert matrix.candidates[1].baseline == BaselineResult.model_validate(
        {
            "name": "bm25s",
            "tokenizer_name": "regex_v1",
            "queries": [],
        }
    )
    policy_decisions = list(evaluate_candidate_policy(matrix))
    assert [decision.candidate_name for decision in policy_decisions] == [
        "regex_v1",
        "kiwi_morphology_v1",
        "kiwi_nouns_v1",
        "mecab_morphology_v1",
        "hf_wordpiece_v1",
    ]
    decisions = {decision.candidate_name: decision for decision in policy_decisions}
    assert decisions["regex_v1"] == CandidateDecision.model_validate(
        {
            "candidate_name": "regex_v1",
            "evidence_baseline": "lexical",
            "disposition": "reject",
            "overall_quality_gate_passed": False,
            "operational_evidence_present": False,
            "mixed_deltas": {
                "recall_at_k": 0.0,
                "mrr": 0.0,
                "ndcg_at_k": 0.0,
            },
            "ko_recall_delta": 0.0,
            "en_recall_delta": 0.0,
            "latency_p95_ratio": 1.0,
            "reasons": ["overall_quality_gate_failed"],
        }
    )
    assert decisions["kiwi_morphology_v1"].disposition == "reject"
    assert decisions["kiwi_morphology_v1"].reasons == ["overall_quality_gate_failed"]
    assert decisions["kiwi_nouns_v1"].disposition == "reject"
    assert decisions["mecab_morphology_v1"].disposition == "reject"
    assert decisions["hf_wordpiece_v1"].disposition == "reject"


def test_hf_wordpiece_candidate_is_admitted() -> None:
    candidate = get_candidate("hf_wordpiece_v1")

    assert candidate.admission_status == "admitted"
    assert candidate.evidence_baseline == "bm25s_hf_wordpiece"


def test_mecab_candidate_is_admitted() -> None:
    candidate = get_candidate("mecab_morphology_v1")

    assert candidate.admission_status == "admitted"
    assert candidate.evidence_baseline == "bm25s_mecab_full"
    assert candidate.operational_evidence.platform_support.linux_x86_64 == "supported"


def test_missing_operational_evidence_still_blocks_promote() -> None:
    matrix = CandidateMatrixReport.model_validate(
        {
            "candidates": [
                {
                    "candidate_name": "regex_v1",
                    "evidence_baseline": "lexical",
                    "role": "control",
                    "admission_status": "admitted",
                    "control": True,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "supported",
                            "fallback_behavior": "none",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "low",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "current_runtime_default",
                    },
                    "baseline": {
                        "name": "lexical",
                        "latency": {
                            "p50_ms": 1.0,
                            "p95_ms": 10.0,
                            "mean_ms": 1.0,
                            "min_ms": 1.0,
                            "max_ms": 10.0,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.72,
                                "mrr": 0.70,
                                "ndcg_at_k": 0.67,
                                "top_k": 5,
                                "queries_evaluated": 1,
                                "per_query": [],
                            },
                            "slices": {
                                "group": {
                                    "ko": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                    "en": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                    "mixed": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                },
                                "kind": {},
                            },
                            "thresholds": [
                                {
                                    "gate": "overall",
                                    "metric": "recall_at_k",
                                    "value": 0.72,
                                    "delta": 0.0,
                                    "verdict": "PASS",
                                    "threshold": 0.72,
                                    "warnings": [],
                                },
                                {
                                    "gate": "overall",
                                    "metric": "mrr",
                                    "value": 0.70,
                                    "delta": 0.0,
                                    "verdict": "PASS",
                                    "threshold": 0.70,
                                    "warnings": [],
                                },
                                {
                                    "gate": "overall",
                                    "metric": "ndcg_at_k",
                                    "value": 0.67,
                                    "delta": 0.0,
                                    "verdict": "PASS",
                                    "threshold": 0.67,
                                    "warnings": [],
                                },
                            ],
                        },
                        "queries": [],
                    },
                },
                {
                    "candidate_name": "kiwi_morphology_v1",
                    "evidence_baseline": "bm25s_kiwi_full",
                    "role": "candidate",
                    "admission_status": "admitted",
                    "control": False,
                    "baseline": {
                        "name": "bm25s_kiwi_full",
                        "tokenizer_name": "kiwi_morphology_v1",
                        "latency": {
                            "p50_ms": 1.0,
                            "p95_ms": 11.0,
                            "mean_ms": 1.0,
                            "min_ms": 1.0,
                            "max_ms": 11.0,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.76,
                                "mrr": 0.74,
                                "ndcg_at_k": 0.71,
                                "top_k": 5,
                                "queries_evaluated": 1,
                                "per_query": [],
                            },
                            "slices": {
                                "group": {
                                    "ko": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                    "en": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                    "mixed": {
                                        "recall_at_k": 0.64,
                                        "mrr": 0.64,
                                        "ndcg_at_k": 0.64,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                },
                                "kind": {},
                            },
                            "thresholds": [
                                {
                                    "gate": "overall",
                                    "metric": "recall_at_k",
                                    "value": 0.76,
                                    "delta": 0.04,
                                    "verdict": "PASS",
                                    "threshold": 0.72,
                                    "warnings": [],
                                },
                                {
                                    "gate": "overall",
                                    "metric": "mrr",
                                    "value": 0.74,
                                    "delta": 0.04,
                                    "verdict": "PASS",
                                    "threshold": 0.7,
                                    "warnings": [],
                                },
                                {
                                    "gate": "overall",
                                    "metric": "ndcg_at_k",
                                    "value": 0.71,
                                    "delta": 0.04,
                                    "verdict": "PASS",
                                    "threshold": 0.67,
                                    "warnings": [],
                                },
                            ],
                        },
                        "queries": [],
                    },
                },
            ]
        }
    )

    decisions = {
        decision.candidate_name: decision
        for decision in evaluate_candidate_policy(matrix)
    }
    assert decisions["regex_v1"].disposition == "benchmark_only"
    assert decisions["regex_v1"].operational_evidence_present is False
    assert decisions["regex_v1"].reasons == ["missing_operational_evidence"]
    assert decisions["kiwi_morphology_v1"].disposition == "benchmark_only"
    assert decisions["kiwi_morphology_v1"].operational_evidence_present is False
    assert "missing_operational_evidence" in decisions["kiwi_morphology_v1"].reasons


def test_measured_operational_evidence_satisfies_presence_gate() -> None:
    matrix = CandidateMatrixReport.model_validate(
        {
            "candidates": [
                {
                    "candidate_name": "regex_v1",
                    "evidence_baseline": "lexical",
                    "role": "control",
                    "admission_status": "admitted",
                    "control": True,
                    "operational_evidence": {
                        "memory_peak_rss_mb": 10.0,
                        "memory_evidence_status": "measured",
                        "disk_size_mb": 1.0,
                        "disk_size_evidence_status": "measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "supported",
                            "fallback_behavior": "none",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "low",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "current_runtime_default",
                    },
                    "baseline": {
                        "name": "lexical",
                        "latency": {
                            "p50_ms": 1.0,
                            "p95_ms": 10.0,
                            "mean_ms": 1.0,
                            "min_ms": 1.0,
                            "max_ms": 10.0,
                        },
                        "quality": {
                            "overall": {
                                "recall_at_k": 0.72,
                                "mrr": 0.70,
                                "ndcg_at_k": 0.67,
                                "top_k": 5,
                                "queries_evaluated": 1,
                                "per_query": [],
                            },
                            "slices": {
                                "group": {
                                    "ko": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                    "en": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                    "mixed": {
                                        "recall_at_k": 0.60,
                                        "mrr": 0.60,
                                        "ndcg_at_k": 0.60,
                                        "top_k": 5,
                                        "queries_evaluated": 1,
                                        "per_query": [],
                                    },
                                },
                                "kind": {},
                            },
                            "thresholds": [
                                {
                                    "gate": "overall",
                                    "metric": "recall_at_k",
                                    "value": 0.72,
                                    "delta": 0.0,
                                    "verdict": "PASS",
                                    "threshold": 0.72,
                                    "warnings": [],
                                },
                                {
                                    "gate": "overall",
                                    "metric": "mrr",
                                    "value": 0.70,
                                    "delta": 0.0,
                                    "verdict": "PASS",
                                    "threshold": 0.70,
                                    "warnings": [],
                                },
                                {
                                    "gate": "overall",
                                    "metric": "ndcg_at_k",
                                    "value": 0.67,
                                    "delta": 0.0,
                                    "verdict": "PASS",
                                    "threshold": 0.67,
                                    "warnings": [],
                                },
                            ],
                        },
                        "queries": [],
                    },
                }
            ]
        }
    )

    decisions = {
        decision.candidate_name: decision
        for decision in evaluate_candidate_policy(matrix)
    }
    assert decisions["regex_v1"].operational_evidence_present is True
    assert decisions["regex_v1"].disposition == "promote"

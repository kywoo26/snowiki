from __future__ import annotations

from snowiki.bench.matrix import CANDIDATE_MATRIX, admitted_candidates, get_candidate
from snowiki.bench.models import CandidateMatrixReport
from snowiki.bench.verdict import evaluate_candidate_policy


def test_candidate_matrix_roadmap_roster_is_closed() -> None:
    assert [candidate.candidate_name for candidate in CANDIDATE_MATRIX] == [
        "regex_v1",
        "kiwi_morphology_v1",
        "kiwi_nouns_v1",
        "lindera_ko_v1",
    ]
    assert [candidate.evidence_baseline for candidate in CANDIDATE_MATRIX] == [
        "lexical",
        "bm25s_kiwi_full",
        "bm25s_kiwi_nouns",
        None,
    ]
    assert [candidate.control for candidate in CANDIDATE_MATRIX] == [
        True,
        False,
        False,
        False,
    ]


def test_lindera_remains_reference_candidate_until_zero_cost_admission_exists() -> None:
    lindera = get_candidate("lindera_ko_v1")

    assert lindera.admission_status == "not_admitted"
    assert lindera.evidence_baseline is None
    assert lindera.operational_evidence.zero_cost_admission is False
    assert lindera.operational_evidence.admission_reason == (
        "zero_cost_local_install_unavailable"
    )
    assert {candidate.candidate_name for candidate in admitted_candidates()} == {
        "regex_v1",
        "kiwi_morphology_v1",
        "kiwi_nouns_v1",
    }


def test_policy_governance_preserves_dual_identity_and_control_path() -> None:
    matrix = CandidateMatrixReport.model_validate(
        {
            "candidates": [
                candidate.model_dump(mode="json") for candidate in CANDIDATE_MATRIX
            ]
        }
    )

    decisions = {
        decision.candidate_name: decision
        for decision in evaluate_candidate_policy(matrix)
    }

    assert decisions["regex_v1"].evidence_baseline == "lexical"
    assert decisions["kiwi_morphology_v1"].evidence_baseline == "bm25s_kiwi_full"
    assert decisions["kiwi_nouns_v1"].evidence_baseline == "bm25s_kiwi_nouns"
    assert decisions["lindera_ko_v1"].evidence_baseline is None
    assert decisions["regex_v1"].disposition == "reject"
    assert decisions["kiwi_morphology_v1"].disposition == "reject"
    assert decisions["kiwi_nouns_v1"].disposition == "reject"
    assert decisions["lindera_ko_v1"].disposition == "reject"

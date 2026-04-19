from __future__ import annotations

from pathlib import Path


def test_step2_runtime_promotion_decision_stays_aligned_with_status_and_proof(
    repo_root: Path,
) -> None:
    decision = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "07-runtime-promotion-decision.md"
    ).read_text(encoding="utf-8")
    proof = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "tokenizer-benchmark-proof.md"
    ).read_text(encoding="utf-8")
    status = (repo_root / "docs" / "roadmap" / "STATUS.md").read_text(
        encoding="utf-8"
    )

    required_decision_markers = [
        "No tokenizer is promoted from the current candidate set",
        "There is no further mandatory residual work for the current candidate set",
        "Step 4 remains blocked",
        "Reopen Step 2 only under a new bounded hypothesis",
    ]
    for marker in required_decision_markers:
        assert marker in decision

    required_proof_markers = [
        "- **Local Closeout Outcome**: benchmark-only/no runtime promotion",
        "- **Promoted Tokenizer**: [NONE]",
        "- **Step 4 Unblocked**: [NO]",
        "-0.111111",
    ]
    for marker in required_proof_markers:
        assert marker in proof

    required_status_markers = [
        "Current candidate set closed. Fresh evidence confirms `benchmark-only/no runtime promotion`; no tokenizer is promoted.",
        "No further mandatory Step 2 residual work for the current candidate set.",
        "Reopen only under a new bounded tokenizer hypothesis or candidate-family program.",
        "Step 2 sparse branch still not proven on mixed-language benchmark.",
        "Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.",
    ]
    for marker in required_status_markers:
        assert marker in status

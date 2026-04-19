from __future__ import annotations

from pathlib import Path


def test_step2_reopening_contract_stays_aligned_with_status_and_decision(
    repo_root: Path,
) -> None:
    contract = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "08-reopening-contract.md"
    ).read_text(encoding="utf-8")
    decision = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "07-runtime-promotion-decision.md"
    ).read_text(encoding="utf-8")
    status = (repo_root / "docs" / "roadmap" / "STATUS.md").read_text(
        encoding="utf-8"
    )

    required_contract_markers = [
        "This reopening is a **new bounded evidence program**, not residual cleanup on the old line.",
        "A small, representative tokenizer-family comparison on a strengthened judged set",
        "Stable winner recommendation",
        "No stable winner",
        "Blocked-with-artifact",
        "runtime promotion",
        "Step 4 remains blocked",
    ]
    for marker in required_contract_markers:
        assert marker in contract

    required_decision_markers = [
        "No tokenizer is promoted from the current candidate set",
        "There is no further mandatory residual work for the current candidate set",
        "Reopen Step 2 only under a new bounded hypothesis",
    ]
    for marker in required_decision_markers:
        assert marker in decision

    required_status_markers = [
        "Strengthened benchmark substrate now shows no stable winner in the current lexical roster; Step 2 remains `benchmark-only/no runtime promotion`.",
        "Open one bounded external-family comparison lane under the frozen family admission packet.",
        "Step 2 sparse branch still not proven on mixed-language benchmark.",
        "Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.",
    ]
    for marker in required_status_markers:
        assert marker in status

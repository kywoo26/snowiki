from __future__ import annotations

from pathlib import Path


def test_step2_candidate_family_admission_stays_aligned_with_status_and_reopening_contract(
    repo_root: Path,
) -> None:
    admission = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "09-candidate-family-admission.md"
    ).read_text(encoding="utf-8")
    contract = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "08-reopening-contract.md"
    ).read_text(encoding="utf-8")
    status = (repo_root / "docs" / "roadmap" / "STATUS.md").read_text(
        encoding="utf-8"
    )

    required_admission_markers = [
        "regex_v1",
        "kiwi_morphology_v1",
        "Mecab family — admitted in principle",
        "Subword/HF family — admitted in principle",
        "Okt / social-text morphology — deferred",
        "Additional Kiwi variants — excluded",
        "This admission packet allows one bounded external-family lane to add the minimum runtime dependencies required for exactly one admitted-in-principle family representative.",
    ]
    for marker in required_admission_markers:
        assert marker in admission

    assert "Stable winner recommendation" in contract
    assert "No stable winner" in contract
    assert "Blocked-with-artifact" in contract

    required_status_markers = [
        "Strengthened benchmark substrate now shows no stable winner in the current lexical roster; Step 2 remains `benchmark-only/no runtime promotion`.",
        "Open one bounded external-family comparison lane under the frozen family admission packet.",
        "Step 2 sparse branch still not proven on mixed-language benchmark.",
        "Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.",
    ]
    for marker in required_status_markers:
        assert marker in status

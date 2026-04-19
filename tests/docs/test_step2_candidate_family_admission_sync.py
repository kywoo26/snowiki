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
        "This admission packet does **not** approve dependency changes by itself.",
    ]
    for marker in required_admission_markers:
        assert marker in admission

    assert "Stable winner recommendation" in contract
    assert "No stable winner" in contract
    assert "Blocked-with-artifact" in contract

    required_status_markers = [
        "Current candidate set remains closed at `benchmark-only/no runtime promotion`; the current reopening cycle is now canonically closed as blocked-with-artifact.",
        "Reopen execution only if one bounded benchmark-asset strengthening pass is explicitly approved under the frozen maturity bar.",
        "Step 2 sparse branch still not proven on mixed-language benchmark.",
        "Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.",
    ]
    for marker in required_status_markers:
        assert marker in status

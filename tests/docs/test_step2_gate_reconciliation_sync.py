from __future__ import annotations

from pathlib import Path


def _between(content: str, start: str, end: str) -> str:
    return content.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0]


def test_step2_gate_reconciliation_stays_aligned_with_proof_and_status(
    repo_root: Path,
) -> None:
    reconciliation = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "04-gate-reconciliation-and-fresh-evidence-program.md"
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
    step4 = (
        repo_root
        / "docs"
        / "roadmap"
        / "step4_hybrid-retrieval-preparation"
        / "roadmap.md"
    ).read_text(encoding="utf-8")

    decision = _between(
        reconciliation, "## Reconciliation decision", "## Fresh-evidence program decision"
    )
    fresh_program = _between(
        reconciliation,
        "## Fresh-evidence program decision",
        "## Canonical posture after this reconciliation",
    )

    required_reconciliation_markers = [
        "**Local Closeout Outcome**: `benchmark-only/no runtime promotion`",
        "**Promoted Tokenizer**: `[NONE]`",
        "**Step 4 Unblocked**: `[NO]`",
        "**Current runtime default tokenizer**: `regex_v1`",
        "historical PR/branch evidence does not override the current canonical owner surfaces",
        "the correct next mandatory work is a fresh Step 2 evidence program",
        "Step 4 runtime work remains blocked",
    ]
    for marker in required_reconciliation_markers:
        assert marker in reconciliation

    required_status_markers = [
        "Benchmark proof failed to reach promotion threshold; local outcome is `benchmark-only/no runtime promotion`.",
        "Launch the fresh evidence program for Step 2",
        "Step 2 sparse branch still not proven on mixed-language benchmark.",
        "Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.",
    ]
    for marker in required_status_markers:
        assert marker in status

    required_proof_markers = [
        "- **Local Closeout Outcome**: benchmark-only/no runtime promotion",
        "- **Promoted Tokenizer**: [NONE]",
        "- **Step 4 Unblocked**: [NO]",
        "memory/disk",
    ]
    for marker in required_proof_markers:
        assert marker in proof

    assert "Step 2 closed as **benchmark-only / no runtime promotion**" in step4
    assert "Step 4 must plan for a hybrid-ready future **without pretending the sparse branch is already proven**." in step4

    assert "current canonical owner surfaces on `main`" in decision
    assert "fresh evidence program" in fresh_program

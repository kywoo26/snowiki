from __future__ import annotations

from pathlib import Path


def _between(content: str, start: str, end: str) -> str:
    return content.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0]


def test_step2_gate_audit_stays_aligned_with_proof_and_status(repo_root: Path) -> None:
    audit = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "04-gate-audit-and-residual-program.md"
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

    audit_decision = _between(audit, "## Gate-audit decision", "## Residual-program decision")
    audit_residual = _between(
        audit, "## Residual-program decision", "## Canonical posture after this audit"
    )

    required_audit_markers = [
        "The current Step 2 blocker is legitimate, not stale",
        "**Local Closeout Outcome**: `benchmark-only/no runtime promotion`",
        "**Promoted Tokenizer**: `[NONE]`",
        "**Step 4 Unblocked**: `[NO]`",
        "**Current runtime default tokenizer**: `regex_v1`",
        "There is **no additional mandatory Step 2 residual substep** required to make the current closeout legitimate.",
        "Step 2 should be reopened only as a **new evidence program**",
        "Step 2 does **not** have a stale blocker; it has a legitimate no-promotion decision.",
        "Step 4 remains blocked because the sparse branch is still not proven.",
    ]
    for marker in required_audit_markers:
        assert marker in audit

    required_proof_markers = [
        "- **Local Closeout Outcome**: benchmark-only/no runtime promotion",
        "- **Promoted Tokenizer**: [NONE]",
        "- **Step 4 Unblocked**: [NO]",
        "-0.027778",
        "Operational Status**: PASS (memory and disk usage are now measured)",
    ]
    for marker in required_proof_markers:
        assert marker in proof

    assert "No further mandatory Step 2 residual work for the current candidate set." in status
    assert "Reopen only under a new bounded tokenizer hypothesis or candidate-family program." in status
    assert "Step 2 sparse branch still not proven on mixed-language benchmark." in status
    assert "Step 2 still not proven, Step 4 remains blocked." in status

    assert "not stale" in audit_decision
    assert "no additional mandatory step 2 residual substep" in audit_residual.casefold()

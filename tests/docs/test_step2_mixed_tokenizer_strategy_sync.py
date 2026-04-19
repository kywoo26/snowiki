from __future__ import annotations

from pathlib import Path


def test_step2_mixed_tokenizer_strategy_stays_aligned_with_proof_and_gate(
    repo_root: Path,
) -> None:
    strategy = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "05-mixed-language-tokenizer-strategy.md"
    ).read_text(encoding="utf-8")
    proof = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "tokenizer-benchmark-proof.md"
    ).read_text(encoding="utf-8")
    reconciliation = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "04-gate-reconciliation-and-fresh-evidence-program.md"
    ).read_text(encoding="utf-8")
    step4 = (
        repo_root
        / "docs"
        / "roadmap"
        / "step4_hybrid-retrieval-preparation"
        / "roadmap.md"
    ).read_text(encoding="utf-8")

    required_strategy_markers = [
        "The current `BilingualTokenizer` is not actually a mixed-language tokenizer",
        "The benchmark BM25 path fuses token streams naïvely",
        "The current proof failure fits the code design",
        "script-aware freeze -> Korean morphology -> lexical merge",
        "Step 2 still cannot reopen on tokenizer strategy alone.",
        "This note does not unblock Step 4.",
    ]
    for marker in required_strategy_markers:
        assert marker in strategy

    required_proof_markers = [
        "0.666667",
        "0.712121",
        "- **Promoted Tokenizer**: [NONE]",
        "- **Step 4 Unblocked**: [NO]",
    ]
    for marker in required_proof_markers:
        assert marker in proof

    assert "fresh evidence program" in reconciliation
    assert "Step 4 runtime implementation may not be treated as unblocked" in reconciliation
    assert "Step 2 closed as **benchmark-only / no runtime promotion**" in step4

from __future__ import annotations

from pathlib import Path


def _between(content: str, start: str, end: str) -> str:
    return content.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0]


def test_step2_closeout_contract_is_normalized(repo_root: Path) -> None:
    plan_path = repo_root / ".sisyphus" / "plans" / "tokenizer-benchmark-proof-closeout.md"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else None
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

    proof_info = _between(proof, "## Informational Evidence", "## Operational Evidence")
    proof_gate = _between(proof, "## Step 4 Gate Decision", "---")
    status_step2 = _between(
        status,
        "- [x] **Step 2: Korean tokenizer deep-dive**",
        "- [x] **Step 3: Wiki skill contract draft**",
    )
    status_step4 = _between(
        status,
        "- [x] **Step 4: Hybrid fusion deep-dive**",
        "- [x] **Step 5: Rust core migration path**",
    )

    plan_task6 = ""
    if plan is not None:
        plan_must_have = _between(plan, "### Must Have", "### Must NOT Have")
        plan_task3 = _between(
            plan,
            "3. Run the local preset sweep on isolated seeded roots",
            "4. Derive the Step 2 local decision package",
        )
        plan_task4 = _between(
            plan,
            "4. Derive the Step 2 local decision package",
            "5. Reproduce the blocking preset via GitHub manual benchmark workflow",
        )
        plan_task6 = _between(
            plan,
            "6. Record the closeout decision and gate Step 4 explicitly",
            "## Final Verification Wave",
        )

        required_plan_markers = [
            "Blocking preset: `retrieval`",
            "Informational local guardrails: `core` and `full`",
        ]
        for marker in required_plan_markers:
            assert marker in plan_must_have

        assert "`benchmark-only/no runtime promotion`" in plan_task4

        required_task3_markers = [
            "Treat `retrieval` as the blocking preset; `core`/`full` are informational guardrails.",
            "Preserve the real `full` failure evidence",
            "`kiwi_nouns_v1` overall recall `0.716667 < 0.72`",
            "`uv run snowiki benchmark --preset core --output reports/step2-proof/core.json` is executed (informational).",
            "`uv run snowiki benchmark --preset retrieval --output reports/step2-proof/retrieval.json` exits 0 (blocking).",
            "`uv run snowiki benchmark --preset full --output reports/step2-proof/full.json` is executed (informational; may exit non-zero due to `kiwi_nouns_v1` recall).",
        ]
        for marker in required_task3_markers:
            assert marker in plan_task3

        for forbidden_claim in [
            "`uv run snowiki benchmark --preset core --output reports/step2-proof/core.json` exits 0.",
            "`uv run snowiki benchmark --preset full --output reports/step2-proof/full.json` exits 0.",
        ]:
            assert forbidden_claim not in plan_task3

        assert "Populate `docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md`" in plan_task6
        assert "Do not mark Step 4 unblocked without both local blocking evidence and GitHub reproduction parity." in plan_task6
        assert "Step 2 still not proven, Step 4 remains blocked" in plan_task6

    required_proof_markers = [
        "- **Benchmark Presets**: `retrieval` (blocking), `core` (informational), `full` (informational)",
        "The `core` and `full` presets provide additional context but do not block the gate.",
        "The redesigned mixed tokenizer path causes both Kiwi candidates to fail the `core` preset overall MRR threshold (`0.643519 < 0.70`).",
        "- **Local Closeout Outcome**: benchmark-only/no runtime promotion",
        "- **Promoted Tokenizer**: [NONE]",
        "- **Step 4 Unblocked**: [NO]",
    ]
    for marker in required_proof_markers:
        assert marker in proof

    for forbidden_claim in [
        "- **Local Closeout Outcome**: promote candidate",
        "- **Step 4 Unblocked**: [YES]",
    ]:
        assert forbidden_claim not in proof_gate

    assert "It will be populated once benchmark runs are complete." not in proof

    required_status_markers = [
        "Current candidate set closed. Fresh evidence confirms `benchmark-only/no runtime promotion`; no tokenizer is promoted.",
        "No further mandatory Step 2 residual work for the current candidate set.",
        "Reopen only under a new bounded tokenizer hypothesis or candidate-family program.",
        "Step 2 sparse branch still not proven on mixed-language benchmark.",
        "Step 2 must be proven first.",
        "Step 2 still not proven, Step 4 remains blocked.",
    ]
    for marker in required_status_markers:
        assert marker in status

    assert "Step 4 unblocked" not in status_step4
    assert "Step 2 sparse branch proven" not in status_step2

    if plan is not None:
        assert (
            "-0.111111" in proof and "regress the mixed slice" in proof
        ) or (
            "docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md"
            in plan_task6
            and "kiwi_nouns_v1" in proof_info
            and "0.643519 < 0.70" in proof_info
        )
    else:
        assert "-0.111111" in proof and "regress the mixed slice" in proof

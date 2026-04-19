from __future__ import annotations

from pathlib import Path


def test_step2_operational_evidence_note_stays_aligned_with_policy(
    repo_root: Path,
) -> None:
    note = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "06-operational-evidence-instrumentation.md"
    ).read_text(encoding="utf-8")
    proof = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "tokenizer-benchmark-proof.md"
    ).read_text(encoding="utf-8")
    matrix = (
        repo_root / "src" / "snowiki" / "bench" / "matrix.py"
    ).read_text(encoding="utf-8")
    verdict = (
        repo_root / "src" / "snowiki" / "bench" / "verdict.py"
    ).read_text(encoding="utf-8")
    benchmark_readme = (
        repo_root / "benchmarks" / "README.md"
    ).read_text(encoding="utf-8")

    required_note_markers = [
        "Operational evidence must become a measured report payload, not a static matrix declaration",
        "Preferred measurement path: stdlib-first instrumentation",
        "Preferred seam placement",
        "This note does not unblock Step 2.",
    ]
    for marker in required_note_markers:
        assert marker in note

    assert 'memory_evidence_status="not_measured"' in matrix
    assert 'disk_size_evidence_status="not_measured"' in matrix
    assert 'evidence.memory_evidence_status == "measured"' in verdict
    assert 'evidence.disk_size_evidence_status == "measured"' in verdict
    assert (
        "Tokenizer-promotion operational evidence (memory/disk) is measured separately"
        in benchmark_readme
    )
    assert "Operational Status**: PASS (memory and disk usage are now measured)" in proof

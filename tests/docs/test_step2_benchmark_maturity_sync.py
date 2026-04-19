from __future__ import annotations

from pathlib import Path


def test_step2_benchmark_maturity_packet_stays_aligned_with_status_and_contract(
    repo_root: Path,
) -> None:
    maturity = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "10-benchmark-maturity-bar.md"
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

    required_maturity_markers = [
        'target total judged queries: **90–120**',
        'at least 8 judged queries per language × intent cell',
        'require **at least 20%** of all judged queries',
        'Current assets are insufficient',
        'Benchmark-asset changes are mandatory before the decisive family comparison',
        'blocked-with-artifact',
    ]
    for marker in required_maturity_markers:
        assert marker in maturity

    assert 'Stable winner recommendation' in contract
    assert 'No stable winner' in contract

    required_status_markers = [
        'Current candidate set remains closed at `benchmark-only/no runtime promotion`; bounded reopening is active and the benchmark maturity bar is now frozen.',
        'Benchmark asset strengthening is now the mandatory next lane before any decisive family comparison.',
        'Step 2 sparse branch still not proven on mixed-language benchmark.',
        'Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.',
    ]
    for marker in required_status_markers:
        assert marker in status

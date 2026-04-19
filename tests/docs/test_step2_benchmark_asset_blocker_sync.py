from __future__ import annotations

from pathlib import Path


def test_step2_benchmark_asset_blocker_stays_aligned_with_status_and_maturity_bar(
    repo_root: Path,
) -> None:
    blocker = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "11-benchmark-asset-strengthening-blocker.md"
    ).read_text(encoding="utf-8")
    maturity = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "10-benchmark-maturity-bar.md"
    ).read_text(encoding="utf-8")
    status = (repo_root / "docs" / "roadmap" / "STATUS.md").read_text(
        encoding="utf-8"
    )

    required_blocker_markers = [
        'benchmark assets are inventory-sensitive canonical assets',
        'increase total judged queries from the current 60 to at least 90',
        'ambiguous intent',
        'hard negatives',
        'identifier/path/code-heavy cases',
        'explicit no-answer cases',
        'Step 2 reopening ends as **blocked-with-artifact**',
    ]
    for marker in required_blocker_markers:
        assert marker in blocker

    assert 'Current assets are insufficient' in maturity
    assert 'Benchmark-asset changes are mandatory before the decisive family comparison' in maturity

    required_status_markers = [
        'Current candidate set remains closed at `benchmark-only/no runtime promotion`; bounded reopening is now blocked pending explicit approval for inventory-sensitive benchmark asset strengthening.',
        'Obtain approval for one bounded benchmark-asset strengthening pass or close the reopening as blocked-with-artifact.',
        'Step 2 sparse branch still not proven on mixed-language benchmark.',
        'Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.',
    ]
    for marker in required_status_markers:
        assert marker in status

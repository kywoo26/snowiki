from __future__ import annotations

from pathlib import Path


def test_step2_reopening_terminal_closeout_stays_aligned_with_status(
    repo_root: Path,
) -> None:
    recommendation = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "11-runtime-promotion-recommendation.md"
    ).read_text(encoding="utf-8")
    blocker = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "11-benchmark-asset-strengthening-blocker.md"
    ).read_text(encoding="utf-8")
    status = (repo_root / "docs" / "roadmap" / "STATUS.md").read_text(encoding="utf-8")
    admission = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "09-candidate-family-admission.md"
    ).read_text(encoding="utf-8")

    required_recommendation_markers = [
        'Current reopening outcome: blocked-with-artifact',
        'No runtime-promotion recommendation is issued from this reopening cycle',
        'The current candidate set remains canonically closed',
        'permission for **one bounded benchmark-asset strengthening pass**',
        'Step 4 remains blocked',
    ]
    for marker in required_recommendation_markers:
        assert marker in recommendation

    required_status_markers = [
        'Current candidate set remains closed at `benchmark-only/no runtime promotion`; the current reopening cycle is now canonically closed as blocked-with-artifact.',
        'Reopen execution only if one bounded benchmark-asset strengthening pass is explicitly approved under the frozen maturity bar.',
        'Step 2 sparse branch still not proven on mixed-language benchmark.',
        'Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.',
    ]
    for marker in required_status_markers:
        assert marker in status

    assert 'benchmark assets are inventory-sensitive canonical assets' in blocker.lower()
    assert 'python-mecab-ko' in admission
    assert 'BertWordPieceTokenizer' in admission

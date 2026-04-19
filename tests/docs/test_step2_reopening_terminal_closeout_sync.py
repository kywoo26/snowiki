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
        'Current rerun outcome: no stable winner in the strengthened current roster',
        'No runtime-promotion recommendation is issued from this reopening cycle',
        'The current candidate set remains canonically closed',
        'one bounded external-family comparison lane',
        'Step 4 remains blocked',
    ]
    for marker in required_recommendation_markers:
        assert marker in recommendation

    required_status_markers = [
        'Strengthened benchmark substrate now shows no stable winner in the current lexical roster; Step 2 remains `benchmark-only/no runtime promotion`.',
        'Open one bounded external-family comparison lane under the frozen family admission packet.',
        'Step 2 sparse branch still not proven on mixed-language benchmark.',
        'Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.',
    ]
    for marker in required_status_markers:
        assert marker in status

    assert 'benchmark assets are inventory-sensitive canonical assets' in blocker.lower()
    assert 'python-mecab-ko' in admission
    assert 'BertWordPieceTokenizer' in admission

from __future__ import annotations

from pathlib import Path


def test_step2_external_family_blocker_stays_aligned_with_status_and_admission_packet(
    repo_root: Path,
) -> None:
    blocker = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "12-external-family-feasibility-blocker.md"
    ).read_text(encoding="utf-8")
    admission = (
        repo_root
        / "docs"
        / "roadmap"
        / "step2_korean-tokenizer-selection"
        / "09-candidate-family-admission.md"
    ).read_text(encoding="utf-8")
    status = (repo_root / "docs" / "roadmap" / "STATUS.md").read_text(encoding="utf-8")
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")

    required_blocker_markers = [
        'No bounded external family lane can proceed yet',
        '`python-mecab-ko`',
        '`huggingface/tokenizers`',
        'Dependency additions are still not autonomous',
        'permission to add **one** new runtime dependency',
    ]
    for marker in required_blocker_markers:
        assert marker in blocker

    assert '`python-mecab-ko`' in admission
    assert '`huggingface/tokenizers`' in admission
    assert 'kiwipiepy' in pyproject
    assert 'python-mecab-ko' not in pyproject
    assert 'tokenizers' not in pyproject

    required_status_markers = [
        'Strengthened benchmark substrate shows no stable winner in the current lexical roster; the next external-family lane is blocked pending dependency approval.',
        'Reopen execution only if one admitted-in-principle external family is explicitly approved for runtime dependency addition.',
        'Step 2 sparse branch still not proven on mixed-language benchmark.',
        'Step 2 must be proven first. Step 2 still not proven, Step 4 remains blocked.',
    ]
    for marker in required_status_markers:
        assert marker in status

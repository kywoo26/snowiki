from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.fileback.models import FilebackProposal
from snowiki.fileback.proposal import (
    build_proposal_id,
    build_target,
    extract_fileback_proposal,
    resolve_preview_root,
    validate_proposal_schema,
)


def test_build_target_and_proposal_id_are_deterministic() -> None:
    assert build_target("What did we ship?") == {
        "title": "What did we ship?",
        "slug": "what-did-we-ship",
        "compiled_path": "compiled/questions/what-did-we-ship.md",
    }
    first = build_proposal_id(
        question="What did we ship?",
        answer_markdown="Answer",
        summary="Summary",
        requested_paths=["compiled/summaries/source.md"],
    )
    second = build_proposal_id(
        question="What did we ship?",
        answer_markdown="Answer",
        summary="Summary",
        requested_paths=["compiled/summaries/source.md"],
    )

    assert first == second
    assert first.startswith("fileback-proposal-")


def test_resolve_preview_root_uses_env_without_creating_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "missing-root"
    monkeypatch.setenv("SNOWIKI_ROOT", str(target))

    assert resolve_preview_root(None) == target.resolve()
    assert not target.exists()


def test_extract_fileback_proposal_accepts_review_envelope() -> None:
    proposal = _proposal()

    assert extract_fileback_proposal(
        {"ok": True, "command": "fileback preview", "result": {"root": "/tmp/wiki", "proposal": proposal}}
    ) == proposal


def test_validate_proposal_schema_rejects_bad_id() -> None:
    proposal = _proposal()
    proposal["proposal_id"] = "../evil"

    with pytest.raises(ValueError, match="proposal_id must match"):
        validate_proposal_schema(proposal)


def _proposal() -> FilebackProposal:
    return {
        "proposal_id": "fileback-proposal-0123456789abcdef",
        "proposal_version": 1,
        "created_at": "2026-04-25T09:00:00Z",
        "target": {
            "title": "What did we ship?",
            "slug": "what-did-we-ship",
            "compiled_path": "compiled/questions/what-did-we-ship.md",
        },
        "draft": {
            "question": "What did we ship?",
            "answer_markdown": "Answer",
            "summary": "Summary",
        },
        "evidence": {
            "requested_paths": ["compiled/summaries/source.md"],
            "resolved_paths": {"compiled": [], "normalized": [], "raw": []},
            "supporting_record_ids": [],
            "supporting_raw_refs": [],
        },
        "derivation": {},
        "apply_plan": {
            "source_type": "manual-question",
            "record_type": "question",
            "record_id": "question-what-did-we-ship-abc123",
            "normalized_path": "normalized/manual-question/2026/04/25/question.json",
        },
    }

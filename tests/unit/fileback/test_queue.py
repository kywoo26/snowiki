from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowiki.fileback.models import FilebackProposal
from snowiki.fileback.queue import (
    build_queue_envelope,
    coerce_queued_fileback_proposal,
    list_queued_fileback_proposals,
    pending_proposal_path,
    queue_fileback_proposal,
)


def test_queue_fileback_proposal_writes_pending_envelope(tmp_path: Path) -> None:
    proposal = _proposal()

    result = queue_fileback_proposal(
        tmp_path,
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )

    assert result == {
        "queue_version": 1,
        "proposal_id": "fileback-proposal-0123456789abcdef",
        "queued_at": "2026-04-25T09:00:00Z",
        "status": "pending",
        "decision": "queued",
        "impact": "medium",
        "requires_human_review": True,
        "reasons": ["auto_apply_not_implemented"],
        "proposal_path": "queue/proposals/pending/fileback-proposal-0123456789abcdef.json",
    }

    payload = json.loads((tmp_path / result["proposal_path"]).read_text(encoding="utf-8"))
    assert payload == build_queue_envelope(
        tmp_path.resolve(),
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )


def test_list_queued_fileback_proposals_returns_pending_metadata(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(
        tmp_path,
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )

    assert list_queued_fileback_proposals(tmp_path) == [
        {
            "proposal_id": "fileback-proposal-0123456789abcdef",
            "queued_at": "2026-04-25T09:00:00Z",
            "status": "pending",
            "decision": "queued",
            "impact": "medium",
            "requires_human_review": True,
            "reasons": ["auto_apply_not_implemented"],
            "proposal_path": "queue/proposals/pending/fileback-proposal-0123456789abcdef.json",
            "target": proposal["target"],
            "summary": "Summary",
        }
    ]


def test_pending_proposal_path_rejects_unsafe_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="proposal_id must match"):
        pending_proposal_path(tmp_path, "../evil")


def test_coerce_queued_fileback_proposal_rejects_non_pending_status() -> None:
    envelope = build_queue_envelope(
        Path("/tmp/wiki"),
        _proposal(),
        queued_at="2026-04-25T09:00:00Z",
    )
    envelope["status"] = "applied"

    with pytest.raises(ValueError, match="status must be pending"):
        coerce_queued_fileback_proposal(envelope)


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
            "raw_note_path": "raw/manual/questions/2026/04/25/what-did-we-ship.md",
            "normalized_path": "normalized/manual-question/2026/04/25/question.json",
            "proposed_raw_note_body": "---\nsource_type: manual-question\n---\n",
            "proposed_normalized_record_payload": {"id": "question-what-did-we-ship-abc123"},
            "rebuild_required": True,
        },
    }

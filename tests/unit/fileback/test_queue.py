from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from snowiki.fileback.models import FilebackProposal
from snowiki.fileback.queue.codec import (
    build_queue_envelope,
    coerce_queued_fileback_proposal,
)
from snowiki.fileback.queue.lifecycle import (
    apply_queued_fileback_proposal,
    list_queued_fileback_proposals,
    queue_fileback_proposal,
    reject_queued_fileback_proposal,
    show_queued_fileback_proposal,
)
from snowiki.fileback.queue.store import (
    find_existing_queue_state_paths,
    pending_proposal_path,
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
        "proposal_path": "queue/proposals/pending/fileback-proposal-0123456789abcdef.json",
    }

    payload = json.loads((tmp_path / result["proposal_path"]).read_text(encoding="utf-8"))
    assert payload == build_queue_envelope(
        tmp_path.resolve(),
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )


def test_queue_fileback_proposal_rejects_duplicate_state(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    assert find_existing_queue_state_paths(tmp_path.resolve(), proposal["proposal_id"])
    with pytest.raises(ValueError, match="already exists"):
        queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T10:00:00Z")


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
            "proposal_path": "queue/proposals/pending/fileback-proposal-0123456789abcdef.json",
            "target": proposal["target"],
            "summary": "Summary",
            "evidence_requested_paths": ["compiled/summaries/source.md"],
        }
    ]


def test_pending_proposal_path_rejects_unsafe_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="proposal_id must match"):
        pending_proposal_path(tmp_path, "../evil")


def test_show_queued_fileback_proposal_hides_payload_by_default(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    shown = show_queued_fileback_proposal(tmp_path, proposal["proposal_id"])
    verbose = show_queued_fileback_proposal(tmp_path, proposal["proposal_id"], verbose=True)

    assert "proposal" not in shown
    assert verbose["proposal"] == proposal


def test_show_queued_fileback_proposal_rejects_symlinked_queue_file(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    outside = tmp_path / "outside.json"
    outside.write_text(
        json.dumps(build_queue_envelope(tmp_path.resolve(), proposal)),
        encoding="utf-8",
    )
    target = tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)

    with pytest.raises(ValueError, match="non-symlink regular file"):
        show_queued_fileback_proposal(tmp_path, proposal["proposal_id"])


def test_show_queued_fileback_proposal_rejects_filename_envelope_mismatch(
    tmp_path: Path,
) -> None:
    requested = _proposal("fileback-proposal-0000000000000001")
    embedded = _proposal("fileback-proposal-0000000000000002")
    target = tmp_path / "queue" / "proposals" / "pending" / f"{requested['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(build_queue_envelope(tmp_path.resolve(), embedded)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requested proposal|queue filename"):
        show_queued_fileback_proposal(tmp_path, requested["proposal_id"])


def test_list_queued_fileback_proposals_rejects_status_mismatch(tmp_path: Path) -> None:
    proposal = _proposal()
    envelope = build_queue_envelope(tmp_path.resolve(), proposal)
    envelope["status"] = "rejected"
    target = tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(ValueError, match="status must be pending"):
        list_queued_fileback_proposals(tmp_path)


def test_show_queued_fileback_proposal_rejects_root_mismatch(tmp_path: Path) -> None:
    proposal = _proposal()
    envelope = build_queue_envelope(tmp_path.resolve(), proposal)
    envelope["root"] = (tmp_path / "other-root").as_posix()
    target = tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(ValueError, match="queue root"):
        show_queued_fileback_proposal(tmp_path, proposal["proposal_id"])


def test_reject_queued_fileback_proposal_deletes_pending_without_archive(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    result = reject_queued_fileback_proposal(
        tmp_path,
        proposal["proposal_id"],
        reason="Needs stronger provenance.",
    )

    assert not pending_proposal_path(tmp_path.resolve(), proposal["proposal_id"]).exists()
    assert not (tmp_path / result["proposal_path"]).exists()
    assert result["status"] == "rejected"
    assert result["transition_reason"] == "Needs stronger provenance."
    assert result["result"] == {"ok": True, "reason": "Needs stronger provenance."}


def test_apply_queued_fileback_proposal_deletes_pending_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    def apply_fileback_proposal(root: Path, reviewed_payload: dict[str, Any]) -> dict[str, Any]:
        assert root == tmp_path.resolve()
        assert reviewed_payload["result"]["proposal"] == proposal
        return {"proposal_id": proposal["proposal_id"], "normalized_path": "normalized/x.json"}

    monkeypatch.setattr(
        "snowiki.fileback.apply.apply_fileback_proposal",
        apply_fileback_proposal,
    )

    result = apply_queued_fileback_proposal(tmp_path, proposal["proposal_id"])

    assert not pending_proposal_path(tmp_path.resolve(), proposal["proposal_id"]).exists()
    assert result["status"] == "applied"
    assert result["result"] == {
        "ok": True,
        "proposal_id": proposal["proposal_id"],
        "normalized_path": "normalized/x.json",
    }


def test_apply_queued_fileback_proposal_keeps_pending_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    def apply_fileback_proposal(root: Path, reviewed_payload: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("apply failed")

    monkeypatch.setattr(
        "snowiki.fileback.apply.apply_fileback_proposal",
        apply_fileback_proposal,
    )

    with pytest.raises(ValueError, match="apply failed"):
        apply_queued_fileback_proposal(tmp_path, proposal["proposal_id"])

    assert pending_proposal_path(tmp_path.resolve(), proposal["proposal_id"]).exists()


def test_coerce_queued_fileback_proposal_rejects_unknown_status() -> None:
    envelope = build_queue_envelope(
        Path("/tmp/wiki"),
        _proposal(),
        queued_at="2026-04-25T09:00:00Z",
    )
    envelope["status"] = "unknown"

    with pytest.raises(ValueError, match="status must be pending"):
        coerce_queued_fileback_proposal(envelope)


def _proposal(
    proposal_id: str = "fileback-proposal-0123456789abcdef",
) -> FilebackProposal:
    return {
        "proposal_id": proposal_id,
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

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from tests.helpers.markdown_ingest import write_markdown_source

from snowiki.cli.main import app


def _workspace_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if path.is_file()
    }


def _build_fileback_workspace(tmp_path: Path) -> Path:
    runner = CliRunner()
    source_path = write_markdown_source(tmp_path)
    ingest = runner.invoke(
        app,
        ["ingest", str(source_path), "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert rebuild.exit_code == 0, rebuild.output

    summary_path = next((tmp_path / "compiled" / "summaries").glob("*.md"))
    return summary_path.relative_to(tmp_path)


def _preview_payload(
    tmp_path: Path,
    evidence_path: Path,
    *,
    answer_markdown: str = "Initial answer that should be reviewed.",
    summary: str = "Initial fileback summary.",
) -> dict[str, Any]:
    runner = CliRunner()
    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What did we ship?",
            "--answer-markdown",
            answer_markdown,
            "--summary",
            summary,
            "--evidence-path",
            evidence_path.as_posix(),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert preview.exit_code == 0, preview.output
    return json.loads(preview.output)


def _write_payload_file(tmp_path: Path, payload: dict[str, Any], *, name: str) -> Path:
    proposal_file = tmp_path / name
    proposal_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return proposal_file


def _invoke_apply(tmp_path: Path, proposal_file: Path):
    runner = CliRunner()
    return runner.invoke(
        app,
        [
            "fileback",
            "apply",
            "--proposal-file",
            str(proposal_file),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )


def test_fileback_preview_is_reviewable_and_non_mutating(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    before = _workspace_snapshot(tmp_path)

    result = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What did we ship?",
            "--answer-markdown",
            "We shipped the first reviewable fileback flow.",
            "--summary",
            "Reviewed answer for the shipped fileback flow.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert _workspace_snapshot(tmp_path) == before

    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "fileback preview"
    proposal = payload["result"]["proposal"]
    assert proposal["target"] == {
        "title": "What did we ship?",
        "slug": "what-did-we-ship",
        "compiled_path": "compiled/questions/what-did-we-ship.md",
    }
    assert proposal["draft"] == {
        "question": "What did we ship?",
        "answer_markdown": "We shipped the first reviewable fileback flow.",
        "summary": "Reviewed answer for the shipped fileback flow.",
    }
    assert proposal["proposal_version"] == 1
    assert proposal["evidence"]["requested_paths"] == [evidence_path.as_posix()]
    assert proposal["evidence"]["resolved_paths"]["compiled"] == [
        evidence_path.as_posix()
    ]
    assert proposal["evidence"]["supporting_record_ids"]
    assert proposal["derivation"]["kind"] == "derived"
    assert proposal["derivation"]["synthesized"] is True
    assert proposal["apply_plan"]["source_type"] == "manual-question"
    assert proposal["apply_plan"]["record_type"] == "question"
    assert proposal["apply_plan"]["raw_note_path"].startswith("raw/manual/questions/")
    assert "what-did-we-ship--" in proposal["apply_plan"]["raw_note_path"]
    assert proposal["apply_plan"]["normalized_path"].startswith(
        "normalized/manual-question/"
    )
    assert "## Answer" in proposal["apply_plan"]["proposed_raw_note_body"]
    assert (
        proposal["apply_plan"]["proposed_normalized_record_payload"]["source_type"]
        == "manual-question"
    )
    assert (
        proposal["apply_plan"]["proposed_normalized_record_payload"]["record_type"]
        == "question"
    )
    assert payload["result"]["proposed_write"] == {
        "raw_note_body": proposal["apply_plan"]["proposed_raw_note_body"],
        "normalized_record_payload": proposal["apply_plan"][
            "proposed_normalized_record_payload"
        ],
    }
    assert proposal["apply_plan"]["rebuild_required"] is True


def test_fileback_preview_queue_persists_pending_proposal_without_applying(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    before = _workspace_snapshot(tmp_path)

    result = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should be queued?",
            "--answer-markdown",
            "Queue this answer for later review.",
            "--summary",
            "Queued fileback answer.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    proposal = payload["result"]["proposal"]
    queue_result = payload["result"]["queue"]
    assert queue_result["decision"] == "queued"
    assert queue_result["requires_human_review"] is True
    assert queue_result["proposal_id"] == proposal["proposal_id"]
    assert queue_result["proposal_path"].startswith("queue/proposals/pending/")

    changed = _workspace_snapshot(tmp_path)
    expected = dict(before)
    queue_path = queue_result["proposal_path"]
    expected[queue_path] = changed[queue_path]
    assert changed == expected

    queued_payload = json.loads((tmp_path / queue_path).read_text(encoding="utf-8"))
    assert queued_payload["status"] == "pending"
    assert queued_payload["proposal"] == proposal
    assert queued_payload["root"] == tmp_path.resolve().as_posix()
    assert not (tmp_path / proposal["apply_plan"]["raw_note_path"]).exists()
    assert not (tmp_path / proposal["apply_plan"]["normalized_path"]).exists()


def test_fileback_queue_list_reports_pending_proposals(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should be listed?",
            "--answer-markdown",
            "List this queued answer.",
            "--summary",
            "Listed fileback answer.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert preview.exit_code == 0, preview.output
    preview_payload = json.loads(preview.output)
    proposal = preview_payload["result"]["proposal"]

    listed = runner.invoke(
        app,
        ["fileback", "queue", "list", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert listed.exit_code == 0, listed.output
    payload = json.loads(listed.output)
    assert payload["ok"] is True
    assert payload["command"] == "fileback queue list"
    assert payload["result"]["root"] == tmp_path.resolve().as_posix()
    assert payload["result"]["status"] == "pending"
    assert payload["result"]["proposals"] == [
        {
            "proposal_id": proposal["proposal_id"],
            "queued_at": payload["result"]["proposals"][0]["queued_at"],
            "status": "pending",
            "decision": "queued",
            "impact": "medium",
            "requires_human_review": True,
            "reasons": ["requires_human_review"],
            "proposal_path": preview_payload["result"]["queue"]["proposal_path"],
            "target": proposal["target"],
            "summary": "Listed fileback answer.",
            "evidence_requested_paths": [evidence_path.as_posix()],
        }
    ]


def test_fileback_queue_show_reports_metadata_and_verbose_payload(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should be shown?",
            "--answer-markdown",
            "Show this queued answer.",
            "--summary",
            "Shown fileback answer.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert preview.exit_code == 0, preview.output
    preview_payload = json.loads(preview.output)
    proposal = preview_payload["result"]["proposal"]

    shown = runner.invoke(
        app,
        ["fileback", "queue", "show", proposal["proposal_id"], "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert shown.exit_code == 0, shown.output
    shown_payload = json.loads(shown.output)
    assert shown_payload["result"]["proposal_id"] == proposal["proposal_id"]
    assert shown_payload["result"]["status"] == "pending"
    assert shown_payload["result"]["target"] == proposal["target"]
    assert shown_payload["result"]["evidence_requested_paths"] == [evidence_path.as_posix()]
    assert "proposal" not in shown_payload["result"]

    verbose = runner.invoke(
        app,
        [
            "fileback",
            "queue",
            "show",
            proposal["proposal_id"],
            "--verbose",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert verbose.exit_code == 0, verbose.output
    verbose_payload = json.loads(verbose.output)
    assert verbose_payload["result"]["proposal"] == proposal


def test_fileback_queue_apply_archives_applied_proposal(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should queue apply?",
            "--answer-markdown",
            "Queue apply should persist this answer.",
            "--summary",
            "Queue apply summary.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert preview.exit_code == 0, preview.output
    proposal = json.loads(preview.output)["result"]["proposal"]

    applied = runner.invoke(
        app,
        ["fileback", "queue", "apply", proposal["proposal_id"], "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert applied.exit_code == 0, applied.output
    payload = json.loads(applied.output)
    result = payload["result"]
    assert payload["command"] == "fileback queue apply"
    assert result["status"] == "applied"
    assert result["previous_status"] == "pending"
    assert result["result"]["ok"] is True
    assert not (tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json").exists()
    assert (tmp_path / result["proposal_path"]).exists()
    assert (tmp_path / proposal["apply_plan"]["raw_note_path"]).exists()
    assert (tmp_path / proposal["apply_plan"]["normalized_path"]).exists()


def test_fileback_queue_reject_and_list_status_filter(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should be rejected?",
            "--answer-markdown",
            "Reject this queued answer.",
            "--summary",
            "Rejected fileback answer.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert preview.exit_code == 0, preview.output
    proposal = json.loads(preview.output)["result"]["proposal"]

    rejected = runner.invoke(
        app,
        [
            "fileback",
            "queue",
            "reject",
            proposal["proposal_id"],
            "--reason",
            "Needs stronger evidence.",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert rejected.exit_code == 0, rejected.output
    rejected_payload = json.loads(rejected.output)
    assert rejected_payload["result"]["status"] == "rejected"
    assert rejected_payload["result"]["transition_reason"] == "Needs stronger evidence."

    pending = runner.invoke(
        app,
        ["fileback", "queue", "list", "--status", "pending", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert pending.exit_code == 0, pending.output
    assert json.loads(pending.output)["result"]["proposals"] == []

    listed = runner.invoke(
        app,
        ["fileback", "queue", "list", "--status", "rejected", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert listed.exit_code == 0, listed.output
    listed_payload = json.loads(listed.output)
    assert listed_payload["result"]["proposals"][0]["proposal_id"] == proposal["proposal_id"]
    assert listed_payload["result"]["proposals"][0]["status"] == "rejected"


def test_fileback_queue_prune_is_dry_run_then_delete(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    proposal_ids: list[str] = []
    for question in ("What should prune one?", "What should prune two?"):
        preview = runner.invoke(
            app,
            [
                "fileback",
                "preview",
                question,
                "--answer-markdown",
                f"Answer for {question}",
                "--summary",
                f"Summary for {question}",
                "--evidence-path",
                evidence_path.as_posix(),
                "--queue",
                "--output",
                "json",
            ],
            env={"SNOWIKI_ROOT": str(tmp_path)},
        )
        assert preview.exit_code == 0, preview.output
        proposal_id = json.loads(preview.output)["result"]["proposal"]["proposal_id"]
        proposal_ids.append(proposal_id)
        rejected = runner.invoke(
            app,
            [
                "fileback",
                "queue",
                "reject",
                proposal_id,
                "--reason",
                "Prune fixture.",
                "--output",
                "json",
            ],
            env={"SNOWIKI_ROOT": str(tmp_path)},
        )
        assert rejected.exit_code == 0, rejected.output

    dry_run = runner.invoke(
        app,
        [
            "fileback",
            "queue",
            "prune",
            "--status",
            "rejected",
            "--keep",
            "1",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert dry_run.exit_code == 0, dry_run.output
    dry_payload = json.loads(dry_run.output)
    assert dry_payload["result"]["dry_run"] is True
    assert dry_payload["result"]["candidate_count"] == 1
    assert (tmp_path / dry_payload["result"]["candidates"][0]).exists()

    deleted = runner.invoke(
        app,
        [
            "fileback",
            "queue",
            "prune",
            "--status",
            "rejected",
            "--keep",
            "1",
            "--delete",
            "--yes",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert deleted.exit_code == 0, deleted.output
    deleted_payload = json.loads(deleted.output)
    assert deleted_payload["result"]["deleted_count"] == 1
    assert not (tmp_path / deleted_payload["result"]["deleted"][0]).exists()
    assert len(proposal_ids) == 2


def test_fileback_preview_auto_apply_low_risk_applies_immediately(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should auto apply?",
            "--answer-markdown",
            "Auto apply this low-risk answer.",
            "--summary",
            "Auto applied fileback answer.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--auto-apply-low-risk",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    proposal = payload["result"]["proposal"]
    queue_result = payload["result"]["queue"]
    assert queue_result["status"] == "applied"
    assert queue_result["decision"] == "auto_applied"
    assert queue_result["requires_human_review"] is False
    assert not (tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json").exists()
    assert (tmp_path / queue_result["proposal_path"]).exists()
    assert (tmp_path / proposal["apply_plan"]["raw_note_path"]).exists()


def test_fileback_queue_uses_explicit_root_option(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path)
    other_root = tmp_path / "other-root"

    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What should use explicit root?",
            "--answer-markdown",
            "Queue this answer under an explicit root.",
            "--summary",
            "Explicit root queued answer.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--root",
            str(tmp_path),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(other_root)},
    )
    assert preview.exit_code == 0, preview.output
    preview_payload = json.loads(preview.output)
    queue_path = preview_payload["result"]["queue"]["proposal_path"]
    assert preview_payload["result"]["root"] == tmp_path.resolve().as_posix()
    assert (tmp_path / queue_path).exists()
    assert not (other_root / queue_path).exists()

    listed = runner.invoke(
        app,
        ["fileback", "queue", "list", "--root", str(tmp_path), "--output", "json"],
        env={"SNOWIKI_ROOT": str(other_root)},
    )
    assert listed.exit_code == 0, listed.output
    listed_payload = json.loads(listed.output)
    assert listed_payload["result"]["root"] == tmp_path.resolve().as_posix()
    assert listed_payload["result"]["proposals"][0]["proposal_path"] == queue_path

    other_listed = runner.invoke(
        app,
        ["fileback", "queue", "list", "--output", "json"],
        env={"SNOWIKI_ROOT": str(other_root)},
    )
    assert other_listed.exit_code == 0, other_listed.output
    other_payload = json.loads(other_listed.output)
    assert other_payload["result"]["root"] == other_root.resolve().as_posix()
    assert other_payload["result"]["proposals"] == []


def test_fileback_apply_persists_derived_record_and_rebuilds_question_output(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(
        tmp_path,
        evidence_path,
        answer_markdown="Reviewed answer with **markdown** support.",
        summary="Reviewed fileback summary.",
    )
    proposal_file = tmp_path / "reviewed-fileback.json"
    proposal_file.write_text(json.dumps(reviewed_payload, indent=2), encoding="utf-8")

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 0, apply.output
    payload = json.loads(apply.output)
    assert payload["ok"] is True
    assert payload["command"] == "fileback apply"

    result = payload["result"]
    preview_proposal = reviewed_payload["result"]["proposal"]
    preview_write = reviewed_payload["result"]["proposed_write"]
    assert (
        result["normalized_path"] == preview_proposal["apply_plan"]["normalized_path"]
    )
    assert result["compiled_path"] == "compiled/questions/what-did-we-ship.md"
    assert result["raw_ref"]["path"] == preview_proposal["apply_plan"]["raw_note_path"]
    assert (tmp_path / result["raw_ref"]["path"]).exists()
    assert (tmp_path / result["normalized_path"]).exists()
    assert (tmp_path / result["compiled_path"]).exists()
    assert (tmp_path / "index/manifest.json").exists()
    assert (tmp_path / result["raw_ref"]["path"]).read_text(
        encoding="utf-8"
    ) == preview_write["raw_note_body"]

    normalized_payload = json.loads(
        (tmp_path / result["normalized_path"]).read_text(encoding="utf-8")
    )
    assert normalized_payload == preview_write["normalized_record_payload"]
    assert normalized_payload["source_type"] == "manual-question"
    assert normalized_payload["record_type"] == "question"
    assert normalized_payload["question"] == "What did we ship?"
    assert (
        normalized_payload["answer_markdown"]
        == "Reviewed answer with **markdown** support."
    )
    assert normalized_payload["summary"] == "Reviewed fileback summary."
    assert normalized_payload["raw_ref"]["path"].startswith("raw/manual/questions/")
    assert normalized_payload["derivation"]["kind"] == "derived"
    assert normalized_payload["derivation"]["synthesized"] is True
    assert (
        normalized_payload["derivation"]["reviewed_proposal_id"]
        == result["proposal_id"]
    )
    assert (
        evidence_path.as_posix()
        in normalized_payload["derivation"]["supporting_compiled_paths"]
    )
    assert normalized_payload["projection"]["title"] == "What did we ship?"
    assert normalized_payload["projection"]["taxonomy"]["questions"][0]["title"] == (
        "What did we ship?"
    )

    compiled_output = (tmp_path / result["compiled_path"]).read_text(encoding="utf-8")
    assert "# What did we ship?" in compiled_output
    assert "## Answer" in compiled_output
    assert "Reviewed answer with **markdown** support." in compiled_output
    assert "## Provenance" in compiled_output
    assert normalized_payload["raw_ref"]["path"] in compiled_output


def test_fileback_apply_rejects_malformed_reviewed_payload(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    del reviewed_payload["result"]["proposal"]
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="malformed-reviewed-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert "result.proposal" in payload["error"]["message"]


@pytest.mark.parametrize(
    ("field_path", "value", "expected_message"),
    [
        (("result", "proposal", "draft", "question"), "   ", "question is required"),
        (
            ("result", "proposal", "draft", "answer_markdown"),
            "   ",
            "answer_markdown is required",
        ),
        (("result", "proposal", "draft", "summary"), "   ", "summary is required"),
        (
            ("result", "proposal", "evidence", "requested_paths"),
            [],
            "at least one evidence path is required",
        ),
    ],
)
def test_fileback_apply_rejects_empty_reviewed_fields(
    tmp_path: Path,
    field_path: tuple[str, ...],
    value: object,
    expected_message: str,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    target: Any = reviewed_payload
    for segment in field_path[:-1]:
        target = target[segment]
    target[field_path[-1]] = value
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="empty-reviewed-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert expected_message in payload["error"]["message"]


@pytest.mark.parametrize(
    ("field_path", "expected_message"),
    [
        (("result", "proposal", "draft", "question"), "question is required"),
        (
            ("result", "proposal", "draft", "answer_markdown"),
            "answer_markdown is required",
        ),
        (("result", "proposal", "draft", "summary"), "summary is required"),
        (
            ("result", "proposal", "evidence", "requested_paths"),
            "at least one evidence path is required",
        ),
    ],
)
def test_fileback_apply_rejects_missing_reviewed_fields(
    tmp_path: Path,
    field_path: tuple[str, ...],
    expected_message: str,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    target: Any = reviewed_payload
    for segment in field_path[:-1]:
        target = target[segment]
    del target[field_path[-1]]
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="missing-reviewed-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert expected_message in payload["error"]["message"]


def test_fileback_apply_rejects_root_mismatch(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    reviewed_payload["result"]["root"] = (tmp_path / "other-root").as_posix()
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="root-mismatch-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert "created for" in payload["error"]["message"]


def test_fileback_apply_rejects_unsupported_version(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    reviewed_payload["result"]["proposal"]["proposal_version"] = 2
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="unsupported-version-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert "unsupported fileback proposal version" in payload["error"]["message"]


def test_fileback_apply_rejects_unsafe_proposal_id(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    reviewed_payload["result"]["proposal"]["proposal_id"] = "../evil"
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="unsafe-proposal-id-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert "proposal_id must match" in payload["error"]["message"]


def test_fileback_apply_rejects_replayed_proposal_id(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    reviewed_payload["result"]["proposal"]["proposal_id"] = (
        "fileback-proposal-0000000000000000"
    )
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="replayed-proposal-id-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert "proposal id no longer matches" in payload["error"]["message"]


def test_fileback_apply_rejects_reviewed_apply_plan_mismatch(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)
    reviewed_payload = _preview_payload(tmp_path, evidence_path)
    reviewed_payload["result"]["proposal"]["apply_plan"]["raw_note_path"] = (
        "raw/manual/questions/2099/01/01/tampered.md"
    )
    proposal_file = _write_payload_file(
        tmp_path, reviewed_payload, name="tampered-apply-plan-fileback.json"
    )

    apply = _invoke_apply(tmp_path, proposal_file)

    assert apply.exit_code == 1
    payload = json.loads(apply.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "fileback_apply_failed"
    assert "proposed write set" in payload["error"]["message"]


def test_fileback_apply_uses_unique_raw_note_paths_for_same_day_repeats(
    tmp_path: Path,
) -> None:
    evidence_path = _build_fileback_workspace(tmp_path)

    first_preview = _preview_payload(
        tmp_path,
        evidence_path,
        answer_markdown="First reviewed answer.",
        summary="First reviewed summary.",
    )
    first_file = _write_payload_file(
        tmp_path, first_preview, name="first-reviewed-fileback.json"
    )
    first_apply = _invoke_apply(tmp_path, first_file)
    assert first_apply.exit_code == 0, first_apply.output
    first_result = json.loads(first_apply.output)["result"]
    first_raw_path = first_result["raw_ref"]["path"]
    first_raw_content = (tmp_path / first_raw_path).read_text(encoding="utf-8")

    second_preview = _preview_payload(
        tmp_path,
        evidence_path,
        answer_markdown="Second reviewed answer.",
        summary="Second reviewed summary.",
    )
    second_file = _write_payload_file(
        tmp_path, second_preview, name="second-reviewed-fileback.json"
    )
    second_apply = _invoke_apply(tmp_path, second_file)
    assert second_apply.exit_code == 0, second_apply.output
    second_result = json.loads(second_apply.output)["result"]
    second_raw_path = second_result["raw_ref"]["path"]

    assert first_result["compiled_path"] == second_result["compiled_path"]
    assert first_raw_path != second_raw_path
    assert (tmp_path / first_raw_path).exists()
    assert (tmp_path / second_raw_path).exists()
    assert (tmp_path / first_raw_path).read_text(encoding="utf-8") == first_raw_content
    assert "First reviewed answer." in first_raw_content
    assert "Second reviewed answer." in (tmp_path / second_raw_path).read_text(
        encoding="utf-8"
    )

    first_normalized = json.loads(
        (tmp_path / first_result["normalized_path"]).read_text(encoding="utf-8")
    )
    second_normalized = json.loads(
        (tmp_path / second_result["normalized_path"]).read_text(encoding="utf-8")
    )
    assert first_normalized["raw_ref"]["path"] == first_raw_path
    assert second_normalized["raw_ref"]["path"] == second_raw_path

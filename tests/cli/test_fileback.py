from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app


def _workspace_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if path.is_file()
    }


def _build_fileback_workspace(tmp_path: Path, claude_basic_fixture: Path) -> Path:
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["ingest", str(claude_basic_fixture), "--source", "claude", "--output", "json"],
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


def test_fileback_preview_is_reviewable_and_non_mutating(
    tmp_path: Path,
    claude_basic_fixture: Path,
) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path, claude_basic_fixture)
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
    assert proposal["apply_plan"]["normalized_path"].startswith("normalized/fileback/")
    assert proposal["apply_plan"]["rebuild_required"] is True


def test_fileback_apply_persists_derived_record_and_rebuilds_question_output(
    tmp_path: Path,
    claude_basic_fixture: Path,
) -> None:
    runner = CliRunner()
    evidence_path = _build_fileback_workspace(tmp_path, claude_basic_fixture)

    preview = runner.invoke(
        app,
        [
            "fileback",
            "preview",
            "What did we ship?",
            "--answer-markdown",
            "Initial answer that should be reviewed.",
            "--summary",
            "Initial fileback summary.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert preview.exit_code == 0, preview.output
    reviewed_payload = json.loads(preview.output)
    reviewed_payload["result"]["proposal"]["draft"]["answer_markdown"] = (
        "Reviewed answer with **markdown** support."
    )
    reviewed_payload["result"]["proposal"]["draft"]["summary"] = (
        "Reviewed fileback summary."
    )
    proposal_file = tmp_path / "reviewed-fileback.json"
    proposal_file.write_text(json.dumps(reviewed_payload, indent=2), encoding="utf-8")

    apply = runner.invoke(
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

    assert apply.exit_code == 0, apply.output
    payload = json.loads(apply.output)
    assert payload["ok"] is True
    assert payload["command"] == "fileback apply"

    result = payload["result"]
    assert result["normalized_path"].startswith("normalized/fileback/")
    assert result["compiled_path"] == "compiled/questions/what-did-we-ship.md"
    assert result["raw_ref"]["path"].startswith("raw/fileback/")
    assert (tmp_path / result["raw_ref"]["path"]).exists()
    assert (tmp_path / result["normalized_path"]).exists()
    assert (tmp_path / result["compiled_path"]).exists()
    assert (tmp_path / "index/manifest.json").exists()

    normalized_payload = json.loads(
        (tmp_path / result["normalized_path"]).read_text(encoding="utf-8")
    )
    assert normalized_payload["source_type"] == "fileback"
    assert normalized_payload["record_type"] == "fileback"
    assert normalized_payload["question"] == "What did we ship?"
    assert (
        normalized_payload["answer_markdown"]
        == "Reviewed answer with **markdown** support."
    )
    assert normalized_payload["summary"] == "Reviewed fileback summary."
    assert normalized_payload["raw_ref"]["path"].startswith("raw/fileback/")
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
    assert (
        normalized_payload["compiler"]["questions"][0]["title"] == "What did we ship?"
    )

    compiled_output = (tmp_path / result["compiled_path"]).read_text(encoding="utf-8")
    assert "# What did we ship?" in compiled_output
    assert "## Answer" in compiled_output
    assert "Reviewed answer with **markdown** support." in compiled_output
    assert "## Provenance" in compiled_output
    assert normalized_payload["raw_ref"]["path"] in compiled_output

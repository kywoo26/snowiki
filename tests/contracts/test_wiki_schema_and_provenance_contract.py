from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from click.testing import CliRunner
from pydantic import BaseModel

from snowiki.cli.main import app
from snowiki.fileback import apply_fileback_proposal, build_fileback_proposal
from snowiki.mcp import create_server
from snowiki.schema import Event, IngestStatus, Provenance, Session


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


def _build_lint_issue_workspace(root: Path) -> None:
    _write_json(
        root / "normalized" / "record.json",
        {
            "id": "record-1",
            "source_type": "claude",
            "record_type": "session",
            "provenance": {"raw_refs": [{"path": "raw/claude/missing.jsonl"}]},
        },
    )
    _write_text(
        root / "compiled" / "topic.md",
        '---\ntitle: "Topic"\n---\n# Topic\n\n[[compiled/missing]]\n',
    )


def _build_fileback_workspace(root: Path, claude_basic_fixture: Path) -> Path:
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["ingest", str(claude_basic_fixture), "--source", "claude", "--output", "json"],
        env={"SNOWIKI_ROOT": str(root)},
    )
    assert ingest.exit_code == 0, ingest.output

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(root)},
    )
    assert rebuild.exit_code == 0, rebuild.output

    summary_paths = sorted((root / "compiled" / "summaries").glob("*.md"))
    assert summary_paths
    return summary_paths[0].relative_to(root)


def test_cli_json_envelope_and_error_behavior_lock_current_transport_truths(
    tmp_path: Path,
) -> None:
    runner = CliRunner()

    status_root = tmp_path / "status-root"
    status_root.mkdir()
    status = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(status_root)},
    )

    assert status.exit_code == 0, status.output
    status_payload = cast(dict[str, Any], json.loads(status.output))
    assert status_payload["ok"] is True
    assert status_payload["command"] == "status"
    assert set(status_payload) == {"command", "ok", "result"}
    assert "error" not in status_payload

    lint_root = tmp_path / "lint-root"
    _build_lint_issue_workspace(lint_root)
    lint = runner.invoke(
        app,
        ["lint", "--output", "json"],
        env={"SNOWIKI_ROOT": str(lint_root)},
    )

    assert lint.exit_code == 1, lint.output
    lint_payload = cast(dict[str, Any], json.loads(lint.output))
    assert lint_payload["ok"] is False
    assert lint_payload["command"] == "lint"
    assert set(lint_payload) == {"command", "ok", "result"}
    assert "error" not in lint_payload

    apply_root = tmp_path / "apply-root"
    apply_root.mkdir()
    malformed_payload = {
        "ok": True,
        "command": "fileback preview",
        "result": {"root": apply_root.as_posix()},
    }
    proposal_file = apply_root / "malformed-reviewed-fileback.json"
    _ = proposal_file.write_text(
        json.dumps(malformed_payload, indent=2), encoding="utf-8"
    )

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
        env={"SNOWIKI_ROOT": str(apply_root)},
    )

    assert apply.exit_code == 1, apply.output
    apply_payload = cast(dict[str, Any], json.loads(apply.output))
    assert apply_payload["ok"] is False
    assert set(apply_payload) == {"error", "ok"}
    assert apply_payload["error"]["code"] == "fileback_apply_failed"
    assert "result.proposal" in apply_payload["error"]["message"]
    assert "command" not in apply_payload
    assert "result" not in apply_payload


def test_mcp_readonly_tools_and_resources_keep_distinct_wrapper_contracts() -> None:
    session_payload: dict[str, Any] = {
        "id": "session-1",
        "path": "normalized/claude/2026/04/18/session-1.json",
        "title": "Schema Contract Session",
        "summary": "Schema provenance contract discussion.",
        "content": "schema provenance contract discussion",
        "recorded_at": "2026-04-18T10:00:00Z",
    }
    server = create_server(
        session_records=[session_payload],
        compiled_pages=[
            {
                "path": "compiled/topics/topic-one.md",
                "title": "Topic One",
                "summary": "Compiled topic resource.",
                "body": "A compiled page.",
                "related": [],
            }
        ],
    )

    search_result = cast(
        dict[str, Any],
        server.call_tool(
        "search", {"query": "schema provenance contract", "limit": 1}
    )
    )
    search_content = cast(list[dict[str, Any]], search_result["content"])
    search_structured = cast(dict[str, Any], search_result["structuredContent"])
    search_hits = cast(list[dict[str, Any]], search_structured["hits"])

    assert set(search_result) == {"content", "structuredContent"}
    assert "contents" not in search_result
    assert "isError" not in search_result
    assert len(search_content) == 1
    assert search_content[0]["type"] == "text"
    assert json.loads(cast(str, search_content[0]["text"])) == search_structured
    assert search_structured["query"] == "schema provenance contract"
    assert search_structured["limit"] == 1
    hit = search_hits[0]
    assert {
        "id",
        "kind",
        "matched_terms",
        "metadata",
        "path",
        "recorded_at",
        "score",
        "source_type",
        "summary",
        "title",
    } <= set(hit)
    assert hit["path"] == session_payload["path"]
    assert hit["source_type"] == "normalized"
    assert hit["recorded_at"] == "2026-04-18T10:00:00+00:00"

    blocked_tool = cast(dict[str, Any], server.call_tool("status", {}))
    assert blocked_tool["isError"] is True
    assert blocked_tool["structuredContent"] == {
        "error": "Write operation `status` is not exposed by this read-only MCP facade."
    }
    assert blocked_tool["content"] == [
        {
            "text": "Write operation `status` is not exposed by this read-only MCP facade.",
            "type": "text",
        }
    ]
    assert "contents" not in blocked_tool

    resource_result = cast(dict[str, Any], server.read_resource("session://session-1"))
    resource_contents = cast(list[dict[str, Any]], resource_result["contents"])
    assert set(resource_result) == {"contents"}
    assert "structuredContent" not in resource_result
    assert len(resource_contents) == 1
    resource_entry = resource_contents[0]
    assert resource_entry["mimeType"] == "application/json"
    assert resource_entry["uri"] == "session://session-1"
    assert json.loads(cast(str, resource_entry["text"])) == session_payload

    missing_resource = cast(dict[str, Any], server.read_resource("topic://missing-topic"))
    missing_entry = cast(list[dict[str, Any]], missing_resource["contents"])[0]
    missing_payload = cast(dict[str, Any], json.loads(cast(str, missing_entry["text"])))
    assert missing_entry["mimeType"] == "application/json"
    assert missing_entry["uri"] == "topic://missing-topic"
    assert missing_payload["uri"] == "topic://missing-topic"
    assert "Unknown topic resource" in missing_payload["error"]


def test_fileback_reviewed_write_contract_requires_matching_apply_plan_and_provenance(
    tmp_path: Path,
    claude_basic_fixture: Path,
) -> None:
    root = tmp_path / "wiki-root"
    evidence_path = _build_fileback_workspace(root, claude_basic_fixture)
    proposal = build_fileback_proposal(
        root,
        question="What schema truths ship today?",
        answer_markdown="The current runtime ships reviewed fileback writes.",
        summary="Reviewed schema truth summary.",
        evidence_paths=[evidence_path.as_posix()],
        created_at="2026-04-18T12:00:00Z",
    )

    assert proposal["proposal_version"] == 1
    assert proposal["evidence"]["requested_paths"] == [evidence_path.as_posix()]
    assert proposal["evidence"]["resolved_paths"]["compiled"] == [
        evidence_path.as_posix()
    ]
    assert proposal["evidence"]["supporting_record_ids"]
    assert proposal["derivation"] == {
        "kind": "derived",
        "synthesized": True,
        "source_authorship": "reviewed_fileback_proposal",
        "honesty_note": (
            "This answer is synthesized from reviewed Snowiki evidence and stored "
            "as a derived fileback record. Supporting sources are preserved as "
            "evidence, not claimed as direct raw authorship."
        ),
        "supporting_compiled_paths": [evidence_path.as_posix()],
        "supporting_normalized_paths": proposal["evidence"]["resolved_paths"][
            "normalized"
        ],
        "supporting_raw_paths": proposal["evidence"]["resolved_paths"]["raw"],
        "supporting_record_ids": proposal["evidence"]["supporting_record_ids"],
    }
    assert proposal["apply_plan"]["source_type"] == "manual-question"
    assert proposal["apply_plan"]["record_type"] == "question"
    assert proposal["apply_plan"]["rebuild_required"] is True

    normalized_payload = cast(
        dict[str, Any], proposal["apply_plan"]["proposed_normalized_record_payload"]
    )
    assert normalized_payload["source_type"] == "manual-question"
    assert normalized_payload["record_type"] == "question"
    assert normalized_payload["raw_ref"]["path"] == proposal["apply_plan"][
        "raw_note_path"
    ]
    assert normalized_payload["provenance"]["link_chain"] == ["normalized", "raw"]
    assert normalized_payload["provenance"]["raw_refs"][0]["path"] == proposal[
        "apply_plan"
    ]["raw_note_path"]
    assert normalized_payload["derivation"]["kind"] == "derived"
    assert normalized_payload["derivation"]["synthesized"] is True
    assert normalized_payload["derivation"]["source_authorship"] == (
        "reviewed_fileback_proposal"
    )
    assert normalized_payload["derivation"]["reviewed_proposal_id"] == proposal[
        "proposal_id"
    ]
    assert normalized_payload["derivation"]["reviewed_proposal_version"] == proposal[
        "proposal_version"
    ]
    assert normalized_payload["derivation"]["supporting_compiled_paths"] == [
        evidence_path.as_posix()
    ]
    assert normalized_payload["derivation"]["supporting_record_ids"]

    reviewed_payload: dict[str, Any] = {
        "ok": True,
        "command": "fileback preview",
        "result": {"root": root.as_posix(), "proposal": proposal},
    }
    mutated_payload = cast(dict[str, Any], copy.deepcopy(reviewed_payload))
    mutated_payload["result"]["proposal"]["apply_plan"]["rebuild_required"] = False

    with pytest.raises(
        ValueError,
        match="reviewed apply plan no longer matches the proposed write set",
    ):
        _ = apply_fileback_proposal(root, mutated_payload)

    result = apply_fileback_proposal(root, reviewed_payload)
    assert result["proposal_id"] == proposal["proposal_id"]
    assert result["proposal_version"] == proposal["proposal_version"]
    assert result["raw_ref"]["path"] == proposal["apply_plan"]["raw_note_path"]
    assert result["normalized_path"] == proposal["apply_plan"]["normalized_path"]
    assert result["compiled_path"] == proposal["target"]["compiled_path"]
    assert result["supporting_raw_ref_count"] >= 1

    normalized_path = root / cast(str, result["normalized_path"])
    assert (
        cast(dict[str, Any], json.loads(normalized_path.read_text(encoding="utf-8")))
        == normalized_payload
    )

    compiled_output = (root / cast(str, result["compiled_path"])).read_text(
        encoding="utf-8"
    )
    assert "## Provenance" in compiled_output
    assert normalized_payload["raw_ref"]["path"] in compiled_output


@pytest.mark.parametrize(
    ("model_cls", "required_fields"),
    [
        (
            Provenance,
            {"id", "source", "identity_keys", "raw_uri", "raw_id", "raw_kind", "captured_at"},
        ),
        (Session, {"identity_keys", "provenance"}),
        (Event, {"identity_keys", "provenance"}),
        (IngestStatus, {"identity_keys", "provenance"}),
    ],
)
def test_provenance_bearing_schema_surfaces_keep_minimum_required_fields(
    model_cls: type[BaseModel],
    required_fields: set[str],
) -> None:
    actual_required = {
        name for name, field in model_cls.model_fields.items() if field.is_required()
    }
    assert required_fields <= actual_required

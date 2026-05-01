from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from tests.helpers.projection import compiler_projection

from snowiki.cli.main import app
from snowiki.search.workspace import current_runtime_tokenizer_name
from snowiki.storage.index_manifest import current_content_identity_payload
from snowiki.storage.zones import StoragePaths


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _compiled_page(*, title: str, page_type: str, updated: str, body: str) -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            f'type: "{page_type}"',
            'created: "2026-04-15"',
            f'updated: "{updated}"',
            f'summary: "Summary for {title}"',
            "sources:",
            '  - "raw/claude/source-a.jsonl"',
            "related:",
            '  - "compiled/overview.md"',
            "tags:",
            f'  - "{page_type}"',
            "record_ids:",
            f'  - "{title.lower().replace(" ", "-")}"',
            "---",
            body,
        ]
    )


def _workspace_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if path.is_file()
    }


def _build_status_workspace(root: Path) -> None:
    _write_text(root / "raw" / "claude" / "source-a.jsonl", "{}\n")
    _write_text(root / "raw" / "opencode" / "source-b.jsonl", "{}\n")
    _write_json(
        root / "normalized" / "claude" / "2026-04-15" / "session-a.json",
        {
            "id": "session-a",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-15T09:00:00Z",
            "projection": compiler_projection("Session A"),
            "provenance": {"raw_refs": [{"path": "raw/claude/source-a.jsonl"}]},
        },
    )
    _write_json(
        root / "normalized" / "opencode" / "2026-04-16" / "session-b.json",
        {
            "id": "session-b",
            "source_type": "opencode",
            "record_type": "session",
            "recorded_at": "2026-04-16T08:30:00Z",
            "projection": compiler_projection("Session B"),
            "provenance": {"raw_refs": [{"path": "raw/opencode/source-b.jsonl"}]},
        },
    )

    _write_text(
        root / "compiled" / "overview.md",
        _compiled_page(
            title="Overview",
            page_type="overview",
            updated="2026-04-16",
            body="# Overview\n\n[[compiled/topics/wiki-dashboard]]\n[[compiled/questions/what-is-status]]\n",
        ),
    )
    _write_text(
        root / "compiled" / "topics" / "wiki-dashboard.md",
        _compiled_page(
            title="Wiki Dashboard",
            page_type="topic",
            updated="2026-04-15",
            body="# Wiki Dashboard\n\n[[compiled/overview]]\n[[compiled/questions/what-is-status]]\n",
        ),
    )
    _write_text(
        root / "compiled" / "questions" / "what-is-status.md",
        _compiled_page(
            title="What Is Status",
            page_type="question",
            updated="2026-04-14",
            body="# What Is Status\n\n[[compiled/overview]]\n[[compiled/topics/wiki-dashboard]]\n",
        ),
    )

    _write_json(
        root / "index" / "manifest.json",
        {
            "tokenizer_name": "kiwi_morphology_v1",
            "records_indexed": 2,
            "pages_indexed": 3,
            "search_documents": 5,
            "compiled_paths": [
                "compiled/overview.md",
                "compiled/questions/what-is-status.md",
                "compiled/topics/wiki-dashboard.md",
            ],
            "content_identity": current_content_identity_payload(
                StoragePaths(root), current_runtime_tokenizer_name()
            ),
        },
    )


def test_status_json_output_reports_wiki_native_dashboard_sections(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "status",
        "result": {
            "root": tmp_path.as_posix(),
            "pages": {
                "total": 3,
                "by_type": {
                    "summary": 0,
                    "concept": 0,
                    "entity": 0,
                    "topic": 1,
                    "question": 1,
                    "project": 0,
                    "decision": 0,
                    "session": 0,
                    "index": 0,
                    "log": 0,
                    "overview": 1,
                },
            },
            "sources": {
                "total": 2,
                "by_type": {"claude": 1, "opencode": 1},
                "freshness": {
                    "total": 0,
                    "counts": {
                        "invalid": 0,
                        "modified": 0,
                        "missing": 0,
                        "untracked": 0,
                        "current": 0,
                    },
                    "stale_count": 0,
                },
            },
            "lint": {
                "summary": {"error": 0, "warning": 0, "info": 0, "total": 0},
                "error_count": 0,
            },
            "freshness": {
                "status": "current",
                "manifest_content_identity": current_content_identity_payload(
                    StoragePaths(tmp_path), current_runtime_tokenizer_name()
                ),
                "current_content_identity": current_content_identity_payload(
                    StoragePaths(tmp_path), current_runtime_tokenizer_name()
                ),
                "latest_normalized_recorded_at": "2026-04-16T08:30:00Z",
                "latest_compiled_update": "2026-04-16",
            },
            "manifest": {
                "path": "index/manifest.json",
                "present": True,
                "tokenizer_name": "kiwi_morphology_v1",
                "records_indexed": 2,
                "pages_indexed": 3,
                "search_documents": 5,
                "compiled_path_count": 3,
            },
        },
    }


def test_status_reports_projection_lint_errors_without_failing(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    normalized_path = tmp_path / "normalized" / "claude" / "2026-04-15" / "session-a.json"
    normalized_payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    del normalized_payload["projection"]
    _write_json(normalized_path, normalized_payload)

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["result"]["lint"]["error_count"] == 1
    assert payload["result"]["lint"]["summary"]["error"] == 1


def test_status_reports_missing_manifest_without_crashing(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    (tmp_path / "index" / "manifest.json").unlink()

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["freshness"]["status"] == "missing"
    assert payload["result"]["freshness"]["manifest_content_identity"] is None
    assert payload["result"]["manifest"]["present"] is False


def test_status_reports_stale_manifest_without_crashing(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["content_identity"]["compiled"]["content_hash"] = "stale"
    _write_json(manifest_path, manifest_payload)

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["freshness"]["status"] == "stale"
    assert payload["result"]["manifest"]["present"] is True
    assert payload["result"]["manifest"]["tokenizer_name"] == "kiwi_morphology_v1"


def test_status_reports_invalid_manifest_without_crashing(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    _write_json(tmp_path / "index" / "manifest.json", [])

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["freshness"]["status"] == "invalid"
    assert payload["result"]["freshness"]["manifest_content_identity"] is None
    assert payload["result"]["manifest"]["present"] is True
    assert payload["result"]["manifest"]["tokenizer_name"] is None


def test_status_human_output_renders_dashboard_summary(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)

    result = runner.invoke(app, ["status"], env={"SNOWIKI_ROOT": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert f"Snowiki status for {tmp_path.as_posix()}" in result.output
    assert "Pages: 3 total" in result.output
    assert (
        "By type: summary: 0, concept: 0, entity: 0, topic: 1, question: 1, project: 0, decision: 0, session: 0, index: 0, log: 0, overview: 1"
        in result.output
    )
    assert "Sources: 2 total" in result.output
    assert "By source: claude: 1, opencode: 1" in result.output
    assert "Lint: 0 errors, 0 warnings, 0 info" in result.output
    assert (
        "Freshness: state=current, tokenizer=kiwi_morphology_v1, latest normalized=2026-04-16T08:30:00Z, latest compiled=2026-04-16"
        in result.output
    )
    assert (
        "Source Freshness: stale=0, invalid=0, modified=0, missing=0, untracked=0, current=0"
        in result.output
    )
    assert (
        "Manifest: tokenizer=kiwi_morphology_v1, records indexed=2, pages indexed=3, search documents=5, compiled paths=3"
        in result.output
    )


def test_status_is_read_only_and_does_not_mutate_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    before = _workspace_snapshot(tmp_path)

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert _workspace_snapshot(tmp_path) == before

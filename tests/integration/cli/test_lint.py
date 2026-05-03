from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from tests.helpers.projection import compiler_projection

from snowiki.cli.main import app
from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.search.workspace import current_runtime_tokenizer_name
from snowiki.storage.index_manifest import (
    IndexManifest,
    current_index_identity,
    write_index_manifest,
)
from snowiki.storage.zones import StoragePaths


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_compiled_page(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _frontmatter_page(*, title: str, body: str = "# Page\n") -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            'type: "topic"',
            'created: "2026-04-16"',
            'updated: "2026-04-16"',
            'summary: "Summary"',
            "sources:",
            '  - "raw/claude/source.jsonl"',
            "related: []",
            "tags: []",
            "record_ids:",
            '  - "record-1"',
            "---",
            body,
        ]
    )


def _write_current_manifest(root: Path) -> None:
    paths = StoragePaths(root)
    paths.ensure_all()
    compiled_paths = tuple(
        path.relative_to(root).as_posix()
        for path in sorted(paths.compiled.rglob("*.md"), key=lambda item: item.as_posix())
    )
    write_index_manifest(
        paths,
        IndexManifest(
            schema_version=1,
            records_indexed=len(list(paths.normalized.rglob("*.json"))),
            pages_indexed=len(compiled_paths),
            search_documents=len(compiled_paths),
            compiled_paths=compiled_paths,
            identity=current_index_identity(
                paths,
                retrieval_identity_for_tokenizer(current_runtime_tokenizer_name()),
            ),
        ),
    )


def test_lint_json_output_includes_summary_checks_and_normalized_issues(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _write_json(
        tmp_path / "normalized" / "record.json",
        {
            "id": "record-1",
            "source_type": "claude",
            "record_type": "session",
            "provenance": {"raw_refs": [{"path": "raw/claude/missing.jsonl"}]},
        },
    )
    _write_compiled_page(
        tmp_path / "compiled" / "topic.md",
        '---\ntitle: "Topic"\n---\n# Topic\n\n[[compiled/missing]]\n',
    )

    result = runner.invoke(
        app,
        ["lint", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["command"] == "lint"
    assert payload["ok"] is False
    assert payload["result"]["root"] == tmp_path.as_posix()
    assert payload["result"]["summary"] == {
        "error": 12,
        "warning": 1,
        "info": 0,
        "total": 13,
    }
    checks_by_name = {check["name"]: check for check in payload["result"]["checks"]}
    assert checks_by_name["normalized.compiler_projection"]["issue_count"] == 1
    assert checks_by_name["compiled.frontmatter"]["issue_count"] == 8
    assert checks_by_name["integrity.raw_target"]["issue_count"] == 1
    assert checks_by_name["source.modified"]["issue_count"] == 0
    issues_by_code = {issue["code"]: issue for issue in payload["result"]["issues"]}
    assert issues_by_code["L003"]["path"] == "normalized/record.json"
    assert issues_by_code["L102"]["path"] == "normalized/record.json"
    assert issues_by_code["L201"]["target"] == "compiled/missing.md"
    assert issues_by_code["L301"]["severity"] == "warning"


def test_lint_human_output_groups_warning_only_findings(tmp_path: Path) -> None:
    runner = CliRunner()
    _write_compiled_page(
        tmp_path / "compiled" / "overview.md", _frontmatter_page(title="Overview")
    )
    _write_compiled_page(
        tmp_path / "compiled" / "topics" / "orphaned.md",
        _frontmatter_page(title="Orphaned"),
    )
    _write_current_manifest(tmp_path)

    result = runner.invoke(
        app,
        ["lint"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert f"Snowiki lint found 1 issue(s) in {tmp_path.as_posix()}" in result.output
    assert "Summary: 0 errors, 1 warnings, 0 info" in result.output
    assert "Warnings (1):" in result.output
    assert "[L301] compiled page has no inbound wikilinks" in result.output
    assert "Path: compiled/topics/orphaned.md" in result.output
    assert "Errors (" not in result.output


def test_lint_json_output_reports_info_level_stale_and_summary_coverage_checks(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _write_json(
        tmp_path / "normalized" / "claude" / "record.json",
        {
            "id": "record-1",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-16T10:00:00Z",
            "projection": compiler_projection("Claude Basic"),
            "raw_refs": [{"path": "raw/claude/source.jsonl"}],
            "provenance": {"raw_refs": [{"path": "raw/claude/source.jsonl"}]},
        },
    )
    _write_json(tmp_path / "raw" / "claude" / "source.jsonl", {"ok": True})
    _write_compiled_page(
        tmp_path / "compiled" / "topics" / "stale.md",
        "\n".join(
            [
                "---",
                'title: "Stale"',
                'type: "topic"',
                'created: "2026-01-01"',
                'updated: "2026-01-15"',
                'summary: "Old summary"',
                "sources: []",
                "related: []",
                "tags: []",
                "record_ids: []",
                "---",
                "# Stale",
            ]
        ),
    )
    _write_current_manifest(tmp_path)

    result = runner.invoke(
        app,
        ["lint", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["result"]["summary"] == {
        "error": 0,
        "warning": 1,
        "info": 2,
        "total": 3,
    }
    checks_by_name = {check["name"]: check for check in payload["result"]["checks"]}
    assert checks_by_name["freshness.stale_compiled_page"] == {
        "name": "freshness.stale_compiled_page",
        "label": "Stale compiled pages",
        "severity": "info",
        "issue_count": 1,
    }
    assert checks_by_name["source.modified"] == {
        "name": "source.modified",
        "label": "Modified Markdown sources",
        "severity": "warning",
        "issue_count": 0,
    }
    assert checks_by_name["source.missing"] == {
        "name": "source.missing",
        "label": "Missing Markdown sources",
        "severity": "warning",
        "issue_count": 0,
    }
    assert checks_by_name["source.untracked"] == {
        "name": "source.untracked",
        "label": "Untracked Markdown sources",
        "severity": "info",
        "issue_count": 0,
    }
    assert checks_by_name["source.invalid_metadata"] == {
        "name": "source.invalid_metadata",
        "label": "Invalid Markdown source metadata",
        "severity": "warning",
        "issue_count": 0,
    }
    assert checks_by_name["coverage.source_without_summary"] == {
        "name": "coverage.source_without_summary",
        "label": "Sources without summary pages",
        "severity": "info",
        "issue_count": 1,
    }
    assert payload["result"]["issues"] == [
        {
            "code": "L301",
            "check": "graph.orphan_compiled_page",
            "message": "compiled page has no inbound wikilinks",
            "path": "compiled/topics/stale.md",
            "severity": "warning",
        },
        {
            "code": "L401",
            "check": "freshness.stale_compiled_page",
            "message": "compiled page has not been updated since 2026-01-15",
            "path": "compiled/topics/stale.md",
            "severity": "info",
        },
        {
            "code": "L402",
            "check": "coverage.source_without_summary",
            "message": "normalized record is missing compiled summary page: compiled/summaries/claude-claude-basic-record-1.md",
            "path": "normalized/claude/record.json",
            "severity": "info",
            "target": "compiled/summaries/claude-claude-basic-record-1.md",
        },
    ]


def test_lint_json_output_reports_source_freshness_findings(tmp_path: Path) -> None:
    runner = CliRunner()
    source_root = tmp_path / "vault"
    source_root.mkdir()
    source_path = source_root / "note.md"
    _ = source_path.write_text("# Note\n", encoding="utf-8")
    snowiki_root = tmp_path / "snowiki"

    ingest_result = runner.invoke(
        app,
        ["ingest", str(source_root), "--rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )
    assert ingest_result.exit_code == 0, ingest_result.output

    _ = source_path.write_text("# Note\n\nChanged.\n", encoding="utf-8")
    _ = (source_root / "new.md").write_text("# New\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["lint", "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    source_issues = [
        issue
        for issue in payload["result"]["issues"]
        if str(issue["check"]).startswith("source.")
    ]
    assert source_issues == [
        {
            "code": "L501",
            "check": "source.modified",
            "message": "source file changed since ingest: note.md",
            "path": source_issues[0]["path"],
            "severity": "warning",
            "target": source_path.as_posix(),
        },
        {
            "code": "L503",
            "check": "source.untracked",
            "message": "source file has not been ingested: new.md",
            "path": (source_root / "new.md").as_posix(),
            "severity": "info",
            "target": source_root.as_posix(),
        },
    ]
    checks_by_name = {check["name"]: check for check in payload["result"]["checks"]}
    assert checks_by_name["source.modified"]["issue_count"] == 1
    assert checks_by_name["source.missing"]["issue_count"] == 0
    assert checks_by_name["source.rename_candidate"]["issue_count"] == 0
    assert checks_by_name["source.untracked"]["issue_count"] == 1


def test_lint_json_output_reports_source_rename_candidate(tmp_path: Path) -> None:
    runner = CliRunner()
    source_root = tmp_path / "vault"
    source_root.mkdir()
    anchor = source_root / "anchor.md"
    old = source_root / "old-name.md"
    new = source_root / "new-name.md"
    _ = anchor.write_text("# Anchor\n", encoding="utf-8")
    _ = old.write_text("# Topic\n\nSame content.\n", encoding="utf-8")
    snowiki_root = tmp_path / "snowiki"
    ingest_result = runner.invoke(
        app,
        ["ingest", str(source_root), "--rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )
    assert ingest_result.exit_code == 0, ingest_result.output
    old.unlink()
    _ = new.write_text("# Topic\n\nSame content.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["lint", "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    rename_issue = next(
        issue
        for issue in payload["result"]["issues"]
        if issue["check"] == "source.rename_candidate"
    )
    assert rename_issue["code"] == "L505"
    assert rename_issue["severity"] == "info"
    assert rename_issue["proposal_type"] == "source_rename_candidate"
    assert rename_issue["recommended_action"] == (
        "reingest_new_source_then_review_prune_old_record"
    )
    assert rename_issue["target"] == new.as_posix()
    assert [evidence["relative_path"] for evidence in rename_issue["evidence"]] == [
        "old-name.md",
        "new-name.md",
    ]
    checks_by_name = {check["name"]: check for check in payload["result"]["checks"]}
    assert checks_by_name["source.rename_candidate"]["issue_count"] == 1


def test_lint_exit_code_depends_only_on_error_findings(tmp_path: Path) -> None:
    runner = CliRunner()
    warning_root = tmp_path / "warning-root"
    error_root = tmp_path / "error-root"

    _write_compiled_page(
        warning_root / "compiled" / "overview.md",
        _frontmatter_page(title="Overview"),
    )
    _write_compiled_page(
        warning_root / "compiled" / "topics" / "orphaned.md",
        _frontmatter_page(title="Orphaned"),
    )
    _write_current_manifest(warning_root)

    warning_result = runner.invoke(
        app,
        ["lint", "--output", "json", "--root", str(warning_root)],
    )
    assert warning_result.exit_code == 0, warning_result.output
    assert json.loads(warning_result.output)["ok"] is True

    _write_compiled_page(
        error_root / "compiled" / "broken.md", "# Missing frontmatter\n"
    )

    error_result = runner.invoke(
        app,
        ["lint", "--output", "json", "--root", str(error_root)],
    )
    assert error_result.exit_code == 1, error_result.output
    assert json.loads(error_result.output)["ok"] is False

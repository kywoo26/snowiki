from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app


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
        "error": 11,
        "warning": 1,
        "info": 0,
        "total": 12,
    }
    assert payload["result"]["checks"] == [
        {
            "name": "normalized.required_key",
            "label": "Required normalized keys",
            "severity": "error",
            "issue_count": 0,
        },
        {
            "name": "normalized.invalid_json",
            "label": "Normalized JSON syntax",
            "severity": "error",
            "issue_count": 0,
        },
        {
            "name": "normalized.invalid_payload",
            "label": "Normalized payload object shape",
            "severity": "error",
            "issue_count": 0,
        },
        {
            "name": "compiled.frontmatter",
            "label": "Compiled page frontmatter",
            "severity": "error",
            "issue_count": 8,
        },
        {
            "name": "integrity.raw_provenance",
            "label": "Normalized raw provenance",
            "severity": "error",
            "issue_count": 0,
        },
        {
            "name": "integrity.raw_target",
            "label": "Raw provenance targets",
            "severity": "error",
            "issue_count": 1,
        },
        {
            "name": "integrity.compiled_layer",
            "label": "Compiled layer presence",
            "severity": "error",
            "issue_count": 0,
        },
        {
            "name": "integrity.index_manifest",
            "label": "Index manifest presence",
            "severity": "error",
            "issue_count": 1,
        },
        {
            "name": "graph.broken_wikilink",
            "label": "Broken compiled wikilinks",
            "severity": "error",
            "issue_count": 1,
        },
        {
            "name": "graph.orphan_compiled_page",
            "label": "Orphan compiled pages",
            "severity": "warning",
            "issue_count": 1,
        },
    ]
    assert payload["result"]["issues"] == [
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "created",
            "message": "compiled page frontmatter missing required key: created",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "record_ids",
            "message": "compiled page frontmatter missing required key: record_ids",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "related",
            "message": "compiled page frontmatter missing required key: related",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "sources",
            "message": "compiled page frontmatter missing required key: sources",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "summary",
            "message": "compiled page frontmatter missing required key: summary",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "tags",
            "message": "compiled page frontmatter missing required key: tags",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "type",
            "message": "compiled page frontmatter missing required key: type",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "field": "updated",
            "message": "compiled page frontmatter missing required key: updated",
            "path": "compiled/topic.md",
            "severity": "error",
        },
        {
            "code": "L201",
            "check": "graph.broken_wikilink",
            "message": "broken wikilink: [[compiled/missing]]",
            "path": "compiled/topic.md",
            "severity": "error",
            "target": "compiled/missing.md",
        },
        {
            "code": "L104",
            "check": "integrity.index_manifest",
            "message": "index manifest missing for compiled layer",
            "path": "index/manifest.json",
            "severity": "error",
        },
        {
            "code": "L102",
            "check": "integrity.raw_target",
            "message": "raw provenance target missing: raw/claude/missing.jsonl",
            "path": "normalized/record.json",
            "severity": "error",
        },
        {
            "code": "L301",
            "check": "graph.orphan_compiled_page",
            "message": "compiled page has no inbound wikilinks",
            "path": "compiled/topic.md",
            "severity": "warning",
        },
    ]


def test_lint_human_output_groups_warning_only_findings(tmp_path: Path) -> None:
    runner = CliRunner()
    _write_compiled_page(
        tmp_path / "compiled" / "overview.md", _frontmatter_page(title="Overview")
    )
    _write_compiled_page(
        tmp_path / "compiled" / "topics" / "orphaned.md",
        _frontmatter_page(title="Orphaned"),
    )
    _write_json(tmp_path / "index" / "manifest.json", {"pages": ["overview.md"]})

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
    _write_json(warning_root / "index" / "manifest.json", {"pages": ["overview.md"]})

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

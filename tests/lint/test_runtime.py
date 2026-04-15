from __future__ import annotations

import json
from pathlib import Path

from snowiki.lint.runtime import collect_structural_issues, run_lint


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_collect_structural_issues_reports_required_normalized_keys_and_frontmatter(
    tmp_path: Path,
) -> None:
    _write_json(tmp_path / "normalized" / "record.json", {"id": "record-1"})
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text('---\ntitle: "Topic"\n---\n# Topic\n', encoding="utf-8")

    issues = collect_structural_issues(tmp_path)

    assert issues == [
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
            "code": "L001",
            "check": "normalized.required_key",
            "field": "record_type",
            "message": "normalized record missing required key: record_type",
            "path": "normalized/record.json",
            "severity": "error",
        },
        {
            "code": "L001",
            "check": "normalized.required_key",
            "field": "source_type",
            "message": "normalized record missing required key: source_type",
            "path": "normalized/record.json",
            "severity": "error",
        },
    ]


def test_run_lint_returns_summary_counts_and_check_inventory(tmp_path: Path) -> None:
    _write_json(tmp_path / "normalized" / "record.json", {"id": "record-1"})

    result = run_lint(tmp_path)

    assert result["root"] == tmp_path.as_posix()
    assert result["summary"] == {"error": 4, "warning": 0, "info": 0, "total": 4}
    assert result["error_count"] == 4
    assert result["checks"][0] == {
        "name": "normalized.required_key",
        "label": "Required normalized keys",
        "severity": "error",
        "issue_count": 2,
    }
    assert result["checks"][4] == {
        "name": "integrity.raw_provenance",
        "label": "Normalized raw provenance",
        "severity": "error",
        "issue_count": 1,
    }
    assert result["checks"][5] == {
        "name": "integrity.raw_target",
        "label": "Raw provenance targets",
        "severity": "error",
        "issue_count": 0,
    }
    assert result["checks"][6] == {
        "name": "integrity.compiled_layer",
        "label": "Compiled layer presence",
        "severity": "error",
        "issue_count": 1,
    }

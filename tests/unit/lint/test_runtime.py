from __future__ import annotations

import json
from pathlib import Path

from snowiki.lint.runtime import (
    collect_freshness_issues,
    collect_structural_issues,
    collect_summary_coverage_issues,
    run_lint,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_compiled_page(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


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
        {
            "code": "L003",
            "check": "normalized.compiler_projection",
            "field": "projection",
            "message": "normalized record missing required compiler projection",
            "path": "normalized/record.json",
            "severity": "error",
        },
    ]


def test_run_lint_returns_summary_counts_and_check_inventory(tmp_path: Path) -> None:
    _write_json(tmp_path / "normalized" / "record.json", {"id": "record-1"})

    result = run_lint(tmp_path)

    assert result["root"] == tmp_path.as_posix()
    assert result["summary"] == {"error": 5, "warning": 0, "info": 0, "total": 5}
    assert result["error_count"] == 5
    assert result["checks"][0] == {
        "name": "normalized.required_key",
        "label": "Required normalized keys",
        "severity": "error",
        "issue_count": 2,
    }
    assert result["checks"][3] == {
        "name": "normalized.compiler_projection",
        "label": "Compiler projection contract",
        "severity": "error",
        "issue_count": 1,
    }
    assert result["checks"][5] == {
        "name": "integrity.raw_provenance",
        "label": "Normalized raw provenance",
        "severity": "error",
        "issue_count": 1,
    }
    assert result["checks"][6] == {
        "name": "integrity.raw_target",
        "label": "Raw provenance targets",
        "severity": "error",
        "issue_count": 0,
    }
    assert result["checks"][7] == {
        "name": "integrity.compiled_layer",
        "label": "Compiled layer presence",
        "severity": "error",
        "issue_count": 1,
    }
    assert result["checks"][-2:] == [
        {
            "name": "freshness.stale_compiled_page",
            "label": "Stale compiled pages",
            "severity": "info",
            "issue_count": 0,
        },
        {
            "name": "coverage.source_without_summary",
            "label": "Sources without summary pages",
            "severity": "info",
            "issue_count": 0,
        },
    ]


def test_collect_freshness_issues_reports_stale_compiled_pages(tmp_path: Path) -> None:
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

    issues = collect_freshness_issues(tmp_path)

    assert issues == [
        {
            "code": "L401",
            "check": "freshness.stale_compiled_page",
            "message": "compiled page has not been updated since 2026-01-15",
            "path": "compiled/topics/stale.md",
            "severity": "info",
        }
    ]


def test_collect_summary_coverage_issues_reports_missing_compiled_summary_page(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "normalized" / "claude" / "record.json",
        {
            "id": "record-1",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-16T10:00:00Z",
            "projection": {
                "title": "Claude Basic",
                "summary": "",
                "tags": [],
                "source_identity": {},
                "sections": [],
                "taxonomy": {
                    "concepts": [],
                    "entities": [],
                    "topics": [],
                    "questions": [],
                    "projects": [],
                    "decisions": [],
                },
            },
            "raw_refs": [{"path": "raw/claude/source.jsonl"}],
        },
    )

    issues = collect_summary_coverage_issues(tmp_path)

    assert issues == [
        {
            "code": "L402",
            "check": "coverage.source_without_summary",
            "message": "normalized record is missing compiled summary page: compiled/summaries/claude-claude-basic-record-1.md",
            "path": "normalized/claude/record.json",
            "severity": "info",
            "target": "compiled/summaries/claude-claude-basic-record-1.md",
        }
    ]


def test_run_lint_reports_missing_compiler_projection(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "normalized" / "claude" / "record.json",
        {
            "id": "record-1",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-16T10:00:00Z",
            "raw_refs": [{"path": "raw/claude/source.jsonl"}],
        },
    )

    result = run_lint(tmp_path)

    assert result["error_count"] == 3
    assert {
        "code": "L003",
        "check": "normalized.compiler_projection",
        "message": "normalized record missing required compiler projection",
        "path": "normalized/claude/record.json",
        "severity": "error",
        "field": "projection",
    } in result["issues"]

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from tests.helpers.projection import compiler_projection

from snowiki.lint.runtime import (
    collect_freshness_issues,
    collect_structural_issues,
    collect_summary_coverage_issues,
    run_lint,
)
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
    checks_by_name = {check["name"]: check for check in result["checks"]}
    assert checks_by_name["freshness.stale_compiled_page"] == {
        "name": "freshness.stale_compiled_page",
        "label": "Stale compiled pages",
        "severity": "info",
        "issue_count": 0,
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
    assert checks_by_name["source.rename_candidate"] == {
        "name": "source.rename_candidate",
        "label": "Markdown source rename candidates",
        "severity": "info",
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
        "issue_count": 0,
    }


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


def test_collect_freshness_issues_skips_missing_invalid_and_current_dates(
    tmp_path: Path,
) -> None:
    _write_compiled_page(tmp_path / "compiled" / "missing.md", "---\ntitle: Missing\n---\n")
    _write_compiled_page(
        tmp_path / "compiled" / "invalid.md",
        "---\nupdated: not-a-date\n---\n",
    )
    _write_compiled_page(
        tmp_path / "compiled" / "current.md",
        "---\nupdated: 2999-01-01T00:00:00Z\n---\n",
    )

    assert collect_freshness_issues(tmp_path) == []


def test_lint_reason_field_paths_are_public(tmp_path: Path) -> None:
    _write_compiled_page(tmp_path / "compiled" / "topic.md", "# Topic\n")
    paths = StoragePaths(tmp_path)
    current = current_index_identity(
        paths,
        retrieval_identity_for_tokenizer(current_runtime_tokenizer_name()),
    )
    write_index_manifest(
        paths,
        IndexManifest(
            schema_version=1,
            records_indexed=0,
            pages_indexed=1,
            search_documents=1,
            compiled_paths=("compiled/topic.md",),
            identity=type(current)(
                normalized=current.normalized,
                compiled=type(current.compiled)(
                    latest_mtime_ns=current.compiled.latest_mtime_ns,
                    file_count=current.compiled.file_count,
                    content_hash="stale",
                ),
                retrieval=current.retrieval,
            ),
        ),
    )

    issue = cast(dict[str, object], collect_freshness_issues(tmp_path)[0])

    assert set(issue) == {
        "code",
        "check",
        "severity",
        "path",
        "message",
        "reasons",
    }
    assert issue["code"] == "L104"
    assert issue["check"] == "integrity.index_manifest"
    assert issue["severity"] == "error"
    assert issue["path"] == "index/manifest.json"
    assert issue["message"] == "index manifest is stale; rebuild required"
    assert all(
        set(reason) == {"field_path", "manifest_value", "current_value"}
        for reason in cast(list[dict[str, object]], issue["reasons"])
    )
    assert cast(list[dict[str, object]], issue["reasons"]) == [
        {
            "field_path": "content_identity.compiled.content_hash",
            "manifest_value": "stale",
            "current_value": current.compiled.content_hash,
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
            "projection": compiler_projection("Claude Basic"),
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


def test_collect_summary_coverage_issues_skips_unloadable_records(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    normalized_root.mkdir()
    (normalized_root / "invalid.json").write_text("{", encoding="utf-8")
    _write_json(normalized_root / "array.json", [])
    _write_json(
        normalized_root / "missing-recorded-at.json",
        {"id": "record-1", "source_type": "claude", "record_type": "session"},
    )
    _write_json(
        normalized_root / "invalid-summary-path.json",
        {
            "id": "record-2",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-16T10:00:00Z",
            "provenance": {"raw_refs": [{"path": "raw/claude/source.jsonl"}]},
        },
    )

    assert collect_summary_coverage_issues(tmp_path) == []


def test_collect_structural_issues_reports_invalid_json_and_payload_shape(
    tmp_path: Path,
) -> None:
    normalized_root = tmp_path / "normalized"
    normalized_root.mkdir()
    (normalized_root / "invalid.json").write_text("{", encoding="utf-8")
    _write_json(normalized_root / "array.json", [])

    issues = collect_structural_issues(tmp_path)

    assert [issue["code"] for issue in issues] == ["L011", "L010"]
    assert {issue["check"] for issue in issues} == {
        "normalized.invalid_json",
        "normalized.invalid_payload",
    }


def test_collect_structural_issues_reports_compiled_page_without_frontmatter(
    tmp_path: Path,
) -> None:
    _write_compiled_page(tmp_path / "compiled" / "plain.md", "# Plain\n")

    issues = collect_structural_issues(tmp_path)

    assert issues == [
        {
            "code": "L002",
            "check": "compiled.frontmatter",
            "message": "compiled page missing YAML frontmatter",
            "path": "compiled/plain.md",
            "severity": "error",
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

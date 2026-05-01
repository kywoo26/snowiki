from __future__ import annotations

import json
from pathlib import Path

from tests.helpers.projection import compiler_projection

from snowiki.lint import run_lint
from snowiki.search.workspace import current_runtime_tokenizer_name
from snowiki.status import run_status
from snowiki.storage.index_manifest import current_content_identity_payload
from snowiki.storage.zones import StoragePaths


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _compiled_page(*, title: str, page_type: str, body: str) -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            f'type: "{page_type}"',
            'created: "2026-04-26"',
            'updated: "2026-04-26"',
            f'summary: "Summary for {title}"',
            "sources:",
            '  - "raw/source.jsonl"',
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


def test_status_lint_summary_excludes_full_lint_coverage(tmp_path: Path) -> None:
    _write_text(tmp_path / "raw" / "source.jsonl", "{}\n")
    _write_json(
        tmp_path / "normalized" / "record.json",
        {
            "id": "record-1",
            "source_type": "markdown",
            "record_type": "document",
            "recorded_at": "2026-04-26T00:00:00Z",
            "projection": compiler_projection("Record One"),
            "provenance": {"raw_refs": [{"path": "raw/source.jsonl"}]},
        },
    )
    _write_text(
        tmp_path / "compiled" / "overview.md",
        _compiled_page(
            title="Overview",
            page_type="overview",
            body="# Overview\n\n[[compiled/topics/record-one]]\n",
        ),
    )
    _write_text(
        tmp_path / "compiled" / "topics" / "record-one.md",
        _compiled_page(
            title="Record One",
            page_type="topic",
            body="# Record One\n\n[[compiled/overview]]\n",
        ),
    )
    _write_json(
        tmp_path / "index" / "manifest.json",
        {
            "tokenizer_name": "kiwi_morphology_v1",
            "records_indexed": 1,
            "pages_indexed": 2,
            "search_documents": 2,
            "compiled_paths": [
                "compiled/overview.md",
                "compiled/topics/record-one.md",
            ],
            "content_identity": current_content_identity_payload(
                StoragePaths(tmp_path), current_runtime_tokenizer_name()
            ),
        },
    )

    status_result = run_status(tmp_path)
    lint_result = run_lint(tmp_path)

    assert status_result["lint"] == {
        "summary": {"error": 0, "warning": 0, "info": 0, "total": 0},
        "error_count": 0,
    }
    assert any(
        issue["check"] == "coverage.source_without_summary"
        for issue in lint_result["issues"]
    )


def test_status_reports_invalid_index_manifest_without_crashing(tmp_path: Path) -> None:
    _write_text(
        tmp_path / "compiled" / "overview.md",
        _compiled_page(title="Overview", page_type="overview", body="# Overview\n"),
    )
    _write_text(tmp_path / "index" / "manifest.json", "[]")

    result = run_status(tmp_path)

    assert result["freshness"]["status"] == "invalid"
    assert result["freshness"]["manifest_content_identity"] is None
    assert result["manifest"] == {
        "path": "index/manifest.json",
        "present": True,
        "tokenizer_name": None,
        "records_indexed": None,
        "pages_indexed": None,
        "search_documents": None,
        "compiled_path_count": None,
    }

from __future__ import annotations

import json
from pathlib import Path

from tests.helpers.projection import compiler_projection

from snowiki.lint import run_lint
from snowiki.search.workspace import content_freshness_identity
from snowiki.status import run_status


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
            "content_identity": content_freshness_identity(tmp_path),
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

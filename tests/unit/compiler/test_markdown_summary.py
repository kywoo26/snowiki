from __future__ import annotations

from pathlib import Path

from tests.helpers.projection import compiler_projection

from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.paths import MAX_SUMMARY_SLUG_LENGTH, summary_slug_for_record
from snowiki.compiler.taxonomy import NormalizedRecord
from snowiki.storage.normalized import NormalizedStorage


def test_markdown_document_rebuild_projects_body_and_source_identity(
    tmp_path: Path,
) -> None:
    storage = NormalizedStorage(tmp_path)
    result = storage.store_markdown_document(
        source_root="/repo/docs",
        relative_path="guide.md",
        payload={
            "title": "Guide",
            "summary": "A short guide.",
            "text": "# Guide\n\nMarkdown body.",
            "projection": compiler_projection(
                "Guide",
                "A short guide.",
                body="# Guide\n\nMarkdown body.",
                tags=["docs"],
                source_identity={
                    "source_root": "/repo/docs",
                    "relative_path": "guide.md",
                    "content_hash": "abc123",
                },
                sections=[{"title": "Document", "body": "# Guide\n\nMarkdown body."}],
            ),
            "frontmatter": {"title": "Guide", "tags": ["docs"]},
            "promoted_frontmatter": {"title": "Guide", "tags": ["docs"]},
            "reserved_frontmatter": {},
            "source_path": "/repo/docs/guide.md",
            "source_root": "/repo/docs",
            "relative_path": "guide.md",
            "content_hash": "abc123",
            "source_metadata": {"extension": ".md", "size": 24},
        },
        raw_ref={
            "sha256": "abc123",
            "path": "raw/markdown/ab/c123",
            "size": 24,
            "mtime": "2026-04-08T12:00:00Z",
        },
        recorded_at="2026-04-08T12:00:00Z",
    )

    paths = CompilerEngine(tmp_path).rebuild()
    summary_paths = [path for path in paths if path.startswith("compiled/summaries/")]

    assert len(summary_paths) == 1
    assert "compiled/index.md" in paths
    assert "compiled/log.md" in paths
    rendered = (tmp_path / summary_paths[0]).read_text(encoding="utf-8")
    assert "Markdown body." in rendered
    assert 'summary: "A short guide."' in rendered
    assert 'summary: "# Guide' not in rendered
    assert "## Source Identity" in rendered
    assert "relative_path: `guide.md`" in rendered
    assert result["id"] in rendered


def test_summary_slug_for_record_bounds_long_titles() -> None:
    record = NormalizedRecord(
        id="record-1",
        path="normalized/markdown/documents/record-1.json",
        source_type="markdown",
        record_type="document",
        recorded_at="2026-04-08T12:00:00Z",
        payload={
            "projection": compiler_projection("Very Long Title " * 40)
        },
        raw_refs=[],
    )

    slug = summary_slug_for_record(record)

    assert len(slug) <= MAX_SUMMARY_SLUG_LENGTH
    assert slug.startswith("markdown-very-long-title")

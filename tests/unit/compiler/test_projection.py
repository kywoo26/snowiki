from __future__ import annotations

import inspect

import pytest
from tests.helpers.projection import compiler_projection

from snowiki.compiler.generators import summary as summary_generator
from snowiki.compiler.projection import (
    projected_sections,
    projected_source_identity,
    projected_summary,
    projected_tags,
    projected_taxonomy_items,
    projected_title,
)
from snowiki.compiler.taxonomy import NormalizedRecord, PageType


def test_projection_helpers_prefer_projection_fields() -> None:
    record = NormalizedRecord(
        id="record-1",
        path="normalized/markdown/documents/record-1.json",
        source_type="markdown",
        record_type="document",
        recorded_at="2026-04-08T12:00:00Z",
        payload={
            "title": "Legacy Title",
            "summary": "Legacy summary",
            "projection": compiler_projection(
                "Projected Title",
                "Projected summary",
                tags=["docs", "wiki"],
                source_identity={
                    "source_root": "/repo/docs",
                    "relative_path": "guide.md",
                    "content_hash": "abc123",
                },
                sections=[{"title": "Document", "body": "Projected body"}],
                topics=["Compiler Boundary"],
            ),
        },
        raw_refs=[],
    )

    assert projected_title(record) == "Projected Title"
    assert projected_summary(record) == "Projected summary"
    assert projected_tags(record) == ["docs", "wiki"]
    assert projected_source_identity(record) == {
        "source_root": "/repo/docs",
        "relative_path": "guide.md",
        "content_hash": "abc123",
    }
    assert projected_sections(record) == [{"title": "Document", "body": "Projected body"}]
    taxonomy = projected_taxonomy_items(record)
    assert [(item.page_type, item.title) for item in taxonomy] == [
        (PageType.TOPIC, "Compiler Boundary")
    ]


def test_projection_helpers_require_projection_contract() -> None:
    record = NormalizedRecord(
        id="record-1",
        path="normalized/markdown/documents/record-1.json",
        source_type="markdown",
        record_type="document",
        recorded_at="2026-04-08T12:00:00Z",
        payload={
            "summary": "Legacy summary",
            "text": "Legacy body",
            "promoted_frontmatter": {"tags": ["legacy", "docs"]},
            "source_root": "/repo/docs",
            "relative_path": "guide.md",
            "content_hash": "abc123",
            "topics": ["Legacy Topic"],
        },
        raw_refs=[],
    )

    with pytest.raises(ValueError, match="missing compiler projection"):
        _ = projected_title(record)


def test_summary_generator_has_no_markdown_source_type_branch() -> None:
    source = inspect.getsource(summary_generator.generate_summary_pages)

    assert 'source_type == "markdown"' not in source

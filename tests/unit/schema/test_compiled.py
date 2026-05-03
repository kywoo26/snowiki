from __future__ import annotations

from snowiki.schema.compiled import CompiledPage, PageType, compiled_page_path, slugify
from snowiki.schema.normalized import NormalizedRecord


def test_page_type_values_are_correct_and_ordered() -> None:
    assert [page_type.value for page_type in PageType] == [
        "summary",
        "concept",
        "entity",
        "topic",
        "question",
        "project",
        "decision",
        "session",
        "index",
        "log",
        "overview",
    ]


def test_compiled_page_path_uses_canonical_locations() -> None:
    assert compiled_page_path(PageType.INDEX, "ignored") == "compiled/index.md"
    assert compiled_page_path(PageType.LOG, "ignored") == "compiled/log.md"
    assert compiled_page_path(PageType.OVERVIEW, "ignored") == "compiled/overview.md"
    assert compiled_page_path(PageType.TOPIC, "hello") == "compiled/topics/hello.md"


def test_slugify_normalizes_titles() -> None:
    assert slugify("  Hello, Snowiki!  ") == "hello-snowiki"
    assert slugify("") == "untitled"


def test_compiled_page_path_property_returns_canonical_path() -> None:
    page = CompiledPage(
        page_type=PageType.TOPIC,
        slug="hello",
        title="Hello",
        created="2026-04-08T12:00:00Z",
        updated="2026-04-08T12:00:00Z",
    )

    assert page.path == "compiled/topics/hello.md"


def test_normalized_record_can_be_constructed_with_required_fields() -> None:
    record = NormalizedRecord(
        id="record-1",
        path="normalized/markdown/documents/record-1.json",
        source_type="markdown",
        record_type="document",
        recorded_at="2026-04-08T12:00:00Z",
        payload={"title": "Hello"},
        raw_refs=[],
    )

    assert record.id == "record-1"
    assert record.path == "normalized/markdown/documents/record-1.json"

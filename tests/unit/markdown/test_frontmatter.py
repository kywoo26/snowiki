from __future__ import annotations

from snowiki.markdown import parse_markdown_document


def test_parse_markdown_document_promotes_safe_frontmatter() -> None:
    document = parse_markdown_document(
        """---
title: Example Note
tags:
  - snowiki
  - ingest
summary: Short summary
provenance: user supplied
---
# Body

Hello world.
"""
    )

    assert document.frontmatter["title"] == "Example Note"
    assert document.promoted == {
        "summary": "Short summary",
        "tags": ["snowiki", "ingest"],
        "title": "Example Note",
    }
    assert document.reserved == {"provenance": "user supplied"}
    assert document.body.startswith("# Body")
    assert document.text.endswith("Hello world.")


def test_parse_markdown_document_without_frontmatter_preserves_body() -> None:
    document = parse_markdown_document("# Plain\n\nNo frontmatter.\n")

    assert document.frontmatter == {}
    assert document.promoted == {}
    assert document.reserved == {}
    assert document.text == "# Plain\n\nNo frontmatter."

from __future__ import annotations

from snowiki.markdown import parse_markdown_document
from snowiki.markdown.frontmatter import parse_frontmatter


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
    assert document.structure.headings[0].text == "Body"


def test_parse_markdown_document_without_frontmatter_preserves_body() -> None:
    document = parse_markdown_document("# Plain\n\nNo frontmatter.\n")

    assert document.frontmatter == {}
    assert document.promoted == {}
    assert document.reserved == {}
    assert document.text == "# Plain\n\nNo frontmatter."


def test_parse_frontmatter_uses_yaml_for_supported_frontmatter() -> None:
    frontmatter = parse_frontmatter(
        """
tags: [snowiki, ingest, 7]
objects: [{"nested": true}]
"""
    )

    assert frontmatter["tags"] == ["snowiki", "ingest", 7]
    assert frontmatter["objects"] == [{"nested": True}]


def test_parse_frontmatter_rejects_malformed_yaml() -> None:
    try:
        _ = parse_frontmatter(" : missing key\ntitle: Example\n")
    except ValueError as exc:
        assert str(exc) == "invalid YAML frontmatter"
    else:  # pragma: no cover - defensive assertion branch
        raise AssertionError("malformed YAML frontmatter should be rejected")


def test_parse_frontmatter_coerces_yaml_native_values_deterministically() -> None:
    frontmatter = parse_frontmatter(
        """
flags: !!set {b: null, a: null}
bad_number: .nan
"""
    )

    assert frontmatter == {"flags": ["a", "b"], "bad_number": "nan"}


def test_parse_markdown_document_treats_unclosed_frontmatter_as_body() -> None:
    document = parse_markdown_document("---\ntitle: Not Frontmatter\n# Body\n")

    assert document.frontmatter == {}
    assert document.body == "---\ntitle: Not Frontmatter\n# Body"
    assert document.text == "---\ntitle: Not Frontmatter\n# Body"


def test_parse_markdown_document_accepts_empty_frontmatter_block() -> None:
    document = parse_markdown_document("---\n---\n# Body\n")

    assert document.frontmatter == {}
    assert document.body == "# Body"
    assert document.text == "# Body"

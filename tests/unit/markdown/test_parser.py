from __future__ import annotations

from snowiki.markdown.parser import first_markdown_heading, parse_markdown_body


def test_parse_markdown_body_extracts_structural_dtos() -> None:
    structure = parse_markdown_body(
        """
Intro with [[Home]] and [site](https://example.com).

# Title

Body with **formatting**.

## Section

More text.
""".strip()
    )

    assert [(heading.level, heading.text) for heading in structure.headings] == [
        (1, "Title"),
        (2, "Section"),
    ]
    assert [(section.title, section.body) for section in structure.sections] == [
        ("Document", "Intro with [[Home]] and [site](https://example.com)."),
        ("Title", "Body with **formatting**."),
        ("Section", "More text."),
    ]
    assert [(link.text, link.target) for link in structure.links] == [
        ("site", "https://example.com")
    ]
    assert structure.wikilinks == ("Home",)
    assert structure.plain_text == (
        "Intro with [[Home]] and [site](https://example.com).\n"
        "Title\n"
        "Body with **formatting**.\n"
        "Section\n"
        "More text."
    )


def test_first_markdown_heading_ignores_code_fence_hashes_and_supports_setext() -> None:
    assert (
        first_markdown_heading(
            """
```python
# Not a heading
```

Real Heading
------------
"""
        )
        == "Real Heading"
    )


def test_parse_markdown_body_ignores_wikilinks_inside_inline_and_fenced_code() -> None:
    structure = parse_markdown_body(
        """
Text [[Real]] and `[[InlineCode]]`.

```markdown
[[FencedCode]]
```
""".strip()
    )

    assert structure.wikilinks == ("Real",)

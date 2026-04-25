from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from markdown_it import MarkdownIt
from markdown_it.token import Token


@dataclass(frozen=True, slots=True)
class MarkdownHeading:
    """Snowiki-owned heading extracted from Markdown body structure."""

    level: int
    text: str
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    """Snowiki-owned link extracted from Markdown inline structure."""

    text: str
    target: str


@dataclass(frozen=True, slots=True)
class MarkdownSection:
    """Compiler-facing section derived from Markdown headings."""

    title: str
    body: str
    level: int
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class MarkdownBodyStructure:
    """Parsed Markdown body data without exposing parser-specific tokens."""

    headings: tuple[MarkdownHeading, ...]
    sections: tuple[MarkdownSection, ...]
    links: tuple[MarkdownLink, ...]
    wikilinks: tuple[str, ...]
    plain_text: str


WIKILINK_PATTERN: Pattern[str] = re.compile(r"\[\[([^\]\n]+)\]\]")


def parse_markdown_body(text: str) -> MarkdownBodyStructure:
    """Parse Markdown body into Snowiki-owned structural data."""
    tokens = MarkdownIt("commonmark").parse(text)
    headings = _extract_headings(tokens)
    return MarkdownBodyStructure(
        headings=tuple(headings),
        sections=_extract_sections(text, headings),
        links=_extract_links(tokens),
        wikilinks=_extract_wikilinks(tokens),
        plain_text=_extract_plain_text(tokens),
    )


def first_markdown_heading(text: str) -> str | None:
    """Return the first parsed Markdown heading text, if present."""
    structure = parse_markdown_body(text)
    return structure.headings[0].text if structure.headings else None


def _extract_headings(tokens: list[Token]) -> list[MarkdownHeading]:
    headings: list[MarkdownHeading] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or not token.tag.startswith("h"):
            continue
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        heading_text = inline.content.strip() if inline and inline.type == "inline" else ""
        if not heading_text:
            continue
        headings.append(
            MarkdownHeading(
                level=_heading_level(token.tag),
                text=heading_text,
                start_line=_token_start_line(token),
                end_line=_token_end_line(token),
            )
        )
    return headings


def _extract_sections(
    text: str,
    headings: list[MarkdownHeading],
) -> tuple[MarkdownSection, ...]:
    if not text.strip():
        return ()
    lines = text.splitlines()
    if not headings:
        return (
            MarkdownSection(
                title="Document",
                body=text.strip(),
                level=0,
                start_line=0,
                end_line=len(lines),
            ),
        )

    sections: list[MarkdownSection] = []
    first_heading = headings[0]
    preamble = "\n".join(lines[: first_heading.start_line]).strip()
    if preamble:
        sections.append(
            MarkdownSection(
                title="Document",
                body=preamble,
                level=0,
                start_line=0,
                end_line=first_heading.start_line,
            )
        )

    for index, heading in enumerate(headings):
        next_line = headings[index + 1].start_line if index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[heading.end_line : next_line]).strip()
        if body:
            sections.append(
                MarkdownSection(
                    title=heading.text,
                    body=body,
                    level=heading.level,
                    start_line=heading.end_line,
                    end_line=next_line,
                )
            )
    return tuple(sections)


def _extract_links(tokens: list[Token]) -> tuple[MarkdownLink, ...]:
    links: list[MarkdownLink] = []
    for token in tokens:
        if token.type != "inline" or not token.children:
            continue
        children = token.children
        for index, child in enumerate(children):
            if child.type != "link_open":
                continue
            href = child.attrGet("href")
            if not href:
                continue
            links.append(
                MarkdownLink(text=_link_text(children[index + 1 :]), target=str(href))
            )
    return tuple(links)


def _extract_wikilinks(tokens: list[Token]) -> tuple[str, ...]:
    wikilinks: list[str] = []
    for token in tokens:
        if token.type != "inline" or not token.children:
            continue
        for child in token.children:
            if child.type != "text" or not child.content:
                continue
            wikilinks.extend(
                match.strip()
                for match in WIKILINK_PATTERN.findall(child.content)
                if match.strip()
            )
    return tuple(wikilinks)


def _extract_plain_text(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.type in {"inline", "code_block", "fence"} and token.content.strip():
            parts.append(token.content.strip())
    return "\n".join(parts)


def _link_text(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.type == "link_close":
            break
        if token.content:
            parts.append(token.content)
    return "".join(parts).strip()


def _heading_level(tag: str) -> int:
    try:
        return int(tag[1:])
    except ValueError:
        return 0


def _token_start_line(token: Token) -> int:
    if token.map is None:
        return 0
    return token.map[0]


def _token_end_line(token: Token) -> int:
    if token.map is None:
        return _token_start_line(token)
    return token.map[1]

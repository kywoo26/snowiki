from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, PageSection
from snowiki.search import (
    InvertedIndex,
    SearchHit,
    build_blended_index,
    build_lexical_index,
    build_wiki_index,
)
from snowiki.search.queries.topical import topical_recall


class QueryHitPayload(TypedDict):
    """Serializable query hit payload."""

    id: str
    path: str
    title: str
    kind: str
    source_type: str
    score: float
    matched_terms: list[str]
    summary: str


class QueryResult(TypedDict):
    """Serializable query command result."""

    query: str
    mode: str
    semantic_backend: str | None
    records_indexed: int
    pages_indexed: int
    hits: list[QueryHitPayload]


class QueryCommandPayload(TypedDict):
    """Top-level payload emitted by the query command."""

    ok: bool
    command: str
    result: QueryResult


def _normalize_output_mode(value: str) -> OutputMode:
    """Normalize Click output strings to the CLI output mode type."""
    return "json" if value == "json" else "human"


def load_normalized_records(root: Path) -> list[dict[str, object]]:
    """Load normalized JSON records from the storage tree."""
    records: list[dict[str, object]] = []
    normalized_root = root / "normalized"
    if not normalized_root.exists():
        return records
    for path in sorted(
        normalized_root.rglob("*.json"), key=lambda item: item.as_posix()
    ):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def _page_body(sections: list[PageSection]) -> str:
    """Render compiled sections into a plain-text body for indexing."""
    return "\n\n".join(f"{section.title}\n{section.body}" for section in sections)


def _page_to_mapping(page: CompiledPage) -> dict[str, object]:
    return {
        "id": page.path,
        "path": page.path,
        "title": page.title,
        "summary": page.summary,
        "body": _page_body(page.sections),
        "tags": page.tags,
        "related": page.related,
        "record_ids": page.record_ids,
        "updated_at": page.updated,
    }


def build_search_index(root: Path) -> tuple[InvertedIndex, int, int]:
    """Build the blended query index for the current workspace."""
    records = load_normalized_records(root)
    pages = CompilerEngine(root).build_pages() if records else []
    lexical = build_lexical_index(records)
    wiki = build_wiki_index(_page_to_mapping(page) for page in pages)
    return (
        build_blended_index(lexical.documents, wiki.documents),
        len(records),
        len(pages),
    )


def _hit_to_payload(hit: SearchHit) -> QueryHitPayload:
    return {
        "id": hit.document.id,
        "path": hit.document.path,
        "title": hit.document.title,
        "kind": hit.document.kind,
        "source_type": hit.document.source_type,
        "score": round(hit.score, 6),
        "matched_terms": list(hit.matched_terms),
        "summary": hit.document.summary,
    }


def _render_query_human(payload: object) -> str:
    """Render a query result payload for human-readable CLI output."""
    if not isinstance(payload, dict):
        raise TypeError("query renderer expected a dictionary payload")
    result = cast(QueryCommandPayload, payload)["result"]
    lines = [
        f"Query mode: {result['mode']}",
        f"records indexed: {result['records_indexed']}",
        f"pages indexed: {result['pages_indexed']}",
        f"hits: {len(result['hits'])}",
    ]
    for index, hit in enumerate(result["hits"], start=1):
        lines.append(
            f"{index}. [{hit['kind']}] {hit['title']} ({hit['path']}) score={hit['score']}"
        )
    return "\n".join(lines)


def run_query(root: Path, query: str, *, mode: str, top_k: int) -> QueryResult:
    """Execute a topical query against normalized and compiled content."""
    index, record_count, page_count = build_search_index(root)
    hits = topical_recall(index, query, limit=top_k)
    return {
        "query": query,
        "mode": mode,
        "semantic_backend": "disabled" if mode == "hybrid" else None,
        "records_indexed": record_count,
        "pages_indexed": page_count,
        "hits": [_hit_to_payload(hit) for hit in hits],
    }


@click.command("query")
@click.argument("query")
@click.option(
    "--mode",
    type=click.Choice(["lexical", "hybrid"], case_sensitive=False),
    default="lexical",
    show_default=True,
)
@click.option("--top-k", type=click.IntRange(min=1), default=5, show_default=True)
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def command(query: str, mode: str, top_k: int, output: str) -> None:
    """Run the query CLI command."""
    output_mode = _normalize_output_mode(output)
    result: QueryResult | None = None
    try:
        result = run_query(Path.cwd(), query, mode=mode, top_k=top_k)
    except Exception as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="query_failed",
            details={"query": query, "mode": mode, "top_k": top_k},
        )
    if result is None:
        raise RuntimeError("query did not produce a result")
    emit_result(
        {"ok": True, "command": "query", "result": result},
        output=output_mode,
        human_renderer=_render_query_human,
    )

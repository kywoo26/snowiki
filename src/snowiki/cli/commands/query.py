from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TypedDict, cast

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.config import get_snowiki_root
from snowiki.search import InvertedIndex, SearchHit
from snowiki.search.queries.topical import topical_recall
from snowiki.search.workspace import build_search_index as build_workspace_search_index


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


def _tree_signature(root: Path) -> tuple[int, int]:
    if not root.exists():
        return (0, 0)
    latest_mtime = root.stat().st_mtime_ns
    file_count = 0
    for path in root.rglob("*"):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        latest_mtime = max(latest_mtime, stat.st_mtime_ns)
        if path.is_file():
            file_count += 1
    return (latest_mtime, file_count)


def _search_index_cache_key(root: Path) -> tuple[str, tuple[int, int], tuple[int, int]]:
    resolved_root = root.resolve()
    return (
        str(resolved_root),
        _tree_signature(resolved_root / "normalized"),
        _tree_signature(resolved_root / "compiled"),
    )


@lru_cache(maxsize=8)
def _build_search_index_cached(
    cache_key: tuple[str, tuple[int, int], tuple[int, int]],
) -> tuple[InvertedIndex, int, int]:
    return build_workspace_search_index(Path(cache_key[0]))


def clear_query_search_index_cache() -> None:
    _build_search_index_cached.cache_clear()


def build_search_index(root: Path) -> tuple[InvertedIndex, int, int]:
    return _build_search_index_cached(_search_index_cache_key(root))


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
    result = cast(QueryCommandPayload, cast(object, payload))["result"]
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
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Snowiki storage root (defaults to ~/.snowiki)",
)
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def command(query: str, mode: str, top_k: int, root: Path | None, output: str) -> None:
    """Run the query CLI command."""
    output_mode = _normalize_output_mode(output)
    try:
        result = run_query(
            root if root else get_snowiki_root(), query, mode=mode, top_k=top_k
        )
    except Exception as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="query_failed",
            details={"query": query, "mode": mode, "top_k": top_k},
        )
    emit_result(
        {"ok": True, "command": "query", "result": result},
        output=output_mode,
        human_renderer=_render_query_human,
    )

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.config import (
    SUPPORTED_RUNTIME_LEXICAL_POLICIES,
    get_snowiki_root,
    select_runtime_lexical_policy,
)
from snowiki.search import SearchHit
from snowiki.search.queries.topical import topical_recall
from snowiki.search.workspace import build_retrieval_snapshot


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
    lexical_policy: str
    lexical_policy_source: str
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


def run_query(
    root: Path,
    query: str,
    *,
    mode: str,
    top_k: int,
    lexical_policy: str | None = None,
    config_lexical_policy: str | None = None,
    env: Mapping[str, str] | None = None,
) -> QueryResult:
    """Execute a topical query against normalized and compiled content."""
    selected_policy = select_runtime_lexical_policy(
        lexical_policy,
        env=env,
        config_policy=config_lexical_policy,
    )
    snapshot = build_retrieval_snapshot(root, lexical_policy=selected_policy.policy)
    hits = topical_recall(snapshot.index, query, limit=top_k)
    return {
        "query": query,
        "mode": mode,
        "lexical_policy": snapshot.lexical_policy,
        "lexical_policy_source": selected_policy.source,
        "semantic_backend": "disabled" if mode == "hybrid" else None,
        "records_indexed": snapshot.records_indexed,
        "pages_indexed": snapshot.pages_indexed,
        "hits": [_hit_to_payload(hit) for hit in hits],
    }


@click.command("query")
@click.argument("query")
@click.option(
    "--mode",
    type=click.Choice(["lexical", "hybrid"], case_sensitive=False),
    default="lexical",
    show_default=True,
    help="Search mode. 'hybrid' is currently a lexical/no-op compatibility surface.",
)
@click.option("--top-k", type=click.IntRange(min=1), default=5, show_default=True)
@click.option(
    "--lexical-policy",
    type=click.Choice(SUPPORTED_RUNTIME_LEXICAL_POLICIES, case_sensitive=False),
    default=None,
    help="Runtime lexical policy override. Precedence: CLI > env > config > default.",
)
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
def command(
    query: str,
    mode: str,
    top_k: int,
    lexical_policy: str | None,
    root: Path | None,
    output: str,
) -> None:
    """Run the query CLI command."""
    output_mode = _normalize_output_mode(output)
    try:
        result = run_query(
            root if root else get_snowiki_root(),
            query,
            mode=mode,
            top_k=top_k,
            lexical_policy=lexical_policy,
        )
    except Exception as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="query_failed",
            details={
                "query": query,
                "mode": mode,
                "top_k": top_k,
                "lexical_policy": lexical_policy,
            },
        )
    emit_result(
        {"ok": True, "command": "query", "result": result},
        output=output_mode,
        human_renderer=_render_query_human,
    )

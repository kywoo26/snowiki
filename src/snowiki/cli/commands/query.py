from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast

import click

from snowiki.cli.context import (
    SnowikiCliContext,
    bind_cli_context,
    initialize_cli_root,
    pass_snowiki_context,
)
from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_error, emit_result
from snowiki.search.queries import QueryResult, run_query


class QueryCommandPayload(TypedDict):
    """Top-level payload emitted by the query command."""

    ok: bool
    command: str
    result: QueryResult


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


@click.command("query", short_help="Search the wiki index.")
@click.argument("query")
@click.option(
    "--mode",
    type=click.Choice(["lexical", "hybrid"], case_sensitive=False),
    default="lexical",
    show_default=True,
    help="Search mode. 'hybrid' is currently a lexical/no-op compatibility surface.",
)
@click.option("--top-k", type=click.IntRange(min=1), default=5, show_default=True)
@root_option
@output_option
@pass_snowiki_context
def command(
    cli_context: SnowikiCliContext,
    query: str,
    mode: str,
    top_k: int,
    root: Path | None,
    output: str,
) -> None:
    """Run the query CLI command."""
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        result = run_query(initialize_cli_root(cli_context), query, mode=mode, top_k=top_k)
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
